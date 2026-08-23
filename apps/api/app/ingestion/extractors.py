from html.parser import HTMLParser
from re import sub
from typing import ClassVar
from unicodedata import normalize

from app.ingestion.artifacts import ExtractedSection, ExtractionArtifact
from app.ingestion.errors import IngestionError
from app.ingestion.models import SourceRegistryEntry
from app.ingestion.normalizers import HTML_MEDIA_TYPES, TEXT_MEDIA_TYPES
from app.ingestion.types import FetchResponse, NormalizedContent, SnapshotMetadata


class _StructuredHTMLParser(HTMLParser):
    _HEADING_TAGS: ClassVar[frozenset[str]] = frozenset({"h1", "h2", "h3", "h4", "h5", "h6"})
    _IGNORED_TAGS: ClassVar[frozenset[str]] = frozenset(
        {"noscript", "script", "style", "svg", "template"}
    )
    _BLOCK_TAGS: ClassVar[frozenset[str]] = frozenset(
        {"article", "br", "div", "li", "main", "p", "section", "table", "td", "th", "tr"}
    )

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._ignored_depth = 0
        self._heading_depth = 0
        self._heading_parts: list[str] = []
        self._body_parts: list[str] = []
        self._heading = "Overview"
        self.sections: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        if tag in self._IGNORED_TAGS:
            self._ignored_depth += 1
        elif not self._ignored_depth and tag in self._HEADING_TAGS:
            self._flush_section()
            self._heading_depth += 1
            self._heading_parts = []
        elif not self._ignored_depth and tag in self._BLOCK_TAGS:
            self._body_parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self._IGNORED_TAGS:
            self._ignored_depth = max(0, self._ignored_depth - 1)
        elif not self._ignored_depth and tag in self._HEADING_TAGS:
            self._heading_depth = max(0, self._heading_depth - 1)
            heading = _clean(" ".join(self._heading_parts))
            self._heading = heading or "Untitled section"
        elif not self._ignored_depth and tag in self._BLOCK_TAGS:
            self._body_parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._ignored_depth:
            return
        if self._heading_depth:
            self._heading_parts.append(data)
        else:
            self._body_parts.append(data)

    def close(self) -> None:
        super().close()
        self._flush_section()

    def _flush_section(self) -> None:
        body = _clean("".join(self._body_parts))
        if body:
            self.sections.append((self._heading, body))
        self._body_parts = []


def _clean(value: str) -> str:
    lines = [sub(r"\s+", " ", line).strip() for line in value.splitlines()]
    return "\n".join(line for line in lines if line)


def _section_id(heading: str, ordinal: int, used: set[str]) -> str:
    ascii_heading = normalize("NFKD", heading).encode("ascii", "ignore").decode().casefold()
    candidate = sub(r"[^a-z0-9]+", "-", ascii_heading).strip("-") or f"section-{ordinal}"
    base = candidate
    suffix = 2
    while candidate in used:
        candidate = f"{base}-{suffix}"
        suffix += 1
    used.add(candidate)
    return candidate


def extract_artifact(
    source: SourceRegistryEntry,
    snapshot: SnapshotMetadata,
    response: FetchResponse,
    normalized_content: NormalizedContent,
    *,
    adapter_key: str | None = None,
    topic: str | None = None,
) -> ExtractionArtifact:
    media_type = normalized_content.media_type
    if normalized_content.sections:
        raw_sections = list(normalized_content.sections)
    elif media_type in HTML_MEDIA_TYPES:
        parser = _StructuredHTMLParser()
        parser.feed(response.body.decode("utf-8", errors="replace"))
        parser.close()
        raw_sections = parser.sections
    elif media_type in TEXT_MEDIA_TYPES:
        raw_sections = [("Content", normalized_content.text)]
    else:
        raise IngestionError(
            "unsupported_extractor",
            f"no structured extractor is registered for {media_type}",
            retryable=False,
        )

    if not raw_sections:
        raw_sections = [("Content", normalized_content.text)]

    used_ids: set[str] = set()
    sections = [
        ExtractedSection(
            id=_section_id(heading, ordinal, used_ids),
            heading=heading,
            body=body,
        )
        for ordinal, (heading, body) in enumerate(raw_sections, start=1)
    ]
    return ExtractionArtifact(
        source_id=source.id,
        snapshot_id=snapshot.id,
        adapter_key=adapter_key or source.adapter_key,
        media_type=media_type,
        topic=topic,
        raw_sha256=snapshot.sha256,
        normalized_sha256=normalized_content.sha256,
        extracted_at=snapshot.fetched_at,
        sections=sections,
    )


def structured_html_sections(body: bytes) -> tuple[tuple[str, str], ...]:
    """Extract heading-scoped sections for adapters that need source-specific filtering."""
    parser = _StructuredHTMLParser()
    parser.feed(body.decode("utf-8", errors="replace"))
    parser.close()
    return tuple(parser.sections)
