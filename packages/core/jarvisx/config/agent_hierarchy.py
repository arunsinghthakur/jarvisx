from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class AgentDefinition:
    code: str
    name: str
    description: str
    is_system_agent: bool = True


def get_agents_from_database() -> List[AgentDefinition]:
    from jarvisx.database.session import SessionLocal
    from jarvisx.database.models import Agent
    
    db = SessionLocal()
    try:
        agents = db.query(Agent).filter(Agent.id != "jarvisx").all()
        
        return [
            AgentDefinition(
                code=agent.id,
                name=agent.name,
                description=agent.description or "",
                is_system_agent=agent.is_system_agent
            )
            for agent in agents
        ]
    finally:
        db.close()


def get_agents_for_organization(organization_id: str) -> List[AgentDefinition]:
    from jarvisx.database.session import SessionLocal
    from jarvisx.database.models import Agent
    from sqlalchemy import or_
    
    db = SessionLocal()
    try:
        agents = db.query(Agent).filter(
            Agent.id != "jarvisx",
            or_(
                Agent.is_system_agent == True,
                Agent.owner_organization_id == organization_id,
                Agent.owner_organization_id == None
            )
        ).all()
        
        return [
            AgentDefinition(
                code=agent.id,
                name=agent.name,
                description=agent.description or "",
                is_system_agent=agent.is_system_agent
            )
            for agent in agents
        ]
    finally:
        db.close()


def get_hierarchy_for_frontend(organization_id: Optional[str] = None) -> List[dict]:
    if organization_id:
        agents = get_agents_for_organization(organization_id)
    else:
        agents = get_agents_from_database()
    
    all_agent_codes = [a.code for a in agents]
    
    result = []
    for agent in agents:
        if agent.code in ["orchestrator", "voice"]:
            continue
        
        possible_sub_agents = [
            code for code in all_agent_codes 
            if code != agent.code and code not in ["orchestrator", "voice"]
        ]
        
        result.append({
            "code": agent.code,
            "name": agent.name,
            "description": agent.description,
            "is_system_agent": agent.is_system_agent,
            "possible_sub_agents": possible_sub_agents,
            "can_have_sub_agents": True
        })
    
    return result


def get_root_agents_for_orchestrator(organization_id: Optional[str] = None) -> List[str]:
    if organization_id:
        agents = get_agents_for_organization(organization_id)
    else:
        agents = get_agents_from_database()
    
    return [
        a.code for a in agents 
        if a.code not in ["orchestrator", "voice"]
    ]


__all__ = [
    "AgentDefinition",
    "get_agents_from_database",
    "get_agents_for_organization",
    "get_hierarchy_for_frontend",
    "get_root_agents_for_orchestrator",
]
