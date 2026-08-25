from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.assistant.service import (
    AssistantAnswerData,
    AssistantAnswerRequest,
    GroundedAssistantService,
)
from app.dependencies import get_grounded_assistant_service, get_verified_identity
from app.identity.service import VerifiedIdentity
from app.schemas import ResponseMeta, SuccessResponse

router = APIRouter(prefix="/assistant", tags=["assistant"])


@router.post(
    "/answer",
    response_model=SuccessResponse[AssistantAnswerData],
    operation_id="answerGroundedQuestion",
    summary="Answer from eligible official evidence with a bounded live fallback",
)
def answer_grounded_question(
    payload: AssistantAnswerRequest,
    request: Request,
    identity: Annotated[VerifiedIdentity, Depends(get_verified_identity)],
    service: Annotated[GroundedAssistantService, Depends(get_grounded_assistant_service)],
) -> SuccessResponse[AssistantAnswerData]:
    del identity
    return SuccessResponse(
        data=service.answer(payload, request_id=request.state.request_id),
        meta=ResponseMeta(request_id=request.state.request_id),
    )
