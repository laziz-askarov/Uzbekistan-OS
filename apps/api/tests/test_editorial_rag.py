import pytest

from app.content.rag import chunk_editorial_markdown


def test_editorial_markdown_chunks_are_bounded_deterministic_and_hashed() -> None:
    body = (
        "# Fees\n\n" + ("Current official fee details. " * 60) + "\n\n# Timing\n\nAllow five days."
    )

    first = chunk_editorial_markdown("Visitor guide", "Reviewed summary.", body, max_chars=600)
    second = chunk_editorial_markdown("Visitor guide", "Reviewed summary.", body, max_chars=600)

    assert first == second
    assert len(first) >= 3
    assert [chunk.ordinal for chunk in first] == list(range(len(first)))
    assert all(0 < len(chunk.content) <= 600 for chunk in first)
    assert all(len(chunk.content_hash) == 64 for chunk in first)
    assert {chunk.heading for chunk in first} >= {"Visitor guide", "Fees", "Timing"}


def test_editorial_chunk_size_has_a_safe_minimum() -> None:
    with pytest.raises(ValueError, match="at least 500"):
        chunk_editorial_markdown("Title", "Summary", "Body", max_chars=100)
