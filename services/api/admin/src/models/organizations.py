from pydantic import BaseModel, Field
from typing import List, Optional, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from services.api.admin.src.models.workspaces import WorkspaceResponse


class OrganizationCreate(BaseModel):
    name: str
    description: Optional[str] = None


class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class OrganizationResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    is_active: bool
    is_platform_admin: bool = False
    delete_protection: bool
    created_at: datetime
    updated_at: datetime
    workspaces: List["WorkspaceResponse"] = Field(default_factory=list)

    class Config:
        from_attributes = True

