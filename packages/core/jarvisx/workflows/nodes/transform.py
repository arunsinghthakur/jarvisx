import logging
from jarvisx.workflows.nodes.base import BaseNodeExecutor

logger = logging.getLogger(__name__)


class TransformNodeExecutor(BaseNodeExecutor):
    async def execute(
        self,
        config: dict,
        input_data: dict,
        node_data: dict
    ) -> dict:
        code = config.get("code", "")
        
        if not code:
            return input_data
        
        try:
            safe_globals = {"__builtins__": {}}
            safe_locals = {"input": input_data}
            
            exec_code = f"""
def _transform(input):
{chr(10).join('    ' + line for line in code.split(chr(10)))}
_result = _transform(input)
"""
            exec(exec_code, safe_globals, safe_locals)
            result = safe_locals.get("_result", input_data)
            
            if isinstance(result, dict):
                return result
            return {"result": result}
            
        except Exception as e:
            logger.error(f"Transform execution failed: {e}")
            return {
                "error": str(e),
                "original_input": input_data,
            }
