import json
import logging
import sys
from urllib.parse import urlparse
from typing import Optional, Tuple

import asyncclick as click
import uvicorn
import jwt
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse, StreamingResponse
from starlette.routing import Route, WebSocketRoute

from services.gateways.voice.src.service import VoiceGatewayService
from jarvisx.a2a.llm_config import LLMConfigNotFoundError
from jarvisx.tracing.litellm_integration import setup_litellm_langfuse_callback

setup_litellm_langfuse_callback()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

_gateway_services: dict[str, VoiceGatewayService] = {}


def _extract_org_from_request(request: Request) -> Tuple[Optional[str], Optional[str]]:
    org_id = request.headers.get("x-tenant-id") or request.headers.get("x-organization-id")
    user_id = request.headers.get("x-user-id")
    
    if org_id and user_id:
        return org_id, user_id
    
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        try:
            token = auth_header[7:]
            payload = jwt.decode(token, options={"verify_signature": False})
            if not org_id:
                org_id = payload.get("org_id") or payload.get("organization_id")
            if not user_id:
                user_id = payload.get("sub")
        except Exception:
            pass
    
    return org_id, user_id


async def _get_or_create_gateway(organization_id: str) -> VoiceGatewayService:
    if organization_id not in _gateway_services:
        service = VoiceGatewayService(organization_id=organization_id)
        await service.create()
        _gateway_services[organization_id] = service
        logger.info(f"Created new gateway service for organization: {organization_id}")
    return _gateway_services[organization_id]


def parse_url(url: str) -> tuple[str, int, str]:
    parsed = urlparse(url)
    host = parsed.hostname or "localhost"
    port = parsed.port or 80
    normalized_url = parsed._replace(path="/").geturl()
    return host, port, normalized_url


def create_health_endpoint(service_name: str, version: str = "1.0.0"):
    async def health_endpoint(request):
        return JSONResponse({
            "status": "healthy",
            "service": service_name,
            "version": version
        })
    return health_endpoint


def _extract_content(msg: dict) -> str:
    content = msg.get("content", "")
    if isinstance(content, dict):
        return content.get("text", content.get("content", str(content)))
    if isinstance(content, list):
        return " ".join(
            p.get("text", p.get("content", "")) if isinstance(p, dict) else str(p)
            for p in content
        )
    return str(content) if content else ""


def _extract_files(msg: dict) -> list:
    data = msg.get("data", {})
    if isinstance(data, dict):
        return data.get("files", [])
    return []


def _extract_session_id(msg: dict) -> str | None:
    for key in ["session_id", "sessionId", "context_id", "contextId"]:
        if key in msg:
            return msg.get(key)
    metadata = msg.get("metadata", {})
    if isinstance(metadata, dict):
        return metadata.get("session_id") or metadata.get("sessionId") or metadata.get("context_id") or metadata.get("contextId")
    return None


