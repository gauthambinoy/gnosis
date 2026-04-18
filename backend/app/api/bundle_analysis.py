"""Bundle analysis API."""

from fastapi import APIRouter, Depends
from app.core.auth import get_current_user_id
from app.core.bundle_analyzer import bundle_analyzer
from dataclasses import asdict

router = APIRouter()


@router.get("")
async def get_bundle_analysis(user_id: str = Depends(get_current_user_id)):
    report = bundle_analyzer.get_last_report()
    if not report:
        report = asdict(bundle_analyzer.analyze_build_dir())
    return report


@router.post("/scan")
async def scan_bundle(body: dict = None, user_id: str = Depends(get_current_user_id)):
    body = body or {}
    path = body.get("path", "frontend/dist")
    report = bundle_analyzer.analyze_build_dir(path)
    return asdict(report)
