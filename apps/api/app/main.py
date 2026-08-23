from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.ai.settings import load_ai_runtime_configuration
from app.config import get_settings
from app.errors import install_exception_handlers
from app.middleware import apply_security_headers, request_id_middleware
from app.observability import configure_logging
from app.routes.admin import router as admin_router
from app.routes.assistant import router as assistant_router
from app.routes.auth import router as auth_router
from app.routes.health import get_health, get_readiness
from app.routes.health import router as health_router


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # Database, Redis, and provider clients will be initialized here as their
    # adapters are introduced. Keeping the lifecycle explicit prevents clients
    # from being created at import time.
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    ai_runtime = load_ai_runtime_configuration(settings)
    configure_logging(settings.log_level)
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Evidence-backed guidance API for Uzbekistan OS.",
        docs_url="/docs" if settings.app_env != "production" else None,
        redoc_url="/redoc" if settings.app_env != "production" else None,
        lifespan=lifespan,
    )
    application.state.ai_runtime = ai_runtime
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "authorization",
            "content-type",
            "idempotency-key",
            "x-request-id",
        ],
    )
    application.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)

    @application.middleware("http")
    async def security_headers(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        apply_security_headers(response, production=settings.app_env == "production")
        return response

    application.middleware("http")(request_id_middleware)
    install_exception_handlers(application)
    application.include_router(health_router, prefix="/api/v1")
    application.add_api_route(
        "/health",
        get_health,
        methods=["GET"],
        include_in_schema=False,
    )
    application.add_api_route(
        "/ready",
        get_readiness,
        methods=["GET"],
        include_in_schema=False,
        response_model=None,
    )
    application.include_router(auth_router, prefix="/api/v1")
    application.include_router(assistant_router, prefix="/api/v1")
    application.include_router(admin_router, prefix="/api/v1")
    return application


app = create_app()
