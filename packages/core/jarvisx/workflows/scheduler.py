import logging
import asyncio
from datetime import datetime
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

from jarvisx.database.models import (
    Workflow, WorkflowExecution, WorkflowTriggerType, WorkflowExecutionStatus
)
from jarvisx.common.id_utils import generate_id
from jarvisx.database.session import SessionLocal

logger = logging.getLogger(__name__)

_scheduler: Optional[AsyncIOScheduler] = None


def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler()
    return _scheduler


async def execute_scheduled_workflow(workflow_id: str):
    from jarvisx.workflows.engine import WorkflowEngine
    
    db = SessionLocal()
    try:
        workflow = db.query(Workflow).filter(
            Workflow.id == workflow_id,
            Workflow.is_active == True
        ).first()
        
        if not workflow:
            logger.warning(f"Scheduled workflow {workflow_id} not found or inactive")
            return
        
        execution = WorkflowExecution(
            id=generate_id(),
            workflow_id=workflow_id,
            status=WorkflowExecutionStatus.PENDING.value,
            trigger_type=WorkflowTriggerType.SCHEDULE.value,
            trigger_data={"scheduled_time": datetime.utcnow().isoformat()},
        )
        db.add(execution)
        db.commit()
        
        engine = WorkflowEngine(db)
        await engine.execute(workflow_id, execution.id, None)
        
        logger.info(f"Scheduled workflow {workflow_id} executed successfully")
        
    except Exception as e:
        logger.exception(f"Failed to execute scheduled workflow {workflow_id}: {e}")
    finally:
        db.close()


def schedule_workflow(workflow: Workflow):
    scheduler = get_scheduler()
    
    job_id = f"workflow_{workflow.id}"
    
    existing_job = scheduler.get_job(job_id)
    if existing_job:
        scheduler.remove_job(job_id)
    
    if not workflow.is_active:
        logger.info(f"Workflow {workflow.id} is inactive, not scheduling")
        return
    
    if workflow.trigger_type != WorkflowTriggerType.SCHEDULE.value:
        return
    
    trigger_config = workflow.trigger_config or {}
    cron_expr = trigger_config.get("cron")
    
    if not cron_expr:
        logger.warning(f"Workflow {workflow.id} has no cron expression")
        return
    
    try:
        parts = cron_expr.split()
        if len(parts) == 5:
            trigger = CronTrigger(
                minute=parts[0],
                hour=parts[1],
                day=parts[2],
                month=parts[3],
                day_of_week=parts[4],
            )
        else:
            logger.error(f"Invalid cron expression for workflow {workflow.id}: {cron_expr}")
            return
        
        scheduler.add_job(
            execute_scheduled_workflow,
            trigger=trigger,
            args=[workflow.id],
            id=job_id,
            replace_existing=True,
        )
        
        logger.info(f"Scheduled workflow {workflow.id} with cron: {cron_expr}")
        
    except Exception as e:
        logger.exception(f"Failed to schedule workflow {workflow.id}: {e}")


def unschedule_workflow(workflow_id: str):
    scheduler = get_scheduler()
    job_id = f"workflow_{workflow_id}"
    
    try:
        existing_job = scheduler.get_job(job_id)
        if existing_job:
            scheduler.remove_job(job_id)
            logger.info(f"Unscheduled workflow {workflow_id}")
    except Exception as e:
        logger.exception(f"Failed to unschedule workflow {workflow_id}: {e}")


def load_scheduled_workflows(db: Session):
    workflows = db.query(Workflow).filter(
        Workflow.is_active == True,
        Workflow.trigger_type == WorkflowTriggerType.SCHEDULE.value
    ).all()
    
    for workflow in workflows:
        schedule_workflow(workflow)
    
    logger.info(f"Loaded {len(workflows)} scheduled workflows")


def start_scheduler():
    scheduler = get_scheduler()
    if not scheduler.running:
        scheduler.start()
        logger.info("Workflow scheduler started")


def stop_scheduler():
    scheduler = get_scheduler()
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Workflow scheduler stopped")
