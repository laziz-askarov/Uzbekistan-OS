from collections.abc import Mapping

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.retrieval.planning import RetrievalPlan
from app.retrieval.service import RankedCandidate, RetrievalCandidate, RetrievalError

_TEXT_SEARCH_CONFIG = {
    "en": "english",
    "ru": "russian",
    "uz": "simple",
}

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
    COALESCE((version.content ->> 'authority_priority')::integer, 0)
      AS authority_priority,
    COALESCE((version.content ->> 'manual_correction')::boolean, false)
      AS manual_correction,
    version.content ->> 'topic' AS topic,
    r.title,
    r.summary,
    r.section_id,
    r.ordinal,
    r.content,
    chunk.content_hash,
    r.attributes,
    COALESCE(
        (
            SELECT jsonb_agg(
                jsonb_build_object(
                    'source_id', source.id::text,
                    'source_url', source.url,
                    'source_title', source.title,
                    'reviewed_at', source.last_verified_at
                )
                ORDER BY source.id
            )
            FROM knowledge.document_sources AS source_link
            JOIN knowledge.sources AS source ON source.id = source_link.source_id
            WHERE source_link.document_version_id = r.document_version_id
        ),
        '[]'::jsonb
    ) AS source_catalog,
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
ORDER BY authority_priority DESC, raw_score DESC, r.ordinal, r.chunk_id
LIMIT :limit
"""

LEXICAL_SEARCH_SQL = _COMMON_SELECT.format(
    score_expression=(
        "ts_rank_cd(to_tsvector(CAST(:text_search_config AS regconfig), r.title || ' ' || "
        "COALESCE(version.content ->> 'topic', '') || ' ' || r.content), "
        "websearch_to_tsquery(CAST(:text_search_config AS regconfig), :query))"
    ),
    extra_join="",
    eligible_source_clause=_ELIGIBLE_SOURCE_CLAUSE,
    extra_where=(
        "AND to_tsvector(CAST(:text_search_config AS regconfig), r.title || ' ' || "
        "COALESCE(version.content ->> 'topic', '') || ' ' || r.content) "
        "@@ websearch_to_tsquery(CAST(:text_search_config AS regconfig), :query)"
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

EDITORIAL_LEXICAL_SEARCH_SQL = """
SELECT
    chunk.id AS chunk_id,
    post.id AS document_id,
    version.id AS document_version_id,
    post.slug::text AS document_slug,
    domain.slug::text AS domain,
    language.code::text AS language,
    domain.risk_level,
    (
        SELECT max(source.trust_tier)
        FROM content.post_sources AS source_link
        JOIN knowledge.sources AS source ON source.id = source_link.source_id
        WHERE source_link.post_version_id = version.id
    ) AS source_trust_tier,
    0 AS authority_priority,
    false AS manual_correction,
    version.structured_content ->> 'topic' AS topic,
    version.title,
    version.summary,
    chunk.section_id,
    chunk.ordinal,
    chunk.content,
    chunk.content_hash,
    jsonb_build_object(
        'heading', chunk.heading,
        'citations', COALESCE(
            (
                SELECT jsonb_agg(
                    jsonb_build_object(
                        'source_id', source_link.source_id::text,
                        'locator', source_link.locator,
                        'quote', source_link.quote
                    ) ORDER BY source_link.sort_order, source_link.id
                )
                FROM content.post_sources AS source_link
                WHERE source_link.post_version_id = version.id
            ),
            '[]'::jsonb
        )
    ) AS attributes,
    COALESCE(
        (
            SELECT jsonb_agg(
                jsonb_build_object(
                    'source_id', source.id::text,
                    'source_url', source.url,
                    'source_title', source.title,
                    'reviewed_at', source.last_verified_at
                ) ORDER BY source_link.sort_order, source.id
            )
            FROM content.post_sources AS source_link
            JOIN knowledge.sources AS source ON source.id = source_link.source_id
            WHERE source_link.post_version_id = version.id
        ),
        '[]'::jsonb
    ) AS source_catalog,
    COALESCE(
        version.structured_content -> 'applicability' -> 'audiences',
        version.structured_content -> 'audiences',
        '[]'::jsonb
    ) AS audiences,
    COALESCE(
        version.structured_content -> 'applicability' -> 'nationalities',
        '[]'::jsonb
    ) AS nationalities,
    COALESCE(
        version.structured_content -> 'applicability' -> 'residency_statuses',
        '[]'::jsonb
    ) AS residency_statuses,
    COALESCE(
        version.structured_content -> 'applicability' -> 'locations',
        '[]'::jsonb
    ) AS locations,
    ts_rank_cd(
        to_tsvector(
            CAST(:text_search_config AS regconfig),
            version.title || ' ' || version.summary || ' ' ||
            COALESCE(version.structured_content ->> 'topic', '') || ' ' || chunk.content
        ),
        websearch_to_tsquery(CAST(:text_search_config AS regconfig), :query)
    ) AS raw_score
