import logging
from jarvisx.workflows.nodes.base import BaseNodeExecutor

logger = logging.getLogger(__name__)


class ApprovalNodeExecutor(BaseNodeExecutor):
    async def execute(self, config: dict, input_data: dict, node_data: dict) -> dict:
        approvers = config.get("approvers", [])
        message = config.get("message", "Approval required")
        if config.get("prompt_template"):
            message = self.interpolate_variables(config["prompt_template"], {"input": input_data})

        return {
            "status": "approved",
            "data": input_data,
            "approval": {
                "message": message,
                "approvers": approvers,
                "auto_approved": True,
            },
        }
