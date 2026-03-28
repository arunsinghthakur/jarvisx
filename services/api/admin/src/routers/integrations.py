import logging
import uuid
import base64
import hashlib
import json
import smtplib
import httpx
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from services.api.admin.src.dependencies import get_db, get_current_user
from services.api.admin.src.models.integrations import (
    IntegrationType,
    IntegrationCreate,
    IntegrationUpdate,
    IntegrationResponse,
    IntegrationListResponse,
    IntegrationTypeInfo,
    IntegrationTypesResponse,
)
from jarvisx.database.models import OrganizationIntegration, User
from jarvisx.config.configs import LLM_ENCRYPTION_KEY

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/organizations/{organization_id}/integrations", tags=["Integrations"])

SENSITIVE_FIELDS = {
    "email": ["smtp_password"],
    "slack": ["webhook_url"],
    "teams": ["webhook_url"],
}


def _encrypt_value(value: str) -> str:
    key = hashlib.sha256(LLM_ENCRYPTION_KEY.encode()).digest()[:32]
    value_bytes = value.encode()
    encrypted = bytes(a ^ b for a, b in zip(value_bytes, key * (len(value_bytes) // len(key) + 1)))
    return base64.b64encode(encrypted).decode()


def _decrypt_value(encrypted_value: str) -> str:
    key = hashlib.sha256(LLM_ENCRYPTION_KEY.encode()).digest()[:32]
    encrypted = base64.b64decode(encrypted_value.encode())
    decrypted = bytes(a ^ b for a, b in zip(encrypted, key * (len(encrypted) // len(key) + 1)))
    return decrypted.decode()


def _separate_config(integration_type: str, config: dict) -> tuple[dict, dict]:
    sensitive_keys = SENSITIVE_FIELDS.get(integration_type, [])
    config_plain = {}
    config_encrypted = {}
    
    for key, value in config.items():
        if key in sensitive_keys and value:
            config_encrypted[key] = _encrypt_value(value)
        else:
            config_plain[key] = value
    
    return config_plain, config_encrypted


def _to_response(integration: OrganizationIntegration) -> IntegrationResponse:
    config = integration.config or {}
    config_encrypted = integration.config_encrypted or {}
    
    display_config = {**config}
    for key in config_encrypted:
        display_config[key] = "••••••••"
    
    return IntegrationResponse(
        id=integration.id,
        organization_id=integration.organization_id,
        integration_type=integration.integration_type,
        name=integration.name,
        config=display_config,
        has_sensitive_config=bool(config_encrypted),
        is_default=integration.is_default,
        is_active=integration.is_active,
        created_at=integration.created_at,
        updated_at=integration.updated_at,
    )


INTEGRATION_TYPES = [
    IntegrationTypeInfo(
        id="email",
        name="Email (SMTP)",
        description="Configure SMTP settings for sending emails from workflows",
        config_fields=[
            {"name": "smtp_host", "label": "SMTP Host", "type": "text", "required": True, "placeholder": "smtp.gmail.com"},
            {"name": "smtp_port", "label": "SMTP Port", "type": "number", "required": False, "default": 587},
            {"name": "smtp_user", "label": "SMTP Username", "type": "text", "required": False, "placeholder": "your-email@gmail.com"},
            {"name": "smtp_password", "label": "SMTP Password", "type": "password", "required": False, "sensitive": True},
            {"name": "from_email", "label": "From Email", "type": "email", "required": True, "placeholder": "noreply@yourcompany.com"},
            {"name": "from_name", "label": "From Name", "type": "text", "required": False, "default": "JarvisX"},
            {"name": "use_tls", "label": "Use TLS", "type": "boolean", "required": False, "default": True},
        ],
    ),
    IntegrationTypeInfo(
        id="slack",
        name="Slack",
        description="Configure Slack webhook for sending notifications",
        config_fields=[
            {"name": "webhook_url", "label": "Webhook URL", "type": "password", "required": True, "sensitive": True, "placeholder": "https://hooks.slack.com/services/..."},
            {"name": "default_channel", "label": "Default Channel", "type": "text", "required": False, "placeholder": "#general"},
            {"name": "bot_name", "label": "Bot Name", "type": "text", "required": False, "default": "JarvisX"},
        ],
    ),
    IntegrationTypeInfo(
        id="teams",
        name="Microsoft Teams",
        description="Configure Microsoft Teams webhook for sending notifications",
        config_fields=[
            {"name": "webhook_url", "label": "Webhook URL", "type": "password", "required": True, "sensitive": True, "placeholder": "https://outlook.office.com/webhook/..."},
            {"name": "card_theme_color", "label": "Card Theme Color", "type": "text", "required": False, "default": "6366f1", "placeholder": "6366f1"},
        ],
    ),
]


@router.get("/types", response_model=IntegrationTypesResponse)
async def get_integration_types(
    current_user: User = Depends(get_current_user),
):
    return IntegrationTypesResponse(types=INTEGRATION_TYPES)


@router.get("", response_model=IntegrationListResponse)
async def list_integrations(
    organization_id: str,
    integration_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    query = db.query(OrganizationIntegration).filter(
        OrganizationIntegration.organization_id == organization_id
    )
    
    if integration_type:
        query = query.filter(OrganizationIntegration.integration_type == integration_type)
    
    integrations = query.order_by(OrganizationIntegration.created_at.desc()).all()
    
    return IntegrationListResponse(
        integrations=[_to_response(i) for i in integrations],
        total=len(integrations),
    )


@router.get("/{integration_id}", response_model=IntegrationResponse)
async def get_integration(
    organization_id: str,
    integration_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    integration = db.query(OrganizationIntegration).filter(
        OrganizationIntegration.id == integration_id,
        OrganizationIntegration.organization_id == organization_id,
    ).first()
    
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    return _to_response(integration)


@router.post("", response_model=IntegrationResponse, status_code=status.HTTP_201_CREATED)
async def create_integration(
    organization_id: str,
    integration_data: IntegrationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    existing = db.query(OrganizationIntegration).filter(
        OrganizationIntegration.organization_id == organization_id,
        OrganizationIntegration.name == integration_data.name,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Integration with this name already exists")
    
    if integration_data.is_default:
        db.query(OrganizationIntegration).filter(
            OrganizationIntegration.organization_id == organization_id,
            OrganizationIntegration.integration_type == integration_data.integration_type.value,
            OrganizationIntegration.is_default == True,
        ).update({"is_default": False})
    
    config_plain, config_encrypted = _separate_config(
        integration_data.integration_type.value,
        integration_data.config
    )
    
    integration = OrganizationIntegration(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        integration_type=integration_data.integration_type.value,
        name=integration_data.name,
        config=config_plain,
        config_encrypted=config_encrypted,
        is_default=integration_data.is_default,
        is_active=integration_data.is_active,
    )
    
    db.add(integration)
    db.commit()
    db.refresh(integration)
    
    logger.info(f"Created integration '{integration.name}' for organization {organization_id}")
    return _to_response(integration)


@router.put("/{integration_id}", response_model=IntegrationResponse)
async def update_integration(
    organization_id: str,
    integration_id: str,
    integration_data: IntegrationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    integration = db.query(OrganizationIntegration).filter(
        OrganizationIntegration.id == integration_id,
        OrganizationIntegration.organization_id == organization_id,
    ).first()
    
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    if integration_data.name and integration_data.name != integration.name:
        existing = db.query(OrganizationIntegration).filter(
            OrganizationIntegration.organization_id == organization_id,
            OrganizationIntegration.name == integration_data.name,
            OrganizationIntegration.id != integration_id,
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Integration with this name already exists")
    
    if integration_data.is_default:
        db.query(OrganizationIntegration).filter(
            OrganizationIntegration.organization_id == organization_id,
            OrganizationIntegration.integration_type == integration.integration_type,
            OrganizationIntegration.is_default == True,
            OrganizationIntegration.id != integration_id,
        ).update({"is_default": False})
    
    if integration_data.name is not None:
        integration.name = integration_data.name
    if integration_data.is_default is not None:
        integration.is_default = integration_data.is_default
    if integration_data.is_active is not None:
        integration.is_active = integration_data.is_active
    
    if integration_data.config is not None:
        current_config = integration.config or {}
        current_encrypted = integration.config_encrypted or {}
        
        sensitive_keys = SENSITIVE_FIELDS.get(integration.integration_type, [])
        
        for key, value in integration_data.config.items():
            if key in sensitive_keys:
                if value and value != "••••••••":
                    current_encrypted[key] = _encrypt_value(value)
            else:
                current_config[key] = value
        
        integration.config = current_config
        integration.config_encrypted = current_encrypted
    
    integration.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(integration)
    
    logger.info(f"Updated integration '{integration.name}' for organization {organization_id}")
    return _to_response(integration)


@router.delete("/{integration_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_integration(
    organization_id: str,
    integration_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    integration = db.query(OrganizationIntegration).filter(
        OrganizationIntegration.id == integration_id,
        OrganizationIntegration.organization_id == organization_id,
    ).first()
    
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    db.delete(integration)
    db.commit()
    
    logger.info(f"Deleted integration '{integration.name}' from organization {organization_id}")


@router.post("/{integration_id}/set-default", response_model=IntegrationResponse)
async def set_default_integration(
    organization_id: str,
    integration_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    integration = db.query(OrganizationIntegration).filter(
        OrganizationIntegration.id == integration_id,
        OrganizationIntegration.organization_id == organization_id,
    ).first()
    
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    db.query(OrganizationIntegration).filter(
        OrganizationIntegration.organization_id == organization_id,
        OrganizationIntegration.integration_type == integration.integration_type,
        OrganizationIntegration.is_default == True,
    ).update({"is_default": False})
    
    integration.is_default = True
    integration.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(integration)
    
    logger.info(f"Set integration '{integration.name}' as default for organization {organization_id}")
    return _to_response(integration)


@router.post("/{integration_id}/test")
async def test_integration(
    organization_id: str,
    integration_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    integration = db.query(OrganizationIntegration).filter(
        OrganizationIntegration.id == integration_id,
        OrganizationIntegration.organization_id == organization_id,
    ).first()
    
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    config = integration.config or {}
    config_encrypted = integration.config_encrypted or {}
    
    for key, value in config_encrypted.items():
        if value:
            config[key] = _decrypt_value(value)
    
    try:
        if integration.integration_type == "email":
            return await _test_email_integration(config)
        elif integration.integration_type == "slack":
            return await _test_slack_integration(config)
        elif integration.integration_type == "teams":
            return await _test_teams_integration(config)
        else:
            return {"success": False, "message": f"Unknown integration type: {integration.integration_type}"}
    except Exception as e:
        logger.error(f"Integration test failed: {e}")
        return {"success": False, "message": str(e)}


async def _test_email_integration(config: dict) -> dict:
    smtp_host = config.get("smtp_host")
    smtp_port = config.get("smtp_port", 587)
    smtp_user = config.get("smtp_user")
    smtp_password = config.get("smtp_password")
    use_tls = config.get("use_tls", True)
    
    if not smtp_host:
        return {"success": False, "message": "SMTP host is required"}
    
    try:
        if use_tls:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10)
        
        if smtp_user and smtp_password:
            server.login(smtp_user, smtp_password)
        
        server.quit()
        return {"success": True, "message": "SMTP connection successful"}
    except Exception as e:
        return {"success": False, "message": f"SMTP connection failed: {str(e)}"}


async def _test_slack_integration(config: dict) -> dict:
    webhook_url = config.get("webhook_url")
    
    if not webhook_url:
        return {"success": False, "message": "Webhook URL is required"}
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                webhook_url,
                json={"text": "JarvisX integration test - connection successful!"},
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                return {"success": True, "message": "Slack webhook test successful - check your channel for the test message"}
            else:
                return {"success": False, "message": f"Slack webhook returned status {response.status_code}: {response.text}"}
    except Exception as e:
        return {"success": False, "message": f"Slack webhook test failed: {str(e)}"}


async def _test_teams_integration(config: dict) -> dict:
    webhook_url = config.get("webhook_url")
    card_theme_color = config.get("card_theme_color", "6366f1")
    
    if not webhook_url:
        return {"success": False, "message": "Webhook URL is required"}
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            payload = {
                "@type": "MessageCard",
                "@context": "http://schema.org/extensions",
                "themeColor": card_theme_color,
                "summary": "JarvisX Integration Test",
                "sections": [{
                    "activityTitle": "JarvisX Integration Test",
                    "text": "Connection successful! Your Microsoft Teams integration is working.",
                    "markdown": True
                }]
            }
            
            response = await client.post(
                webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                return {"success": True, "message": "Teams webhook test successful - check your channel for the test message"}
            else:
                return {"success": False, "message": f"Teams webhook returned status {response.status_code}: {response.text}"}
    except Exception as e:
        return {"success": False, "message": f"Teams webhook test failed: {str(e)}"}
