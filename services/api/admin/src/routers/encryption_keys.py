"""
Platform Admin API for Encryption Key Management
Allows platform administrators to generate and manage per-organization encryption keys
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
import logging

from jarvisx.database.models import EncryptionKey, Organization, User
from jarvisx.database.session import get_db
from services.api.admin.src.dependencies import get_current_user, require_platform_admin
from services.api.admin.src.utils.encryption import get_enhanced_encryption_service
from services.api.admin.src.utils.audit_logger import get_audit_logger
from services.api.admin.src.services.reencryption_service import get_reencryption_service

router = APIRouter(prefix="/api/admin/encryption-keys", tags=["admin", "encryption"])
logger = logging.getLogger(__name__)
audit_logger = get_audit_logger()


# ============================================================================
# Request/Response Models
# ============================================================================

class EncryptionKeyResponse(BaseModel):
    """Response model for encryption key (metadata only, never the actual key!)"""
    id: str
    organization_id: Optional[str]
    organization_name: Optional[str]
    key_name: str
    key_purpose: str
    key_version: int
    is_active: bool
    is_primary: bool
    created_by: Optional[str]
    created_at: datetime
    rotated_at: Optional[datetime]
    last_used_at: Optional[datetime]
    expires_at: Optional[datetime]

    class Config:
        from_attributes = True


class GenerateKeyRequest(BaseModel):
    """Request to generate new encryption key"""
    organization_id: str
    purpose: str = "sso"  # sso, data, backup


class RotateKeyRequest(BaseModel):
    """Request to rotate encryption key"""
    re_encrypt_data: bool = False  # Whether to re-encrypt existing data


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("/", response_model=List[EncryptionKeyResponse])
def list_encryption_keys(
    organization_id: Optional[str] = None,
    purpose: Optional[str] = None,
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_platform_admin),
):
    """
    List all encryption keys (metadata only, never actual keys)

    Platform admin only

    Args:
        organization_id: Filter by organization
        purpose: Filter by purpose (sso, data, backup)
        include_inactive: Include inactive keys
    """
    query = db.query(EncryptionKey)

    if organization_id:
        query = query.filter(EncryptionKey.organization_id == organization_id)

    if purpose:
        query = query.filter(EncryptionKey.key_purpose == purpose)

    if not include_inactive:
        query = query.filter(EncryptionKey.is_active == True)

    keys = query.order_by(
        EncryptionKey.organization_id,
        EncryptionKey.key_purpose,
        EncryptionKey.created_at.desc()
    ).all()

    # Enrich with organization names
    result = []
    for key in keys:
        org_name = None
        if key.organization_id:
            org = db.query(Organization).filter(Organization.id == key.organization_id).first()
            org_name = org.name if org else None

        result.append(EncryptionKeyResponse(
            id=key.id,
            organization_id=key.organization_id,
            organization_name=org_name,
            key_name=key.key_name,
            key_purpose=key.key_purpose,
            key_version=key.key_version,
            is_active=key.is_active,
            is_primary=key.is_primary,
            created_by=key.created_by,
            created_at=key.created_at,
            rotated_at=key.rotated_at,
            last_used_at=key.last_used_at,
            expires_at=key.expires_at,
        ))

    return result


@router.get("/{key_id}", response_model=EncryptionKeyResponse)
def get_encryption_key(
    key_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_platform_admin),
):
    """
    Get encryption key details (metadata only)

    Platform admin only
    """
    key = db.query(EncryptionKey).filter(EncryptionKey.id == key_id).first()

    if not key:
        raise HTTPException(status_code=404, detail="Encryption key not found")

    # Get organization name
    org_name = None
    if key.organization_id:
        org = db.query(Organization).filter(Organization.id == key.organization_id).first()
        org_name = org.name if org else None

    return EncryptionKeyResponse(
        id=key.id,
        organization_id=key.organization_id,
        organization_name=org_name,
        key_name=key.key_name,
        key_purpose=key.key_purpose,
        key_version=key.key_version,
        is_active=key.is_active,
        is_primary=key.is_primary,
        created_by=key.created_by,
        created_at=key.created_at,
        rotated_at=key.rotated_at,
        last_used_at=key.last_used_at,
        expires_at=key.expires_at,
    )


@router.post("/generate", response_model=EncryptionKeyResponse, status_code=status.HTTP_201_CREATED)
def generate_encryption_key(
    request: GenerateKeyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_platform_admin),
):
    """
    Generate new encryption key for organization

    Platform admin only

    This creates a new Fernet key, encrypts it with the master key,
    and stores it in the database.
    """
    # Validate organization exists
    org = db.query(Organization).filter(Organization.id == request.organization_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Validate purpose
    valid_purposes = ["sso", "data", "backup"]
    if request.purpose not in valid_purposes:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid purpose. Must be one of: {', '.join(valid_purposes)}"
        )

    encryption_service = get_enhanced_encryption_service()

    try:
        # Generate key
        key_id = encryption_service.generate_org_key(
            organization_id=request.organization_id,
            purpose=request.purpose,
            created_by=current_user.id,
            db=db
        )

        # Get the created key
        key = db.query(EncryptionKey).filter(EncryptionKey.id == key_id).first()

        # Audit log
        audit_logger.log_event(
            event_type="encryption_key.generated",
            user_id=current_user.id,
            organization_id=request.organization_id,
            details={
                "key_id": key_id,
                "purpose": request.purpose,
                "key_version": key.key_version
            },
            success=True
        )

        logger.info(
            f"Encryption key generated by {current_user.email}",
            extra={
                "organization_id": request.organization_id,
                "purpose": request.purpose,
                "key_id": key_id
            }
        )

        return EncryptionKeyResponse(
            id=key.id,
            organization_id=key.organization_id,
            organization_name=org.name,
            key_name=key.key_name,
            key_purpose=key.key_purpose,
            key_version=key.key_version,
            is_active=key.is_active,
            is_primary=key.is_primary,
            created_by=key.created_by,
            created_at=key.created_at,
            rotated_at=key.rotated_at,
            last_used_at=key.last_used_at,
            expires_at=key.expires_at,
        )

    except Exception as e:
        logger.error(f"Failed to generate encryption key: {e}")
        audit_logger.log_event(
            event_type="encryption_key.generation_failed",
            user_id=current_user.id,
            organization_id=request.organization_id,
            success=False,
            error_message=str(e)
        )
        raise HTTPException(status_code=500, detail=f"Failed to generate key: {str(e)}")


@router.post("/{key_id}/rotate", response_model=EncryptionKeyResponse)
def rotate_encryption_key(
    key_id: str,
    request: RotateKeyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_platform_admin),
):
    """
    Rotate encryption key

    Creates a new key version and marks the old one as inactive.

    Platform admin only

    Args:
        key_id: Current key ID to rotate
        request: Rotation options
    """
    old_key = db.query(EncryptionKey).filter(EncryptionKey.id == key_id).first()

    if not old_key:
        raise HTTPException(status_code=404, detail="Key not found")

    encryption_service = get_enhanced_encryption_service()

    try:
        # Generate new key
        new_key_id = encryption_service.generate_org_key(
            organization_id=old_key.organization_id,
            purpose=old_key.key_purpose,
            created_by=current_user.id,
            db=db
        )

        # Mark old key as rotated
        old_key.rotated_at = datetime.utcnow()
        db.commit()

        # Clear cache
        encryption_service.clear_cache()

        # Get new key
        new_key = db.query(EncryptionKey).filter(EncryptionKey.id == new_key_id).first()

        # Get organization name
        org_name = None
        if new_key.organization_id:
            org = db.query(Organization).filter(Organization.id == new_key.organization_id).first()
            org_name = org.name if org else None

        # Audit log
        audit_logger.log_event(
            event_type="encryption_key.rotated",
            user_id=current_user.id,
            organization_id=old_key.organization_id,
            details={
                "old_key_id": key_id,
                "new_key_id": new_key_id,
                "old_version": old_key.key_version,
                "new_version": new_key.key_version,
                "re_encrypt_data": request.re_encrypt_data
            },
            success=True
        )

        logger.info(
            f"Encryption key rotated by {current_user.email}",
            extra={
                "organization_id": old_key.organization_id,
                "old_key_id": key_id,
                "new_key_id": new_key_id
            }
        )

        # TODO: Optionally re-encrypt data with new key
        if request.re_encrypt_data:
            logger.warning("Data re-encryption requested but not yet implemented")
            # This would:
            # 1. Query all SSO configs for this organization
            # 2. Decrypt secrets with old key
            # 3. Re-encrypt with new key
            # 4. Update records
            pass

        return EncryptionKeyResponse(
            id=new_key.id,
            organization_id=new_key.organization_id,
            organization_name=org_name,
            key_name=new_key.key_name,
            key_purpose=new_key.key_purpose,
            key_version=new_key.key_version,
            is_active=new_key.is_active,
            is_primary=new_key.is_primary,
            created_by=new_key.created_by,
            created_at=new_key.created_at,
            rotated_at=new_key.rotated_at,
            last_used_at=new_key.last_used_at,
            expires_at=new_key.expires_at,
        )

    except Exception as e:
        logger.error(f"Failed to rotate encryption key: {e}")
        audit_logger.log_event(
            event_type="encryption_key.rotation_failed",
            user_id=current_user.id,
            organization_id=old_key.organization_id,
            success=False,
            error_message=str(e)
        )
        raise HTTPException(status_code=500, detail=f"Failed to rotate key: {str(e)}")


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_encryption_key(
    key_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_platform_admin),
):
    """
    Deactivate encryption key

    Note: Keys are never actually deleted, only deactivated.
    This ensures encrypted data can still be decrypted if needed.

    Platform admin only
    """
    key = db.query(EncryptionKey).filter(EncryptionKey.id == key_id).first()

    if not key:
        raise HTTPException(status_code=404, detail="Key not found")

    if key.is_primary:
        raise HTTPException(
            status_code=400,
            detail="Cannot deactivate primary key. Rotate it first."
        )

    key.is_active = False
    db.commit()

    # Audit log
    audit_logger.log_event(
        event_type="encryption_key.deactivated",
        user_id=current_user.id,
        organization_id=key.organization_id,
        details={"key_id": key_id},
        success=True
    )

    logger.info(
        f"Encryption key deactivated by {current_user.email}",
        extra={"key_id": key_id, "organization_id": key.organization_id}
    )

    return None


# ============================================================================
# Re-encryption Endpoints
# ============================================================================

class ReencryptionStatusResponse(BaseModel):
    """Response model for re-encryption status"""
    organization_id: str
    old_key_version: int
    sso_configs_remaining: int
    integrations_remaining: int
    total_remaining: int
    needs_reencryption: bool

    class Config:
        from_attributes = True


class ReencryptionResultResponse(BaseModel):
    """Response model for re-encryption result"""
    organization_id: str
    old_key_version: int
    new_key_version: int
    total_success: int
    total_errors: int
    sso_configs: dict
    integrations: dict
    completed_at: str

    class Config:
        from_attributes = True


@router.get("/reencryption/status/{organization_id}", response_model=ReencryptionStatusResponse)
def get_reencryption_status(
    organization_id: str,
    key_version: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_platform_admin),
):
    """
    Check re-encryption status for an organization

    Shows how many records still need to be re-encrypted from an old key version

    Platform admin only
    """
    reencryption_service = get_reencryption_service()

    try:
        status = reencryption_service.check_reencryption_status(
            organization_id=organization_id,
            key_version=key_version,
            db=db
        )

        return ReencryptionStatusResponse(**status)

    except Exception as e:
        logger.error(f"Failed to check re-encryption status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to check status: {str(e)}")


@router.post("/reencryption/run/{organization_id}", response_model=ReencryptionResultResponse)
def run_reencryption(
    organization_id: str,
    old_key_version: int,
    purpose: str = "sso",
    db: Session = Depends(get_db),
    current_user: User = Depends(require_platform_admin),
):
    """
    Run background re-encryption for an organization

    Re-encrypts all data from old key version to current primary key

    Platform admin only

    Warning: This can take time for large datasets. Consider running during off-peak hours.
    """
    # Validate organization exists
    org = db.query(Organization).filter(Organization.id == organization_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    reencryption_service = get_reencryption_service()

    try:
        logger.info(
            f"Re-encryption started by {current_user.email}",
            extra={
                "organization_id": organization_id,
                "old_key_version": old_key_version,
                "purpose": purpose
            }
        )

        # Run re-encryption
        result = reencryption_service.reencrypt_all_org_data(
            organization_id=organization_id,
            old_key_version=old_key_version,
            db=db,
            purpose=purpose
        )

        # Audit log
        audit_logger.log_event(
            event_type="encryption_key.reencryption_completed",
            user_id=current_user.id,
            organization_id=organization_id,
            details={
                "old_key_version": old_key_version,
                "new_key_version": result["new_key_version"],
                "total_success": result["total_success"],
                "total_errors": result["total_errors"]
            },
            success=result["total_errors"] == 0
        )

        return ReencryptionResultResponse(**result)

    except Exception as e:
        logger.error(f"Failed to run re-encryption: {e}")
        audit_logger.log_event(
            event_type="encryption_key.reencryption_failed",
            user_id=current_user.id,
            organization_id=organization_id,
            success=False,
            error_message=str(e)
        )
        raise HTTPException(status_code=500, detail=f"Re-encryption failed: {str(e)}")
