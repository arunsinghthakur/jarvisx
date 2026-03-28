import logging
import os
import json
import csv
import base64
from io import StringIO
from pathlib import Path
from typing import Optional

from jarvisx.workflows.nodes.base import BaseNodeExecutor
from jarvisx.config.configs import WORKSPACE_BASE_PATH
from jarvisx.common.multimedia import (
    is_binary_extension,
    detect_mime_type,
    get_content_category,
    extract_text_from_pdf,
    extract_text_from_docx,
)

logger = logging.getLogger(__name__)


class FileReadNodeExecutor(BaseNodeExecutor):
    SUPPORTED_EXTENSIONS = {'txt', 'json', 'md', 'csv', 'log', 'xml', 'yaml', 'yml'}
    BINARY_EXTENSIONS = {
        'pdf', 'jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'tiff',
        'mp3', 'wav', 'ogg', 'flac', 'aac', 'm4a',
        'mp4', 'webm', 'avi', 'mov', 'mkv',
        'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
    }
    MAX_FILE_SIZE = 50 * 1024 * 1024

    async def execute(
        self,
        config: dict,
        input_data: dict,
        node_data: dict
    ) -> dict:
        file_path_config = config.get("file_path", "")
        encoding = config.get("encoding", "utf-8")
        parse_format = config.get("parse_format", "auto")
        extract_text = config.get("extract_text", True)
        
        if not file_path_config:
            return {
                "success": False,
                "error": "No file path specified",
                "content": None
            }
        
        base_path = Path(WORKSPACE_BASE_PATH)
        file_path = base_path / file_path_config
        file_path = file_path.resolve()
        
        if not str(file_path).startswith(str(base_path.resolve())):
            return {
                "success": False,
                "error": "Invalid file path - cannot access files outside workspace",
                "content": None
            }
        
        if not file_path.exists():
            return {
                "success": False,
                "error": f"File not found: {file_path_config}",
                "content": None
            }
        
        if not file_path.is_file():
            return {
                "success": False,
                "error": f"Path is not a file: {file_path_config}",
                "content": None
            }
        
        file_size = file_path.stat().st_size
        if file_size > self.MAX_FILE_SIZE:
            return {
                "success": False,
                "error": f"File too large ({file_size} bytes). Maximum size is {self.MAX_FILE_SIZE} bytes",
                "content": None
            }
        
        extension = file_path.suffix.lower().lstrip('.')
        
        if extension in self.BINARY_EXTENSIONS or is_binary_extension(extension):
            return await self._read_binary_file(
                file_path, file_path_config, extension, file_size, extract_text
            )
        
        try:
            with open(file_path, "r", encoding=encoding) as f:
                raw_content = f.read()
            
            if parse_format == "auto":
                parse_format = extension
            
            parsed_content = self._parse_content(raw_content, parse_format)
            mime_type = detect_mime_type(file_path=str(file_path))
            
            logger.info(f"[FileReadNode] Successfully read text file: {file_path_config}")
            
            return {
                "success": True,
                "content": raw_content,
                "parsed_content": parsed_content,
                "file_path": file_path_config,
                "filename": file_path.name,
                "extension": extension,
                "size_bytes": file_size,
                "encoding": encoding,
                "format": parse_format,
                "mime_type": mime_type,
                "is_binary": False,
                "content_category": "text",
                "response": raw_content
            }
            
        except UnicodeDecodeError:
            logger.info(f"[FileReadNode] Text decode failed, trying binary read: {file_path_config}")
            return await self._read_binary_file(
                file_path, file_path_config, extension, file_size, extract_text
            )
        except Exception as e:
            logger.error(f"[FileReadNode] Failed to read file: {e}")
            return {
                "success": False,
                "error": str(e),
                "content": None
            }
    
    async def _read_binary_file(
        self,
        file_path: Path,
        file_path_config: str,
        extension: str,
        file_size: int,
        extract_text: bool = True
    ) -> dict:
        try:
            with open(file_path, "rb") as f:
                raw_bytes = f.read()
            
            content_base64 = base64.b64encode(raw_bytes).decode("utf-8")
            mime_type = detect_mime_type(file_path=str(file_path), content=raw_bytes)
            content_category = get_content_category(mime_type)
            
            extracted_text = None
            if extract_text:
                if extension == "pdf" or mime_type == "application/pdf":
                    extracted_text = extract_text_from_pdf(raw_bytes)
                elif extension in ("docx",) or "wordprocessingml" in mime_type:
                    extracted_text = extract_text_from_docx(raw_bytes)
            
            logger.info(f"[FileReadNode] Successfully read binary file: {file_path_config} ({mime_type})")
            
            return {
                "success": True,
                "content": content_base64,
                "file_path": file_path_config,
                "filename": file_path.name,
                "extension": extension,
                "size_bytes": file_size,
                "mime_type": mime_type,
                "is_binary": True,
                "content_category": content_category,
                "extracted_text": extracted_text,
                "response": extracted_text if extracted_text else f"[Binary file: {file_path.name}]"
            }
            
        except Exception as e:
            logger.error(f"[FileReadNode] Failed to read binary file: {e}")
            return {
                "success": False,
                "error": str(e),
                "content": None
            }
    
    def _parse_content(self, content: str, format: str) -> Optional[any]:
        try:
            if format == "json":
                return json.loads(content)
            
            elif format == "csv":
                reader = csv.DictReader(StringIO(content))
                return list(reader)
            
            elif format in ("yaml", "yml"):
                try:
                    import yaml
                    return yaml.safe_load(content)
                except ImportError:
                    logger.warning("[FileReadNode] PyYAML not installed, returning raw content")
                    return content
            
            else:
                return content
                
        except Exception as e:
            logger.warning(f"[FileReadNode] Failed to parse as {format}: {e}")
            return content
