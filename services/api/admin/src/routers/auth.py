from fastapi import APIRouter, HTTPException, Depends, Header, Form, Request, Response
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import uuid
import secrets
import logging

from jarvisx.database.models import User, RefreshToken, Organization, Team, TeamMember, SSOConfig
from jarvisx.database.session import get_db
from services.api.admin.src.models.auth import (
    LoginRequest, LoginResponse, RefreshTokenRequest, RefreshTokenResponse,
    UserResponse, ChangePasswordRequest
)
from services.api.admin.src.models.sso import (
    SSOLoginRequest, SSOLoginResponse, SSOCallbackRequest, SAMLResponseRequest
)
from services.api.admin.src.auth import (
    verify_password, create_access_token, create_refresh_token,
    decode_access_token, get_token_expiry, hash_password,
    REFRESH_TOKEN_EXPIRE_DAYS
)
from services.api.admin.src.services.oauth_handler import oauth_handler
from services.api.admin.src.services.saml_handler import saml_handler
from services.api.admin.src.utils.encryption import get_enhanced_encryption_service
from services.api.admin.src.utils.state_storage import get_state_storage
from services.api.admin.src.utils.audit_logger import get_audit_logger
from services.api.admin.src.utils.cookies import (
    set_auth_cookies, clear_auth_cookies, get_access_token_from_request,
    get_refresh_token_from_request, generate_csrf_token, validate_csrf_token
)
from services.api.admin.src.config.sso_settings import get_sso_settings
from services.api.admin.src.permissions import get_user_permissions


def _get_decrypted_client_secret(sso_config: SSOConfig, db: Session) -> str:
    """Decrypt the client secret from SSO config"""
    if not sso_config.client_secret:
        return None
    
    try:
        encryption_service = get_enhanced_encryption_service()
        return encryption_service.decrypt_with_org_key(
            encrypted=sso_config.client_secret,
            organization_id=str(sso_config.organization_id),
            db=db,
            purpose="sso",
            key_version=sso_config.client_secret_key_version,
            key_id=sso_config.client_secret_key_id
        )
    except Exception as e:
        logger.error(f"Failed to decrypt client secret: {e}")
        raise HTTPException(status_code=500, detail="Failed to decrypt SSO credentials")

router = APIRouter(prefix="/api/auth", tags=["auth"])
logger = logging.getLogger(__name__)
audit_logger = get_audit_logger()
settings = get_sso_settings()


@router.post("/login")
def login(credentials: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == credentials.email).first()
    
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User account is disabled")
    
    organization = db.query(Organization).filter(Organization.id == user.organization_id).first()
    if not organization or not organization.is_active:
        raise HTTPException(status_code=403, detail="Organization is not active")
    
    user_is_platform_admin = (
        organization.is_platform_admin and 
        user.effective_role in ("owner", "admin")
    )
    
    access_token = create_access_token(
        data={
            "sub": user.id,
            "email": user.email,
            "organization_id": user.organization_id,
            "role": user.effective_role,
            "is_platform_admin": user_is_platform_admin
        }
    )
    
    refresh_token, token_hash = create_refresh_token()
    expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    db_refresh_token = RefreshToken(
        id=str(uuid.uuid4()),
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at
    )
    db.add(db_refresh_token)
    
    user.last_login_at = datetime.utcnow()
    db.commit()
    
    csrf_token = generate_csrf_token()
    set_auth_cookies(response, access_token, refresh_token, csrf_token)
    
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=get_token_expiry(),
        user=UserResponse(
            id=user.id,
            organization_id=user.organization_id,
            organization_name=organization.name,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            role=user.effective_role,
            is_active=user.is_active,
            is_verified=user.is_verified,
            is_platform_admin=user_is_platform_admin,
            last_login_at=user.last_login_at,
            created_at=user.created_at
        )
    )


