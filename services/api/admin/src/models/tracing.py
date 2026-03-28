from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel


class TraceSummaryResponse(BaseModel):
    id: str
    name: str
    timestamp: datetime
    duration_ms: Optional[float] = None
    status: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    metadata: dict = {}
    input: Optional[Any] = None
    output: Optional[Any] = None


class ObservationResponse(BaseModel):
    id: str
    name: str
    type: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    level: Optional[str] = None
    status_message: Optional[str] = None
    model: Optional[str] = None
    input: Optional[Any] = None
    output: Optional[Any] = None
    metadata: dict = {}
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    cost: Optional[float] = None
    model_parameters: Optional[dict] = None


class TraceDetailResponse(BaseModel):
    id: str
    name: str
    timestamp: datetime
    duration_ms: Optional[float] = None
    status: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    metadata: dict = {}
    input: Optional[Any] = None
    output: Optional[Any] = None
    observations: List[ObservationResponse] = []


class TracesListResponse(BaseModel):
    traces: List[TraceSummaryResponse]
    total: int
    limit: int
    offset: int


class TracingStatsResponse(BaseModel):
    total_traces: int
    error_count: int
    success_count: int
    avg_latency_ms: float
    traces_today: int
    traces_this_week: int
    error_rate: float = 0.0

    class Config:
        from_attributes = True


class ObservationsListResponse(BaseModel):
    observations: List[ObservationResponse]
    trace_id: str
