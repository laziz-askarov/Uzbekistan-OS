from hashlib import sha256
from html.parser import HTMLParser
from io import BytesIO
from json import JSONDecodeError, dumps, loads
from re import sub
from typing import ClassVar

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.ingestion.errors import IngestionError
from app.ingestion.types import FetchResponse, NormalizedContent

HTML_MEDIA_TYPES = {"text/html", "application/xhtml+xml"}
TEXT_MEDIA_TYPES = {"text/plain", "text/xml", "application/xml", "application/rss+xml"}
PDF_MEDIA_TYPES = {"application/pdf"}
JSON_MEDIA_TYPES = {"application/json", "application/ld+json"}
MAX_JSON_DEPTH = 32
MAX_JSON_NODES = 50_000


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
    normalized_media_type = content_type
    sections: tuple[tuple[str, str], ...] = ()
    if content_type in HTML_MEDIA_TYPES:
        parser = _VisibleTextParser()
        parser.feed(response.body.decode("utf-8", errors="replace"))
        text = _clean_text("".join(parser.parts))
    elif content_type in TEXT_MEDIA_TYPES:
        text = _clean_text(response.body.decode("utf-8", errors="replace"))
    elif content_type in JSON_MEDIA_TYPES:
        sections = _extract_json_sections(
            response.body,
            max_characters=max_normalized_characters,
        )
        text = "\n\n".join(f"{heading}\n{body}" for heading, body in sections)
    elif content_type in PDF_MEDIA_TYPES:
        sections = _extract_pdf_sections(
            response.body,
            max_pages=max_pdf_pages,
            max_characters=max_normalized_characters,
        )
        text = "\n\n".join(body for _, body in sections)
        normalized_media_type = "text/markdown"
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
        media_type=normalized_media_type,
        sections=sections,
    )


class _DuplicateJsonKeyError(ValueError):
    pass


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateJsonKeyError(key)
        result[key] = value
    return result


def _extract_json_sections(
    body: bytes,
    *,
    max_characters: int,
) -> tuple[tuple[str, str], ...]:
    try:
        payload = loads(
            body.decode("utf-8-sig"),
            object_pairs_hook=_unique_json_object,
        )
    except UnicodeDecodeError as error:
        raise IngestionError(
            "invalid_json_encoding",
            "JSON source must use UTF-8 encoding",
            retryable=False,
        ) from error
    except _DuplicateJsonKeyError as error:
        raise IngestionError(
            "duplicate_json_key",
            f"JSON source contains a duplicate key: {error}",
            retryable=False,
        ) from error
    except JSONDecodeError as error:
        raise IngestionError(
            "invalid_json",
            "JSON source could not be parsed safely",
            retryable=False,
        ) from error

    if not isinstance(payload, (dict, list)):
        raise IngestionError(
            "invalid_json_root",
            "JSON source must contain an object or array at its root",
            retryable=False,
        )

    preferred_sections = _preferred_json_sections(payload)
    if preferred_sections:
        sections = preferred_sections
    else:
        entries = (
            list(payload.items())
            if isinstance(payload, dict)
            else list(enumerate(payload, 1))
        )
        sections_list: list[tuple[str, str]] = []
        node_count = [0]
        for key, value in entries:
            heading = str(key) if isinstance(payload, dict) else f"Item {key}"
            lines: list[str] = []
            _flatten_json_value(
                value,
                path="",
                lines=lines,
                depth=1,
                node_count=node_count,
            )
            section_body = "\n".join(lines).strip()
            if section_body:
                sections_list.append((heading.strip() or "Content", section_body))
        sections = tuple(sections_list)

    if not sections:
        raise IngestionError(
            "empty_normalized_content",
            "JSON source did not contain retrievable content",
            retryable=False,
        )
    character_count = sum(len(heading) + len(section_body) for heading, section_body in sections)
    if character_count > max_characters:
        raise IngestionError(
            "normalized_content_too_large",
            f"normalized source exceeds {max_characters} characters",
            retryable=False,
        )
    return sections


def _preferred_json_sections(
    payload: dict[str, object] | list[object],
) -> tuple[tuple[str, str], ...]:
    if not isinstance(payload, dict) or not isinstance(payload.get("sections"), list):
        return ()
    sections: list[tuple[str, str]] = []
    for item in payload["sections"]:
        if not isinstance(item, dict):
            return ()
        heading = item.get("heading")
        section_body = item.get("body")
        if not isinstance(heading, str) or not isinstance(section_body, str):
            return ()
        cleaned_heading = _clean_text(heading)
        cleaned_body = _clean_text(section_body)
        if not cleaned_heading or not cleaned_body:
            return ()
        sections.append((cleaned_heading, cleaned_body))
    return tuple(sections)


def _flatten_json_value(
    value: object,
    *,
    path: str,
    lines: list[str],
    depth: int,
    node_count: list[int],
) -> None:
    node_count[0] += 1
    if node_count[0] > MAX_JSON_NODES:
        raise IngestionError(
            "json_node_limit_exceeded",
            f"JSON source exceeds the {MAX_JSON_NODES} node limit",
            retryable=False,
        )
    if depth > MAX_JSON_DEPTH:
        raise IngestionError(
            "json_depth_limit_exceeded",
            f"JSON source exceeds the {MAX_JSON_DEPTH} level depth limit",
            retryable=False,
        )

    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else key
            _flatten_json_value(
                child,
                path=child_path,
                lines=lines,
                depth=depth + 1,
                node_count=node_count,
            )
        return
    if isinstance(value, list):
        for index, child in enumerate(value, start=1):
            child_path = f"{path}[{index}]" if path else f"Item {index}"
            _flatten_json_value(
                child,
                path=child_path,
                lines=lines,
                depth=depth + 1,
                node_count=node_count,
            )
        return

    label = path or "Value"
    rendered = value if isinstance(value, str) else dumps(value, ensure_ascii=False)
    cleaned = _clean_text(rendered)
    if cleaned:
        lines.append(f"{label}: {cleaned}")


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
            markdown = f"## Page {page_number}\n\n{text}"
            character_count += len(markdown)
            if character_count > max_characters:
                raise IngestionError(
                    "normalized_content_too_large",
                    f"normalized source exceeds {max_characters} characters",
                    retryable=False,
                )
            sections.append((f"Page {page_number}", markdown))
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
