from fastapi import APIRouter, HTTPException, Depends
from app.core.response_templates import response_template_engine
from app.core.auth import get_current_user_id
from pydantic import BaseModel
from dataclasses import asdict
from app.core.safe_error import safe_http_error

router = APIRouter(prefix="/api/v1/response-templates", tags=["response-templates"])


class TemplateCreate(BaseModel):
    name: str
    format: str = "markdown"
    structure: str = ""
    example: str = ""


class ApplyRequest(BaseModel):
    content: str


@router.get("")
async def list_templates(user_id: str = Depends(get_current_user_id)):
    return {"templates": response_template_engine.list_templates()}


@router.post("")
async def create_template(req: TemplateCreate, user_id: str = Depends(get_current_user_id)):
    try:
        template = response_template_engine.create_template(req.name, req.format, req.structure, req.example)
        return asdict(template)
    except ValueError as e:
        safe_http_error(e, "Operation failed", 400)


@router.get("/{template_id}")
async def get_template(template_id: str, user_id: str = Depends(get_current_user_id)):
    template = response_template_engine.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return asdict(template)


@router.post("/{template_id}/apply")
async def apply_template(template_id: str, req: ApplyRequest, user_id: str = Depends(get_current_user_id)):
    try:
        result = response_template_engine.apply_template(req.content, template_id)
        return {"formatted": result, "template_id": template_id}
    except ValueError as e:
        safe_http_error(e, "Operation failed", 404)
