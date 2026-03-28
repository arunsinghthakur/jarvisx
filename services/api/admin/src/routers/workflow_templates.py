from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from jarvisx.database.session import get_db
from jarvisx.database.models import WorkflowTemplate, Workflow
from jarvisx.common.id_utils import generate_id
from services.api.admin.src.dependencies import get_current_user, CurrentUser

router = APIRouter(prefix="/api/workflow-templates", tags=["workflow-templates"])


class TemplateCreate(BaseModel):
    name: str
    description: Optional[str] = None
    category: str = "general"
    workflow_id: Optional[str] = None
    definition: Optional[dict] = None
    trigger_type: str = "manual"
    trigger_config: Optional[dict] = None
    tags: Optional[list[str]] = None


class TemplateUse(BaseModel):
    workspace_id: str
    name: Optional[str] = None


@router.get("")
def list_templates(
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    query = db.query(WorkflowTemplate).filter(
        (WorkflowTemplate.is_system == True) |
        (WorkflowTemplate.organization_id == current_user.organization_id) |
        (WorkflowTemplate.organization_id == None)
    )

    if category:
        query = query.filter(WorkflowTemplate.category == category)
    if search:
        query = query.filter(WorkflowTemplate.name.ilike(f"%{search}%"))

    total = query.count()
    templates = query.order_by(WorkflowTemplate.use_count.desc()).offset(offset).limit(limit).all()

    return {
        "templates": [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "category": t.category,
                "trigger_type": t.trigger_type,
                "tags": t.tags or [],
                "is_system": t.is_system,
                "use_count": t.use_count,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in templates
        ],
        "total": total,
    }


@router.get("/{template_id}")
def get_template(
    template_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    template = db.query(WorkflowTemplate).filter(WorkflowTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    return {
        "id": template.id,
        "name": template.name,
        "description": template.description,
        "category": template.category,
        "definition": template.definition,
        "trigger_type": template.trigger_type,
        "trigger_config": template.trigger_config,
        "tags": template.tags or [],
        "is_system": template.is_system,
        "use_count": template.use_count,
    }


@router.post("")
def create_template(
    body: TemplateCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    definition = body.definition

    if body.workflow_id and not definition:
        workflow = db.query(Workflow).filter(Workflow.id == body.workflow_id).first()
        if not workflow:
            raise HTTPException(status_code=404, detail="Source workflow not found")
        definition = workflow.definition
        if not body.trigger_type:
            body.trigger_type = workflow.trigger_type

    if not definition:
        raise HTTPException(status_code=400, detail="Either workflow_id or definition is required")

    template = WorkflowTemplate(
        id=generate_id(),
        name=body.name,
        description=body.description,
        category=body.category,
        definition=definition,
        trigger_type=body.trigger_type,
        trigger_config=body.trigger_config,
        tags=body.tags,
        is_system=False,
        organization_id=current_user.organization_id,
        created_by=current_user.user_id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(template)
    db.commit()

    return {"id": template.id, "name": template.name}


@router.post("/{template_id}/use")
def use_template(
    template_id: str,
    body: TemplateUse,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    template = db.query(WorkflowTemplate).filter(WorkflowTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    name = body.name or f"{template.name} (Copy)"

    existing = db.query(Workflow).filter(
        Workflow.workspace_id == body.workspace_id,
        Workflow.name == name,
    ).first()
    if existing:
        name = f"{name} {datetime.utcnow().strftime('%H%M%S')}"

    workflow = Workflow(
        id=generate_id(),
        workspace_id=body.workspace_id,
        name=name,
        description=template.description,
        definition=template.definition,
        trigger_type=template.trigger_type,
        trigger_config=template.trigger_config,
        is_active=False,
        created_by=current_user.user_id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(workflow)

    template.use_count = (template.use_count or 0) + 1
    db.commit()

    return {"workflow_id": workflow.id, "name": workflow.name}
