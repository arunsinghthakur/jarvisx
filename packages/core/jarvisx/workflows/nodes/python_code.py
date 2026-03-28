import logging
from jarvisx.workflows.nodes.base import BaseNodeExecutor

logger = logging.getLogger(__name__)


class PythonCodeNodeExecutor(BaseNodeExecutor):
    async def execute(self, config: dict, input_data: dict, node_data: dict) -> dict:
        code = config.get("code", "")

        if not code:
            return {"error": "No code provided", "data": input_data}

        safe_builtins = {
            "abs": abs, "all": all, "any": any, "bool": bool, "dict": dict,
            "enumerate": enumerate, "filter": filter, "float": float, "int": int,
            "isinstance": isinstance, "len": len, "list": list, "map": map,
            "max": max, "min": min, "range": range, "reversed": reversed,
            "round": round, "set": set, "sorted": sorted, "str": str, "sum": sum,
            "tuple": tuple, "type": type, "zip": zip, "print": lambda *a, **k: None,
        }

        local_vars = {"input": input_data, "result": None}

        try:
            exec(code, {"__builtins__": safe_builtins}, local_vars)

            output = local_vars.get("result")
            if output is None:
                output = {k: v for k, v in local_vars.items() if k not in ("input", "result", "__builtins__")}

            if isinstance(output, dict):
                return {**output, "data": input_data}
            return {"result": output, "data": input_data}
        except Exception as e:
            logger.error(f"Python code execution failed: {e}")
            return {"error": str(e), "data": input_data}
