from fastapi import APIRouter
from app.core.aws_services import aws_services

router = APIRouter(prefix="/api/v1/aws", tags=["aws"])


@router.get("/status")
async def get_aws_status():
    return {"status": "ok", "services": aws_services.get_status()}
