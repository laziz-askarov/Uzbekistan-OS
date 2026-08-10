from collections.abc import Mapping

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.retrieval.planning import RetrievalPlan
from app.retrieval.service import RankedCandidate, RetrievalCandidate, RetrievalError

_ELIGIBLE_SOURCE_CLAUSE = """
EXISTS (
    SELECT 1
    FROM knowledge.document_sources AS eligible_ds
    JOIN knowledge.sources AS eligible_s ON eligible_s.id = eligible_ds.source_id
    JOIN knowledge.source_organizations AS eligible_o
      ON eligible_o.id = eligible_s.organization_id
    WHERE eligible_ds.document_version_id = r.document_version_id
      AND eligible_s.is_active = true
      AND eligible_s.crawl_policy IN ('allowed', 'manual_only')
      AND eligible_o.is_active = true
      AND eligible_o.is_official = true
)
AND NOT EXISTS (
    SELECT 1
    FROM knowledge.document_sources AS blocked_ds
    JOIN knowledge.sources AS blocked_s ON blocked_s.id = blocked_ds.source_id
    JOIN knowledge.source_organizations AS blocked_o
      ON blocked_o.id = blocked_s.organization_id
    WHERE blocked_ds.document_version_id = r.document_version_id
      AND (
        blocked_s.is_active = false
        OR blocked_s.crawl_policy NOT IN ('allowed', 'manual_only')
        OR blocked_o.is_active = false
        OR blocked_o.is_official = false
      )
)
"""

_COMMON_SELECT = """
SELECT
    r.chunk_id,
    r.document_id,
    r.document_version_id,
    r.document_slug,
    domain.slug::text AS domain,
    language.code::text AS language,
    domain.risk_level,
    (
        SELECT max(source.trust_tier)
        FROM knowledge.document_sources AS source_link
        JOIN knowledge.sources AS source ON source.id = source_link.source_id
        WHERE source_link.document_version_id = r.document_version_id
    ) AS source_trust_tier,
    r.title,
    r.summary,
    r.section_id,
    r.ordinal,
    r.content,
    chunk.content_hash,
    r.attributes,
    COALESCE(
        version.content -> 'applicability' -> 'audiences',
        version.content -> 'audiences',
        '[]'::jsonb
    ) AS audiences,
    COALESCE(version.content -> 'applicability' -> 'nationalities', '[]'::jsonb)
      AS nationalities,
    COALESCE(version.content -> 'applicability' -> 'residency_statuses', '[]'::jsonb)
      AS residency_statuses,
    COALESCE(version.content -> 'applicability' -> 'locations', '[]'::jsonb) AS locations,
    {score_expression} AS raw_score
FROM knowledge.retrievable_chunks AS r
JOIN knowledge.chunks AS chunk ON chunk.id = r.chunk_id
JOIN knowledge.document_versions AS version ON version.id = r.document_version_id
JOIN knowledge.domains AS domain ON domain.id = r.domain_id
JOIN geography.languages AS language ON language.id = r.language_id
{extra_join}
WHERE lower(language.code::text) = :language
  AND lower(domain.slug::text) = ANY(CAST(:domains AS text[]))
  AND {eligible_source_clause}
  {extra_where}
ORDER BY raw_score DESC, r.ordinal, r.chunk_id
LIMIT :limit
"""

LEXICAL_SEARCH_SQL = _COMMON_SELECT.format(
    score_expression=(
        "ts_rank_cd(to_tsvector('simple', r.title || ' ' || r.content), "
        "websearch_to_tsquery('simple', :query))"
    ),
    extra_join="",
    eligible_source_clause=_ELIGIBLE_SOURCE_CLAUSE,
    extra_where=(
        "AND to_tsvector('simple', r.title || ' ' || r.content) "
        "@@ websearch_to_tsquery('simple', :query)"
    ),
)

VECTOR_SEARCH_SQL = _COMMON_SELECT.format(
    score_expression="1 - (embedding.vector <=> CAST(:query_vector AS vector))",
    extra_join=(
        "JOIN knowledge.embeddings AS embedding ON embedding.chunk_id = r.chunk_id "
        "AND embedding.model_key = :model_key"
    ),
    eligible_source_clause=_ELIGIBLE_SOURCE_CLAUSE,
    extra_where="",
)


class SqlAlchemyRetrievalRepository:
    """Query only the retrieval-eligibility view and currently supported sources."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def search_lexical(
        self,
        plan: RetrievalPlan,
        *,
        limit: int,
    ) -> tuple[RankedCandidate, ...]:
        rows = self.session.execute(
            text(LEXICAL_SEARCH_SQL),
            {
                "query": plan.normalized_query,
                "language": plan.language.value,
                "domains": plan.domains,
                "limit": limit,
            },
        ).mappings()
        return tuple(self._ranked(row) for row in rows)

    def search_vector(
        self,
        plan: RetrievalPlan,
        query_vector: list[float],
        *,
        model_key: str,
        limit: int,
    ) -> tuple[RankedCandidate, ...]:
        rows = self.session.execute(
            text(VECTOR_SEARCH_SQL),
            {
                "query_vector": self._vector_literal(query_vector),
                "model_key": model_key,
                "language": plan.language.value,
                "domains": plan.domains,
                "limit": limit,
            },
        ).mappings()
        return tuple(self._ranked(row) for row in rows)

    @staticmethod
    def _ranked(row: Mapping[str, object]) -> RankedCandidate:
        attributes = row.get("attributes")
        if not isinstance(attributes, dict):
            raise RetrievalError(
                "invalid_chunk_attributes",
                "retrieved chunk attributes are not a JSON object",
            )
        citations = attributes.get("citations")
        if not isinstance(citations, list):
            citations = []
        return RankedCandidate(
            candidate=RetrievalCandidate(
                chunk_id=row["chunk_id"],
                document_id=row["document_id"],
                document_version_id=row["document_version_id"],
                document_slug=str(row["document_slug"]),
                domain=str(row["domain"]).lower(),
                language=str(row["language"]).lower(),
                risk_level=str(row["risk_level"]),
                source_trust_tier=int(row["source_trust_tier"]),
                title=str(row["title"]),
                summary=str(row["summary"]),
                section_id=str(row["section_id"]),
                heading=str(attributes.get("heading") or row["section_id"]),
                ordinal=int(row["ordinal"]),
                content=str(row["content"]),
                content_hash=str(row["content_hash"]),
                citations=citations,
                audiences=SqlAlchemyRetrievalRepository._string_list(row.get("audiences")),
                nationalities=SqlAlchemyRetrievalRepository._string_list(row.get("nationalities")),
                residency_statuses=SqlAlchemyRetrievalRepository._string_list(
                    row.get("residency_statuses")
                ),
                locations=SqlAlchemyRetrievalRepository._string_list(row.get("locations")),
            ),
            score=float(row["raw_score"]),
        )

    @staticmethod
    def _string_list(value: object) -> list[str]:
        return [str(item) for item in value] if isinstance(value, list) else []

    @staticmethod
    def _vector_literal(vector: list[float]) -> str:
        return "[" + ",".join(format(value, ".17g") for value in vector) + "]"
