import asyncio
import logging
from jarvisx.workflows.nodes.base import BaseNodeExecutor

logger = logging.getLogger(__name__)

MAX_DELAY_SECONDS = 3600


class DelayNodeExecutor(BaseNodeExecutor):
    async def execute(self, config: dict, input_data: dict, node_data: dict) -> dict:
        delay_seconds = min(int(config.get("delay_seconds", 0)), MAX_DELAY_SECONDS)
        delay_ms = min(int(config.get("delay_ms", 0)), MAX_DELAY_SECONDS * 1000)

        total_seconds = delay_seconds + (delay_ms / 1000.0)
        total_seconds = min(total_seconds, MAX_DELAY_SECONDS)

        if total_seconds > 0:
            logger.info(f"Delay node waiting {total_seconds}s")
            await asyncio.sleep(total_seconds)

        return {**input_data, "delay": {"waited_seconds": total_seconds}}
