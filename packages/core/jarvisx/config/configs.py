import os
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _get_bool(name: str, default: bool = True) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() == "true"


def _get_list(name: str, default: str = "") -> list[str]:
    raw = os.getenv(name, default)
    return [p.strip() for p in raw.split(",") if p.strip()] if raw else []


# ---------------------------------------------------------------------------
# Tier 1: Infrastructure -- read once at startup from .env
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DatabaseConfig:
    host: str
    port: str
    user: str
    password: str
    db: str
    schema: str
    url_async: str
    url_sync: str

    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        host = os.getenv("POSTGRES_HOST", "localhost")
        port = os.getenv("POSTGRES_PORT", "5434")
        user = os.getenv("POSTGRES_USER", "postgres")
        password = os.getenv("POSTGRES_PASSWORD", "postgres")
        db = os.getenv("POSTGRES_DB", "jarvisx")
        schema = os.getenv("POSTGRES_SCHEMA", "jarvisx")
        return cls(
            host=host, port=port, user=user, password=password, db=db, schema=schema,
            url_async=f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}",
            url_sync=f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}?options=-csearch_path%3D{schema}",
        )


@dataclass(frozen=True)
class PortsConfig:
    voice_chat: int
    admin_api: int
    admin_ui: int
    voice_gateway: int
    api_base_url: str
    frontend_base_url: str
    voice_chat_base_url: str
    chatbot_base_url: str

    @classmethod
    def from_env(cls) -> "PortsConfig":
        vc = int(os.getenv("UI_REACT_VOICE_CHAT_PORT", "5001"))
        aa = int(os.getenv("ADMIN_API_PORT", "5002"))
        au = int(os.getenv("ADMIN_UI_PORT", "5003"))
        vg = _get_int("VOICE_GATEWAY_PORT", 9003)
        return cls(
            voice_chat=vc, admin_api=aa, admin_ui=au, voice_gateway=vg,
            api_base_url=os.getenv("API_BASE_URL", f"http://localhost:{aa}"),
            frontend_base_url=os.getenv("FRONTEND_BASE_URL", f"http://localhost:{au}"),
            voice_chat_base_url=os.getenv("VOICE_CHAT_BASE_URL", f"http://localhost:{vc}"),
            chatbot_base_url=os.getenv("CHATBOT_BASE_URL", f"http://localhost:{vc}"),
        )


@dataclass(frozen=True)
class SecretsConfig:
    tavily_api_key: Optional[str]
    llm_encryption_key: str
    sso_encryption_key: str

    @classmethod
    def from_env(cls) -> "SecretsConfig":
        return cls(
            tavily_api_key=os.getenv("TAVILY_API_KEY"),
            llm_encryption_key=os.getenv("LLM_ENCRYPTION_KEY", os.getenv("JWT_SECRET_KEY", "jarvisx-secret-key-change-in-production")),
            sso_encryption_key=os.getenv("SSO_ENCRYPTION_KEY", "gAAAAABl1234567890abcdefghijklmnopqrstuvwxyzABCDEFGH="),
        )


@dataclass(frozen=True)
class SmtpConfig:
    host: str
    port: int
    user: str
    password: str
    from_email: str
    from_name: str
    use_tls: bool
    otp_expiry_minutes: int
    otp_max_attempts: int

    @classmethod
    def from_env(cls) -> "SmtpConfig":
        return cls(
            host=os.getenv("SMTP_HOST", ""),
            port=_get_int("SMTP_PORT", 587),
            user=os.getenv("SMTP_USER", ""),
            password=os.getenv("SMTP_PASSWORD", ""),
            from_email=os.getenv("SMTP_FROM_EMAIL", "noreply@jarvisx.ai"),
            from_name=os.getenv("SMTP_FROM_NAME", "JarvisX"),
            use_tls=_get_bool("SMTP_USE_TLS", True),
            otp_expiry_minutes=_get_int("OTP_EXPIRY_MINUTES", 15),
            otp_max_attempts=_get_int("OTP_MAX_ATTEMPTS", 3),
        )


