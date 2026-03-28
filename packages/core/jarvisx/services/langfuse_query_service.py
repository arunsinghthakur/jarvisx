from __future__ import annotations

import logging
import json
from typing import Optional, List, Any
from datetime import datetime, timedelta
from dataclasses import dataclass

import psycopg2
from psycopg2.extras import RealDictCursor

from jarvisx.tracing.langfuse_client import get_langfuse
from jarvisx.config.configs import (
    LANGFUSE_POSTGRES_HOST,
    LANGFUSE_POSTGRES_PORT,
    LANGFUSE_POSTGRES_USER,
    LANGFUSE_POSTGRES_PASSWORD,
    LANGFUSE_POSTGRES_DB,
)

logger = logging.getLogger(__name__)


@dataclass
class TraceSummary:
    id: str
    name: str
    timestamp: datetime
    duration_ms: Optional[float]
    status: str
    user_id: Optional[str]
    session_id: Optional[str]
    metadata: dict
    input: Optional[Any]
    output: Optional[Any]


@dataclass
class ObservationSummary:
    id: str
    name: str
    type: str
    start_time: datetime
    end_time: Optional[datetime]
    duration_ms: Optional[float]
    level: Optional[str]
    status_message: Optional[str]
    model: Optional[str]
    input: Optional[Any]
    output: Optional[Any]
    metadata: dict
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    cost: Optional[float] = None
    model_parameters: Optional[dict] = None


@dataclass
class TraceDetail:
    id: str
    name: str
    timestamp: datetime
    duration_ms: Optional[float]
    status: str
    user_id: Optional[str]
    session_id: Optional[str]
    metadata: dict
    input: Optional[Any]
    output: Optional[Any]
    observations: List[ObservationSummary]


@dataclass
class TracingStats:
    total_traces: int
    error_count: int
    success_count: int
    avg_latency_ms: float
    traces_today: int
    traces_this_week: int


