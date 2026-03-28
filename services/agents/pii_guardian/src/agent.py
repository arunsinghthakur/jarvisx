import logging
from pathlib import Path
from typing import Optional, Dict, Any

from google.adk.tools.function_tool import FunctionTool
from google.genai import types

from jarvisx.common.utils import read_file
from jarvisx.database.session import SessionLocal
from jarvisx.services.pii_service import PIIService
from jarvisx.a2a.lazy_agent import LazyLlmAgent
from jarvisx.a2a.agent_defaults import DEFAULT_SAFETY_SETTINGS

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
DESCRIPTION = read_file(str(PROMPTS_DIR / "description.txt"))
INSTRUCTION = read_file(str(PROMPTS_DIR / "instruction.txt"))


def _get_risk_recommendation(risk_level: str) -> str:
    recommendations = {
        "high": "HIGH RISK: Contains highly sensitive PII. Do not store or transmit without encryption. Consider if this data is necessary.",
        "medium": "MEDIUM RISK: Contains personal information. Apply standard data protection measures. Mask before logging.",
        "low": "LOW RISK: Contains minimal PII. Standard handling procedures apply."
    }
    return recommendations.get(risk_level, "Unable to determine risk level.")


def _create_pii_tools(organization_id: str):
    def scan_for_pii(text: str) -> Dict[str, Any]:
        db = SessionLocal()
        try:
            service = PIIService(db)
            detections = service.detect(text, organization_id)
            
            if not detections:
                return {
                    "has_pii": False,
                    "message": "No PII detected in the provided text.",
                    "matches": []
                }
            
            return {
                "has_pii": True,
                "total_matches": len(detections),
                "matches": detections,
                "message": f"Found {len(detections)} PII instance(s) in the text."
            }
        finally:
            db.close()

    def mask_pii(text: str) -> Dict[str, Any]:
        db = SessionLocal()
        try:
            service = PIIService(db)
            result = service.scan(text, organization_id)
            
            return {
                "original_length": len(text),
                "masked_text": result.masked_text,
                "pii_found": result.has_pii,
                "categories_masked": result.categories_found,
                "total_masked": len(result.matches)
            }
        finally:
            db.close()

    def classify_pii(text: str) -> Dict[str, Any]:
        db = SessionLocal()
        try:
            service = PIIService(db)
            classification = service.classify(text, organization_id)
            
            return {
                "has_pii": classification["has_pii"],
                "risk_level": classification["risk_level"],
                "max_sensitivity": classification["max_sensitivity"],
                "total_pii_count": classification["total_matches"],
                "by_category": classification["categories"],
                "by_sensitivity": classification["sensitivities"],
                "recommendation": _get_risk_recommendation(classification["risk_level"])
            }
        finally:
            db.close()

    def get_pii_report(text: str) -> Dict[str, Any]:
        db = SessionLocal()
        try:
            service = PIIService(db)
            report = service.get_report(text, organization_id)
            return report
        finally:
            db.close()

    return [
        FunctionTool(func=scan_for_pii),
        FunctionTool(func=mask_pii),
        FunctionTool(func=classify_pii),
        FunctionTool(func=get_pii_report),
    ]


def create_pii_guardian_agent(
    organization_id: Optional[str] = None,
    workflow_id: Optional[str] = None,
    sub_agent_config: Optional[Dict[str, Any]] = None,
    llm_config_id: Optional[str] = None,
) -> LazyLlmAgent:
    if not organization_id:
        raise ValueError("organization_id is required to create pii_guardian agent")
    
    logger.info("[PII_GUARDIAN] Creating lazy agent for org: %s (llm_config_id: %s)", organization_id, llm_config_id)
    
    tools = _create_pii_tools(organization_id)
    
    sub_agent_loader = None
    sub_agent_codes = []
    
    if sub_agent_config:
        enabled_subs = [k for k, v in sub_agent_config.items() if v.get("enabled", True)]
        if enabled_subs:
            sub_agent_codes = enabled_subs
            logger.info("[PII_GUARDIAN] Configured with sub-agents: %s", enabled_subs)
            
            async def load_sub_agents(org_id, _codes):
                from jarvisx.a2a.system_agent_factory import load_selected_agents
                sub_hierarchy = {k: v for k, v in sub_agent_config.items() if v.get("enabled", True)}
                return await load_selected_agents(org_id, enabled_subs, workflow_id, sub_hierarchy)
            
            sub_agent_loader = load_sub_agents
    
    return LazyLlmAgent(
        name="pii_guardian",
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
