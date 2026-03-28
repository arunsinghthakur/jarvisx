from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class IntegrationType(str, Enum):
    EMAIL = "email"
    SLACK = "slack"
    TEAMS = "teams"


class EmailConfigCreate(BaseModel):
    smtp_host: str = Field(..., min_length=1)
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    from_email: str = Field(..., min_length=1)
    from_name: str = Field(default="JarvisX")
    use_tls: bool = True


class EmailConfigUpdate(BaseModel):
    smtp_host: Optional[str] = Field(None, min_length=1)
    smtp_port: Optional[int] = Field(None, ge=1, le=65535)
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    from_email: Optional[str] = Field(None, min_length=1)
    from_name: Optional[str] = None
    use_tls: Optional[bool] = None


class SlackConfigCreate(BaseModel):
    webhook_url: str = Field(..., min_length=1)
    default_channel: Optional[str] = None
    bot_name: Optional[str] = None


class SlackConfigUpdate(BaseModel):
    webhook_url: Optional[str] = Field(None, min_length=1)
    default_channel: Optional[str] = None
    bot_name: Optional[str] = None


class TeamsConfigCreate(BaseModel):
    webhook_url: str = Field(..., min_length=1)
    card_theme_color: Optional[str] = Field(default="6366f1")


class TeamsConfigUpdate(BaseModel):
    webhook_url: Optional[str] = Field(None, min_length=1)
    card_theme_color: Optional[str] = None


class IntegrationBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    integration_type: IntegrationType
    is_default: bool = False
    is_active: bool = True


class IntegrationCreate(IntegrationBase):
    config: Dict[str, Any] = Field(default_factory=dict)


class IntegrationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None
    config: Optional[Dict[str, Any]] = None


class IntegrationResponse(BaseModel):
    id: str
    organization_id: str
    integration_type: str
    name: str
    config: Dict[str, Any]
    has_sensitive_config: bool
    is_default: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class IntegrationListResponse(BaseModel):
    integrations: List[IntegrationResponse]
    total: int


class IntegrationTypeInfo(BaseModel):
    id: str
    name: str
    description: str
    config_fields: List[Dict[str, Any]]


class IntegrationTypesResponse(BaseModel):
    types: List[IntegrationTypeInfo]
