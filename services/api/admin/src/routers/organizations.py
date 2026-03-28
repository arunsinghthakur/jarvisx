from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session, joinedload
from typing import List
from datetime import datetime
import uuid

from jarvisx.database.models import Organization, Workspace
from jarvisx.database.session import get_db
from services.api.admin.src.models import OrganizationCreate, OrganizationUpdate, OrganizationResponse
from services.api.admin.src.dependencies import OrganizationContext, get_organization_context

router = APIRouter(prefix="/api/organizations", tags=["organizations"])


@router.get("", response_model=List[OrganizationResponse])
def list_organizations(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    org_ctx: OrganizationContext = Depends(get_organization_context)
):
    query = db.query(Organization).options(joinedload(Organization.workspaces))
    
    if not org_ctx.is_platform_admin:
        query = query.filter(Organization.id == org_ctx.organization_id)
    
    organizations = query.offset(skip).limit(limit).all()
    return organizations


@router.get("/{organization_id}", response_model=OrganizationResponse)
def get_organization(
    organization_id: str, 
    db: Session = Depends(get_db),
    org_ctx: OrganizationContext = Depends(get_organization_context)
):
    if not org_ctx.can_access_organization(organization_id):
        raise HTTPException(status_code=403, detail="Access denied to this organization")
    
    organization = db.query(Organization).options(
        joinedload(Organization.workspaces)
    ).filter(Organization.id == organization_id).first()
    
    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")
    return organization


@router.post("")
def create_organization(
    org_data: OrganizationCreate, 
    db: Session = Depends(get_db),
    org_ctx: OrganizationContext = Depends(get_organization_context)
):
    if not org_ctx.is_platform_admin:
        raise HTTPException(status_code=403, detail="Only platform administrators can create organizations")
    
    organization_id = str(uuid.uuid4())
    
    organization = Organization(
        id=organization_id,
        name=org_data.name,
        description=org_data.description
    )
    db.add(organization)
    db.flush()
    
    from services.api.admin.src.routers.auth import create_default_user_for_organization
    user, email, password = create_default_user_for_organization(db, organization_id, org_data.name)
    
    db.commit()
    db.refresh(organization)
    
    return {
        "organization": {
            "id": organization.id,
            "name": organization.name,
            "description": organization.description,
            "is_active": organization.is_active,
            "is_platform_admin": organization.is_platform_admin,
            "delete_protection": organization.delete_protection,
            "created_at": organization.created_at.isoformat(),
            "updated_at": organization.updated_at.isoformat(),
        },
        "default_user": {
            "email": email,
            "password": password,
            "note": "Please change this password after first login"
        }
    }


@router.put("/{organization_id}", response_model=OrganizationResponse)
def update_organization(
    organization_id: str, 
    org_data: OrganizationUpdate, 
    db: Session = Depends(get_db),
    org_ctx: OrganizationContext = Depends(get_organization_context)
):
    if not org_ctx.can_access_organization(organization_id):
        raise HTTPException(status_code=403, detail="Access denied to this organization")
    
    organization = db.query(Organization).filter(Organization.id == organization_id).first()
    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    if organization.delete_protection and not org_ctx.is_platform_admin:
        if org_data.name is not None or org_data.description is not None:
            raise HTTPException(status_code=403, detail="Cannot modify protected organization details")
    
    if org_data.name is not None:
        organization.name = org_data.name
    if org_data.description is not None:
        organization.description = org_data.description
    if org_data.is_active is not None:
        if not org_ctx.is_platform_admin:
            raise HTTPException(status_code=403, detail="Only platform administrators can change organization status")
        organization.is_active = org_data.is_active
    
    organization.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(organization)
    return organization


@router.delete("/{organization_id}")
def delete_organization(
    organization_id: str, 
    db: Session = Depends(get_db),
    org_ctx: OrganizationContext = Depends(get_organization_context)
):
    if not org_ctx.is_platform_admin:
        raise HTTPException(status_code=403, detail="Only platform administrators can delete organizations")
    
    organization = db.query(Organization).filter(Organization.id == organization_id).first()
    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    if organization.delete_protection:
        raise HTTPException(status_code=400, detail="This organization is protected and cannot be deleted")
    
    workspace_count = db.query(Workspace).filter(Workspace.organization_id == organization_id).count()
    if workspace_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete organization: it has {workspace_count} workspace(s). Delete workspaces first."
        )
    
    db.delete(organization)
    db.commit()
    return {"message": "Organization deleted successfully"}


@router.get("/{organization_id}/workspaces", response_model=List[dict])
def list_organization_workspaces(
    organization_id: str, 
    db: Session = Depends(get_db),
    org_ctx: OrganizationContext = Depends(get_organization_context)
):
    if not org_ctx.can_access_organization(organization_id):
        raise HTTPException(status_code=403, detail="Access denied to this organization")
    
    organization = db.query(Organization).filter(Organization.id == organization_id).first()
    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    workspaces = db.query(Workspace).filter(Workspace.organization_id == organization_id).all()
    return [
        {
            "id": t.id,
            "name": t.name,
            "description": t.description,
            "is_active": t.is_active,
            "chat_mode": t.chat_mode,
            "voice_agent_name": t.voice_agent_name
        }
        for t in workspaces
    ]
