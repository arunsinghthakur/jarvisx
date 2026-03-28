import logging
from pathlib import Path
from typing import List, Optional, Dict, Any

from google.genai import types

from jarvisx.common.utils import read_file
from jarvisx.a2a.lazy_agent import LazyLlmAgent
from jarvisx.a2a.system_agent_factory import load_selected_agents
from jarvisx.a2a.agent_defaults import DEFAULT_SAFETY_SETTINGS

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
DESCRIPTION = read_file(str(PROMPTS_DIR / "description.txt"))
INSTRUCTION = read_file(str(PROMPTS_DIR / "instruction.txt"))


def _fetch_agent_hierarchy_from_workflow(workflow_id: str) -> Dict[str, Any]:
    from jarvisx.database.session import SessionLocal
    from jarvisx.database.models import Workflow, WorkflowTriggerType
    
    logger.info("[ORCHESTRATOR] Fetching agent_hierarchy from workflow: %s", workflow_id)
    
    db = SessionLocal()
    try:
        workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
        if not workflow:
            logger.warning("[ORCHESTRATOR] Workflow not found: %s", workflow_id)
            return {}
        
        config = workflow.trigger_config or {}
        
        if "agent_hierarchy" in config:
            hierarchy = config.get("agent_hierarchy", {})
            logger.info("[ORCHESTRATOR] Using agent_hierarchy from workflow: %s", list(hierarchy.keys()))
            return hierarchy
        
        if "connected_agents" in config:
            connected_agents = config.get("connected_agents", [])
            hierarchy = {code: {"enabled": True, "sub_agents": {}} for code in connected_agents}
            logger.info("[ORCHESTRATOR] Converted connected_agents to hierarchy: %s", list(hierarchy.keys()))
            return hierarchy
        
        definition = workflow.definition or {}
        nodes = definition.get("nodes", [])
        
        hierarchy = {}
        for node in nodes:
            if node.get("type") == "agent":
                node_data = node.get("data", {})
                node_config = node_data.get("config", {})
                agent_code = node_config.get("agent")
                if agent_code and agent_code != "orchestrator":
                    hierarchy[agent_code] = {"enabled": True, "sub_agents": {}}
        
        if hierarchy:
            logger.info("[ORCHESTRATOR] Extracted agents from workflow definition: %s", list(hierarchy.keys()))
            return hierarchy
        
        return {}
    finally:
        db.close()


def create_orchestrator_agent(
    workflow_id: str,
    organization_id: str,
    mcp_tools: list = None,
    llm_config_id: str = None,
) -> LazyLlmAgent:
    logger.info("=" * 60)
    logger.info("[ORCHESTRATOR] create_orchestrator_agent() called")
    logger.info("[ORCHESTRATOR] Workflow ID: %s", workflow_id)
    logger.info("[ORCHESTRATOR] Organization ID: %s", organization_id)
    logger.info("[ORCHESTRATOR] LLM Config ID: %s", llm_config_id)
    logger.info("[ORCHESTRATOR] Creating LAZY orchestrator - NO LLM initialized yet")
    logger.info("=" * 60)
    
    if not organization_id:
        raise ValueError("organization_id is required to create orchestrator agent")
    
    if not workflow_id:
        raise ValueError("workflow_id is required to create orchestrator agent")
    
    async def load_sub_agents_from_workflow(org_id: str, _codes: List[str]) -> List:
        hierarchy = _fetch_agent_hierarchy_from_workflow(workflow_id)
        
        if not hierarchy:
            return []
        
        enabled_agents = [k for k, v in hierarchy.items() if v.get("enabled", True)]
        
        if not enabled_agents:
            return []
        
        logger.info("[ORCHESTRATOR] Loading %d sub-agents: %s", len(enabled_agents), enabled_agents)
        
        agents = await load_selected_agents(
            org_id, 
            enabled_agents, 
            workflow_id,
            hierarchy
        )
        return agents
    
    orchestrator = LazyLlmAgent(
        name="orchestrator",
        organization_id=organization_id,
        description=DESCRIPTION,
        instruction=INSTRUCTION,
        generate_content_config=types.GenerateContentConfig(
            safety_settings=DEFAULT_SAFETY_SETTINGS,
        ),
        tools=mcp_tools or [],
        sub_agent_codes=["workflow_defined"],
        sub_agent_loader=load_sub_agents_from_workflow,
        llm_config_id=llm_config_id,
    )
    
    logger.info("[ORCHESTRATOR] Lazy orchestrator created - LLM and sub-agents will load on first message")
    logger.info("=" * 60)
    
    return orchestrator


__all__ = ["create_orchestrator_agent"]