@router.post("/refresh")
def refresh_token_endpoint(
    request: Request,
    response: Response,
    body: RefreshTokenRequest = None,
    db: Session = Depends(get_db)
):
    import hashlib
    
    token = None
    if body and body.refresh_token:
        token = body.refresh_token
    else:
        token = get_refresh_token_from_request(request)
    
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token provided")
    
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    
    db_token = db.query(RefreshToken).filter(
        RefreshToken.token_hash == token_hash,
        RefreshToken.is_revoked == False
    ).first()
    
    if not db_token:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    
    if db_token.expires_at < datetime.utcnow():
        db_token.is_revoked = True
        db.commit()
        raise HTTPException(status_code=401, detail="Refresh token expired")
    
    user = db.query(User).filter(User.id == db_token.user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=403, detail="User account is disabled")
    
    organization = db.query(Organization).filter(Organization.id == user.organization_id).first()
    
    user_is_platform_admin = (
        organization and 
        organization.is_platform_admin and 
        user.effective_role in ("owner", "admin")
    )
    
    access_token = create_access_token(
        data={
            "sub": user.id,
            "email": user.email,
            "organization_id": user.organization_id,
            "role": user.effective_role,
            "is_platform_admin": user_is_platform_admin
        }
    )
    
    new_refresh_token, new_token_hash = create_refresh_token()
    db_token.is_revoked = True
    
    new_db_token = RefreshToken(
        id=str(uuid.uuid4()),
        user_id=user.id,
        token_hash=new_token_hash,
        expires_at=datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )
    db.add(new_db_token)
    db.commit()
    
    csrf_token = generate_csrf_token()
    set_auth_cookies(response, access_token, new_refresh_token, csrf_token)
    
    return RefreshTokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=get_token_expiry()
    )


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    body: RefreshTokenRequest = None,
    db: Session = Depends(get_db)
):
    import hashlib
    
    token = None
    if body and body.refresh_token:
        token = body.refresh_token
    else:
        token = get_refresh_token_from_request(request)
    
    if token:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        db_token = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
        if db_token:
            db_token.is_revoked = True
            db.commit()
    
    clear_auth_cookies(response)
    
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
def get_current_user_info(
    request: Request,
    db: Session = Depends(get_db),
    authorization: str = Header(None)
):
    return _get_current_user_from_request(db, request, authorization)


def _get_current_user_from_request(db: Session, request: Request, authorization: str = None) -> UserResponse:
    token = get_access_token_from_request(request)
    
    if not token and authorization and authorization.startswith("Bearer "):
        token = authorization.replace("Bearer ", "")
    
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    payload = decode_access_token(token)
    
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    organization = db.query(Organization).filter(Organization.id == user.organization_id).first()
    
    # Platform admin only for owner/admin users in platform admin org (least privilege)
    user_is_platform_admin = (
        organization and 
        organization.is_platform_admin and 
        user.effective_role in ("owner", "admin")
    )
    
    permissions = get_user_permissions(user.effective_role, user_is_platform_admin)
    
    return UserResponse(
        id=user.id,
        organization_id=user.organization_id,
        organization_name=organization.name if organization else None,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        role=user.effective_role,
        is_active=user.is_active,
        is_verified=user.is_verified,
        is_platform_admin=user_is_platform_admin,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
        permissions=permissions
    )


