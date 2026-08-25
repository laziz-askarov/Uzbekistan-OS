from unittest.mock import Mock

from app.retrieval.planning import QueryRequest, RetrievalPlanner
from app.retrieval.repositories import (
    LEXICAL_SEARCH_SQL,
    VECTOR_SEARCH_SQL,
    SqlAlchemyRetrievalRepository,
)


def test_retrieval_queries_use_eligibility_view_and_current_source_policy() -> None:
    for statement in (LEXICAL_SEARCH_SQL, VECTOR_SEARCH_SQL):
        assert "FROM knowledge.retrievable_chunks AS r" in statement
        assert "eligible_s.is_active = true" in statement
        assert "eligible_s.crawl_policy IN ('allowed', 'manual_only')" in statement
        assert "eligible_o.is_official = true" in statement
        assert "NOT EXISTS" in statement
        assert "language.code" in statement
        assert "domain.slug" in statement
        assert "source_catalog" in statement
        assert "source.last_verified_at" in statement

    assert "websearch_to_tsquery" in LEXICAL_SEARCH_SQL
    assert "CAST(:text_search_config AS regconfig)" in LEXICAL_SEARCH_SQL
    assert "version.content ->> 'topic'" in LEXICAL_SEARCH_SQL
    assert "embedding.model_key = :model_key" in VECTOR_SEARCH_SQL
    assert "<=> CAST(:query_vector AS vector)" in VECTOR_SEARCH_SQL


def test_vector_literal_is_deterministic_and_not_sql_syntax() -> None:
    assert (
        SqlAlchemyRetrievalRepository._vector_literal([0.1, -2.5, 3.0])
        == "[0.10000000000000001,-2.5,3]"
    )


def test_lexical_search_uses_meaningful_query_terms() -> None:
    session = Mock()
    session.execute.return_value.mappings.return_value = []
    plan = RetrievalPlanner().plan(
        QueryRequest(query="What are the overstay penalties?", language="en")
    )

    SqlAlchemyRetrievalRepository(session).search_lexical(plan, limit=20)

    parameters = session.execute.call_args.args[1]
    assert parameters["query"] == "overstay OR penalties"
    assert parameters["text_search_config"] == "english"


def test_repository_enriches_citations_with_current_official_source_metadata() -> None:
    row = {
        "chunk_id": "00000000-0000-0000-0000-000000000001",
        "document_id": "00000000-0000-0000-0000-000000000002",
        "document_version_id": "00000000-0000-0000-0000-000000000003",
        "document_slug": "evisa-uz",
        "domain": "immigration",
        "language": "uz",
        "risk_level": "high",
        "source_trust_tier": 1,
        "title": "Elektron viza",
        "summary": "Rasmiy yo'riqnoma",
        "section_id": "overview",
        "ordinal": 0,
        "content": "Rasmiy matn",
        "content_hash": "a" * 64,
        "attributes": {
            "heading": "Umumiy",
            "citations": [
                {
                    "source_id": "00000000-0000-0000-0000-000000002104",
                    "locator": "Elektron viza haqida",
                }
            ],
        },
        "source_catalog": [
            {
                "source_id": "00000000-0000-0000-0000-000000002104",
                "source_url": "https://e-visa.gov.uz/what-you-need-to-know",
                "source_title": "Elektron viza",
                "reviewed_at": "2026-08-21T00:00:00Z",
            }
        ],
        "audiences": [],
        "nationalities": [],
        "residency_statuses": [],
        "locations": [],
        "raw_score": 1,
    }

    ranked = SqlAlchemyRetrievalRepository._ranked(row)

    citation = ranked.candidate.citations[0]
    assert str(citation.source_url) == "https://e-visa.gov.uz/what-you-need-to-know"
    assert citation.source_title == "Elektron viza"
    assert citation.reviewed_at is not None
