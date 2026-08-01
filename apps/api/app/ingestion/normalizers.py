from hashlib import sha256
from html.parser import HTMLParser
from io import BytesIO
from re import sub
from typing import ClassVar

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.ingestion.errors import IngestionError
from app.ingestion.types import FetchResponse, NormalizedContent

HTML_MEDIA_TYPES = {"text/html", "application/xhtml+xml"}
TEXT_MEDIA_TYPES = {"text/plain", "text/xml", "application/xml", "application/rss+xml"}
PDF_MEDIA_TYPES = {"application/pdf"}


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


def normalize_response(
    response: FetchResponse,
    *,
    max_pdf_pages: int = 250,
    max_normalized_characters: int = 2_000_000,
) -> NormalizedContent:
    content_type = (response.header("content-type") or "").split(";", 1)[0].strip().casefold()
    sections: tuple[tuple[str, str], ...] = ()
    if content_type in HTML_MEDIA_TYPES:
        parser = _VisibleTextParser()
        parser.feed(response.body.decode("utf-8", errors="replace"))
        text = _clean_text("".join(parser.parts))
    elif content_type in TEXT_MEDIA_TYPES:
        text = _clean_text(response.body.decode("utf-8", errors="replace"))
    elif content_type in PDF_MEDIA_TYPES:
        sections = _extract_pdf_sections(
            response.body,
            max_pages=max_pdf_pages,
            max_characters=max_normalized_characters,
        )
        text = "\n\n".join(f"{heading}\n{body}" for heading, body in sections)
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

    if len(text) > max_normalized_characters:
        raise IngestionError(
            "normalized_content_too_large",
            f"normalized source exceeds {max_normalized_characters} characters",
            retryable=False,
        )

    digest = sha256(text.encode("utf-8")).hexdigest()
    return NormalizedContent(
        text=text,
        sha256=digest,
        media_type=content_type,
        sections=sections,
    )


def _extract_pdf_sections(
    body: bytes,
    *,
    max_pages: int,
    max_characters: int,
) -> tuple[tuple[str, str], ...]:
    if b"%PDF-" not in body[:1024]:
        raise IngestionError(
            "invalid_pdf_signature",
            "PDF response does not contain a valid file signature",
            retryable=False,
        )
    try:
        reader = PdfReader(BytesIO(body), strict=True)
        if reader.is_encrypted:
            raise IngestionError(
                "encrypted_pdf_unsupported",
                "encrypted PDF sources are not supported",
                retryable=False,
            )
        page_count = len(reader.pages)
        if page_count < 1:
            raise IngestionError(
                "empty_pdf",
                "PDF source does not contain any pages",
                retryable=False,
            )
        if page_count > max_pages:
            raise IngestionError(
                "pdf_page_limit_exceeded",
                f"PDF source exceeds the {max_pages} page limit",
                retryable=False,
            )

        sections: list[tuple[str, str]] = []
        character_count = 0
        for page_number, page in enumerate(reader.pages, start=1):
            text = _clean_text(page.extract_text() or "")
            if not text:
                continue
            character_count += len(text)
            if character_count > max_characters:
                raise IngestionError(
                    "normalized_content_too_large",
                    f"normalized source exceeds {max_characters} characters",
                    retryable=False,
                )
            sections.append((f"Page {page_number}", text))
    except IngestionError:
        raise
    except (PdfReadError, KeyError, TypeError, ValueError) as error:
        raise IngestionError(
            "invalid_pdf",
            "PDF source could not be parsed safely",
            retryable=False,
        ) from error

    if not sections:
        raise IngestionError(
            "pdf_text_unavailable",
            "PDF source does not contain extractable text; OCR is not enabled",
            retryable=False,
        )
    return tuple(sections)
