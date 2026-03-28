from __future__ import annotations

import contextvars
from dataclasses import dataclass, field
from typing import Optional, Any
import uuid

TRACE_ID_HEADER = "x-trace-id"
SPAN_ID_HEADER = "x-span-id"

_trace_context: contextvars.ContextVar[Optional["TraceContext"]] = contextvars.ContextVar(
    "trace_context", default=None
)


@dataclass
class TraceContext:
    trace_id: str
    span_id: Optional[str] = None
    tenant_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    trace: Optional[Any] = None
    current_span: Optional[Any] = None
    metadata: dict = field(default_factory=dict)
    
    @classmethod
    def create(
        cls,
        trace_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> "TraceContext":
        return cls(
            trace_id=trace_id or str(uuid.uuid4()),
            tenant_id=tenant_id,
            user_id=user_id,
            session_id=session_id,
        )
    
    @classmethod
    def from_headers(cls, headers: dict) -> "TraceContext":
        return cls(
            trace_id=headers.get(TRACE_ID_HEADER) or headers.get("x-request-id") or str(uuid.uuid4()),
            span_id=headers.get(SPAN_ID_HEADER),
            tenant_id=headers.get("x-tenant-id"),
            user_id=headers.get("x-user-id"),
        )
    
    def to_headers(self) -> dict:
        headers = {TRACE_ID_HEADER: self.trace_id}
        if self.span_id:
            headers[SPAN_ID_HEADER] = self.span_id
        if self.tenant_id:
            headers["x-tenant-id"] = self.tenant_id
        if self.user_id:
            headers["x-user-id"] = self.user_id
        return headers


def get_current_trace_context() -> Optional[TraceContext]:
    return _trace_context.get()


def set_trace_context(ctx: TraceContext) -> contextvars.Token:
    return _trace_context.set(ctx)


def clear_trace_context(token: Optional[contextvars.Token] = None):
    if token:
        _trace_context.reset(token)
    else:
        _trace_context.set(None)
