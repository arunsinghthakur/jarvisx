import asyncio
import logging
from datetime import datetime
from typing import Optional, Any
from sqlalchemy.orm import Session

from jarvisx.database.models import (
    Workflow, WorkflowExecution, WorkflowExecutionLog,
    WorkflowExecutionStatus
)
from jarvisx.common.id_utils import generate_id
from jarvisx.workflows.nodes import get_node_executor
from jarvisx.config.configs import LANGFUSE_TRACE_WORKFLOWS
from jarvisx.tracing import get_langfuse, flush_langfuse


def _trace_workflows_enabled() -> bool:
    try:
        from jarvisx.services.platform_settings import PlatformSettingsService
        return PlatformSettingsService.get("tracing", "trace_workflows", LANGFUSE_TRACE_WORKFLOWS)
    except Exception:
        return LANGFUSE_TRACE_WORKFLOWS

logger = logging.getLogger(__name__)

MAX_TOTAL_EXECUTIONS = 1000


class WorkflowEngine:
    def __init__(self, db: Session):
        self.db = db
        self._current_trace = None
        self._organization_id = None
        self._workspace_id = None
        self._workflow_id = None

    async def execute(
        self,
        workflow_id: str,
        execution_id: str,
        trigger_data: Optional[dict] = None
    ) -> dict:
        from jarvisx.database.models import Workspace

        workflow = self.db.query(Workflow).filter(Workflow.id == workflow_id).first()
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")

        self._workflow_id = workflow_id
        workspace = self.db.query(Workspace).filter(Workspace.id == workflow.workspace_id).first()
        if workspace:
            self._organization_id = workspace.organization_id
            self._workspace_id = workspace.id

        execution = self.db.query(WorkflowExecution).filter(
            WorkflowExecution.id == execution_id
        ).first()
        if not execution:
            raise ValueError(f"Execution {execution_id} not found")

        trace = None
        if _trace_workflows_enabled():
            langfuse = get_langfuse()
            if langfuse:
                try:
                    trace = langfuse.start_span(
                        name=f"workflow:{workflow.name}",
                        metadata={
                            "workflow_id": workflow_id,
                            "workflow_name": workflow.name,
                            "execution_id": execution_id,
                            "workspace_id": workflow.workspace_id,
                        },
                    )
                except Exception as e:
                    logger.debug(f"Failed to create workflow trace: {e}")
        self._current_trace = trace

        execution.status = WorkflowExecutionStatus.RUNNING.value
        execution.started_at = datetime.utcnow()
        self.db.commit()

        try:
            result = await self._execute_workflow(workflow, execution, trigger_data)

            execution.status = WorkflowExecutionStatus.COMPLETED.value
            execution.completed_at = datetime.utcnow()
            self.db.commit()

            if trace:
                try:
                    trace.end(output={"status": "completed", "result_keys": list(result.keys()) if result else []})
                except Exception as trace_err:
                    logger.debug(f"Failed to end workflow trace: {trace_err}")

            return result
        except Exception as e:
            logger.exception(f"Workflow execution failed: {e}")
            execution.status = WorkflowExecutionStatus.FAILED.value
            execution.error_message = str(e)
            execution.completed_at = datetime.utcnow()
            self.db.commit()

            if trace:
                try:
                    trace.end(output={"status": "failed", "error": str(e)}, level="ERROR")
                except Exception as trace_err:
                    logger.debug(f"Failed to end error workflow trace: {trace_err}")

            raise
        finally:
            flush_langfuse()
            self._current_trace = None

    async def debug_start(self, workflow_id: str, execution_id: str, trigger_data: Optional[dict] = None) -> dict:
        workflow = self.db.query(Workflow).filter(Workflow.id == workflow_id).first()
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")

        self._workflow_id = workflow_id

        execution = self.db.query(WorkflowExecution).filter(WorkflowExecution.id == execution_id).first()
        if not execution:
            raise ValueError(f"Execution {execution_id} not found")

        definition = workflow.definition or {}
        nodes = definition.get("nodes", [])
        edges = definition.get("edges", [])
        trigger_nodes = [n for n in nodes if n["type"] in ("trigger", "chatbot_trigger")]
        if not trigger_nodes:
            trigger_nodes = nodes[:1]

        node_outputs = {}
        for tn in trigger_nodes:
            node_outputs[tn["id"]] = trigger_data or {}

        to_execute_ids = [n["id"] for n in trigger_nodes]

        state = {
            "node_outputs": node_outputs,
            "execution_counts": {},
            "to_execute": to_execute_ids,
            "completed_nodes": [],
            "current_node": None,
        }

        execution.status = WorkflowExecutionStatus.RUNNING.value
        execution.started_at = datetime.utcnow()
        execution.execution_metadata = {"debug_state": state}
        self.db.commit()

        return state

    async def debug_step(self, workflow_id: str, execution_id: str) -> dict:
        workflow = self.db.query(Workflow).filter(Workflow.id == workflow_id).first()
        execution = self.db.query(WorkflowExecution).filter(WorkflowExecution.id == execution_id).first()
        if not workflow or not execution:
            raise ValueError("Workflow or execution not found")

        self._workflow_id = workflow_id
        meta = execution.execution_metadata or {}
        state = meta.get("debug_state", {})
        to_execute_ids = state.get("to_execute", [])
        node_outputs = state.get("node_outputs", {})

        if not to_execute_ids:
            execution.status = WorkflowExecutionStatus.COMPLETED.value
            execution.completed_at = datetime.utcnow()
            self.db.commit()
            return {**state, "done": True}

        definition = workflow.definition or {}
        nodes = definition.get("nodes", [])
        edges = definition.get("edges", [])
        node_map = {n["id"]: n for n in nodes}
        adjacency = {}
        for edge in edges:
            adjacency.setdefault(edge["source"], []).append({
                "target": edge["target"],
                "sourceHandle": edge.get("sourceHandle"),
                "targetHandle": edge.get("targetHandle"),
            })

        current_id = to_execute_ids.pop(0)
        current_node = node_map.get(current_id)
        if not current_node:
            state["to_execute"] = to_execute_ids
            execution.execution_metadata = {**meta, "debug_state": state}
            self.db.commit()
            return {**state, "done": False, "skipped": current_id}

        input_data = self._gather_input(current_id, current_node["type"], edges, node_outputs, None)

        try:
            output = await self._execute_node(current_node, input_data, execution_id)
        except Exception as e:
            state["current_node"] = current_id
            state["to_execute"] = to_execute_ids
            state["error"] = str(e)
            execution.execution_metadata = {**meta, "debug_state": state}
            self.db.commit()
            return {**state, "done": False}

        node_outputs[current_id] = output
        state["completed_nodes"] = state.get("completed_nodes", []) + [current_id]
        state["node_outputs"] = node_outputs

        new_targets = []
        self._schedule_downstream(
            current_node, output, current_id, adjacency, node_map,
            state.get("execution_counts", {}), node_outputs, new_targets, {}
        )
        to_execute_ids.extend([n["id"] for n in new_targets])

        state["to_execute"] = to_execute_ids
        state["current_node"] = to_execute_ids[0] if to_execute_ids else None
        execution.execution_metadata = {**meta, "debug_state": state}
        self.db.commit()

        return {**state, "done": len(to_execute_ids) == 0, "executed_node": current_id, "output": output}

    def debug_get_state(self, execution_id: str) -> dict:
        execution = self.db.query(WorkflowExecution).filter(WorkflowExecution.id == execution_id).first()
        if not execution:
            raise ValueError("Execution not found")
        meta = execution.execution_metadata or {}
        return meta.get("debug_state", {})

    async def _execute_workflow(
        self,
        workflow: Workflow,
        execution: WorkflowExecution,
        trigger_data: Optional[dict]
    ) -> dict:
        definition = workflow.definition or {}
        nodes = definition.get("nodes", [])
        edges = definition.get("edges", [])

        if not nodes:
            return {"result": "No nodes to execute"}

        node_map = {node["id"]: node for node in nodes}

        adjacency = {}
        reverse_adjacency = {}
        for edge in edges:
            source = edge["source"]
            target = edge["target"]
            adjacency.setdefault(source, []).append({
                "target": target,
                "sourceHandle": edge.get("sourceHandle"),
                "targetHandle": edge.get("targetHandle"),
            })
            reverse_adjacency.setdefault(target, []).append(source)

        trigger_nodes = [n for n in nodes if n["type"] in ("trigger", "chatbot_trigger")]
        if not trigger_nodes:
            trigger_nodes = nodes[:1]

        node_outputs = {}
        execution_counts = {}
        loop_state = {}
        total_executions = 0

        for trigger_node in trigger_nodes:
            node_outputs[trigger_node["id"]] = trigger_data or {}

        to_execute = list(trigger_nodes)

        while to_execute:
            current_node = to_execute.pop(0)
            node_id = current_node["id"]
            node_type = current_node["type"]

            count = execution_counts.get(node_id, 0)
            is_in_loop = self._is_node_in_loop_body(node_id, node_map, adjacency)
            if not is_in_loop and count > 0:
                continue

            total_executions += 1
            if total_executions > MAX_TOTAL_EXECUTIONS:
                raise RuntimeError(f"Workflow exceeded maximum execution limit ({MAX_TOTAL_EXECUTIONS})")

            input_data = self._gather_input(node_id, node_type, edges, node_outputs, trigger_data)

            if node_type == "join":
                input_sources = reverse_adjacency.get(node_id, [])
                if not all(s in node_outputs for s in input_sources):
                    to_execute.append(current_node)
                    continue

            try:
                output = await self._execute_node(current_node, input_data, execution.id)
            except Exception as e:
                error_targets = self._get_handle_targets(node_id, "error", adjacency, node_map)
                if error_targets:
                    error_output = {"error": str(e), "failed_node": node_id, "data": input_data}
                    node_outputs[node_id] = error_output
                    execution_counts[node_id] = count + 1
                    for t_node in error_targets:
                        node_outputs[t_node["id"]] = error_output
                        to_execute.append(t_node)
                    continue
                raise

            node_outputs[node_id] = output
            execution_counts[node_id] = count + 1

            self._schedule_downstream(
                current_node, output, node_id, adjacency, node_map,
                execution_counts, node_outputs, to_execute, loop_state
            )

        last_executed_id = None
        for node in nodes:
            if node["id"] in node_outputs:
                last_executed_id = node["id"]
        return node_outputs.get(last_executed_id, {})

    def _gather_input(self, node_id, node_type, edges, node_outputs, trigger_data):
        if node_type in ("trigger", "chatbot_trigger"):
            return node_outputs.get(node_id, trigger_data or {})

        input_sources = [e["source"] for e in edges if e["target"] == node_id]
        if input_sources:
            combined = {}
            for src in input_sources:
                if src in node_outputs:
                    src_out = node_outputs[src]
                    if isinstance(src_out, dict):
                        combined.update(src_out)
            return combined
        return node_outputs.get(node_id, {})

    def _schedule_downstream(
        self, current_node, output, node_id, adjacency, node_map,
        execution_counts, node_outputs, to_execute, loop_state
    ):
        if node_id not in adjacency:
            return

        node_type = current_node["type"]

        for edge_info in adjacency[node_id]:
            target_id = edge_info["target"]
            target_node = node_map.get(target_id)
            if not target_node:
                continue

            handle = edge_info.get("sourceHandle")

            if node_type == "condition":
                condition_result = output.get("result", False)
                if (handle == "true" and condition_result) or (handle == "false" and not condition_result):
                    node_outputs[target_id] = output.get("data", {})
                    to_execute.append(target_node)

            elif node_type == "switch":
                matched_case = output.get("matched_case", "default")
                if handle == matched_case or (handle == "default" and not output.get("matched")):
                    node_outputs[target_id] = output.get("data", {})
                    to_execute.append(target_node)

            elif node_type == "loop":
                should_continue = output.get("continue", False)
                if handle == "loop" and should_continue:
                    node_outputs[target_id] = output.get("data", {})
                    to_execute.append(target_node)
                elif handle == "done" and not should_continue:
                    node_outputs[target_id] = output.get("data", {})
                    to_execute.append(target_node)

            elif node_type == "error_handler":
                if handle == "try":
                    node_outputs[target_id] = output.get("data", output)
                    to_execute.append(target_node)

            elif node_type == "fork":
                node_outputs[target_id] = output.get("data", output)
                to_execute.append(target_node)

            elif node_type == "foreach":
                items = output.get("items", [])
                current_index = output.get("current_index", 0)
                if handle == "body" and current_index < len(items):
                    item_data = {
                        **output.get("data", {}),
                        "item": items[current_index],
                        "foreach": {"index": current_index, "total": len(items), "item": items[current_index]},
                    }
                    node_outputs[target_id] = item_data
                    to_execute.append(target_node)
                elif handle == "done" and current_index >= len(items):
                    node_outputs[target_id] = output.get("data", {})
                    to_execute.append(target_node)

            elif handle == "error":
                pass

            else:
                node_outputs[target_id] = output
                to_execute.append(target_node)

    def _get_handle_targets(self, node_id, handle_name, adjacency, node_map):
        targets = []
        for edge_info in adjacency.get(node_id, []):
            if edge_info.get("sourceHandle") == handle_name:
                target = node_map.get(edge_info["target"])
                if target:
                    targets.append(target)
        return targets

    def _is_node_in_loop_body(self, node_id, node_map, adjacency):
        for nid, edges_list in adjacency.items():
            node = node_map.get(nid)
            if node and node["type"] == "loop":
                for edge_info in edges_list:
                    if edge_info.get("sourceHandle") == "loop" and edge_info["target"] == node_id:
                        return True
        return False

    async def _execute_node(
        self,
        node: dict,
        input_data: dict,
        execution_id: str
    ) -> dict:
        node_id = node["id"]
        node_type = node["type"]
        node_data = node.get("data", {})
        node_data["organization_id"] = self._organization_id
        node_data["workspace_id"] = self._workspace_id
        node_data["workflow_id"] = self._workflow_id
        config = node_data.get("config", {})
        node_label = node_data.get("label", node_type)

        span = None
        if _trace_workflows_enabled() and self._current_trace:
            langfuse = get_langfuse()
            if langfuse:
                try:
                    span = langfuse.start_span(
                        name=f"node:{node_label}",
                        metadata={"node_id": node_id, "node_type": node_type, "input_keys": list(input_data.keys())},
                    )
                except Exception as e:
                    logger.debug(f"Failed to create node span: {e}")

        log = WorkflowExecutionLog(
            id=generate_id(),
            execution_id=execution_id,
            node_id=node_id,
            node_type=node_type,
            status=WorkflowExecutionStatus.RUNNING.value,
            input_data=input_data,
            started_at=datetime.utcnow(),
        )
        self.db.add(log)
        self.db.commit()

        retry_config = config.get("retry", {})
        max_retries = int(retry_config.get("max_retries", 0))
        backoff = retry_config.get("backoff", "none")
        initial_delay_ms = int(retry_config.get("initial_delay_ms", 1000))

        last_error = None
        for attempt in range(max_retries + 1):
            try:
                executor = get_node_executor(node_type)
                output = await executor.execute(config, input_data, node_data)

                log.status = WorkflowExecutionStatus.COMPLETED.value
                log.output_data = output
                log.completed_at = datetime.utcnow()
                self.db.commit()

                if span:
                    try:
                        span.end(output={"output_keys": list(output.keys()) if output else []})
                    except Exception as span_err:
                        logger.debug(f"Failed to end node span: {span_err}")

                return output
            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    delay = self._calculate_retry_delay(attempt, backoff, initial_delay_ms)
                    logger.warning(f"Node {node_id} attempt {attempt + 1} failed, retrying in {delay}ms: {e}")
                    await asyncio.sleep(delay / 1000.0)
                    continue

                logger.exception(f"Node {node_id} execution failed after {attempt + 1} attempts: {e}")
                log.status = WorkflowExecutionStatus.FAILED.value
                log.error = str(e)
                log.completed_at = datetime.utcnow()
                self.db.commit()

                if max_retries > 0:
                    self._create_dead_letter(execution_id, node_id, node_type, str(e), input_data, attempt + 1)

                if span:
                    try:
                        span.end(output=None, level="ERROR", status_message=str(e))
                    except Exception as span_err:
                        logger.debug(f"Failed to end error node span: {span_err}")

                raise

    def _calculate_retry_delay(self, attempt: int, backoff: str, initial_delay_ms: int) -> int:
        if backoff == "linear":
            return initial_delay_ms * (attempt + 1)
        if backoff == "exponential":
            return initial_delay_ms * (2 ** attempt)
        return initial_delay_ms

    def _create_dead_letter(self, execution_id: str, node_id: str, node_type: str, error: str, input_data: dict, retry_count: int):
        try:
            from jarvisx.database.models import WorkflowDeadLetter
            dl = WorkflowDeadLetter(
                id=generate_id(),
                execution_id=execution_id,
                workflow_id=self._workflow_id,
                node_id=node_id,
                node_type=node_type,
                error=error,
                input_data=input_data,
                retry_count=retry_count,
                status="pending",
            )
            self.db.add(dl)
            self.db.commit()
        except Exception as e:
            logger.warning(f"Failed to create dead letter entry: {e}")
