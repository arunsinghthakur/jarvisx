import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.orm import Session
from sqlalchemy import or_

from jarvisx.database.models import PolicyRule, ComplianceConfig

logger = logging.getLogger(__name__)


class PolicyRuleType(str, Enum):
    DATA_PROTECTION = "data_protection"
    ACCESS_CONTROL = "access_control"
    GOVERNANCE = "governance"
    RATE_LIMIT = "rate_limit"
    CONTENT_FILTER = "content_filter"
    WORKFLOW_VALIDATION = "workflow_validation"


class PolicyDecision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    WARN = "warn"
    REQUIRE_APPROVAL = "require_approval"


@dataclass
class PolicyEvaluationResult:
    allowed: bool
    decision: PolicyDecision
    rule_name: Optional[str]
    rule_type: Optional[str]
    reason: str
    recommendations: List[str]
    metadata: Dict[str, Any]


@dataclass
class PolicyContext:
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    user_id: Optional[str] = None
    workspace_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class PolicyService:
    def __init__(self, db: Session):
        self.db = db
        self._rule_cache: Dict[str, List[PolicyRule]] = {}
    
    def get_rules(self, organization_id: Optional[str] = None, rule_type: Optional[str] = None) -> List[PolicyRule]:
        cache_key = f"{organization_id or 'system'}:{rule_type or 'all'}"
        if cache_key in self._rule_cache:
            return self._rule_cache[cache_key]
        
        query = self.db.query(PolicyRule).filter(PolicyRule.is_active == True)
        
        if organization_id:
            query = query.filter(
                or_(
                    PolicyRule.is_system_rule == True,
                    PolicyRule.organization_id == organization_id
                )
            )
        else:
            query = query.filter(PolicyRule.is_system_rule == True)
        
        if rule_type:
            query = query.filter(PolicyRule.rule_type == rule_type)
        
        rules = query.order_by(PolicyRule.priority.desc()).all()
        self._rule_cache[cache_key] = rules
        return rules
    
    def get_compliance_config(self, organization_id: str) -> Optional[ComplianceConfig]:
        return self.db.query(ComplianceConfig).filter(
            ComplianceConfig.organization_id == organization_id
        ).first()
    
    def _is_enforcement_enabled(self, organization_id: str) -> bool:
        config = self.get_compliance_config(organization_id)
        return config is None or config.policy_enforcement_enabled
    
    def _evaluate_rate_limit_rule(self, rule: PolicyRule, context: PolicyContext) -> PolicyEvaluationResult:
        config = rule.rule_config
        return PolicyEvaluationResult(
            allowed=True,
            decision=PolicyDecision.ALLOW,
            rule_name=rule.name,
            rule_type=rule.rule_type,
            reason="Rate limit check passed (implementation requires request tracking)",
            recommendations=[],
            metadata={
                "max_requests": config.get("max_requests", 100),
                "window_seconds": config.get("window_seconds", 60)
            }
        )
    
    def _evaluate_data_protection_rule(self, rule: PolicyRule, context: PolicyContext) -> PolicyEvaluationResult:
        config = rule.rule_config
        action = config.get("action", "mask_pii")
        applies_to = config.get("applies_to", [])
        
        if context.resource_type and context.resource_type in applies_to:
            return PolicyEvaluationResult(
                allowed=True,
                decision=PolicyDecision.WARN,
                rule_name=rule.name,
                rule_type=rule.rule_type,
                reason=f"Data protection rule applies: {action}",
                recommendations=[f"Apply {action} before processing"],
                metadata={"action_required": action}
            )
        
        return PolicyEvaluationResult(
            allowed=True,
            decision=PolicyDecision.ALLOW,
            rule_name=rule.name,
            rule_type=rule.rule_type,
            reason="Data protection rule does not apply to this resource",
            recommendations=[],
            metadata={}
        )
    
    def _evaluate_access_control_rule(self, rule: PolicyRule, context: PolicyContext) -> PolicyEvaluationResult:
        config = rule.rule_config
        allowed_actions = config.get("allowed_actions", [])
        denied_actions = config.get("denied_actions", [])
        require_approval = config.get("require_approval", [])
        
        if context.action in denied_actions:
            return PolicyEvaluationResult(
                allowed=False,
                decision=PolicyDecision.DENY,
                rule_name=rule.name,
                rule_type=rule.rule_type,
                reason=f"Action '{context.action}' is explicitly denied by policy",
                recommendations=["Contact administrator for access"],
                metadata={"denied_action": context.action}
            )
        
        if context.action in require_approval:
            return PolicyEvaluationResult(
                allowed=False,
                decision=PolicyDecision.REQUIRE_APPROVAL,
                rule_name=rule.name,
                rule_type=rule.rule_type,
                reason=f"Action '{context.action}' requires approval",
                recommendations=["Submit approval request before proceeding"],
                metadata={"requires_approval": True}
            )
        
        if allowed_actions and context.action not in allowed_actions:
            return PolicyEvaluationResult(
                allowed=False,
                decision=PolicyDecision.DENY,
                rule_name=rule.name,
                rule_type=rule.rule_type,
                reason=f"Action '{context.action}' is not in allowed list",
                recommendations=[f"Allowed actions: {', '.join(allowed_actions)}"],
                metadata={"allowed_actions": allowed_actions}
            )
        
        return PolicyEvaluationResult(
            allowed=True,
            decision=PolicyDecision.ALLOW,
            rule_name=rule.name,
            rule_type=rule.rule_type,
            reason="Access control check passed",
            recommendations=[],
            metadata={}
        )
    
    def _evaluate_governance_rule(self, rule: PolicyRule, context: PolicyContext) -> PolicyEvaluationResult:
        config = rule.rule_config
        return PolicyEvaluationResult(
            allowed=True,
            decision=PolicyDecision.ALLOW,
            rule_name=rule.name,
            rule_type=rule.rule_type,
            reason="Governance rule noted",
            recommendations=[],
            metadata={
                "retention_days": config.get("retention_days"),
                "applies_to": config.get("applies_to", [])
            }
        )
    
    def _evaluate_content_filter_rule(self, rule: PolicyRule, context: PolicyContext) -> PolicyEvaluationResult:
        config = rule.rule_config
        blocked_keywords = config.get("blocked_keywords", [])
        
        if context.data:
            data_str = str(context.data).lower()
            for keyword in blocked_keywords:
                if keyword.lower() in data_str:
                    return PolicyEvaluationResult(
                        allowed=False,
                        decision=PolicyDecision.DENY,
                        rule_name=rule.name,
                        rule_type=rule.rule_type,
                        reason=f"Content contains blocked keyword",
                        recommendations=["Remove or modify blocked content"],
                        metadata={"blocked_keyword_found": True}
                    )
        
        return PolicyEvaluationResult(
            allowed=True,
            decision=PolicyDecision.ALLOW,
            rule_name=rule.name,
            rule_type=rule.rule_type,
            reason="Content filter check passed",
            recommendations=[],
            metadata={}
        )
    
    def _evaluate_workflow_validation_rule(self, rule: PolicyRule, context: PolicyContext) -> PolicyEvaluationResult:
        config = rule.rule_config
        max_nodes = config.get("max_nodes")
        allowed_node_types = config.get("allowed_node_types", [])
        
        if context.data and context.resource_type == "workflow":
            nodes = context.data.get("nodes", [])
            
            if max_nodes and len(nodes) > max_nodes:
                return PolicyEvaluationResult(
                    allowed=False,
                    decision=PolicyDecision.DENY,
                    rule_name=rule.name,
                    rule_type=rule.rule_type,
                    reason=f"Workflow exceeds maximum nodes ({max_nodes})",
                    recommendations=[f"Reduce workflow to {max_nodes} nodes or fewer"],
                    metadata={"node_count": len(nodes), "max_allowed": max_nodes}
                )
            
            if allowed_node_types:
                for node in nodes:
                    node_type = node.get("type")
                    if node_type and node_type not in allowed_node_types:
                        return PolicyEvaluationResult(
                            allowed=False,
                            decision=PolicyDecision.DENY,
                            rule_name=rule.name,
                            rule_type=rule.rule_type,
                            reason=f"Workflow contains disallowed node type: {node_type}",
                            recommendations=[f"Allowed node types: {', '.join(allowed_node_types)}"],
                            metadata={"disallowed_node_type": node_type}
                        )
        
        return PolicyEvaluationResult(
            allowed=True,
            decision=PolicyDecision.ALLOW,
            rule_name=rule.name,
            rule_type=rule.rule_type,
            reason="Workflow validation passed",
            recommendations=[],
            metadata={}
        )
    
    def evaluate(
        self,
        organization_id: str,
        context: PolicyContext
    ) -> PolicyEvaluationResult:
        if not self._is_enforcement_enabled(organization_id):
            return PolicyEvaluationResult(
                allowed=True,
                decision=PolicyDecision.ALLOW,
                rule_name=None,
                rule_type=None,
                reason="Policy enforcement is disabled for this organization",
                recommendations=[],
                metadata={"enforcement_disabled": True}
            )
        
        rules = self.get_rules(organization_id)
        
        for rule in rules:
            result = self._evaluate_single_rule(rule, context)
            
            if not result.allowed or result.decision in [PolicyDecision.DENY, PolicyDecision.REQUIRE_APPROVAL]:
                return result
        
        return PolicyEvaluationResult(
            allowed=True,
            decision=PolicyDecision.ALLOW,
            rule_name=None,
            rule_type=None,
            reason="All policy checks passed",
            recommendations=[],
            metadata={"rules_evaluated": len(rules)}
        )
    
    def _evaluate_single_rule(self, rule: PolicyRule, context: PolicyContext) -> PolicyEvaluationResult:
        evaluators = {
            PolicyRuleType.RATE_LIMIT: self._evaluate_rate_limit_rule,
            PolicyRuleType.DATA_PROTECTION: self._evaluate_data_protection_rule,
            PolicyRuleType.ACCESS_CONTROL: self._evaluate_access_control_rule,
            PolicyRuleType.GOVERNANCE: self._evaluate_governance_rule,
            PolicyRuleType.CONTENT_FILTER: self._evaluate_content_filter_rule,
            PolicyRuleType.WORKFLOW_VALIDATION: self._evaluate_workflow_validation_rule,
        }
        
        evaluator = evaluators.get(rule.rule_type)
        if evaluator:
            try:
                return evaluator(rule, context)
            except Exception as e:
                logger.error(f"Error evaluating rule {rule.name}: {e}")
                return PolicyEvaluationResult(
                    allowed=True,
                    decision=PolicyDecision.ALLOW,
                    rule_name=rule.name,
                    rule_type=rule.rule_type,
                    reason=f"Rule evaluation error: {str(e)}",
                    recommendations=[],
                    metadata={"error": str(e)}
                )
        
        return PolicyEvaluationResult(
            allowed=True,
            decision=PolicyDecision.ALLOW,
            rule_name=rule.name,
            rule_type=rule.rule_type,
            reason=f"Unknown rule type: {rule.rule_type}",
            recommendations=[],
            metadata={}
        )
    
    def check_policy(
        self,
        organization_id: str,
        action: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        user_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        context = PolicyContext(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            user_id=user_id,
            data=data
        )
        
        result = self.evaluate(organization_id, context)
        
        return {
            "allowed": result.allowed,
            "decision": result.decision,
            "rule_name": result.rule_name,
            "reason": result.reason,
            "recommendations": result.recommendations
        }
    
    def validate_request(
        self,
        organization_id: str,
        request_type: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        context = PolicyContext(
            action=request_type,
            resource_type=request_type,
            data=data
        )
        
        result = self.evaluate(organization_id, context)
        
        return {
            "valid": result.allowed,
            "decision": result.decision,
            "violations": [] if result.allowed else [result.reason],
            "recommendations": result.recommendations
        }
    
    def list_applicable_policies(
        self,
        organization_id: str,
        action: Optional[str] = None,
        resource_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        rules = self.get_rules(organization_id)
        
        return [
            {
                "id": rule.id,
                "name": rule.name,
                "description": rule.description,
                "type": rule.rule_type,
                "priority": rule.priority,
                "is_system_rule": rule.is_system_rule,
                "config": rule.rule_config
            }
            for rule in rules
        ]
    
    def explain_policy_decision(
        self,
        organization_id: str,
        action: str,
        context_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        context = PolicyContext(
            action=action,
            data=context_data
        )
        
        rules = self.get_rules(organization_id)
        evaluations = []
        
        for rule in rules:
            result = self._evaluate_single_rule(rule, context)
            evaluations.append({
                "rule_name": rule.name,
                "rule_type": rule.rule_type,
                "priority": rule.priority,
                "decision": result.decision,
                "reason": result.reason
            })
        
        final_result = self.evaluate(organization_id, context)
        
        return {
            "action": action,
            "final_decision": final_result.decision,
            "allowed": final_result.allowed,
            "reason": final_result.reason,
            "rule_evaluations": evaluations,
            "recommendations": final_result.recommendations
        }
    
    def clear_cache(self):
        self._rule_cache.clear()
