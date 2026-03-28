"""
SSO Configuration Management API
Handles CRUD operations for organization SSO configurations
"""
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from typing import List
import uuid
from datetime import datetime
import logging

from jarvisx.database.models import SSOConfig, Organization, User, Team
from jarvisx.database.session import get_db
from services.api.admin.src.models.sso import (
    SSOConfigCreate,
    SSOConfigUpdate,
    SSOConfigResponse,
    SSOConfigResponseWithSecret,
    SSOMetadataResponse,
)
from services.api.admin.src.services.saml_handler import saml_handler
from services.api.admin.src.dependencies import get_current_user, require_admin
from services.api.admin.src.utils.encryption import encrypt_secret, decrypt_secret, get_enhanced_encryption_service
from services.api.admin.src.utils.audit_logger import get_audit_logger, AuditEvent
from services.api.admin.src.config.sso_settings import get_sso_settings

router = APIRouter(prefix="/api/sso", tags=["sso"])
logger = logging.getLogger(__name__)
audit_logger = get_audit_logger()
settings = get_sso_settings()


def _encrypt_client_secret(client_secret: str, organization_id: str, db: Session) -> dict:
    """Encrypt client secret for storage using organization-specific key (with versioning)"""
    try:
        enhanced_encryption = get_enhanced_encryption_service()
        return enhanced_encryption.encrypt_with_org_key(
            plaintext=client_secret,
            organization_id=organization_id,
            db=db,
            purpose="sso"
        )
    except Exception as e:
        logger.error(f"Failed to encrypt client secret: {e}")
        raise HTTPException(status_code=500, detail="Failed to encrypt secret")


def _decrypt_client_secret(
    encrypted_secret: str,
    organization_id: str,
    db: Session,
    key_version: int = None,
    key_id: str = None,
    auto_reencrypt: bool = False
) -> dict:
    """
    Decrypt client secret using organization-specific key (with lazy re-encryption)

    Returns dict with plaintext and optionally new encrypted data if re-encrypted
    """
    try:
        enhanced_encryption = get_enhanced_encryption_service()

        if auto_reencrypt:
            # Use lazy re-encryption
            return enhanced_encryption.decrypt_and_maybe_reencrypt(
                encrypted=encrypted_secret,
                organization_id=organization_id,
                db=db,
                purpose="sso",
                key_version=key_version,
                key_id=key_id,
                auto_reencrypt=True
            )
        else:
            # Just decrypt
            plaintext = enhanced_encryption.decrypt_with_org_key(
                encrypted=encrypted_secret,
                organization_id=organization_id,
                db=db,
                purpose="sso",
                key_version=key_version,
                key_id=key_id
            )
            return {
                "plaintext": plaintext,
                "reencrypted": False,
                "new_ciphertext": None,
                "new_key_version": None,
                "new_key_id": None
            }
    except Exception as e:
        logger.error(f"Failed to decrypt client secret: {e}")
        raise HTTPException(status_code=500, detail="Failed to decrypt secret")


@router.get("/configs", response_model=List[SSOConfigResponse])
def list_sso_configs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all SSO configurations for the current user's organization
    """
    configs = (
        db.query(SSOConfig)
        .filter(SSOConfig.organization_id == current_user.organization_id)
        .all()
    )
    
    result = []
    for config in configs:
        config_dict = {
            "id": config.id,
            "organization_id": config.organization_id,
            "provider": config.provider,
            "is_enabled": config.is_enabled,
            "client_id": config.client_id,
            "tenant_id": config.tenant_id,
            "idp_entity_id": config.idp_entity_id,
            "idp_sso_url": config.idp_sso_url,
            "idp_x509_cert": config.idp_x509_cert,
            "sp_entity_id": config.sp_entity_id,
            "provider_config": config.provider_config,
            "allowed_domains": config.allowed_domains,
            "auto_provision_users": config.auto_provision_users,
            "default_team_id": config.default_team_id,
            "default_team_name": None,
            "created_at": config.created_at,
            "updated_at": config.updated_at,
        }
        
        if config.default_team_id:
            team = db.query(Team).filter(Team.id == config.default_team_id).first()
            if team:
                config_dict["default_team_name"] = team.name
        
        result.append(config_dict)
    
    return result


@router.get("/configs/{config_id}", response_model=SSOConfigResponse)
def get_sso_config(
    config_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a specific SSO configuration
    """
    config = db.query(SSOConfig).filter(SSOConfig.id == config_id).first()

    if not config:
        raise HTTPException(status_code=404, detail="SSO configuration not found")

    if config.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")

    return config


