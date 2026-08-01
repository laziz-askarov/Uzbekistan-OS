from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.readiness import check_dependencies
from app.schemas import (
    ErrorDetail,
    ErrorResponse,
    HealthData,
    ReadinessData,
    ResponseMeta,
    SuccessResponse,
)

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


@router.get(
    "/ready",
    response_model=SuccessResponse[ReadinessData],
    responses={503: {"model": ErrorResponse}},
    operation_id="getReadiness",
    summary="Check service dependencies",
)
def get_readiness(request: Request) -> SuccessResponse[ReadinessData] | JSONResponse:
    settings = get_settings()
    checks = check_dependencies(settings)
    request_id = request.state.request_id
    if any(status != "ok" for status in checks.values()):
        body = ErrorResponse(
            error=ErrorDetail(
                code="service_not_ready",
                message="one or more required service dependencies are unavailable",
                details={"checks": checks},
            ),
            meta=ResponseMeta(request_id=request_id),
        )
        return JSONResponse(status_code=503, content=body.model_dump(mode="json"))
    return SuccessResponse(
        data=ReadinessData(service="api", status="ready", checks=checks),
        meta=ResponseMeta(request_id=request_id),
    )
