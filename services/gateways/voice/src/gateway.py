import logging
from typing import Any, AsyncIterator, Dict, List, Optional
from io import BytesIO

import openai
from google.adk.runners import Runner
from google.genai.types import Content, Part

from jarvisx.a2a.llm_config import (
    get_tts_config,
    get_stt_config,
    LLMConfigNotFoundError,
)
from jarvisx.a2a.storage import get_session_service
from jarvisx.common.multimedia import create_part_from_bytes, create_part_from_text, decode_base64_content
from services.agents.orchestrator.src.agent import create_orchestrator_agent

logger = logging.getLogger(__name__)


def _sanitize_app_name(workflow_id: str) -> str:
    return f"workflow_{workflow_id.replace('-', '_')}"


class VoiceGateway:
    def __init__(self, organization_id: str):
        if not organization_id:
            raise ValueError("organization_id is required to create VoiceGateway")
        
        self.organization_id = organization_id
        self._workflow_runners: Dict[str, Runner] = {}
        self._session_service = get_session_service()
        self._llm_config_error = None
        
        self._init_audio_client()
    
    def _init_audio_client(self):
        tts_config = get_tts_config(self.organization_id)
        stt_config = get_stt_config(self.organization_id)
        
        api_key = tts_config.api_key
        api_base = tts_config.api_base_url
        
        if not api_key or not api_base:
            raise LLMConfigNotFoundError(
                f"TTS/STT configuration incomplete for organization {self.organization_id}. "
                "Please configure TTS and STT settings in the LLM Settings page."
            )
        
        self.client = openai.OpenAI(api_key=api_key, base_url=api_base)
        self.stt_model = stt_config.model_name
        self.tts_model = tts_config.model_name
        self.language = "en"
        self.default_voice = "alloy"
    
    def _get_or_create_runner(self, workflow_id: str) -> Runner:
        if workflow_id not in self._workflow_runners:
            app_name = _sanitize_app_name(workflow_id)
            logger.info("=" * 60)
            logger.info("[VOICE GATEWAY] Creating Runner for workflow: %s", workflow_id)
            logger.info("[VOICE GATEWAY] App name: %s", app_name)
            logger.info("[VOICE GATEWAY] Organization ID: %s", self.organization_id)
            logger.info("=" * 60)
            
            orchestrator = create_orchestrator_agent(
                workflow_id=workflow_id,
                organization_id=self.organization_id
            )
            logger.info("[VOICE GATEWAY] Lazy orchestrator created: %s", orchestrator.name)
            
            runner = Runner(
                agent=orchestrator,
                app_name=app_name,
                session_service=self._session_service,
            )
            self._workflow_runners[workflow_id] = runner
            logger.info("[VOICE GATEWAY] Runner initialized for workflow %s", workflow_id)
        
        return self._workflow_runners[workflow_id]
    
    async def create(self, workflow_id: str = None):
        logger.info("[VOICE GATEWAY] Gateway initialized for organization: %s", self.organization_id)
    
    async def cleanup(self):
        self._workflow_runners.clear()
    
    async def transcribe_audio(self, audio_bytes: bytes, filename: str = "audio.webm") -> Optional[str]:
        try:
            if not audio_bytes:
                return None
                
            audio_file = BytesIO(audio_bytes)
            audio_file.name = filename
            
            transcript = self.client.audio.transcriptions.create(
                model=self.stt_model,
                file=audio_file,
                language=self.language
            )
            
            if hasattr(transcript, 'text'):
                text = transcript.text
            elif isinstance(transcript, dict):
                text = transcript.get('text')
            elif isinstance(transcript, str):
                text = transcript
            else:
                return None
            
            return text.strip() if text and text.strip() else None
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            return None
    
    async def text_to_speech(self, text: str, voice: Optional[str] = None, output_format: str = "mp3") -> Optional[bytes]:
        try:
            response = self.client.audio.speech.create(
                model=self.tts_model,
                voice=voice or self.default_voice,
                input=text,
                response_format=output_format
            )
            return b"".join(response.iter_bytes())
        except Exception as e:
            logger.error(f"Error converting text to speech: {e}")
            return None
    
    def _build_content_parts(self, message: str, files: Optional[List[dict]] = None) -> List[Part]:
        parts = []
        
        if message:
            parts.append(create_part_from_text(message))
        
        if files:
            for file_info in files:
                content = file_info.get("content")
                mime_type = file_info.get("mime_type", "application/octet-stream")
                filename = file_info.get("filename", "file")
                
                if not content:
                    logger.warning(f"Skipping file {filename}: no content")
                    continue
                
                file_bytes = decode_base64_content(content)
                parts.append(create_part_from_bytes(file_bytes, mime_type))
                logger.info(f"Added file to message: {filename} ({mime_type}, {len(file_bytes)} bytes)")
        
        if not parts:
            parts.append(create_part_from_text(""))
        
        return parts
    
    async def _send_message(
        self, 
        message: str, 
        workflow_id: str,
        user_id: str,
        session_id: str,
        files: Optional[List[dict]] = None
    ) -> tuple[str, str]:
        runner = self._get_or_create_runner(workflow_id)
        app_name = _sanitize_app_name(workflow_id)
        
        session = await self._session_service.get_session(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id,
        )
        
        if not session:
            session = await self._session_service.create_session(
                app_name=app_name,
                user_id=user_id,
                session_id=session_id,
            )
        
        parts = self._build_content_parts(message, files)
        user_content = Content(
            role="user",
            parts=parts
        )
        
        response_text = ""
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=user_content,
        ):
            if hasattr(event, 'content') and event.content:
                for part in event.content.parts:
                    if hasattr(part, 'text') and part.text:
                        response_text += part.text
        
        return response_text or "Sorry, I couldn't complete your request.", session_id
    
    async def process_voice_message(
        self, 
        audio_bytes: bytes, 
        workflow_id: str,
        user_id: str,
        session_id: Optional[str] = None,
        voice: Optional[str] = None,
    ) -> tuple[Optional[str], Optional[str], Optional[bytes]]:
        if not workflow_id or not user_id:
            raise ValueError("workflow_id and user_id are required")
        
        transcribed_text = await self.transcribe_audio(audio_bytes)
        if not transcribed_text:
            return None, None, None
        
        effective_session_id = session_id or f"{workflow_id}_{user_id}"
        
        try:
            response, effective_session_id = await self._send_message(
                message=transcribed_text,
                workflow_id=workflow_id,
                user_id=user_id,
                session_id=effective_session_id,
            )
        except Exception as e:
            logger.error(f"Error communicating with orchestrator: {e}")
            return transcribed_text, None, None
        
        audio_response = await self.text_to_speech(response, voice)
        return transcribed_text, response, audio_response
    
    async def process_text_message_stream(
        self,
        message: str,
        workflow_id: str,
        user_id: str,
        session_id: Optional[str] = None,
        files: Optional[List[dict]] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        if not workflow_id or not user_id:
            yield {"content": "Sorry, I couldn't process your request. Please try again.", "done": True, "session_id": None}
            return
        
        effective_session_id = session_id or f"{workflow_id}_{user_id}"
        app_name = _sanitize_app_name(workflow_id)
        
        try:
            runner = self._get_or_create_runner(workflow_id)
            
            session = await self._session_service.get_session(
                app_name=app_name,
                user_id=user_id,
                session_id=effective_session_id,
            )
            
            if not session:
                session = await self._session_service.create_session(
                    app_name=app_name,
                    user_id=user_id,
                    session_id=effective_session_id,
                )
                logger.info("[VOICE GATEWAY] Created new session: app=%s, user=%s, session=%s", 
                           app_name, user_id, effective_session_id)
            else:
                logger.info("[VOICE GATEWAY] Resuming session: app=%s, user=%s, session=%s, events=%d", 
                           app_name, user_id, effective_session_id, len(session.events) if session.events else 0)
            
            parts = self._build_content_parts(message, files)
            user_content = Content(
                role="user",
                parts=parts
            )
            
            if files:
                logger.info(f"Processing multimodal message with {len(files)} file(s)")
            
            has_content = False
            logger.info("[VOICE GATEWAY] Starting runner.run_async for user=%s, session=%s", user_id, effective_session_id)
            
            async for event in runner.run_async(
                user_id=user_id,
                session_id=effective_session_id,
                new_message=user_content,
            ):
                event_type = type(event).__name__
                logger.info("[VOICE GATEWAY] Event: %s, has_content=%s", event_type, hasattr(event, 'content') and event.content is not None)
                
                if hasattr(event, 'content') and event.content:
                    if hasattr(event.content, 'parts') and event.content.parts:
                        for part in event.content.parts:
                            if hasattr(part, 'text') and part.text:
                                has_content = True
                                logger.info("[VOICE GATEWAY] Yielding text: %s...", part.text[:50] if len(part.text) > 50 else part.text)
                                yield {"content": part.text, "done": False, "session_id": None}
            
            logger.info("[VOICE GATEWAY] Runner completed. has_content=%s", has_content)
            
            if not has_content:
                yield {"content": "I'm sorry, I couldn't generate a response. Please try again.", "done": False, "session_id": None}
            
            yield {"content": "", "done": True, "session_id": effective_session_id}
            
        except LLMConfigNotFoundError as e:
            logger.error(f"LLM config not found: {e}")
            yield {"content": "Please configure LLM settings to use this chatbot.", "done": True, "session_id": effective_session_id}
        except Exception as e:
            logger.error(f"Error processing request: {e}", exc_info=True)
            yield {"content": "Sorry, something went wrong. Please try again.", "done": True, "session_id": effective_session_id}
