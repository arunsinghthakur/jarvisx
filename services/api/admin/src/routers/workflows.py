from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session

from jarvisx.database.session import get_db
from jarvisx.database.models import (
    Workflow, WorkflowExecution, WorkflowExecutionLog,
    WorkflowTriggerType, WorkflowExecutionStatus, User,
    WorkflowVersion,
)
from jarvisx.common.id_utils import generate_id
from services.api.admin.src.models import (
    WorkflowCreate, WorkflowUpdate, WorkflowResponse,
    WorkflowListResponse, WorkflowExecutionResponse,
    ExecutionListResponse, ExecutionLogResponse,
    ExecuteWorkflowRequest, ExecuteWorkflowResponse,
    LastExecutionInfo,
)
from services.api.admin.src.dependencies import get_current_user, CurrentUser
from services.api.admin.src.permissions import Resource, Action
from services.api.admin.src.decorators import require_permission

router = APIRouter(prefix="/api/workflows", tags=["workflows"])


def workflow_to_response(workflow: Workflow, db: Session = None) -> WorkflowResponse:
    last_execution_info = None
    
    if db:
        last_exec = db.query(WorkflowExecution).filter(
            WorkflowExecution.workflow_id == workflow.id
        ).order_by(WorkflowExecution.created_at.desc()).first()
        
        if last_exec:
            last_execution_info = LastExecutionInfo(
                id=last_exec.id,
                status=last_exec.status,
                started_at=last_exec.started_at,
                completed_at=last_exec.completed_at,
                error_message=last_exec.error_message,
            )
    
    return WorkflowResponse(
        id=workflow.id,
        workspace_id=workflow.workspace_id,
        name=workflow.name,
        description=workflow.description,
        definition=workflow.definition or {},
        trigger_type=workflow.trigger_type,
        trigger_config=workflow.trigger_config,
        is_active=workflow.is_active,
        created_by=workflow.created_by,
        created_at=workflow.created_at,
        updated_at=workflow.updated_at,
        last_execution=last_execution_info,
    )


def execution_to_response(execution: WorkflowExecution, include_logs: bool = False) -> WorkflowExecutionResponse:
    logs = []
    if include_logs and execution.logs:
        logs = [
            ExecutionLogResponse(
                id=log.id,
                node_id=log.node_id,
                node_type=log.node_type,
                status=log.status,
                input_data=log.input_data,
                output_data=log.output_data,
                error=log.error,
                started_at=log.started_at,
                completed_at=log.completed_at,
            )
            for log in execution.logs
        ]
    
    return WorkflowExecutionResponse(
        id=execution.id,
        workflow_id=execution.workflow_id,
        status=execution.status,
        trigger_type=execution.trigger_type,
        trigger_data=execution.trigger_data,
        started_at=execution.started_at,
        completed_at=execution.completed_at,
        error_message=execution.error_message,
        created_at=execution.created_at,
        logs=logs,
    )


def generate_chatbot_url(workflow_id: str) -> str:
    from jarvisx.config import CHATBOT_BASE_URL
    return f"{CHATBOT_BASE_URL}/chatbot/{workflow_id}"


