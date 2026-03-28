from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class StatTrend(BaseModel):
    value: int
    change: int
    change_percent: float
    period_label: str


class DashboardStats(BaseModel):
    total_workspaces: int
    active_workspaces: int
    total_workflows: int
    active_workflows: int
    total_executions: int
    successful_executions: int
    failed_executions: int
    workspaces_trend: Optional[StatTrend] = None
    workflows_trend: Optional[StatTrend] = None
    executions_trend: Optional[StatTrend] = None


class DashboardStatsResponse(BaseModel):
    stats: DashboardStats


class ActivityItem(BaseModel):
    id: str
    type: str
    title: str
    timestamp: datetime
    meta: Optional[str] = None
    workflow_id: Optional[str] = None
    execution_id: Optional[str] = None


class ActivityResponse(BaseModel):
    activities: List[ActivityItem]
    total: int


class ExecutionTrendPoint(BaseModel):
    name: str
    date: str
    success: int
    failed: int


class ExecutionTrendsResponse(BaseModel):
    trends: List[ExecutionTrendPoint]
    total_success: int
    total_failed: int
    success_rate: float
