from typing import Any

from pydantic import BaseModel, Field


class ResponseMeta(BaseModel):
    request_id: str | None = None


class SuccessResponse[DataT](BaseModel):
    data: DataT
    meta: ResponseMeta = Field(default_factory=ResponseMeta)


class HealthData(BaseModel):
    service: str
    status: str
    version: str
    environment: str


class ReadinessData(BaseModel):
    service: str
    status: str
    checks: dict[str, str]


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    error: ErrorDetail
    meta: ResponseMeta = Field(default_factory=ResponseMeta)
