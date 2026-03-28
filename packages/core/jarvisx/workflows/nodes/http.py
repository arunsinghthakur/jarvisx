import json
import logging
import httpx
from jarvisx.workflows.nodes.base import BaseNodeExecutor

logger = logging.getLogger(__name__)


class HTTPNodeExecutor(BaseNodeExecutor):
    async def execute(
        self,
        config: dict,
        input_data: dict,
        node_data: dict
    ) -> dict:
        method = config.get("method", "GET").upper()
        url_template = config.get("url", "")
        headers_str = config.get("headers", "{}")
        body_template = config.get("body", "")
        
        context = {"input": input_data}
        url = self.interpolate_variables(url_template, context)
        
        if not url:
            raise ValueError("URL is required for HTTP node")
        
        try:
            headers = json.loads(headers_str) if headers_str else {}
        except json.JSONDecodeError:
            headers = {}
        
        body = None
        if body_template and method in ["POST", "PUT", "PATCH"]:
            body_str = self.interpolate_variables(body_template, context)
            try:
                body = json.loads(body_str)
            except json.JSONDecodeError:
                body = body_str
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=body if isinstance(body, dict) else None,
                    content=body if isinstance(body, str) else None,
                )
                
                response_data = {
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                }
                
                try:
                    response_data["body"] = response.json()
                except Exception:
                    response_data["body"] = response.text
                
                response_data["success"] = 200 <= response.status_code < 300
                
                return response_data
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP request failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "status_code": None,
            }
        except Exception as e:
            logger.error(f"HTTP node error: {e}")
            raise
