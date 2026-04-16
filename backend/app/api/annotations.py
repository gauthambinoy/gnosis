from fastapi import APIRouter, HTTPException, Depends
from app.core.annotations import annotation_engine
from app.core.auth import get_current_user_id
from dataclasses import asdict

router = APIRouter(prefix="/api/v1/annotations", tags=["annotations"])


@router.get("/{execution_id}")
async def list_annotations(execution_id: str, user_id: str = Depends(get_current_user_id)):
    return {"annotations": annotation_engine.list_annotations(execution_id)}


@router.post("/{execution_id}")
async def add_annotation(execution_id: str, data: dict, user_id: str = Depends(get_current_user_id)):
    try:
        ann = annotation_engine.add_annotation(
            execution_id=execution_id,
            user_id=user_id,
            text=data.get("text", ""),
            selection_start=data.get("selection_start", 0),
            selection_end=data.get("selection_end", 0),
            annotation_type=data.get("type", "note"),
        )
        return asdict(ann)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{annotation_id}")
async def delete_annotation(annotation_id: str, user_id: str = Depends(get_current_user_id)):
    if not annotation_engine.delete_annotation(annotation_id):
        raise HTTPException(status_code=404, detail="Annotation not found")
    return {"status": "deleted"}
