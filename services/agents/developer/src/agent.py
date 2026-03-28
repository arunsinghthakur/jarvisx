import logging
from pathlib import Path
from typing import Optional, Dict, Any

from google.genai import types

from jarvisx.common.utils import read_file
from jarvisx.a2a.lazy_agent import LazyLlmAgent
from jarvisx.a2a.agent_defaults import DEFAULT_SAFETY_SETTINGS

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
DESCRIPTION = read_file(str(PROMPTS_DIR / "description.txt"))
INSTRUCTION = read_file(str(PROMPTS_DIR / "instruction.txt"))


def create_developer_agent(
    organization_id: Optional[str] = None,
    workflow_id: Optional[str] = None,
    sub_agent_config: Optional[Dict[str, Any]] = None,
    mcp_tools: list = None,
    llm_config_id: Optional[str] = None,
) -> LazyLlmAgent:
    if not organization_id:
        raise ValueError("organization_id is required to create developer agent")
    
    logger.info("[DEVELOPER] Creating lazy agent for org: %s (llm_config_id: %s)", organization_id, llm_config_id)
    
    sub_agent_loader = None
    sub_agent_codes = []
    
    if sub_agent_config:
        enabled_subs = [k for k, v in sub_agent_config.items() if v.get("enabled", True)]
        if enabled_subs:
            sub_agent_codes = enabled_subs
            logger.info("[DEVELOPER] Configured with sub-agents: %s", enabled_subs)
            
            async def load_sub_agents(org_id, _codes):
                from jarvisx.a2a.system_agent_factory import load_selected_agents
                sub_hierarchy = {k: v for k, v in sub_agent_config.items() if v.get("enabled", True)}
                return await load_selected_agents(org_id, enabled_subs, workflow_id, sub_hierarchy)
            
            sub_agent_loader = load_sub_agents
    
    return LazyLlmAgent(
        name="developer",
        organization_id=organization_id,
        description=DESCRIPTION,
        instruction=INSTRUCTION,
        generate_content_config=types.GenerateContentConfig(
            safety_settings=DEFAULT_SAFETY_SETTINGS,
        ),
        tools=mcp_tools or [],
        sub_agent_codes=sub_agent_codes,
        sub_agent_loader=sub_agent_loader,
        llm_config_id=llm_config_id,
    )
