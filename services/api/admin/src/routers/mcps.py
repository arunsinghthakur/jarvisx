from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List
from datetime import datetime

from jarvisx.database.models import MCPServer, AgentMCP, Agent
from jarvisx.database.session import get_db
from services.api.admin.src.models import MCPServerCreate, MCPServerUpdate
from services.api.admin.src.dependencies import (
    OrganizationContext, get_organization_context, CurrentUser, get_current_user
)
from services.api.admin.src.permissions import Resource, Action
from services.api.admin.src.decorators import require_permission

router = APIRouter(prefix="/api/available/mcps", tags=["mcps"])


@router.get("", response_model=List[dict])
def list_available_mcps(
    db: Session = Depends(get_db),
    org_ctx: OrganizationContext = Depends(get_organization_context)
):
    query = db.query(MCPServer)
    
    if not org_ctx.is_platform_admin:
        query = query.filter(
            or_(
                MCPServer.is_system_server == True,
                MCPServer.owner_organization_id == org_ctx.organization_id,
                MCPServer.owner_organization_id == None
            )
        )
    
    mcps = query.all()
    return [
        {
            "id": m.id,
            "name": m.name,
            "description": m.description,
            "default_config": m.default_config,
            "is_system_server": m.is_system_server,
            "delete_protection": m.delete_protection,
            "owner_organization_id": m.owner_organization_id,
            "can_edit": org_ctx.can_modify_resource(m.owner_organization_id, m.is_system_server),
            "can_delete": not m.delete_protection and org_ctx.can_modify_resource(m.owner_organization_id, m.is_system_server)
        }
        for m in mcps
    ]


@router.post("", response_model=dict)
@require_permission(Resource.MCPS, Action.CREATE)
def create_mcp_server(
    mcp_data: MCPServerCreate, 
    db: Session = Depends(get_db),
    org_ctx: OrganizationContext = Depends(get_organization_context),
    current_user: CurrentUser = Depends(get_current_user)
):
    existing = db.query(MCPServer).filter(MCPServer.id == mcp_data.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="MCP server ID already exists")
    
    owner_org_id = org_ctx.organization_id
    if mcp_data.owner_organization_id:
        if not org_ctx.is_platform_admin and mcp_data.owner_organization_id != org_ctx.organization_id:
            raise HTTPException(status_code=403, detail="Cannot create MCP server for another organization")
        owner_org_id = mcp_data.owner_organization_id
    
    mcp_server = MCPServer(
        id=mcp_data.id,
        name=mcp_data.name,
        description=mcp_data.description,
        default_config=mcp_data.default_config or {},
        is_system_server=False,
        owner_organization_id=owner_org_id
    )
    db.add(mcp_server)
    db.commit()
    db.refresh(mcp_server)
    
    return {
        "id": mcp_server.id,
        "name": mcp_server.name,
        "description": mcp_server.description,
        "default_config": mcp_server.default_config,
        "is_system_server": mcp_server.is_system_server,
        "owner_organization_id": mcp_server.owner_organization_id
    }


@router.put("/{mcp_id}", response_model=dict)
@require_permission(Resource.MCPS, Action.EDIT)
def update_mcp_server(
    mcp_id: str, 
    mcp_data: MCPServerUpdate, 
    db: Session = Depends(get_db),
    org_ctx: OrganizationContext = Depends(get_organization_context),
    current_user: CurrentUser = Depends(get_current_user)
):
    mcp_server = db.query(MCPServer).filter(MCPServer.id == mcp_id).first()
    if not mcp_server:
        raise HTTPException(status_code=404, detail="MCP server not found")
    
    if not org_ctx.can_access_resource(mcp_server.owner_organization_id, mcp_server.is_system_server):
        raise HTTPException(status_code=403, detail="Access denied to this MCP server")
    
    if mcp_server.is_system_server and not org_ctx.is_platform_admin:
        if mcp_data.name is not None or mcp_data.description is not None:
            raise HTTPException(status_code=403, detail="Cannot modify system MCP server name or description")
    
    if not org_ctx.can_modify_resource(mcp_server.owner_organization_id, mcp_server.is_system_server):
        if mcp_data.default_config is not None:
            pass
    
    if mcp_data.name is not None:
        mcp_server.name = mcp_data.name
    if mcp_data.description is not None:
        mcp_server.description = mcp_data.description
    if mcp_data.default_config is not None:
        mcp_server.default_config = mcp_data.default_config
    
    mcp_server.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(mcp_server)
    
    return {
        "id": mcp_server.id,
        "name": mcp_server.name,
        "description": mcp_server.description,
        "default_config": mcp_server.default_config,
        "is_system_server": mcp_server.is_system_server,
        "owner_organization_id": mcp_server.owner_organization_id
    }


@router.delete("/{mcp_id}")
@require_permission(Resource.MCPS, Action.DELETE)
def delete_mcp_server(
    mcp_id: str, 
    db: Session = Depends(get_db),
    org_ctx: OrganizationContext = Depends(get_organization_context),
    current_user: CurrentUser = Depends(get_current_user)
):
    mcp_server = db.query(MCPServer).filter(MCPServer.id == mcp_id).first()
    if not mcp_server:
        raise HTTPException(status_code=404, detail="MCP server not found")
    
    if not org_ctx.can_modify_resource(mcp_server.owner_organization_id, mcp_server.is_system_server):
        raise HTTPException(status_code=403, detail="Access denied to delete this MCP server")
    
    if mcp_server.delete_protection:
        raise HTTPException(status_code=400, detail="This MCP server is protected and cannot be deleted")
    
    if mcp_server.is_system_server and not org_ctx.is_platform_admin:
        raise HTTPException(status_code=403, detail="Only platform administrators can delete system MCP servers")
    
    db.delete(mcp_server)
    db.commit()
    return {"message": "MCP server deleted successfully"}


@router.get("/{mcp_id}/agents", response_model=List[dict])
def get_mcp_agents(
    mcp_id: str, 
    db: Session = Depends(get_db),
    org_ctx: OrganizationContext = Depends(get_organization_context)
):
    mcp_server = db.query(MCPServer).filter(MCPServer.id == mcp_id).first()
    if not mcp_server:
        raise HTTPException(status_code=404, detail="MCP server not found")
    
    if not org_ctx.can_access_resource(mcp_server.owner_organization_id, mcp_server.is_system_server):
        raise HTTPException(status_code=403, detail="Access denied to this MCP server")
    
    mcp_assignments = db.query(AgentMCP).filter(
        AgentMCP.mcp_server_id == mcp_id,
        AgentMCP.is_enabled == True
    ).all()
    
    agent_ids = [ma.agent_id for ma in mcp_assignments]
    if not agent_ids:
        return []
    
    agents = db.query(Agent).filter(Agent.id.in_(agent_ids)).all()
    agent_map = {agent.id: agent for agent in agents}
    
    result = []
    for ma in mcp_assignments:
        agent = agent_map.get(ma.agent_id)
        if agent:
            result.append({
                "id": agent.id,
                "name": agent.name,
                "description": agent.description,
                "default_url": agent.default_url,
                "is_system_agent": agent.is_system_agent,
                "is_custom_agent": not agent.is_system_agent,
                "mcp_config": ma.mcp_config,
                "is_enabled": ma.is_enabled
            })
    
    return result
