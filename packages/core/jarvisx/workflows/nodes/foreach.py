import logging
from jarvisx.workflows.nodes.base import BaseNodeExecutor

logger = logging.getLogger(__name__)


class ForEachNodeExecutor(BaseNodeExecutor):
    async def execute(self, config: dict, input_data: dict, node_data: dict) -> dict:
        array_field = config.get("array_field", "items")
        items = input_data.get(array_field, [])

        if not isinstance(items, list):
            try:
                items = list(items)
            except (TypeError, ValueError):
                items = [items] if items else []

        foreach_state = input_data.get("foreach", {})
        current_index = foreach_state.get("index", -1) + 1

        if current_index < len(items):
            return {
                "items": items,
                "current_index": current_index,
                "data": {k: v for k, v in input_data.items() if k != "foreach"},
                "continue": True,
            }
        else:
            return {
                "items": items,
                "current_index": current_index,
                "data": {k: v for k, v in input_data.items() if k != "foreach"},
                "continue": False,
                "results": input_data.get("results", []),
            }
