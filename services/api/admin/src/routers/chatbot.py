import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from jarvisx.database.session import get_db
from jarvisx.database.models import (
    Workflow, WorkflowTriggerType, Workspace, User,
    ChatbotConversation, ChatbotMessage
)
from jarvisx.common.id_utils import generate_id
from services.api.admin.src.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chatbot", tags=["chatbot"])

_gateway_cache: Dict[str, Any] = {}


async def _get_or_create_gateway(organization_id: str):
    from services.gateways.voice.src.gateway import VoiceGateway
    
    if organization_id not in _gateway_cache:
        logger.info("[CHATBOT ROUTER] Creating new VoiceGateway for org: %s", organization_id)
        gateway = VoiceGateway(organization_id=organization_id)
        await gateway.create()
        _gateway_cache[organization_id] = gateway
        logger.info("[CHATBOT ROUTER] Gateway cached for organization: %s", organization_id)
    else:
        logger.debug("[CHATBOT ROUTER] Reusing cached gateway for org: %s", organization_id)
    
    return _gateway_cache[organization_id]


class ChatbotConfigResponse(BaseModel):
    workflow_id: str
    bot_name: str
    chat_mode: str
    allow_file_upload: bool
    connected_agents: List[str]
    agent_hierarchy: Optional[dict] = None


class ChatMessage(BaseModel):
    role: str
    content: str

class SendMessageRequest(BaseModel):
    messages: List[ChatMessage]
    session_id: Optional[str] = None
    files: Optional[List[dict]] = None


class ConversationResponse(BaseModel):
    id: str
    session_id: str
    title: Optional[str]
    created_at: datetime
    updated_at: datetime
    message_count: int


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    created_at: datetime


class ConversationDetailResponse(BaseModel):
    id: str
    session_id: str
    title: Optional[str]
    created_at: datetime
    messages: List[MessageResponse]


class ConversationUpdateRequest(BaseModel):
    title: Optional[str] = None


def get_chatbot_workflow(workflow_id: str, db: Session) -> Workflow:
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    
    if not workflow:
        raise HTTPException(status_code=404, detail="Chatbot not found")
    
    if workflow.trigger_type != WorkflowTriggerType.CHATBOT.value:
        raise HTTPException(status_code=400, detail="This workflow is not a chatbot")
    
    if not workflow.is_active:
        raise HTTPException(status_code=400, detail="Chatbot is not active")
    
    return workflow


def get_organization_id_from_workflow(workflow: Workflow, db: Session) -> str:
    workspace = db.query(Workspace).filter(Workspace.id == workflow.workspace_id).first()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace.organization_id


