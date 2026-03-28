from __future__ import annotations

import logging
import base64
import hashlib
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from jarvisx.config.configs import LLM_ENCRYPTION_KEY
from jarvisx.database.session import get_engine

logger = logging.getLogger(__name__)


@dataclass
class EmailConfig:
    name: str
    smtp_host: str
    smtp_port: int
    smtp_user: Optional[str]
    smtp_password: Optional[str]
    from_email: str
    from_name: str
    use_tls: bool
    is_default: bool


@dataclass
class SlackConfig:
    name: str
    webhook_url: str
    default_channel: Optional[str]
    bot_name: Optional[str]
    is_default: bool


@dataclass
class TeamsConfig:
    name: str
    webhook_url: str
    card_theme_color: Optional[str]
    is_default: bool


class IntegrationNotFoundError(Exception):
    pass


def _decrypt_value(encrypted_value: Optional[str]) -> Optional[str]:
    if not encrypted_value:
        return None
    try:
        key = hashlib.sha256(LLM_ENCRYPTION_KEY.encode()).digest()[:32]
        encrypted = base64.b64decode(encrypted_value.encode())
        decrypted = bytes(a ^ b for a, b in zip(encrypted, key * (len(encrypted) // len(key) + 1)))
        return decrypted.decode()
    except Exception as e:
        logger.warning(f"Failed to decrypt value: {e}")
        return None


def _get_integration_from_db(
    organization_id: str,
    integration_type: str,
    get_default: bool = False,
) -> Optional[dict]:
    if not organization_id:
        return None
    
    try:
        engine = get_engine()
        with engine.connect() as conn:
            query_parts = [
                "SELECT * FROM organization_integrations",
                "WHERE is_active = true",
                "AND organization_id = :organization_id",
                "AND integration_type = :integration_type",
            ]
            params = {
                "organization_id": organization_id,
                "integration_type": integration_type,
            }
            
            if get_default:
                query_parts.append("AND is_default = true")
            
            query_parts.append("ORDER BY is_default DESC, created_at ASC LIMIT 1")
            
            query = " ".join(query_parts)
            result = conn.execute(text(query), params).fetchone()
            
            if result:
                config = result.config or {}
                config_encrypted = result.config_encrypted or {}
                
                decrypted_config = {}
                for key, value in config_encrypted.items():
                    if value:
                        decrypted_config[key] = _decrypt_value(value)
                
                return {
                    "id": result.id,
                    "name": result.name,
                    "integration_type": result.integration_type,
                    "is_default": result.is_default,
                    "config": {**config, **decrypted_config},
                }
    except SQLAlchemyError as e:
        logger.warning(f"Failed to fetch integration from database: {e}")
    
    return None


def get_integration_by_id(integration_id: str) -> Optional[dict]:
    if not integration_id:
        return None
    
    try:
        engine = get_engine()
        with engine.connect() as conn:
            query = "SELECT * FROM organization_integrations WHERE id = :integration_id AND is_active = true"
            result = conn.execute(text(query), {"integration_id": integration_id}).fetchone()
            
            if result:
                config = result.config or {}
                config_encrypted = result.config_encrypted or {}
                
                decrypted_config = {}
                for key, value in config_encrypted.items():
                    if value:
                        decrypted_config[key] = _decrypt_value(value)
                
                return {
                    "id": result.id,
                    "name": result.name,
                    "integration_type": result.integration_type,
                    "is_default": result.is_default,
                    "config": {**config, **decrypted_config},
                }
    except SQLAlchemyError as e:
        logger.warning(f"Failed to fetch integration by ID: {e}")
    
    return None


def _integration_to_email_config(integration: dict) -> EmailConfig:
    config = integration["config"]
    return EmailConfig(
        name=integration["name"],
        smtp_host=config.get("smtp_host", ""),
        smtp_port=config.get("smtp_port", 587),
        smtp_user=config.get("smtp_user"),
        smtp_password=config.get("smtp_password"),
        from_email=config.get("from_email", ""),
        from_name=config.get("from_name", ""),
        use_tls=config.get("use_tls", True),
        is_default=integration["is_default"],
    )


def _integration_to_slack_config(integration: dict) -> SlackConfig:
    config = integration["config"]
    return SlackConfig(
        name=integration["name"],
        webhook_url=config.get("webhook_url", ""),
        default_channel=config.get("default_channel"),
        bot_name=config.get("bot_name"),
        is_default=integration["is_default"],
    )


def _integration_to_teams_config(integration: dict) -> TeamsConfig:
    config = integration["config"]
    return TeamsConfig(
        name=integration["name"],
        webhook_url=config.get("webhook_url", ""),
        card_theme_color=config.get("card_theme_color"),
        is_default=integration["is_default"],
    )


def get_email_config(organization_id: str, email_config_id: Optional[str] = None) -> EmailConfig:
    if not organization_id:
        raise IntegrationNotFoundError(
            "Organization ID is required. Please provide a valid organization context."
        )
    
    if email_config_id:
        integration = get_integration_by_id(email_config_id)
        if integration and integration["integration_type"] == "email":
            return _integration_to_email_config(integration)
        logger.warning(f"Email config ID {email_config_id} not found, falling back to org defaults")
    
    integration = _get_integration_from_db(organization_id, "email", get_default=True)
    if not integration:
        integration = _get_integration_from_db(organization_id, "email")
    
    if integration:
        return _integration_to_email_config(integration)
    
    logger.error(f"No email config found for organization {organization_id}")
    raise IntegrationNotFoundError(
        f"Organization {organization_id} must configure Email/SMTP settings before sending emails. "
        "Please add an Email configuration in the Settings page."
    )


def get_slack_config(organization_id: str, slack_config_id: Optional[str] = None) -> SlackConfig:
    if not organization_id:
        raise IntegrationNotFoundError(
            "Organization ID is required. Please provide a valid organization context."
        )
    
    if slack_config_id:
        integration = get_integration_by_id(slack_config_id)
        if integration and integration["integration_type"] == "slack":
            return _integration_to_slack_config(integration)
        logger.warning(f"Slack config ID {slack_config_id} not found, falling back to org defaults")
    
    integration = _get_integration_from_db(organization_id, "slack", get_default=True)
    if not integration:
        integration = _get_integration_from_db(organization_id, "slack")
    
    if integration:
        return _integration_to_slack_config(integration)
    
    logger.error(f"No Slack config found for organization {organization_id}")
    raise IntegrationNotFoundError(
        f"Organization {organization_id} must configure Slack settings before sending notifications. "
        "Please add a Slack configuration in the Settings page."
    )


def get_teams_config(organization_id: str, teams_config_id: Optional[str] = None) -> TeamsConfig:
    if not organization_id:
        raise IntegrationNotFoundError(
            "Organization ID is required. Please provide a valid organization context."
        )
    
    if teams_config_id:
        integration = get_integration_by_id(teams_config_id)
        if integration and integration["integration_type"] == "teams":
            return _integration_to_teams_config(integration)
        logger.warning(f"Teams config ID {teams_config_id} not found, falling back to org defaults")
    
    integration = _get_integration_from_db(organization_id, "teams", get_default=True)
    if not integration:
        integration = _get_integration_from_db(organization_id, "teams")
    
    if integration:
        return _integration_to_teams_config(integration)
    
    logger.error(f"No Teams config found for organization {organization_id}")
    raise IntegrationNotFoundError(
        f"Organization {organization_id} must configure Microsoft Teams settings before sending notifications. "
        "Please add a Teams configuration in the Settings page."
    )
