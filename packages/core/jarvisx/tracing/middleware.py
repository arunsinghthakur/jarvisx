from __future__ import annotations

import logging
import time
from typing import Callable, Optional, Tuple

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from jarvisx.config.configs import LANGFUSE_TRACE_API, LANGFUSE_API_TRACED_PREFIXES
from jarvisx.tracing.langfuse_client import get_langfuse, should_sample


def _get_trace_api() -> bool:
    try:
        from jarvisx.services.platform_settings import PlatformSettingsService
        return PlatformSettingsService.get("tracing", "trace_api", LANGFUSE_TRACE_API)
    except Exception:
        return LANGFUSE_TRACE_API


def _get_api_prefixes() -> list:
    try:
        from jarvisx.services.platform_settings import PlatformSettingsService
        raw = PlatformSettingsService.get("tracing", "api_traced_prefixes", "")
        if isinstance(raw, list):
            return raw
        if isinstance(raw, str) and raw:
            return [p.strip() for p in raw.split(",") if p.strip()]
        return LANGFUSE_API_TRACED_PREFIXES
    except Exception:
        return LANGFUSE_API_TRACED_PREFIXES
from jarvisx.tracing.context import (
    TraceContext,
    set_trace_context,
    clear_trace_context,
    TRACE_ID_HEADER,
)

logger = logging.getLogger(__name__)

_SKIP_PATHS = frozenset(("/health", "/", "/docs", "/openapi.json", "/redoc"))


def _extract_user_from_token(auth_header: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    if not auth_header or not auth_header.startswith("Bearer "):
        return None, None

    try:
        import jwt
        token = auth_header[7:]
        payload = jwt.decode(token, options={"verify_signature": False})
        user_id = payload.get("sub")
        org_id = payload.get("org_id") or payload.get("organization_id")
        return user_id, org_id
    except Exception:
        return None, None


def _should_trace_path(path: str) -> bool:
    prefixes = _get_api_prefixes()
    if not prefixes:
        return True
    return any(path.startswith(prefix) for prefix in prefixes)


class LangFuseTracingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, service_name: str = "jarvisx-api"):
        super().__init__(app)
        self.service_name = service_name

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path in _SKIP_PATHS:
            return await call_next(request)

        ctx = TraceContext.from_headers(dict(request.headers))

        if not ctx.tenant_id or not ctx.user_id:
            auth_header = request.headers.get("authorization")
            token_user_id, token_org_id = _extract_user_from_token(auth_header)
            if token_user_id and not ctx.user_id:
                ctx.user_id = token_user_id
            if token_org_id and not ctx.tenant_id:
                ctx.tenant_id = token_org_id

        trace = None
        tracing_active = _get_trace_api() and _should_trace_path(request.url.path) and should_sample()

        if tracing_active:
            langfuse = get_langfuse()
            if langfuse:
                try:
                    trace = langfuse.trace(
                        name=f"{request.method} {request.url.path}",
                        metadata={
                            "service": self.service_name,
                            "method": request.method,
                            "path": request.url.path,
                            "organization_id": ctx.tenant_id,
                            "tenant_id": ctx.tenant_id,
                            "user_id": ctx.user_id,
                        },
                        input={
                            "method": request.method,
                            "path": request.url.path,
                            "query_params": str(request.query_params),
                        },
                    )
                    logger.debug(f"Created trace: {trace.id}")
                except Exception as e:
                    logger.warning(f"Failed to create trace: {e}")

        ctx.trace = trace
        token = set_trace_context(ctx)

        start_time = time.time()

        try:
            response = await call_next(request)

            duration_ms = (time.time() - start_time) * 1000

            if trace:
                try:
                    trace.update(
                        output={
                            "status_code": response.status_code,
                            "duration_ms": round(duration_ms, 2),
                        }
                    )
                except Exception as e:
                    logger.debug(f"Failed to update trace: {e}")

            response.headers[TRACE_ID_HEADER] = ctx.trace_id

            return response
        except Exception as e:
            if trace:
                try:
                    trace.update(
                        output={"error": str(e)},
                        level="ERROR",
                        status_message=str(e),
                    )
                except Exception:
                    pass
            raise
        finally:
            clear_trace_context(token)
