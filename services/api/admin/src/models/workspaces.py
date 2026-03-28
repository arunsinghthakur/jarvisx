from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from jarvisx.database.models import ChatMode


class WorkspaceCreate(BaseModel):
    organization_id: str
    name: str
    description: Optional[str] = None
    chat_mode: ChatMode = ChatMode.BOTH
    ui_base_url: Optional[str] = None
    voice_agent_name: str


class WorkspaceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    chat_mode: Optional[ChatMode] = None
    ui_base_url: Optional[str] = None
    voice_agent_name: Optional[str] = None


class WorkspaceResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    description: Optional[str]
    is_active: bool
    is_system_workspace: bool
    delete_protection: bool
    chat_mode: ChatMode
    ui_base_url: Optional[str]
    voice_agent_name: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
