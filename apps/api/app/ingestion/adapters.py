import json
from collections.abc import Mapping
from hashlib import sha256
from html.parser import HTMLParser
from re import sub
from typing import Protocol

from app.ingestion.errors import IngestionError
from app.ingestion.extractors import structured_html_sections
from app.ingestion.models import SourceRegistryEntry
from app.ingestion.normalizers import HTML_MEDIA_TYPES, normalize_response
from app.ingestion.types import FetchResponse, NormalizedContent

JSON_MEDIA_TYPES = {"application/json", "application/ld+json"}


class SourceAdapter(Protocol):
    def normalize(
        self,
        source: SourceRegistryEntry,
        response: FetchResponse,
        *,
        max_pdf_pages: int,
        max_characters: int,
    ) -> NormalizedContent: ...


class GenericSourceAdapter:
    def normalize(
        self,
        source: SourceRegistryEntry,
        response: FetchResponse,
        *,
        max_pdf_pages: int,
        max_characters: int,
    ) -> NormalizedContent:
        del source
        return normalize_response(
            response,
            max_pdf_pages=max_pdf_pages,
            max_normalized_characters=max_characters,
        )


class GovUzActivityHtmlAdapter:
    """Keep the reviewed GOV.UZ article and discard shared navigation/footer chrome."""

    _STOP_HEADINGS = frozenset(
        {
            "foydali havolalar",
            "biz ijtimoiy tarmoqlarda",
            "bog'lanish",
        }
    )

    def normalize(
        self,
        source: SourceRegistryEntry,
        response: FetchResponse,
        *,
        max_pdf_pages: int,
        max_characters: int,
    ) -> NormalizedContent:
        del max_pdf_pages
        media_type = _media_type(response)
        if media_type not in HTML_MEDIA_TYPES:
            raise IngestionError(
                "source_content_type_mismatch",
                "GOV.UZ activity adapter requires an HTML response",
                retryable=False,
            )
        raw_sections = structured_html_sections(response.body)
        title_tokens = _tokens(source.title.replace("(Uzbek)", ""))
        start = next(
            (
                index
                for index, (heading, _) in enumerate(raw_sections)
                if title_tokens and title_tokens.issubset(_tokens(heading))
            ),
            None,
        )
        if start is None:
            raise IngestionError(
                "source_structure_changed",
                "the approved GOV.UZ article heading was not found",
                retryable=False,
            )
        selected: list[tuple[str, str]] = []
        for heading, body in raw_sections[start:]:
            if selected and heading.casefold().strip() in self._STOP_HEADINGS:
                break
            selected.append((heading, body))
        return _normalized_sections(selected, media_type=media_type, max_characters=max_characters)


class _FragmentTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        if tag in {"br", "li", "p", "div"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"li", "p", "div"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


class EVisaUzbekLocalizationAdapter:
    """Extract reviewed Uzbek guidance from the official e-visa localization payload."""

    _SECTION_KEYS = (
        (
            "Elektron viza haqida",
            ("ABOUT_EVISA_P1",),
        ),
        (
            "Veb-saytdan foydalanish",
            (
                "ABOUT_WEBSITE_P1",
                "ABOUT_WEBSITE_P1_1",
                "ABOUT_WEBSITE_P1_2",
                "ABOUT_WEBSITE_P1_3",
                "ABOUT_WEBSITE_P1_4",
                "ABOUT_WEBSITE_P1_5",
                "ABOUT_WEBSITE_P1_6",
                "ABOUT_WEBSITE_P2",
            ),
        ),
    )

    def normalize(
        self,
        source: SourceRegistryEntry,
        response: FetchResponse,
        *,
        max_pdf_pages: int,
        max_characters: int,
    ) -> NormalizedContent:
        del source, max_pdf_pages
        media_type = _media_type(response)
        if media_type not in JSON_MEDIA_TYPES:
            raise IngestionError(
                "source_content_type_mismatch",
                "e-visa localization adapter requires a JSON response",
                retryable=False,
            )
        try:
            payload = json.loads(response.body.decode("utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise IngestionError(
                "invalid_source_json",
                "official e-visa localization payload is not valid JSON",
                retryable=False,
            ) from error
        if not isinstance(payload, dict):
            raise IngestionError(
                "invalid_source_json",
                "official e-visa localization payload must be a JSON object",
                retryable=False,
            )
        sections: list[tuple[str, str]] = []
        for heading, keys in self._SECTION_KEYS:
            values = [_fragment_text(payload.get(key)) for key in keys]
            body = "\n".join(value for value in values if value)
            if body:
                sections.append((heading, body))
        if len(sections) != len(self._SECTION_KEYS):
            raise IngestionError(
                "source_structure_changed",
                "required e-visa guidance fields are missing",
                retryable=False,
            )
        return _normalized_sections(sections, media_type=media_type, max_characters=max_characters)


class SourceAdapterRegistry:
    def __init__(self, adapters: Mapping[str, SourceAdapter] | None = None) -> None:
        defaults: dict[str, SourceAdapter] = {
            "generic-html": GenericSourceAdapter(),
            "generic-pdf": GenericSourceAdapter(),
            "generic-manual": GenericSourceAdapter(),
            "govuz-activity-html": GovUzActivityHtmlAdapter(),
            "evisa-uz-localization-json": EVisaUzbekLocalizationAdapter(),
        }
        if adapters:
            defaults.update(adapters)
        self._adapters = defaults

    def resolve(self, key: str) -> SourceAdapter:
        adapter = self._adapters.get(key)
        if adapter is None:
            raise IngestionError(
                "source_adapter_unavailable",
                f"no approved source adapter is registered for {key!r}",
                retryable=False,
            )
        return adapter


def _media_type(response: FetchResponse) -> str:
    return (response.header("content-type") or "").split(";", 1)[0].strip().casefold()


def _tokens(value: str) -> set[str]:
    return set(sub(r"[^\w]+", " ", value.casefold()).split())


def _fragment_text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    parser = _FragmentTextParser()
    parser.feed(value)
    parser.close()
    lines = [sub(r"\s+", " ", line).strip() for line in "".join(parser.parts).splitlines()]
    return "\n".join(line for line in lines if line)


def _normalized_sections(
    sections: list[tuple[str, str]],
    *,
    media_type: str,
    max_characters: int,
) -> NormalizedContent:
    text = "\n\n".join(f"{heading}\n{body}" for heading, body in sections)
    if not text:
        raise IngestionError(
            "empty_normalized_content",
            "source adapter did not extract any reviewed content",
            retryable=False,
        )
    if len(text) > max_characters:
        raise IngestionError(
            "normalized_content_too_large",
            f"normalized source exceeds {max_characters} characters",
            retryable=False,
        )
    return NormalizedContent(
        text=text,
        sha256=sha256(text.encode("utf-8")).hexdigest(),
        media_type=media_type,
        sections=tuple(sections),
    )
