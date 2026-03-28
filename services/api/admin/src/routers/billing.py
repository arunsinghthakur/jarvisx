from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime, timedelta
import uuid

from jarvisx.database.models import Organization, Subscription, UsageRecord, Invoice
from jarvisx.database.session import get_db
from services.api.admin.src.models.billing import (
    PlanDetails, SubscriptionResponse, SubscriptionUpdate,
    UsageRecordCreate, UsageRecordResponse, UsageSummary,
    InvoiceResponse, BillingOverview
)
from services.api.admin.src.dependencies import OrganizationContext, get_organization_context

router = APIRouter(prefix="/api/billing", tags=["billing"])

PLANS = {
    "free": PlanDetails(
        id="free",
        name="Free",
        price=0,
        currency="USD",
        interval="month",
        features=[
            "1 Organization",
            "2 Tenants",
            "1 Team (3 members)",
            "5 Agents",
            "1,000 API calls/month",
            "Community support",
        ],
        limits={
            "organizations": 1,
            "workspaces": 2,
            "teams": 1,
            "team_members": 3,
            "agents": 5,
            "api_calls": 1000,
            "storage_mb": 100,
        },
        is_popular=False
    ),
    "starter": PlanDetails(
        id="starter",
        name="Starter",
        price=2900,
        currency="USD",
        interval="month",
        features=[
            "3 Organizations",
            "10 Tenants",
            "3 Teams (10 members each)",
            "20 Agents",
            "50,000 API calls/month",
            "Email support",
            "Basic analytics",
        ],
        limits={
            "organizations": 3,
            "workspaces": 10,
            "teams": 3,
            "team_members": 10,
            "agents": 20,
            "api_calls": 50000,
            "storage_mb": 1000,
        },
        is_popular=False
    ),
    "professional": PlanDetails(
        id="professional",
        name="Professional",
        price=9900,
        currency="USD",
        interval="month",
        features=[
            "10 Organizations",
            "50 Tenants",
            "10 Teams (25 members each)",
            "Unlimited Agents",
            "500,000 API calls/month",
            "Priority support",
            "Advanced analytics",
            "Custom integrations",
            "SSO/SAML",
        ],
        limits={
            "organizations": 10,
            "workspaces": 50,
            "teams": 10,
            "team_members": 25,
            "agents": -1,
            "api_calls": 500000,
            "storage_mb": 10000,
        },
        is_popular=True
    ),
    "enterprise": PlanDetails(
        id="enterprise",
        name="Enterprise",
        price=0,
        currency="USD",
        interval="month",
        features=[
            "Unlimited Organizations",
            "Unlimited Tenants",
            "Unlimited Teams",
            "Unlimited Agents",
            "Unlimited API calls",
            "24/7 dedicated support",
            "Custom SLA",
            "On-premise deployment",
            "Advanced security",
            "Custom development",
        ],
        limits={
            "organizations": -1,
            "workspaces": -1,
            "teams": -1,
            "team_members": -1,
            "agents": -1,
            "api_calls": -1,
            "storage_mb": -1,
        },
        is_popular=False
    ),
}


@router.get("/plans", response_model=List[PlanDetails])
def get_available_plans():
    return list(PLANS.values())


@router.get("/plans/{plan_id}", response_model=PlanDetails)
def get_plan_details(plan_id: str):
    if plan_id not in PLANS:
        raise HTTPException(status_code=404, detail="Plan not found")
    return PLANS[plan_id]


