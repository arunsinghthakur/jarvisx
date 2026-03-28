from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import uuid

from jarvisx.database.models import ComplianceConfig, PIIPattern, PolicyRule, AuditLog
from jarvisx.database.session import get_db
from jarvisx.services.pii_service import PIIService
from jarvisx.services.audit_service import AuditService
from jarvisx.services.policy_service import PolicyService
from services.api.admin.src.dependencies import OrganizationContext, get_organization_context

router = APIRouter(prefix="/api/compliance", tags=["compliance"])


class ComplianceConfigUpdate(BaseModel):
    pii_detection_enabled: Optional[bool] = None
    pii_sensitivity_level: Optional[str] = None
    pii_mask_in_logs: Optional[bool] = None
    pii_mask_in_responses: Optional[bool] = None
    audit_enabled: Optional[bool] = None
    audit_retention_days: Optional[int] = None
    audit_log_level: Optional[str] = None
    policy_enforcement_enabled: Optional[bool] = None


class PIIPatternCreate(BaseModel):
    name: str
    pattern_regex: str
    category: str
    sensitivity: str = "medium"
    mask_char: str = "*"
    mask_style: str = "partial"


class PIIPatternUpdate(BaseModel):
    name: Optional[str] = None
    pattern_regex: Optional[str] = None
    category: Optional[str] = None
    sensitivity: Optional[str] = None
    mask_char: Optional[str] = None
    mask_style: Optional[str] = None
    is_active: Optional[bool] = None


class PolicyRuleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    rule_type: str
    rule_config: dict
    priority: int = 50


class PolicyRuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    rule_type: Optional[str] = None
    rule_config: Optional[dict] = None
    is_active: Optional[bool] = None
    priority: Optional[int] = None


class PIIScanRequest(BaseModel):
    text: str


@router.get("/config")
def get_compliance_config(
    db: Session = Depends(get_db),
    org_ctx: OrganizationContext = Depends(get_organization_context)
):
    config = db.query(ComplianceConfig).filter(
        ComplianceConfig.organization_id == org_ctx.organization_id
    ).first()
    
    if not config:
        return {
            "id": None,
            "organization_id": org_ctx.organization_id,
            "pii_detection_enabled": True,
            "pii_sensitivity_level": "medium",
            "pii_mask_in_logs": True,
            "pii_mask_in_responses": False,
            "audit_enabled": True,
            "audit_retention_days": 90,
            "audit_log_level": "standard",
            "policy_enforcement_enabled": True,
            "is_default": True
        }
    
    return {
        "id": config.id,
        "organization_id": config.organization_id,
        "pii_detection_enabled": config.pii_detection_enabled,
        "pii_sensitivity_level": config.pii_sensitivity_level,
        "pii_mask_in_logs": config.pii_mask_in_logs,
        "pii_mask_in_responses": config.pii_mask_in_responses,
        "audit_enabled": config.audit_enabled,
        "audit_retention_days": config.audit_retention_days,
        "audit_log_level": config.audit_log_level,
        "policy_enforcement_enabled": config.policy_enforcement_enabled,
        "is_default": False
    }


