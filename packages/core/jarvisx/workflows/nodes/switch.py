import logging
from jarvisx.workflows.nodes.base import BaseNodeExecutor

logger = logging.getLogger(__name__)


class SwitchNodeExecutor(BaseNodeExecutor):
    async def execute(self, config: dict, input_data: dict, node_data: dict) -> dict:
        expression = config.get("expression", "")
        cases = config.get("cases", [])

        if not expression:
            return {"matched_case": "default", "matched": False, "data": input_data}

        try:
            safe_globals = {"__builtins__": {}}
            safe_locals = {"input": input_data}
            value = eval(expression, safe_globals, safe_locals)
        except Exception as e:
            logger.error(f"Switch expression evaluation failed: {e}")
            return {"matched_case": "default", "matched": False, "data": input_data, "error": str(e)}

        for case in cases:
            case_value = case.get("value")
            case_label = case.get("label", str(case_value))
            try:
                if str(value) == str(case_value):
                    return {"matched_case": case_label, "matched": True, "data": input_data, "value": str(value)}
            except Exception:
                continue

        return {"matched_case": "default", "matched": False, "data": input_data, "value": str(value)}
