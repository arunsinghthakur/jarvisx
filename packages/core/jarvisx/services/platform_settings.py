import logging
import time
from datetime import datetime
from typing import Any, Optional

from jarvisx.common.id_utils import generate_id

logger = logging.getLogger(__name__)

_ENV_DEFAULTS = {
    ("tracing", "sample_rate"): ("LANGFUSE_SAMPLE_RATE", 0.1, "float"),
    ("tracing", "trace_llm"): ("LANGFUSE_TRACE_LLM", False, "bool"),
    ("tracing", "trace_api"): ("LANGFUSE_TRACE_API", False, "bool"),
    ("tracing", "trace_workflows"): ("LANGFUSE_TRACE_WORKFLOWS", True, "bool"),
    ("tracing", "llm_input_limit"): ("LANGFUSE_LLM_INPUT_LIMIT", 500, "int"),
    ("tracing", "llm_output_limit"): ("LANGFUSE_LLM_OUTPUT_LIMIT", 500, "int"),
    ("tracing", "api_traced_prefixes"): ("LANGFUSE_API_TRACED_PREFIXES", "", "string"),
    ("performance", "agent_card_cache_ttl"): ("AGENT_CARD_CACHE_TTL", 14400, "int"),
    ("performance", "mcp_cache_ttl"): ("MCP_CACHE_TTL", 14400, "int"),
    ("auth", "otp_expiry_minutes"): ("OTP_EXPIRY_MINUTES", 15, "int"),
    ("auth", "otp_max_attempts"): ("OTP_MAX_ATTEMPTS", 3, "int"),
}


def _cast(value: Any, value_type: str) -> Any:
    if value_type == "bool":
        if isinstance(value, bool):
            return value
        return str(value).lower() in ("true", "1", "yes")
    if value_type == "int":
        return int(value)
    if value_type == "float":
        return float(value)
    return str(value)


class PlatformSettingsService:
    _cache: dict = {}
    _cache_ts: dict = {}
    _cache_ttl: int = 60

    @classmethod
    def get(cls, category: str, key: str, default: Any = None) -> Any:
        cache_key = f"{category}:{key}"

        cached = cls._cache.get(cache_key)
        ts = cls._cache_ts.get(cache_key, 0)
        if cached is not None and (time.time() - ts) < cls._cache_ttl:
            return cached

        try:
            from jarvisx.database.session import get_db_session
            from jarvisx.database.models import PlatformSetting

            with get_db_session() as db:
                setting = db.query(PlatformSetting).filter(
                    PlatformSetting.category == category,
                    PlatformSetting.key == key,
                ).first()
                if setting:
                    val = _cast(setting.value, setting.value_type)
                    cls._cache[cache_key] = val
                    cls._cache_ts[cache_key] = time.time()
                    return val
        except Exception as e:
            logger.debug(f"DB lookup failed for {cache_key}, using fallback: {e}")

        env_info = _ENV_DEFAULTS.get((category, key))
        if env_info:
            import os
            env_name, env_default, value_type = env_info
            env_val = os.getenv(env_name)
            if env_val is not None:
                return _cast(env_val, value_type)
            return env_default

        return default

    @classmethod
    def set(cls, category: str, key: str, value: Any, updated_by: Optional[str] = None) -> dict:
        from jarvisx.database.session import get_db_session
        from jarvisx.database.models import PlatformSetting

        env_info = _ENV_DEFAULTS.get((category, key))
        value_type = env_info[2] if env_info else "string"

        with get_db_session() as db:
            setting = db.query(PlatformSetting).filter(
                PlatformSetting.category == category,
                PlatformSetting.key == key,
            ).first()

            if setting:
                setting.value = value
                setting.value_type = value_type
                setting.updated_at = datetime.utcnow()
                setting.updated_by = updated_by
            else:
                setting = PlatformSetting(
                    id=f"ps_{category}_{key}",
                    category=category,
                    key=key,
                    value=value,
                    value_type=value_type,
                    updated_at=datetime.utcnow(),
                    updated_by=updated_by,
                )
                db.add(setting)

            db.commit()
            db.refresh(setting)

            cache_key = f"{category}:{key}"
            cls._cache[cache_key] = _cast(value, value_type)
            cls._cache_ts[cache_key] = time.time()

            return {
                "id": setting.id,
                "category": setting.category,
                "key": setting.key,
                "value": setting.value,
                "value_type": setting.value_type,
                "description": setting.description,
                "updated_at": setting.updated_at.isoformat() if setting.updated_at else None,
            }

    @classmethod
    def get_category(cls, category: str) -> list[dict]:
        try:
            from jarvisx.database.session import get_db_session
            from jarvisx.database.models import PlatformSetting

            with get_db_session() as db:
                settings = db.query(PlatformSetting).filter(
                    PlatformSetting.category == category,
                ).order_by(PlatformSetting.key).all()
                return [
                    {
                        "id": s.id,
                        "category": s.category,
                        "key": s.key,
                        "value": s.value,
                        "value_type": s.value_type,
                        "description": s.description,
                        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
                    }
                    for s in settings
                ]
        except Exception as e:
            logger.warning(f"Failed to load category {category}: {e}")
            return []

    @classmethod
    def get_all(cls) -> dict[str, list[dict]]:
        try:
            from jarvisx.database.session import get_db_session
            from jarvisx.database.models import PlatformSetting

            with get_db_session() as db:
                settings = db.query(PlatformSetting).order_by(
                    PlatformSetting.category, PlatformSetting.key
                ).all()
                grouped: dict[str, list[dict]] = {}
                for s in settings:
                    entry = {
                        "id": s.id,
                        "category": s.category,
                        "key": s.key,
                        "value": s.value,
                        "value_type": s.value_type,
                        "description": s.description,
                        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
                    }
                    grouped.setdefault(s.category, []).append(entry)
                return grouped
        except Exception as e:
            logger.warning(f"Failed to load all settings: {e}")
            return {}

    @classmethod
    def invalidate_cache(cls, category: Optional[str] = None, key: Optional[str] = None):
        if category and key:
            cache_key = f"{category}:{key}"
            cls._cache.pop(cache_key, None)
            cls._cache_ts.pop(cache_key, None)
        else:
            cls._cache.clear()
            cls._cache_ts.clear()
