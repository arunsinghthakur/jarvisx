"""
State storage for SSO flows
Supports both in-memory (development) and Redis (production) backends
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from threading import Lock

from services.api.admin.src.config.sso_settings import get_sso_settings

logger = logging.getLogger(__name__)


class InMemoryStateStorage:
    """In-memory state storage with TTL cleanup"""

    def __init__(self, ttl_seconds: int = 600):
        self._states: Dict[str, Dict[str, Any]] = {}
        self._lock = Lock()
        self.ttl_seconds = ttl_seconds

    def set(self, key: str, value: Dict[str, Any], ttl_seconds: Optional[int] = None) -> None:
        """Store state with TTL"""
        expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds or self.ttl_seconds)
        with self._lock:
            self._states[key] = {
                "value": value,
                "expires_at": expires_at,
            }
            # Cleanup expired states
            self._cleanup_expired()

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve state if not expired"""
        with self._lock:
            state_data = self._states.get(key)
            if not state_data:
                return None

            if state_data["expires_at"] < datetime.utcnow():
                # Expired, remove it
                del self._states[key]
                return None

            return state_data["value"]

    def delete(self, key: str) -> None:
        """Delete state"""
        with self._lock:
            self._states.pop(key, None)

    def _cleanup_expired(self) -> None:
        """Remove expired states"""
        now = datetime.utcnow()
        expired_keys = [
            key for key, data in self._states.items()
            if data["expires_at"] < now
        ]
        for key in expired_keys:
            del self._states[key]


class RedisStateStorage:
    """Redis-based state storage"""

    def __init__(self, ttl_seconds: int = 600):
        self.ttl_seconds = ttl_seconds
        self._redis = None
        self._init_redis()

    def _init_redis(self):
        """Initialize Redis connection"""
        try:
            import redis
            settings = get_sso_settings()

            redis_kwargs = {
                "host": settings.redis_host,
                "port": settings.redis_port,
                "db": settings.redis_db,
                "decode_responses": True,
            }

            if settings.redis_password:
                redis_kwargs["password"] = settings.redis_password

            if settings.redis_ssl:
                redis_kwargs["ssl"] = True

            self._redis = redis.Redis(**redis_kwargs)
            # Test connection
            self._redis.ping()
            logger.info("Redis connection established for SSO state storage")
        except ImportError:
            logger.error("redis package not installed. Install with: pip install redis")
            raise
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    def set(self, key: str, value: Dict[str, Any], ttl_seconds: Optional[int] = None) -> None:
        """Store state with TTL in Redis"""
        try:
            ttl = ttl_seconds or self.ttl_seconds
            self._redis.setex(
                f"sso:state:{key}",
                ttl,
                json.dumps(value)
            )
        except Exception as e:
            logger.error(f"Failed to set state in Redis: {e}")
            raise

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve state from Redis"""
        try:
            value = self._redis.get(f"sso:state:{key}")
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Failed to get state from Redis: {e}")
            raise

    def delete(self, key: str) -> None:
        """Delete state from Redis"""
        try:
            self._redis.delete(f"sso:state:{key}")
        except Exception as e:
            logger.error(f"Failed to delete state from Redis: {e}")
            raise


# Singleton instance
_state_storage = None
_storage_lock = Lock()


def get_state_storage():
    """Get or create state storage instance"""
    global _state_storage

    if _state_storage is not None:
        return _state_storage

    with _storage_lock:
        if _state_storage is not None:
            return _state_storage

        settings = get_sso_settings()

        if settings.sso_use_redis:
            try:
                _state_storage = RedisStateStorage(ttl_seconds=settings.sso_state_ttl_seconds)
                logger.info("Using Redis for SSO state storage")
            except Exception as e:
                logger.warning(f"Failed to initialize Redis, falling back to in-memory: {e}")
                _state_storage = InMemoryStateStorage(ttl_seconds=settings.sso_state_ttl_seconds)
        else:
            _state_storage = InMemoryStateStorage(ttl_seconds=settings.sso_state_ttl_seconds)
            logger.info("Using in-memory storage for SSO state (not recommended for production)")

        return _state_storage
