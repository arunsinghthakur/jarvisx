from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Literal
from datetime import datetime


# SSO Provider Types
SSOProviderType = Literal["google", "microsoft", "okta", "saml"]


class SSOConfigBase(BaseModel):
    provider: SSOProviderType
    is_enabled: bool = True

    # OAuth2/OIDC fields
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    tenant_id: Optional[str] = None  # For Azure AD/Microsoft

    # SAML fields
    idp_entity_id: Optional[str] = None
    idp_sso_url: Optional[str] = None
    idp_x509_cert: Optional[str] = None
    sp_entity_id: Optional[str] = None

    # Provider-specific configuration
    provider_config: Optional[Dict] = Field(default_factory=dict)

    # Settings
    allowed_domains: Optional[List[str]] = Field(default_factory=list)
    auto_provision_users: bool = True
    default_team_id: Optional[str] = None


class SSOConfigCreate(SSOConfigBase):
    """Create SSO configuration"""
    pass


class SSOConfigUpdate(BaseModel):
    """Update SSO configuration - all fields optional"""
    is_enabled: Optional[bool] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    tenant_id: Optional[str] = None
    idp_entity_id: Optional[str] = None
    idp_sso_url: Optional[str] = None
    idp_x509_cert: Optional[str] = None
    sp_entity_id: Optional[str] = None
    provider_config: Optional[Dict] = None
    allowed_domains: Optional[List[str]] = None
    auto_provision_users: Optional[bool] = None
    default_team_id: Optional[str] = None


class SSOConfigResponse(SSOConfigBase):
    """SSO configuration response - excludes sensitive data by default"""
    id: str
    organization_id: str
    client_secret: Optional[str] = Field(None, exclude=True)  # Never return secret
    default_team_id: Optional[str] = None
    default_team_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SSOConfigResponseWithSecret(SSOConfigResponse):
    """SSO configuration response with secret (for admin use only)"""
    client_secret: Optional[str] = None  # Include secret when explicitly requested

    class Config:
        from_attributes = True


class SSOLoginRequest(BaseModel):
    """Request to initiate SSO login"""
    organization_id: str
    provider: SSOProviderType
    redirect_uri: Optional[str] = None
    app_type: Optional[str] = "admin"


class SSOLoginResponse(BaseModel):
    """Response with SSO authorization URL"""
    authorization_url: str
    state: str  # CSRF protection token


class SSOCallbackRequest(BaseModel):
    """OAuth2 callback data"""
    code: str
    state: str
    redirect_uri: Optional[str] = None


class SAMLResponseRequest(BaseModel):
    """SAML response data"""
    SAMLResponse: str
    RelayState: Optional[str] = None


class SSOUserInfo(BaseModel):
    """User information from SSO provider"""
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    provider: SSOProviderType
    provider_user_id: str
    raw_claims: Optional[Dict] = None


class SSOMetadataResponse(BaseModel):
    """SAML Service Provider metadata"""
    metadata_xml: str
    entity_id: str
    acs_url: str