@router.get("/{workflow_id}/config", response_model=ChatbotConfigResponse)
async def get_chatbot_config(
    workflow_id: str,
    warmup: bool = Query(False, description="Pre-initialize agents in background"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workflow = get_chatbot_workflow(workflow_id, db)
    organization_id = get_organization_id_from_workflow(workflow, db)
    
    config = workflow.trigger_config or {}
    
    agent_hierarchy = config.get("agent_hierarchy")
    connected_agents = config.get("connected_agents", [])
    
    if agent_hierarchy is None and connected_agents:
        agent_hierarchy = {code: {"enabled": True, "sub_agents": {}} for code in connected_agents}
    
    if warmup:
        logger.info("[CHATBOT CONFIG] Scheduling warmup task for workflow: %s", workflow_id)
        background_tasks.add_task(_warmup_workflow, workflow_id, organization_id)
    
    return ChatbotConfigResponse(
        workflow_id=workflow_id,
        bot_name=config.get("bot_name", "JarvisX Assistant"),
        chat_mode=config.get("chat_mode", "both"),
        allow_file_upload=config.get("allow_file_upload", True),
        connected_agents=connected_agents,
        agent_hierarchy=agent_hierarchy,
    )


async def _warmup_workflow(workflow_id: str, organization_id: str):
    try:
        logger.info("[CHATBOT WARMUP] Starting warmup for workflow: %s", workflow_id)
        gateway = await _get_or_create_gateway(organization_id)
        
        runner = gateway._get_or_create_runner(workflow_id)
        
        agent = runner.agent
        if hasattr(agent, '_ensure_sub_agents_loaded'):
            await agent._ensure_sub_agents_loaded()
            sub_agent_names = [a.name for a in agent.sub_agents] if agent.sub_agents else []
            logger.info("[CHATBOT WARMUP] Orchestrator sub-agents loaded: %s", sub_agent_names)
            
            for sub_agent in (agent.sub_agents or []):
                if hasattr(sub_agent, '_ensure_sub_agents_loaded'):
                    await sub_agent._ensure_sub_agents_loaded()
        
        logger.info("[CHATBOT WARMUP] Warmup completed for workflow: %s", workflow_id)
    except Exception as e:
        logger.error("[CHATBOT WARMUP] Error warming up workflow %s: %s", workflow_id, e)


@router.post("/{workflow_id}/warmup")
async def warmup_chatbot(
    workflow_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workflow = get_chatbot_workflow(workflow_id, db)
    organization_id = get_organization_id_from_workflow(workflow, db)
    
    await _warmup_workflow(workflow_id, organization_id)
    
    return {"status": "ok", "message": "Chatbot warmed up successfully"}


@router.post("/{workflow_id}/chat")
async def chat_with_bot(
    workflow_id: str,
    request: SendMessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not request.messages:
        raise HTTPException(status_code=400, detail="No messages provided")
    
    last_user_message = None
    for msg in reversed(request.messages):
        if msg.role == "user":
            last_user_message = msg.content
            break
    
    if not last_user_message:
        raise HTTPException(status_code=400, detail="No user message found")
    
    workflow = get_chatbot_workflow(workflow_id, db)
    
    organization_id = get_organization_id_from_workflow(workflow, db)
    user_id = current_user.user_id
    
    logger.info("=" * 60)
    logger.info("[CHATBOT ROUTER] Processing chat request")
    logger.info("[CHATBOT ROUTER] Workflow ID: %s", workflow_id)
    logger.info("[CHATBOT ROUTER] Workflow Name: %s", workflow.name)
    logger.info("[CHATBOT ROUTER] Organization ID: %s", organization_id)
    logger.info("[CHATBOT ROUTER] Sub-agents will be loaded lazily by Orchestrator")
    logger.info("=" * 60)
    
    session_id = request.session_id or generate_id()
    
    conversation = db.query(ChatbotConversation).filter(
        ChatbotConversation.workflow_id == workflow_id,
        ChatbotConversation.session_id == session_id,
        ChatbotConversation.organization_id == organization_id,
    ).first()
    
    if not conversation:
        conversation = ChatbotConversation(
            id=generate_id(),
            workflow_id=workflow_id,
            user_id=user_id,
            organization_id=organization_id,
            session_id=session_id,
            title=last_user_message[:50] if last_user_message else "New Chat",
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
    
    user_message = ChatbotMessage(
        id=generate_id(),
        conversation_id=conversation.id,
        role="user",
        content=last_user_message,
    )
    db.add(user_message)
    db.commit()
    
    gateway = await _get_or_create_gateway(organization_id)
    logger.info("[CHATBOT ROUTER] Processing message with workflow_id: %s, session_id: %s", workflow_id, session_id)
    
    import json
    
    async def generate_response():
        full_response = []
        async for chunk in gateway.process_text_message_stream(
            message=last_user_message,
            workflow_id=workflow_id,
            user_id=user_id or "anonymous",
            session_id=session_id,
            files=request.files,
        ):
            content = chunk.get("content", "") if isinstance(chunk, dict) else str(chunk)
            if content:
                full_response.append(content)
                yield f"0:{json.dumps(content)}\n"
        
        assistant_content = "".join(full_response)
        assistant_message = ChatbotMessage(
            id=generate_id(),
            conversation_id=conversation.id,
            role="assistant",
            content=assistant_content,
        )
        db.add(assistant_message)
        conversation.updated_at = datetime.utcnow()
        db.commit()
        
        finish_data = {"finishReason": "stop"}
        yield f"d:{json.dumps(finish_data)}\n"
        
        session_data = [{"session_id": session_id, "context_id": session_id}]
        yield f"8:{json.dumps(session_data)}\n"
    
    return StreamingResponse(
        generate_response(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Session-Id": session_id,
        }
    )


@router.get("/{workflow_id}/conversations", response_model=List[ConversationResponse])
def list_conversations(
    workflow_id: str,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workflow = get_chatbot_workflow(workflow_id, db)
    organization_id = get_organization_id_from_workflow(workflow, db)
    
    conversations = db.query(ChatbotConversation).filter(
        ChatbotConversation.workflow_id == workflow_id,
        ChatbotConversation.organization_id == organization_id,
        ChatbotConversation.user_id == current_user.user_id,
    ).order_by(
        ChatbotConversation.updated_at.desc()
    ).offset(offset).limit(limit).all()
    
    result = []
    for conv in conversations:
        message_count = db.query(ChatbotMessage).filter(
            ChatbotMessage.conversation_id == conv.id
        ).count()
        
        result.append(ConversationResponse(
            id=conv.id,
            session_id=conv.session_id,
            title=conv.title,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            message_count=message_count,
        ))
    
    return result


@router.get("/{workflow_id}/conversations/{conversation_id}", response_model=ConversationDetailResponse)
def get_conversation(
    workflow_id: str,
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workflow = get_chatbot_workflow(workflow_id, db)
    organization_id = get_organization_id_from_workflow(workflow, db)
    
    conversation = db.query(ChatbotConversation).filter(
        ChatbotConversation.id == conversation_id,
        ChatbotConversation.workflow_id == workflow_id,
        ChatbotConversation.organization_id == organization_id,
        ChatbotConversation.user_id == current_user.user_id,
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    messages = db.query(ChatbotMessage).filter(
        ChatbotMessage.conversation_id == conversation_id
    ).order_by(ChatbotMessage.created_at.asc()).all()
    
    return ConversationDetailResponse(
        id=conversation.id,
        session_id=conversation.session_id,
        title=conversation.title,
        created_at=conversation.created_at,
        messages=[
            MessageResponse(
                id=msg.id,
                role=msg.role,
                content=msg.content,
                created_at=msg.created_at,
            )
            for msg in messages
        ],
    )


@router.patch("/{workflow_id}/conversations/{conversation_id}", response_model=ConversationResponse)
def update_conversation(
    workflow_id: str,
    conversation_id: str,
    request: ConversationUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workflow = get_chatbot_workflow(workflow_id, db)
    organization_id = get_organization_id_from_workflow(workflow, db)
    
    conversation = db.query(ChatbotConversation).filter(
        ChatbotConversation.id == conversation_id,
        ChatbotConversation.workflow_id == workflow_id,
        ChatbotConversation.organization_id == organization_id,
        ChatbotConversation.user_id == current_user.user_id,
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    if request.title is not None:
        conversation.title = request.title
    
    conversation.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(conversation)
    
    message_count = db.query(ChatbotMessage).filter(
        ChatbotMessage.conversation_id == conversation.id
    ).count()
    
    return ConversationResponse(
        id=conversation.id,
        session_id=conversation.session_id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        message_count=message_count,
    )


@router.delete("/{workflow_id}/conversations/{conversation_id}")
def delete_conversation(
    workflow_id: str,
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workflow = get_chatbot_workflow(workflow_id, db)
    organization_id = get_organization_id_from_workflow(workflow, db)
    
    conversation = db.query(ChatbotConversation).filter(
        ChatbotConversation.id == conversation_id,
        ChatbotConversation.workflow_id == workflow_id,
        ChatbotConversation.organization_id == organization_id,
        ChatbotConversation.user_id == current_user.user_id,
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    db.delete(conversation)
    db.commit()
    
    return {"message": "Conversation deleted successfully"}
