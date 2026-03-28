from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class MCPAssignmentCreate(BaseModel):
    mcp_server_name: str
    is_enabled: bool = True
    mcp_config: Optional[dict] = None


class MCPAssignmentResponse(BaseModel):
    id: str
    workspace_id: str
    mcp_server_name: str
    is_enabled: bool
    mcp_config: Optional[dict]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