FROM content.rag_chunks AS chunk
JOIN content.post_versions AS version ON version.id = chunk.post_version_id
JOIN content.posts AS post ON post.id = version.post_id
JOIN knowledge.domains AS domain ON domain.id = post.domain_id
JOIN geography.languages AS language ON language.id = post.language_id
WHERE post.status = 'published'
  AND version.status = 'published'
  AND post.published_version_id = version.id
  AND version.include_in_rag = true
  AND version.review_due_at >= now()
  AND domain.is_active = true
  AND language.is_active = true
  AND lower(language.code::text) = :language
  AND lower(domain.slug::text) = ANY(CAST(:domains AS text[]))
  AND EXISTS (
      SELECT 1
      FROM content.post_sources AS eligible_link
      JOIN knowledge.sources AS eligible_source ON eligible_source.id = eligible_link.source_id
      JOIN knowledge.source_organizations AS eligible_org
        ON eligible_org.id = eligible_source.organization_id
      WHERE eligible_link.post_version_id = version.id
        AND eligible_source.is_active = true
        AND eligible_source.crawl_policy IN ('allowed', 'manual_only')
        AND eligible_org.is_active = true
        AND eligible_org.is_official = true
  )
  AND NOT EXISTS (
      SELECT 1
      FROM content.post_sources AS blocked_link
      JOIN knowledge.sources AS blocked_source ON blocked_source.id = blocked_link.source_id
      JOIN knowledge.source_organizations AS blocked_org
        ON blocked_org.id = blocked_source.organization_id
      WHERE blocked_link.post_version_id = version.id
        AND (
          blocked_source.is_active = false
          OR blocked_source.crawl_policy NOT IN ('allowed', 'manual_only')
          OR blocked_org.is_active = false
          OR blocked_org.is_official = false
        )
  )
  AND to_tsvector(
      CAST(:text_search_config AS regconfig),
      version.title || ' ' || version.summary || ' ' ||
      COALESCE(version.structured_content ->> 'topic', '') || ' ' || chunk.content
  ) @@ websearch_to_tsquery(CAST(:text_search_config AS regconfig), :query)
ORDER BY raw_score DESC, chunk.ordinal, chunk.id
LIMIT :limit
"""


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
        parameters = {
            "query": " OR ".join(plan.query_terms),
            "text_search_config": _TEXT_SEARCH_CONFIG[plan.language.value],
            "language": plan.language.value,
            "domains": plan.domains,
            "limit": limit,
        }
        official_rows = self.session.execute(
            text(LEXICAL_SEARCH_SQL),
            parameters,
        ).mappings()
        editorial_rows = self.session.execute(
            text(EDITORIAL_LEXICAL_SEARCH_SQL), parameters
        ).mappings()
        ranked = [self._ranked(row) for row in (*official_rows, *editorial_rows)]
        ranked.sort(
            key=lambda item: (
                -item.candidate.authority_priority,
                -item.score,
                item.candidate.ordinal,
                str(item.candidate.chunk_id),
            )
        )
        return tuple(ranked[:limit])

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
        source_catalog = row.get("source_catalog")
        source_catalog = source_catalog if isinstance(source_catalog, list) else []
        source_by_id = {
            str(item.get("source_id")): item
            for item in source_catalog
            if isinstance(item, dict) and item.get("source_id")
        }
        enriched_citations = []
        for citation in citations:
            if not isinstance(citation, dict):
                continue
            source = source_by_id.get(str(citation.get("source_id")), {})
            enriched_citations.append(
                {
                    **citation,
                    "source_url": source.get("source_url"),
                    "source_title": source.get("source_title"),
                    "reviewed_at": source.get("reviewed_at"),
                }
            )
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
                authority_priority=int(row.get("authority_priority") or 0),
                manual_correction=bool(row.get("manual_correction")),
                topic=(str(row["topic"]) if row.get("topic") else None),
                source_ids=[
                    item
                    for item in (
                        SqlAlchemyRetrievalRepository._uuid(item.get("source_id"))
                        for item in source_catalog
                        if isinstance(item, dict)
                    )
                    if item is not None
                ],
                title=str(row["title"]),
                summary=str(row["summary"]),
                section_id=str(row["section_id"]),
                heading=str(attributes.get("heading") or row["section_id"]),
                ordinal=int(row["ordinal"]),
                content=str(row["content"]),
                content_hash=str(row["content_hash"]),
                citations=enriched_citations,
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

    @staticmethod
    def _uuid(value: object):
        from uuid import UUID

        try:
            return UUID(str(value))
        except (TypeError, ValueError):
            return None
