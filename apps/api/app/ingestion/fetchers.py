from collections.abc import Mapping
from datetime import UTC, datetime
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from app.ingestion.errors import IngestionError
from app.ingestion.models import SourceRegistryEntry
from app.ingestion.types import FetchResponse


class _RejectRedirects(HTTPRedirectHandler):
    def redirect_request(
        self,
        request: Request,
        file_pointer: object,
        code: int,
        message: str,
        headers: Mapping[str, str],
        new_url: str,
    ) -> None:
        del request, file_pointer, code, message, headers, new_url
        return None


class HttpSourceFetcher:
    def __init__(self, *, timeout_seconds: float = 20, max_bytes: int = 10_000_000) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_bytes = max_bytes
        self._opener = build_opener(_RejectRedirects())

    def fetch(
        self,
        source: SourceRegistryEntry,
        conditional_headers: Mapping[str, str],
    ) -> FetchResponse:
        request = Request(
            str(source.url),
            headers={
                "Accept": "text/html, application/xhtml+xml, text/plain, application/xml;q=0.8",
                "User-Agent": "UzbekistanOSBot/0.1 (+source-review-required)",
                **conditional_headers,
            },
            method="GET",
        )
        try:
            with self._opener.open(request, timeout=self.timeout_seconds) as response:
                body = response.read(self.max_bytes + 1)
                if len(body) > self.max_bytes:
                    raise IngestionError(
                        "response_too_large",
                        f"source response exceeds {self.max_bytes} bytes",
                        retryable=False,
                    )
                return FetchResponse(
                    url=response.url,
                    status_code=response.status,
                    body=body,
                    fetched_at=datetime.now(UTC),
                    headers=dict(response.headers.items()),
                )
        except HTTPError as error:
            body = error.read(self.max_bytes + 1)
            return FetchResponse(
                url=error.url,
                status_code=error.code,
                body=body,
                fetched_at=datetime.now(UTC),
                headers=dict(error.headers.items()),
            )
        except URLError as error:
            raise IngestionError(
                "fetch_unavailable",
                f"source fetch failed: {error.reason}",
                retryable=True,
            ) from error
