from uuid import uuid4

from app.knowledge.chunking import chunk_sections
from app.knowledge.publication import CandidateCitation, CandidateSection


def section(section_id: str, body: str) -> CandidateSection:
    return CandidateSection(
        id=section_id,
        heading=section_id.title(),
        body=body,
        citations=[
            CandidateCitation(
                source_id=uuid4(),
                locator=f"{section_id} source section",
            )
        ],
    )


def test_semantic_chunker_preserves_heading_order_and_citation_provenance() -> None:
    chunks = chunk_sections(
        [
            section("requirements", "First complete concept.\n\nSecond complete concept."),
            section("deadline", "Apply before the stated deadline."),
        ],
        max_characters=200,
    )

    assert [chunk.section_id for chunk in chunks] == ["requirements", "deadline"]
    assert [chunk.ordinal for chunk in chunks] == [0, 1]
    assert chunks[0].content == "First complete concept.\n\nSecond complete concept."
    assert chunks[0].attributes["heading"] == "Requirements"
    assert chunks[0].attributes["citations"][0]["locator"] == (
        "requirements source section"
    )


def test_semantic_chunker_never_crosses_sections_or_size_boundaries() -> None:
    long_paragraphs = "\n\n".join(["word " * 32 for _ in range(4)])
    chunks = chunk_sections([section("steps", long_paragraphs)], max_characters=200)

    assert len(chunks) == 4
    assert all(chunk.section_id == "steps" for chunk in chunks)
    assert all(len(chunk.content) <= 200 for chunk in chunks)
    assert all(chunk.attributes["fragment_count"] == 4 for chunk in chunks)
    assert len({chunk.content_hash for chunk in chunks}) == 1