@dataclass(frozen=True)
class AuthConfig:
    cookie_domain: Optional[str]
    secure_cookies: bool
    access_token_max_age: int
    refresh_token_max_age: int
    csrf_token_max_age: int
    cookie_samesite_access: str
    cookie_samesite_refresh: str
    cookie_samesite_csrf: str

    @classmethod
    def from_env(cls) -> "AuthConfig":
        return cls(
            cookie_domain=os.getenv("COOKIE_DOMAIN", None),
            secure_cookies=_get_bool("SECURE_COOKIES", False),
            access_token_max_age=_get_int("ACCESS_TOKEN_MAX_AGE", 30 * 60),
            refresh_token_max_age=_get_int("REFRESH_TOKEN_MAX_AGE", 7 * 24 * 60 * 60),
            csrf_token_max_age=_get_int("CSRF_TOKEN_MAX_AGE", 24 * 60 * 60),
            cookie_samesite_access=os.getenv("COOKIE_SAMESITE_ACCESS", "lax"),
            cookie_samesite_refresh=os.getenv("COOKIE_SAMESITE_REFRESH", "strict"),
            cookie_samesite_csrf=os.getenv("COOKIE_SAMESITE_CSRF", "strict"),
        )


@dataclass(frozen=True)
class SSOEnvConfig:
    redirect_path_admin: str
    redirect_path_voice: str
    error_path_admin: str
    error_path_voice: str
    state_ttl_seconds: int
    use_redis: bool
    verify_jwt_signature: bool
    audit_logging_enabled: bool
    session_timeout_hours: int

    @classmethod
    def from_env(cls) -> "SSOEnvConfig":
        return cls(
            redirect_path_admin=os.getenv("SSO_REDIRECT_PATH_ADMIN", "/dashboard"),
            redirect_path_voice=os.getenv("SSO_REDIRECT_PATH_VOICE", "/"),
            error_path_admin=os.getenv("SSO_ERROR_PATH_ADMIN", "/login"),
            error_path_voice=os.getenv("SSO_ERROR_PATH_VOICE", "/"),
            state_ttl_seconds=_get_int("SSO_STATE_TTL_SECONDS", 600),
            use_redis=_get_bool("SSO_USE_REDIS", False),
            verify_jwt_signature=_get_bool("SSO_VERIFY_JWT_SIGNATURE", True),
            audit_logging_enabled=_get_bool("SSO_AUDIT_LOGGING_ENABLED", True),
            session_timeout_hours=_get_int("SSO_SESSION_TIMEOUT_HOURS", 24),
        )


@dataclass(frozen=True)
class RedisConfig:
    host: str
    port: int
    password: Optional[str]
    db: int
    ssl: bool

    @classmethod
    def from_env(cls) -> "RedisConfig":
        return cls(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=_get_int("REDIS_PORT", 6379),
            password=os.getenv("REDIS_PASSWORD", None),
            db=_get_int("REDIS_DB", 0),
            ssl=_get_bool("REDIS_SSL", False),
        )


@dataclass(frozen=True)
class LangfuseConfig:
    host: str
    public_key: str
    secret_key: str
    enabled: bool
    sample_rate: float
    trace_llm: bool
    trace_api: bool
    trace_workflows: bool
    llm_input_limit: int
    llm_output_limit: int
    api_traced_prefixes: tuple
    postgres_host: str
    postgres_port: str
    postgres_user: str
    postgres_password: str
    postgres_db: str

    @classmethod
    def from_env(cls) -> "LangfuseConfig":
        prefixes = _get_list("LANGFUSE_API_TRACED_PREFIXES")
        return cls(
            host=os.getenv("LANGFUSE_BASE_URL", os.getenv("LANGFUSE_HOST", "http://localhost:3100")),
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY", ""),
            secret_key=os.getenv("LANGFUSE_SECRET_KEY", ""),
            enabled=_get_bool("LANGFUSE_ENABLED", True),
            sample_rate=float(os.getenv("LANGFUSE_SAMPLE_RATE", "0.1")),
            trace_llm=_get_bool("LANGFUSE_TRACE_LLM", False),
            trace_api=_get_bool("LANGFUSE_TRACE_API", False),
            trace_workflows=_get_bool("LANGFUSE_TRACE_WORKFLOWS", True),
            llm_input_limit=_get_int("LANGFUSE_LLM_INPUT_LIMIT", 500),
            llm_output_limit=_get_int("LANGFUSE_LLM_OUTPUT_LIMIT", 500),
            api_traced_prefixes=tuple(prefixes),
            postgres_host=os.getenv("LANGFUSE_POSTGRES_HOST", "localhost"),
            postgres_port=os.getenv("LANGFUSE_POSTGRES_PORT", "5435"),
            postgres_user=os.getenv("LANGFUSE_POSTGRES_USER", "langfuse"),
            postgres_password=os.getenv("LANGFUSE_POSTGRES_PASSWORD", "langfuse"),
            postgres_db=os.getenv("LANGFUSE_POSTGRES_DB", "langfuse"),
        )


