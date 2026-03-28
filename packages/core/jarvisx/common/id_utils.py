from __future__ import annotations

import uuid

AGENT_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
MCP_NAMESPACE = uuid.UUID("6ba7b811-9dad-11d1-80b4-00c04fd430c8")
ORG_NAMESPACE = uuid.UUID("6ba7b812-9dad-11d1-80b4-00c04fd430c8")
WORKSPACE_NAMESPACE = uuid.UUID("6ba7b813-9dad-11d1-80b4-00c04fd430c8")


def generate_id() -> str:
    return str(uuid.uuid4())


def _coerce_uuid(namespace: uuid.UUID, value: str) -> str:
    if len(value) == 36 and value.count("-") == 4:
        return value
    return str(uuid.uuid5(namespace, value))


def agent_uuid(value: str) -> str:
    return _coerce_uuid(AGENT_NAMESPACE, value)


def mcp_uuid(value: str) -> str:
    return _coerce_uuid(MCP_NAMESPACE, value)


def org_uuid(value: str) -> str:
    return _coerce_uuid(ORG_NAMESPACE, value)


def workspace_uuid(org_id: str, name: str) -> str:
    return str(uuid.uuid5(WORKSPACE_NAMESPACE, f"{name}:{org_id}"))
