from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum


class BillingPlan(str, Enum):
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class PlanDetails(BaseModel):
    id: str
    name: str
    price: int
    currency: str = "USD"
    interval: str = "month"
    features: List[str]
    limits: dict
    is_popular: bool = False


class SubscriptionResponse(BaseModel):
    id: str
    organization_id: str
    plan: str
    status: str
    current_period_start: datetime
    current_period_end: datetime
    cancel_at_period_end: bool


class SubscriptionUpdate(BaseModel):
    plan: Optional[str] = None
    cancel_at_period_end: Optional[bool] = None


class UsageRecordCreate(BaseModel):
    organization_id: str
    workspace_id: Optional[str] = None
    usage_type: str
    quantity: int = 1
    unit_cost: int = 0
    usage_metadata: Optional[dict] = None


class UsageRecordResponse(BaseModel):
    id: str
    organization_id: str
    workspace_id: Optional[str]
    usage_type: str
    quantity: int
    unit_cost: int
    usage_metadata: Optional[dict]
    recorded_at: datetime


class UsageSummary(BaseModel):
    usage_type: str
    total_quantity: int
    total_cost: int
    percentage_of_limit: float


class InvoiceResponse(BaseModel):
    id: str
    organization_id: str
    invoice_number: str
    period_start: datetime
    period_end: datetime
    subtotal: int
    tax: int
    total: int
    currency: str
    status: str
    paid_at: Optional[datetime]
    created_at: datetime


class BillingOverview(BaseModel):
    subscription: Optional[SubscriptionResponse]
    current_usage: List[UsageSummary]
    upcoming_invoice_estimate: int
    recent_invoices: List[InvoiceResponse]

