"""
SSO Configuration Settings
Centralized configuration for SSO functionality
"""
from functools import lru_cache

from jarvisx.config.configs import (
    SSO_ENCRYPTION_KEY,
    API_BASE_URL,
    FRONTEND_BASE_URL,
    VOICE_CHAT_BASE_URL,
    SSO_REDIRECT_PATH_ADMIN,
    SSO_REDIRECT_PATH_VOICE,
    SSO_ERROR_PATH_ADMIN,
    SSO_ERROR_PATH_VOICE,
    SSO_STATE_TTL_SECONDS,
    SSO_USE_REDIS,
    REDIS_HOST,
    REDIS_PORT,
    REDIS_PASSWORD,
    REDIS_DB,
    REDIS_SSL,
    SSO_VERIFY_JWT_SIGNATURE,
    SSO_AUDIT_LOGGING_ENABLED,
    SSO_SESSION_TIMEOUT_HOURS,
)


class SSOSettings:
    """SSO-specific settings from centralized config"""

    def __init__(self):
        self.sso_encryption_key = SSO_ENCRYPTION_KEY
        self.api_base_url = API_BASE_URL
        self.frontend_base_url = FRONTEND_BASE_URL
        self.voice_chat_base_url = VOICE_CHAT_BASE_URL
        self.sso_redirect_path_admin = SSO_REDIRECT_PATH_ADMIN
        self.sso_redirect_path_voice = SSO_REDIRECT_PATH_VOICE
        self.sso_error_path_admin = SSO_ERROR_PATH_ADMIN
        self.sso_error_path_voice = SSO_ERROR_PATH_VOICE
        self.sso_state_ttl_seconds = SSO_STATE_TTL_SECONDS
        self.sso_use_redis = SSO_USE_REDIS
        self.redis_host = REDIS_HOST
        self.redis_port = REDIS_PORT
        self.redis_password = REDIS_PASSWORD
        self.redis_db = REDIS_DB
        self.redis_ssl = REDIS_SSL
        self.sso_verify_jwt_signature = SSO_VERIFY_JWT_SIGNATURE
        self.sso_audit_logging_enabled = SSO_AUDIT_LOGGING_ENABLED
        self.sso_session_timeout_hours = SSO_SESSION_TIMEOUT_HOURS


@lru_cache()
def get_sso_settings() -> SSOSettings:
    """Get cached SSO settings instance"""
    return SSOSettings()
