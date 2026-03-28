from __future__ import annotations

import logging
import random
from typing import Optional, Any

from jarvisx.config.configs import (
    LANGFUSE_HOST,
    LANGFUSE_PUBLIC_KEY,
    LANGFUSE_SECRET_KEY,
    LANGFUSE_ENABLED,
    LANGFUSE_SAMPLE_RATE,
)


def _get_sample_rate() -> float:
    try:
        from jarvisx.services.platform_settings import PlatformSettingsService
        return PlatformSettingsService.get("tracing", "sample_rate", LANGFUSE_SAMPLE_RATE)
    except Exception:
        return LANGFUSE_SAMPLE_RATE

logger = logging.getLogger(__name__)

_langfuse_instance: Optional[Any] = None


def _is_configured() -> bool:
    configured = bool(LANGFUSE_ENABLED and LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY)
    if not configured:
        logger.debug(f"LangFuse config check: ENABLED={LANGFUSE_ENABLED}, PK={bool(LANGFUSE_PUBLIC_KEY)}, SK={bool(LANGFUSE_SECRET_KEY)}")
    return configured


def get_langfuse():
    global _langfuse_instance
    
    if _langfuse_instance is not None:
        return _langfuse_instance
    
    if not _is_configured():
        logger.warning("LangFuse is not configured or disabled")
        return None
    
    try:
        from langfuse import Langfuse
        
        logger.info(f"Initializing LangFuse client with host={LANGFUSE_HOST}")
        _langfuse_instance = Langfuse(
            public_key=LANGFUSE_PUBLIC_KEY,
            secret_key=LANGFUSE_SECRET_KEY,
            host=LANGFUSE_HOST,
        )
        logger.info("LangFuse client initialized successfully")
        return _langfuse_instance
    except ImportError:
        logger.warning("langfuse package not installed")
        return None
    except Exception as e:
        logger.warning(f"Failed to initialize LangFuse client: {e}")
        return None


def create_trace(
    name: str,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    metadata: Optional[dict] = None,
    tags: Optional[list[str]] = None,
    trace_id: Optional[str] = None,
):
    langfuse = get_langfuse()
    if not langfuse:
        return None
    
    try:
        return langfuse.trace(
            name=name,
            user_id=user_id,
            session_id=session_id,
            metadata=metadata or {},
            tags=tags,
            id=trace_id,
        )
    except Exception as e:
        logger.warning(f"Failed to create trace: {e}")
        return None


def create_span(
    trace,
    name: str,
    input: Optional[Any] = None,
    metadata: Optional[dict] = None,
):
    if not trace:
        return None
    
    try:
        return trace.span(
            name=name,
            input=input,
            metadata=metadata or {},
        )
    except Exception as e:
        logger.warning(f"Failed to create span: {e}")
        return None


def create_generation(
    trace,
    name: str,
    model: Optional[str] = None,
    input: Optional[Any] = None,
    metadata: Optional[dict] = None,
):
    if not trace:
        return None
    
    try:
        return trace.generation(
            name=name,
            model=model,
            input=input,
            metadata=metadata or {},
        )
    except Exception as e:
        logger.warning(f"Failed to create generation: {e}")
        return None


def should_sample(force: bool = False) -> bool:
    if force:
        return True
    rate = _get_sample_rate()
    if rate >= 1.0:
        return True
    if rate <= 0.0:
        return False
    return random.random() < rate


def flush_langfuse():
    langfuse = get_langfuse()
    if langfuse:
        try:
            langfuse.flush()
        except Exception as e:
            logger.warning(f"Failed to flush LangFuse: {e}")
