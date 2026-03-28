from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List
from datetime import datetime
import httpx
import uuid

from jarvisx.database.models import Agent, AgentMCP, MCPServer, OrganizationLLMConfig
from jarvisx.database.session import get_db
from jarvisx.config.agent_hierarchy import get_hierarchy_for_frontend
from services.api.admin.src.models import AgentCreate, AgentUpdate
from services.api.admin.src.dependencies import (
    OrganizationContext, get_organization_context, CurrentUser, get_current_user
)
from services.api.admin.src.permissions import Resource, Action
from services.api.admin.src.decorators import require_permission

router = APIRouter(prefix="/api/available/agents", tags=["agents"])


@router.get("/hierarchy/definitions")
def get_agent_hierarchy_definitions(
    org_ctx: OrganizationContext = Depends(get_organization_context)
):
    return get_hierarchy_for_frontend(organization_id=org_ctx.organization_id)


@router.get("", response_model=List[dict])
def list_available_agents(
    db: Session = Depends(get_db),
    org_ctx: OrganizationContext = Depends(get_organization_context)
):
    query = db.query(Agent).filter(Agent.id != "jarvisx")
    
    if not org_ctx.is_platform_admin:
        query = query.filter(
            or_(
                Agent.is_system_agent == True,
                Agent.owner_organization_id == org_ctx.organization_id,
                Agent.owner_organization_id == None
            )
        )
    
    agents = query.all()
    result = []
    for a in agents:
        llm_config = None
        if a.llm_config_id:
            config = db.query(OrganizationLLMConfig).filter(OrganizationLLMConfig.id == a.llm_config_id).first()
            if config:
                llm_config = {
                    "id": config.id,
                    "name": config.name,
                    "provider": config.provider,
                    "model_name": config.model_name,
                }
        
        result.append({
            "id": a.id,
            "name": a.name,
            "description": a.description,
            "default_url": a.default_url,
            "health_endpoint": a.health_endpoint,
            "is_system_agent": a.is_system_agent,
            "is_custom_agent": not a.is_system_agent,
            "is_dynamic_agent": a.is_dynamic_agent,
            "system_prompt": a.system_prompt,
            "llm_config_id": a.llm_config_id,
            "llm_config": llm_config,
            "delete_protection": a.delete_protection,
            "owner_organization_id": a.owner_organization_id,
            "can_edit": org_ctx.can_modify_resource(a.owner_organization_id, a.is_system_agent),
            "can_delete": not a.delete_protection and org_ctx.can_modify_resource(a.owner_organization_id, a.is_system_agent)
        })
    return result


