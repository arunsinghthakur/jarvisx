from datetime import datetime, timedelta
from typing import List, Optional
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session
from pydantic import BaseModel

from jarvisx.database.session import get_db
from jarvisx.database.models import (
    Organization, User, Workspace, Workflow, WorkflowExecution,
    Subscription, Agent, MCPServer
)
from jarvisx.config.configs import WORKSPACE_BASE_PATH
from services.api.admin.src.dependencies import get_current_user, CurrentUser

router = APIRouter(prefix="/api/platform", tags=["platform"])


def require_platform_admin(current_user: CurrentUser):
    if not current_user.is_platform_admin:
        raise HTTPException(
            status_code=403,
            detail="Platform admin access required"
        )


class PlatformOverview(BaseModel):
    total_organizations: int
    active_organizations: int
    inactive_organizations: int
    total_users: int
    total_workspaces: int
    total_workflows: int
    total_agents: int
    system_agents: int
    custom_agents: int
    total_mcps: int
    system_mcps: int
    custom_mcps: int


class PlatformOverviewResponse(BaseModel):
    overview: PlatformOverview


class OrganizationMetrics(BaseModel):
    id: str
    name: str
    description: Optional[str]
    is_active: bool
    is_platform_admin: bool
    created_at: datetime
    user_count: int
    workspace_count: int
    workflow_count: int
    execution_count_30d: int
    subscription_plan: Optional[str]
    subscription_status: Optional[str]


class OrganizationsListResponse(BaseModel):
    organizations: List[OrganizationMetrics]
    total: int


class UsageTrendPoint(BaseModel):
    date: str
    organizations: int
    users: int
    workspaces: int
    executions: int


class PlatformUsageTrendsResponse(BaseModel):
    trends: List[UsageTrendPoint]
    period_days: int


class PlanDistribution(BaseModel):
    plan: str
    count: int
    total_mrr: int


class SubscriptionInfo(BaseModel):
    organization_id: str
    organization_name: str
    plan: str
    status: str
    mrr: int
    next_billing_date: Optional[datetime]


class PlatformBillingSummary(BaseModel):
    total_mrr: int
    revenue_30d: int
    total_subscriptions: int
    active_subscriptions: int
    past_due_count: int
    past_due_amount: int


class PlatformBillingResponse(BaseModel):
    summary: PlatformBillingSummary
    plan_distribution: List[PlanDistribution]
    subscriptions: List[SubscriptionInfo]


