"""Gnosis File Manager — Handle file uploads, storage, and retrieval."""
import os
import uuid
import hashlib
import mimetypes
import logging
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Dict, Optional, List
from pathlib import Path

logger = logging.getLogger("gnosis.files")

UPLOAD_DIR = Path(os.getenv("GNOSIS_UPLOAD_DIR", "./uploads"))
MAX_FILE_SIZE = int(os.getenv("GNOSIS_MAX_FILE_SIZE", 50 * 1024 * 1024))  # 50MB default
ALLOWED_EXTENSIONS = {
    ".txt", ".md", ".csv", ".json", ".xml", ".yaml", ".yml",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx",
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp",
    ".py", ".js", ".ts", ".html", ".css",
    ".log", ".env",
}


@dataclass
class FileRecord:
    id: str
    filename: str
    original_name: str
    size: int
    mime_type: str
    checksum: str
    agent_id: Optional[str] = None
    uploaded_by: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class FileManager:
    def __init__(self):
        self._files: Dict[str, FileRecord] = {}
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    
    async def upload(self, content: bytes, original_name: str, agent_id: str = None, 
                     uploaded_by: str = None, tags: list = None) -> FileRecord:
        if len(content) > MAX_FILE_SIZE:
            raise ValueError(f"File too large: {len(content)} bytes (max {MAX_FILE_SIZE})")
        
        ext = Path(original_name).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError(f"File type not allowed: {ext}")
        
        file_id = str(uuid.uuid4())
        filename = f"{file_id}{ext}"
        filepath = UPLOAD_DIR / filename
        
        checksum = hashlib.sha256(content).hexdigest()
        mime_type = mimetypes.guess_type(original_name)[0] or "application/octet-stream"
        
        filepath.write_bytes(content)
        
        record = FileRecord(
            id=file_id,
            filename=filename,
            original_name=original_name,
            size=len(content),
            mime_type=mime_type,
            checksum=checksum,
            agent_id=agent_id,
            uploaded_by=uploaded_by,
            tags=tags or [],
        )
        self._files[file_id] = record
        logger.info(f"File uploaded: {file_id} ({original_name}, {len(content)} bytes)")
        return record
    
    def get(self, file_id: str) -> Optional[FileRecord]:
        return self._files.get(file_id)
    
    def get_path(self, file_id: str) -> Optional[Path]:
        record = self._files.get(file_id)
        if record:
            path = UPLOAD_DIR / record.filename
            if path.exists():
                return path
        return None
    
    def list_files(self, agent_id: str = None) -> List[FileRecord]:
        files = list(self._files.values())
        if agent_id:
            files = [f for f in files if f.agent_id == agent_id]
        return sorted(files, key=lambda f: f.created_at, reverse=True)
    
    def delete(self, file_id: str) -> bool:
        record = self._files.pop(file_id, None)
        if record:
            path = UPLOAD_DIR / record.filename
            if path.exists():
                path.unlink()
            logger.info(f"File deleted: {file_id}")
            return True
        return False
    
    def read_text(self, file_id: str) -> Optional[str]:
        """Read file content as text (for text-based files)."""
        path = self.get_path(file_id)
        if not path:
            return None
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return None
    
    @property
    def stats(self) -> dict:
        total_size = sum(f.size for f in self._files.values())
        return {
            "total_files": len(self._files),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
        }


file_manager = FileManager()
