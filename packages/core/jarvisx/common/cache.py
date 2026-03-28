from __future__ import annotations

import time
from typing import Any, Generic, Optional, TypeVar

T = TypeVar("T")


class TTLCache(Generic[T]):
    
    def __init__(self, ttl: int):
        self._cache: dict[str, tuple[T, float]] = {}
        self._ttl = ttl

    def get(self, key: str) -> Optional[T]:
        entry = self._cache.get(key)
        if not entry:
            return None
        value, timestamp = entry
        if (time.time() - timestamp) >= self._ttl:
            del self._cache[key]
            return None
        return value

    def set(self, key: str, value: T) -> None:
        self._cache[key] = (value, time.time())

    def invalidate(self, key: str) -> None:
        if key in self._cache:
            del self._cache[key]

    def invalidate_all(self) -> None:
        self._cache.clear()

    def is_valid(self, key: str) -> bool:
        return self.get(key) is not None

    @property
    def ttl(self) -> int:
        return self._ttl


class GlobalTTLCache(TTLCache[T]):
    
    _instances: dict[str, "GlobalTTLCache"] = {}

    def __new__(cls, cache_name: str, ttl: int) -> "GlobalTTLCache":
        if cache_name not in cls._instances:
            instance = super().__new__(cls)
            instance._cache = {}
            instance._ttl = ttl
            cls._instances[cache_name] = instance
        return cls._instances[cache_name]

    def __init__(self, cache_name: str, ttl: int):
        pass


__all__ = ["TTLCache", "GlobalTTLCache"]
