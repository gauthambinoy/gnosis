from fastapi import APIRouter, HTTPException, Depends
from app.core.ab_comparison import ab_engine
from app.core.auth import get_current_user_id
from dataclasses import asdict

router = APIRouter(prefix="/api/v1/ab-compare", tags=["ab-compare"])


@router.post("")
async def create_comparison(data: dict, user_id: str = Depends(get_current_user_id)):
    comp = ab_engine.create_comparison(
        prompt=data.get("prompt", ""),
        response_a=data.get("response_a", ""),
        response_b=data.get("response_b", ""),
        agent_a=data.get("agent_a", ""),
        agent_b=data.get("agent_b", ""),
    )
    return asdict(comp)


@router.post("/{comparison_id}/vote")
async def vote(comparison_id: str, data: dict, user_id: str = Depends(get_current_user_id)):
    try:
        comp = ab_engine.vote(comparison_id, data.get("winner", ""))
        return asdict(comp)
    except KeyError:
        raise HTTPException(status_code=404, detail="Comparison not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("")
async def list_comparisons(user_id: str = Depends(get_current_user_id)):
    return {"comparisons": ab_engine.list_comparisons()}
