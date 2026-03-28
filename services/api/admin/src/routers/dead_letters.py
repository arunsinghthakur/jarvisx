from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from jarvisx.database.session import get_db
from jarvisx.database.models import WorkflowDeadLetter, WorkflowExecution, WorkflowExecutionStatus
from jarvisx.common.id_utils import generate_id
from services.api.admin.src.dependencies import get_current_user, CurrentUser

router = APIRouter(prefix="/api/workflows/dead-letters", tags=["dead-letters"])


@router.get("")
def list_dead_letters(
    workflow_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    query = db.query(WorkflowDeadLetter)
    if workflow_id:
        query = query.filter(WorkflowDeadLetter.workflow_id == workflow_id)
    if status:
        query = query.filter(WorkflowDeadLetter.status == status)

    total = query.count()
    items = query.order_by(WorkflowDeadLetter.created_at.desc()).offset(offset).limit(limit).all()

    return {
        "items": [
            {
                "id": dl.id,
                "execution_id": dl.execution_id,
                "workflow_id": dl.workflow_id,
                "node_id": dl.node_id,
                "node_type": dl.node_type,
                "error": dl.error,
                "retry_count": dl.retry_count,
                "status": dl.status,
                "created_at": dl.created_at.isoformat() if dl.created_at else None,
                "resolved_at": dl.resolved_at.isoformat() if dl.resolved_at else None,
            }
            for dl in items
        ],
        "total": total,
    }


@router.post("/{dead_letter_id}/retry")
def retry_dead_letter(
    dead_letter_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    dl = db.query(WorkflowDeadLetter).filter(WorkflowDeadLetter.id == dead_letter_id).first()
    if not dl:
        raise HTTPException(status_code=404, detail="Dead letter not found")

    dl.status = "retried"
    dl.resolved_at = datetime.utcnow()
    db.commit()

    return {"status": "retried", "id": dl.id}


@router.post("/{dead_letter_id}/discard")
def discard_dead_letter(
    dead_letter_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    dl = db.query(WorkflowDeadLetter).filter(WorkflowDeadLetter.id == dead_letter_id).first()
    if not dl:
        raise HTTPException(status_code=404, detail="Dead letter not found")

    dl.status = "discarded"
    dl.resolved_at = datetime.utcnow()
    db.commit()

    return {"status": "discarded", "id": dl.id}
