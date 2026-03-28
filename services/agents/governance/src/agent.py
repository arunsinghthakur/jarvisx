import uuid
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from google.adk.tools.function_tool import FunctionTool
from google.genai import types

from jarvisx.common.utils import read_file
from jarvisx.database.session import SessionLocal
from jarvisx.database.models import ComplianceConfig, AuditLog, ChatbotConversation, WorkflowExecution
from jarvisx.services.audit_service import AuditService, AuditEntry, EventCategory
from jarvisx.services.policy_service import PolicyService
from jarvisx.services.pii_service import PIIService
from jarvisx.a2a.lazy_agent import LazyLlmAgent
from jarvisx.a2a.agent_defaults import DEFAULT_SAFETY_SETTINGS
from sqlalchemy import func

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
DESCRIPTION = read_file(str(PROMPTS_DIR / "description.txt"))
INSTRUCTION = read_file(str(PROMPTS_DIR / "instruction.txt"))


def _generate_compliance_recommendations(status: str, checks: List[Dict]) -> List[str]:
    recommendations = []
    
    for check in checks:
        if check["status"] == "NOT_CONFIGURED":
            recommendations.append("Configure compliance settings to enable full compliance monitoring.")
        elif check["status"] == "VIOLATIONS_FOUND":
            recommendations.append(f"Review and address {check.get('count', 'multiple')} policy violations.")
        elif check["status"] == "HIGH_VOLUME":
            recommendations.append("High PII exposure detected. Review data handling procedures.")
    
    if not recommendations:
        recommendations.append("Compliance status is healthy. Continue regular monitoring.")
    
    return recommendations


def _calculate_compliance_score(violations: int, pii_events: int, total_events: int) -> int:
    if total_events == 0:
        return 100
    
    score = 100
    violation_penalty = min(violations * 5, 30)
    score -= violation_penalty
    pii_penalty = min(pii_events * 2, 20)
    score -= pii_penalty
    
    return max(score, 0)


def _assess_soc2_compliance(violations: int, config) -> Dict[str, Any]:
    controls_met = []
    controls_at_risk = []
    
    if config and config.audit_enabled:
        controls_met.append("CC7.2 - System monitoring enabled")
    else:
        controls_at_risk.append("CC7.2 - System monitoring not enabled")
    
    if violations == 0:
        controls_met.append("CC6.1 - Access controls functioning")
    else:
        controls_at_risk.append("CC6.1 - Access control violations detected")
    
    if config and config.policy_enforcement_enabled:
        controls_met.append("CC6.3 - Logical access controls implemented")
    else:
        controls_at_risk.append("CC6.3 - Policy enforcement not enabled")
    
    return {
        "status": "AT_RISK" if controls_at_risk else "COMPLIANT",
        "controls_met": controls_met,
        "controls_at_risk": controls_at_risk
    }


def _assess_gdpr_compliance(pii_events: int, config) -> Dict[str, Any]:
    requirements_met = []
    requirements_at_risk = []
    
    if config and config.pii_detection_enabled:
        requirements_met.append("Article 32 - Data protection measures in place")
    else:
        requirements_at_risk.append("Article 32 - PII detection not enabled")
    
    if config and config.audit_retention_days:
        requirements_met.append("Article 17 - Data retention policy configured")
    else:
        requirements_at_risk.append("Article 17 - Data retention not configured")
    
    if pii_events > 50:
        requirements_at_risk.append("Article 33 - High volume of PII processing detected")
    else:
        requirements_met.append("Article 33 - PII processing within acceptable limits")
    
    return {
        "status": "AT_RISK" if requirements_at_risk else "COMPLIANT",
        "requirements_met": requirements_met,
        "requirements_at_risk": requirements_at_risk
    }


def _assess_hipaa_compliance(violations: int, pii_events: int, config) -> Dict[str, Any]:
    safeguards_met = []
    safeguards_at_risk = []
    
    if config and config.audit_enabled:
        safeguards_met.append("164.312(b) - Audit controls implemented")
    else:
        safeguards_at_risk.append("164.312(b) - Audit controls not enabled")
    
    if config and config.pii_mask_in_logs:
        safeguards_met.append("164.312(e) - Transmission security (PII masking)")
    else:
        safeguards_at_risk.append("164.312(e) - PII masking not enabled in logs")
    
    if violations == 0:
        safeguards_met.append("164.312(a) - Access controls functioning")
    else:
        safeguards_at_risk.append("164.312(a) - Access control violations detected")
    
    return {
        "status": "AT_RISK" if safeguards_at_risk else "COMPLIANT",
        "safeguards_met": safeguards_met,
        "safeguards_at_risk": safeguards_at_risk
    }


