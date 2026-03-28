from datetime import datetime
from typing import Optional, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from jarvisx.database.session import get_db
from jarvisx.database.models import (
    Workflow, WorkflowExecution, WorkflowExecutionStatus
)
from jarvisx.common.id_utils import generate_id
from jarvisx.workflows.engine import WorkflowEngine
from services.api.admin.src.dependencies import get_current_user, CurrentUser

router = APIRouter(prefix="/api/workflows", tags=["workflow-debug"])


class DebugStartRequest(BaseModel):
    trigger_data: Optional[dict] = None


class DebugInjectRequest(BaseModel):
    node_id: str
    data: dict


class DebugResumeRequest(BaseModel):
    breakpoints: list[str] = []


@router.post("/{workflow_id}/debug/start")
async def debug_start(
    workflow_id: str,
    body: DebugStartRequest = DebugStartRequest(),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    execution = WorkflowExecution(
        id=generate_id(),
        workflow_id=workflow_id,
        status=WorkflowExecutionStatus.PENDING.value,
        trigger_type="debug",
        trigger_data=body.trigger_data,
    )
    db.add(execution)
    db.commit()

    engine = WorkflowEngine(db)
    state = await engine.debug_start(workflow_id, execution.id, body.trigger_data)

    return {"execution_id": execution.id, "state": state}


@router.post("/{workflow_id}/debug/{execution_id}/step")
async def debug_step(
    workflow_id: str,
    execution_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    engine = WorkflowEngine(db)
    try:
        state = await engine.debug_step(workflow_id, execution_id)
        return {"state": state}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{workflow_id}/debug/{execution_id}/resume")
async def debug_resume(
    workflow_id: str,
    execution_id: str,
    body: DebugResumeRequest = DebugResumeRequest(),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    engine = WorkflowEngine(db)
    breakpoints = set(body.breakpoints)
    results = []

    for _ in range(1000):
        state = await engine.debug_step(workflow_id, execution_id)
        results.append(state)
        if state.get("done"):
            break
        current = state.get("current_node")
        if current and current in breakpoints:
            break

    return {"state": results[-1] if results else {}, "steps": len(results)}


@router.get("/{workflow_id}/debug/{execution_id}/state")
def debug_get_state(
    workflow_id: str,
    execution_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    engine = WorkflowEngine(db)
    try:
        state = engine.debug_get_state(execution_id)
        return {"state": state}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{workflow_id}/debug/{execution_id}/inject")
def debug_inject(
    workflow_id: str,
    execution_id: str,
    body: DebugInjectRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    execution = db.query(WorkflowExecution).filter(
        WorkflowExecution.id == execution_id
    ).first()
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    meta = execution.execution_metadata or {}
    state = meta.get("debug_state", {})
    node_outputs = state.get("node_outputs", {})
    node_outputs[body.node_id] = body.data
    state["node_outputs"] = node_outputs
    execution.execution_metadata = {**meta, "debug_state": state}
    db.commit()

    return {"status": "injected", "node_id": body.node_id}


@router.post("/{workflow_id}/debug/{execution_id}/stop")
def debug_stop(
    workflow_id: str,
    execution_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    execution = db.query(WorkflowExecution).filter(
        WorkflowExecution.id == execution_id
    ).first()
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    execution.status = WorkflowExecutionStatus.CANCELLED.value
    execution.completed_at = datetime.utcnow()
    db.commit()

    return {"status": "stopped", "execution_id": execution_id}