@router.post("/change-password")
def change_password(
    request: ChangePasswordRequest,
    db: Session = Depends(get_db),
    authorization: str = Header(None)
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.replace("Bearer ", "")
    payload = decode_access_token(token)
    
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not verify_password(request.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    
    user.password_hash = hash_password(request.new_password)
    user.updated_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Password changed successfully"}


# ============================================================================
# SSO AUTHENTICATION ENDPOINTS
# ============================================================================

PROVIDER_LABELS = {
    "google": "Google",
    "microsoft": "Microsoft",
    "okta": "Okta",
    "saml": "SAML 2.0",
}


@router.get("/sso/discover")
def discover_sso_provider(
    email: str = None,
    domain: str = None,
    org_slug: str = None,
    db: Session = Depends(get_db),
):
    """
    Discover SSO provider for an organization

    This endpoint helps identify if an organization has SSO configured
    based on email domain, organization slug, or domain.

    Args:
        email: User email (extracts domain automatically)
        domain: Email domain directly
        org_slug: Organization slug/identifier

    Returns:
        SSO provider information or has_sso: false
    """
    # Extract domain from email
    if email and "@" in email:
        domain = email.split("@")[1].lower()

    # Try to find SSO config by domain
    if domain:
        sso_configs = (
            db.query(SSOConfig)
            .join(Organization, SSOConfig.organization_id == Organization.id)
            .filter(
                SSOConfig.is_enabled == True,
            )
            .all()
        )

        # Check if domain is in allowed_domains
        for sso_config in sso_configs:
            if sso_config.allowed_domains and domain in [d.lower() for d in sso_config.allowed_domains]:
                org = db.query(Organization).filter(Organization.id == sso_config.organization_id).first()
                return {
                    "has_sso": True,
                    "organization_id": sso_config.organization_id,
                    "organization_name": org.name if org else None,
                    "organization_slug": org.slug if org else None,
                    "provider": sso_config.provider,
                    "provider_label": PROVIDER_LABELS.get(sso_config.provider, sso_config.provider),
                }

    # Try to find by organization slug
    if org_slug:
        org = (
            db.query(Organization)
            .filter(Organization.slug == org_slug)
            .first()
        )

        if org:
            sso_config = (
                db.query(SSOConfig)
                .filter(
                    SSOConfig.organization_id == org.id,
                    SSOConfig.is_enabled == True,
                )
                .first()
            )

            if sso_config:
                return {
                    "has_sso": True,
                    "organization_id": org.id,
                    "organization_name": org.name,
                    "organization_slug": org.slug,
                    "provider": sso_config.provider,
                    "provider_label": PROVIDER_LABELS.get(sso_config.provider, sso_config.provider),
                }

    return {"has_sso": False}


@router.post("/sso/initiate", response_model=SSOLoginResponse)
async def initiate_sso_login(
    sso_request: SSOLoginRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Initiate SSO login flow - returns authorization URL
    """
    client_ip = request.client.host if request.client else None

    sso_config = (
        db.query(SSOConfig)
        .filter(
            SSOConfig.organization_id == sso_request.organization_id,
            SSOConfig.provider == sso_request.provider,
            SSOConfig.is_enabled == True,
        )
        .first()
    )

    if not sso_config:
        audit_logger.log_sso_login_failed(
            organization_id=sso_request.organization_id,
            provider=sso_request.provider,
            error_message="SSO configuration not found or disabled",
            ip_address=client_ip,
        )
        raise HTTPException(
            status_code=404,
            detail=f"SSO configuration not found or disabled for provider '{sso_request.provider}'",
        )

    from urllib.parse import urlparse, urlunparse
    
    raw_redirect_uri = sso_request.redirect_uri or f"{settings.api_base_url}/api/auth/sso/callback"
    parsed = urlparse(raw_redirect_uri)
    clean_redirect_uri = urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', ''))
    
    app_type = sso_request.app_type or "admin"

    try:
        if sso_config.provider in ["google", "microsoft", "okta"]:
            decrypted_secret = _get_decrypted_client_secret(sso_config, db)
            authorization_url, state = await oauth_handler.get_authorization_url(
                sso_config, clean_redirect_uri, decrypted_secret
            )
        elif sso_config.provider == "saml":
            state = secrets.token_urlsafe(32)
            acs_url = f"{settings.api_base_url}/api/auth/sso/saml/acs/{sso_config.id}"
            entity_id = sso_config.sp_entity_id or f"jarvisx-sp-{sso_config.organization_id}"

            authorization_url = saml_handler.get_authorization_url(
                sso_config, acs_url, entity_id, relay_state=state
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported SSO provider: {sso_config.provider}")
        
        state_storage = get_state_storage()
        state_storage.set(state, {
            "config_id": sso_config.id,
            "organization_id": sso_config.organization_id,
            "provider": sso_config.provider,
            "redirect_uri": clean_redirect_uri,
            "app_type": app_type,
            "created_at": datetime.utcnow().isoformat(),
        })

        # Audit log
        audit_logger.log_sso_login_initiated(
            organization_id=sso_config.organization_id,
            provider=sso_config.provider,
            ip_address=client_ip,
        )

        return SSOLoginResponse(
            authorization_url=authorization_url,
            state=state,
        )

    except Exception as e:
        logger.error(f"Failed to initiate SSO: {e}")
        audit_logger.log_sso_login_failed(
            organization_id=sso_request.organization_id,
            provider=sso_request.provider,
            error_message=str(e),
            ip_address=client_ip,
        )
        raise HTTPException(status_code=500, detail=f"Failed to initiate SSO: {str(e)}")


@router.get("/sso/callback")
async def handle_oauth_callback(
    code: str,
    state: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Handle OAuth2/OIDC callback
    """
    client_ip = request.client.host if request.client else None

    # Validate state (CSRF protection)
    state_storage = get_state_storage()
    state_data = state_storage.get(state)

    if not state_data:
        audit_logger.log_event(
            event_type="sso.state.invalid",
            ip_address=client_ip,
            success=False,
            error_message="Invalid or expired state parameter",
        )
        raise HTTPException(status_code=400, detail="Invalid or expired state")

    # Remove state (one-time use)
    state_storage.delete(state)

    # Get SSO configuration
    sso_config = db.query(SSOConfig).filter(SSOConfig.id == state_data["config_id"]).first()
    if not sso_config:
        audit_logger.log_sso_login_failed(
            organization_id=state_data.get("organization_id", ""),
            provider=state_data.get("provider", ""),
            error_message="SSO configuration not found",
            ip_address=client_ip,
        )
        raise HTTPException(status_code=404, detail="SSO configuration not found")

    try:
        decrypted_secret = _get_decrypted_client_secret(sso_config, db)
        user_info = await oauth_handler.handle_callback(
            sso_config, code, state_data["redirect_uri"], decrypted_secret
        )

        login_response = _handle_sso_user(db, sso_config, user_info, client_ip)

        app_type = state_data.get("app_type", "admin")
        if app_type == "voice":
            frontend_url = settings.voice_chat_base_url
        else:
            frontend_url = settings.frontend_base_url
        
        csrf_token = generate_csrf_token()
        redirect_response = RedirectResponse(url=f"{frontend_url}/sso/callback?success=true", status_code=302)
        set_auth_cookies(redirect_response, login_response.access_token, login_response.refresh_token, csrf_token)
        
        return redirect_response

    except Exception as e:
        logger.error(f"SSO callback failed: {e}")
        audit_logger.log_sso_login_failed(
            organization_id=sso_config.organization_id,
            provider=sso_config.provider,
            error_message=str(e),
            ip_address=client_ip,
        )
        app_type = state_data.get("app_type", "admin")
        if app_type == "voice":
            frontend_url = settings.voice_chat_base_url
            error_path = settings.sso_error_path_voice
        else:
            frontend_url = settings.frontend_base_url
            error_path = settings.sso_error_path_admin
        error_redirect = f"{frontend_url}{error_path}?error=sso_failed"
        return RedirectResponse(url=error_redirect, status_code=302)


@router.post("/sso/saml/acs/{config_id}")
async def handle_saml_acs(
    config_id: str,
    request: Request,
    db: Session = Depends(get_db),
    SAMLResponse: str = Form(...),
    RelayState: str = Form(None),
):
    """
    Handle SAML Assertion Consumer Service (ACS) callback (SP-initiated)
    """
    client_ip = request.client.host if request.client else None

    # Get SSO configuration
    sso_config = db.query(SSOConfig).filter(SSOConfig.id == config_id).first()
    if not sso_config or sso_config.provider != "saml":
        audit_logger.log_sso_login_failed(
            organization_id="",
            provider="saml",
            error_message="SAML configuration not found",
            ip_address=client_ip,
        )
        raise HTTPException(status_code=404, detail="SAML configuration not found")

    # Build request data for python3-saml
    request_data = {
        "http_host": request.headers.get("host", "localhost"),
        "script_name": request.url.path,
        "server_port": request.url.port or 443,
        "https": "on" if request.url.scheme == "https" else "off",
        "post_data": {"SAMLResponse": SAMLResponse},
    }

    acs_url = str(request.url)
    entity_id = sso_config.sp_entity_id or f"jarvisx-sp-{sso_config.organization_id}"

    try:
        # Process SAML response
        user_info = saml_handler.process_response(
            sso_config, SAMLResponse, acs_url, entity_id, request_data
        )

        # Authenticate or create user
        login_response = _handle_sso_user(db, sso_config, user_info, client_ip)

        # In production, redirect to frontend with tokens
        return login_response

    except Exception as e:
        logger.error(f"SAML authentication failed: {e}")
        audit_logger.log_sso_login_failed(
            organization_id=sso_config.organization_id,
            provider="saml",
            error_message=str(e),
            ip_address=client_ip,
        )
        raise HTTPException(status_code=500, detail=f"SAML authentication failed: {str(e)}")


@router.post("/sso/saml/idp/{org_slug}")
async def handle_idp_initiated_saml(
    org_slug: str,
    request: Request,
    db: Session = Depends(get_db),
    SAMLResponse: str = Form(...),
    RelayState: str = Form(None),
):
    """
    Handle IdP-initiated SAML login

    This endpoint allows SAML Identity Providers to initiate login flows.
    The organization is identified by the slug in the URL path.

    URL Format: /api/auth/sso/saml/idp/{org_slug}
    Example: /api/auth/sso/saml/idp/acme-corp

    Args:
        org_slug: Organization slug (URL-safe identifier)
        SAMLResponse: Base64-encoded SAML response from IdP
        RelayState: Optional relay state from IdP

    Returns:
        Login response with tokens or redirects to frontend
    """
    client_ip = request.client.host if request.client else None

    # Lookup organization by slug
    org = db.query(Organization).filter(Organization.slug == org_slug).first()

    if not org:
        audit_logger.log_sso_login_failed(
            organization_id="",
            provider="saml",
            error_message=f"Organization not found: {org_slug}",
            ip_address=client_ip,
        )
        raise HTTPException(status_code=404, detail=f"Organization not found: {org_slug}")

    # Get SAML configuration for this organization
    sso_config = (
        db.query(SSOConfig)
        .filter(
            SSOConfig.organization_id == org.id,
            SSOConfig.provider == "saml",
            SSOConfig.is_enabled == True,
        )
        .first()
    )

    if not sso_config:
        audit_logger.log_sso_login_failed(
            organization_id=org.id,
            provider="saml",
            error_message="SAML not configured for this organization",
            ip_address=client_ip,
        )
        raise HTTPException(
            status_code=404,
            detail=f"SAML not configured for organization: {org.name}"
        )

    # Build request data for python3-saml
    request_data = {
        "http_host": request.headers.get("host", "localhost"),
        "script_name": request.url.path,
        "server_port": request.url.port or 443,
        "https": "on" if request.url.scheme == "https" else "off",
        "post_data": {"SAMLResponse": SAMLResponse},
    }

    # Use this endpoint as ACS URL for IdP-initiated flow
    acs_url = f"{settings.api_base_url}/api/auth/sso/saml/idp/{org_slug}"
    entity_id = sso_config.sp_entity_id or f"jarvisx-sp-{org.id}"

    try:
        # Process SAML response
        user_info = saml_handler.process_response(
            sso_config, SAMLResponse, acs_url, entity_id, request_data
        )

        # Authenticate or create user
        login_response = _handle_sso_user(db, sso_config, user_info, client_ip)

        # Log successful IdP-initiated login
        logger.info(f"IdP-initiated SAML login successful for {user_info.email} in org {org.name}")

        # In production, you might want to redirect to frontend with tokens
        # For now, return the tokens directly
        # TODO: Consider redirecting to: {FRONTEND_BASE_URL}/auth/callback?token={access_token}
        return login_response

    except Exception as e:
        logger.error(f"IdP-initiated SAML authentication failed: {e}")
        audit_logger.log_sso_login_failed(
            organization_id=org.id,
            provider="saml",
            error_message=f"IdP-initiated: {str(e)}",
            ip_address=client_ip,
        )
        raise HTTPException(
            status_code=500,
            detail=f"SAML authentication failed: {str(e)}"
        )


def _handle_sso_user(db: Session, sso_config: SSOConfig, user_info, client_ip: str = None) -> LoginResponse:
    """
    Handle SSO user authentication or auto-provisioning
    """
    was_provisioned = False

    # Check domain restriction
    if sso_config.allowed_domains:
        user_domain = user_info.email.split("@")[1]
        if user_domain not in sso_config.allowed_domains:
            audit_logger.log_event(
                event_type="sso.domain.rejected",
                organization_id=sso_config.organization_id,
                email=user_info.email,
                provider=sso_config.provider,
                ip_address=client_ip,
                success=False,
                error_message=f"Domain '{user_domain}' is not allowed",
            )
            raise HTTPException(
                status_code=403,
                detail=f"Domain '{user_domain}' is not allowed for SSO",
            )

    # Find existing user
    user = db.query(User).filter(User.email == user_info.email).first()

    if not user:
        was_provisioned = True
        # Auto-provision user if enabled
        if not sso_config.auto_provision_users:
            raise HTTPException(
                status_code=403,
                detail="User does not exist and auto-provisioning is disabled",
            )

        # Create new user
        user = User(
            id=str(uuid.uuid4()),
            organization_id=sso_config.organization_id,
            email=user_info.email,
            password_hash=hash_password(secrets.token_urlsafe(32)),  # Random password (won't be used)
            first_name=user_info.first_name,
            last_name=user_info.last_name,
            is_active=True,
            is_verified=True,  # SSO users are pre-verified
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(user)

        # Add to configured team
        if not sso_config.default_team_id:
            raise HTTPException(
                status_code=400,
                detail="SSO configuration error: No default team configured for auto-provisioned users"
            )
        
        target_team = db.query(Team).filter(
            Team.id == sso_config.default_team_id,
            Team.organization_id == sso_config.organization_id,
            Team.is_active == True,
        ).first()
        
        if not target_team:
            raise HTTPException(
                status_code=400,
                detail="SSO configuration error: Configured default team not found or inactive"
            )

        # Add user to team
        team_member = TeamMember(
            id=str(uuid.uuid4()),
            team_id=target_team.id,
            user_id=user.id,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(team_member)
        db.flush()

    # Check if user belongs to correct organization
    if user.organization_id != sso_config.organization_id:
        raise HTTPException(
            status_code=403,
            detail="User belongs to a different organization",
        )

    if not user.is_active:
        raise HTTPException(status_code=403, detail="User account is disabled")

    # Get organization
    organization = db.query(Organization).filter(Organization.id == user.organization_id).first()
    if not organization or not organization.is_active:
        raise HTTPException(status_code=403, detail="Organization is not active")

    # Determine if user should be platform admin
    # SSO users are NOT platform admins by default (least privilege principle)
    # Only grant platform admin to existing users who already had it before SSO
    # (i.e., users created through seed data or manually)
    user_is_platform_admin = False
    if not was_provisioned:
        # Existing user - check if org is platform admin org AND user has owner role
        # This maintains backward compatibility for existing admins
        user_is_platform_admin = (
            organization.is_platform_admin and 
            user.effective_role in ("owner", "admin")
        )

    # Create access and refresh tokens
    access_token = create_access_token(
        data={
            "sub": user.id,
            "email": user.email,
            "organization_id": user.organization_id,
            "role": user.effective_role,
            "is_platform_admin": user_is_platform_admin,
        }
    )

    refresh_token, token_hash = create_refresh_token()
    expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    db_refresh_token = RefreshToken(
        id=str(uuid.uuid4()),
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
        created_at=datetime.utcnow(),
    )
    db.add(db_refresh_token)

    # Update last login
    user.last_login_at = datetime.utcnow()
    db.commit()
    db.refresh(user)

    # Audit log successful login
    audit_logger.log_sso_login_success(
        user_id=user.id,
        organization_id=user.organization_id,
        email=user.email,
        provider=sso_config.provider,
        was_provisioned=was_provisioned,
        ip_address=client_ip,
    )

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=get_token_expiry(),
        user=UserResponse(
            id=user.id,
            organization_id=user.organization_id,
            organization_name=organization.name,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            role=user.effective_role,
            is_active=user.is_active,
            is_verified=user.is_verified,
            is_platform_admin=user_is_platform_admin,
            last_login_at=user.last_login_at,
            created_at=user.created_at,
        ),
    )


def create_default_user_for_organization(
    db: Session,
    organization_id: str,
    organization_name: str
) -> tuple:
    org_slug = organization_name.lower().replace(' ', '-').replace('_', '-')
    org_slug = ''.join(c for c in org_slug if c.isalnum() or c == '-')
    
    email = f"admin@{org_slug}.org"
    default_password = "admin"
    
    existing_email = db.query(User).filter(User.email == email).first()
    if existing_email:
        email = f"admin-{organization_id[:8]}@{org_slug}.org"
    
    user = User(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        email=email,
        password_hash=hash_password(default_password),
        first_name="Admin",
        last_name="User",
        is_active=True,
        is_verified=True
    )
    db.add(user)
    
    team = Team(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        name="Default Team",
        description="Default team for the organization",
        role="owner",
        is_default=True,
        is_active=True
    )
    db.add(team)
    db.flush()
    
    team_member = TeamMember(
        id=str(uuid.uuid4()),
        team_id=team.id,
        user_id=user.id,
        is_active=True
    )
    db.add(team_member)
    
    return user, email, default_password