@dataclass(frozen=True)
class CacheConfig:
    agent_card_ttl: int
    mcp_ttl: int
    workspace_base_path: str

    @classmethod
    def from_env(cls) -> "CacheConfig":
        return cls(
            agent_card_ttl=_get_int("AGENT_CARD_CACHE_TTL", 14_400),
            mcp_ttl=_get_int("MCP_CACHE_TTL", 14_400),
            workspace_base_path=os.getenv("WORKSPACE_BASE_PATH", os.path.expanduser("~/.jarvisx/workspaces")),
        )


# ---------------------------------------------------------------------------
# Instantiate config groups
# ---------------------------------------------------------------------------

_db = DatabaseConfig.from_env()
_ports = PortsConfig.from_env()
_secrets = SecretsConfig.from_env()
_smtp = SmtpConfig.from_env()
_auth = AuthConfig.from_env()
_sso_env = SSOEnvConfig.from_env()
_redis = RedisConfig.from_env()
_langfuse = LangfuseConfig.from_env()
_cache = CacheConfig.from_env()

# ---------------------------------------------------------------------------
# Backward-compatible module-level aliases
# All 24 importing files continue to work with zero changes.
# ---------------------------------------------------------------------------

# Database
POSTGRES_HOST = _db.host
POSTGRES_PORT = _db.port
POSTGRES_USER = _db.user
POSTGRES_PASSWORD = _db.password
POSTGRES_DB = _db.db
POSTGRES_SCHEMA = _db.schema
BASE_DB_URL_ASYNC = _db.url_async
BASE_DB_URL_SYNC = _db.url_sync

# Ports & URLs
UI_REACT_VOICE_CHAT_PORT = _ports.voice_chat
ADMIN_API_PORT = _ports.admin_api
ADMIN_UI_PORT = _ports.admin_ui
VOICE_GATEWAY_PORT = _ports.voice_gateway
API_BASE_URL = _ports.api_base_url
FRONTEND_BASE_URL = _ports.frontend_base_url
VOICE_CHAT_BASE_URL = _ports.voice_chat_base_url
CHATBOT_BASE_URL = _ports.chatbot_base_url

# Secrets
TAVILY_API_KEY = _secrets.tavily_api_key
LLM_ENCRYPTION_KEY = _secrets.llm_encryption_key
SSO_ENCRYPTION_KEY = _secrets.sso_encryption_key

# SMTP / OTP
SMTP_HOST = _smtp.host
SMTP_PORT = _smtp.port
SMTP_USER = _smtp.user
SMTP_PASSWORD = _smtp.password
SMTP_FROM_EMAIL = _smtp.from_email
SMTP_FROM_NAME = _smtp.from_name
SMTP_USE_TLS = _smtp.use_tls
OTP_EXPIRY_MINUTES = _smtp.otp_expiry_minutes
OTP_MAX_ATTEMPTS = _smtp.otp_max_attempts

# Auth / Cookies
COOKIE_DOMAIN = _auth.cookie_domain
SECURE_COOKIES = _auth.secure_cookies
ACCESS_TOKEN_MAX_AGE = _auth.access_token_max_age
REFRESH_TOKEN_MAX_AGE = _auth.refresh_token_max_age
CSRF_TOKEN_MAX_AGE = _auth.csrf_token_max_age
COOKIE_SAMESITE_ACCESS = _auth.cookie_samesite_access
COOKIE_SAMESITE_REFRESH = _auth.cookie_samesite_refresh
COOKIE_SAMESITE_CSRF = _auth.cookie_samesite_csrf

# SSO
SSO_REDIRECT_PATH_ADMIN = _sso_env.redirect_path_admin
SSO_REDIRECT_PATH_VOICE = _sso_env.redirect_path_voice
SSO_ERROR_PATH_ADMIN = _sso_env.error_path_admin
SSO_ERROR_PATH_VOICE = _sso_env.error_path_voice
SSO_STATE_TTL_SECONDS = _sso_env.state_ttl_seconds
SSO_USE_REDIS = _sso_env.use_redis
SSO_VERIFY_JWT_SIGNATURE = _sso_env.verify_jwt_signature
SSO_AUDIT_LOGGING_ENABLED = _sso_env.audit_logging_enabled
SSO_SESSION_TIMEOUT_HOURS = _sso_env.session_timeout_hours

# Redis
REDIS_HOST = _redis.host
REDIS_PORT = _redis.port
REDIS_PASSWORD = _redis.password
REDIS_DB = _redis.db
REDIS_SSL = _redis.ssl

