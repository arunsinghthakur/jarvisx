import logging
import json
import csv
import io
from jarvisx.workflows.nodes.base import BaseNodeExecutor

logger = logging.getLogger(__name__)


class DataTransformNodeExecutor(BaseNodeExecutor):
    async def execute(self, config: dict, input_data: dict, node_data: dict) -> dict:
        operation = config.get("operation", "parse_json")

        try:
            if operation == "parse_json":
                raw = input_data.get("content", input_data.get("body", ""))
                if isinstance(raw, str):
                    parsed = json.loads(raw)
                else:
                    parsed = raw
                return {"parsed": parsed, "data": input_data}

            elif operation == "parse_csv":
                raw = input_data.get("content", "")
                delimiter = config.get("delimiter", ",")
                reader = csv.DictReader(io.StringIO(raw), delimiter=delimiter)
                rows = list(reader)
                return {"rows": rows, "count": len(rows), "headers": reader.fieldnames or [], "data": input_data}

            elif operation == "to_csv":
                rows = input_data.get("rows", [])
                if not rows:
                    return {"csv": "", "data": input_data}
                output = io.StringIO()
                writer = csv.DictWriter(output, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
                return {"csv": output.getvalue(), "data": input_data}

            elif operation == "to_json":
                data = input_data.get("rows", input_data.get("parsed", input_data))
                return {"json": json.dumps(data, indent=2), "data": input_data}

            elif operation == "filter":
                field = config.get("field", "")
                value = config.get("value", "")
                rows = input_data.get("rows", [])
                filtered = [r for r in rows if str(r.get(field, "")) == str(value)]
                return {"rows": filtered, "count": len(filtered), "data": input_data}

            elif operation == "aggregate":
                field = config.get("field", "")
                agg_type = config.get("agg_type", "count")
                rows = input_data.get("rows", [])
                values = [float(r.get(field, 0)) for r in rows if r.get(field) is not None]

                result = 0
                if agg_type == "count":
                    result = len(values)
                elif agg_type == "sum":
                    result = sum(values)
                elif agg_type == "avg" and values:
                    result = sum(values) / len(values)
                elif agg_type == "min" and values:
                    result = min(values)
                elif agg_type == "max" and values:
                    result = max(values)

                return {"result": result, "agg_type": agg_type, "field": field, "data": input_data}

            elif operation == "pick_fields":
                fields = config.get("fields", [])
                rows = input_data.get("rows", [])
                if rows:
                    picked = [{f: r.get(f) for f in fields} for r in rows]
                    return {"rows": picked, "count": len(picked), "data": input_data}
                data = {f: input_data.get(f) for f in fields}
                return {"picked": data, "data": input_data}

            return {"error": f"Unknown operation: {operation}", "data": input_data}
        except Exception as e:
            logger.error(f"Data transform failed: {e}")
            return {"error": str(e), "data": input_data}
