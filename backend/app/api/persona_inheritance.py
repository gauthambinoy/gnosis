from fastapi import APIRouter, HTTPException, Depends
from app.core.persona_inheritance import persona_inheritance_engine
from app.core.auth import get_current_user_id
from pydantic import BaseModel
from dataclasses import asdict
from typing import Optional, List
from app.core.safe_error import safe_http_error

router = APIRouter(prefix="/api/v1/persona-templates", tags=["persona-inheritance"])


class TemplateCreate(BaseModel):
    name: str
    base_traits: dict = {}
    overridable: Optional[List[str]] = None


class InheritRequest(BaseModel):
    overrides: dict = {}


@router.post("")
async def create_template(
    req: TemplateCreate, user_id: str = Depends(get_current_user_id)
):
    template = persona_inheritance_engine.create_template(
        req.name, req.base_traits, req.overridable
    )
    return asdict(template)


@router.get("")
async def list_templates(user_id: str = Depends(get_current_user_id)):
    return {"templates": persona_inheritance_engine.list_templates()}


@router.get("/{template_id}")
async def get_template(template_id: str, user_id: str = Depends(get_current_user_id)):
    template = persona_inheritance_engine.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return asdict(template)


@router.post("/{template_id}/inherit")
async def inherit_template(
    template_id: str, req: InheritRequest, user_id: str = Depends(get_current_user_id)
):
    try:
        result = persona_inheritance_engine.inherit(template_id, req.overrides)
        return result
    except ValueError as e:
        safe_http_error(e, "Operation failed", 404)
