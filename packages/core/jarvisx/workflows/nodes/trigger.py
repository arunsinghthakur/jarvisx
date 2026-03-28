from jarvisx.workflows.nodes.base import BaseNodeExecutor


class TriggerNodeExecutor(BaseNodeExecutor):
    async def execute(
        self,
        config: dict,
        input_data: dict,
        node_data: dict
    ) -> dict:
        return input_data
