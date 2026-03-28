import logging
from jarvisx.workflows.nodes.base import BaseNodeExecutor

logger = logging.getLogger(__name__)


class LoopNodeExecutor(BaseNodeExecutor):
    async def execute(self, config: dict, input_data: dict, node_data: dict) -> dict:
        max_iterations = int(config.get("max_iterations", 5))
        break_condition = config.get("break_condition", "")

        loop_info = input_data.get("loop", {})
        current_index = loop_info.get("index", 0) if loop_info else 0

        should_break = False
        if break_condition:
            try:
                safe_globals = {"__builtins__": {}}
                safe_locals = {"input": input_data, "loop": {"index": current_index, "iteration": current_index + 1}}
                should_break = bool(eval(break_condition, safe_globals, safe_locals))
            except Exception as e:
                logger.error(f"Loop break condition evaluation failed: {e}")
                should_break = False

        should_continue = not should_break and current_index < max_iterations - 1
        next_index = current_index + 1 if should_continue else current_index

        return {
            "continue": should_continue,
            "data": {
                **{k: v for k, v in input_data.items() if k != "loop"},
                "loop": {"index": next_index, "iteration": next_index + 1, "max": max_iterations},
            },
            "loop": {"index": current_index, "iteration": current_index + 1, "max": max_iterations},
        }