@click.command()
@click.option("--url", type=str, default="http://localhost:9003/", help="Base URL to run the gateway on")
async def main(url: str) -> None:
    host, port, _ = parse_url(url)
    
    async def speech_to_text_endpoint(request: Request):
        try:
            org_id, user_id_from_token = _extract_org_from_request(request)
            
            if not org_id:
                return JSONResponse({
                    "error": "llm_config_required",
                    "message": "Organization ID is required. Please provide x-tenant-id header or valid JWT token.",
                    "action": "Ensure your request includes proper authentication."
                }, status_code=403)
            
            form = await request.form()
            audio_file = form.get("audio")
            if not audio_file:
                return JSONResponse({"error": "Audio file is required"}, status_code=400)
            
            try:
                service = await _get_or_create_gateway(org_id)
            except LLMConfigNotFoundError as e:
                return JSONResponse({
                    "error": "llm_config_required",
                    "message": str(e),
                    "action": "Please configure LLM settings in the LLM Settings page."
                }, status_code=403)
            
            audio_bytes = await audio_file.read()
            text = await service.transcribe_audio_bytes(audio_bytes)
            
            if not text:
                return JSONResponse({"text": "", "status": "no_speech"})
            return JSONResponse({"text": text, "status": "success"})
        except LLMConfigNotFoundError as e:
            return JSONResponse({
                "error": "llm_config_required",
                "message": str(e),
                "action": "Please configure LLM settings in the LLM Settings page."
            }, status_code=403)
        except Exception as e:
            logger.error(f"Error in speech_to_text: {e}")
            return JSONResponse({"error": "Failed to process audio"}, status_code=500)
    
    async def text_to_speech_endpoint(request: Request):
        try:
            org_id, user_id_from_token = _extract_org_from_request(request)
            
            if not org_id:
                return JSONResponse({
                    "error": "llm_config_required",
                    "message": "Organization ID is required. Please provide x-tenant-id header or valid JWT token.",
                    "action": "Ensure your request includes proper authentication."
                }, status_code=403)
            
            data = await request.json()
            text = data.get("text", "")
            if not text:
                return JSONResponse({"error": "Text is required"}, status_code=400)
            
            try:
                service = await _get_or_create_gateway(org_id)
            except LLMConfigNotFoundError as e:
                return JSONResponse({
                    "error": "llm_config_required",
                    "message": str(e),
                    "action": "Please configure LLM settings in the LLM Settings page."
                }, status_code=403)
            
            audio_bytes = await service.text_to_speech(text, data.get("voice"))
            return Response(content=audio_bytes, media_type="audio/mpeg")
        except LLMConfigNotFoundError as e:
            return JSONResponse({
                "error": "llm_config_required",
                "message": str(e),
                "action": "Please configure LLM settings in the LLM Settings page."
            }, status_code=403)
        except Exception as e:
            logger.error(f"Error in text_to_speech: {e}")
            return JSONResponse({"error": "Failed to generate audio"}, status_code=500)
    
    async def chat_endpoint(request: Request):
        try:
            org_id, user_id_from_token = _extract_org_from_request(request)
            
            if not org_id:
                return JSONResponse({
                    "error": "llm_config_required",
                    "message": "Organization ID is required. Please provide x-tenant-id header or valid JWT token.",
                    "action": "Ensure your request includes proper authentication."
                }, status_code=403)
            
            data = await request.json()
            messages = data.get("messages", [])
            
            if not messages:
                return JSONResponse({"error": "No messages provided"}, status_code=400)
            
            last_message = None
            session_id = None
            files = []
            for msg in reversed(messages):
                if msg.get("role") == "user":
                    last_message = _extract_content(msg)
                    session_id = _extract_session_id(msg)
                    files = _extract_files(msg)
                    break
            
            if not session_id:
                for msg in reversed(messages):
                    session_id = _extract_session_id(msg)
                    if session_id:
                        break
            
            if not last_message and not files:
                return JSONResponse({"error": "No user message found"}, status_code=400)
            
            session_id = session_id or data.get("session_id") or data.get("context_id")
            workflow_id = data.get("workflow_id") or request.headers.get("x-workflow-id") or data.get("workspace_id") or request.headers.get("x-workspace-id")
            user_id = data.get("user_id") or request.headers.get("x-user-id") or user_id_from_token
            
            if not workflow_id or not user_id:
                return JSONResponse({"error": "Invalid request: workflow_id and user_id are required"}, status_code=400)
            
            if not isinstance(last_message, str):
                last_message = json.dumps(last_message) if isinstance(last_message, (dict, list)) else str(last_message)
            
            try:
                service = await _get_or_create_gateway(org_id)
            except LLMConfigNotFoundError as e:
                return JSONResponse({
                    "error": "llm_config_required",
                    "message": str(e),
                    "action": "Please configure LLM settings in the LLM Settings page."
                }, status_code=403)
            
            logger.info(f"[CHAT] Processing: workflow={workflow_id}, user={user_id}, session={session_id}")
            
            updated_session_id = session_id
            
            async def generate_stream():
                nonlocal updated_session_id
                async for chunk in service.process_text_message_stream(
                    message=last_message, 
                    workflow_id=workflow_id, 
                    user_id=user_id,
                    session_id=session_id,
                    files=files
                ):
                    content = chunk.get("content", "")
                    if chunk.get("session_id"):
                        updated_session_id = chunk["session_id"]
                    yield f"0:{json.dumps(content)}\n"
                
                if updated_session_id:
                    yield f"8:{json.dumps([{'session_id': updated_session_id, 'context_id': updated_session_id}])}\n"
            
            return StreamingResponse(
                generate_stream(),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"}
            )
        except LLMConfigNotFoundError as e:
            return JSONResponse({
                "error": "llm_config_required",
                "message": str(e),
                "action": "Please configure LLM settings in the LLM Settings page."
            }, status_code=403)
        except Exception as e:
            logger.error(f"Error in chat: {e}")
            return JSONResponse({"error": "Failed to process message"}, status_code=500)
    
    async def on_shutdown():
        for service in _gateway_services.values():
            await service.cleanup()
        _gateway_services.clear()
    
    from services.gateways.voice.src.ws_handler import ws_voice_handler

    app = Starlette(
        routes=[
            Route("/health", create_health_endpoint("voice-gateway"), methods=["GET"]),
            Route("/api/audio/transcribe-only", speech_to_text_endpoint, methods=["POST"]),
            Route("/api/audio/tts", text_to_speech_endpoint, methods=["POST"]),
            Route("/api/chat", chat_endpoint, methods=["POST"]),
            WebSocketRoute("/ws/voice", ws_voice_handler),
        ],
        on_shutdown=[on_shutdown]
    )
    
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
    
    config = uvicorn.Config(app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)
    
    await server.serve()


if __name__ == "__main__":
    main()
