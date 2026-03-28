from jarvisx.workflows.nodes.base import BaseNodeExecutor
from jarvisx.workflows.nodes.trigger import TriggerNodeExecutor
from jarvisx.workflows.nodes.agent import AgentNodeExecutor
from jarvisx.workflows.nodes.http import HTTPNodeExecutor
from jarvisx.workflows.nodes.condition import ConditionNodeExecutor
from jarvisx.workflows.nodes.transform import TransformNodeExecutor
from jarvisx.workflows.nodes.email import EmailNodeExecutor
from jarvisx.workflows.nodes.file_save import FileSaveNodeExecutor
from jarvisx.workflows.nodes.file_read import FileReadNodeExecutor
from jarvisx.workflows.nodes.notification import NotificationNodeExecutor
from jarvisx.workflows.nodes.loop import LoopNodeExecutor
from jarvisx.workflows.nodes.switch import SwitchNodeExecutor
from jarvisx.workflows.nodes.fork import ForkNodeExecutor, JoinNodeExecutor
from jarvisx.workflows.nodes.error_handler import ErrorHandlerNodeExecutor
from jarvisx.workflows.nodes.approval import ApprovalNodeExecutor
from jarvisx.workflows.nodes.delay import DelayNodeExecutor
from jarvisx.workflows.nodes.foreach import ForEachNodeExecutor
from jarvisx.workflows.nodes.sub_workflow import SubWorkflowNodeExecutor
from jarvisx.workflows.nodes.webhook_response import WebhookResponseNodeExecutor
from jarvisx.workflows.nodes.database import DatabaseNodeExecutor
from jarvisx.workflows.nodes.cloud_storage import CloudStorageNodeExecutor
from jarvisx.workflows.nodes.google_sheets import GoogleSheetsNodeExecutor
from jarvisx.workflows.nodes.data_transform import DataTransformNodeExecutor
from jarvisx.workflows.nodes.python_code import PythonCodeNodeExecutor

_executors = {
    "trigger": TriggerNodeExecutor(),
    "chatbot_trigger": TriggerNodeExecutor(),
    "agent": AgentNodeExecutor(),
    "http": HTTPNodeExecutor(),
    "condition": ConditionNodeExecutor(),
    "transform": TransformNodeExecutor(),
    "email": EmailNodeExecutor(),
    "file_save": FileSaveNodeExecutor(),
    "file_read": FileReadNodeExecutor(),
    "notification": NotificationNodeExecutor(),
    "loop": LoopNodeExecutor(),
    "switch": SwitchNodeExecutor(),
    "fork": ForkNodeExecutor(),
    "join": JoinNodeExecutor(),
    "error_handler": ErrorHandlerNodeExecutor(),
    "approval": ApprovalNodeExecutor(),
    "delay": DelayNodeExecutor(),
    "foreach": ForEachNodeExecutor(),
    "sub_workflow": SubWorkflowNodeExecutor(),
    "webhook_response": WebhookResponseNodeExecutor(),
    "database": DatabaseNodeExecutor(),
    "cloud_storage": CloudStorageNodeExecutor(),
    "google_sheets": GoogleSheetsNodeExecutor(),
    "data_transform": DataTransformNodeExecutor(),
    "python_code": PythonCodeNodeExecutor(),
}


def get_node_executor(node_type: str) -> BaseNodeExecutor:
    executor = _executors.get(node_type)
    if not executor:
        raise ValueError(f"Unknown node type: {node_type}")
    return executor


__all__ = [
    "BaseNodeExecutor",
    "get_node_executor",
    "TriggerNodeExecutor",
    "AgentNodeExecutor",
    "HTTPNodeExecutor",
    "ConditionNodeExecutor",
    "TransformNodeExecutor",
    "EmailNodeExecutor",
    "FileSaveNodeExecutor",
    "FileReadNodeExecutor",
    "NotificationNodeExecutor",
    "LoopNodeExecutor",
    "SwitchNodeExecutor",
    "ForkNodeExecutor",
    "JoinNodeExecutor",
    "ErrorHandlerNodeExecutor",
    "ApprovalNodeExecutor",
    "DelayNodeExecutor",
    "ForEachNodeExecutor",
    "SubWorkflowNodeExecutor",
    "WebhookResponseNodeExecutor",
    "DatabaseNodeExecutor",
    "CloudStorageNodeExecutor",
    "GoogleSheetsNodeExecutor",
    "DataTransformNodeExecutor",
    "PythonCodeNodeExecutor",
]
