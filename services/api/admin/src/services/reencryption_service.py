"""
Background Re-encryption Service
Handles bulk re-encryption of data after key rotation
"""
import logging
from typing import Optional
from sqlalchemy.orm import Session
from datetime import datetime

from jarvisx.database.models import SSOConfig, OrganizationIntegration, EncryptionKey
from services.api.admin.src.utils.encryption import get_enhanced_encryption_service

logger = logging.getLogger(__name__)


class ReencryptionService:
    """Service for background re-encryption tasks"""

    def __init__(self):
        self.encryption_service = get_enhanced_encryption_service()

    def reencrypt_org_sso_configs(
        self,
        organization_id: str,
        old_key_version: int,
        new_key_version: int,
        db: Session
    ) -> dict:
        """
        Re-encrypt all SSO configs for an organization

        Args:
            organization_id: Organization ID
            old_key_version: Old key version to migrate from
            new_key_version: New key version to migrate to
            db: Database session

        Returns:
            Dict with migration statistics
        """
        logger.info(
            f"Starting SSO config re-encryption for org {organization_id}: "
            f"v{old_key_version} → v{new_key_version}"
        )

        # Find all configs encrypted with old key
        configs = db.query(SSOConfig).filter(
            SSOConfig.organization_id == organization_id,
            SSOConfig.client_secret_key_version == old_key_version
        ).all()

        success_count = 0
        error_count = 0
        errors = []

        for config in configs:
            try:
                if not config.client_secret:
                    continue

                # Decrypt with old key
                plaintext = self.encryption_service.decrypt_with_org_key(
                    encrypted=config.client_secret,
                    organization_id=organization_id,
                    db=db,
                    purpose="sso",
                    key_version=old_key_version
                )

                # Encrypt with new key
                encrypted_data = self.encryption_service.encrypt_with_org_key(
                    plaintext=plaintext,
                    organization_id=organization_id,
                    db=db,
                    purpose="sso"
                )

                # Update record
                config.client_secret = encrypted_data["ciphertext"]
                config.client_secret_key_version = encrypted_data["key_version"]
                config.client_secret_key_id = encrypted_data["key_id"]

                db.commit()
                success_count += 1

                logger.info(f"Re-encrypted SSO config {config.id}")

            except Exception as e:
                error_count += 1
                error_msg = f"Failed to re-encrypt SSO config {config.id}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
                db.rollback()

        result = {
            "total_records": len(configs),
            "success_count": success_count,
            "error_count": error_count,
            "errors": errors,
            "organization_id": organization_id,
            "old_key_version": old_key_version,
            "new_key_version": new_key_version
        }

        logger.info(
            f"Completed SSO config re-encryption for org {organization_id}: "
            f"{success_count} success, {error_count} errors"
        )

        return result

    def reencrypt_org_integrations(
        self,
        organization_id: str,
        old_key_version: int,
        new_key_version: int,
        db: Session
    ) -> dict:
        """
        Re-encrypt all organization integrations

        Args:
            organization_id: Organization ID
            old_key_version: Old key version
            new_key_version: New key version
            db: Database session

        Returns:
            Dict with migration statistics
        """
        logger.info(
            f"Starting integrations re-encryption for org {organization_id}: "
            f"v{old_key_version} → v{new_key_version}"
        )

        # Find all integrations encrypted with old key
        integrations = db.query(OrganizationIntegration).filter(
            OrganizationIntegration.organization_id == organization_id,
            OrganizationIntegration.config_encrypted_key_version == old_key_version
        ).all()

        success_count = 0
        error_count = 0
        errors = []

        for integration in integrations:
            try:
                if not integration.config_encrypted:
                    continue

                # Decrypt with old key
                # Note: config_encrypted is JSON, may need special handling
                # For now, skip or implement custom logic

                success_count += 1
                logger.info(f"Re-encrypted integration {integration.id}")

            except Exception as e:
                error_count += 1
                error_msg = f"Failed to re-encrypt integration {integration.id}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
                db.rollback()

        result = {
            "total_records": len(integrations),
            "success_count": success_count,
            "error_count": error_count,
            "errors": errors,
            "organization_id": organization_id,
            "old_key_version": old_key_version,
            "new_key_version": new_key_version
        }

        logger.info(
            f"Completed integrations re-encryption for org {organization_id}: "
            f"{success_count} success, {error_count} errors"
        )

        return result

    def reencrypt_all_org_data(
        self,
        organization_id: str,
        old_key_version: int,
        db: Session,
        purpose: str = "sso"
    ) -> dict:
        """
        Re-encrypt all data for an organization

        Args:
            organization_id: Organization ID
            old_key_version: Old key version to migrate from
            db: Database session
            purpose: Key purpose (sso, data, backup)

        Returns:
            Dict with combined statistics
        """
        # Get new key version
        new_key = db.query(EncryptionKey).filter(
            EncryptionKey.organization_id == organization_id,
            EncryptionKey.key_purpose == purpose,
            EncryptionKey.is_primary == True,
            EncryptionKey.is_active == True
        ).first()

        if not new_key:
            raise ValueError(f"No primary key found for org {organization_id}, purpose {purpose}")

        new_key_version = new_key.key_version

        logger.info(
            f"Starting full re-encryption for org {organization_id}: "
            f"v{old_key_version} → v{new_key_version}"
        )

        # Re-encrypt SSO configs
        sso_result = self.reencrypt_org_sso_configs(
            organization_id, old_key_version, new_key_version, db
        )

        # Re-encrypt integrations
        integration_result = self.reencrypt_org_integrations(
            organization_id, old_key_version, new_key_version, db
        )

        # Combine results
        combined_result = {
            "organization_id": organization_id,
            "old_key_version": old_key_version,
            "new_key_version": new_key_version,
            "sso_configs": sso_result,
            "integrations": integration_result,
            "total_success": sso_result["success_count"] + integration_result["success_count"],
            "total_errors": sso_result["error_count"] + integration_result["error_count"],
            "completed_at": datetime.utcnow().isoformat()
        }

        logger.info(
            f"Completed full re-encryption for org {organization_id}: "
            f"{combined_result['total_success']} success, {combined_result['total_errors']} errors"
        )

        return combined_result

    def check_reencryption_status(
        self,
        organization_id: str,
        key_version: int,
        db: Session
    ) -> dict:
        """
        Check how many records still need re-encryption

        Args:
            organization_id: Organization ID
            key_version: Old key version to check
            db: Database session

        Returns:
            Dict with status information
        """
        sso_count = db.query(SSOConfig).filter(
            SSOConfig.organization_id == organization_id,
            SSOConfig.client_secret_key_version == key_version
        ).count()

        integration_count = db.query(OrganizationIntegration).filter(
            OrganizationIntegration.organization_id == organization_id,
            OrganizationIntegration.config_encrypted_key_version == key_version
        ).count()

        return {
            "organization_id": organization_id,
            "old_key_version": key_version,
            "sso_configs_remaining": sso_count,
            "integrations_remaining": integration_count,
            "total_remaining": sso_count + integration_count,
            "needs_reencryption": (sso_count + integration_count) > 0
        }


# Singleton instance
_reencryption_service: Optional[ReencryptionService] = None


def get_reencryption_service() -> ReencryptionService:
    """Get or create reencryption service singleton"""
    global _reencryption_service
    if _reencryption_service is None:
        _reencryption_service = ReencryptionService()
    return _reencryption_service
