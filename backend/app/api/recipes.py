from fastapi import APIRouter, HTTPException, Depends
from app.core.recipes import recipe_engine
from app.core.auth import get_current_user_id
from typing import Optional

router = APIRouter(prefix="/api/v1/recipes", tags=["growth"])


@router.get("")
async def list_recipes(
    category: Optional[str] = None, user_id: str = Depends(get_current_user_id)
):
    return {"recipes": recipe_engine.list_recipes(category=category)}


@router.get("/{recipe_id}")
async def get_recipe(recipe_id: str, user_id: str = Depends(get_current_user_id)):
    recipe = recipe_engine.get_recipe(recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return recipe


@router.post("/{recipe_id}/deploy")
async def deploy_recipe(recipe_id: str, user_id: str = Depends(get_current_user_id)):
    result = recipe_engine.deploy_recipe(recipe_id, user_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result