@router.post("", response_model=WorkflowResponse)
@require_permission(Resource.WORKFLOWS, Action.CREATE)
def create_workflow(
    workflow_data: WorkflowCreate,
    workspace_id: str = Query(..., description="Workspace ID"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    existing = db.query(Workflow).filter(
        Workflow.workspace_id == workspace_id,
        Workflow.name == workflow_data.name
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Workflow with this name already exists")
    
    workflow_id = generate_id()
    trigger_config = workflow_data.trigger_config or {}
    
    if workflow_data.trigger_type == WorkflowTriggerType.CHATBOT.value:
        trigger_config["chatbot_url"] = generate_chatbot_url(workflow_id)
    
    workflow = Workflow(
        id=workflow_id,
        workspace_id=workspace_id,
        name=workflow_data.name,
        description=workflow_data.description,
        definition=workflow_data.definition.model_dump() if workflow_data.definition else {},
        trigger_type=workflow_data.trigger_type,
        trigger_config=trigger_config,
        is_active=workflow_data.is_active,
        created_by=current_user.user_id,
    )
    
    db.add(workflow)
    db.commit()
    db.refresh(workflow)
    
    return workflow_to_response(workflow, db)


@router.get("", response_model=WorkflowListResponse)
@require_permission(Resource.WORKFLOWS, Action.VIEW)
def list_workflows(
    workspace_id: str = Query(..., description="Workspace ID"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    query = db.query(Workflow).filter(Workflow.workspace_id == workspace_id)
    
    if is_active is not None:
        query = query.filter(Workflow.is_active == is_active)
    
    total = query.count()
    workflows = query.order_by(Workflow.updated_at.desc()).offset(offset).limit(limit).all()
    
    return WorkflowListResponse(
        workflows=[workflow_to_response(w, db) for w in workflows],
        total=total,
    )


@router.get("/{workflow_id}", response_model=WorkflowResponse)
@require_permission(Resource.WORKFLOWS, Action.VIEW)
def get_workflow(
    workflow_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    return workflow_to_response(workflow, db)


@router.put("/{workflow_id}", response_model=WorkflowResponse)
@require_permission(Resource.WORKFLOWS, Action.EDIT)
def update_workflow(
    workflow_id: str,
    workflow_data: WorkflowUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    if workflow_data.name is not None and workflow_data.name != workflow.name:
        existing = db.query(Workflow).filter(
            Workflow.workspace_id == workflow.workspace_id,
            Workflow.name == workflow_data.name,
            Workflow.id != workflow_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Workflow with this name already exists")
        workflow.name = workflow_data.name
    
    if workflow_data.description is not None:
        workflow.description = workflow_data.description
    
    if workflow_data.definition is not None:
        _snapshot_version(db, workflow, current_user.user_id)
        workflow.definition = workflow_data.definition.model_dump()
    
    if workflow_data.trigger_type is not None:
        workflow.trigger_type = workflow_data.trigger_type
        if workflow_data.trigger_type == WorkflowTriggerType.CHATBOT.value:
            trigger_config = workflow.trigger_config or {}
            if "chatbot_url" not in trigger_config:
                trigger_config["chatbot_url"] = generate_chatbot_url(workflow_id)
                workflow.trigger_config = trigger_config
    
    if workflow_data.trigger_config is not None:
        new_config = workflow_data.trigger_config.copy()
        if workflow.trigger_type == WorkflowTriggerType.CHATBOT.value:
            new_config["chatbot_url"] = generate_chatbot_url(workflow_id)
        workflow.trigger_config = new_config
    
    if workflow_data.is_active is not None:
        workflow.is_active = workflow_data.is_active
    
    workflow.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(workflow)
    
    return workflow_to_response(workflow, db)


@router.delete("/{workflow_id}")
@require_permission(Resource.WORKFLOWS, Action.DELETE)
def delete_workflow(
    workflow_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    db.delete(workflow)
    db.commit()
    
    return {"message": "Workflow deleted successfully"}


async def execute_workflow_async(
    workflow_id: str,
    execution_id: str,
    trigger_data: Optional[dict],
    db_session_factory,
):
    from jarvisx.workflows.engine import WorkflowEngine
    
    db = db_session_factory()
    try:
        engine = WorkflowEngine(db)
        await engine.execute(workflow_id, execution_id, trigger_data)
    finally:
        db.close()


@router.post("/{workflow_id}/execute", response_model=ExecuteWorkflowResponse)
@require_permission(Resource.WORKFLOWS, Action.EXECUTE)
def execute_workflow(
    workflow_id: str,
    request: ExecuteWorkflowRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    if not workflow.is_active:
        raise HTTPException(status_code=400, detail="Workflow is not active")
    
    execution = WorkflowExecution(
        id=generate_id(),
        workflow_id=workflow_id,
        status=WorkflowExecutionStatus.PENDING.value,
        trigger_type=WorkflowTriggerType.MANUAL.value,
        trigger_data=request.trigger_data,
    )
    
    db.add(execution)
    db.commit()
    db.refresh(execution)
    
    from jarvisx.database.session import SessionLocal
    background_tasks.add_task(
        execute_workflow_async,
        workflow_id,
        execution.id,
        request.trigger_data,
        SessionLocal,
    )
    
    return ExecuteWorkflowResponse(
        execution_id=execution.id,
        status=execution.status,
        message="Workflow execution started",
    )


@router.get("/{workflow_id}/executions", response_model=ExecutionListResponse)
@require_permission(Resource.WORKFLOWS, Action.VIEW)
def list_executions(
    workflow_id: str,
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    query = db.query(WorkflowExecution).filter(WorkflowExecution.workflow_id == workflow_id)
    
    if status:
        query = query.filter(WorkflowExecution.status == status)
    
    total = query.count()
    executions = query.order_by(WorkflowExecution.created_at.desc()).offset(offset).limit(limit).all()
    
    return ExecutionListResponse(
        executions=[execution_to_response(e) for e in executions],
        total=total,
    )


@router.get("/executions/{execution_id}", response_model=WorkflowExecutionResponse)
@require_permission(Resource.WORKFLOWS, Action.VIEW)
def get_execution(
    execution_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    execution = db.query(WorkflowExecution).filter(WorkflowExecution.id == execution_id).first()
    
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    return execution_to_response(execution, include_logs=True)


@router.get("/executions/{execution_id}/output")
@require_permission(Resource.WORKFLOWS, Action.VIEW)
def get_execution_output(
    execution_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    execution = db.query(WorkflowExecution).filter(WorkflowExecution.id == execution_id).first()
    
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    logs = db.query(WorkflowExecutionLog).filter(
        WorkflowExecutionLog.execution_id == execution_id
    ).order_by(WorkflowExecutionLog.completed_at.desc()).all()
    
    final_output = None
    all_outputs = {}
    
    for log in logs:
        if log.output_data:
            all_outputs[log.node_id] = {
                "node_type": log.node_type,
                "status": log.status,
                "output": log.output_data,
                "completed_at": log.completed_at.isoformat() if log.completed_at else None
            }
            if final_output is None and log.status == "completed":
                final_output = log.output_data
    
    return {
        "execution_id": execution_id,
        "workflow_id": execution.workflow_id,
        "status": execution.status,
        "final_output": final_output,
        "node_outputs": all_outputs,
        "started_at": execution.started_at.isoformat() if execution.started_at else None,
        "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
        "error_message": execution.error_message
    }


webhooks_router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


@webhooks_router.post("/{workflow_id}")
async def webhook_trigger(
    workflow_id: str,
    background_tasks: BackgroundTasks,
    request_body: dict = None,
    db: Session = Depends(get_db),
):
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    if not workflow.is_active:
        raise HTTPException(status_code=400, detail="Workflow is not active")
    
    if workflow.trigger_type != WorkflowTriggerType.WEBHOOK.value:
        raise HTTPException(status_code=400, detail="Workflow is not configured for webhook triggers")
    
    execution = WorkflowExecution(
        id=generate_id(),
        workflow_id=workflow_id,
        status=WorkflowExecutionStatus.PENDING.value,
        trigger_type=WorkflowTriggerType.WEBHOOK.value,
        trigger_data=request_body,
    )
    
    db.add(execution)
    db.commit()
    db.refresh(execution)
    
    from jarvisx.database.session import SessionLocal
    background_tasks.add_task(
        execute_workflow_async,
        workflow_id,
        execution.id,
        request_body,
        SessionLocal,
    )
    
    return {
        "execution_id": execution.id,
        "status": "accepted",
        "message": "Webhook received, workflow execution started",
    }


def _snapshot_version(db: Session, workflow: Workflow, user_id: Optional[str] = None):
    if not workflow.definition:
        return

    last_version = db.query(WorkflowVersion).filter(
        WorkflowVersion.workflow_id == workflow.id
    ).order_by(WorkflowVersion.version_number.desc()).first()

    version_number = (last_version.version_number + 1) if last_version else 1

    old_def = workflow.definition or {}
    old_nodes = len(old_def.get("nodes", []))
    old_edges = len(old_def.get("edges", []))
    summary = f"v{version_number}: {old_nodes} nodes, {old_edges} edges"

    version = WorkflowVersion(
        id=generate_id(),
        workflow_id=workflow.id,
        version_number=version_number,
        definition=workflow.definition,
        trigger_config=workflow.trigger_config,
        change_summary=summary,
        created_by=user_id,
        created_at=datetime.utcnow(),
    )
    db.add(version)
    db.flush()


@router.get("/{workflow_id}/versions")
@require_permission(Resource.WORKFLOWS, Action.VIEW)
def list_versions(
    workflow_id: str,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    versions = db.query(WorkflowVersion).filter(
        WorkflowVersion.workflow_id == workflow_id
    ).order_by(WorkflowVersion.version_number.desc()).limit(limit).all()

    return {
        "versions": [
            {
                "id": v.id,
                "version_number": v.version_number,
                "change_summary": v.change_summary,
                "created_by": v.created_by,
                "created_at": v.created_at.isoformat() if v.created_at else None,
            }
            for v in versions
        ]
    }


@router.get("/{workflow_id}/versions/{version_id}")
@require_permission(Resource.WORKFLOWS, Action.VIEW)
def get_version(
    workflow_id: str,
    version_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    version = db.query(WorkflowVersion).filter(
        WorkflowVersion.id == version_id,
        WorkflowVersion.workflow_id == workflow_id,
    ).first()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    return {
        "id": version.id,
        "version_number": version.version_number,
        "definition": version.definition,
        "trigger_config": version.trigger_config,
        "change_summary": version.change_summary,
        "created_by": version.created_by,
        "created_at": version.created_at.isoformat() if version.created_at else None,
    }


@router.post("/{workflow_id}/versions/{version_id}/restore")
@require_permission(Resource.WORKFLOWS, Action.EDIT)
def restore_version(
    workflow_id: str,
    version_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    version = db.query(WorkflowVersion).filter(
        WorkflowVersion.id == version_id,
        WorkflowVersion.workflow_id == workflow_id,
    ).first()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    _snapshot_version(db, workflow, current_user.user_id)

    workflow.definition = version.definition
    if version.trigger_config:
        workflow.trigger_config = version.trigger_config
    workflow.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(workflow)

    return workflow_to_response(workflow, db)


@router.get("/{workflow_id}/export")
@require_permission(Resource.WORKFLOWS, Action.VIEW)
def export_workflow(
    workflow_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    return {
        "name": workflow.name,
        "description": workflow.description,
        "definition": workflow.definition,
        "trigger_type": workflow.trigger_type,
        "trigger_config": workflow.trigger_config,
        "exported_at": datetime.utcnow().isoformat(),
    }
