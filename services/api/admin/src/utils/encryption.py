"""
Encryption utilities for sensitive data
Uses Fernet (symmetric encryption) for client secrets
"""
from cryptography.fernet import Fernet, InvalidToken
from typing import Optional
import logging

from services.api.admin.src.config.sso_settings import get_sso_settings

logger = logging.getLogger(__name__)


class EncryptionService:
    """Service for encrypting and decrypting sensitive data"""

    def __init__(self):
        settings = get_sso_settings()
        try:
            self._cipher = Fernet(settings.sso_encryption_key.encode())
        except Exception as e:
            logger.error(f"Failed to initialize encryption cipher: {e}")
            logger.warning("Using development fallback - DO NOT USE IN PRODUCTION")
            # Generate a new key for development
            self._cipher = Fernet(Fernet.generate_key())

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a plaintext string

        Args:
            plaintext: String to encrypt

        Returns:
            Base64 encoded encrypted string
        """
        if not plaintext:
            return ""

        try:
            encrypted_bytes = self._cipher.encrypt(plaintext.encode())
            return encrypted_bytes.decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise ValueError("Failed to encrypt data")

    def decrypt(self, encrypted: str) -> str:
        """
        Decrypt an encrypted string

        Args:
            encrypted: Base64 encoded encrypted string

        Returns:
            Decrypted plaintext string

        Raises:
            ValueError: If decryption fails
        """
        if not encrypted:
            return ""

        try:
            decrypted_bytes = self._cipher.decrypt(encrypted.encode())
            return decrypted_bytes.decode()
        except InvalidToken:
            logger.error("Invalid encryption token - data may be corrupted or key changed")
            raise ValueError("Failed to decrypt data - invalid token")
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise ValueError("Failed to decrypt data")


# Singleton instance
_encryption_service: Optional[EncryptionService] = None


def get_encryption_service() -> EncryptionService:
    """Get or create encryption service singleton"""
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service


def encrypt_secret(plaintext: str) -> str:
    """Convenience function to encrypt a secret"""
    return get_encryption_service().encrypt(plaintext)


def decrypt_secret(encrypted: str) -> str:
    """Convenience function to decrypt a secret"""
    return get_encryption_service().decrypt(encrypted)


# ============================================================================
# Enhanced Encryption Service (Per-Organization Keys)
# ============================================================================

class EnhancedEncryptionService:
    """
    Multi-tier encryption service with per-organization keys

    Architecture:
    - Master Key (ENV) encrypts Organization Keys
    - Organization Keys (DB) encrypt actual secrets
    - Provides better isolation and key rotation
    """

    def __init__(self, master_key: str):
        """
        Initialize with master key from environment

        Args:
            master_key: Base64-encoded Fernet key from ENV
        """
        try:
            self.master_cipher = Fernet(master_key.encode())
        except Exception as e:
            logger.error(f"Failed to initialize master cipher: {e}")
            raise ValueError("Invalid master encryption key")

        self._org_key_cache = {}  # Cache for decrypted org keys

    def encrypt_with_org_key(
        self,
        plaintext: str,
        organization_id: str,
        db: "Session",
        purpose: str = "sso"
    ) -> dict:
        """
        Encrypt data using organization-specific key (with version tracking)

        Args:
            plaintext: Data to encrypt
            organization_id: Organization ID
            db: Database session
            purpose: Key purpose (sso, data, backup)

        Returns:
            Dict with encrypted data and version info:
            {
                "ciphertext": "...",
                "key_version": 1,
                "key_id": "uuid..."
            }

        Raises:
            ValueError: If no key found or encryption fails
        """
        if not plaintext:
            return {"ciphertext": "", "key_version": None, "key_id": None}

        # Get organization key (decrypted) and metadata
        org_key, key_record = self._get_org_key_with_metadata(organization_id, purpose, db)

        # Encrypt with organization key
        org_cipher = Fernet(org_key.encode())
        encrypted = org_cipher.encrypt(plaintext.encode())

        # Update last_used_at
        self._update_key_usage(organization_id, purpose, db)

        return {
            "ciphertext": encrypted.decode(),
            "key_version": key_record.key_version,
            "key_id": key_record.id
        }

    def decrypt_with_org_key(
        self,
        encrypted: str,
        organization_id: str,
        db: "Session",
        purpose: str = "sso",
        key_version: int = None,
        key_id: str = None
    ) -> str:
        """
        Decrypt data using organization-specific key (version-aware)

        Args:
            encrypted: Base64 encoded encrypted data
            organization_id: Organization ID
            db: Database session
            purpose: Key purpose
            key_version: Specific key version to use (for old data)
            key_id: Specific key ID to use (for old data)

        Returns:
            Decrypted plaintext

        Raises:
            ValueError: If no key found or decryption fails
        """
        if not encrypted:
            return ""

        # Get organization key (decrypted)
        if key_version or key_id:
            # Decrypt with specific version (for old data)
            org_key = self._get_org_key_by_version(
                organization_id, purpose, db, key_version, key_id
            )
        else:
            # Decrypt with current primary key (backward compatibility)
            org_key, _ = self._get_org_key_with_metadata(organization_id, purpose, db)

        # Decrypt with organization key
        org_cipher = Fernet(org_key.encode())
        try:
            decrypted = org_cipher.decrypt(encrypted.encode())
            return decrypted.decode()
        except InvalidToken:
            logger.error(f"Failed to decrypt for org {organization_id} - invalid token")
            raise ValueError("Failed to decrypt data - invalid or corrupted")

    def _get_org_key(
        self,
        organization_id: str,
        purpose: str,
        db: "Session"
    ) -> str:
        """
        Get organization encryption key (decrypted) - backward compatibility

        Args:
            organization_id: Organization ID
            purpose: Key purpose
            db: Database session

        Returns:
            Decrypted Fernet key (base64 string)

        Raises:
            ValueError: If no key found
        """
        key, _ = self._get_org_key_with_metadata(organization_id, purpose, db)
        return key

    def _get_org_key_with_metadata(
        self,
        organization_id: str,
        purpose: str,
        db: "Session"
    ) -> tuple:
        """
        Get organization encryption key (decrypted) with metadata

        Uses cache to avoid repeated DB lookups and decryption

        Args:
            organization_id: Organization ID
            purpose: Key purpose
            db: Database session

        Returns:
            Tuple of (decrypted_key, key_record)

        Raises:
            ValueError: If no key found
        """
        cache_key = f"{organization_id}:{purpose}"

        # Check cache first (only for key, not metadata)
        cached_key = self._org_key_cache.get(cache_key)

        # Query from database
        from jarvisx.database.models import EncryptionKey

        key_record = db.query(EncryptionKey).filter(
            EncryptionKey.organization_id == organization_id,
            EncryptionKey.key_purpose == purpose,
            EncryptionKey.is_active == True,
            EncryptionKey.is_primary == True
        ).first()

        if not key_record:
            # Try to auto-generate key for organization
            logger.warning(
                f"No encryption key found for org {organization_id}, purpose {purpose}. "
                f"Auto-generating..."
            )
            key_id = self.generate_org_key(organization_id, purpose, "system", db)
            key_record = db.query(EncryptionKey).filter(EncryptionKey.id == key_id).first()

        if not key_record:
            raise ValueError(
                f"No encryption key found for org {organization_id}, purpose {purpose}"
            )

        # Use cached key if available, otherwise decrypt
        if cached_key:
            decrypted_key = cached_key
        else:
            # Decrypt with master key
            try:
                decrypted_key = self.master_cipher.decrypt(
                    key_record.encrypted_key.encode()
                ).decode()
            except InvalidToken:
                logger.error(f"Failed to decrypt org key - master key may have changed")
                raise ValueError("Failed to decrypt organization key")

            # Cache it
            self._org_key_cache[cache_key] = decrypted_key

        return decrypted_key, key_record

    def _get_org_key_by_version(
        self,
        organization_id: str,
        purpose: str,
        db: "Session",
        key_version: int = None,
        key_id: str = None
    ) -> str:
        """
        Get organization encryption key by specific version or ID

        Args:
            organization_id: Organization ID
            purpose: Key purpose
            db: Database session
            key_version: Specific version to retrieve
            key_id: Specific key ID to retrieve

        Returns:
            Decrypted Fernet key (base64 string)

        Raises:
            ValueError: If key not found
        """
        from jarvisx.database.models import EncryptionKey

        # Build query
        query = db.query(EncryptionKey).filter(
            EncryptionKey.organization_id == organization_id,
            EncryptionKey.key_purpose == purpose,
            EncryptionKey.is_active == True
        )

        if key_id:
            query = query.filter(EncryptionKey.id == key_id)
        elif key_version:
            query = query.filter(EncryptionKey.key_version == key_version)

        key_record = query.first()

        if not key_record:
            raise ValueError(
                f"No encryption key found for org {organization_id}, "
                f"purpose {purpose}, version {key_version}, id {key_id}"
            )

        # Decrypt with master key
        try:
            decrypted_key = self.master_cipher.decrypt(
                key_record.encrypted_key.encode()
            ).decode()
        except InvalidToken:
            logger.error(f"Failed to decrypt org key - master key may have changed")
            raise ValueError("Failed to decrypt organization key")

        return decrypted_key

    def generate_org_key(
        self,
        organization_id: str,
        purpose: str,
        created_by: str,
        db: "Session"
    ) -> str:
        """
        Generate new encryption key for organization

        Args:
            organization_id: Organization ID
            purpose: Key purpose (sso, data, backup)
            created_by: User ID who created the key
            db: Database session

        Returns:
            Key ID

        Raises:
            ValueError: If generation fails
        """
        from jarvisx.database.models import EncryptionKey
        from datetime import datetime
        import uuid

        # Generate new Fernet key
        new_key = Fernet.generate_key().decode()

        # Encrypt with master key
        encrypted_key = self.master_cipher.encrypt(new_key.encode()).decode()

        # Get current primary key to determine version
        old_key = db.query(EncryptionKey).filter(
            EncryptionKey.organization_id == organization_id,
            EncryptionKey.key_purpose == purpose,
            EncryptionKey.is_primary == True
        ).first()

        key_version = 1
        if old_key:
            old_key.is_primary = False
            # Keep old key ACTIVE for decryption of existing data
            # It will be deactivated after all data is re-encrypted
            key_version = old_key.key_version + 1

        # Create new key record
        key_record = EncryptionKey(
            id=str(uuid.uuid4()),
            organization_id=organization_id,
            key_name=f"{organization_id}_{purpose}_v{key_version}",
            key_purpose=purpose,
            encrypted_key=encrypted_key,
            key_version=key_version,
            is_active=True,
            is_primary=True,
            created_by=created_by,
            created_at=datetime.utcnow()
        )

        db.add(key_record)
        db.commit()
        db.refresh(key_record)

        # Clear cache
        cache_key = f"{organization_id}:{purpose}"
        if cache_key in self._org_key_cache:
            del self._org_key_cache[cache_key]

        logger.info(
            f"Generated encryption key for org {organization_id}, purpose {purpose}, version {key_version}"
        )

        return key_record.id

    def _update_key_usage(self, organization_id: str, purpose: str, db: "Session"):
        """Update last_used_at timestamp for key"""
        from jarvisx.database.models import EncryptionKey
        from datetime import datetime

        try:
            key_record = db.query(EncryptionKey).filter(
                EncryptionKey.organization_id == organization_id,
                EncryptionKey.key_purpose == purpose,
                EncryptionKey.is_primary == True
            ).first()

            if key_record:
                key_record.last_used_at = datetime.utcnow()
                db.commit()
        except Exception as e:
            logger.warning(f"Failed to update key usage: {e}")
            # Don't fail the encryption operation

    def clear_cache(self):
        """Clear the key cache (useful after key rotation)"""
        self._org_key_cache.clear()
        logger.info("Cleared encryption key cache")

    def decrypt_and_maybe_reencrypt(
        self,
        encrypted: str,
        organization_id: str,
        db: "Session",
        purpose: str = "sso",
        key_version: int = None,
        key_id: str = None,
        auto_reencrypt: bool = True
    ) -> dict:
        """
        Decrypt data and optionally re-encrypt with current key (lazy migration)

        This enables seamless key rotation:
        - Decrypts with the version that was used originally
        - Checks if it's an old version
        - Re-encrypts with current primary key if auto_reencrypt=True

        Args:
            encrypted: Encrypted ciphertext
            organization_id: Organization ID
            db: Database session
            purpose: Key purpose
            key_version: Original key version used to encrypt
            key_id: Original key ID used to encrypt
            auto_reencrypt: Whether to re-encrypt with current key if version is old

        Returns:
            Dict with:
            {
                "plaintext": "decrypted data",
                "reencrypted": bool,  # True if data was re-encrypted
                "new_ciphertext": "..." or None,
                "new_key_version": int or None,
                "new_key_id": str or None
            }

        Raises:
            ValueError: If decryption fails
        """
        if not encrypted:
            return {
                "plaintext": "",
                "reencrypted": False,
                "new_ciphertext": None,
                "new_key_version": None,
                "new_key_id": None
            }

        # Decrypt with the original key version
        plaintext = self.decrypt_with_org_key(
            encrypted=encrypted,
            organization_id=organization_id,
            db=db,
            purpose=purpose,
            key_version=key_version,
            key_id=key_id
        )

        # Check if we should re-encrypt
        if not auto_reencrypt:
            return {
                "plaintext": plaintext,
                "reencrypted": False,
                "new_ciphertext": None,
                "new_key_version": None,
                "new_key_id": None
            }

        # Get current primary key
        _, current_key_record = self._get_org_key_with_metadata(
            organization_id, purpose, db
        )

        # Check if this data was encrypted with an old key
        needs_reencryption = False
        if key_version and key_version < current_key_record.key_version:
            needs_reencryption = True
        elif key_id and key_id != current_key_record.id:
            needs_reencryption = True

        if not needs_reencryption:
            # Already using current key
            return {
                "plaintext": plaintext,
                "reencrypted": False,
                "new_ciphertext": None,
                "new_key_version": None,
                "new_key_id": None
            }

        # Re-encrypt with current key
        logger.info(
            f"Lazy re-encryption: org {organization_id}, purpose {purpose}, "
            f"old version {key_version} → new version {current_key_record.key_version}"
        )

        new_encrypted = self.encrypt_with_org_key(
            plaintext=plaintext,
            organization_id=organization_id,
            db=db,
            purpose=purpose
        )

        return {
            "plaintext": plaintext,
            "reencrypted": True,
            "new_ciphertext": new_encrypted["ciphertext"],
            "new_key_version": new_encrypted["key_version"],
            "new_key_id": new_encrypted["key_id"]
        }


# Singleton instances
_enhanced_encryption_service: Optional[EnhancedEncryptionService] = None


def get_enhanced_encryption_service() -> EnhancedEncryptionService:
    """Get or create enhanced encryption service singleton"""
    global _enhanced_encryption_service
    if _enhanced_encryption_service is None:
        settings = get_sso_settings()
        _enhanced_encryption_service = EnhancedEncryptionService(
            master_key=settings.sso_encryption_key
        )
    return _enhanced_encryption_service
