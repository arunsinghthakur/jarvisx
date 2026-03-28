from __future__ import annotations

import functools
import logging
import time
from typing import Optional, Callable

from jarvisx.tracing.langfuse_client import get_langfuse, should_sample

logger = logging.getLogger(__name__)


def traced(
    name: Optional[str] = None,
    metadata: Optional[dict] = None,
):
    def decorator(func: Callable) -> Callable:
        span_name = name or func.__name__
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            langfuse = get_langfuse() if should_sample() else None
            span = None
            
            if langfuse:
                try:
                    span = langfuse.start_span(
                        name=span_name,
                        metadata=metadata or {},
                    )
                except Exception as e:
                    logger.debug(f"Failed to create span: {e}")
            
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                if span:
                    try:
                        span.end(output=str(result)[:1000] if result else None)
                    except Exception as span_err:
                        logger.debug(f"Failed to end span for {span_name}: {span_err}")
                return result
            except Exception as e:
                if span:
                    try:
                        span.end(
                            output=None,
                            level="ERROR",
                            status_message=str(e),
                        )
                    except Exception as span_err:
                        logger.debug(f"Failed to end error span for {span_name}: {span_err}")
                raise
            finally:
                duration = time.time() - start_time
                logger.debug(f"{span_name} completed in {duration:.3f}s")
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            langfuse = get_langfuse() if should_sample() else None
            span = None
            
            if langfuse:
                try:
                    span = langfuse.start_span(
                        name=span_name,
                        metadata=metadata or {},
                    )
                except Exception as e:
                    logger.debug(f"Failed to create span: {e}")
            
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                if span:
                    try:
                        span.end(output=str(result)[:1000] if result else None)
                    except Exception as span_err:
                        logger.debug(f"Failed to end span for {span_name}: {span_err}")
                return result
            except Exception as e:
                if span:
                    try:
                        span.end(
                            output=None,
                            level="ERROR",
                            status_message=str(e),
                        )
                    except Exception as span_err:
                        logger.debug(f"Failed to end error span for {span_name}: {span_err}")
                raise
            finally:
                duration = time.time() - start_time
                logger.debug(f"{span_name} completed in {duration:.3f}s")
        
        if asyncio_iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def asyncio_iscoroutinefunction(func: Callable) -> bool:
    import asyncio
    return asyncio.iscoroutinefunction(func)
