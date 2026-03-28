import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from google.adk.tools.function_tool import FunctionTool
from google.genai import types

from jarvisx.common.utils import read_file
from jarvisx.database.session import SessionLocal
from jarvisx.services.audit_service import AuditService, AuditEntry, EventType, EventCategory, AuditOutcome
from jarvisx.a2a.lazy_agent import LazyLlmAgent
from jarvisx.a2a.agent_defaults import DEFAULT_SAFETY_SETTINGS

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
DESCRIPTION = read_file(str(PROMPTS_DIR / "description.txt"))
INSTRUCTION = read_file(str(PROMPTS_DIR / "instruction.txt"))


def _generate_recommendations(summary: Dict[str, Any]) -> List[str]:
    recommendations = []
    
    if summary["policy_violations"] > 0:
        recommendations.append(f"URGENT: {summary['policy_violations']} policy violations detected. Review and remediate immediately.")
    
    if summary["pii_events"] > 0:
        recommendations.append(f"PII was detected in {summary['pii_events']} events. Verify data handling procedures.")
    
    auth_events = summary["events_by_category"].get("authentication", 0)
    failed_logins = summary["events_by_type"].get("login_failed", 0)
    if failed_logins > auth_events * 0.1:
        recommendations.append("High rate of failed login attempts detected. Consider implementing additional security measures.")
    
    if not recommendations:
        recommendations.append("No significant compliance issues detected. Continue monitoring.")
    
    return recommendations


def _create_audit_tools(organization_id: str):
    def log_access(
        resource_type: str,
        resource_id: str,
        action: str,
        user_id: Optional[str] = None,
        details: Optional[str] = None
    ) -> Dict[str, Any]:
        db = SessionLocal()
        try:
            service = AuditService(db)
            detail_dict = {"notes": details} if details else None
            
            log = service.log_access(
                organization_id=organization_id,
                resource_type=resource_type,
                resource_id=resource_id,
                action=action,
                user_id=user_id,
                outcome=AuditOutcome.SUCCESS,
                details=detail_dict
            )
            
            if log:
                return {
                    "logged": True,
                    "log_id": log.id,
                    "message": f"Access event logged: {action} on {resource_type}/{resource_id}"
                }
            return {"logged": False, "message": "Audit logging is disabled for this organization"}
        finally:
            db.close()

    def log_agent_call(
        agent_id: str,
        input_text: str,
        output_text: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        db = SessionLocal()
        try:
            service = AuditService(db)
            
            log = service.log_agent_call(
                organization_id=organization_id,
                agent_id=agent_id,
                input_text=input_text,
                output_text=output_text,
                user_id=user_id,
                outcome=AuditOutcome.SUCCESS
            )
            
            if log:
                return {
                    "logged": True,
                    "log_id": log.id,
                    "pii_detected": log.pii_detected,
                    "message": f"Agent call logged for {agent_id}"
                }
            return {"logged": False, "message": "Audit logging is disabled for this organization"}
        finally:
            db.close()

    def query_audit_logs(
        event_type: Optional[str] = None,
        event_category: Optional[str] = None,
        user_id: Optional[str] = None,
        days_back: int = 7,
        limit: int = 50
    ) -> Dict[str, Any]:
        db = SessionLocal()
        try:
            service = AuditService(db)
            
            start_date = datetime.utcnow() - timedelta(days=days_back)
            
            logs = service.query(
                organization_id=organization_id,
                event_type=event_type,
                event_category=event_category,
                user_id=user_id,
                start_date=start_date,
                limit=limit
            )
            
            total = service.count(
                organization_id=organization_id,
                event_type=event_type,
                event_category=event_category,
                start_date=start_date
            )
            
            return {
                "total_matching": total,
                "returned": len(logs),
                "period_days": days_back,
                "logs": [
                    {
                        "id": log.id,
                        "timestamp": log.created_at.isoformat(),
                        "event_type": log.event_type,
                        "event_category": log.event_category,
                        "user_id": log.user_id,
                        "agent_id": log.agent_id,
                        "resource_type": log.resource_type,
                        "resource_id": log.resource_id,
                        "action": log.action,
                        "outcome": log.outcome,
                        "pii_detected": log.pii_detected
                    }
                    for log in logs
                ]
            }
        finally:
            db.close()

    def generate_compliance_report(days_back: int = 30) -> Dict[str, Any]:
        db = SessionLocal()
        try:
            service = AuditService(db)
            
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days_back)
            
            report = service.export_report(
                organization_id=organization_id,
                start_date=start_date,
                end_date=end_date
            )
            
            summary = report["summary"]
            
            compliance_status = "COMPLIANT"
            if summary["policy_violations"] > 0:
                compliance_status = "VIOLATIONS_DETECTED"
            elif summary["pii_events"] > 10:
                compliance_status = "REVIEW_RECOMMENDED"
            
            return {
                "compliance_status": compliance_status,
                "report_period": f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
                "summary": {
                    "total_events": summary["total_events"],
                    "pii_exposure_events": summary["pii_events"],
                    "policy_violations": summary["policy_violations"],
                    "events_by_category": summary["events_by_category"],
                    "events_by_type": summary["events_by_type"]
                },
                "recommendations": _generate_recommendations(summary),
                "generated_at": datetime.utcnow().isoformat()
            }
        finally:
            db.close()

    return [
        FunctionTool(func=log_access),
        FunctionTool(func=log_agent_call),
        FunctionTool(func=query_audit_logs),
        FunctionTool(func=generate_compliance_report),
    ]


def create_audit_agent(
    organization_id: Optional[str] = None,
    workflow_id: Optional[str] = None,
    sub_agent_config: Optional[Dict[str, Any]] = None,
    llm_config_id: Optional[str] = None,
) -> LazyLlmAgent:
    if not organization_id:
        raise ValueError("organization_id is required to create audit agent")
    
    logger.info("[AUDIT] Creating lazy agent for org: %s (llm_config_id: %s)", organization_id, llm_config_id)
    
    tools = _create_audit_tools(organization_id)
    
    sub_agent_loader = None
    sub_agent_codes = []
    
    if sub_agent_config:
        enabled_subs = [k for k, v in sub_agent_config.items() if v.get("enabled", True)]
        if enabled_subs:
            sub_agent_codes = enabled_subs
            logger.info("[AUDIT] Configured with sub-agents: %s", enabled_subs)
            
            async def load_sub_agents(org_id, _codes):
                from jarvisx.a2a.system_agent_factory import load_selected_agents
                sub_hierarchy = {k: v for k, v in sub_agent_config.items() if v.get("enabled", True)}
                return await load_selected_agents(org_id, enabled_subs, workflow_id, sub_hierarchy)
            
            sub_agent_loader = load_sub_agents
    
    return LazyLlmAgent(
        name="audit",
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
