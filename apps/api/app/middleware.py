import logging
from collections.abc import Awaitable, Callable
from re import fullmatch
from time import perf_counter
from uuid import uuid4

from fastapi import Request, Response

from app.observability import bind_request_id, reset_request_id

logger = logging.getLogger("uzbekistan_os.http")


def apply_security_headers(response: Response, *, production: bool) -> None:
    response.headers.setdefault("cache-control", "no-store")
    response.headers.setdefault("permissions-policy", "camera=(), geolocation=(), microphone=()")
    response.headers.setdefault("referrer-policy", "no-referrer")
    response.headers.setdefault("x-content-type-options", "nosniff")
    response.headers.setdefault("x-frame-options", "DENY")
    if production:
        response.headers.setdefault(
            "strict-transport-security",
            "max-age=31536000; includeSubDomains",
        )


def _request_id(value: str | None) -> str:
    if value and len(value) <= 128 and fullmatch(r"[A-Za-z0-9._:-]+", value):
        return value
    return str(uuid4())


async def request_id_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    request_id = _request_id(request.headers.get("x-request-id"))
    request.state.request_id = request_id
    token = bind_request_id(request_id)
    started = perf_counter()
    status_code = 500
    failed = False
    try:
        response = await call_next(request)
        status_code = response.status_code
        response.headers["x-request-id"] = request_id
        return response
    except Exception:
        failed = True
        logger.exception(
            "request failed",
            extra={
                "duration_ms": round((perf_counter() - started) * 1000, 2),
                "http_method": request.method,
                "http_path": request.url.path,
                "status_code": status_code,
            },
        )
        raise
    finally:
        if not failed:
            logger.info(
                "request completed",
                extra={
                    "duration_ms": round((perf_counter() - started) * 1000, 2),
                    "http_method": request.method,
                    "http_path": request.url.path,
                    "status_code": status_code,
                },
            )
        reset_request_id(token)
