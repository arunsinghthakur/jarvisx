from pydantic import BaseModel
from typing import Optional, List


class AgentCreate(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    default_url: Optional[str] = None
    health_endpoint: Optional[str] = None
    is_custom_agent: bool = True
    is_dynamic_agent: bool = False
    system_prompt: Optional[str] = None
    llm_config_id: Optional[str] = None
    mcp_server_ids: Optional[List[str]] = None
    owner_organization_id: Optional[str] = None


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    default_url: Optional[str] = None
    health_endpoint: Optional[str] = None
    system_prompt: Optional[str] = None
    llm_config_id: Optional[str] = None
    mcp_server_ids: Optional[List[str]] = None
