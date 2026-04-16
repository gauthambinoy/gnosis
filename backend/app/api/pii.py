from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.core.pii_detector import pii_detector
from app.core.auth import get_current_user_id
from dataclasses import asdict
from typing import Optional, List

router = APIRouter(prefix="/api/v1/pii", tags=["compliance"])

class ScanRequest(BaseModel):
    text: str
    redact: bool = True

@router.post("/scan")
async def scan_text(req: ScanRequest, user_id: str = Depends(get_current_user_id)):
    result = pii_detector.scan(req.text)
    response = {
        "pii_found": result.pii_found,
        "detection_count": len(result.detections),
        "detections": [{"type": d.pii_type, "start": d.start, "end": d.end, "confidence": d.confidence} for d in result.detections],
        "scan_time_ms": result.scan_time_ms,
    }
    if req.redact:
        response["redacted_text"] = result.redacted_text
    return response

@router.post("/redact")
async def redact_text(req: ScanRequest, user_id: str = Depends(get_current_user_id)):
    return {"redacted_text": pii_detector.redact(req.text)}

@router.get("/stats")
async def pii_stats(user_id: str = Depends(get_current_user_id)):
    return pii_detector.stats
