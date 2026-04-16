from fastapi import APIRouter, HTTPException, Depends
from app.core.compliance_reports import compliance_engine
from app.core.auth import get_current_user_id
from dataclasses import asdict
from typing import Optional
from app.core.safe_error import safe_http_error

router = APIRouter(prefix="/api/v1/compliance/reports", tags=["compliance-reports"])


@router.post("/generate")
async def generate_report(data: dict, user_id: str = Depends(get_current_user_id)):
    try:
        report = compliance_engine.generate_report(
            workspace_id=data.get("workspace_id", ""),
            report_type=data.get("type", "gdpr"),
        )
        return asdict(report)
    except ValueError as e:
        safe_http_error(e, "Operation failed", 400)


@router.get("")
async def list_reports(workspace_id: Optional[str] = None, user_id: str = Depends(get_current_user_id)):
    return {"reports": compliance_engine.list_reports(workspace_id or "")}


@router.get("/{report_id}")
async def get_report(report_id: str, user_id: str = Depends(get_current_user_id)):
    try:
        report = compliance_engine.get_report(report_id)
        return asdict(report)
    except KeyError:
        raise HTTPException(status_code=404, detail="Report not found")
