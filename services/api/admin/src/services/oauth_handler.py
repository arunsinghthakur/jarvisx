"""
OAuth2/OIDC authentication handler for Google, Microsoft, and Okta
"""
import secrets
import logging
from typing import Dict, Optional, Tuple
from urllib.parse import urlencode
from authlib.integrations.starlette_client import OAuth
from authlib.integrations.base_client import OAuthError
from authlib.jose import jwt, JsonWebKey
from authlib.jose.errors import JoseError
import httpx

from jarvisx.database.models import SSOConfig
from services.api.admin.src.models.sso import SSOUserInfo
from services.api.admin.src.config.sso_settings import get_sso_settings

logger = logging.getLogger(__name__)


# OAuth provider configurations
OAUTH_PROVIDERS = {
    "google": {
        "server_metadata_url": "https://accounts.google.com/.well-known/openid-configuration",
        "client_kwargs": {"scope": "openid email profile"},
    },
    "microsoft": {
        "server_metadata_url": "https://login.microsoftonline.com/{tenant_id}/v2.0/.well-known/openid-configuration",
        "client_kwargs": {"scope": "openid email profile"},
    },
    "okta": {
        "server_metadata_url": "{okta_domain}/.well-known/openid-configuration",
        "client_kwargs": {"scope": "openid email profile"},
    },
}


