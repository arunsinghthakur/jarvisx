import json
import re
import logging
from typing import TYPE_CHECKING
from sqlalchemy import String, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, Session as DBSession
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import TypeDecorator
from typing_extensions import override

from google.adk.memory.base_memory_service import BaseMemoryService, SearchMemoryResponse
from google.adk.memory.memory_entry import MemoryEntry
from google.adk.memory import _utils
from jarvisx.a2a.base_storage import Base, BaseDatabaseStorageService

if TYPE_CHECKING:
    from google.adk.sessions.session import Session
    from google.adk.events.event import Event

logger = logging.getLogger(__name__)

DEFAULT_MAX_KEY_LENGTH = 128


class DynamicJSON(TypeDecorator):
    impl = Text
    
    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB)
        return dialect.type_descriptor(Text)
    
    def process_bind_param(self, value, dialect):
        if value is not None:
            if dialect.name == "postgresql":
                return value
            return json.dumps(value)
        return value
    
    def process_result_value(self, value, dialect):
        if value is not None:
            if dialect.name == "postgresql":
                return value
            return json.loads(value)
        return value


class StorageMemoryEvent(Base):
    
    __tablename__ = "memory_events"
    
    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    app_name: Mapped[str] = mapped_column(String(DEFAULT_MAX_KEY_LENGTH), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(DEFAULT_MAX_KEY_LENGTH), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(DEFAULT_MAX_KEY_LENGTH), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(DEFAULT_MAX_KEY_LENGTH), primary_key=True, default="default")
    workspace_id: Mapped[str] = mapped_column(String(DEFAULT_MAX_KEY_LENGTH), primary_key=True, default="default")
    
    author: Mapped[str] = mapped_column(String(255))
    content: Mapped[dict] = mapped_column(DynamicJSON, nullable=True)
    timestamp: Mapped[DateTime] = mapped_column(DateTime, default=func.now())
    
    text_content: Mapped[str] = mapped_column(Text, nullable=True)


def _extract_words_lower(text: str) -> set[str]:
    return set([word.lower() for word in re.findall(r'[A-Za-z]+', text)])


class DatabaseMemoryService(BaseDatabaseStorageService, BaseMemoryService):
    
    def __init__(self, db_url: str, schema: str = "jarvisx", workspace_id: str = "default", tenant_id: str = "default"):
        BaseDatabaseStorageService.__init__(self, db_url, schema, workspace_id, tenant_id)
        Base.metadata.schema = schema
        Base.metadata.create_all(self.engine)
    
    @override
    async def add_session_to_memory(self, session: "Session"):
        db: DBSession = self.SessionLocal()
        try:
            user_key = f"{session.app_name}/{session.user_id}"
            
            for event in session.events:
                if not event.content or not event.content.parts:
                    continue
                
                text_parts = []
                for part in event.content.parts:
                    if hasattr(part, 'text') and part.text:
                        text_parts.append(part.text)
                
                text_content = ' '.join(text_parts) if text_parts else None
                
                content_dict = None
                if event.content:
                    content_dict = {
                        "parts": [
                            {
                                "text": part.text if hasattr(part, 'text') else None,
                                "inline_data": part.inline_data.model_dump() if hasattr(part, 'inline_data') and part.inline_data else None,
                            }
                            for part in event.content.parts
                        ]
                    }
                
                existing = db.query(StorageMemoryEvent).filter_by(
                    id=event.id,
                    app_name=session.app_name,
                    user_id=session.user_id,
                    session_id=session.id,
                    tenant_id=self.tenant_id,
                    workspace_id=self.workspace_id
                ).first()
                
                if existing:
                    existing.author = event.author
                    existing.content = content_dict
                    existing.text_content = text_content
                    if hasattr(event, 'timestamp') and event.timestamp:
                        existing.timestamp = event.timestamp
                else:
                    memory_event = StorageMemoryEvent(
                        id=event.id,
                        app_name=session.app_name,
                        user_id=session.user_id,
                        session_id=session.id,
                        tenant_id=self.tenant_id,
                        workspace_id=self.workspace_id,
                        author=event.author,
                        content=content_dict,
                        text_content=text_content,
                        timestamp=event.timestamp if hasattr(event, 'timestamp') and event.timestamp else None
                    )
                    db.add(memory_event)
            
            db.commit()
            logger.debug(f"Added {len([e for e in session.events if e.content and e.content.parts])} events to memory for session {session.id}, tenant {self.tenant_id}, workspace {self.workspace_id}")
        except Exception as e:
            db.rollback()
            logger.error(f"Error adding session to memory: {e}", exc_info=True)
            raise
        finally:
            db.close()
    
    @override
    async def search_memory(
        self, *, app_name: str, user_id: str, query: str
    ) -> SearchMemoryResponse:
        db: DBSession = self.SessionLocal()
        try:
            words_in_query = _extract_words_lower(query)
            response = SearchMemoryResponse()
            
            events = db.query(StorageMemoryEvent).filter_by(
                app_name=app_name,
                user_id=user_id,
                tenant_id=self.tenant_id,
                workspace_id=self.workspace_id
            ).all()
            
            for event in events:
                if not event.text_content:
                    continue
                
                words_in_event = _extract_words_lower(event.text_content)
                if not words_in_event:
                    continue
                
                if any(query_word in words_in_event for query_word in words_in_query):
                    content = None
                    if event.content and event.content.get("parts"):
                        from google.genai import types
                        parts = []
                        for part_dict in event.content["parts"]:
                            if part_dict.get("text"):
                                parts.append(types.Part.from_text(part_dict["text"]))
                            elif part_dict.get("inline_data"):
                                parts.append(types.Part.from_inline_data(**part_dict["inline_data"]))
                        
                        if parts:
                            content = types.Content(role="model", parts=parts)
                    
                    if content:
                        response.memories.append(
                            MemoryEntry(
                                content=content,
                                author=event.author,
                                timestamp=_utils.format_timestamp(event.timestamp) if event.timestamp else "",
                            )
                        )
            
            logger.debug(f"Found {len(response.memories)} matching memories for query: {query[:50]}")
            return response
        except Exception as e:
            logger.error(f"Error searching memory: {e}", exc_info=True)
            return SearchMemoryResponse()
        finally:
            db.close()