@router.get("/subscription/{organization_id}", response_model=SubscriptionResponse)
def get_subscription(
    organization_id: str, 
    db: Session = Depends(get_db),
    org_ctx: OrganizationContext = Depends(get_organization_context)
):
    if not org_ctx.can_access_organization(organization_id):
        raise HTTPException(status_code=403, detail="Access denied to this organization's billing")
    
    org = db.query(Organization).filter(Organization.id == organization_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    subscription = db.query(Subscription).filter(
        Subscription.organization_id == organization_id
    ).first()
    
    if not subscription:
        now = datetime.utcnow()
        subscription = Subscription(
            id=str(uuid.uuid4()),
            organization_id=organization_id,
            plan="free",
            status="active",
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
        )
        db.add(subscription)
        db.commit()
        db.refresh(subscription)
    
    return SubscriptionResponse(
        id=subscription.id,
        organization_id=subscription.organization_id,
        plan=subscription.plan,
        status=subscription.status,
        current_period_start=subscription.current_period_start,
        current_period_end=subscription.current_period_end,
        cancel_at_period_end=subscription.cancel_at_period_end,
    )


@router.put("/subscription/{organization_id}", response_model=SubscriptionResponse)
def update_subscription(
    organization_id: str,
    update_data: SubscriptionUpdate,
    db: Session = Depends(get_db),
    org_ctx: OrganizationContext = Depends(get_organization_context)
):
    if not org_ctx.can_access_organization(organization_id):
        raise HTTPException(status_code=403, detail="Access denied to this organization's billing")
    
    subscription = db.query(Subscription).filter(
        Subscription.organization_id == organization_id
    ).first()
    
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    if update_data.plan is not None:
        if update_data.plan not in PLANS:
            raise HTTPException(status_code=400, detail="Invalid plan")
        subscription.plan = update_data.plan
    
    if update_data.cancel_at_period_end is not None:
        subscription.cancel_at_period_end = update_data.cancel_at_period_end
    
    subscription.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(subscription)
    
    return SubscriptionResponse(
        id=subscription.id,
        organization_id=subscription.organization_id,
        plan=subscription.plan,
        status=subscription.status,
        current_period_start=subscription.current_period_start,
        current_period_end=subscription.current_period_end,
        cancel_at_period_end=subscription.cancel_at_period_end,
    )


@router.get("/usage/{organization_id}", response_model=List[UsageSummary])
def get_usage_summary(
    organization_id: str,
    period_start: Optional[datetime] = None,
    period_end: Optional[datetime] = None,
    db: Session = Depends(get_db),
    org_ctx: OrganizationContext = Depends(get_organization_context)
):
    if not org_ctx.can_access_organization(organization_id):
        raise HTTPException(status_code=403, detail="Access denied to this organization's usage data")
    
    if not period_start:
        period_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if not period_end:
        period_end = datetime.utcnow()
    
    subscription = db.query(Subscription).filter(
        Subscription.organization_id == organization_id
    ).first()
    
    plan_limits = PLANS.get(subscription.plan if subscription else "free", PLANS["free"]).limits
    
    usage_query = db.query(
        UsageRecord.usage_type,
        func.sum(UsageRecord.quantity).label("total_quantity"),
        func.sum(UsageRecord.quantity * UsageRecord.unit_cost).label("total_cost")
    ).filter(
        UsageRecord.organization_id == organization_id,
        UsageRecord.recorded_at >= period_start,
        UsageRecord.recorded_at <= period_end
    ).group_by(UsageRecord.usage_type).all()
    
    usage_types = {
        "api_calls": {"name": "API Calls", "limit_key": "api_calls"},
        "agent_runs": {"name": "Agent Runs", "limit_key": "agents"},
        "storage": {"name": "Storage (MB)", "limit_key": "storage_mb"},
        "tokens": {"name": "Tokens", "limit_key": "api_calls"},
    }
    
    summaries = []
    usage_dict = {u.usage_type: {"quantity": u.total_quantity or 0, "cost": u.total_cost or 0} for u in usage_query}
    
    for usage_type, info in usage_types.items():
        data = usage_dict.get(usage_type, {"quantity": 0, "cost": 0})
        limit = plan_limits.get(info["limit_key"], 0)
        percentage = (data["quantity"] / limit * 100) if limit > 0 else 0
        
        summaries.append(UsageSummary(
            usage_type=usage_type,
            total_quantity=data["quantity"],
            total_cost=data["cost"],
            percentage_of_limit=min(percentage, 100)
        ))
    
    return summaries


@router.post("/usage", response_model=UsageRecordResponse)
def record_usage(
    usage_data: UsageRecordCreate, 
    db: Session = Depends(get_db),
    org_ctx: OrganizationContext = Depends(get_organization_context)
):
    if not org_ctx.can_access_organization(usage_data.organization_id):
        raise HTTPException(status_code=403, detail="Access denied to record usage for this organization")
    
    usage_record = UsageRecord(
        id=str(uuid.uuid4()),
        organization_id=usage_data.organization_id,
        workspace_id=usage_data.workspace_id,
        usage_type=usage_data.usage_type,
        quantity=usage_data.quantity,
        unit_cost=usage_data.unit_cost,
        usage_metadata=usage_data.usage_metadata,
        recorded_at=datetime.utcnow()
    )
    db.add(usage_record)
    db.commit()
    db.refresh(usage_record)
    
    return UsageRecordResponse(
        id=usage_record.id,
        organization_id=usage_record.organization_id,
        workspace_id=usage_record.workspace_id,
        usage_type=usage_record.usage_type,
        quantity=usage_record.quantity,
        unit_cost=usage_record.unit_cost,
        usage_metadata=usage_record.usage_metadata,
        recorded_at=usage_record.recorded_at,
    )


@router.get("/invoices/{organization_id}", response_model=List[InvoiceResponse])
def get_invoices(
    organization_id: str,
    limit: int = 12,
    db: Session = Depends(get_db),
    org_ctx: OrganizationContext = Depends(get_organization_context)
):
    if not org_ctx.can_access_organization(organization_id):
        raise HTTPException(status_code=403, detail="Access denied to this organization's invoices")
    
    invoices = db.query(Invoice).filter(
        Invoice.organization_id == organization_id
    ).order_by(Invoice.created_at.desc()).limit(limit).all()
    
    return [
        InvoiceResponse(
            id=inv.id,
            organization_id=inv.organization_id,
            invoice_number=inv.invoice_number,
            period_start=inv.period_start,
            period_end=inv.period_end,
            subtotal=inv.subtotal,
            tax=inv.tax,
            total=inv.total,
            currency=inv.currency,
            status=inv.status,
            paid_at=inv.paid_at,
            created_at=inv.created_at,
        )
        for inv in invoices
    ]


@router.get("/overview/{organization_id}", response_model=BillingOverview)
def get_billing_overview(
    organization_id: str, 
    db: Session = Depends(get_db),
    org_ctx: OrganizationContext = Depends(get_organization_context)
):
    if not org_ctx.can_access_organization(organization_id):
        raise HTTPException(status_code=403, detail="Access denied to this organization's billing")
    
    subscription_response = get_subscription(organization_id, db, org_ctx)
    usage_summary = get_usage_summary(organization_id, db=db, org_ctx=org_ctx)
    invoices = get_invoices(organization_id, limit=5, db=db, org_ctx=org_ctx)
    
    plan = PLANS.get(subscription_response.plan, PLANS["free"])
    upcoming_estimate = plan.price
    
    return BillingOverview(
        subscription=subscription_response,
        current_usage=usage_summary,
        upcoming_invoice_estimate=upcoming_estimate,
        recent_invoices=invoices,
    )
