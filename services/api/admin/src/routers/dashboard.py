from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, case, and_
from sqlalchemy.orm import Session

from jarvisx.database.session import get_db
from jarvisx.database.models import (
    Workspace, Workflow, WorkflowExecution, WorkflowExecutionStatus
)
from services.api.admin.src.models.dashboard import (
    DashboardStats, DashboardStatsResponse, StatTrend,
    ActivityItem, ActivityResponse,
    ExecutionTrendPoint, ExecutionTrendsResponse,
)
from services.api.admin.src.dependencies import get_current_user, CurrentUser

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStatsResponse)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    now = datetime.utcnow()
    period_start = now - timedelta(days=7)
    prev_period_start = period_start - timedelta(days=7)

    org_id = current_user.organization.id

    workspace_ids = [
        ws.id for ws in db.query(Workspace.id).filter(
            Workspace.organization_id == org_id
        ).all()
    ]

    total_workspaces = db.query(Workspace).filter(
        Workspace.organization_id == org_id
    ).count()

    active_workspaces = db.query(Workspace).filter(
        Workspace.organization_id == org_id,
        Workspace.is_active == True
    ).count()

    if workspace_ids:
        total_workflows = db.query(Workflow).filter(
            Workflow.workspace_id.in_(workspace_ids)
        ).count()

        active_workflows = db.query(Workflow).filter(
            Workflow.workspace_id.in_(workspace_ids),
            Workflow.is_active == True
        ).count()

        workflow_ids = [
            wf.id for wf in db.query(Workflow.id).filter(
                Workflow.workspace_id.in_(workspace_ids)
            ).all()
        ]
    else:
        total_workflows = 0
        active_workflows = 0
        workflow_ids = []

    if workflow_ids:
        total_executions = db.query(WorkflowExecution).filter(
            WorkflowExecution.workflow_id.in_(workflow_ids)
        ).count()

        successful_executions = db.query(WorkflowExecution).filter(
            WorkflowExecution.workflow_id.in_(workflow_ids),
            WorkflowExecution.status == WorkflowExecutionStatus.COMPLETED.value
        ).count()

        failed_executions = db.query(WorkflowExecution).filter(
            WorkflowExecution.workflow_id.in_(workflow_ids),
            WorkflowExecution.status == WorkflowExecutionStatus.FAILED.value
        ).count()

        current_period_executions = db.query(WorkflowExecution).filter(
            WorkflowExecution.workflow_id.in_(workflow_ids),
            WorkflowExecution.created_at >= period_start
        ).count()

        prev_period_executions = db.query(WorkflowExecution).filter(
            WorkflowExecution.workflow_id.in_(workflow_ids),
            WorkflowExecution.created_at >= prev_period_start,
            WorkflowExecution.created_at < period_start
        ).count()

        exec_change = current_period_executions - prev_period_executions
        exec_change_pct = (
            (exec_change / prev_period_executions * 100) 
            if prev_period_executions > 0 else 0.0
        )

        executions_trend = StatTrend(
            value=current_period_executions,
            change=exec_change,
            change_percent=round(exec_change_pct, 1),
            period_label="vs last 7 days"
        )
    else:
        total_executions = 0
        successful_executions = 0
        failed_executions = 0
        executions_trend = None

    current_workflows = db.query(Workflow).filter(
        Workflow.workspace_id.in_(workspace_ids) if workspace_ids else False,
        Workflow.created_at >= period_start
    ).count() if workspace_ids else 0

    prev_workflows = db.query(Workflow).filter(
        Workflow.workspace_id.in_(workspace_ids) if workspace_ids else False,
        Workflow.created_at >= prev_period_start,
        Workflow.created_at < period_start
    ).count() if workspace_ids else 0

    wf_change = current_workflows - prev_workflows
    wf_change_pct = (wf_change / prev_workflows * 100) if prev_workflows > 0 else 0.0

    workflows_trend = StatTrend(
        value=current_workflows,
        change=wf_change,
        change_percent=round(wf_change_pct, 1),
        period_label="vs last 7 days"
    ) if workspace_ids else None

    stats = DashboardStats(
        total_workspaces=total_workspaces,
        active_workspaces=active_workspaces,
        total_workflows=total_workflows,
        active_workflows=active_workflows,
        total_executions=total_executions,
        successful_executions=successful_executions,
        failed_executions=failed_executions,
        workspaces_trend=None,
        workflows_trend=workflows_trend,
        executions_trend=executions_trend,
    )

    return DashboardStatsResponse(stats=stats)


