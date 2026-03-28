from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field


class NodePosition(BaseModel):
    x: float
    y: float


class WorkflowNode(BaseModel):
    id: str
    type: str
    position: NodePosition
    data: dict = Field(default_factory=dict)


class WorkflowEdge(BaseModel):
    id: Optional[str] = None
    source: str
    target: str
    sourceHandle: Optional[str] = None
    targetHandle: Optional[str] = None


class WorkflowDefinition(BaseModel):
    nodes: List[WorkflowNode] = Field(default_factory=list)
    edges: List[WorkflowEdge] = Field(default_factory=list)


class WorkflowCreate(BaseModel):
    name: str
    description: Optional[str] = None
    definition: WorkflowDefinition = Field(default_factory=WorkflowDefinition)
    trigger_type: str = "manual"
    trigger_config: Optional[dict] = None
    is_active: bool = True


class WorkflowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    definition: Optional[WorkflowDefinition] = None
    trigger_type: Optional[str] = None
    trigger_config: Optional[dict] = None
    is_active: Optional[bool] = None


class LastExecutionInfo(BaseModel):
    id: str
    status: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]


class WorkflowResponse(BaseModel):
    id: str
    workspace_id: str
    name: str
    description: Optional[str]
    definition: dict
    trigger_type: str
    trigger_config: Optional[dict]
    is_active: bool
    created_by: Optional[str]
    created_at: datetime
    updated_at: datetime
    last_execution: Optional[LastExecutionInfo] = None

    class Config:
        from_attributes = True


class WorkflowListResponse(BaseModel):
    workflows: List[WorkflowResponse]
    total: int


class ExecutionLogResponse(BaseModel):
    id: str
    node_id: str
    node_type: str
    status: str
    input_data: Optional[dict]
    output_data: Optional[dict]
    error: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class WorkflowExecutionResponse(BaseModel):
    id: str
    workflow_id: str
    status: str
    trigger_type: str
    trigger_data: Optional[dict]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]
    created_at: datetime
    logs: List[ExecutionLogResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


class ExecutionListResponse(BaseModel):
    executions: List[WorkflowExecutionResponse]
    total: int


class ExecuteWorkflowRequest(BaseModel):
    trigger_data: Optional[dict] = None
    sync: bool = False


class ExecuteWorkflowResponse(BaseModel):
    execution_id: str
    status: str
    message: str
