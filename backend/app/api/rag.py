from fastapi import APIRouter, HTTPException, UploadFile, File, Query
from pydantic import BaseModel, Field
from typing import Optional
from app.core.rag_engine import rag_engine
from dataclasses import asdict

router = APIRouter(prefix="/api/v1/rag", tags=["rag"])


class IngestTextRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1)
    agent_id: Optional[str] = None
    chunk_size: int = Field(500, ge=100, le=2000)
    overlap: int = Field(50, ge=0, le=200)


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    agent_id: Optional[str] = None
    top_k: int = Field(5, ge=1, le=20)


@router.post("/ingest/text")
async def ingest_text(req: IngestTextRequest):
    doc = await rag_engine.ingest(name=req.name, content=req.content, agent_id=req.agent_id, chunk_size=req.chunk_size, overlap=req.overlap)
    return asdict(doc)


@router.post("/ingest/file")
async def ingest_file(file: UploadFile = File(...), agent_id: Optional[str] = Query(None)):
    content_bytes = await file.read()
    try:
        content = content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be text-based (TXT, MD, CSV, JSON)")

    ext = (file.filename or "file.txt").rsplit(".", 1)[-1].lower()
    doc = await rag_engine.ingest(name=file.filename or "uploaded", content=content, file_type=ext, agent_id=agent_id)
    return asdict(doc)


@router.post("/search")
async def search_documents(req: SearchRequest):
    results = await rag_engine.search(query=req.query, agent_id=req.agent_id, top_k=req.top_k)
    return {"results": [asdict(r) for r in results], "total": len(results), "query": req.query}


@router.get("/documents")
async def list_documents(agent_id: Optional[str] = None):
    docs = rag_engine.list_documents(agent_id=agent_id)
    return {"documents": [asdict(d) for d in docs], "total": len(docs)}


@router.get("/documents/{doc_id}")
async def get_document(doc_id: str):
    doc = rag_engine.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return asdict(doc)


@router.get("/documents/{doc_id}/chunks")
async def get_document_chunks(doc_id: str):
    chunks = rag_engine.get_chunks(doc_id)
    if not chunks:
        raise HTTPException(status_code=404, detail="Document not found or has no chunks")
    return {"chunks": [{"id": c.id, "content": c.content, "chunk_index": c.chunk_index} for c in chunks], "total": len(chunks)}


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    if not rag_engine.delete_document(doc_id):
        raise HTTPException(status_code=404, detail="Document not found")
    return {"deleted": True}


@router.get("/stats")
async def rag_stats():
    return rag_engine.stats
