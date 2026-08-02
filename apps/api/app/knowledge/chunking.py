from dataclasses import dataclass
from hashlib import sha256

from app.knowledge.publication import CandidateSection


@dataclass(frozen=True)
class SemanticChunk:
    section_id: str
    ordinal: int
    content: str
    content_hash: str
    token_count: int
    attributes: dict[str, object]


def chunk_sections(
    sections: list[CandidateSection],
    *,
    max_characters: int = 1800,
) -> tuple[SemanticChunk, ...]:
    """Chunk reviewed sections without crossing heading or citation boundaries."""
    if max_characters < 200:
        raise ValueError("semantic chunk size must be at least 200 characters")

    chunks: list[SemanticChunk] = []
    for section in sections:
        fragments = _section_fragments(section.body, max_characters=max_characters)
        for fragment_index, fragment in enumerate(fragments):
            attributes: dict[str, object] = {
                "heading": section.heading,
                "citations": [citation.model_dump(mode="json") for citation in section.citations],
                "fragment_index": fragment_index,
                "fragment_count": len(fragments),
            }
            chunks.append(
                SemanticChunk(
                    section_id=section.id,
                    ordinal=len(chunks),
                    content=fragment,
                    content_hash=sha256(fragment.encode()).hexdigest(),
                    token_count=len(fragment.split()),
                    attributes=attributes,
                )
            )
    return tuple(chunks)


def _section_fragments(body: str, *, max_characters: int) -> tuple[str, ...]:
    paragraphs = [paragraph.strip() for paragraph in body.split("\n\n") if paragraph.strip()]
    if not paragraphs:
        return (body.strip(),)

    units: list[str] = []
    for paragraph in paragraphs:
        if len(paragraph) <= max_characters:
            units.append(paragraph)
            continue
        units.extend(_split_oversized_paragraph(paragraph, max_characters=max_characters))

    fragments: list[str] = []
    current = ""
    for unit in units:
        candidate = unit if not current else f"{current}\n\n{unit}"
        if current and len(candidate) > max_characters:
            fragments.append(current)
            current = unit
        else:
            current = candidate
    if current:
        fragments.append(current)
    return tuple(fragments)


def _split_oversized_paragraph(paragraph: str, *, max_characters: int) -> list[str]:
    words = paragraph.split()
    fragments: list[str] = []
    current: list[str] = []
    current_size = 0
    for word in words:
        next_size = current_size + len(word) + (1 if current else 0)
        if current and next_size > max_characters:
            fragments.append(" ".join(current))
            current = [word]
            current_size = len(word)
        else:
            current.append(word)
            current_size = next_size
    if current:
        fragments.append(" ".join(current))
    return fragments
