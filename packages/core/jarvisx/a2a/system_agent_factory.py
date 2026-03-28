import logging
from typing import List, Optional, Dict, Any

from google.adk.agents.base_agent import BaseAgent

from jarvisx.config.constants import SystemAgentCodes
from jarvisx.a2a.llm_config import LLMConfigNotFoundError
from jarvisx.mcp.toolset_loader import load_mcp_toolsets
from jarvisx.common.id_utils import agent_uuid
from jarvisx.tracing.litellm_integration import setup_litellm_langfuse_callback

logger = logging.getLogger(__name__)

setup_litellm_langfuse_callback()


async def _load_agent_mcp_tools(agent_code: str) -> list:
    from jarvisx.database.session import SessionLocal
    from jarvisx.database.models import Agent, AgentMCP, MCPServer
    
    agent_id = agent_uuid(agent_code)
    
    db = SessionLocal()
    try:
        agent = db.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            return []
        
        mcp_assignments = db.query(AgentMCP).filter(
            AgentMCP.agent_id == agent_id,
            AgentMCP.is_enabled == True
        ).all()
        
        if not mcp_assignments:
            return []
        
        mcp_server_ids = tuple(m.mcp_server_id for m in mcp_assignments)
        
        mcp_servers = db.query(MCPServer).filter(MCPServer.id.in_(mcp_server_ids)).all()
        mcp_names = [s.name for s in mcp_servers]
        
        logger.info("[AGENT FACTORY] Loading MCP tools for %s: %s", agent_code, mcp_names)
        
        toolsets = await load_mcp_toolsets(mcp_server_ids)
        return toolsets
    except Exception as e:
        logger.error("[AGENT FACTORY] Failed to load MCP tools for %s: %s", agent_code, e)
        return []
    finally:
        db.close()


def _get_agent_creators():
    from services.agents.developer.src.agent import create_developer_agent
    from services.agents.browser.src.agent import create_browser_agent
    from services.agents.researcher.src.agent import create_researcher_agent
    from services.agents.knowledge.src.agent import create_knowledge_agent
    from services.agents.pii_guardian.src.agent import create_pii_guardian_agent
    from services.agents.audit.src.agent import create_audit_agent
    from services.agents.policy.src.agent import create_policy_agent
    from services.agents.governance.src.agent import create_governance_agent
    
    return {
        SystemAgentCodes.DEVELOPER: ("Developer", create_developer_agent),
        SystemAgentCodes.BROWSER: ("Browser", create_browser_agent),
        SystemAgentCodes.RESEARCHER: ("Researcher", create_researcher_agent),
        SystemAgentCodes.KNOWLEDGE: ("Knowledge", create_knowledge_agent),
        SystemAgentCodes.PII_GUARDIAN: ("PII Guardian", create_pii_guardian_agent),
        SystemAgentCodes.AUDIT: ("Audit", create_audit_agent),
        SystemAgentCodes.POLICY: ("Policy", create_policy_agent),
        SystemAgentCodes.GOVERNANCE: ("Governance", create_governance_agent),
    }


async def load_system_agents(organization_id: str) -> List[BaseAgent]:
    if not organization_id:
        raise ValueError("organization_id is required to load system agents")
    
    logger.info("[AGENT FACTORY] load_system_agents() for org: %s", organization_id)
    
    agents: List[BaseAgent] = []
    agent_creators = _get_agent_creators()
    
    for agent_code, (agent_name, create_func) in agent_creators.items():
        try:
            agent = create_func(organization_id=organization_id)
            agents.append(agent)
            logger.info("[AGENT FACTORY] Created lazy agent: %s (NO LLM yet)", agent_name)
        except LLMConfigNotFoundError as e:
            logger.warning("[AGENT FACTORY] Skipping %s agent - no LLM config: %s", agent_name, e)
            raise
        except Exception as e:
            logger.error("[AGENT FACTORY] Failed to create %s agent: %s", agent_name, e)
    
    logger.info("[AGENT FACTORY] Created %d lazy agents (NO LLM initialized)", len(agents))
    return agents


async def load_selected_agents(
    organization_id: str, 
    agent_codes: Optional[List[str]] = None,
    workflow_id: Optional[str] = None,
    agent_hierarchy: Optional[Dict[str, Any]] = None
) -> List[BaseAgent]:
    logger.info("=" * 60)
    logger.info("[AGENT FACTORY] load_selected_agents() called")
    logger.info("[AGENT FACTORY] Organization ID: %s", organization_id)
    logger.info("[AGENT FACTORY] Workflow ID: %s", workflow_id)
    logger.info("[AGENT FACTORY] Requested agent codes: %s", agent_codes)
    logger.info("[AGENT FACTORY] Agent hierarchy provided: %s", agent_hierarchy is not None)
    logger.info("=" * 60)
    
    if not organization_id:
        raise ValueError("organization_id is required to load agents")
    
    if not agent_codes:
        logger.info("[AGENT FACTORY] No agent codes specified, returning empty list")
        return []
    
    agents: List[BaseAgent] = []
    agent_creators = _get_agent_creators()
    available_codes = list(agent_creators.keys())
    logger.info("[AGENT FACTORY] Available agent codes: %s", available_codes)
    
    for agent_code in agent_codes:
        logger.info("[AGENT FACTORY] Processing agent code: %s", agent_code)
        if agent_code not in agent_creators:
            logger.warning("[AGENT FACTORY] Unknown agent code: %s, skipping (available: %s)", 
                          agent_code, available_codes)
            continue
        
        agent_name, create_func = agent_creators[agent_code]
        logger.info("[AGENT FACTORY] Creating lazy agent: %s (code: %s)", agent_name, agent_code)
        
        mcp_tools = await _load_agent_mcp_tools(agent_code)
        
        sub_agent_config = None
        if agent_hierarchy and agent_code in agent_hierarchy:
            agent_config = agent_hierarchy[agent_code]
            if isinstance(agent_config, dict):
                sub_agent_config = agent_config.get("sub_agents", {})
                if sub_agent_config:
                    logger.info("[AGENT FACTORY] Agent %s has sub-agent config: %s", 
                               agent_code, list(sub_agent_config.keys()))
        
        try:
            agent = create_func(
                organization_id=organization_id,
                workflow_id=workflow_id,
                sub_agent_config=sub_agent_config,
                mcp_tools=mcp_tools
            )
            agents.append(agent)
            logger.info("[AGENT FACTORY] Created lazy agent: %s (NO LLM initialized yet)", agent_name)
        except LLMConfigNotFoundError as e:
            logger.error("[AGENT FACTORY] LLM config error for %s: %s", agent_name, e)
            raise
        except TypeError as e:
            logger.info("[AGENT FACTORY] Agent %s doesn't support hierarchy params, using basic creation", agent_name)
            agent = create_func(organization_id=organization_id, mcp_tools=mcp_tools)
            agents.append(agent)
        except Exception as e:
            logger.error("[AGENT FACTORY] Failed to create %s agent: %s", agent_name, e)
    
    logger.info("[AGENT FACTORY] Created %d of %d requested lazy agents", len(agents), len(agent_codes))
    logger.info("[AGENT FACTORY] Agents: %s", [a.name for a in agents])
    logger.info("=" * 60)
    return agents


__all__ = ["load_system_agents", "load_selected_agents"]
