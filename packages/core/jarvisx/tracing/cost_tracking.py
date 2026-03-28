import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

MODEL_PRICING = {
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    "claude-3-5-sonnet": {"input": 3.00, "output": 15.00},
    "claude-3-haiku": {"input": 0.25, "output": 1.25},
    "claude-3-opus": {"input": 15.00, "output": 75.00},
    "gemini-2.0-flash": {"input": 0.10, "output": 0.40},
    "gemini-2.5-flash": {"input": 0.15, "output": 0.60},
    "gemini-2.5-pro": {"input": 1.25, "output": 10.00},
}


def _estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    pricing = None
    model_lower = (model or "").lower()
    for key, p in MODEL_PRICING.items():
        if key in model_lower:
            pricing = p
            break

    if not pricing:
        pricing = {"input": 1.00, "output": 3.00}

    cost = (input_tokens / 1_000_000 * pricing["input"]) + (output_tokens / 1_000_000 * pricing["output"])
    return round(cost, 6)


def record_usage(
    model: str,
    input_tokens: int,
    output_tokens: int,
    organization_id: Optional[str] = None,
    workspace_id: Optional[str] = None,
    workflow_id: Optional[str] = None,
    execution_id: Optional[str] = None,
    agent_name: Optional[str] = None,
):
    try:
        from jarvisx.database.session import get_db_session
        from jarvisx.database.models import UsageMetric
        from jarvisx.common.id_utils import generate_id

        total = input_tokens + output_tokens
        cost = _estimate_cost(model, input_tokens, output_tokens)

        with get_db_session() as db:
            metric = UsageMetric(
                id=generate_id(),
                organization_id=organization_id or "unknown",
                workspace_id=workspace_id,
                workflow_id=workflow_id,
                execution_id=execution_id,
                agent_name=agent_name,
                model_name=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total,
                estimated_cost_usd=cost,
                recorded_at=datetime.utcnow(),
            )
            db.add(metric)
            db.commit()
    except Exception as e:
        logger.debug(f"Failed to record usage metric: {e}")


def setup_cost_tracking_callback():
    try:
        import litellm

        class CostTrackingCallback(litellm.integrations.custom_logger.CustomLogger):
            def log_success_event(self, kwargs, response_obj, start_time, end_time):
                try:
                    usage = getattr(response_obj, "usage", None)
                    if not usage:
                        return
                    model = kwargs.get("model", "unknown")
                    input_tokens = getattr(usage, "prompt_tokens", 0) or 0
                    output_tokens = getattr(usage, "completion_tokens", 0) or 0
                    metadata = kwargs.get("litellm_params", {}).get("metadata", {})

                    record_usage(
                        model=model,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        organization_id=metadata.get("organization_id"),
                        workspace_id=metadata.get("workspace_id"),
                        workflow_id=metadata.get("workflow_id"),
                        execution_id=metadata.get("execution_id"),
                        agent_name=metadata.get("agent_name"),
                    )
                except Exception as e:
                    logger.debug(f"Cost tracking callback error: {e}")

        callback = CostTrackingCallback()
        litellm.callbacks.append(callback)
        logger.info("Cost tracking callback registered")
        return True
    except Exception as e:
        logger.warning(f"Failed to setup cost tracking: {e}")
        return False
