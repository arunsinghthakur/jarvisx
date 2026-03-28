import asyncio
import base64
import json
import logging
import struct
import wave
from io import BytesIO
from typing import Optional

from starlette.websockets import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class TextChunker:
    PHRASE_DELIMITERS = {',', '.', '!', '?', ':', ';', '\n'}
    MAX_CHUNK_CHARS = 80
    MIN_CHUNK_CHARS = 15

    def __init__(self):
        self._buffer = ""

    def feed(self, text: str) -> list[str]:
        self._buffer += text
        chunks = []

        while len(self._buffer) >= self.MIN_CHUNK_CHARS:
            best_split = -1

            for i, ch in enumerate(self._buffer):
                if i < self.MIN_CHUNK_CHARS:
                    continue
                if ch in self.PHRASE_DELIMITERS:
                    best_split = i + 1
                    break

            if best_split == -1 and len(self._buffer) >= self.MAX_CHUNK_CHARS:
                space_pos = self._buffer.rfind(' ', self.MIN_CHUNK_CHARS, self.MAX_CHUNK_CHARS)
                best_split = space_pos + 1 if space_pos > 0 else self.MAX_CHUNK_CHARS

            if best_split > 0:
                chunk = self._buffer[:best_split].strip()
                self._buffer = self._buffer[best_split:]
                if chunk:
                    chunks.append(chunk)
            else:
                break

        return chunks

    def flush(self) -> Optional[str]:
        remaining = self._buffer.strip()
        self._buffer = ""
        return remaining if remaining else None


def _pcm_to_wav(pcm_bytes: bytes, sample_rate: int = 16000, channels: int = 1, sample_width: int = 2) -> bytes:
    buf = BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_bytes)
    return buf.getvalue()


async def ws_voice_handler(websocket: WebSocket):
    await websocket.accept()

    audio_buffer = bytearray()
    config = {}
    gateway_service = None
    tts_cancelled = False
    tts_tasks: list[asyncio.Task] = []
    audio_sequence = 0
    audio_send_lock = asyncio.Lock()

    try:
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)
            msg_type = msg.get("type", "")

            if msg_type == "config":
                org_id = msg.get("organization_id")
                if not org_id:
                    await _send(websocket, {"type": "error", "message": "organization_id required in config"})
                    continue

                config = {
                    "organization_id": org_id,
                    "workflow_id": msg.get("workflow_id"),
                    "user_id": msg.get("user_id"),
                    "session_id": msg.get("session_id"),
                    "voice": msg.get("voice", "alloy"),
                }

                from services.gateways.voice.src.service import VoiceGatewayService
                try:
                    gateway_service = VoiceGatewayService(organization_id=org_id)
                    await gateway_service.create()
                    await _send(websocket, {"type": "ready"})
                except Exception as e:
                    await _send(websocket, {"type": "error", "message": str(e)})

            elif msg_type == "audio_chunk":
                pcm_b64 = msg.get("data", "")
                if pcm_b64:
                    audio_buffer.extend(base64.b64decode(pcm_b64))

            elif msg_type == "speech_end":
                if not gateway_service or not config.get("workflow_id"):
                    await _send(websocket, {"type": "error", "message": "Not configured"})
                    continue

                if len(audio_buffer) < 1600:
                    audio_buffer.clear()
                    continue

                pcm_bytes = bytes(audio_buffer)
                audio_buffer.clear()

                wav_bytes = _pcm_to_wav(pcm_bytes)
                transcript = await gateway_service.gateway.transcribe_audio(wav_bytes, "audio.wav")

                if not transcript:
                    await _send(websocket, {"type": "transcript", "text": "", "final": True})
                    continue

                await _send(websocket, {"type": "transcript", "text": transcript, "final": True})

                tts_cancelled = False
                audio_sequence = 0
                for t in tts_tasks:
                    t.cancel()
                tts_tasks.clear()

                await _process_llm_and_tts(
                    websocket, gateway_service, config, transcript,
                    tts_tasks, lambda: tts_cancelled, audio_send_lock,
                )

            elif msg_type == "text_message":
                if not gateway_service or not config.get("workflow_id"):
                    await _send(websocket, {"type": "error", "message": "Not configured"})
                    continue

                content = msg.get("content", "")
                if not content:
                    continue

                if msg.get("session_id"):
                    config["session_id"] = msg["session_id"]

                tts_cancelled = False
                for t in tts_tasks:
                    t.cancel()
                tts_tasks.clear()

                await _process_llm_and_tts(
                    websocket, gateway_service, config, content,
                    tts_tasks, lambda: tts_cancelled, audio_send_lock,
                )

            elif msg_type == "stop_audio":
                tts_cancelled = True
                for t in tts_tasks:
                    t.cancel()
                tts_tasks.clear()

    except WebSocketDisconnect:
        logger.info("[WS] Client disconnected")
    except Exception as e:
        logger.error(f"[WS] Error: {e}", exc_info=True)
        try:
            await _send(websocket, {"type": "error", "message": str(e)})
        except Exception:
            pass
    finally:
        for t in tts_tasks:
            t.cancel()
        try:
            await websocket.close()
        except Exception:
            pass


async def _process_llm_and_tts(
    websocket: WebSocket,
    service,
    config: dict,
    text: str,
    tts_tasks: list,
    is_cancelled,
    send_lock: asyncio.Lock,
):
    chunker = TextChunker()
    chunk_index = 0
    pending_audio: dict[int, bytes] = {}
    next_to_send = [0]

    async def _tts_and_send(phrase: str, idx: int):
        if is_cancelled():
            return
        try:
            audio_bytes = await service.gateway.text_to_speech(phrase, config.get("voice"))
            if audio_bytes and not is_cancelled():
                pending_audio[idx] = audio_bytes
                async with send_lock:
                    while next_to_send[0] in pending_audio:
                        audio_b64 = base64.b64encode(pending_audio.pop(next_to_send[0])).decode()
                        await _send(websocket, {"type": "audio_chunk", "data": audio_b64, "index": next_to_send[0]})
                        next_to_send[0] += 1
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.debug(f"[WS] TTS chunk {idx} failed: {e}")

    try:
        async for chunk in service.gateway.process_text_message_stream(
            message=text,
            workflow_id=config["workflow_id"],
            user_id=config.get("user_id", "anonymous"),
            session_id=config.get("session_id"),
        ):
            if is_cancelled():
                break

            content = chunk.get("content", "")
            if chunk.get("done"):
                if chunk.get("session_id"):
                    config["session_id"] = chunk["session_id"]
                break

            if content:
                await _send(websocket, {"type": "text_chunk", "content": content})
                phrases = chunker.feed(content)
                for phrase in phrases:
                    idx = chunk_index
                    chunk_index += 1
                    task = asyncio.create_task(_tts_and_send(phrase, idx))
                    tts_tasks.append(task)

        remaining = chunker.flush()
        if remaining and not is_cancelled():
            idx = chunk_index
            chunk_index += 1
            task = asyncio.create_task(_tts_and_send(remaining, idx))
            tts_tasks.append(task)

        if tts_tasks:
            await asyncio.gather(*tts_tasks, return_exceptions=True)

        await _send(websocket, {"type": "text_done", "session_id": config.get("session_id")})
        await _send(websocket, {"type": "audio_done"})

    except Exception as e:
        logger.error(f"[WS] LLM+TTS pipeline error: {e}", exc_info=True)
        await _send(websocket, {"type": "error", "message": str(e)})


async def _send(websocket: WebSocket, data: dict):
    try:
        await websocket.send_text(json.dumps(data))
    except Exception:
        pass