# Langfuse
LANGFUSE_HOST = _langfuse.host
LANGFUSE_PUBLIC_KEY = _langfuse.public_key
LANGFUSE_SECRET_KEY = _langfuse.secret_key
LANGFUSE_ENABLED = _langfuse.enabled
LANGFUSE_SAMPLE_RATE = _langfuse.sample_rate
LANGFUSE_TRACE_LLM = _langfuse.trace_llm
LANGFUSE_TRACE_API = _langfuse.trace_api
LANGFUSE_TRACE_WORKFLOWS = _langfuse.trace_workflows
LANGFUSE_LLM_INPUT_LIMIT = _langfuse.llm_input_limit
LANGFUSE_LLM_OUTPUT_LIMIT = _langfuse.llm_output_limit
LANGFUSE_API_TRACED_PREFIXES = list(_langfuse.api_traced_prefixes)
LANGFUSE_POSTGRES_HOST = _langfuse.postgres_host
LANGFUSE_POSTGRES_PORT = _langfuse.postgres_port
LANGFUSE_POSTGRES_USER = _langfuse.postgres_user
LANGFUSE_POSTGRES_PASSWORD = _langfuse.postgres_password
LANGFUSE_POSTGRES_DB = _langfuse.postgres_db

# Cache & Workspace
AGENT_CARD_CACHE_TTL = _cache.agent_card_ttl
MCP_CACHE_TTL = _cache.mcp_ttl
WORKSPACE_BASE_PATH = _cache.workspace_base_path

__all__ = [
    "DatabaseConfig", "PortsConfig", "SecretsConfig", "SmtpConfig",
    "AuthConfig", "SSOEnvConfig", "RedisConfig", "LangfuseConfig", "CacheConfig",
    "UI_REACT_VOICE_CHAT_PORT", "ADMIN_API_PORT", "ADMIN_UI_PORT",
    "TAVILY_API_KEY",
    "POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_USER", "POSTGRES_PASSWORD",
    "POSTGRES_DB", "POSTGRES_SCHEMA", "BASE_DB_URL_ASYNC", "BASE_DB_URL_SYNC",
    "AGENT_CARD_CACHE_TTL", "MCP_CACHE_TTL", "WORKSPACE_BASE_PATH",
    "LLM_ENCRYPTION_KEY",
    "SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD",
    "SMTP_FROM_EMAIL", "SMTP_FROM_NAME", "SMTP_USE_TLS",
    "OTP_EXPIRY_MINUTES", "OTP_MAX_ATTEMPTS",
    "LANGFUSE_HOST", "LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_ENABLED",
    "LANGFUSE_SAMPLE_RATE", "LANGFUSE_TRACE_LLM", "LANGFUSE_TRACE_API",
    "LANGFUSE_TRACE_WORKFLOWS", "LANGFUSE_LLM_INPUT_LIMIT", "LANGFUSE_LLM_OUTPUT_LIMIT",
    "LANGFUSE_API_TRACED_PREFIXES",
    "LANGFUSE_POSTGRES_HOST", "LANGFUSE_POSTGRES_PORT", "LANGFUSE_POSTGRES_USER",
    "LANGFUSE_POSTGRES_PASSWORD", "LANGFUSE_POSTGRES_DB",
    "VOICE_GATEWAY_PORT", "CHATBOT_BASE_URL",
    "COOKIE_DOMAIN", "SECURE_COOKIES", "ACCESS_TOKEN_MAX_AGE",
    "REFRESH_TOKEN_MAX_AGE", "CSRF_TOKEN_MAX_AGE",
    "COOKIE_SAMESITE_ACCESS", "COOKIE_SAMESITE_REFRESH", "COOKIE_SAMESITE_CSRF",
    "SSO_ENCRYPTION_KEY", "API_BASE_URL", "FRONTEND_BASE_URL", "VOICE_CHAT_BASE_URL",
    "SSO_REDIRECT_PATH_ADMIN", "SSO_REDIRECT_PATH_VOICE",
    "SSO_ERROR_PATH_ADMIN", "SSO_ERROR_PATH_VOICE",
    "SSO_STATE_TTL_SECONDS", "SSO_USE_REDIS",
    "REDIS_HOST", "REDIS_PORT", "REDIS_PASSWORD", "REDIS_DB", "REDIS_SSL",
    "SSO_VERIFY_JWT_SIGNATURE", "SSO_AUDIT_LOGGING_ENABLED", "SSO_SESSION_TIMEOUT_HOURS",
]
