import logging
from jarvisx.workflows.nodes.base import BaseNodeExecutor

logger = logging.getLogger(__name__)


class DatabaseNodeExecutor(BaseNodeExecutor):
    async def execute(self, config: dict, input_data: dict, node_data: dict) -> dict:
        operation = config.get("operation", "query")
        connection_string = config.get("connection_string", "")
        query = config.get("query", "")

        if not connection_string or not query:
            return {"error": "connection_string and query are required", "data": input_data}

        if query:
            query = self.interpolate_variables(query, {"input": input_data})

        try:
            from sqlalchemy import create_engine, text

            engine = create_engine(connection_string, pool_pre_ping=True)
            with engine.connect() as conn:
                if operation in ("query", "select"):
                    result = conn.execute(text(query))
                    rows = [dict(row._mapping) for row in result]
                    return {"rows": rows, "count": len(rows), "data": input_data}
                else:
                    result = conn.execute(text(query))
                    conn.commit()
                    return {"affected_rows": result.rowcount, "data": input_data}
        except Exception as e:
            logger.error(f"Database node execution failed: {e}")
            return {"error": str(e), "data": input_data}
