import re
from dataclasses import dataclass
from hashlib import sha256
from math import ceil


@dataclass(frozen=True, slots=True)
class EditorialRagChunk:
    section_id: str
    ordinal: int
    heading: str
    content: str
    content_hash: str
    token_count: int


_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_NON_SLUG = re.compile(r"[^a-z0-9]+")


def chunk_editorial_markdown(
    title: str, summary: str, body_markdown: str, *, max_chars: int = 2600
) -> tuple[EditorialRagChunk, ...]:
    """Create deterministic, bounded chunks from reviewed editorial Markdown."""
    if max_chars < 500:
        raise ValueError("editorial RAG chunks must allow at least 500 characters")

    sections: list[tuple[str, str]] = []
    heading = title.strip()
    paragraphs: list[str] = [summary.strip()]
    for block in re.split(r"\n\s*\n", body_markdown.strip()):
        cleaned = block.strip()
        if not cleaned:
            continue
        match = _HEADING.match(cleaned)
        if match:
            if paragraphs:
                sections.append((heading, "\n\n".join(paragraphs)))
            heading = match.group(2).strip()
            paragraphs = []
        else:
            paragraphs.append(cleaned)
    if paragraphs:
        sections.append((heading, "\n\n".join(paragraphs)))

    chunks: list[EditorialRagChunk] = []
    for section_heading, section_text in sections:
        pieces = _bounded_pieces(section_text, max_chars=max_chars)
        section_id = _slug(section_heading) or f"section-{len(chunks) + 1}"
        for piece in pieces:
            ordinal = len(chunks)
            content = piece.strip()
            chunks.append(
                EditorialRagChunk(
                    section_id=section_id,
                    ordinal=ordinal,
                    heading=section_heading,
                    content=content,
                    content_hash=sha256(content.encode()).hexdigest(),
                    token_count=max(1, ceil(len(content) / 4)),
                )
            )
    return tuple(chunks)


def _bounded_pieces(text: str, *, max_chars: int) -> list[str]:
    paragraphs = [part.strip() for part in text.split("\n\n") if part.strip()]
    pieces: list[str] = []
    current = ""
    for paragraph in paragraphs:
        segments = [
            paragraph[index : index + max_chars] for index in range(0, len(paragraph), max_chars)
        ]
        for segment in segments:
            candidate = f"{current}\n\n{segment}".strip() if current else segment
            if current and len(candidate) > max_chars:
                pieces.append(current)
                current = segment
            else:
                current = candidate
    if current:
        pieces.append(current)
    return pieces


def _slug(value: str) -> str:
    return _NON_SLUG.sub("-", value.lower()).strip("-")[:160]
