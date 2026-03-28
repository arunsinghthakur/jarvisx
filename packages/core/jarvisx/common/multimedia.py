import base64
import logging
import mimetypes
from pathlib import Path
from typing import Optional, Union

from google.genai import types

logger = logging.getLogger(__name__)

SUPPORTED_MIME_TYPES = {
    "image/jpeg": "image",
    "image/png": "image",
    "image/gif": "image",
    "image/webp": "image",
    "audio/mpeg": "audio",
    "audio/mp3": "audio",
    "audio/wav": "audio",
    "audio/x-wav": "audio",
    "audio/pcm": "audio",
    "audio/ogg": "audio",
    "video/mp4": "video",
    "video/webm": "video",
    "video/mpeg": "video",
    "application/pdf": "document",
    "text/plain": "text",
    "text/markdown": "text",
    "text/csv": "text",
    "application/json": "text",
    "application/msword": "document",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "document",
    "application/vnd.ms-excel": "document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "document",
}

BINARY_EXTENSIONS = {
    "pdf", "jpg", "jpeg", "png", "gif", "webp", "bmp", "tiff",
    "mp3", "wav", "ogg", "flac", "aac", "m4a",
    "mp4", "webm", "avi", "mov", "mkv",
    "doc", "docx", "xls", "xlsx", "ppt", "pptx",
}

EXTENSION_TO_MIME = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "gif": "image/gif",
    "webp": "image/webp",
    "bmp": "image/bmp",
    "tiff": "image/tiff",
    "pdf": "application/pdf",
    "mp3": "audio/mpeg",
    "wav": "audio/wav",
    "ogg": "audio/ogg",
    "flac": "audio/flac",
    "aac": "audio/aac",
    "m4a": "audio/mp4",
    "mp4": "video/mp4",
    "webm": "video/webm",
    "avi": "video/x-msvideo",
    "mov": "video/quicktime",
    "mkv": "video/x-matroska",
    "doc": "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xls": "application/vnd.ms-excel",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "ppt": "application/vnd.ms-powerpoint",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "txt": "text/plain",
    "md": "text/markdown",
    "csv": "text/csv",
    "json": "application/json",
}


def detect_mime_type(
    file_path: Optional[str] = None,
    content: Optional[bytes] = None,
    filename: Optional[str] = None
) -> str:
    if file_path:
        extension = Path(file_path).suffix.lower().lstrip(".")
        if extension in EXTENSION_TO_MIME:
            return EXTENSION_TO_MIME[extension]
        
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type:
            return mime_type
    
    if filename:
        extension = Path(filename).suffix.lower().lstrip(".")
        if extension in EXTENSION_TO_MIME:
            return EXTENSION_TO_MIME[extension]
    
    if content and len(content) >= 12:
        if content[:4] == b"\x89PNG":
            return "image/png"
        if content[:2] == b"\xff\xd8":
            return "image/jpeg"
        if content[:6] in (b"GIF87a", b"GIF89a"):
            return "image/gif"
        if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
            return "image/webp"
        if content[:4] == b"%PDF":
            return "application/pdf"
        if content[:3] == b"ID3" or content[:2] == b"\xff\xfb":
            return "audio/mpeg"
        if content[:4] == b"RIFF" and content[8:12] == b"WAVE":
            return "audio/wav"
        if content[:4] == b"OggS":
            return "audio/ogg"
        if content[4:8] == b"ftyp":
            subtype = content[8:12]
            if subtype in (b"mp41", b"mp42", b"isom", b"avc1"):
                return "video/mp4"
            if subtype == b"M4A ":
                return "audio/mp4"
        if content[:4] == b"\x1aE\xdf\xa3":
            return "video/webm"
    
    return "application/octet-stream"


def is_binary_extension(extension: str) -> bool:
    return extension.lower().lstrip(".") in BINARY_EXTENSIONS


def get_content_category(mime_type: str) -> str:
    return SUPPORTED_MIME_TYPES.get(mime_type, "unknown")


def decode_base64_content(content: Union[str, bytes]) -> bytes:
    if isinstance(content, bytes):
        return content
    try:
        return base64.b64decode(content)
    except Exception:
        return content.encode("utf-8")


def create_part_from_bytes(data: bytes, mime_type: str) -> types.Part:
    return types.Part.from_bytes(data=data, mime_type=mime_type)


def create_part_from_text(text: str) -> types.Part:
    return types.Part.from_text(text=text)


def create_multimodal_parts(
    input_data: dict,
    text_prompt: Optional[str] = None
) -> list:
    parts = []
    
    if text_prompt:
        parts.append(create_part_from_text(text_prompt))
    
    if input_data.get("is_binary") and input_data.get("content"):
        content = input_data["content"]
        mime_type = input_data.get("mime_type", "application/octet-stream")
        
        file_bytes = decode_base64_content(content)
        parts.append(create_part_from_bytes(file_bytes, mime_type))
        
        logger.info(f"Added binary content part: {mime_type}, {len(file_bytes)} bytes")
    
    files = input_data.get("files", [])
    for file_info in files:
        content = file_info.get("content")
        mime_type = file_info.get("mime_type", "application/octet-stream")
        filename = file_info.get("filename", "file")
        
        if not content:
            logger.warning(f"Skipping file {filename}: no content")
            continue
        
        file_bytes = decode_base64_content(content)
        parts.append(create_part_from_bytes(file_bytes, mime_type))
        
        logger.info(f"Added file part: {filename} ({mime_type}, {len(file_bytes)} bytes)")
    
    if not parts:
        response_text = input_data.get("response") or input_data.get("content")
        if response_text and isinstance(response_text, str):
            parts.append(create_part_from_text(response_text))
        else:
            parts.append(create_part_from_text(str(input_data)))
    
    return parts


def extract_text_from_pdf(pdf_bytes: bytes) -> Optional[str]:
    try:
        from pypdf import PdfReader
        from io import BytesIO
        
        reader = PdfReader(BytesIO(pdf_bytes))
        text_parts = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)
        
        return "\n\n".join(text_parts) if text_parts else None
    except ImportError:
        logger.warning("pypdf not installed, cannot extract PDF text")
        return None
    except Exception as e:
        logger.error(f"Failed to extract PDF text: {e}")
        return None


def extract_text_from_docx(docx_bytes: bytes) -> Optional[str]:
    try:
        from docx import Document
        from io import BytesIO
        
        doc = Document(BytesIO(docx_bytes))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        
        return "\n\n".join(paragraphs) if paragraphs else None
    except ImportError:
        logger.warning("python-docx not installed, cannot extract DOCX text")
        return None
    except Exception as e:
        logger.error(f"Failed to extract DOCX text: {e}")
        return None