@router.put("/config")
def update_compliance_config(
    config_update: ComplianceConfigUpdate,
    db: Session = Depends(get_db),
    org_ctx: OrganizationContext = Depends(get_organization_context)
):
    config = db.query(ComplianceConfig).filter(
        ComplianceConfig.organization_id == org_ctx.organization_id
    ).first()
    
    if not config:
        config = ComplianceConfig(
            id=str(uuid.uuid4()),
            organization_id=org_ctx.organization_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(config)
    
    update_data = config_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(config, key, value)
    
    config.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(config)
    
    return {
        "id": config.id,
        "organization_id": config.organization_id,
        "pii_detection_enabled": config.pii_detection_enabled,
        "pii_sensitivity_level": config.pii_sensitivity_level,
        "pii_mask_in_logs": config.pii_mask_in_logs,
        "pii_mask_in_responses": config.pii_mask_in_responses,
        "audit_enabled": config.audit_enabled,
        "audit_retention_days": config.audit_retention_days,
        "audit_log_level": config.audit_log_level,
        "policy_enforcement_enabled": config.policy_enforcement_enabled
    }


@router.get("/pii-patterns")
def list_pii_patterns(
    include_system: bool = True,
    db: Session = Depends(get_db),
    org_ctx: OrganizationContext = Depends(get_organization_context)
):
    query = db.query(PIIPattern)
    
    if include_system:
        query = query.filter(
            or_(
                PIIPattern.is_system_pattern == True,
                PIIPattern.organization_id == org_ctx.organization_id
            )
        )
    else:
        query = query.filter(PIIPattern.organization_id == org_ctx.organization_id)
    
    patterns = query.order_by(PIIPattern.category, PIIPattern.name).all()
    
    return [
        {
            "id": p.id,
            "name": p.name,
            "pattern_regex": p.pattern_regex,
            "category": p.category,
            "sensitivity": p.sensitivity,
            "mask_char": p.mask_char,
            "mask_style": p.mask_style,
            "is_system_pattern": p.is_system_pattern,
            "is_active": p.is_active,
            "can_edit": not p.is_system_pattern or org_ctx.is_platform_admin,
            "can_delete": not p.is_system_pattern or org_ctx.is_platform_admin
        }
        for p in patterns
    ]


@router.post("/pii-patterns")
def create_pii_pattern(
    pattern: PIIPatternCreate,
    db: Session = Depends(get_db),
    org_ctx: OrganizationContext = Depends(get_organization_context)
):
    new_pattern = PIIPattern(
        id=str(uuid.uuid4()),
        organization_id=org_ctx.organization_id,
        name=pattern.name,
        pattern_regex=pattern.pattern_regex,
        category=pattern.category,
        sensitivity=pattern.sensitivity,
        mask_char=pattern.mask_char,
        mask_style=pattern.mask_style,
        is_system_pattern=False,
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.add(new_pattern)
    db.commit()
    db.refresh(new_pattern)
    
    return {
        "id": new_pattern.id,
        "name": new_pattern.name,
        "pattern_regex": new_pattern.pattern_regex,
        "category": new_pattern.category,
        "sensitivity": new_pattern.sensitivity,
        "mask_char": new_pattern.mask_char,
        "mask_style": new_pattern.mask_style,
        "is_system_pattern": new_pattern.is_system_pattern,
        "is_active": new_pattern.is_active
    }


@router.put("/pii-patterns/{pattern_id}")
def update_pii_pattern(
    pattern_id: str,
    pattern_update: PIIPatternUpdate,
    db: Session = Depends(get_db),
    org_ctx: OrganizationContext = Depends(get_organization_context)
):
    pattern = db.query(PIIPattern).filter(PIIPattern.id == pattern_id).first()
    
    if not pattern:
        raise HTTPException(status_code=404, detail="PII pattern not found")
    
    if pattern.is_system_pattern and not org_ctx.is_platform_admin:
        raise HTTPException(status_code=403, detail="Only platform admins can modify system patterns")
    
    if pattern.organization_id and pattern.organization_id != org_ctx.organization_id and not org_ctx.is_platform_admin:
        raise HTTPException(status_code=403, detail="Cannot modify patterns from other organizations")
    
    update_data = pattern_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(pattern, key, value)
    
    pattern.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(pattern)
    
    return {
        "id": pattern.id,
        "name": pattern.name,
        "pattern_regex": pattern.pattern_regex,
        "category": pattern.category,
        "sensitivity": pattern.sensitivity,
        "mask_char": pattern.mask_char,
        "mask_style": pattern.mask_style,
        "is_system_pattern": pattern.is_system_pattern,
        "is_active": pattern.is_active
    }


@router.delete("/pii-patterns/{pattern_id}")
def delete_pii_pattern(
    pattern_id: str,
    db: Session = Depends(get_db),
    org_ctx: OrganizationContext = Depends(get_organization_context)
):
    pattern = db.query(PIIPattern).filter(PIIPattern.id == pattern_id).first()
    
    if not pattern:
        raise HTTPException(status_code=404, detail="PII pattern not found")
    
    if pattern.is_system_pattern and not org_ctx.is_platform_admin:
        raise HTTPException(status_code=403, detail="Only platform admins can delete system patterns")
    
    if pattern.organization_id and pattern.organization_id != org_ctx.organization_id and not org_ctx.is_platform_admin:
        raise HTTPException(status_code=403, detail="Cannot delete patterns from other organizations")
    
    db.delete(pattern)
    db.commit()
    
    return {"message": "PII pattern deleted successfully"}


@router.get("/policies")
def list_policy_rules(
    include_system: bool = True,
    rule_type: Optional[str] = None,
    db: Session = Depends(get_db),
    org_ctx: OrganizationContext = Depends(get_organization_context)
):
    query = db.query(PolicyRule)
    
    if include_system:
        query = query.filter(
            or_(
                PolicyRule.is_system_rule == True,
                PolicyRule.organization_id == org_ctx.organization_id
            )
        )
    else:
        query = query.filter(PolicyRule.organization_id == org_ctx.organization_id)
    
    if rule_type:
        query = query.filter(PolicyRule.rule_type == rule_type)
    
    rules = query.order_by(PolicyRule.priority.desc(), PolicyRule.name).all()
    
    return [
        {
            "id": r.id,
            "name": r.name,
            "description": r.description,
            "rule_type": r.rule_type,
            "rule_config": r.rule_config,
            "is_system_rule": r.is_system_rule,
            "is_active": r.is_active,
            "priority": r.priority,
            "can_edit": not r.is_system_rule or org_ctx.is_platform_admin,
            "can_delete": not r.is_system_rule or org_ctx.is_platform_admin
        }
        for r in rules
    ]


@router.post("/policies")
def create_policy_rule(
    rule: PolicyRuleCreate,
    db: Session = Depends(get_db),
    org_ctx: OrganizationContext = Depends(get_organization_context)
):
    new_rule = PolicyRule(
        id=str(uuid.uuid4()),
        organization_id=org_ctx.organization_id,
        name=rule.name,
        description=rule.description,
        rule_type=rule.rule_type,
        rule_config=rule.rule_config,
        is_system_rule=False,
        is_active=True,
        priority=rule.priority,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.add(new_rule)
    db.commit()
    db.refresh(new_rule)
    
    return {
        "id": new_rule.id,
        "name": new_rule.name,
        "description": new_rule.description,
        "rule_type": new_rule.rule_type,
        "rule_config": new_rule.rule_config,
        "is_system_rule": new_rule.is_system_rule,
        "is_active": new_rule.is_active,
        "priority": new_rule.priority
    }


@router.put("/policies/{rule_id}")
def update_policy_rule(
    rule_id: str,
    rule_update: PolicyRuleUpdate,
    db: Session = Depends(get_db),
    org_ctx: OrganizationContext = Depends(get_organization_context)
):
    rule = db.query(PolicyRule).filter(PolicyRule.id == rule_id).first()
    
    if not rule:
        raise HTTPException(status_code=404, detail="Policy rule not found")
    
    if rule.is_system_rule and not org_ctx.is_platform_admin:
        raise HTTPException(status_code=403, detail="Only platform admins can modify system rules")
    
    if rule.organization_id and rule.organization_id != org_ctx.organization_id and not org_ctx.is_platform_admin:
        raise HTTPException(status_code=403, detail="Cannot modify rules from other organizations")
    
    update_data = rule_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(rule, key, value)
    
    rule.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(rule)
    
    return {
        "id": rule.id,
        "name": rule.name,
        "description": rule.description,
        "rule_type": rule.rule_type,
        "rule_config": rule.rule_config,
        "is_system_rule": rule.is_system_rule,
        "is_active": rule.is_active,
        "priority": rule.priority
    }


@router.delete("/policies/{rule_id}")
def delete_policy_rule(
    rule_id: str,
    db: Session = Depends(get_db),
    org_ctx: OrganizationContext = Depends(get_organization_context)
):
    rule = db.query(PolicyRule).filter(PolicyRule.id == rule_id).first()
    
    if not rule:
        raise HTTPException(status_code=404, detail="Policy rule not found")
    
    if rule.is_system_rule and not org_ctx.is_platform_admin:
        raise HTTPException(status_code=403, detail="Only platform admins can delete system rules")
    
    if rule.organization_id and rule.organization_id != org_ctx.organization_id and not org_ctx.is_platform_admin:
        raise HTTPException(status_code=403, detail="Cannot delete rules from other organizations")
    
    db.delete(rule)
    db.commit()
    
    return {"message": "Policy rule deleted successfully"}


@router.get("/audit-logs")
def list_audit_logs(
    event_type: Optional[str] = None,
    event_category: Optional[str] = None,
    user_id: Optional[str] = None,
    days_back: int = Query(default=7, ge=1, le=365),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    org_ctx: OrganizationContext = Depends(get_organization_context)
):
    service = AuditService(db)
    
    start_date = datetime.utcnow() - timedelta(days=days_back)
    
    logs = service.query(
        organization_id=org_ctx.organization_id,
        event_type=event_type,
        event_category=event_category,
        user_id=user_id,
        start_date=start_date,
        limit=limit,
        offset=offset
    )
    
    total = service.count(
        organization_id=org_ctx.organization_id,
        event_type=event_type,
        event_category=event_category,
        start_date=start_date
    )
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "logs": [
            {
                "id": log.id,
                "event_type": log.event_type,
                "event_category": log.event_category,
                "user_id": log.user_id,
                "workspace_id": log.workspace_id,
                "agent_id": log.agent_id,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "action": log.action,
                "outcome": log.outcome,
                "pii_detected": log.pii_detected,
                "ip_address": log.ip_address,
                "created_at": log.created_at.isoformat()
            }
            for log in logs
        ]
    }


@router.get("/audit-logs/export")
def export_audit_logs(
    days_back: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
    org_ctx: OrganizationContext = Depends(get_organization_context)
):
    service = AuditService(db)
    
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days_back)
    
    report = service.export_report(
        organization_id=org_ctx.organization_id,
        start_date=start_date,
        end_date=end_date
    )
    
    return report


@router.post("/pii/scan")
def scan_for_pii(
    request: PIIScanRequest,
    db: Session = Depends(get_db),
    org_ctx: OrganizationContext = Depends(get_organization_context)
):
    service = PIIService(db)
    result = service.scan(request.text, org_ctx.organization_id)
    
    return {
        "has_pii": result.has_pii,
        "total_matches": len(result.matches),
        "categories_found": result.categories_found,
        "sensitivity_levels": result.sensitivity_levels,
        "masked_text": result.masked_text,
        "matches": [
            {
                "pattern_name": m.pattern_name,
                "category": m.category,
                "sensitivity": m.sensitivity,
                "position": {"start": m.start_position, "end": m.end_position}
            }
            for m in result.matches
        ]
    }


@router.get("/dashboard")
def get_compliance_dashboard(
    db: Session = Depends(get_db),
    org_ctx: OrganizationContext = Depends(get_organization_context)
):
    service = AuditService(db)
    
    now = datetime.utcnow()
    last_7_days = now - timedelta(days=7)
    last_30_days = now - timedelta(days=30)
    
    events_7d = service.count(
        organization_id=org_ctx.organization_id,
        start_date=last_7_days
    )
    
    events_30d = service.count(
        organization_id=org_ctx.organization_id,
        start_date=last_30_days
    )
    
    violations_7d = service.count(
        organization_id=org_ctx.organization_id,
        event_category="policy_violation",
        start_date=last_7_days
    )
    
    pii_events_7d = db.query(AuditLog).filter(
        AuditLog.organization_id == org_ctx.organization_id,
        AuditLog.pii_detected == True,
        AuditLog.created_at >= last_7_days
    ).count()
    
    config = db.query(ComplianceConfig).filter(
        ComplianceConfig.organization_id == org_ctx.organization_id
    ).first()
    
    custom_patterns = db.query(PIIPattern).filter(
        PIIPattern.organization_id == org_ctx.organization_id,
        PIIPattern.is_system_pattern == False
    ).count()
    
    custom_rules = db.query(PolicyRule).filter(
        PolicyRule.organization_id == org_ctx.organization_id,
        PolicyRule.is_system_rule == False
    ).count()
    
    compliance_status = "COMPLIANT"
    if violations_7d > 0:
        compliance_status = "VIOLATIONS_DETECTED"
    elif pii_events_7d > 10:
        compliance_status = "REVIEW_RECOMMENDED"
    
    return {
        "compliance_status": compliance_status,
        "metrics": {
            "audit_events_7d": events_7d,
            "audit_events_30d": events_30d,
            "policy_violations_7d": violations_7d,
            "pii_exposure_events_7d": pii_events_7d,
            "custom_pii_patterns": custom_patterns,
            "custom_policy_rules": custom_rules
        },
        "configuration": {
            "pii_detection_enabled": config.pii_detection_enabled if config else True,
            "audit_enabled": config.audit_enabled if config else True,
            "policy_enforcement_enabled": config.policy_enforcement_enabled if config else True,
            "retention_days": config.audit_retention_days if config else 90
        },
        "quick_stats": {
            "daily_average_events": round(events_30d / 30, 2),
            "pii_detection_rate": round(pii_events_7d / events_7d * 100, 2) if events_7d > 0 else 0
        }
    }
