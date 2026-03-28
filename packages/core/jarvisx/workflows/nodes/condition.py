import logging
from jarvisx.workflows.nodes.base import BaseNodeExecutor

logger = logging.getLogger(__name__)


class ConditionNodeExecutor(BaseNodeExecutor):
    async def execute(
        self,
        config: dict,
        input_data: dict,
        node_data: dict
    ) -> dict:
        condition_expr = config.get("condition", "")
        
        if not condition_expr:
            return {"result": True, "data": input_data}
        
        context = {"input": input_data}
        
        try:
            safe_globals = {"__builtins__": {}}
            safe_locals = {"input": input_data}
            
            result = eval(condition_expr, safe_globals, safe_locals)
            
            return {
                "result": bool(result),
                "data": input_data,
                "condition": condition_expr,
            }
        except Exception as e:
            logger.error(f"Condition evaluation failed: {e}")
            return {
                "result": False,
                "data": input_data,
                "error": str(e),
                "condition": condition_expr,
            }
