from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from jarvisx.database.models import Workspace, Agent, AgentMCP, MCPServer
from jarvisx.database.session import get_db

router = APIRouter(prefix="/api/workspace-config", tags=["workspace-config"])


@router.get("/{workspace_id}")
def get_workspace_config(workspace_id: str, db: Session = Depends(get_db)):
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    if not workspace.is_active:
        raise HTTPException(status_code=403, detail="Workspace is inactive")
    
    enabled_agents = []
    for aa in workspace.agent_assignments:
        if not aa.is_enabled:
            continue
        
        agent = db.query(Agent).filter(Agent.id == aa.agent_id).first()
        agent_url = agent.default_url if agent else None
        
        enabled_agents.append({
            "agent_id": aa.agent_id,
            "agent_url": agent_url,
            "agent_name": agent.name if agent else aa.agent_id,
            "allowed_delegate_agents": aa.allowed_delegate_agents or [],
            "max_parallel_mcp_runs": aa.max_parallel_mcp_runs
        })
    
    enabled_mcps = []
    agent_ids = [aa.agent_id for aa in workspace.agent_assignments if aa.is_enabled]
    if agent_ids:
        mcp_assignments = db.query(AgentMCP).filter(
            AgentMCP.agent_id.in_(agent_ids),
            AgentMCP.is_enabled == True
        ).all()
        
        mcp_server_ids = {ma.mcp_server_id for ma in mcp_assignments}
        mcp_servers = db.query(MCPServer).filter(
            MCPServer.id.in_(mcp_server_ids)
        ).all()
        mcp_server_map = {mcp.id: mcp for mcp in mcp_servers}
        
        for ma in mcp_assignments:
            mcp_server = mcp_server_map.get(ma.mcp_server_id)
            if mcp_server:
                enabled_mcps.append({
                    "mcp_server_id": ma.mcp_server_id,
                    "mcp_server_name": mcp_server.name,
                    "mcp_config": ma.mcp_config
                })
    
    return {
        "workspace_id": workspace.id,
        "workspace_name": workspace.name,
        "chat_mode": workspace.chat_mode,
        "ui_base_url": workspace.ui_base_url,
        "voice_agent_name": workspace.voice_agent_name,
        "enabled_agents": enabled_agents,
        "enabled_mcp_servers": enabled_mcps,
    }
