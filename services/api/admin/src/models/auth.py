from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
from datetime import datetime


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: "UserResponse"


class RefreshTokenRequest(BaseModel):
    refresh_token: Optional[str] = None


class RefreshTokenResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: str = "member"


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    id: str
    organization_id: str
    organization_name: Optional[str] = None
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    role: str
    is_active: bool
    is_verified: bool
    is_platform_admin: bool = False
    last_login_at: Optional[datetime]
    created_at: datetime
    permissions: Optional[Dict[str, Dict[str, bool]]] = None

    class Config:
        from_attributes = True


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class TeamCreate(BaseModel):
    name: str
    description: Optional[str] = None


class TeamUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class TeamResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    description: Optional[str]
    is_default: bool
    is_active: bool
    member_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class TeamMemberAdd(BaseModel):
    user_id: str
    role: str = "member"


class TeamMemberResponse(BaseModel):
    id: str
    team_id: str
    user_id: str
    role: str
    is_active: bool
    user: Optional[UserResponse] = None
    created_at: datetime

    class Config:
        from_attributes = True


LoginResponse.model_rebuild()
