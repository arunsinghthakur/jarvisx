import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

from google.adk.tools.function_tool import FunctionTool
from google.genai import types

from jarvisx.common.utils import read_file
from jarvisx.database.session import SessionLocal
from jarvisx.services.policy_service import PolicyService, PolicyContext
from jarvisx.a2a.lazy_agent import LazyLlmAgent
from jarvisx.a2a.agent_defaults import DEFAULT_SAFETY_SETTINGS

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
DESCRIPTION = read_file(str(PROMPTS_DIR / "description.txt"))
INSTRUCTION = read_file(str(PROMPTS_DIR / "instruction.txt"))


def _create_policy_tools(organization_id: str):
    def check_policy(
        action: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        db = SessionLocal()
        try:
            service = PolicyService(db)
            result = service.check_policy(
                organization_id=organization_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                user_id=user_id
            )
            return result
        finally:
            db.close()

    def validate_request(
        request_type: str,
        data: Optional[str] = None
    ) -> Dict[str, Any]:
        db = SessionLocal()
        try:
            service = PolicyService(db)
            
            data_dict = {}
            if data:
                try:
                    data_dict = json.loads(data)
                except json.JSONDecodeError:
                    data_dict = {"raw_data": data}
            
            result = service.validate_request(
                organization_id=organization_id,
                request_type=request_type,
                data=data_dict
            )
            return result
        finally:
            db.close()

    def list_applicable_policies(
        action: Optional[str] = None,
        resource_type: Optional[str] = None
    ) -> Dict[str, Any]:
        db = SessionLocal()
        try:
            service = PolicyService(db)
            policies = service.list_applicable_policies(
                organization_id=organization_id,
                action=action,
                resource_type=resource_type
            )
            
            return {
                "total_policies": len(policies),
                "policies": policies,
                "filter_applied": {
                    "action": action,
                    "resource_type": resource_type
                }
            }
        finally:
            db.close()

    def explain_policy_decision(
        action: str,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        db = SessionLocal()
        try:
            service = PolicyService(db)
            
            context_data = None
            if context:
                try:
                    context_data = json.loads(context)
                except json.JSONDecodeError:
                    context_data = {"context": context}
            
            explanation = service.explain_policy_decision(
                organization_id=organization_id,
                action=action,
                context_data=context_data
            )
            
            return explanation
        finally:
            db.close()

    return [
        FunctionTool(func=check_policy),
        FunctionTool(func=validate_request),
        FunctionTool(func=list_applicable_policies),
        FunctionTool(func=explain_policy_decision),
    ]


def create_policy_agent(
    organization_id: Optional[str] = None,
    workflow_id: Optional[str] = None,
    sub_agent_config: Optional[Dict[str, Any]] = None,
    llm_config_id: Optional[str] = None,
) -> LazyLlmAgent:
    if not organization_id:
        raise ValueError("organization_id is required to create policy agent")
    
    logger.info("[POLICY] Creating lazy agent for org: %s (llm_config_id: %s)", organization_id, llm_config_id)
    
    tools = _create_policy_tools(organization_id)
    
    sub_agent_loader = None
    sub_agent_codes = []
    
    if sub_agent_config:
        enabled_subs = [k for k, v in sub_agent_config.items() if v.get("enabled", True)]
        if enabled_subs:
            sub_agent_codes = enabled_subs
            logger.info("[POLICY] Configured with sub-agents: %s", enabled_subs)
            
            async def load_sub_agents(org_id, _codes):
                from jarvisx.a2a.system_agent_factory import load_selected_agents
                sub_hierarchy = {k: v for k, v in sub_agent_config.items() if v.get("enabled", True)}
                return await load_selected_agents(org_id, enabled_subs, workflow_id, sub_hierarchy)
            
            sub_agent_loader = load_sub_agents
    
    return LazyLlmAgent(
        name="policy",
        organization_id=organization_id,
        description=DESCRIPTION,
        instruction=INSTRUCTION,
        generate_content_config=types.GenerateContentConfig(
            safety_settings=DEFAULT_SAFETY_SETTINGS,
        ),
        tools=tools,
        sub_agent_codes=sub_agent_codes,
        sub_agent_loader=sub_agent_loader,
        llm_config_id=llm_config_id,
    )