@router.get("/configs/{config_id}/with-secret", response_model=SSOConfigResponseWithSecret)
def get_sso_config_with_secret(
    config_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Get SSO configuration including client secret (admin only)
    """
    config = db.query(SSOConfig).filter(SSOConfig.id == config_id).first()

    if not config:
        raise HTTPException(status_code=404, detail="SSO configuration not found")

    if config.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Decrypt secret before returning (with lazy re-encryption)
    if config.client_secret:
        result = _decrypt_client_secret(
            encrypted_secret=config.client_secret,
            organization_id=config.organization_id,
            db=db,
            key_version=config.client_secret_key_version,
            key_id=config.client_secret_key_id,
            auto_reencrypt=True  # Enable lazy re-encryption
        )
        config.client_secret = result["plaintext"]

        # If data was re-encrypted, update the record
        if result["reencrypted"]:
            config.client_secret = result["new_ciphertext"]
            config.client_secret_key_version = result["new_key_version"]
            config.client_secret_key_id = result["new_key_id"]
            db.commit()
            logger.info(f"Lazy re-encrypted SSO config {config.id} from old key to version {result['new_key_version']}")
            # Return decrypted value for display
            config.client_secret = result["plaintext"]

    return config


@router.post("/configs", response_model=SSOConfigResponse, status_code=status.HTTP_201_CREATED)
def create_sso_config(
    config_data: SSOConfigCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Create a new SSO configuration (admin only)
    """
    # Check if configuration for this provider already exists
    existing = (
        db.query(SSOConfig)
        .filter(
            SSOConfig.organization_id == current_user.organization_id,
            SSOConfig.provider == config_data.provider,
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"SSO configuration for provider '{config_data.provider}' already exists",
        )

    # Validate required fields based on provider
    if config_data.provider in ["google", "microsoft", "okta"]:
        if not config_data.client_id or not config_data.client_secret:
            raise HTTPException(
                status_code=400,
                detail="client_id and client_secret are required for OAuth providers",
            )
        if config_data.provider == "microsoft" and not config_data.tenant_id:
            raise HTTPException(
                status_code=400,
                detail="tenant_id is required for Microsoft provider",
            )

    elif config_data.provider == "saml":
        if not config_data.idp_entity_id or not config_data.idp_sso_url or not config_data.idp_x509_cert:
            raise HTTPException(
                status_code=400,
                detail="idp_entity_id, idp_sso_url, and idp_x509_cert are required for SAML",
            )

    if config_data.auto_provision_users:
        if not config_data.default_team_id:
            raise HTTPException(
                status_code=400,
                detail="default_team_id is required when auto_provision_users is enabled",
            )
        team = db.query(Team).filter(
            Team.id == config_data.default_team_id,
            Team.organization_id == current_user.organization_id,
        ).first()
        if not team:
            raise HTTPException(
                status_code=400,
                detail="Invalid default_team_id: Team not found in this organization",
            )

    # Encrypt client secret (versioned)
    client_secret = None
    client_secret_key_version = None
    client_secret_key_id = None
    if config_data.client_secret:
        encrypted_data = _encrypt_client_secret(config_data.client_secret, current_user.organization_id, db)
        client_secret = encrypted_data["ciphertext"]
        client_secret_key_version = encrypted_data["key_version"]
        client_secret_key_id = encrypted_data["key_id"]

    # Create configuration
    new_config = SSOConfig(
        id=str(uuid.uuid4()),
        organization_id=current_user.organization_id,
        provider=config_data.provider,
        is_enabled=config_data.is_enabled,
        client_id=config_data.client_id,
        client_secret=client_secret,
        client_secret_key_version=client_secret_key_version,
        client_secret_key_id=client_secret_key_id,
        tenant_id=config_data.tenant_id,
        idp_entity_id=config_data.idp_entity_id,
        idp_sso_url=config_data.idp_sso_url,
        idp_x509_cert=config_data.idp_x509_cert,
        sp_entity_id=config_data.sp_entity_id,
        provider_config=config_data.provider_config or {},
        allowed_domains=config_data.allowed_domains or [],
        auto_provision_users=config_data.auto_provision_users,
        default_team_id=config_data.default_team_id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db.add(new_config)
    db.commit()
    db.refresh(new_config)

    # Audit log
    audit_logger.log_config_change(
        event_type=AuditEvent.SSO_CONFIG_CREATED,
        config_id=new_config.id,
        organization_id=current_user.organization_id,
        provider=new_config.provider,
        admin_user_id=current_user.id,
    )

    return new_config


@router.put("/configs/{config_id}", response_model=SSOConfigResponse)
def update_sso_config(
    config_id: str,
    config_data: SSOConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Update an existing SSO configuration (admin only)
    """
    config = db.query(SSOConfig).filter(SSOConfig.id == config_id).first()

    if not config:
        raise HTTPException(status_code=404, detail="SSO configuration not found")

    if config.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Update fields
    update_data = config_data.model_dump(exclude_unset=True)

    # Validate default_team_id if auto_provision_users is being set or already enabled
    auto_provision = update_data.get("auto_provision_users", config.auto_provision_users)
    new_team_id = update_data.get("default_team_id", config.default_team_id)
    
    if auto_provision and not new_team_id:
        raise HTTPException(
            status_code=400,
            detail="default_team_id is required when auto_provision_users is enabled",
        )
    
    if "default_team_id" in update_data and update_data["default_team_id"]:
        team = db.query(Team).filter(
            Team.id == update_data["default_team_id"],
            Team.organization_id == current_user.organization_id,
        ).first()
        if not team:
            raise HTTPException(
                status_code=400,
                detail="Invalid default_team_id: Team not found in this organization",
            )

    # Encrypt client secret if provided (versioned), or remove from update if empty
    if "client_secret" in update_data:
        if update_data["client_secret"]:
            encrypted_data = _encrypt_client_secret(update_data["client_secret"], config.organization_id, db)
            update_data["client_secret"] = encrypted_data["ciphertext"]
            update_data["client_secret_key_version"] = encrypted_data["key_version"]
            update_data["client_secret_key_id"] = encrypted_data["key_id"]
        else:
            del update_data["client_secret"]

    for key, value in update_data.items():
        setattr(config, key, value)

    config.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(config)

    # Audit log
    audit_logger.log_config_change(
        event_type=AuditEvent.SSO_CONFIG_UPDATED,
        config_id=config.id,
        organization_id=current_user.organization_id,
        provider=config.provider,
        admin_user_id=current_user.id,
        changes=update_data,
    )

    return config


@router.delete("/configs/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sso_config(
    config_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Delete an SSO configuration (admin only)
    """
    config = db.query(SSOConfig).filter(SSOConfig.id == config_id).first()

    if not config:
        raise HTTPException(status_code=404, detail="SSO configuration not found")

    if config.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Audit log before deletion
    audit_logger.log_config_change(
        event_type=AuditEvent.SSO_CONFIG_DELETED,
        config_id=config.id,
        organization_id=current_user.organization_id,
        provider=config.provider,
        admin_user_id=current_user.id,
    )

    db.delete(config)
    db.commit()

    return None


@router.post("/configs/{config_id}/toggle", response_model=SSOConfigResponse)
def toggle_sso_config(
    config_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Toggle SSO configuration enabled/disabled state (admin only)
    """
    config = db.query(SSOConfig).filter(SSOConfig.id == config_id).first()

    if not config:
        raise HTTPException(status_code=404, detail="SSO configuration not found")

    if config.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")

    config.is_enabled = not config.is_enabled
    config.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(config)

    # Audit log
    audit_logger.log_config_change(
        event_type=AuditEvent.SSO_CONFIG_TOGGLED,
        config_id=config.id,
        organization_id=current_user.organization_id,
        provider=config.provider,
        admin_user_id=current_user.id,
        changes={"is_enabled": config.is_enabled},
    )

    return config


@router.get("/saml/metadata/{config_id}", response_model=SSOMetadataResponse)
def get_saml_metadata(
    config_id: str,
    idp_initiated: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get SAML Service Provider metadata XML for configuration

    Args:
        config_id: SSO configuration ID
        idp_initiated: If true, generates metadata for IdP-initiated flow (uses org slug URL)

    Returns:
        SAML metadata XML with entity ID and ACS URL
    """
    config = db.query(SSOConfig).filter(SSOConfig.id == config_id).first()

    if not config:
        raise HTTPException(status_code=404, detail="SSO configuration not found")

    if config.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")

    if config.provider != "saml":
        raise HTTPException(
            status_code=400,
            detail="Metadata is only available for SAML configurations",
        )

    # Get organization for slug
    org = db.query(Organization).filter(Organization.id == config.organization_id).first()

    if idp_initiated:
        # IdP-initiated flow: use organization slug in URL
        if not org or not org.slug:
            raise HTTPException(
                status_code=400,
                detail="Organization slug required for IdP-initiated flow. Run migration 004 to add slugs."
            )
        acs_url = f"{settings.api_base_url}/api/auth/sso/saml/idp/{org.slug}"
        entity_id = config.sp_entity_id or f"{settings.api_base_url}/saml/sp/idp/{org.slug}"
    else:
        # SP-initiated flow: use config ID in URL
        acs_url = f"{settings.api_base_url}/api/auth/sso/saml/acs/{config_id}"
        entity_id = config.sp_entity_id or f"{settings.api_base_url}/saml/sp/{config_id}"

    try:
        metadata_xml = saml_handler.get_metadata(config, acs_url, entity_id)
        return SSOMetadataResponse(
            metadata_xml=metadata_xml,
            entity_id=entity_id,
            acs_url=acs_url,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate metadata: {str(e)}")
