import logging
from jarvisx.workflows.nodes.base import BaseNodeExecutor

logger = logging.getLogger(__name__)


class ErrorHandlerNodeExecutor(BaseNodeExecutor):
    async def execute(self, config: dict, input_data: dict, node_data: dict) -> dict:
        return {"data": input_data}
