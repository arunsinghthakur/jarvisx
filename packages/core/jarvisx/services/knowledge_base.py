import uuid
import logging
import tiktoken
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from datetime import datetime

from jarvisx.database.models import (
    KnowledgeBaseEntry, 
    KnowledgeBaseChunk,
    KnowledgeBaseEntryType,
    Organization
)
from jarvisx.a2a.llm_config import get_embedding_config, LLMConfigNotFoundError

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSION = 1536
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

_embedding_clients: Dict[str, Any] = {}


def get_embedding_client(organization_id: str):
    if not organization_id:
        raise LLMConfigNotFoundError(
            "Organization ID is required for embedding operations. "
            "Please provide a valid organization context."
        )
    
    if organization_id in _embedding_clients:
        return _embedding_clients[organization_id]
    
    from openai import OpenAI
    
    embedding_config = get_embedding_config(organization_id)
    
    client = OpenAI(
        api_key=embedding_config.api_key,
        base_url=embedding_config.api_base_url,
    )
    
    _embedding_clients[organization_id] = client
    logger.info("[KNOWLEDGE BASE] Created embedding client for org %s using config: %s", 
                organization_id, embedding_config.name)
    return client


def get_embedding_model(organization_id: str) -> str:
    try:
        embedding_config = get_embedding_config(organization_id)
        if embedding_config.additional_config and "embedding_model" in embedding_config.additional_config:
            return embedding_config.additional_config["embedding_model"]
        return EMBEDDING_MODEL
    except LLMConfigNotFoundError:
        return EMBEDDING_MODEL


def count_tokens(text: str, model: str = "cl100k_base") -> int:
    try:
        encoding = tiktoken.get_encoding(model)
        return len(encoding.encode(text))
    except Exception:
        return len(text.split())


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    try:
        encoding = tiktoken.get_encoding("cl100k_base")
        tokens = encoding.encode(text)
    except Exception:
        words = text.split()
        chunks = []
        for i in range(0, len(words), chunk_size - overlap):
            chunk = " ".join(words[i:i + chunk_size])
            if chunk:
                chunks.append(chunk)
        return chunks if chunks else [text]
    
    chunks = []
    start = 0
    while start < len(tokens):
        end = start + chunk_size
        chunk_tokens = tokens[start:end]
        chunk_text = encoding.decode(chunk_tokens)
        if chunk_text.strip():
            chunks.append(chunk_text)
        start = end - overlap if end < len(tokens) else len(tokens)
    
    return chunks if chunks else [text]


