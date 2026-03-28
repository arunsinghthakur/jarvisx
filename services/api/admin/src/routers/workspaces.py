from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import uuid

from jarvisx.database.models import Workspace, Organization
from jarvisx.database.session import get_db
from services.api.admin.src.models import WorkspaceCreate, WorkspaceUpdate, WorkspaceResponse
from services.api.admin.src.dependencies import (
    OrganizationContext, get_organization_context, CurrentUser, get_current_user
)
from services.api.admin.src.permissions import Resource, Action
from services.api.admin.src.decorators import require_permission

router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])


@router.get("", response_model=List[WorkspaceResponse])
def list_workspaces(
    skip: int = 0, 
    limit: int = 100, 
    organization_id: Optional[str] = None, 
    db: Session = Depends(get_db),
    org_ctx: OrganizationContext = Depends(get_organization_context)
):
    query = db.query(Workspace)
    
    if org_ctx.is_platform_admin:
        if organization_id:
            query = query.filter(Workspace.organization_id == organization_id)
    else:
        query = query.filter(Workspace.organization_id == org_ctx.organization_id)
    
    workspaces = query.offset(skip).limit(limit).all()
    return workspaces


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
def get_workspace(
    workspace_id: str, 
    db: Session = Depends(get_db),
    org_ctx: OrganizationContext = Depends(get_organization_context)
):
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    if not org_ctx.can_access_organization(workspace.organization_id):
        raise HTTPException(status_code=403, detail="Access denied to this workspace")
    
    return workspace


@router.post("", response_model=WorkspaceResponse)
@require_permission(Resource.WORKSPACES, Action.CREATE)
def create_workspace(
    workspace_data: WorkspaceCreate, 
    db: Session = Depends(get_db),
    org_ctx: OrganizationContext = Depends(get_organization_context),
    current_user: CurrentUser = Depends(get_current_user)
):
    if not org_ctx.can_access_organization(workspace_data.organization_id):
        raise HTTPException(status_code=403, detail="Cannot create workspace in this organization")
    
    organization = db.query(Organization).filter(Organization.id == workspace_data.organization_id).first()
    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    workspace_id = str(uuid.uuid4())
    
    workspace = Workspace(
        id=workspace_id,
        organization_id=workspace_data.organization_id,
        name=workspace_data.name,
        description=workspace_data.description,
        chat_mode=workspace_data.chat_mode.value if hasattr(workspace_data.chat_mode, 'value') else workspace_data.chat_mode,
        ui_base_url=workspace_data.ui_base_url,
        voice_agent_name=workspace_data.voice_agent_name
    )
    db.add(workspace)
    db.commit()
    db.refresh(workspace)

    return workspace


@router.put("/{workspace_id}", response_model=WorkspaceResponse)
@require_permission(Resource.WORKSPACES, Action.EDIT)
def update_workspace(
    workspace_id: str, 
    workspace_data: WorkspaceUpdate, 
    db: Session = Depends(get_db),
    org_ctx: OrganizationContext = Depends(get_organization_context),
    current_user: CurrentUser = Depends(get_current_user)
):
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    if not org_ctx.can_access_organization(workspace.organization_id):
        raise HTTPException(status_code=403, detail="Access denied to this workspace")
    
    if workspace.delete_protection or workspace.is_system_workspace:
        if not org_ctx.is_platform_admin:
            if workspace_data.name is not None or workspace_data.description is not None:
                raise HTTPException(status_code=403, detail="Cannot modify protected workspace details")
    
    if workspace_data.name is not None:
        workspace.name = workspace_data.name
    if workspace_data.description is not None:
        workspace.description = workspace_data.description
    if workspace_data.is_active is not None:
        workspace.is_active = workspace_data.is_active
    if workspace_data.chat_mode is not None:
        workspace.chat_mode = workspace_data.chat_mode.value if hasattr(workspace_data.chat_mode, 'value') else workspace_data.chat_mode
    if workspace_data.ui_base_url is not None:
        workspace.ui_base_url = workspace_data.ui_base_url
    if workspace_data.voice_agent_name is not None:
        workspace.voice_agent_name = workspace_data.voice_agent_name
    
    workspace.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(workspace)
    return workspace


@router.delete("/{workspace_id}")
@require_permission(Resource.WORKSPACES, Action.DELETE)
def delete_workspace(
    workspace_id: str, 
    db: Session = Depends(get_db),
    org_ctx: OrganizationContext = Depends(get_organization_context),
    current_user: CurrentUser = Depends(get_current_user)
):
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    if not org_ctx.can_access_organization(workspace.organization_id):
        raise HTTPException(status_code=403, detail="Access denied to this workspace")
    
    if workspace.delete_protection:
        raise HTTPException(status_code=400, detail="This workspace is protected and cannot be deleted")
    
    if workspace.is_system_workspace and not org_ctx.is_platform_admin:
        raise HTTPException(status_code=403, detail="Only platform administrators can delete system workspaces")
    
    db.delete(workspace)
    db.commit()
    return {"message": "Workspace deleted successfully"}
