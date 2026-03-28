import logging
from jarvisx.workflows.nodes.base import BaseNodeExecutor

logger = logging.getLogger(__name__)


class SubWorkflowNodeExecutor(BaseNodeExecutor):
    async def execute(self, config: dict, input_data: dict, node_data: dict) -> dict:
        sub_workflow_id = config.get("workflow_id", "")
        if not sub_workflow_id:
            return {"error": "No sub-workflow ID configured", "data": input_data}

        try:
            from jarvisx.database.session import get_db_session
            from jarvisx.database.models import Workflow, WorkflowExecution, WorkflowExecutionStatus
            from jarvisx.common.id_utils import generate_id

            db = get_db_session()
            try:
                workflow = db.query(Workflow).filter(Workflow.id == sub_workflow_id).first()
                if not workflow:
                    return {"error": f"Sub-workflow {sub_workflow_id} not found", "data": input_data}

                from jarvisx.workflows.engine import WorkflowEngine

                execution = WorkflowExecution(
                    id=generate_id(),
                    workflow_id=sub_workflow_id,
                    status=WorkflowExecutionStatus.PENDING.value,
                    trigger_type="sub_workflow",
                    trigger_data=input_data,
                )
                db.add(execution)
                db.commit()

                engine = WorkflowEngine(db)
                result = await engine.execute(sub_workflow_id, execution.id, input_data)

                return {
                    "data": result,
                    "sub_workflow": {
                        "workflow_id": sub_workflow_id,
                        "execution_id": execution.id,
                        "status": "completed",
                    },
                }
            finally:
                db.close()
        except Exception as e:
            logger.exception(f"Sub-workflow execution failed: {e}")
            return {"error": str(e), "data": input_data}
