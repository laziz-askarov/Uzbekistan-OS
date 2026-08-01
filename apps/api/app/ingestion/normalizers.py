from hashlib import sha256
from html.parser import HTMLParser
from re import sub
from typing import ClassVar

from app.ingestion.errors import IngestionError
from app.ingestion.types import FetchResponse, NormalizedContent

HTML_MEDIA_TYPES = {"text/html", "application/xhtml+xml"}
TEXT_MEDIA_TYPES = {"text/plain", "text/xml", "application/xml", "application/rss+xml"}


class _VisibleTextParser(HTMLParser):
    _BLOCK_TAGS: ClassVar[frozenset[str]] = frozenset(
        {
            "article",
            "br",
            "div",
            "footer",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "header",
            "li",
            "main",
            "p",
            "section",
            "table",
            "td",
            "th",
            "tr",
        }
    )
    _IGNORED_TAGS: ClassVar[frozenset[str]] = frozenset(
        {"noscript", "script", "style", "svg", "template"}
    )

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._ignored_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        if tag in self._IGNORED_TAGS:
            self._ignored_depth += 1
        elif not self._ignored_depth and tag in self._BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self._IGNORED_TAGS:
            self._ignored_depth = max(0, self._ignored_depth - 1)
        elif not self._ignored_depth and tag in self._BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._ignored_depth:
            self.parts.append(data)


def _clean_text(value: str) -> str:
    lines = [sub(r"\s+", " ", line).strip() for line in value.splitlines()]
    return "\n".join(line for line in lines if line)


def normalize_response(response: FetchResponse) -> NormalizedContent:
    content_type = (response.header("content-type") or "").split(";", 1)[0].strip().casefold()
    if content_type in HTML_MEDIA_TYPES:
        parser = _VisibleTextParser()
        parser.feed(response.body.decode("utf-8", errors="replace"))
        text = _clean_text("".join(parser.parts))
    elif content_type in TEXT_MEDIA_TYPES:
        text = _clean_text(response.body.decode("utf-8", errors="replace"))
    else:
        raise IngestionError(
            "unsupported_content_type",
            f"unsupported ingestion content type: {content_type or 'missing'}",
            retryable=False,
        )

    if not text:
        raise IngestionError(
            "empty_normalized_content",
            "fetched source did not contain visible text",
            retryable=False,
        )

    digest = sha256(text.encode("utf-8")).hexdigest()
    return NormalizedContent(text=text, sha256=digest, media_type=content_type)
