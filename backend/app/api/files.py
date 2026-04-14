from fastapi import APIRouter, HTTPException, UploadFile, File, Query
from fastapi.responses import FileResponse
from typing import Optional, List
from app.core.file_manager import file_manager
from dataclasses import asdict

router = APIRouter(prefix="/api/v1/files", tags=["files"])


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    agent_id: Optional[str] = Query(None),
    tags: Optional[str] = Query(None, description="Comma-separated tags"),
):
    content = await file.read()
    try:
        tag_list = [t.strip() for t in tags.split(",")] if tags else []
        record = await file_manager.upload(
            content=content,
            original_name=file.filename or "unnamed",
            agent_id=agent_id,
            tags=tag_list,
        )
        return asdict(record)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("")
async def list_files(agent_id: Optional[str] = None):
    files = file_manager.list_files(agent_id=agent_id)
    return {"files": [asdict(f) for f in files], "total": len(files)}


@router.get("/stats")
async def file_stats():
    return file_manager.stats


@router.get("/{file_id}")
async def get_file_info(file_id: str):
    record = file_manager.get(file_id)
    if not record:
        raise HTTPException(status_code=404, detail="File not found")
    return asdict(record)


@router.get("/{file_id}/download")
async def download_file(file_id: str):
    record = file_manager.get(file_id)
    if not record:
        raise HTTPException(status_code=404, detail="File not found")
    path = file_manager.get_path(file_id)
    if not path:
        raise HTTPException(status_code=404, detail="File not found on disk")
    return FileResponse(path, filename=record.original_name, media_type=record.mime_type)


@router.get("/{file_id}/content")
async def get_file_content(file_id: str):
    """Get text content of a file (for text-based files only)."""
    text = await file_manager.read_text(file_id)
    if text is None:
        raise HTTPException(status_code=400, detail="File is not text-readable or not found")
    record = file_manager.get(file_id)
    return {"file_id": file_id, "filename": record.original_name, "content": text}


@router.delete("/{file_id}")
async def delete_file(file_id: str):
    if not await file_manager.delete(file_id):
        raise HTTPException(status_code=404, detail="File not found")
    return {"deleted": True}
