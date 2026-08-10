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

    assert "websearch_to_tsquery" in LEXICAL_SEARCH_SQL
    assert "embedding.model_key = :model_key" in VECTOR_SEARCH_SQL
    assert "<=> CAST(:query_vector AS vector)" in VECTOR_SEARCH_SQL


def test_vector_literal_is_deterministic_and_not_sql_syntax() -> None:
    assert (
        SqlAlchemyRetrievalRepository._vector_literal([0.1, -2.5, 3.0])
        == "[0.10000000000000001,-2.5,3]"
    )
