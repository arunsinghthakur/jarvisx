"""
Audit logging for security events
Logs SSO authentication attempts, configuration changes, and security events
"""
import logging
from datetime import datetime
from typing import Optional, Dict, Any

from services.api.admin.src.config.sso_settings import get_sso_settings

logger = logging.getLogger(__name__)


class AuditEvent:
    """Audit event types"""
    SSO_LOGIN_INITIATED = "sso.login.initiated"
    SSO_LOGIN_SUCCESS = "sso.login.success"
    SSO_LOGIN_FAILED = "sso.login.failed"
    SSO_CONFIG_CREATED = "sso.config.created"
    SSO_CONFIG_UPDATED = "sso.config.updated"
    SSO_CONFIG_DELETED = "sso.config.deleted"
    SSO_CONFIG_TOGGLED = "sso.config.toggled"
    SSO_USER_PROVISIONED = "sso.user.provisioned"
    SSO_DOMAIN_REJECTED = "sso.domain.rejected"
    SSO_STATE_INVALID = "sso.state.invalid"
    SSO_TOKEN_EXCHANGE_FAILED = "sso.token.exchange_failed"


class AuditLogger:
    """Centralized audit logging service"""

    def __init__(self):
        self.settings = get_sso_settings()
        self.enabled = self.settings.sso_audit_logging_enabled

    def log_event(
        self,
        event_type: str,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        email: Optional[str] = None,
        provider: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None,
    ):
        """
        Log an audit event

        Args:
            event_type: Type of event (use AuditEvent constants)
            user_id: User ID if available
            organization_id: Organization ID
            email: User email
            provider: SSO provider
            ip_address: Client IP address
            user_agent: Client user agent
            details: Additional event details
            success: Whether the event was successful
            error_message: Error message if failed
        """
        if not self.enabled:
            return

        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "success": success,
            "user_id": user_id,
            "organization_id": organization_id,
            "email": email,
            "provider": provider,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "details": details or {},
            "error_message": error_message,
        }

        # Log to structured logger (can be sent to ELK, Splunk, CloudWatch, etc.)
        if success:
            logger.info(f"AUDIT: {event_type}", extra=log_entry)
        else:
            logger.warning(f"AUDIT: {event_type} FAILED", extra=log_entry)

    def log_sso_login_initiated(
        self,
        organization_id: str,
        provider: str,
        ip_address: Optional[str] = None,
    ):
        """Log SSO login initiation"""
        self.log_event(
            event_type=AuditEvent.SSO_LOGIN_INITIATED,
            organization_id=organization_id,
            provider=provider,
            ip_address=ip_address,
        )

    def log_sso_login_success(
        self,
        user_id: str,
        organization_id: str,
        email: str,
        provider: str,
        was_provisioned: bool = False,
        ip_address: Optional[str] = None,
    ):
        """Log successful SSO login"""
        self.log_event(
            event_type=AuditEvent.SSO_LOGIN_SUCCESS,
            user_id=user_id,
            organization_id=organization_id,
            email=email,
            provider=provider,
            ip_address=ip_address,
            details={"was_provisioned": was_provisioned},
            success=True,
        )

    def log_sso_login_failed(
        self,
        organization_id: str,
        provider: str,
        email: Optional[str] = None,
        error_message: str = "",
        ip_address: Optional[str] = None,
    ):
        """Log failed SSO login"""
        self.log_event(
            event_type=AuditEvent.SSO_LOGIN_FAILED,
            organization_id=organization_id,
            email=email,
            provider=provider,
            ip_address=ip_address,
            success=False,
            error_message=error_message,
        )

    def log_config_change(
        self,
        event_type: str,
        config_id: str,
        organization_id: str,
        provider: str,
        admin_user_id: str,
        changes: Optional[Dict[str, Any]] = None,
    ):
        """Log SSO configuration changes"""
        self.log_event(
            event_type=event_type,
            user_id=admin_user_id,
            organization_id=organization_id,
            provider=provider,
            details={
                "config_id": config_id,
                "changes": changes or {},
            },
        )


# Singleton instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get or create audit logger singleton"""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger
