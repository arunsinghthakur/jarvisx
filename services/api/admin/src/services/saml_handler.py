"""
SAML 2.0 authentication handler for enterprise SSO
"""
from typing import Dict, Optional
from onelogin.saml2.auth import OneLogin_Saml2_Auth
from onelogin.saml2.settings import OneLogin_Saml2_Settings
from onelogin.saml2.utils import OneLogin_Saml2_Utils

from jarvisx.database.models import SSOConfig
from services.api.admin.src.models.sso import SSOUserInfo


class SAMLHandler:
    """Handler for SAML 2.0 authentication"""

    def _build_saml_settings(
        self,
        sso_config: SSOConfig,
        acs_url: str,
        entity_id: str,
    ) -> Dict:
        """
        Build python3-saml settings dictionary

        Args:
            sso_config: SSO configuration from database
            acs_url: Assertion Consumer Service URL (callback URL)
            entity_id: Service Provider Entity ID

        Returns:
            Dictionary compatible with python3-saml settings
        """
        settings = {
            "strict": True,
            "debug": False,
            "sp": {
                "entityId": entity_id,
                "assertionConsumerService": {
                    "url": acs_url,
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
                },
                "singleLogoutService": {
                    "url": acs_url,  # Can be different endpoint if needed
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
                },
                "NameIDFormat": "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
            },
            "idp": {
                "entityId": sso_config.idp_entity_id,
                "singleSignOnService": {
                    "url": sso_config.idp_sso_url,
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
                },
                "x509cert": sso_config.idp_x509_cert,
            },
            "security": {
                "nameIdEncrypted": False,
                "authnRequestsSigned": False,
                "logoutRequestSigned": False,
                "logoutResponseSigned": False,
                "signMetadata": False,
                "wantMessagesSigned": False,
                "wantAssertionsSigned": True,
                "wantNameId": True,
                "wantNameIdEncrypted": False,
                "wantAssertionsEncrypted": False,
                "signatureAlgorithm": "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256",
                "digestAlgorithm": "http://www.w3.org/2001/04/xmlenc#sha256",
            },
        }

        # Merge provider-specific configuration
        if sso_config.provider_config:
            if "sp" in sso_config.provider_config:
                settings["sp"].update(sso_config.provider_config["sp"])
            if "idp" in sso_config.provider_config:
                settings["idp"].update(sso_config.provider_config["idp"])
            if "security" in sso_config.provider_config:
                settings["security"].update(sso_config.provider_config["security"])

        return settings

    def _prepare_request(self, request_data: Dict) -> Dict:
        """
        Prepare FastAPI request for python3-saml

        Args:
            request_data: Dict containing HTTP request information

        Returns:
            Dictionary compatible with python3-saml request format
        """
        return {
            "http_host": request_data.get("http_host"),
            "script_name": request_data.get("script_name", ""),
            "server_port": request_data.get("server_port", 443),
            "get_data": request_data.get("get_data", {}),
            "post_data": request_data.get("post_data", {}),
            "https": request_data.get("https", "on"),
        }

    def get_authorization_url(
        self,
        sso_config: SSOConfig,
        acs_url: str,
        entity_id: str,
        relay_state: Optional[str] = None,
        request_data: Optional[Dict] = None,
    ) -> str:
        """
        Generate SAML SSO redirect URL

        Args:
            sso_config: SSO configuration
            acs_url: Assertion Consumer Service URL
            entity_id: Service Provider Entity ID
            relay_state: Optional RelayState parameter
            request_data: HTTP request information

        Returns:
            SAML SSO redirect URL
        """
        settings = self._build_saml_settings(sso_config, acs_url, entity_id)

        # Create minimal request if not provided
        if request_data is None:
            request_data = {
                "http_host": "localhost",
                "script_name": "/",
                "server_port": 443,
                "https": "on",
            }

        prepared_request = self._prepare_request(request_data)

        auth = OneLogin_Saml2_Auth(prepared_request, settings)

        # Generate SSO URL
        sso_url = auth.login(return_to=relay_state)

        return sso_url

    def process_response(
        self,
        sso_config: SSOConfig,
        saml_response: str,
        acs_url: str,
        entity_id: str,
        request_data: Dict,
    ) -> SSOUserInfo:
        """
        Process SAML response and extract user info

        Args:
            sso_config: SSO configuration
            saml_response: Base64 encoded SAML response
            acs_url: Assertion Consumer Service URL
            entity_id: Service Provider Entity ID
            request_data: HTTP request information

        Returns:
            SSOUserInfo with user details

        Raises:
            Exception: If SAML response validation fails
        """
        settings = self._build_saml_settings(sso_config, acs_url, entity_id)

        # Add SAMLResponse to request data
        request_data = request_data.copy()
        if "post_data" not in request_data:
            request_data["post_data"] = {}
        request_data["post_data"]["SAMLResponse"] = saml_response

        prepared_request = self._prepare_request(request_data)

        auth = OneLogin_Saml2_Auth(prepared_request, settings)

        # Process the SAML response
        auth.process_response()

        errors = auth.get_errors()
        if errors:
            error_reason = auth.get_last_error_reason()
            raise Exception(f"SAML response validation failed: {errors}. Reason: {error_reason}")

        if not auth.is_authenticated():
            raise Exception("SAML authentication failed")

        # Extract user attributes
        attributes = auth.get_attributes()
        nameid = auth.get_nameid()

        # Map SAML attributes to user info
        # Common attribute mappings (can be customized via provider_config)
        email = (
            nameid
            if "@" in nameid
            else (
                attributes.get("email", [None])[0]
                or attributes.get("mail", [None])[0]
                or attributes.get("emailAddress", [None])[0]
            )
        )

        first_name = (
            attributes.get("firstName", [None])[0]
            or attributes.get("givenName", [None])[0]
            or attributes.get("given_name", [None])[0]
        )

        last_name = (
            attributes.get("lastName", [None])[0]
            or attributes.get("surname", [None])[0]
            or attributes.get("sn", [None])[0]
            or attributes.get("family_name", [None])[0]
        )

        return SSOUserInfo(
            email=email,
            first_name=first_name,
            last_name=last_name,
            provider="saml",
            provider_user_id=nameid,
            raw_claims={
                "nameid": nameid,
                "attributes": attributes,
                "session_index": auth.get_session_index(),
            },
        )

    def get_metadata(
        self,
        sso_config: SSOConfig,
        acs_url: str,
        entity_id: str,
    ) -> str:
        """
        Generate Service Provider metadata XML

        Args:
            sso_config: SSO configuration
            acs_url: Assertion Consumer Service URL
            entity_id: Service Provider Entity ID

        Returns:
            XML metadata string
        """
        settings = self._build_saml_settings(sso_config, acs_url, entity_id)
        saml_settings = OneLogin_Saml2_Settings(settings)

        metadata = saml_settings.get_sp_metadata()
        errors = saml_settings.validate_metadata(metadata)

        if errors:
            raise Exception(f"Metadata validation failed: {errors}")

        return metadata


# Singleton instance
saml_handler = SAMLHandler()
