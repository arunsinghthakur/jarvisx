from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class KnowledgeBaseEntryType(str, Enum):
    DOCUMENT = "document"
    SNIPPET = "snippet"
    URL = "url"


class SnippetCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)
    metadata: Optional[Dict[str, Any]] = None


class SnippetUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    content: Optional[str] = Field(None, min_length=1)
    metadata: Optional[Dict[str, Any]] = None


class KnowledgeBaseEntryResponse(BaseModel):
    id: str
    organization_id: str
    entry_type: KnowledgeBaseEntryType
    title: str
    source_filename: Optional[str] = None
    content_preview: Optional[str] = None
    chunk_count: int
    file_size: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = Field(default=None, validation_alias="entry_metadata")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True


class KnowledgeBaseEntriesResponse(BaseModel):
    entries: List[KnowledgeBaseEntryResponse]
    total: int


class SearchQuery(BaseModel):
    query: str = Field(..., min_length=1)
    limit: int = Field(default=5, ge=1, le=20)
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0)


class SearchResult(BaseModel):
    entry_id: str
    entry_title: str
    entry_type: str
    chunk_content: str
    chunk_index: int
    similarity_score: float
    metadata: Optional[Dict[str, Any]] = None


class SearchResponse(BaseModel):
    query: str
    results: List[SearchResult]
    total_results: int


class KnowledgeBaseStats(BaseModel):
    total_entries: int
    total_chunks: int
    entries_by_type: Dict[str, int]
    total_tokens: int

