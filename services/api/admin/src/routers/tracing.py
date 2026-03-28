from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query

from jarvisx.services.langfuse_query_service import langfuse_query_service
from services.api.admin.src.dependencies import get_current_user, CurrentUser
from services.api.admin.src.models.tracing import (
    TraceSummaryResponse,
    ObservationResponse,
    TraceDetailResponse,
    TracesListResponse,
    TracingStatsResponse,
    ObservationsListResponse,
)

router = APIRouter(prefix="/api/tracing", tags=["tracing"])


@router.get("/traces", response_model=TracesListResponse)
async def list_traces(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    start_time: Optional[datetime] = Query(None, description="Filter traces from this time"),
    end_time: Optional[datetime] = Query(None, description="Filter traces until this time"),
    name_filter: Optional[str] = Query(None, description="Filter by trace name"),
    tags: Optional[List[str]] = Query(None, description="Filter by tags"),
    status: Optional[str] = Query(None, description="Filter by status (success/error)"),
    current_user: CurrentUser = Depends(get_current_user),
):
    organization_id = current_user.organization_id
    
    traces, total = langfuse_query_service.list_traces(
        organization_id=organization_id,
        limit=limit,
        offset=offset,
        start_time=start_time,
        end_time=end_time,
        name_filter=name_filter,
        tags=tags,
        status_filter=status,
    )
    
    trace_responses = [
        TraceSummaryResponse(
            id=t.id,
            name=t.name,
            timestamp=t.timestamp,
            duration_ms=t.duration_ms,
            status=t.status,
            user_id=t.user_id,
            session_id=t.session_id,
            metadata=t.metadata,
            input=t.input,
            output=t.output,
        )
        for t in traces
    ]
    
    return TracesListResponse(
        traces=trace_responses,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/traces/{trace_id}", response_model=TraceDetailResponse)
async def get_trace(
    trace_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    organization_id = current_user.organization_id
    
    trace = langfuse_query_service.get_trace(
        trace_id=trace_id,
        organization_id=organization_id,
    )
    
    if not trace:
        raise HTTPException(
            status_code=404,
            detail="Trace not found or does not belong to your organization"
        )
    
    observations = [
        ObservationResponse(
            id=obs.id,
            name=obs.name,
            type=obs.type,
            start_time=obs.start_time,
            end_time=obs.end_time,
            duration_ms=obs.duration_ms,
            level=obs.level,
            status_message=obs.status_message,
            model=obs.model,
            input=obs.input,
            output=obs.output,
            metadata=obs.metadata,
            prompt_tokens=obs.prompt_tokens,
            completion_tokens=obs.completion_tokens,
            total_tokens=obs.total_tokens,
            cost=obs.cost,
            model_parameters=obs.model_parameters,
        )
        for obs in trace.observations
    ]
    
    return TraceDetailResponse(
        id=trace.id,
        name=trace.name,
        timestamp=trace.timestamp,
        duration_ms=trace.duration_ms,
        status=trace.status,
        user_id=trace.user_id,
        session_id=trace.session_id,
        metadata=trace.metadata,
        input=trace.input,
        output=trace.output,
        observations=observations,
    )


@router.get("/traces/{trace_id}/observations", response_model=ObservationsListResponse)
async def get_trace_observations(
    trace_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    organization_id = current_user.organization_id
    
    trace = langfuse_query_service.get_trace(
        trace_id=trace_id,
        organization_id=organization_id,
    )
    
    if not trace:
        raise HTTPException(
            status_code=404,
            detail="Trace not found or does not belong to your organization"
        )
    
    observations = [
        ObservationResponse(
            id=obs.id,
            name=obs.name,
            type=obs.type,
            start_time=obs.start_time,
            end_time=obs.end_time,
            duration_ms=obs.duration_ms,
            level=obs.level,
            status_message=obs.status_message,
            model=obs.model,
            input=obs.input,
            output=obs.output,
            metadata=obs.metadata,
            prompt_tokens=obs.prompt_tokens,
            completion_tokens=obs.completion_tokens,
            total_tokens=obs.total_tokens,
            cost=obs.cost,
            model_parameters=obs.model_parameters,
        )
        for obs in trace.observations
    ]
    
    return ObservationsListResponse(
        observations=observations,
        trace_id=trace_id,
    )


@router.get("/stats", response_model=TracingStatsResponse)
async def get_tracing_stats(
    days: int = Query(7, ge=1, le=90, description="Number of days to include in stats"),
    current_user: CurrentUser = Depends(get_current_user),
):
    organization_id = current_user.organization_id
    
    stats = langfuse_query_service.get_stats(
        organization_id=organization_id,
        days=days,
    )
    
    error_rate = 0.0
    if stats.total_traces > 0:
        error_rate = round((stats.error_count / stats.total_traces) * 100, 2)
    
    return TracingStatsResponse(
        total_traces=stats.total_traces,
        error_count=stats.error_count,
        success_count=stats.success_count,
        avg_latency_ms=stats.avg_latency_ms,
        traces_today=stats.traces_today,
        traces_this_week=stats.traces_this_week,
        error_rate=error_rate,
    )
