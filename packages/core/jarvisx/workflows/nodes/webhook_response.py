import logging
from jarvisx.workflows.nodes.base import BaseNodeExecutor

logger = logging.getLogger(__name__)


class WebhookResponseNodeExecutor(BaseNodeExecutor):
    async def execute(self, config: dict, input_data: dict, node_data: dict) -> dict:
        status_code = int(config.get("status_code", 200))
        body_template = config.get("body", "")
        headers = config.get("headers", {})

        if body_template:
            body = self.interpolate_variables(body_template, {"input": input_data})
        else:
            body = input_data

        return {
            "webhook_response": {
                "status_code": status_code,
                "body": body,
                "headers": headers,
            },
            "data": input_data,
        }