@router.post("", response_model=dict)
@require_permission(Resource.AGENTS, Action.CREATE)
def create_custom_agent(
    agent_data: AgentCreate, 
    db: Session = Depends(get_db),
    org_ctx: OrganizationContext = Depends(get_organization_context),
    current_user: CurrentUser = Depends(get_current_user)
):
    existing = db.query(Agent).filter(Agent.id == agent_data.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Agent ID already exists")
    
    if agent_data.is_dynamic_agent:
        if not agent_data.system_prompt:
            raise HTTPException(status_code=400, detail="Dynamic agents require a system prompt")
        if not agent_data.llm_config_id:
            raise HTTPException(status_code=400, detail="Dynamic agents require an LLM configuration")
        
        llm_config = db.query(OrganizationLLMConfig).filter(
            OrganizationLLMConfig.id == agent_data.llm_config_id,
            OrganizationLLMConfig.organization_id == org_ctx.organization_id
        ).first()
        if not llm_config:
            raise HTTPException(status_code=400, detail="LLM configuration not found or does not belong to your organization")
    else:
        if not agent_data.default_url:
            raise HTTPException(status_code=400, detail="External agents require a default_url")
        if not agent_data.default_url.startswith(("http://", "https://")):
            raise HTTPException(status_code=400, detail="Agent URL must start with http:// or https://")
    
    owner_org_id = org_ctx.organization_id
    if agent_data.owner_organization_id:
        if not org_ctx.is_platform_admin and agent_data.owner_organization_id != org_ctx.organization_id:
            raise HTTPException(status_code=403, detail="Cannot create agent for another organization")
        owner_org_id = agent_data.owner_organization_id
    
    agent = Agent(
        id=agent_data.id,
        name=agent_data.name,
        description=agent_data.description,
        default_url=agent_data.default_url,
        health_endpoint=agent_data.health_endpoint,
        is_system_agent=False,
        is_dynamic_agent=agent_data.is_dynamic_agent,
        system_prompt=agent_data.system_prompt,
        llm_config_id=agent_data.llm_config_id if agent_data.is_dynamic_agent else None,
        owner_organization_id=owner_org_id,
        created_by=org_ctx.organization.name
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    
    if agent_data.mcp_server_ids:
        for mcp_id in agent_data.mcp_server_ids:
            mcp_server = db.query(MCPServer).filter(MCPServer.id == mcp_id).first()
            if mcp_server:
                agent_mcp = AgentMCP(
                    id=str(uuid.uuid4()),
                    agent_id=agent.id,
                    mcp_server_id=mcp_id,
                    is_enabled=True
                )
                db.add(agent_mcp)
        db.commit()
    
    llm_config = None
    if agent.llm_config_id:
        config = db.query(OrganizationLLMConfig).filter(OrganizationLLMConfig.id == agent.llm_config_id).first()
        if config:
            llm_config = {
                "id": config.id,
                "name": config.name,
                "provider": config.provider,
                "model_name": config.model_name,
            }
    
    return {
        "id": agent.id,
        "name": agent.name,
        "description": agent.description,
        "default_url": agent.default_url,
        "health_endpoint": agent.health_endpoint,
        "is_system_agent": agent.is_system_agent,
        "is_custom_agent": not agent.is_system_agent,
        "is_dynamic_agent": agent.is_dynamic_agent,
        "system_prompt": agent.system_prompt,
        "llm_config_id": agent.llm_config_id,
        "llm_config": llm_config,
        "owner_organization_id": agent.owner_organization_id
    }


@router.put("/{agent_id}", response_model=dict)
@require_permission(Resource.AGENTS, Action.EDIT)
def update_agent(
    agent_id: str, 
    agent_data: AgentUpdate, 
    db: Session = Depends(get_db),
    org_ctx: OrganizationContext = Depends(get_organization_context),
    current_user: CurrentUser = Depends(get_current_user)
):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    if not org_ctx.can_access_resource(agent.owner_organization_id, agent.is_system_agent):
        raise HTTPException(status_code=403, detail="Access denied to this agent")
    
    if agent.is_system_agent and not org_ctx.is_platform_admin:
        if agent_data.name is not None or agent_data.description is not None:
            raise HTTPException(status_code=403, detail="Cannot modify system agent name or description")
    
    if not org_ctx.can_modify_resource(agent.owner_organization_id, agent.is_system_agent):
        if agent_data.default_url is not None and agent_data.default_url != agent.default_url:
            raise HTTPException(status_code=403, detail="Cannot modify this agent's URL")
    
    if agent_data.name is not None:
        agent.name = agent_data.name
    if agent_data.description is not None:
        agent.description = agent_data.description
    if agent_data.default_url is not None:
        if agent_data.default_url and not agent_data.default_url.startswith(("http://", "https://")):
            raise HTTPException(status_code=400, detail="Agent URL must start with http:// or https://")
        agent.default_url = agent_data.default_url
    if agent_data.health_endpoint is not None:
        if agent_data.health_endpoint and not agent_data.health_endpoint.startswith(("http://", "https://", "/")):
            raise HTTPException(status_code=400, detail="Health endpoint must be a URL or path starting with /")
        agent.health_endpoint = agent_data.health_endpoint
    
    if agent_data.system_prompt is not None:
        agent.system_prompt = agent_data.system_prompt
    
    if agent_data.llm_config_id is not None:
        if agent_data.llm_config_id:
            llm_config = db.query(OrganizationLLMConfig).filter(
                OrganizationLLMConfig.id == agent_data.llm_config_id,
                OrganizationLLMConfig.organization_id == org_ctx.organization_id
            ).first()
            if not llm_config:
                raise HTTPException(status_code=400, detail="LLM configuration not found or does not belong to your organization")
        agent.llm_config_id = agent_data.llm_config_id
    
    if agent_data.mcp_server_ids is not None:
        db.query(AgentMCP).filter(AgentMCP.agent_id == agent_id).delete()
        for mcp_id in agent_data.mcp_server_ids:
            mcp_server = db.query(MCPServer).filter(MCPServer.id == mcp_id).first()
            if mcp_server:
                agent_mcp = AgentMCP(
                    id=str(uuid.uuid4()),
                    agent_id=agent.id,
                    mcp_server_id=mcp_id,
                    is_enabled=True
                )
                db.add(agent_mcp)
    
    agent.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(agent)
    
    llm_config = None
    if agent.llm_config_id:
        config = db.query(OrganizationLLMConfig).filter(OrganizationLLMConfig.id == agent.llm_config_id).first()
        if config:
            llm_config = {
                "id": config.id,
                "name": config.name,
                "provider": config.provider,
                "model_name": config.model_name,
            }
    
    return {
        "id": agent.id,
        "name": agent.name,
        "description": agent.description,
        "default_url": agent.default_url,
        "health_endpoint": agent.health_endpoint,
        "is_system_agent": agent.is_system_agent,
        "is_custom_agent": not agent.is_system_agent,
        "is_dynamic_agent": agent.is_dynamic_agent,
        "system_prompt": agent.system_prompt,
        "llm_config_id": agent.llm_config_id,
        "llm_config": llm_config,
        "owner_organization_id": agent.owner_organization_id
    }


@router.delete("/{agent_id}")
@require_permission(Resource.AGENTS, Action.DELETE)
def delete_agent(
    agent_id: str, 
    db: Session = Depends(get_db),
    org_ctx: OrganizationContext = Depends(get_organization_context),
    current_user: CurrentUser = Depends(get_current_user)
):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    if not org_ctx.can_modify_resource(agent.owner_organization_id, agent.is_system_agent):
        raise HTTPException(status_code=403, detail="Access denied to delete this agent")
    
    if agent.delete_protection:
        raise HTTPException(status_code=400, detail="This agent is protected and cannot be deleted")
    
    if agent.is_system_agent and not org_ctx.is_platform_admin:
        raise HTTPException(status_code=403, detail="Only platform administrators can delete system agents")
    
    db.delete(agent)
    db.commit()
    return {"message": "Agent deleted successfully"}


@router.get("/{agent_id}/mcps", response_model=List[dict])
def get_agent_mcps(
    agent_id: str, 
    db: Session = Depends(get_db),
    org_ctx: OrganizationContext = Depends(get_organization_context)
):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    if not org_ctx.can_access_resource(agent.owner_organization_id, agent.is_system_agent):
        raise HTTPException(status_code=403, detail="Access denied to this agent")
    
    mcp_assignments = db.query(AgentMCP).filter(
        AgentMCP.agent_id == agent_id,
        AgentMCP.is_enabled == True
    ).all()
    
    mcp_server_ids = [ma.mcp_server_id for ma in mcp_assignments]
    if not mcp_server_ids:
        return []
    
    mcp_servers = db.query(MCPServer).filter(MCPServer.id.in_(mcp_server_ids)).all()
    mcp_server_map = {mcp.id: mcp for mcp in mcp_servers}
    
    result = []
    for ma in mcp_assignments:
        mcp_server = mcp_server_map.get(ma.mcp_server_id)
        if mcp_server:
            result.append({
                "id": mcp_server.id,
                "name": mcp_server.name,
                "description": mcp_server.description,
                "default_config": mcp_server.default_config,
                "is_system_server": mcp_server.is_system_server,
                "delete_protection": mcp_server.delete_protection,
                "mcp_config": ma.mcp_config,
                "is_enabled": ma.is_enabled
            })
    
    return result


@router.get("/{agent_id}/health")
async def check_agent_health(
    agent_id: str, 
    db: Session = Depends(get_db),
    org_ctx: OrganizationContext = Depends(get_organization_context)
):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    if not org_ctx.can_access_resource(agent.owner_organization_id, agent.is_system_agent):
        raise HTTPException(status_code=403, detail="Access denied to this agent")
    
    if agent.is_dynamic_agent:
        return {"status": "dynamic", "message": "Dynamic agent runs in-process with orchestrator"}
    
    if not agent.default_url:
        return {"status": "unknown", "error": "No URL configured"}
    
    base_url = agent.default_url.rstrip('/')
    if agent.health_endpoint:
        if agent.health_endpoint.startswith('http://') or agent.health_endpoint.startswith('https://'):
            health_url = agent.health_endpoint
        else:
            health_url = f"{base_url}{'' if agent.health_endpoint.startswith('/') else '/'}{agent.health_endpoint}"
    else:
        health_url = f"{base_url}/health"
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(health_url)
            return {"status": "online", "data": response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text}
    except httpx.ConnectError:
        return {"status": "offline", "error": "Connection refused"}
    except httpx.TimeoutException:
        return {"status": "offline", "error": "Request timed out"}
    except Exception as e:
        return {"status": "offline", "error": str(e)}


@router.get("/health/all")
async def check_all_agents_health(
    db: Session = Depends(get_db),
    org_ctx: OrganizationContext = Depends(get_organization_context)
):
    query = db.query(Agent).filter(Agent.id != "jarvisx")
    
    if not org_ctx.is_platform_admin:
        query = query.filter(
            or_(
                Agent.is_system_agent == True,
                Agent.owner_organization_id == org_ctx.organization_id,
                Agent.owner_organization_id == None
            )
        )
    
    agents = query.all()
    results = {}
    
    async with httpx.AsyncClient(timeout=5.0) as client:
        for agent in agents:
            if agent.is_dynamic_agent:
                results[agent.id] = {
                    "name": agent.name,
                    "url": None,
                    "status": "dynamic",
                    "message": "Dynamic agent runs in-process with orchestrator"
                }
                continue
            
            if not agent.default_url:
                if agent.is_system_agent:
                    results[agent.id] = {
                        "name": agent.name,
                        "url": None,
                        "status": "in-process",
                        "message": "System agent runs in-process with orchestrator"
                    }
                else:
                    results[agent.id] = {
                        "name": agent.name,
                        "url": None,
                        "status": "unknown",
                        "error": "No URL configured"
                    }
                continue
            
            base_url = agent.default_url.rstrip('/')
            if agent.health_endpoint:
                if agent.health_endpoint.startswith('http://') or agent.health_endpoint.startswith('https://'):
                    health_url = agent.health_endpoint
                else:
                    health_url = f"{base_url}{'' if agent.health_endpoint.startswith('/') else '/'}{agent.health_endpoint}"
            else:
                health_url = f"{base_url}/health"
            
            try:
                response = await client.get(health_url)
                results[agent.id] = {
                    "name": agent.name,
                    "url": agent.default_url,
                    "status": "online",
                    "data": response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
                }
            except httpx.ConnectError:
                results[agent.id] = {
                    "name": agent.name,
                    "url": agent.default_url,
                    "status": "offline",
                    "error": "Connection refused"
                }
            except httpx.TimeoutException:
                results[agent.id] = {
                    "name": agent.name,
                    "url": agent.default_url,
                    "status": "offline",
                    "error": "Request timed out"
                }
            except Exception as e:
                results[agent.id] = {
                    "name": agent.name,
                    "url": agent.default_url,
                    "status": "offline",
                    "error": str(e)
                }
    
    return results
