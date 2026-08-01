from fastapi import APIRouter, Request

from app.config import get_settings
from app.schemas import HealthData, ResponseMeta, SuccessResponse

router = APIRouter(tags=["system"])


@router.get(
    "/health",
    response_model=SuccessResponse[HealthData],
    operation_id="getHealth",
    summary="Get service health",
)
async def get_health(request: Request) -> SuccessResponse[HealthData]:
    settings = get_settings()
    return SuccessResponse(
        data=HealthData(
            service="api",
            status="ok",
            version=settings.app_version,
            environment=settings.app_env,
        ),
        meta=ResponseMeta(request_id=request.state.request_id),
    )

