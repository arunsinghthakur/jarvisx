import logging
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import json

from sqlalchemy.orm import Session
from sqlalchemy import desc, and_

from jarvisx.database.models import AuditLog, ComplianceConfig
from jarvisx.services.pii_service import PIIService

logger = logging.getLogger(__name__)


class EventCategory(str, Enum):
    AUTHENTICATION = "authentication"
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    AGENT_INTERACTION = "agent_interaction"
    WORKFLOW_EXECUTION = "workflow_execution"
    ADMIN_ACTION = "admin_action"
    POLICY_VIOLATION = "policy_violation"
    SYSTEM = "system"


class EventType(str, Enum):
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    READ = "read"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    EXPORT = "export"
    AGENT_CALL = "agent_call"
    AGENT_RESPONSE = "agent_response"
    WORKFLOW_START = "workflow_start"
    WORKFLOW_COMPLETE = "workflow_complete"
    WORKFLOW_FAILED = "workflow_failed"
    CONFIG_CHANGE = "config_change"
    USER_CREATED = "user_created"
    USER_DELETED = "user_deleted"
    POLICY_EVALUATED = "policy_evaluated"
    POLICY_BLOCKED = "policy_blocked"
    PII_DETECTED = "pii_detected"
    ERROR = "error"


class AuditOutcome(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    BLOCKED = "blocked"
    PARTIAL = "partial"


@dataclass
class AuditEntry:
    event_type: str
    event_category: str
    organization_id: str
    workspace_id: Optional[str] = None
    user_id: Optional[str] = None
    agent_id: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    action: Optional[str] = None
    outcome: Optional[str] = None
    event_data: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class AuditService:
    def __init__(self, db: Session):
        self.db = db
        self._pii_service: Optional[PIIService] = None
    
    @property
    def pii_service(self) -> PIIService:
        if self._pii_service is None:
            self._pii_service = PIIService(self.db)
        return self._pii_service
    
    def get_compliance_config(self, organization_id: str) -> Optional[ComplianceConfig]:
        return self.db.query(ComplianceConfig).filter(
            ComplianceConfig.organization_id == organization_id
        ).first()
    
    def _should_log(self, organization_id: str) -> bool:
        config = self.get_compliance_config(organization_id)
        return config is None or config.audit_enabled
    
    def _mask_pii_in_data(self, data: Any, organization_id: str) -> tuple[Any, bool, List[str]]:
        config = self.get_compliance_config(organization_id)
        if config and not config.pii_mask_in_logs:
            return data, False, []
        
        pii_detected = False
        pii_categories: List[str] = []
        
        if isinstance(data, str):
            result = self.pii_service.scan(data, organization_id)
            if result.has_pii:
                pii_detected = True
                pii_categories.extend(result.categories_found)
                return result.masked_text, pii_detected, pii_categories
            return data, pii_detected, pii_categories
        
        if isinstance(data, dict):
            masked_data = {}
            for key, value in data.items():
                masked_value, detected, categories = self._mask_pii_in_data(value, organization_id)
                masked_data[key] = masked_value
                if detected:
                    pii_detected = True
                    pii_categories.extend(categories)
            return masked_data, pii_detected, list(set(pii_categories))
        
        if isinstance(data, list):
            masked_list = []
            for item in data:
                masked_item, detected, categories = self._mask_pii_in_data(item, organization_id)
                masked_list.append(masked_item)
                if detected:
                    pii_detected = True
                    pii_categories.extend(categories)
            return masked_list, pii_detected, list(set(pii_categories))
        
        return data, pii_detected, pii_categories
    
    def log(self, entry: AuditEntry) -> Optional[AuditLog]:
        if not self._should_log(entry.organization_id):
            return None
        
        pii_detected = False
        pii_categories: List[str] = []
        masked_event_data = entry.event_data
        
        if entry.event_data:
            masked_event_data, pii_detected, pii_categories = self._mask_pii_in_data(
                entry.event_data, entry.organization_id
            )
        
        audit_log = AuditLog(
            id=str(uuid.uuid4()),
            organization_id=entry.organization_id,
            workspace_id=entry.workspace_id,
            user_id=entry.user_id,
            event_type=entry.event_type,
            event_category=entry.event_category,
            event_data=masked_event_data,
            agent_id=entry.agent_id,
            resource_type=entry.resource_type,
            resource_id=entry.resource_id,
            action=entry.action,
            outcome=entry.outcome,
            pii_detected=pii_detected,
            pii_categories=pii_categories if pii_categories else None,
            ip_address=entry.ip_address,
            user_agent=entry.user_agent,
            created_at=datetime.utcnow()
        )
        
        self.db.add(audit_log)
        self.db.commit()
        self.db.refresh(audit_log)
        
        logger.debug(f"Audit log created: {audit_log.id} - {entry.event_type}")
        return audit_log
    
    def log_access(
        self,
        organization_id: str,
        resource_type: str,
        resource_id: str,
        action: str,
        user_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
        outcome: str = AuditOutcome.SUCCESS,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None
    ) -> Optional[AuditLog]:
        entry = AuditEntry(
            event_type=EventType.READ if action == "read" else action,
            event_category=EventCategory.DATA_ACCESS,
            organization_id=organization_id,
            workspace_id=workspace_id,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            outcome=outcome,
            event_data=details,
            ip_address=ip_address
        )
        return self.log(entry)
    
    def log_agent_call(
        self,
        organization_id: str,
        agent_id: str,
        input_text: str,
        output_text: Optional[str] = None,
        workspace_id: Optional[str] = None,
        user_id: Optional[str] = None,
        outcome: str = AuditOutcome.SUCCESS,
        error: Optional[str] = None
    ) -> Optional[AuditLog]:
        entry = AuditEntry(
            event_type=EventType.AGENT_CALL,
            event_category=EventCategory.AGENT_INTERACTION,
            organization_id=organization_id,
            workspace_id=workspace_id,
            user_id=user_id,
            agent_id=agent_id,
            action="invoke",
            outcome=outcome,
            event_data={
                "input": input_text,
                "output": output_text,
                "error": error
            }
        )
        return self.log(entry)
    
    def log_authentication(
        self,
        organization_id: str,
        user_id: str,
        event_type: str,
        outcome: str = AuditOutcome.SUCCESS,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> Optional[AuditLog]:
        entry = AuditEntry(
            event_type=event_type,
            event_category=EventCategory.AUTHENTICATION,
            organization_id=organization_id,
            user_id=user_id,
            action=event_type,
            outcome=outcome,
            event_data=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
        return self.log(entry)
    
    def log_workflow_event(
        self,
        organization_id: str,
        workflow_id: str,
        execution_id: str,
        event_type: str,
        workspace_id: Optional[str] = None,
        user_id: Optional[str] = None,
        outcome: str = AuditOutcome.SUCCESS,
        details: Optional[Dict[str, Any]] = None
    ) -> Optional[AuditLog]:
        entry = AuditEntry(
            event_type=event_type,
            event_category=EventCategory.WORKFLOW_EXECUTION,
            organization_id=organization_id,
            workspace_id=workspace_id,
            user_id=user_id,
            resource_type="workflow",
            resource_id=workflow_id,
            action="execute",
            outcome=outcome,
            event_data={
                "execution_id": execution_id,
                **(details or {})
            }
        )
        return self.log(entry)
    
    def log_policy_event(
        self,
        organization_id: str,
        policy_name: str,
        action: str,
        allowed: bool,
        context: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        workspace_id: Optional[str] = None
    ) -> Optional[AuditLog]:
        entry = AuditEntry(
            event_type=EventType.POLICY_EVALUATED if allowed else EventType.POLICY_BLOCKED,
            event_category=EventCategory.POLICY_VIOLATION if not allowed else EventCategory.SYSTEM,
            organization_id=organization_id,
            workspace_id=workspace_id,
            user_id=user_id,
            resource_type="policy",
            resource_id=policy_name,
            action=action,
            outcome=AuditOutcome.SUCCESS if allowed else AuditOutcome.BLOCKED,
            event_data={
                "policy_name": policy_name,
                "action_requested": action,
                "decision": "allowed" if allowed else "blocked",
                "context": context
            }
        )
        return self.log(entry)
    
    def query(
        self,
        organization_id: str,
        event_type: Optional[str] = None,
        event_category: Optional[str] = None,
        user_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        pii_detected: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[AuditLog]:
        query = self.db.query(AuditLog).filter(
            AuditLog.organization_id == organization_id
        )
        
        if event_type:
            query = query.filter(AuditLog.event_type == event_type)
        if event_category:
            query = query.filter(AuditLog.event_category == event_category)
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        if workspace_id:
            query = query.filter(AuditLog.workspace_id == workspace_id)
        if agent_id:
            query = query.filter(AuditLog.agent_id == agent_id)
        if resource_type:
            query = query.filter(AuditLog.resource_type == resource_type)
        if resource_id:
            query = query.filter(AuditLog.resource_id == resource_id)
        if start_date:
            query = query.filter(AuditLog.created_at >= start_date)
        if end_date:
            query = query.filter(AuditLog.created_at <= end_date)
        if pii_detected is not None:
            query = query.filter(AuditLog.pii_detected == pii_detected)
        
        return query.order_by(desc(AuditLog.created_at)).offset(offset).limit(limit).all()
    
    def count(
        self,
        organization_id: str,
        event_type: Optional[str] = None,
        event_category: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> int:
        query = self.db.query(AuditLog).filter(
            AuditLog.organization_id == organization_id
        )
        
        if event_type:
            query = query.filter(AuditLog.event_type == event_type)
        if event_category:
            query = query.filter(AuditLog.event_category == event_category)
        if start_date:
            query = query.filter(AuditLog.created_at >= start_date)
        if end_date:
            query = query.filter(AuditLog.created_at <= end_date)
        
        return query.count()
    
    def export_report(
        self,
        organization_id: str,
        start_date: datetime,
        end_date: datetime,
        format: str = "json"
    ) -> Dict[str, Any]:
        logs = self.query(
            organization_id=organization_id,
            start_date=start_date,
            end_date=end_date,
            limit=10000
        )
        
        summary = {
            "organization_id": organization_id,
            "report_period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "generated_at": datetime.utcnow().isoformat(),
            "total_events": len(logs),
            "events_by_category": {},
            "events_by_type": {},
            "pii_events": 0,
            "policy_violations": 0
        }
        
        for log in logs:
            category = log.event_category
            event_type = log.event_type
            
            summary["events_by_category"][category] = summary["events_by_category"].get(category, 0) + 1
            summary["events_by_type"][event_type] = summary["events_by_type"].get(event_type, 0) + 1
            
            if log.pii_detected:
                summary["pii_events"] += 1
            if log.event_category == EventCategory.POLICY_VIOLATION:
                summary["policy_violations"] += 1
        
        events = [
            {
                "id": log.id,
                "timestamp": log.created_at.isoformat(),
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
                "ip_address": log.ip_address
            }
            for log in logs
        ]
        
        return {
            "summary": summary,
            "events": events
        }
    
    def cleanup_old_logs(self, organization_id: str) -> int:
        config = self.get_compliance_config(organization_id)
        retention_days = config.audit_retention_days if config else 90
        
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        
        deleted = self.db.query(AuditLog).filter(
            and_(
                AuditLog.organization_id == organization_id,
                AuditLog.created_at < cutoff_date
            )
        ).delete()
        
        self.db.commit()
        logger.info(f"Cleaned up {deleted} audit logs older than {retention_days} days for org {organization_id}")
        return deleted
