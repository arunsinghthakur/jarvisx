import logging
from jarvisx.workflows.nodes.base import BaseNodeExecutor

logger = logging.getLogger(__name__)


class CloudStorageNodeExecutor(BaseNodeExecutor):
    async def execute(self, config: dict, input_data: dict, node_data: dict) -> dict:
        operation = config.get("operation", "download")
        provider = config.get("provider", "s3")
        bucket = config.get("bucket", "")
        key = config.get("key", "")

        if key:
            key = self.interpolate_variables(key, {"input": input_data})

        if not bucket or not key:
            return {"error": "bucket and key are required", "data": input_data}

        try:
            if provider == "s3":
                return await self._s3_operation(operation, config, bucket, key, input_data)
            return {"error": f"Unsupported provider: {provider}", "data": input_data}
        except Exception as e:
            logger.error(f"Cloud storage operation failed: {e}")
            return {"error": str(e), "data": input_data}

    async def _s3_operation(self, operation, config, bucket, key, input_data):
        import boto3

        s3 = boto3.client(
            "s3",
            aws_access_key_id=config.get("access_key"),
            aws_secret_access_key=config.get("secret_key"),
            region_name=config.get("region", "us-east-1"),
        )

        if operation == "download":
            obj = s3.get_object(Bucket=bucket, Key=key)
            content = obj["Body"].read().decode("utf-8", errors="replace")
            return {"content": content, "key": key, "bucket": bucket, "data": input_data}

        elif operation == "upload":
            body = input_data.get("content", "")
            if isinstance(body, dict):
                import json
                body = json.dumps(body)
            s3.put_object(Bucket=bucket, Key=key, Body=body.encode("utf-8"))
            return {"uploaded": True, "key": key, "bucket": bucket, "data": input_data}

        elif operation == "list":
            prefix = config.get("prefix", "")
            response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix, MaxKeys=100)
            files = [obj["Key"] for obj in response.get("Contents", [])]
            return {"files": files, "count": len(files), "bucket": bucket, "data": input_data}

        return {"error": f"Unknown operation: {operation}", "data": input_data}