@router.get("/activity", response_model=ActivityResponse)
def get_dashboard_activity(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    org_id = current_user.organization.id

    workspace_ids = [
        ws.id for ws in db.query(Workspace.id).filter(
            Workspace.organization_id == org_id
        ).all()
    ]

    if not workspace_ids:
        return ActivityResponse(activities=[], total=0)

    workflow_ids = [
        wf.id for wf in db.query(Workflow.id).filter(
            Workflow.workspace_id.in_(workspace_ids)
        ).all()
    ]

    if not workflow_ids:
        return ActivityResponse(activities=[], total=0)

    executions = (
        db.query(WorkflowExecution, Workflow.name.label("workflow_name"))
        .join(Workflow, WorkflowExecution.workflow_id == Workflow.id)
        .filter(WorkflowExecution.workflow_id.in_(workflow_ids))
        .order_by(WorkflowExecution.created_at.desc())
        .limit(limit)
        .all()
    )

    total = db.query(WorkflowExecution).filter(
        WorkflowExecution.workflow_id.in_(workflow_ids)
    ).count()

    activities = []
    for execution, workflow_name in executions:
        if execution.status == WorkflowExecutionStatus.COMPLETED.value:
            activity_type = "workflow_completed"
            title = f"Workflow <strong>{workflow_name}</strong> completed successfully"
        elif execution.status == WorkflowExecutionStatus.FAILED.value:
            activity_type = "workflow_failed"
            title = f"Workflow <strong>{workflow_name}</strong> failed"
        elif execution.status == WorkflowExecutionStatus.RUNNING.value:
            activity_type = "workflow_started"
            title = f"Workflow <strong>{workflow_name}</strong> started"
        else:
            activity_type = "workflow"
            title = f"Workflow <strong>{workflow_name}</strong> is {execution.status}"

        duration = None
        if execution.started_at and execution.completed_at:
            delta = execution.completed_at - execution.started_at
            duration = f"Duration: {delta.total_seconds():.1f}s"

        meta = duration or f"Trigger: {execution.trigger_type}"

        activities.append(ActivityItem(
            id=execution.id,
            type=activity_type,
            title=title,
            timestamp=execution.created_at,
            meta=meta,
            workflow_id=execution.workflow_id,
            execution_id=execution.id,
        ))

    return ActivityResponse(activities=activities, total=total)


@router.get("/execution-trends", response_model=ExecutionTrendsResponse)
def get_execution_trends(
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    org_id = current_user.organization.id
    now = datetime.utcnow()
    start_date = now - timedelta(days=days)

    workspace_ids = [
        ws.id for ws in db.query(Workspace.id).filter(
            Workspace.organization_id == org_id
        ).all()
    ]

    if not workspace_ids:
        return _empty_trends_response(days, start_date)

    workflow_ids = [
        wf.id for wf in db.query(Workflow.id).filter(
            Workflow.workspace_id.in_(workspace_ids)
        ).all()
    ]

    if not workflow_ids:
        return _empty_trends_response(days, start_date)

    date_trunc = func.date(WorkflowExecution.created_at)

    results = (
        db.query(
            date_trunc.label("date"),
            func.sum(
                case(
                    (WorkflowExecution.status == WorkflowExecutionStatus.COMPLETED.value, 1),
                    else_=0
                )
            ).label("success"),
            func.sum(
                case(
                    (WorkflowExecution.status == WorkflowExecutionStatus.FAILED.value, 1),
                    else_=0
                )
            ).label("failed"),
        )
        .filter(
            WorkflowExecution.workflow_id.in_(workflow_ids),
            WorkflowExecution.created_at >= start_date
        )
        .group_by(date_trunc)
        .order_by(date_trunc)
        .all()
    )

    date_map = {str(r.date): {"success": int(r.success), "failed": int(r.failed)} for r in results}

    trends = []
    total_success = 0
    total_failed = 0

    for i in range(days):
        day = start_date + timedelta(days=i)
        date_str = day.strftime("%Y-%m-%d")
        day_name = day.strftime("%a")

        data = date_map.get(date_str, {"success": 0, "failed": 0})
        total_success += data["success"]
        total_failed += data["failed"]

        trends.append(ExecutionTrendPoint(
            name=day_name,
            date=date_str,
            success=data["success"],
            failed=data["failed"],
        ))

    total = total_success + total_failed
    success_rate = (total_success / total * 100) if total > 0 else 0.0

    return ExecutionTrendsResponse(
        trends=trends,
        total_success=total_success,
        total_failed=total_failed,
        success_rate=round(success_rate, 1),
    )


def _empty_trends_response(days: int, start_date: datetime) -> ExecutionTrendsResponse:
    trends = []
    for i in range(days):
        day = start_date + timedelta(days=i)
        trends.append(ExecutionTrendPoint(
            name=day.strftime("%a"),
            date=day.strftime("%Y-%m-%d"),
            success=0,
            failed=0,
        ))
    return ExecutionTrendsResponse(
        trends=trends,
        total_success=0,
        total_failed=0,
        success_rate=0.0,
    )


@router.get("/costs")
def get_cost_summary(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    from jarvisx.database.models import UsageMetric
    from sqlalchemy import func

    org_id = current_user.organization_id
    now = datetime.utcnow()

    def _sum_cost(start):
        result = db.query(func.sum(UsageMetric.estimated_cost_usd)).filter(
            UsageMetric.organization_id == org_id,
            UsageMetric.recorded_at >= start,
        ).scalar()
        return round(float(result or 0), 4)

    def _sum_tokens(start):
        result = db.query(func.sum(UsageMetric.total_tokens)).filter(
            UsageMetric.organization_id == org_id,
            UsageMetric.recorded_at >= start,
        ).scalar()
        return int(result or 0)

    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    return {
        "today": {"cost": _sum_cost(today_start), "tokens": _sum_tokens(today_start)},
        "seven_days": {"cost": _sum_cost(now - timedelta(days=7)), "tokens": _sum_tokens(now - timedelta(days=7))},
        "thirty_days": {"cost": _sum_cost(now - timedelta(days=30)), "tokens": _sum_tokens(now - timedelta(days=30))},
    }


@router.get("/costs/by-workflow")
def get_costs_by_workflow(
    days: int = Query(30, ge=1, le=90),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    from jarvisx.database.models import UsageMetric, Workflow
    from sqlalchemy import func

    org_id = current_user.organization_id
    since = datetime.utcnow() - timedelta(days=days)

    results = db.query(
        UsageMetric.workflow_id,
        func.sum(UsageMetric.estimated_cost_usd).label("total_cost"),
        func.sum(UsageMetric.total_tokens).label("total_tokens"),
        func.count(UsageMetric.id).label("call_count"),
    ).filter(
        UsageMetric.organization_id == org_id,
        UsageMetric.recorded_at >= since,
        UsageMetric.workflow_id.isnot(None),
    ).group_by(UsageMetric.workflow_id).order_by(
        func.sum(UsageMetric.estimated_cost_usd).desc()
    ).limit(limit).all()

    items = []
    for r in results:
        wf = db.query(Workflow.name).filter(Workflow.id == r.workflow_id).first()
        items.append({
            "workflow_id": r.workflow_id,
            "workflow_name": wf.name if wf else "Unknown",
            "total_cost": round(float(r.total_cost or 0), 4),
            "total_tokens": int(r.total_tokens or 0),
            "call_count": r.call_count,
        })

    return {"items": items, "days": days}


@router.get("/costs/by-agent")
def get_costs_by_agent(
    days: int = Query(30, ge=1, le=90),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    from jarvisx.database.models import UsageMetric
    from sqlalchemy import func

    org_id = current_user.organization_id
    since = datetime.utcnow() - timedelta(days=days)

    results = db.query(
        UsageMetric.model_name,
        func.sum(UsageMetric.estimated_cost_usd).label("total_cost"),
        func.sum(UsageMetric.total_tokens).label("total_tokens"),
        func.count(UsageMetric.id).label("call_count"),
    ).filter(
        UsageMetric.organization_id == org_id,
        UsageMetric.recorded_at >= since,
    ).group_by(UsageMetric.model_name).order_by(
        func.sum(UsageMetric.estimated_cost_usd).desc()
    ).limit(limit).all()

    return {
        "items": [
            {
                "model_name": r.model_name or "Unknown",
                "total_cost": round(float(r.total_cost or 0), 4),
                "total_tokens": int(r.total_tokens or 0),
                "call_count": r.call_count,
            }
            for r in results
        ],
        "days": days,
    }


@router.get("/costs/trends")
def get_cost_trends(
    days: int = Query(30, ge=1, le=90),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    from jarvisx.database.models import UsageMetric
    from sqlalchemy import func, cast, Date

    org_id = current_user.organization_id
    since = datetime.utcnow() - timedelta(days=days)

    results = db.query(
        cast(UsageMetric.recorded_at, Date).label("day"),
        func.sum(UsageMetric.estimated_cost_usd).label("cost"),
        func.sum(UsageMetric.total_tokens).label("tokens"),
        func.count(UsageMetric.id).label("calls"),
    ).filter(
        UsageMetric.organization_id == org_id,
        UsageMetric.recorded_at >= since,
    ).group_by(cast(UsageMetric.recorded_at, Date)).order_by(
        cast(UsageMetric.recorded_at, Date)
    ).all()

    return {
        "trends": [
            {
                "date": str(r.day),
                "cost": round(float(r.cost or 0), 4),
                "tokens": int(r.tokens or 0),
                "calls": r.calls,
            }
            for r in results
        ],
        "days": days,
    }