def _create_governance_tools(organization_id: str):
    def enforce_data_retention(dry_run: bool = True) -> Dict[str, Any]:
        db = SessionLocal()
        try:
            config = db.query(ComplianceConfig).filter(
                ComplianceConfig.organization_id == organization_id
            ).first()
            
            retention_days = config.audit_retention_days if config else 90
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
            
            audit_count = db.query(func.count(AuditLog.id)).filter(
                AuditLog.organization_id == organization_id,
                AuditLog.created_at < cutoff_date
            ).scalar()
            
            conversation_count = db.query(func.count(ChatbotConversation.id)).filter(
                ChatbotConversation.organization_id == organization_id,
                ChatbotConversation.created_at < cutoff_date
            ).scalar()
            
            deleted_counts = {}
            
            if not dry_run:
                audit_service = AuditService(db)
                deleted_counts["audit_logs"] = audit_service.cleanup_old_logs(organization_id)
            
            return {
                "retention_policy_days": retention_days,
                "cutoff_date": cutoff_date.isoformat(),
                "dry_run": dry_run,
                "data_affected": {
                    "audit_logs": audit_count,
                    "conversations": conversation_count
                },
                "deleted": deleted_counts if not dry_run else {},
                "message": "Dry run completed. Set dry_run=False to actually delete data." if dry_run else "Data retention enforced."
            }
        finally:
            db.close()

    def check_compliance_status() -> Dict[str, Any]:
        db = SessionLocal()
        try:
            config = db.query(ComplianceConfig).filter(
                ComplianceConfig.organization_id == organization_id
            ).first()
            
            compliance_checks = []
            overall_status = "COMPLIANT"
            
            if config:
                compliance_checks.append({
                    "check": "Compliance Configuration",
                    "status": "CONFIGURED",
                    "details": {
                        "pii_detection": config.pii_detection_enabled,
                        "audit_enabled": config.audit_enabled,
                        "policy_enforcement": config.policy_enforcement_enabled
                    }
                })
            else:
                compliance_checks.append({
                    "check": "Compliance Configuration",
                    "status": "NOT_CONFIGURED",
                    "details": "Using default settings"
                })
            
            audit_service = AuditService(db)
            recent_violations = audit_service.count(
                organization_id=organization_id,
                event_category="policy_violation",
                start_date=datetime.utcnow() - timedelta(days=7)
            )
            
            if recent_violations > 0:
                overall_status = "VIOLATIONS_DETECTED"
                compliance_checks.append({
                    "check": "Policy Violations (7 days)",
                    "status": "VIOLATIONS_FOUND",
                    "count": recent_violations
                })
            else:
                compliance_checks.append({
                    "check": "Policy Violations (7 days)",
                    "status": "CLEAN",
                    "count": 0
                })
            
            pii_exposure_count = db.query(func.count(AuditLog.id)).filter(
                AuditLog.organization_id == organization_id,
                AuditLog.pii_detected == True,
                AuditLog.created_at >= datetime.utcnow() - timedelta(days=7)
            ).scalar()
            
            if pii_exposure_count > 10:
                if overall_status == "COMPLIANT":
                    overall_status = "REVIEW_RECOMMENDED"
                compliance_checks.append({
                    "check": "PII Exposure Events (7 days)",
                    "status": "HIGH_VOLUME",
                    "count": pii_exposure_count
                })
            else:
                compliance_checks.append({
                    "check": "PII Exposure Events (7 days)",
                    "status": "ACCEPTABLE",
                    "count": pii_exposure_count
                })
            
            retention_days = config.audit_retention_days if config else 90
            compliance_checks.append({
                "check": "Data Retention Policy",
                "status": "CONFIGURED",
                "retention_days": retention_days
            })
            
            return {
                "organization_id": organization_id,
                "overall_status": overall_status,
                "checked_at": datetime.utcnow().isoformat(),
                "checks": compliance_checks,
                "recommendations": _generate_compliance_recommendations(overall_status, compliance_checks)
            }
        finally:
            db.close()

    def request_approval(
        action: str,
        resource_type: str,
        resource_id: str,
        reason: str
    ) -> Dict[str, Any]:
        approval_request = {
            "id": str(uuid.uuid4()),
            "organization_id": organization_id,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "reason": reason,
            "status": "PENDING",
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat()
        }
        
        db = SessionLocal()
        try:
            audit_service = AuditService(db)
            
            audit_service.log(AuditEntry(
                event_type="approval_requested",
                event_category=EventCategory.ADMIN_ACTION,
                organization_id=organization_id,
                resource_type=resource_type,
                resource_id=resource_id,
                action=action,
                outcome="pending",
                event_data=approval_request
            ))
        finally:
            db.close()
        
        return {
            "approval_request": approval_request,
            "message": f"Approval request created. Awaiting approval for: {action} on {resource_type}/{resource_id}",
            "next_steps": [
                "Request has been logged for audit purposes",
                "Approver will be notified",
                "Request expires in 24 hours if not acted upon"
            ]
        }

    def generate_governance_report() -> Dict[str, Any]:
        db = SessionLocal()
        try:
            config = db.query(ComplianceConfig).filter(
                ComplianceConfig.organization_id == organization_id
            ).first()
            
            audit_service = AuditService(db)
            
            now = datetime.utcnow()
            last_30_days = now - timedelta(days=30)
            last_7_days = now - timedelta(days=7)
            
            total_events_30d = audit_service.count(
                organization_id=organization_id,
                start_date=last_30_days
            )
            
            total_events_7d = audit_service.count(
                organization_id=organization_id,
                start_date=last_7_days
            )
            
            violations_30d = audit_service.count(
                organization_id=organization_id,
                event_category="policy_violation",
                start_date=last_30_days
            )
            
            pii_events_30d = db.query(func.count(AuditLog.id)).filter(
                AuditLog.organization_id == organization_id,
                AuditLog.pii_detected == True,
                AuditLog.created_at >= last_30_days
            ).scalar()
            
            compliance_status = check_compliance_status()
            
            report = {
                "report_title": "Governance Report",
                "organization_id": organization_id,
                "generated_at": now.isoformat(),
                "report_period": {
                    "start": last_30_days.isoformat(),
                    "end": now.isoformat()
                },
                "executive_summary": {
                    "overall_status": compliance_status["overall_status"],
                    "total_audit_events": total_events_30d,
                    "policy_violations": violations_30d,
                    "pii_exposure_events": pii_events_30d,
                    "compliance_score": _calculate_compliance_score(violations_30d, pii_events_30d, total_events_30d)
                },
                "configuration": {
                    "pii_detection_enabled": config.pii_detection_enabled if config else True,
                    "audit_enabled": config.audit_enabled if config else True,
                    "policy_enforcement_enabled": config.policy_enforcement_enabled if config else True,
                    "data_retention_days": config.audit_retention_days if config else 90
                },
                "trends": {
                    "events_last_7_days": total_events_7d,
                    "events_last_30_days": total_events_30d,
                    "daily_average": round(total_events_30d / 30, 2)
                },
                "recommendations": compliance_status["recommendations"],
                "frameworks": {
                    "soc2": _assess_soc2_compliance(violations_30d, config),
                    "gdpr": _assess_gdpr_compliance(pii_events_30d, config),
                    "hipaa": _assess_hipaa_compliance(violations_30d, pii_events_30d, config)
                }
            }
            
            return report
        finally:
            db.close()

    return [
        FunctionTool(func=enforce_data_retention),
        FunctionTool(func=check_compliance_status),
        FunctionTool(func=request_approval),
        FunctionTool(func=generate_governance_report),
    ]


