from pydantic import BaseModel
from typing import Optional


class MCPServerCreate(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    default_config: Optional[dict] = None
    owner_organization_id: Optional[str] = None


class MCPServerUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    default_config: Optional[dict] = None

