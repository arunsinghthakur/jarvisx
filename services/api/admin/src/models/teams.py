from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


class TeamMemberBase(BaseModel):
    user_id: str


class TeamMemberCreate(TeamMemberBase):
    pass


class TeamMemberUpdate(BaseModel):
    is_active: Optional[bool] = None


class TeamMemberResponse(BaseModel):
    id: str
    team_id: str
    user_id: str
    is_active: bool
    created_at: datetime
    user_email: Optional[str] = None
    user_first_name: Optional[str] = None
    user_last_name: Optional[str] = None

    class Config:
        from_attributes = True


class TeamWorkspaceResponse(BaseModel):
    id: str
    team_id: str
    workspace_id: str
    workspace_name: str
    created_at: datetime

    class Config:
        from_attributes = True


class TeamBase(BaseModel):
    name: str
    description: Optional[str] = None
    role: str = "member"


class TeamCreate(TeamBase):
    organization_id: Optional[str] = None
    scope_all_workspaces: bool = True
    workspace_ids: Optional[List[str]] = None


class TeamUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    scope_all_workspaces: Optional[bool] = None
    workspace_ids: Optional[List[str]] = None


class TeamResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    description: Optional[str]
    role: str
    is_default: bool
    is_active: bool
    scope_all_workspaces: bool
    created_at: datetime
    updated_at: datetime
    member_count: int = 0
    organization_name: Optional[str] = None
    scoped_workspace_count: int = 0

    class Config:
        from_attributes = True


class TeamDetailResponse(TeamResponse):
    members: List[TeamMemberResponse] = []
    scoped_workspaces: List[TeamWorkspaceResponse] = []


class UserInvite(BaseModel):
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class UserResponse(BaseModel):
    id: str
    organization_id: str
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    effective_role: str
    is_active: bool
    is_verified: bool
    last_login_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class ResendOTPRequest(BaseModel):
    user_id: str


class VerificationResponse(BaseModel):
    success: bool
    message: str
    user_id: Optional[str] = None
    email: Optional[str] = None
    first_name: Optional[str] = None


class SetPasswordRequest(BaseModel):
    token: str
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    password: str
