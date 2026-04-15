"""Gnosis File Manager — Handle file uploads, storage, and retrieval."""
import os
import uuid
import hashlib
import mimetypes
import logging
import filetype
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
}

# Filenames that must never be uploaded regardless of extension
DENIED_FILENAMES = {
    ".env", ".env.local", ".env.production", ".env.staging", ".env.development",
    ".htpasswd", ".htaccess", ".npmrc", ".pypirc", ".netrc",
    "id_rsa", "id_ed25519", "id_dsa", ".pgpass",
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
    
    def _get_aws(self):
        """Lazy import to avoid circular dependency at module load."""
        try:
            from app.core.aws_services import aws_services
            return aws_services
        except Exception:
            return None
    
    async def upload(self, content: bytes, original_name: str, agent_id: str = None, 
                     uploaded_by: str = None, tags: list = None) -> FileRecord:
        if len(content) > MAX_FILE_SIZE:
            raise ValueError(f"File too large: {len(content)} bytes (max {MAX_FILE_SIZE})")
        
        ext = Path(original_name).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError(f"File type not allowed: {ext}")

        # Block sensitive filenames regardless of extension
        base_name = Path(original_name).name.lower()
        if base_name in DENIED_FILENAMES or base_name.startswith(".env"):
            raise ValueError(f"Filename not allowed for security reasons: {base_name}")
        
        # Validate content type via magic bytes (not just extension)
        kind = filetype.guess(content)
        if kind is not None:
            mime_type = kind.mime
            # Verify the detected type matches the claimed extension
            detected_ext = f".{kind.extension}"
            if detected_ext != ext:
                # Allow some known aliases (e.g., .jpg/.jpeg)
                EXTENSION_ALIASES = {
                    ".jpg": ".jpeg", ".jpeg": ".jpg",
                    ".yml": ".yaml", ".yaml": ".yml",
                }
                if EXTENSION_ALIASES.get(ext) != detected_ext and EXTENSION_ALIASES.get(detected_ext) != ext:
                    logger.warning(f"MIME mismatch: claimed={ext}, detected={detected_ext} for {original_name}")
        
        file_id = str(uuid.uuid4())
        filename = f"{file_id}{ext}"
        
        checksum = hashlib.sha256(content).hexdigest()
        # Prefer magic-byte detection, fall back to extension-based guess
        detected = filetype.guess(content)
        mime_type = detected.mime if detected else (mimetypes.guess_type(original_name)[0] or "application/octet-stream")
        
        # Try S3 first, fall back to local storage
        s3_uri = None
        aws = self._get_aws()
        if aws:
            s3_uri = await aws.upload_file(content, filename, content_type=mime_type)
        
        if not s3_uri:
            filepath = UPLOAD_DIR / filename
            filepath.write_bytes(content)
        
        record = FileRecord(
            id=file_id,
            filename=s3_uri or filename,
            original_name=original_name,
            size=len(content),
            mime_type=mime_type,
            checksum=checksum,
            agent_id=agent_id,
            uploaded_by=uploaded_by,
            tags=tags or [],
        )
        self._files[file_id] = record
        storage = "S3" if s3_uri else "local"
        logger.info(f"File uploaded ({storage}): {file_id} ({original_name}, {len(content)} bytes)")
        return record
    
    def get(self, file_id: str) -> Optional[FileRecord]:
        return self._files.get(file_id)
    
    def get_path(self, file_id: str) -> Optional[Path]:
        record = self._files.get(file_id)
        if record:
            if record.filename.startswith("s3://"):
                return None  # Use download_content() for S3 files
            path = UPLOAD_DIR / record.filename
            if path.exists():
                return path
        return None
    
    async def download_content(self, file_id: str) -> Optional[bytes]:
        """Download file content — works for both S3 and local files."""
        record = self._files.get(file_id)
        if not record:
            return None
        if record.filename.startswith("s3://"):
            aws = self._get_aws()
            if aws:
                return await aws.download_file(record.filename)
            return None
        path = UPLOAD_DIR / record.filename
        if path.exists():
            return path.read_bytes()
        return None
    
    def list_files(self, agent_id: str = None) -> List[FileRecord]:
        files = list(self._files.values())
        if agent_id:
            files = [f for f in files if f.agent_id == agent_id]
        return sorted(files, key=lambda f: f.created_at, reverse=True)
    
    async def delete(self, file_id: str) -> bool:
        record = self._files.pop(file_id, None)
        if record:
            if record.filename.startswith("s3://"):
                aws = self._get_aws()
                if aws:
                    await aws.delete_file(record.filename)
            else:
                path = UPLOAD_DIR / record.filename
                if path.exists():
                    path.unlink()
            logger.info(f"File deleted: {file_id}")
            return True
        return False
    
    async def read_text(self, file_id: str) -> Optional[str]:
        """Read file content as text (for text-based files)."""
        if self._files.get(file_id, None) and self._files[file_id].filename.startswith("s3://"):
            content = await self.download_content(file_id)
            if content is None:
                return None
            try:
                return content.decode("utf-8")
            except UnicodeDecodeError:
                return None
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