def create_governance_agent(
    organization_id: Optional[str] = None,
    workflow_id: Optional[str] = None,
    sub_agent_config: Optional[Dict[str, Any]] = None,
    llm_config_id: Optional[str] = None,
) -> LazyLlmAgent:
    if not organization_id:
        raise ValueError("organization_id is required to create governance agent")
    
    logger.info("[GOVERNANCE] Creating lazy agent for org: %s (llm_config_id: %s)", organization_id, llm_config_id)
    
    tools = _create_governance_tools(organization_id)
    
    sub_agent_loader = None
    sub_agent_codes = []
    
    if sub_agent_config:
        enabled_subs = [k for k, v in sub_agent_config.items() if v.get("enabled", True)]
        if enabled_subs:
            sub_agent_codes = enabled_subs
            logger.info("[GOVERNANCE] Configured with sub-agents: %s", enabled_subs)
            
            async def load_sub_agents(org_id, _codes):
                from jarvisx.a2a.system_agent_factory import load_selected_agents
                sub_hierarchy = {k: v for k, v in sub_agent_config.items() if v.get("enabled", True)}
                return await load_selected_agents(org_id, enabled_subs, workflow_id, sub_hierarchy)
            
            sub_agent_loader = load_sub_agents
    
    return LazyLlmAgent(
        name="governance",
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