class LangfuseQueryService:
    def __init__(self):
        self._langfuse = None
        self._pg_conn = None
    
    @property
    def langfuse(self):
        if self._langfuse is None:
            self._langfuse = get_langfuse()
        return self._langfuse
    
    def _get_pg_connection(self):
        try:
            return psycopg2.connect(
                host=LANGFUSE_POSTGRES_HOST,
                port=LANGFUSE_POSTGRES_PORT,
                user=LANGFUSE_POSTGRES_USER,
                password=LANGFUSE_POSTGRES_PASSWORD,
                dbname=LANGFUSE_POSTGRES_DB,
            )
        except Exception as e:
            logger.error(f"Failed to connect to Langfuse PostgreSQL: {e}")
            return None
    
    def _query_traces_from_postgres(
        self,
        organization_id: str,
        limit: int = 50,
        offset: int = 0,
        name_filter: Optional[str] = None,
        status_filter: Optional[str] = None,
    ) -> tuple[List[TraceSummary], int]:
        conn = self._get_pg_connection()
        if not conn:
            return [], 0
        
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                where_clauses = []
                params = []
                
                where_clauses.append("(metadata->>'organization_id' = %s OR metadata->>'tenant_id' = %s)")
                params.extend([organization_id, organization_id])
                
                if name_filter:
                    where_clauses.append("LOWER(name) LIKE LOWER(%s)")
                    params.append(f"%{name_filter}%")
                
                where_sql = " AND ".join(where_clauses)
                
                count_sql = f"SELECT COUNT(*) FROM traces WHERE {where_sql}"
                cur.execute(count_sql, params)
                total_count = cur.fetchone()['count']
                
                query_sql = f"""
                    SELECT id, name, timestamp, metadata, input, output, 
                           session_id, user_id, level
                    FROM traces 
                    WHERE {where_sql}
                    ORDER BY timestamp DESC
                    LIMIT %s OFFSET %s
                """
                params.extend([limit, offset])
                cur.execute(query_sql, params)
                rows = cur.fetchall()
                
                summaries = []
                for row in rows:
                    metadata = row.get('metadata') or {}
                    if isinstance(metadata, str):
                        metadata = json.loads(metadata)
                    
                    output = row.get('output')
                    if isinstance(output, str):
                        try:
                            output = json.loads(output)
                        except:
                            pass
                    
                    status = 'success'
                    if output and isinstance(output, dict):
                        if output.get('error'):
                            status = 'error'
                        status_code = output.get('status_code')
                        if status_code and status_code >= 400:
                            status = 'error'
                    level = row.get('level')
                    if level and level.upper() == 'ERROR':
                        status = 'error'
                    
                    if status_filter and status != status_filter:
                        continue
                    
                    summary = TraceSummary(
                        id=row['id'],
                        name=row.get('name') or 'Unknown',
                        timestamp=row.get('timestamp') or datetime.utcnow(),
                        duration_ms=metadata.get('duration_ms'),
                        status=status,
                        user_id=row.get('user_id') or metadata.get('user_id'),
                        session_id=row.get('session_id'),
                        metadata=metadata,
                        input=row.get('input'),
                        output=output,
                    )
                    summaries.append(summary)
                
                if status_filter:
                    return summaries, len(summaries)
                
                return summaries, total_count
                
        except Exception as e:
            logger.error(f"Failed to query traces from PostgreSQL: {e}")
            return [], 0
        finally:
            conn.close()
    
    def _get_trace_from_postgres(
        self,
        trace_id: str,
        organization_id: str,
    ) -> Optional[TraceDetail]:
        conn = self._get_pg_connection()
        if not conn:
            return None
        
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT id, name, timestamp, metadata, input, output,
                           session_id, user_id, level
                    FROM traces 
                    WHERE id = %s
                """, (trace_id,))
                row = cur.fetchone()
                
                if not row:
                    return None
                
                metadata = row.get('metadata') or {}
                if isinstance(metadata, str):
                    metadata = json.loads(metadata)
                
                trace_org_id = metadata.get('organization_id') or metadata.get('tenant_id')
                if trace_org_id and trace_org_id != organization_id:
                    logger.warning(f"Trace {trace_id} does not belong to organization {organization_id}")
                    return None
                
                output = row.get('output')
                if isinstance(output, str):
                    try:
                        output = json.loads(output)
                    except:
                        pass
                
                status = 'success'
                if output and isinstance(output, dict):
                    if output.get('error'):
                        status = 'error'
                    status_code = output.get('status_code')
                    if status_code and status_code >= 400:
                        status = 'error'
                
                cur.execute("""
                    SELECT id, name, type, start_time, end_time, level, 
                           status_message, model, input, output, metadata,
                           prompt_tokens, completion_tokens, total_tokens,
                           calculated_total_cost as cost, model_parameters
                    FROM observations 
                    WHERE trace_id = %s
                    ORDER BY start_time ASC
                """, (trace_id,))
                obs_rows = cur.fetchall()
                
                observations = []
                for obs in obs_rows:
                    obs_metadata = obs.get('metadata') or {}
                    if isinstance(obs_metadata, str):
                        obs_metadata = json.loads(obs_metadata)
                    
                    obs_input = obs.get('input')
                    if isinstance(obs_input, str):
                        try:
                            obs_input = json.loads(obs_input)
                        except:
                            pass
                    
                    obs_output = obs.get('output')
                    if isinstance(obs_output, str):
                        try:
                            obs_output = json.loads(obs_output)
                        except:
                            pass
                    
                    start_time = obs.get('start_time')
                    end_time = obs.get('end_time')
                    duration_ms = None
                    if start_time and end_time:
                        duration_ms = (end_time - start_time).total_seconds() * 1000
                    
                    obs_model_params = obs.get('model_parameters')
                    if isinstance(obs_model_params, str):
                        try:
                            obs_model_params = json.loads(obs_model_params)
                        except:
                            pass
                    
                    observations.append(ObservationSummary(
                        id=obs['id'],
                        name=obs.get('name') or 'Unknown',
                        type=obs.get('type') or 'SPAN',
                        start_time=start_time or datetime.utcnow(),
                        end_time=end_time,
                        duration_ms=duration_ms,
                        level=obs.get('level'),
                        status_message=obs.get('status_message'),
                        model=obs.get('model'),
                        input=obs_input,
                        output=obs_output,
                        metadata=obs_metadata,
                        prompt_tokens=obs.get('prompt_tokens'),
                        completion_tokens=obs.get('completion_tokens'),
                        total_tokens=obs.get('total_tokens'),
                        cost=obs.get('cost'),
                        model_parameters=obs_model_params,
                    ))
                
                return TraceDetail(
                    id=row['id'],
                    name=row.get('name') or 'Unknown',
                    timestamp=row.get('timestamp') or datetime.utcnow(),
                    duration_ms=metadata.get('duration_ms'),
                    status=status,
                    user_id=row.get('user_id') or metadata.get('user_id'),
                    session_id=row.get('session_id'),
                    metadata=metadata,
                    input=row.get('input'),
                    output=output,
                    observations=observations,
                )
                
        except Exception as e:
            logger.error(f"Failed to get trace from PostgreSQL: {e}")
            return None
        finally:
            conn.close()
    
    def _filter_by_organization(
        self,
        traces: List[Any],
        organization_id: str,
        include_unassigned: bool = True,
    ) -> List[Any]:
        filtered = []
        for trace in traces:
            metadata = getattr(trace, 'metadata', {}) or {}
            trace_org_id = metadata.get('organization_id') or metadata.get('tenant_id')
            
            if trace_org_id == organization_id:
                filtered.append(trace)
            elif include_unassigned and not trace_org_id:
                filtered.append(trace)
        return filtered
    
    def _determine_status(self, trace: Any) -> str:
        output = getattr(trace, 'output', None)
        if output and isinstance(output, dict):
            if output.get('error'):
                return 'error'
            status_code = output.get('status_code')
            if status_code and status_code >= 400:
                return 'error'
        
        level = getattr(trace, 'level', None)
        if level and level.upper() == 'ERROR':
            return 'error'
        
        return 'success'
    
    def _calculate_duration(self, trace: Any) -> Optional[float]:
        output = getattr(trace, 'output', None)
        if output and isinstance(output, dict):
            duration = output.get('duration_ms')
            if duration is not None:
                return float(duration)
        
        start_time = getattr(trace, 'start_time', None) or getattr(trace, 'timestamp', None)
        end_time = getattr(trace, 'end_time', None)
        
        if start_time and end_time:
            if isinstance(start_time, datetime) and isinstance(end_time, datetime):
                return (end_time - start_time).total_seconds() * 1000
        
        return None
    
    def _matches_name_filter(self, trace: Any, name_filter: str) -> bool:
        trace_name = getattr(trace, 'name', '') or ''
        return name_filter.lower() in trace_name.lower()
    
    def list_traces(
        self,
        organization_id: str,
        limit: int = 50,
        offset: int = 0,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        name_filter: Optional[str] = None,
        tags: Optional[List[str]] = None,
        status_filter: Optional[str] = None,
    ) -> tuple[List[TraceSummary], int]:
        logger.info(f"list_traces called: org={organization_id}, name_filter={name_filter}, status_filter={status_filter}")
        
        if not self.langfuse:
            logger.warning("Langfuse client not available, falling back to PostgreSQL")
            return self._query_traces_from_postgres(
                organization_id=organization_id,
                limit=limit,
                offset=offset,
                name_filter=name_filter,
                status_filter=status_filter,
            )
        
        try:
            api_params = {}
            
            if tags:
                api_params['tags'] = tags
            
            if start_time:
                api_params['from_timestamp'] = start_time
            
            if end_time:
                api_params['to_timestamp'] = end_time
            
            all_org_traces = []
            page_cursor = None
            max_pages = 10
            pages_fetched = 0
            
            while pages_fetched < max_pages:
                page_params = {**api_params, 'limit': 100}
                if page_cursor:
                    page_params['page'] = page_cursor
                
                traces_response = self.langfuse.api.trace.list(**page_params)
                
                page_traces = []
                if hasattr(traces_response, 'data'):
                    page_traces = traces_response.data
                elif isinstance(traces_response, list):
                    page_traces = traces_response
                
                if not page_traces:
                    break
                
                org_traces = self._filter_by_organization(page_traces, organization_id)
                all_org_traces.extend(org_traces)
                
                if len(all_org_traces) >= offset + limit + 50:
                    break
                
                if hasattr(traces_response, 'meta') and hasattr(traces_response.meta, 'page'):
                    page_cursor = traces_response.meta.page + 1
                else:
                    break
                
                pages_fetched += 1
            
            logger.info(f"Fetched {len(all_org_traces)} org traces from API before filters")
            
            if len(all_org_traces) == 0:
                logger.info("No traces from API, falling back to PostgreSQL")
                return self._query_traces_from_postgres(
                    organization_id=organization_id,
                    limit=limit,
                    offset=offset,
                    name_filter=name_filter,
                    status_filter=status_filter,
                )
            
            if name_filter:
                before_count = len(all_org_traces)
                all_org_traces = [
                    t for t in all_org_traces
                    if self._matches_name_filter(t, name_filter)
                ]
                logger.info(f"Name filter '{name_filter}': {before_count} -> {len(all_org_traces)} traces")
            
            if status_filter:
                before_count = len(all_org_traces)
                all_org_traces = [
                    t for t in all_org_traces
                    if self._determine_status(t) == status_filter
                ]
                logger.info(f"Status filter '{status_filter}': {before_count} -> {len(all_org_traces)} traces")
            
            total_count = len(all_org_traces)
            paginated_traces = all_org_traces[offset:offset + limit]
            logger.info(f"Returning {len(paginated_traces)} traces (total: {total_count})")
            
            summaries = []
            for trace in paginated_traces:
                try:
                    summary = TraceSummary(
                        id=getattr(trace, 'id', ''),
                        name=getattr(trace, 'name', 'Unknown'),
                        timestamp=getattr(trace, 'timestamp', datetime.utcnow()),
                        duration_ms=self._calculate_duration(trace),
                        status=self._determine_status(trace),
                        user_id=getattr(trace, 'user_id', None) or (getattr(trace, 'metadata', {}) or {}).get('user_id'),
                        session_id=getattr(trace, 'session_id', None),
                        metadata=getattr(trace, 'metadata', {}) or {},
                        input=getattr(trace, 'input', None),
                        output=getattr(trace, 'output', None),
                    )
                    summaries.append(summary)
                except Exception as e:
                    logger.warning(f"Failed to parse trace: {e}")
                    continue
            
            return summaries, total_count
            
        except Exception as e:
            logger.error(f"Failed to list traces from Langfuse API: {e}, falling back to PostgreSQL")
            return self._query_traces_from_postgres(
                organization_id=organization_id,
                limit=limit,
                offset=offset,
                name_filter=name_filter,
                status_filter=status_filter,
            )
    
    def get_trace(
        self,
        trace_id: str,
        organization_id: str,
        include_unassigned: bool = True,
    ) -> Optional[TraceDetail]:
        if not self.langfuse:
            logger.warning("Langfuse client not available, falling back to PostgreSQL")
            return self._get_trace_from_postgres(trace_id, organization_id)
        
        try:
            trace = self.langfuse.api.trace.get(trace_id)
            
            if not trace:
                logger.info(f"Trace {trace_id} not found via API, falling back to PostgreSQL")
                return self._get_trace_from_postgres(trace_id, organization_id)
            
            metadata = getattr(trace, 'metadata', {}) or {}
            trace_org_id = metadata.get('organization_id') or metadata.get('tenant_id')
            
            if trace_org_id and trace_org_id != organization_id:
                logger.warning(f"Trace {trace_id} does not belong to organization {organization_id}")
                return None
            
            if not trace_org_id and not include_unassigned:
                logger.warning(f"Trace {trace_id} has no organization and unassigned traces are not allowed")
                return None
            
            observations = self._get_observations_for_trace(trace_id, organization_id)
            
            return TraceDetail(
                id=getattr(trace, 'id', ''),
                name=getattr(trace, 'name', 'Unknown'),
                timestamp=getattr(trace, 'timestamp', datetime.utcnow()),
                duration_ms=self._calculate_duration(trace),
                status=self._determine_status(trace),
                user_id=getattr(trace, 'user_id', None) or metadata.get('user_id'),
                session_id=getattr(trace, 'session_id', None),
                metadata=metadata,
                input=getattr(trace, 'input', None),
                output=getattr(trace, 'output', None),
                observations=observations,
            )
            
        except Exception as e:
            logger.error(f"Failed to get trace {trace_id} from Langfuse API: {e}, falling back to PostgreSQL")
            return self._get_trace_from_postgres(trace_id, organization_id)
    
    def _get_observations_for_trace(
        self,
        trace_id: str,
        organization_id: str,
    ) -> List[ObservationSummary]:
        if not self.langfuse:
            return []
        
        try:
            observations_response = self.langfuse.api.observations.get_many(
                trace_id=trace_id,
                limit=100
            )
            
            observations = []
            if hasattr(observations_response, 'data'):
                observations = observations_response.data
            elif isinstance(observations_response, list):
                observations = observations_response
            
            summaries = []
            for obs in observations:
                try:
                    start_time = getattr(obs, 'start_time', None) or getattr(obs, 'timestamp', datetime.utcnow())
                    end_time = getattr(obs, 'end_time', None)
                    
                    duration_ms = None
                    if start_time and end_time:
                        if isinstance(start_time, datetime) and isinstance(end_time, datetime):
                            duration_ms = (end_time - start_time).total_seconds() * 1000
                    
                    usage = getattr(obs, 'usage', None) or {}
                    if isinstance(usage, dict):
                        prompt_tokens = usage.get('promptTokens') or usage.get('prompt_tokens')
                        completion_tokens = usage.get('completionTokens') or usage.get('completion_tokens')
                        total_tokens = usage.get('totalTokens') or usage.get('total_tokens')
                    else:
                        prompt_tokens = getattr(usage, 'promptTokens', None) or getattr(usage, 'prompt_tokens', None)
                        completion_tokens = getattr(usage, 'completionTokens', None) or getattr(usage, 'completion_tokens', None)
                        total_tokens = getattr(usage, 'totalTokens', None) or getattr(usage, 'total_tokens', None)
                    
                    cost = getattr(obs, 'calculatedTotalCost', None) or getattr(obs, 'total_cost', None)
                    model_params = getattr(obs, 'modelParameters', None) or getattr(obs, 'model_parameters', None)
                    
                    summary = ObservationSummary(
                        id=getattr(obs, 'id', ''),
                        name=getattr(obs, 'name', 'Unknown'),
                        type=getattr(obs, 'type', 'SPAN'),
                        start_time=start_time,
                        end_time=end_time,
                        duration_ms=duration_ms,
                        level=getattr(obs, 'level', None),
                        status_message=getattr(obs, 'status_message', None),
                        model=getattr(obs, 'model', None),
                        input=getattr(obs, 'input', None),
                        output=getattr(obs, 'output', None),
                        metadata=getattr(obs, 'metadata', {}) or {},
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        total_tokens=total_tokens,
                        cost=cost,
                        model_parameters=model_params,
                    )
                    summaries.append(summary)
                except Exception as e:
                    logger.warning(f"Failed to parse observation: {e}")
                    continue
            
            summaries.sort(key=lambda x: x.start_time)
            return summaries
            
        except Exception as e:
            logger.error(f"Failed to get observations for trace {trace_id}: {e}")
            return []
    
    def _get_stats_from_postgres(self, organization_id: str, days: int = 7) -> TracingStats:
        conn = self._get_pg_connection()
        if not conn:
            return TracingStats(
                total_traces=0, error_count=0, success_count=0,
                avg_latency_ms=0.0, traces_today=0, traces_this_week=0,
            )
        
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT COUNT(*) as total FROM traces 
                    WHERE metadata->>'organization_id' = %s OR metadata->>'tenant_id' = %s
                """, (organization_id, organization_id))
                total_traces = cur.fetchone()['total']
                
                cur.execute("""
                    SELECT COUNT(*) as cnt FROM traces 
                    WHERE (metadata->>'organization_id' = %s OR metadata->>'tenant_id' = %s)
                    AND timestamp >= CURRENT_DATE
                """, (organization_id, organization_id))
                traces_today = cur.fetchone()['cnt']
                
                cur.execute("""
                    SELECT COUNT(*) as cnt FROM traces 
                    WHERE (metadata->>'organization_id' = %s OR metadata->>'tenant_id' = %s)
                    AND timestamp >= NOW() - INTERVAL '%s days'
                """, (organization_id, organization_id, days))
                traces_this_week = cur.fetchone()['cnt']
                
                return TracingStats(
                    total_traces=total_traces,
                    error_count=0,
                    success_count=total_traces,
                    avg_latency_ms=0.0,
                    traces_today=traces_today,
                    traces_this_week=traces_this_week,
                )
        except Exception as e:
            logger.error(f"Failed to get stats from PostgreSQL: {e}")
            return TracingStats(
                total_traces=0, error_count=0, success_count=0,
                avg_latency_ms=0.0, traces_today=0, traces_this_week=0,
            )
        finally:
            conn.close()
    
    def _make_naive(self, dt: datetime) -> datetime:
        if dt is None:
            return None
        if dt.tzinfo is not None:
            return dt.replace(tzinfo=None)
        return dt
    
    def get_stats(
        self,
        organization_id: str,
        days: int = 7,
    ) -> TracingStats:
        if not self.langfuse:
            return self._get_stats_from_postgres(organization_id, days)
        
        try:
            now = datetime.utcnow()
            week_ago = now - timedelta(days=days)
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            
            traces_response = self.langfuse.api.trace.list(limit=100)
            
            all_traces = []
            if hasattr(traces_response, 'data'):
                all_traces = traces_response.data
            elif isinstance(traces_response, list):
                all_traces = traces_response
            
            if not all_traces:
                logger.info("No traces from API for stats, falling back to PostgreSQL")
                return self._get_stats_from_postgres(organization_id, days)
            
            filtered_traces = self._filter_by_organization(all_traces, organization_id)
            
            total_traces = len(filtered_traces)
            error_count = 0
            success_count = 0
            traces_today = 0
            traces_this_week = 0
            total_latency = 0.0
            latency_count = 0
            
            for trace in filtered_traces:
                status = self._determine_status(trace)
                if status == 'error':
                    error_count += 1
                else:
                    success_count += 1
                
                timestamp = getattr(trace, 'timestamp', None)
                if timestamp:
                    timestamp_naive = self._make_naive(timestamp)
                    if timestamp_naive >= today_start:
                        traces_today += 1
                    if timestamp_naive >= week_ago:
                        traces_this_week += 1
                
                duration = self._calculate_duration(trace)
                if duration is not None:
                    total_latency += duration
                    latency_count += 1
            
            avg_latency = total_latency / latency_count if latency_count > 0 else 0.0
            
            return TracingStats(
                total_traces=total_traces,
                error_count=error_count,
                success_count=success_count,
                avg_latency_ms=round(avg_latency, 2),
                traces_today=traces_today,
                traces_this_week=traces_this_week,
            )
            
        except Exception as e:
            logger.error(f"Failed to get tracing stats from API: {e}, falling back to PostgreSQL")
            return self._get_stats_from_postgres(organization_id, days)


langfuse_query_service = LangfuseQueryService()