def get_embedding(text: str, organization_id: str) -> Optional[List[float]]:
    try:
        client = get_embedding_client(organization_id)
        model = get_embedding_model(organization_id)
        response = client.embeddings.create(
            model=model,
            input=text,
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Error getting embedding: {e}")
        return None


def get_embeddings_batch(texts: List[str], organization_id: str) -> List[Optional[List[float]]]:
    if not texts:
        return []
    try:
        client = get_embedding_client(organization_id)
        model = get_embedding_model(organization_id)
        response = client.embeddings.create(
            model=model,
            input=texts,
        )
        embeddings = [None] * len(texts)
        for item in response.data:
            embeddings[item.index] = item.embedding
        return embeddings
    except Exception as e:
        logger.error(f"Error getting batch embeddings: {e}")
        return [None] * len(texts)


class KnowledgeBaseService:
    def __init__(self, db: Session):
        self.db = db
    
    def _verify_organization_access(self, organization_id: str) -> Organization:
        org = self.db.query(Organization).filter(Organization.id == organization_id).first()
        if not org:
            raise ValueError(f"Organization {organization_id} not found")
        return org
    
    def create_snippet(
        self, 
        organization_id: str, 
        title: str, 
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> KnowledgeBaseEntry:
        self._verify_organization_access(organization_id)
        
        entry_id = str(uuid.uuid4())
        content_preview = content[:500] if len(content) > 500 else content
        
        entry = KnowledgeBaseEntry(
            id=entry_id,
            organization_id=organization_id,
            entry_type=KnowledgeBaseEntryType.SNIPPET.value,
            title=title,
            content_preview=content_preview,
            chunk_count=0,
            metadata=metadata,
        )
        self.db.add(entry)
        self.db.flush()
        
        chunks = chunk_text(content)
        embeddings = get_embeddings_batch(chunks, organization_id)
        
        for i, (chunk_content, embedding) in enumerate(zip(chunks, embeddings)):
            chunk = KnowledgeBaseChunk(
                id=str(uuid.uuid4()),
                entry_id=entry_id,
                organization_id=organization_id,
                chunk_index=i,
                content=chunk_content,
                token_count=count_tokens(chunk_content),
                embedding=embedding,
                metadata={"source": "snippet"},
            )
            self.db.add(chunk)
        
        entry.chunk_count = len(chunks)
        self.db.commit()
        self.db.refresh(entry)
        return entry
    
    def create_document_entry(
        self,
        organization_id: str,
        title: str,
        filename: str,
        content: str,
        file_size: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> KnowledgeBaseEntry:
        self._verify_organization_access(organization_id)
        
        entry_id = str(uuid.uuid4())
        content_preview = content[:500] if len(content) > 500 else content
        
        entry = KnowledgeBaseEntry(
            id=entry_id,
            organization_id=organization_id,
            entry_type=KnowledgeBaseEntryType.DOCUMENT.value,
            title=title,
            source_filename=filename,
            content_preview=content_preview,
            file_size=file_size,
            chunk_count=0,
            metadata=metadata,
        )
        self.db.add(entry)
        self.db.flush()
        
        chunks = chunk_text(content)
        embeddings = get_embeddings_batch(chunks, organization_id)
        
        for i, (chunk_content, embedding) in enumerate(zip(chunks, embeddings)):
            chunk = KnowledgeBaseChunk(
                id=str(uuid.uuid4()),
                entry_id=entry_id,
                organization_id=organization_id,
                chunk_index=i,
                content=chunk_content,
                token_count=count_tokens(chunk_content),
                embedding=embedding,
                metadata={"source": "document", "filename": filename},
            )
            self.db.add(chunk)
        
        entry.chunk_count = len(chunks)
        self.db.commit()
        self.db.refresh(entry)
        return entry
    
    def update_snippet(
        self,
        organization_id: str,
        entry_id: str,
        title: Optional[str] = None,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> KnowledgeBaseEntry:
        entry = self.db.query(KnowledgeBaseEntry).filter(
            KnowledgeBaseEntry.id == entry_id,
            KnowledgeBaseEntry.organization_id == organization_id,
            KnowledgeBaseEntry.entry_type == KnowledgeBaseEntryType.SNIPPET.value
        ).first()
        
        if not entry:
            raise ValueError(f"Snippet {entry_id} not found")
        
        if title:
            entry.title = title
        
        if metadata is not None:
            entry.entry_metadata = metadata
        
        if content:
            self.db.query(KnowledgeBaseChunk).filter(
                KnowledgeBaseChunk.entry_id == entry_id
            ).delete()
            
            entry.content_preview = content[:500] if len(content) > 500 else content
            
            chunks = chunk_text(content)
            embeddings = get_embeddings_batch(chunks, organization_id)
            
            for i, (chunk_content, embedding) in enumerate(zip(chunks, embeddings)):
                chunk = KnowledgeBaseChunk(
                    id=str(uuid.uuid4()),
                    entry_id=entry_id,
                    organization_id=organization_id,
                    chunk_index=i,
                    content=chunk_content,
                    token_count=count_tokens(chunk_content),
                    embedding=embedding,
                    metadata={"source": "snippet"},
                )
                self.db.add(chunk)
            
            entry.chunk_count = len(chunks)
        
        entry.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(entry)
        return entry
    
    def delete_entry(self, organization_id: str, entry_id: str) -> bool:
        entry = self.db.query(KnowledgeBaseEntry).filter(
            KnowledgeBaseEntry.id == entry_id,
            KnowledgeBaseEntry.organization_id == organization_id
        ).first()
        
        if not entry:
            return False
        
        self.db.delete(entry)
        self.db.commit()
        return True
    
    def get_entry(self, organization_id: str, entry_id: str) -> Optional[KnowledgeBaseEntry]:
        return self.db.query(KnowledgeBaseEntry).filter(
            KnowledgeBaseEntry.id == entry_id,
            KnowledgeBaseEntry.organization_id == organization_id
        ).first()
    
    def list_entries(
        self, 
        organization_id: str,
        entry_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[List[KnowledgeBaseEntry], int]:
        query = self.db.query(KnowledgeBaseEntry).filter(
            KnowledgeBaseEntry.organization_id == organization_id
        )
        
        if entry_type:
            query = query.filter(KnowledgeBaseEntry.entry_type == entry_type)
        
        total = query.count()
        entries = query.order_by(KnowledgeBaseEntry.created_at.desc()).offset(skip).limit(limit).all()
        
        return entries, total
    
    def search(
        self,
        organization_id: str,
        query: str,
        limit: int = 5,
        similarity_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        query_embedding = get_embedding(query, organization_id)
        if not query_embedding:
            return []
        
        embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"
        
        sql = text("""
            SELECT 
                c.id as chunk_id,
                c.entry_id,
                c.content,
                c.chunk_index,
                c.metadata as chunk_metadata,
                e.title as entry_title,
                e.entry_type,
                e.metadata as entry_metadata,
                1 - (c.embedding <=> :embedding::vector) as similarity
            FROM knowledge_base_chunks c
            JOIN knowledge_base_entries e ON c.entry_id = e.id
            WHERE c.organization_id = :organization_id
                AND c.embedding IS NOT NULL
                AND 1 - (c.embedding <=> :embedding::vector) >= :threshold
            ORDER BY c.embedding <=> :embedding::vector
            LIMIT :limit
        """)
        
        result = self.db.execute(sql, {
            "organization_id": organization_id,
            "embedding": embedding_str,
            "threshold": similarity_threshold,
            "limit": limit
        })
        
        results = []
        for row in result:
            results.append({
                "entry_id": row.entry_id,
                "entry_title": row.entry_title,
                "entry_type": row.entry_type,
                "chunk_content": row.content,
                "chunk_index": row.chunk_index,
                "similarity_score": float(row.similarity),
                "metadata": row.chunk_metadata or row.entry_metadata,
            })
        
        return results
    
    def get_stats(self, organization_id: str) -> Dict[str, Any]:
        entries_count = self.db.query(func.count(KnowledgeBaseEntry.id)).filter(
            KnowledgeBaseEntry.organization_id == organization_id
        ).scalar() or 0
        
        chunks_count = self.db.query(func.count(KnowledgeBaseChunk.id)).filter(
            KnowledgeBaseChunk.organization_id == organization_id
        ).scalar() or 0
        
        total_tokens = self.db.query(func.sum(KnowledgeBaseChunk.token_count)).filter(
            KnowledgeBaseChunk.organization_id == organization_id
        ).scalar() or 0
        
        entries_by_type_result = self.db.query(
            KnowledgeBaseEntry.entry_type,
            func.count(KnowledgeBaseEntry.id)
        ).filter(
            KnowledgeBaseEntry.organization_id == organization_id
        ).group_by(KnowledgeBaseEntry.entry_type).all()
        
        entries_by_type = {row[0]: row[1] for row in entries_by_type_result}
        
        return {
            "total_entries": entries_count,
            "total_chunks": chunks_count,
            "entries_by_type": entries_by_type,
            "total_tokens": total_tokens,
        }
    
    def get_entry_content(self, organization_id: str, entry_id: str) -> Optional[str]:
        chunks = self.db.query(KnowledgeBaseChunk).filter(
            KnowledgeBaseChunk.entry_id == entry_id,
            KnowledgeBaseChunk.organization_id == organization_id
        ).order_by(KnowledgeBaseChunk.chunk_index).all()
        
        if not chunks:
            return None
        
        return "\n".join(chunk.content for chunk in chunks)