class OAuthHandler:
    """Handler for OAuth2/OIDC authentication"""

    def __init__(self):
        self.oauth = OAuth()
        self._registered_clients = {}
        self._jwks_cache = {}  # Cache for JWKS keys
        self.settings = get_sso_settings()

    def _get_provider_config(self, sso_config: SSOConfig) -> Dict:
        """Get provider-specific OAuth configuration"""
        provider = sso_config.provider
        base_config = OAUTH_PROVIDERS.get(provider, {}).copy()

        if provider == "microsoft" and sso_config.tenant_id:
            # Azure AD specific
            base_config["server_metadata_url"] = base_config["server_metadata_url"].format(
                tenant_id=sso_config.tenant_id
            )
        elif provider == "okta" and sso_config.provider_config:
            # Okta specific
            okta_domain = sso_config.provider_config.get("okta_domain")
            if okta_domain:
                base_config["server_metadata_url"] = base_config["server_metadata_url"].format(
                    okta_domain=okta_domain
                )

        return base_config

    def _register_client(self, sso_config: SSOConfig, redirect_uri: str, decrypted_secret: str = None) -> str:
        """Register OAuth client dynamically"""
        client_name = f"{sso_config.provider}_{sso_config.organization_id}"

        if client_name in self._registered_clients and decrypted_secret is None:
            return client_name

        provider_config = self._get_provider_config(sso_config)

        client_secret = decrypted_secret if decrypted_secret else sso_config.client_secret

        self.oauth.register(
            name=client_name,
            client_id=sso_config.client_id,
            client_secret=client_secret,
            server_metadata_url=provider_config.get("server_metadata_url"),
            client_kwargs=provider_config.get("client_kwargs", {}),
            overwrite=True,
        )

        self._registered_clients[client_name] = True
        return client_name

    async def get_authorization_url(
        self, sso_config: SSOConfig, redirect_uri: str, decrypted_secret: str = None
    ) -> Tuple[str, str]:
        """
        Generate OAuth authorization URL

        Returns:
            Tuple of (authorization_url, state)
        """
        client_name = self._register_client(sso_config, redirect_uri, decrypted_secret)
        client = getattr(self.oauth, client_name)

        auth_params = {
            "redirect_uri": redirect_uri,
        }

        if sso_config.provider == "microsoft":
            auth_params["response_mode"] = "query"

        result = await client.create_authorization_url(**auth_params)
        logger.info(f"create_authorization_url result: {result}")

        if isinstance(result, dict):
            authorization_url = result.get('url')
            state = result.get('state')
            if not authorization_url:
                raise ValueError(f"No 'url' key found in result: {result}")
            if not state:
                raise ValueError(f"No 'state' key found in result: {result}")
            logger.info(f"Extracted URL and state from authlib")
        elif isinstance(result, tuple):
            authorization_url, state = result[0], result[1] if len(result) > 1 else secrets.token_urlsafe(32)
        else:
            raise ValueError(f"Unexpected result type: {type(result)}, value: {result}")

        return authorization_url, state

    async def handle_callback(
        self,
        sso_config: SSOConfig,
        code: str,
        redirect_uri: str,
        decrypted_secret: str = None,
    ) -> SSOUserInfo:
        """
        Handle OAuth callback and exchange code for user info

        Args:
            sso_config: SSO configuration
            code: Authorization code from provider
            redirect_uri: Redirect URI used in authorization
            decrypted_secret: Decrypted client secret

        Returns:
            SSOUserInfo with user details

        Raises:
            OAuthError: If token exchange or user info retrieval fails
        """
        client_name = self._register_client(sso_config, redirect_uri, decrypted_secret)
        client = getattr(self.oauth, client_name)

        try:
            # Exchange code for token
            token = await client.fetch_access_token(
                redirect_uri=redirect_uri,
                code=code,
            )

            # Get user info
            if sso_config.provider == "google":
                user_info = await self._get_google_user_info(token)
            elif sso_config.provider == "microsoft":
                user_info = await self._get_microsoft_user_info(token)
            elif sso_config.provider == "okta":
                user_info = await self._get_okta_user_info(token)
            else:
                raise OAuthError(f"Unsupported provider: {sso_config.provider}")

            return user_info

        except Exception as e:
            raise OAuthError(f"OAuth callback failed: {str(e)}")

    async def _fetch_jwks(self, jwks_uri: str) -> Dict:
        """Fetch JWKS from provider"""
        if jwks_uri in self._jwks_cache:
            return self._jwks_cache[jwks_uri]

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(jwks_uri)
                resp.raise_for_status()
                jwks = resp.json()
                self._jwks_cache[jwks_uri] = jwks
                return jwks
        except Exception as e:
            logger.error(f"Failed to fetch JWKS: {e}")
            raise OAuthError("Failed to fetch JWKS for token verification")

    async def _verify_id_token(self, id_token: str, provider: str, client_id: str) -> Dict:
        """Verify JWT ID token signature"""
        if not self.settings.sso_verify_jwt_signature:
            logger.warning("JWT signature verification is disabled - not recommended for production")
            return jwt.decode(id_token, claims_options={"verify_signature": False})

        try:
            # Get JWKS URI based on provider
            jwks_uri_map = {
                "google": "https://www.googleapis.com/oauth2/v3/certs",
                "microsoft": f"https://login.microsoftonline.com/common/discovery/v2.0/keys",
                "okta": None,  # Will be in provider config
            }

            jwks_uri = jwks_uri_map.get(provider)
            if not jwks_uri:
                logger.warning(f"JWKS URI not configured for {provider}, skipping verification")
                return jwt.decode(id_token, claims_options={"verify_signature": False})

            # Fetch JWKS
            jwks = await self._fetch_jwks(jwks_uri)

            # Verify token
            claims = jwt.decode(
                id_token,
                jwks,
                claims_options={
                    "iss": {"essential": True},
                    "aud": {"essential": True, "value": client_id},
                }
            )
            return claims

        except JoseError as e:
            logger.error(f"JWT verification failed: {e}")
            raise OAuthError(f"Invalid ID token: {str(e)}")
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            # Fall back to unverified if verification fails
            logger.warning("Falling back to unverified token due to verification error")
            return jwt.decode(id_token, claims_options={"verify_signature": False})

    async def _get_google_user_info(self, token: Dict) -> SSOUserInfo:
        """Extract user info from Google OAuth token"""
        id_token = token.get("id_token")
        if id_token:
            # Verify and decode token
            try:
                claims = await self._verify_id_token(id_token, "google", token.get("client_id", ""))
            except Exception as e:
                logger.warning(f"Token verification failed, using userinfo endpoint: {e}")
                # Fallback to userinfo endpoint
                async with httpx.AsyncClient() as client:
                    resp = await client.get(
                        "https://www.googleapis.com/oauth2/v3/userinfo",
                        headers={"Authorization": f"Bearer {token['access_token']}"},
                    )
                    resp.raise_for_status()
                    claims = resp.json()
        else:
            # Fallback: fetch from userinfo endpoint
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://www.googleapis.com/oauth2/v3/userinfo",
                    headers={"Authorization": f"Bearer {token['access_token']}"},
                )
                resp.raise_for_status()
                claims = resp.json()

        return SSOUserInfo(
            email=claims.get("email"),
            first_name=claims.get("given_name"),
            last_name=claims.get("family_name"),
            provider="google",
            provider_user_id=claims.get("sub"),
            raw_claims=claims,
        )

    async def _get_microsoft_user_info(self, token: Dict) -> SSOUserInfo:
        """Extract user info from Microsoft OAuth token"""
        id_token = token.get("id_token")
        if id_token:
            try:
                claims = await self._verify_id_token(id_token, "microsoft", token.get("client_id", ""))
            except Exception as e:
                logger.warning(f"Token verification failed, using Graph API: {e}")
                # Fallback to Microsoft Graph API
                async with httpx.AsyncClient() as client:
                    resp = await client.get(
                        "https://graph.microsoft.com/v1.0/me",
                        headers={"Authorization": f"Bearer {token['access_token']}"},
                    )
                    resp.raise_for_status()
                    claims = resp.json()
        else:
            # Fallback: fetch from Microsoft Graph API
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://graph.microsoft.com/v1.0/me",
                    headers={"Authorization": f"Bearer {token['access_token']}"},
                )
                resp.raise_for_status()
                claims = resp.json()

        # Microsoft uses different claim names
        email = claims.get("email") or claims.get("upn") or claims.get("preferred_username")
        given_name = claims.get("given_name") or claims.get("givenName")
        family_name = claims.get("family_name") or claims.get("surname")

        return SSOUserInfo(
            email=email,
            first_name=given_name,
            last_name=family_name,
            provider="microsoft",
            provider_user_id=claims.get("oid") or claims.get("sub"),
            raw_claims=claims,
        )

    async def _get_okta_user_info(self, token: Dict) -> SSOUserInfo:
        """Extract user info from Okta OAuth token"""
        id_token = token.get("id_token")
        if not id_token:
            raise OAuthError("No id_token in Okta response")

        try:
            claims = await self._verify_id_token(id_token, "okta", token.get("client_id", ""))
        except Exception as e:
            logger.warning(f"Okta token verification failed: {e}")
            # Fall back to unverified for Okta
            claims = jwt.decode(id_token, claims_options={"verify_signature": False})

        return SSOUserInfo(
            email=claims.get("email"),
            first_name=claims.get("given_name"),
            last_name=claims.get("family_name"),
            provider="okta",
            provider_user_id=claims.get("sub"),
            raw_claims=claims,
        )


# Singleton instance
oauth_handler = OAuthHandler()