@router.get("/overview", response_model=PlatformOverviewResponse)
def get_platform_overview(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    require_platform_admin(current_user)
    
    total_orgs = db.query(Organization).count()
    active_orgs = db.query(Organization).filter(Organization.is_active == True).count()
    inactive_orgs = total_orgs - active_orgs
    
    total_users = db.query(User).count()
    total_workspaces = db.query(Workspace).count()
    total_workflows = db.query(Workflow).count()
    
    total_agents = db.query(Agent).count()
    system_agents = db.query(Agent).filter(Agent.is_system_agent == True).count()
    custom_agents = total_agents - system_agents
    
    total_mcps = db.query(MCPServer).count()
    system_mcps = db.query(MCPServer).filter(MCPServer.is_system_server == True).count()
    custom_mcps = total_mcps - system_mcps
    
    overview = PlatformOverview(
        total_organizations=total_orgs,
        active_organizations=active_orgs,
        inactive_organizations=inactive_orgs,
        total_users=total_users,
        total_workspaces=total_workspaces,
        total_workflows=total_workflows,
        total_agents=total_agents,
        system_agents=system_agents,
        custom_agents=custom_agents,
        total_mcps=total_mcps,
        system_mcps=system_mcps,
        custom_mcps=custom_mcps,
    )
    
    return PlatformOverviewResponse(overview=overview)


@router.get("/organizations", response_model=OrganizationsListResponse)
def get_platform_organizations(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    include_inactive: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    require_platform_admin(current_user)
    
    query = db.query(Organization)
    if not include_inactive:
        query = query.filter(Organization.is_active == True)
    
    total = query.count()
    organizations = query.order_by(Organization.created_at.desc()).offset(skip).limit(limit).all()
    
    now = datetime.utcnow()
    thirty_days_ago = now - timedelta(days=30)
    
    result = []
    for org in organizations:
        user_count = db.query(User).filter(User.organization_id == org.id).count()
        
        workspace_ids = [
            ws.id for ws in db.query(Workspace.id).filter(
                Workspace.organization_id == org.id
            ).all()
        ]
        workspace_count = len(workspace_ids)
        
        if workspace_ids:
            workflow_count = db.query(Workflow).filter(
                Workflow.workspace_id.in_(workspace_ids)
            ).count()
            
            workflow_ids = [
                wf.id for wf in db.query(Workflow.id).filter(
                    Workflow.workspace_id.in_(workspace_ids)
                ).all()
            ]
            
            if workflow_ids:
                execution_count_30d = db.query(WorkflowExecution).filter(
                    WorkflowExecution.workflow_id.in_(workflow_ids),
                    WorkflowExecution.created_at >= thirty_days_ago
                ).count()
            else:
                execution_count_30d = 0
        else:
            workflow_count = 0
            execution_count_30d = 0
        
        subscription = db.query(Subscription).filter(
            Subscription.organization_id == org.id
        ).first()
        
        result.append(OrganizationMetrics(
            id=org.id,
            name=org.name,
            description=org.description,
            is_active=org.is_active,
            is_platform_admin=org.is_platform_admin,
            created_at=org.created_at,
            user_count=user_count,
            workspace_count=workspace_count,
            workflow_count=workflow_count,
            execution_count_30d=execution_count_30d,
            subscription_plan=subscription.plan if subscription else "free",
            subscription_status=subscription.status if subscription else "active",
        ))
    
    return OrganizationsListResponse(organizations=result, total=total)


@router.get("/usage-trends", response_model=PlatformUsageTrendsResponse)
def get_platform_usage_trends(
    days: int = Query(30, ge=7, le=90),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    require_platform_admin(current_user)
    
    now = datetime.utcnow()
    start_date = now - timedelta(days=days)
    
    trends = []
    
    for i in range(days):
        day = start_date + timedelta(days=i)
        day_end = day + timedelta(days=1)
        date_str = day.strftime("%Y-%m-%d")
        
        orgs_created = db.query(Organization).filter(
            Organization.created_at < day_end
        ).count()
        
        users_created = db.query(User).filter(
            User.created_at < day_end
        ).count()
        
        workspaces_created = db.query(Workspace).filter(
            Workspace.created_at < day_end
        ).count()
        
        executions_on_day = db.query(WorkflowExecution).filter(
            WorkflowExecution.created_at >= day,
            WorkflowExecution.created_at < day_end
        ).count()
        
        trends.append(UsageTrendPoint(
            date=date_str,
            organizations=orgs_created,
            users=users_created,
            workspaces=workspaces_created,
            executions=executions_on_day,
        ))
    
    return PlatformUsageTrendsResponse(trends=trends, period_days=days)


@router.get("/billing", response_model=PlatformBillingResponse)
def get_platform_billing(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    require_platform_admin(current_user)
    
    PLAN_PRICES = {
        "free": 0,
        "starter": 2900,
        "pro": 9900,
        "business": 29900,
        "enterprise": 99900,
    }
    
    subscriptions_query = db.query(Subscription).all()
    
    total_mrr = 0
    active_subscriptions = 0
    past_due_count = 0
    past_due_amount = 0
    plan_counts = {}
    plan_mrr = {}
    subscription_list = []
    
    for sub in subscriptions_query:
        plan = sub.plan or "free"
        price = PLAN_PRICES.get(plan, 0)
        
        org = db.query(Organization).filter(Organization.id == sub.organization_id).first()
        org_name = org.name if org else "Unknown"
        
        if sub.status == "active":
            total_mrr += price
            active_subscriptions += 1
        elif sub.status == "past_due":
            past_due_count += 1
            past_due_amount += price
        
        if plan not in plan_counts:
            plan_counts[plan] = 0
            plan_mrr[plan] = 0
        plan_counts[plan] += 1
        if sub.status == "active":
            plan_mrr[plan] += price
        
        subscription_list.append(SubscriptionInfo(
            organization_id=sub.organization_id,
            organization_name=org_name,
            plan=plan,
            status=sub.status or "active",
            mrr=price if sub.status == "active" else 0,
            next_billing_date=sub.current_period_end,
        ))
    
    orgs_without_subscription = db.query(Organization).filter(
        ~Organization.id.in_([s.organization_id for s in subscriptions_query])
    ).all()
    
    for org in orgs_without_subscription:
        plan_counts["free"] = plan_counts.get("free", 0) + 1
        subscription_list.append(SubscriptionInfo(
            organization_id=org.id,
            organization_name=org.name,
            plan="free",
            status="active",
            mrr=0,
            next_billing_date=None,
        ))
    
    plan_distribution = [
        PlanDistribution(plan=plan, count=count, total_mrr=plan_mrr.get(plan, 0))
        for plan, count in sorted(plan_counts.items(), key=lambda x: PLAN_PRICES.get(x[0], 0))
    ]
    
    total_subscriptions = len(subscriptions_query) + len(orgs_without_subscription)
    
    summary = PlatformBillingSummary(
        total_mrr=total_mrr,
        revenue_30d=total_mrr,
        total_subscriptions=total_subscriptions,
        active_subscriptions=active_subscriptions + len(orgs_without_subscription),
        past_due_count=past_due_count,
        past_due_amount=past_due_amount,
    )
    
    return PlatformBillingResponse(
        summary=summary,
        plan_distribution=plan_distribution,
        subscriptions=subscription_list,
    )


@router.get("/health")
def platform_health(
    current_user: CurrentUser = Depends(get_current_user),
):
    require_platform_admin(current_user)
    return {"status": "healthy", "platform_admin": True}


class DirectoryItem(BaseModel):
    name: str
    path: str
    is_directory: bool


class BrowseDirectoriesResponse(BaseModel):
    current_path: str
    base_path: str
    directories: List[DirectoryItem]
    can_go_up: bool


class FileItem(BaseModel):
    name: str
    path: str
    size_bytes: int
    extension: str
    modified_at: Optional[str]


class BrowseFilesResponse(BaseModel):
    current_path: str
    base_path: str
    files: List[FileItem]
    directories: List[DirectoryItem]
    can_go_up: bool


@router.get("/browse-directories", response_model=BrowseDirectoriesResponse)
def browse_directories(
    path: str = Query(default="", description="Relative path from workspace base"),
    current_user: CurrentUser = Depends(get_current_user),
):
    base_path = Path(WORKSPACE_BASE_PATH)
    base_path.mkdir(parents=True, exist_ok=True)
    
    if path:
        target_path = base_path / path
    else:
        target_path = base_path
    
    target_path = target_path.resolve()
    if not str(target_path).startswith(str(base_path.resolve())):
        raise HTTPException(status_code=400, detail="Invalid path - cannot navigate outside workspace")
    
    if not target_path.exists():
        target_path.mkdir(parents=True, exist_ok=True)
    
    if not target_path.is_dir():
        raise HTTPException(status_code=400, detail="Path is not a directory")
    
    directories = []
    try:
        for item in sorted(target_path.iterdir()):
            if item.is_dir() and not item.name.startswith('.'):
                rel_path = str(item.relative_to(base_path))
                directories.append(DirectoryItem(
                    name=item.name,
                    path=rel_path,
                    is_directory=True
                ))
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied to read directory")
    
    current_rel_path = str(target_path.relative_to(base_path)) if target_path != base_path else ""
    can_go_up = target_path != base_path
    
    return BrowseDirectoriesResponse(
        current_path=current_rel_path,
        base_path=str(base_path),
        directories=directories,
        can_go_up=can_go_up
    )


@router.get("/browse-files", response_model=BrowseFilesResponse)
def browse_files(
    path: str = Query(default="", description="Relative path from workspace base"),
    extensions: str = Query(default="", description="Comma-separated list of extensions to filter (e.g., txt,json,md)"),
    current_user: CurrentUser = Depends(get_current_user),
):
    base_path = Path(WORKSPACE_BASE_PATH)
    base_path.mkdir(parents=True, exist_ok=True)
    
    if path:
        target_path = base_path / path
    else:
        target_path = base_path
    
    target_path = target_path.resolve()
    if not str(target_path).startswith(str(base_path.resolve())):
        raise HTTPException(status_code=400, detail="Invalid path - cannot navigate outside workspace")
    
    if not target_path.exists():
        raise HTTPException(status_code=404, detail="Path does not exist")
    
    if not target_path.is_dir():
        raise HTTPException(status_code=400, detail="Path is not a directory")
    
    ext_filter = set()
    if extensions:
        ext_filter = {f".{ext.strip().lower().lstrip('.')}" for ext in extensions.split(",")}
    
    files = []
    directories = []
    
    try:
        for item in sorted(target_path.iterdir()):
            if item.name.startswith('.'):
                continue
            
            if item.is_dir():
                rel_path = str(item.relative_to(base_path))
                directories.append(DirectoryItem(
                    name=item.name,
                    path=rel_path,
                    is_directory=True
                ))
            elif item.is_file():
                ext = item.suffix.lower()
                if ext_filter and ext not in ext_filter:
                    continue
                
                rel_path = str(item.relative_to(base_path))
                stat = item.stat()
                files.append(FileItem(
                    name=item.name,
                    path=rel_path,
                    size_bytes=stat.st_size,
                    extension=ext.lstrip('.') if ext else "",
                    modified_at=datetime.fromtimestamp(stat.st_mtime).isoformat()
                ))
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied to read directory")
    
    current_rel_path = str(target_path.relative_to(base_path)) if target_path != base_path else ""
    can_go_up = target_path != base_path
    
    return BrowseFilesResponse(
        current_path=current_rel_path,
        base_path=str(base_path),
        files=files,
        directories=directories,
        can_go_up=can_go_up
    )
