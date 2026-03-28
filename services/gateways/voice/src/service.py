import logging
from typing import Optional

from services.gateways.voice.src.gateway import VoiceGateway

logger = logging.getLogger(__name__)


class VoiceGatewayService:
    def __init__(self, organization_id: str):
        if not organization_id:
            raise ValueError("organization_id is required to create VoiceGatewayService")
        self.gateway = VoiceGateway(organization_id=organization_id)
    
    async def create(self):
        await self.gateway.create()
    
    async def cleanup(self):
        await self.gateway.cleanup()
    
    async def transcribe_audio_bytes(self, audio_bytes: bytes, filename: str = "audio.webm") -> str:
        return await self.gateway.transcribe_audio(audio_bytes, filename)
    
    async def text_to_speech(self, text: str, voice: str = None) -> bytes:
        audio_bytes = await self.gateway.text_to_speech(text, voice)
        if not audio_bytes:
            raise ValueError("Failed to convert text to speech")
        return audio_bytes
    
    async def process_voice_message(
        self, 
        audio_bytes: bytes, 
        workflow_id: str,
        user_id: str,
        session_id: str = None,
        voice: str = None,
    ) -> tuple[str, str, bytes]:
        transcribed, response, audio = await self.gateway.process_voice_message(
            audio_bytes=audio_bytes,
            workflow_id=workflow_id,
            user_id=user_id,
            session_id=session_id,
            voice=voice,
        )
        if transcribed is None:
            raise ValueError("Failed to transcribe audio")
        if response is None:
            raise ValueError("Failed to get response from Central Orchestrator")
        if audio is None:
            raise ValueError("Failed to convert response to speech")
        return transcribed, response, audio
    
    async def process_text_message_stream(
        self,
        message: str,
        workflow_id: str,
        user_id: str,
        session_id: str = None,
        files: list = None
    ):
        async for chunk in self.gateway.process_text_message_stream(
            message=message,
            workflow_id=workflow_id,
            user_id=user_id,
            session_id=session_id,
            files=files
        ):
            yield chunk
