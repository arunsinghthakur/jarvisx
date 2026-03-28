from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional
import io

from jarvisx.database.session import get_db
from jarvisx.database.models import Organization
from services.api.admin.src.dependencies import OrganizationContext, get_organization_context
from services.api.admin.src.models.knowledge_base import (
    SnippetCreate,
    SnippetUpdate,
    KnowledgeBaseEntryResponse,
    KnowledgeBaseEntriesResponse,
    SearchQuery,
    SearchResponse,
    SearchResult,
    KnowledgeBaseStats,
)
from jarvisx.services.knowledge_base import KnowledgeBaseService

router = APIRouter(prefix="/api/organizations/{organization_id}/knowledge-base", tags=["knowledge-base"])


def _verify_organization_access(organization_id: str, db: Session, org_ctx: OrganizationContext) -> Organization:
    org = db.query(Organization).filter(Organization.id == organization_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    if not org_ctx.can_access_organization(organization_id):
        raise HTTPException(status_code=403, detail="Access denied to this organization")
    return org


@router.get("/stats", response_model=KnowledgeBaseStats)
def get_stats(
    organization_id: str,
    db: Session = Depends(get_db),
    org_ctx: OrganizationContext = Depends(get_organization_context)
):
    _verify_organization_access(organization_id, db, org_ctx)
    service = KnowledgeBaseService(db)
    return service.get_stats(organization_id)


@router.get("/entries", response_model=KnowledgeBaseEntriesResponse)
def list_entries(
    organization_id: str,
    entry_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    org_ctx: OrganizationContext = Depends(get_organization_context)
):
    _verify_organization_access(organization_id, db, org_ctx)
    service = KnowledgeBaseService(db)
    entries, total = service.list_entries(organization_id, entry_type, skip, limit)
    return KnowledgeBaseEntriesResponse(
        entries=[KnowledgeBaseEntryResponse.model_validate(e) for e in entries],
        total=total
    )


@router.get("/entries/{entry_id}", response_model=KnowledgeBaseEntryResponse)
def get_entry(
    organization_id: str,
    entry_id: str,
    db: Session = Depends(get_db),
    org_ctx: OrganizationContext = Depends(get_organization_context)
):
    _verify_organization_access(organization_id, db, org_ctx)
    service = KnowledgeBaseService(db)
    entry = service.get_entry(organization_id, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    return entry


@router.get("/entries/{entry_id}/content")
def get_entry_content(
    organization_id: str,
    entry_id: str,
    db: Session = Depends(get_db),
    org_ctx: OrganizationContext = Depends(get_organization_context)
):
    _verify_organization_access(organization_id, db, org_ctx)
    service = KnowledgeBaseService(db)
    content = service.get_entry_content(organization_id, entry_id)
    if content is None:
        raise HTTPException(status_code=404, detail="Entry not found")
    return {"content": content}


@router.post("/snippets", response_model=KnowledgeBaseEntryResponse)
def create_snippet(
    organization_id: str,
    snippet: SnippetCreate,
    db: Session = Depends(get_db),
    org_ctx: OrganizationContext = Depends(get_organization_context)
):
    _verify_organization_access(organization_id, db, org_ctx)
    service = KnowledgeBaseService(db)
    try:
        entry = service.create_snippet(
            organization_id=organization_id,
            title=snippet.title,
            content=snippet.content,
            metadata=snippet.metadata
        )
        return entry
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/snippets/{entry_id}", response_model=KnowledgeBaseEntryResponse)
def update_snippet(
    organization_id: str,
    entry_id: str,
    snippet: SnippetUpdate,
    db: Session = Depends(get_db),
    org_ctx: OrganizationContext = Depends(get_organization_context)
):
    _verify_organization_access(organization_id, db, org_ctx)
    service = KnowledgeBaseService(db)
    try:
        entry = service.update_snippet(
            organization_id=organization_id,
            entry_id=entry_id,
            title=snippet.title,
            content=snippet.content,
            metadata=snippet.metadata
        )
        return entry
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/documents", response_model=KnowledgeBaseEntryResponse)
async def upload_document(
    organization_id: str,
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    org_ctx: OrganizationContext = Depends(get_organization_context)
):
    _verify_organization_access(organization_id, db, org_ctx)
    
    allowed_extensions = {'.txt', '.md', '.pdf'}
    filename = file.filename or "unknown"
    ext = '.' + filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"File type not supported. Allowed: {', '.join(allowed_extensions)}"
        )
    
    content_bytes = await file.read()
    file_size = len(content_bytes)
    
    if file_size > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size exceeds 10MB limit")
    
    if ext == '.pdf':
        try:
            from pypdf import PdfReader
            pdf_reader = PdfReader(io.BytesIO(content_bytes))
            content = ""
            for page in pdf_reader.pages:
                content += page.extract_text() or ""
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to parse PDF: {str(e)}")
    else:
        try:
            content = content_bytes.decode('utf-8')
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="File encoding not supported. Please use UTF-8.")
    
    if not content.strip():
        raise HTTPException(status_code=400, detail="Document appears to be empty")
    
    service = KnowledgeBaseService(db)
    try:
        entry = service.create_document_entry(
            organization_id=organization_id,
            title=title or filename,
            filename=filename,
            content=content,
            file_size=file_size,
            metadata={"original_filename": filename, "file_extension": ext}
        )
        return entry
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/entries/{entry_id}")
def delete_entry(
    organization_id: str,
    entry_id: str,
    db: Session = Depends(get_db),
    org_ctx: OrganizationContext = Depends(get_organization_context)
):
    _verify_organization_access(organization_id, db, org_ctx)
    service = KnowledgeBaseService(db)
    if not service.delete_entry(organization_id, entry_id):
        raise HTTPException(status_code=404, detail="Entry not found")
    return {"message": "Entry deleted successfully"}


@router.post("/search", response_model=SearchResponse)
def search_knowledge_base(
    organization_id: str,
    query: SearchQuery,
    db: Session = Depends(get_db),
    org_ctx: OrganizationContext = Depends(get_organization_context)
):
    _verify_organization_access(organization_id, db, org_ctx)
    service = KnowledgeBaseService(db)
    results = service.search(
        organization_id=organization_id,
        query=query.query,
        limit=query.limit,
        similarity_threshold=query.similarity_threshold
    )
    return SearchResponse(
        query=query.query,
        results=[SearchResult(**r) for r in results],
        total_results=len(results)
    )
