from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.assistant.service import AssistantError
from app.identity.authentication import AuthenticationError
from app.ingestion.admin import AdminIngestionError
from app.ingestion.errors import IngestionError
from app.ingestion.review import ReviewError
from app.knowledge.lifecycle import KnowledgeLifecycleError
from app.knowledge.publication import PublicationError
from app.schemas import ErrorDetail, ErrorResponse, ResponseMeta


def _error_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    authenticate: bool = False,
) -> JSONResponse:
    headers = {"WWW-Authenticate": "Bearer"} if authenticate else None
    body = ErrorResponse(
        error=ErrorDetail(code=code, message=message),
        meta=ResponseMeta(request_id=getattr(request.state, "request_id", None)),
    )
    return JSONResponse(
        status_code=status_code,
        content=body.model_dump(mode="json"),
        headers=headers,
    )


def install_exception_handlers(application: FastAPI) -> None:
    @application.exception_handler(RequestValidationError)
    async def request_validation_error_handler(
        request: Request,
        error: RequestValidationError,
    ) -> JSONResponse:
        issues = [
            {
                "location": [str(part) for part in issue["loc"]],
                "message": issue["msg"],
                "type": issue["type"],
            }
            for issue in error.errors()
        ]
        body = ErrorResponse(
            error=ErrorDetail(
                code="request_validation_error",
                message="the request payload or parameters are invalid",
                details={"issues": issues},
            ),
            meta=ResponseMeta(request_id=getattr(request.state, "request_id", None)),
        )
        return JSONResponse(
            status_code=422,
            content=body.model_dump(mode="json"),
        )

    @application.exception_handler(AuthenticationError)
    async def authentication_error_handler(
        request: Request,
        error: AuthenticationError,
    ) -> JSONResponse:
        if error.code in {"authentication_unconfigured", "identity_provider_unavailable"}:
            status_code = 503
        elif error.code in {"principal_not_provisioned", "principal_disabled"}:
            status_code = 403
        else:
            status_code = 401
        return _error_response(
            request,
            status_code=status_code,
            code=error.code,
            message=str(error),
            authenticate=status_code == 401,
        )

    @application.exception_handler(AssistantError)
    async def assistant_error_handler(
        request: Request,
        error: AssistantError,
    ) -> JSONResponse:
        return _error_response(
            request,
            status_code=422,
            code=error.code,
            message=str(error),
        )

    @application.exception_handler(ReviewError)
    async def review_error_handler(
        request: Request,
        error: ReviewError,
    ) -> JSONResponse:
        if error.code == "review_forbidden":
            status_code = 403
        elif error.code in {"review_not_found", "artifact_not_found"}:
            status_code = 404
        elif error.code == "invalid_decision_reason":
            status_code = 422
        else:
            status_code = 409
        return _error_response(
            request,
            status_code=status_code,
            code=error.code,
            message=str(error),
        )

    @application.exception_handler(AdminIngestionError)
    async def admin_ingestion_error_handler(
        request: Request,
        error: AdminIngestionError,
    ) -> JSONResponse:
        if error.code == "admin_forbidden":
            status_code = 403
        elif error.code == "source_not_found":
            status_code = 404
        elif error.code in {
            "invalid_upload_encoding",
            "empty_upload",
            "upload_too_large",
        }:
            status_code = 422
        elif error.code == "ingestion_infrastructure_unavailable":
            status_code = 503
        else:
            status_code = 409
        return _error_response(
            request,
            status_code=status_code,
            code=error.code,
            message=str(error),
        )

    @application.exception_handler(IngestionError)
    async def ingestion_error_handler(
        request: Request,
        error: IngestionError,
    ) -> JSONResponse:
        status_code = 409 if error.code in {"job_in_progress", "job_terminal"} else 422
        return _error_response(
            request,
            status_code=status_code,
            code=error.code,
            message=str(error),
        )

    @application.exception_handler(PublicationError)
    async def publication_error_handler(
        request: Request,
        error: PublicationError,
    ) -> JSONResponse:
        if error.code == "publication_forbidden":
            status_code = 403
        elif error.code == "review_not_found":
            status_code = 404
        elif error.code in {
            "invalid_publication_time",
            "domain_not_found",
            "language_not_found",
        }:
            status_code = 422
        else:
            status_code = 409
        return _error_response(
            request,
            status_code=status_code,
            code=error.code,
            message=str(error),
        )

    @application.exception_handler(KnowledgeLifecycleError)
    async def knowledge_lifecycle_error_handler(
        request: Request,
        error: KnowledgeLifecycleError,
    ) -> JSONResponse:
        if error.code == "publication_forbidden":
            status_code = 403
        elif error.code == "document_not_found":
            status_code = 404
        elif error.code == "invalid_lifecycle_time":
            status_code = 422
        else:
            status_code = 409
        return _error_response(
            request,
            status_code=status_code,
            code=error.code,
            message=str(error),
        )
