from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict

from app.dependencies import get_authenticated_principal
from app.identity.service import AuthenticatedPrincipal
from app.schemas import ResponseMeta, SuccessResponse

router = APIRouter(prefix="/auth", tags=["authentication"])


class PrincipalData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    roles: list[str]


@router.get(
    "/me",
    response_model=SuccessResponse[PrincipalData],
    operation_id="getAuthenticatedPrincipal",
    summary="Get the authenticated internal principal",
)
def get_authenticated_identity(
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
) -> SuccessResponse[PrincipalData]:
    return SuccessResponse(
        data=PrincipalData(id=principal.id, roles=sorted(principal.roles)),
        meta=ResponseMeta(request_id=request.state.request_id),
    )
