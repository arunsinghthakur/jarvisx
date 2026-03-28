from typing import Optional

from google.adk.sessions.database_session_service import DatabaseSessionService

from jarvisx.a2a.memory_service import DatabaseMemoryService
from jarvisx.a2a.artifact_service import DatabaseArtifactService

from jarvisx.config.configs import (
    POSTGRES_SCHEMA,
    BASE_DB_URL_ASYNC,
)


def get_session_service(tenant_id: Optional[str] = None, workspace_id: Optional[str] = None) -> DatabaseSessionService:
    return DatabaseSessionService(
        db_url=BASE_DB_URL_ASYNC,
        connect_args={"server_settings": {"search_path": POSTGRES_SCHEMA}}
    )


def get_memory_service(tenant_id: Optional[str] = None, workspace_id: Optional[str] = None) -> DatabaseMemoryService:
    effective_tenant_id = tenant_id or "default"
    effective_workspace_id = workspace_id or "default"
    return DatabaseMemoryService(
        db_url=BASE_DB_URL_ASYNC, 
        schema=POSTGRES_SCHEMA, 
        workspace_id=effective_workspace_id,
        tenant_id=effective_tenant_id
    )


def get_artifact_service(tenant_id: Optional[str] = None, workspace_id: Optional[str] = None) -> DatabaseArtifactService:
    effective_tenant_id = tenant_id or "default"
    effective_workspace_id = workspace_id or "default"
    return DatabaseArtifactService(
        db_url=BASE_DB_URL_ASYNC, 
        schema=POSTGRES_SCHEMA, 
        workspace_id=effective_workspace_id,
        tenant_id=effective_tenant_id
    )
