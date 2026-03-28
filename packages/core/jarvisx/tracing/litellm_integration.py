from __future__ import annotations

import logging
import os

from jarvisx.config.configs import (
    LANGFUSE_HOST,
    LANGFUSE_PUBLIC_KEY,
    LANGFUSE_SECRET_KEY,
    LANGFUSE_ENABLED,
    LANGFUSE_TRACE_LLM,
    LANGFUSE_SAMPLE_RATE,
    LANGFUSE_LLM_INPUT_LIMIT,
    LANGFUSE_LLM_OUTPUT_LIMIT,
)


def _get_tracing_setting(key: str, default):
    try:
        from jarvisx.services.platform_settings import PlatformSettingsService
        return PlatformSettingsService.get("tracing", key, default)
    except Exception:
        return default

logger = logging.getLogger(__name__)

_litellm_callback_initialized = False


def setup_litellm_langfuse_callback():
    global _litellm_callback_initialized

    if _litellm_callback_initialized:
        return True

    try:
        import litellm
    except ImportError:
        logger.warning("litellm package not installed, cannot setup LangFuse callback")
        return False

    trace_llm = _get_tracing_setting("trace_llm", LANGFUSE_TRACE_LLM)
    if not LANGFUSE_ENABLED or not trace_llm:
        logger.debug("LangFuse LLM tracing is disabled")
        return False

    if not LANGFUSE_PUBLIC_KEY or not LANGFUSE_SECRET_KEY:
        logger.debug("LangFuse credentials not configured")
        return False

    try:
        os.environ["LANGFUSE_PUBLIC_KEY"] = LANGFUSE_PUBLIC_KEY
        os.environ["LANGFUSE_SECRET_KEY"] = LANGFUSE_SECRET_KEY
        os.environ["LANGFUSE_HOST"] = LANGFUSE_HOST

        sample_rate = _get_tracing_setting("sample_rate", LANGFUSE_SAMPLE_RATE)
        input_limit = _get_tracing_setting("llm_input_limit", LANGFUSE_LLM_INPUT_LIMIT)
        output_limit = _get_tracing_setting("llm_output_limit", LANGFUSE_LLM_OUTPUT_LIMIT)

        os.environ["LANGFUSE_SAMPLE_RATE"] = str(sample_rate)

        if input_limit > 0:
            os.environ["LANGFUSE_INPUT_LIMIT"] = str(input_limit)
        if output_limit > 0:
            os.environ["LANGFUSE_OUTPUT_LIMIT"] = str(output_limit)

        if "langfuse" not in litellm.success_callback:
            litellm.success_callback.append("langfuse")
        if "langfuse" not in litellm.failure_callback:
            litellm.failure_callback.append("langfuse")

        try:
            from jarvisx.tracing.cost_tracking import setup_cost_tracking_callback
            setup_cost_tracking_callback()
        except Exception as cost_err:
            logger.debug(f"Cost tracking setup skipped: {cost_err}")

        _litellm_callback_initialized = True
        logger.info(
            f"LiteLLM LangFuse callback configured: host={LANGFUSE_HOST}, "
            f"sample_rate={LANGFUSE_SAMPLE_RATE}, "
            f"input_limit={LANGFUSE_LLM_INPUT_LIMIT}, output_limit={LANGFUSE_LLM_OUTPUT_LIMIT}"
        )
        return True
    except Exception as e:
        logger.warning(f"Failed to setup LiteLLM LangFuse callback: {e}")
        return False
