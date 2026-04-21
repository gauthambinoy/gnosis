from fastapi import APIRouter, Depends
from app.core.aws_services import aws_services
from app.core.auth import get_current_user_id

router = APIRouter(prefix="/api/v1/aws", tags=["aws"])


@router.get("/status")
async def get_aws_status(user_id: str = Depends(get_current_user_id)):
    return {"status": "ok", "services": aws_services.get_status()}
