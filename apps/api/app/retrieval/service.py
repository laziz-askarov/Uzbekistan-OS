from datetime import datetime
from math import isfinite
from typing import Protocol
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, model_validator

from app.retrieval.planning import RetrievalPlan


class RetrievalError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class CitationReference(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source_id: UUID
    locator: str = Field(min_length=1)
    quote: str | None = None
    source_url: AnyHttpUrl | None = None
    source_title: str | None = None
    reviewed_at: datetime | None = None


class RetrievalCandidate(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    chunk_id: UUID
    document_id: UUID
    document_version_id: UUID
    document_slug: str
    domain: str
    language: str
    risk_level: str
    source_trust_tier: int = Field(ge=1, le=3)
    authority_priority: int = Field(default=0, ge=0, le=100)
    manual_correction: bool = False
    topic: str | None = None
    source_ids: list[UUID] = Field(default_factory=list)
    title: str
    summary: str
    section_id: str
    heading: str
    ordinal: int = Field(ge=0)
    content: str = Field(min_length=1)
    content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    citations: list[CitationReference]
    audiences: list[str] = Field(default_factory=list)
    nationalities: list[str] = Field(default_factory=list)
    residency_statuses: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)


class RankedCandidate(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    candidate: RetrievalCandidate
    score: float

    @model_validator(mode="after")
    def validate_score(self) -> "RankedCandidate":
        if not isfinite(self.score):
            raise ValueError("candidate score must be finite")
        return self


class RetrievedChunk(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    candidate: RetrievalCandidate
    retrieval_score: float = Field(ge=0, le=1)
    lexical_rank: int | None = Field(default=None, ge=1)
    vector_rank: int | None = Field(default=None, ge=1)


class RetrievalResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    plan_fingerprint: str
    status: str
    items: list[RetrievedChunk]
    lexical_candidate_count: int = Field(ge=0)
    vector_candidate_count: int = Field(ge=0)


class RetrievalRepository(Protocol):
    def search_lexical(self, plan: RetrievalPlan, *, limit: int) -> tuple[RankedCandidate, ...]: ...

    def search_vector(
        self,
        plan: RetrievalPlan,
        query_vector: list[float],
        *,
        model_key: str,
        limit: int,
    ) -> tuple[RankedCandidate, ...]: ...


class HybridRetrievalService:
    def __init__(
        self,
        repository: RetrievalRepository,
        *,
        reciprocal_rank_constant: int = 60,
        lexical_weight: float = 0.55,
        vector_weight: float = 0.45,
    ) -> None:
        if reciprocal_rank_constant < 1:
            raise ValueError("reciprocal rank constant must be positive")
        if lexical_weight <= 0 or vector_weight <= 0:
            raise ValueError("retrieval weights must be positive")
        self.repository = repository
        self.rrf_constant = reciprocal_rank_constant
        self.lexical_weight = lexical_weight
        self.vector_weight = vector_weight

    def retrieve(
        self,
        plan: RetrievalPlan,
        *,
        query_vector: list[float] | None = None,
        model_key: str | None = None,
        limit: int = 8,
    ) -> RetrievalResult:
        if not 1 <= limit <= 50:
            raise RetrievalError("invalid_retrieval_limit", "retrieval limit must be 1 to 50")
        candidate_limit = min(max(limit * 4, 20), 100)
        lexical = self.repository.search_lexical(plan, limit=candidate_limit)
        vector: tuple[RankedCandidate, ...] = ()
        if query_vector is not None or model_key is not None:
            self._validate_vector_request(query_vector, model_key)
            vector = self.repository.search_vector(
                plan,
                query_vector or [],
                model_key=model_key or "",
                limit=candidate_limit,
            )

        fused = self._fuse(lexical, vector)
        filtered = [item for item in fused if self._matches_plan(item.candidate, plan)]
        filtered = self._prefer_manual_corrections(filtered)
        selected = filtered[:limit]
        return RetrievalResult(
            plan_fingerprint=plan.fingerprint,
            status="sufficient" if selected else "insufficient",
            items=selected,
            lexical_candidate_count=len(lexical),
            vector_candidate_count=len(vector),
        )

    def _fuse(
        self,
        lexical: tuple[RankedCandidate, ...],
        vector: tuple[RankedCandidate, ...],
    ) -> list[RetrievedChunk]:
        candidates: dict[UUID, RetrievalCandidate] = {}
        scores: dict[UUID, float] = {}
        lexical_ranks: dict[UUID, int] = {}
        vector_ranks: dict[UUID, int] = {}
        for rank, item in enumerate(lexical, 1):
            self._remember(candidates, item.candidate)
            lexical_ranks[item.candidate.chunk_id] = rank
            scores[item.candidate.chunk_id] = scores.get(item.candidate.chunk_id, 0) + (
                self.lexical_weight / (self.rrf_constant + rank)
            )
        for rank, item in enumerate(vector, 1):
            self._remember(candidates, item.candidate)
            vector_ranks[item.candidate.chunk_id] = rank
            scores[item.candidate.chunk_id] = scores.get(item.candidate.chunk_id, 0) + (
                self.vector_weight / (self.rrf_constant + rank)
            )
        maximum = (self.lexical_weight + self.vector_weight) / (self.rrf_constant + 1)
        return sorted(
            (
                RetrievedChunk(
                    candidate=candidate,
                    retrieval_score=min(scores[chunk_id] / maximum, 1.0),
                    lexical_rank=lexical_ranks.get(chunk_id),
                    vector_rank=vector_ranks.get(chunk_id),
                )
                for chunk_id, candidate in candidates.items()
            ),
            key=lambda item: (
                -item.candidate.authority_priority,
                -item.retrieval_score,
                item.candidate.ordinal,
                str(item.candidate.chunk_id),
            ),
        )

    @staticmethod
    def _prefer_manual_corrections(items: list[RetrievedChunk]) -> list[RetrievedChunk]:
        """Suppress stale evidence when a reviewed correction targets the same source."""
        corrected_source_ids = {
            source_id
            for item in items
            if item.candidate.manual_correction
            for source_id in item.candidate.source_ids
        }
        if not corrected_source_ids:
            return items
        return [
            item
            for item in items
            if item.candidate.manual_correction
            or corrected_source_ids.isdisjoint(item.candidate.source_ids)
        ]

    @staticmethod
    def _remember(
        candidates: dict[UUID, RetrievalCandidate],
        candidate: RetrievalCandidate,
    ) -> None:
        existing = candidates.get(candidate.chunk_id)
        if existing is not None and existing != candidate:
            raise RetrievalError(
                "candidate_lineage_conflict",
                "retrieval backends returned conflicting lineage for one chunk",
            )
        candidates[candidate.chunk_id] = candidate

    @staticmethod
    def _validate_vector_request(
        query_vector: list[float] | None,
        model_key: str | None,
    ) -> None:
        if not query_vector or not model_key or not model_key.strip():
            raise RetrievalError(
                "invalid_vector_request",
                "query vector and configured model key must be supplied together",
            )
        if any(not isfinite(value) for value in query_vector):
            raise RetrievalError(
                "invalid_query_vector",
                "query vector must contain only finite values",
            )

    @staticmethod
    def _matches_plan(candidate: RetrievalCandidate, plan: RetrievalPlan) -> bool:
        if candidate.language != plan.language.value:
            return False
        if candidate.domain not in plan.domains:
            return False
        if candidate.source_trust_tier not in plan.allowed_trust_tiers:
            return False
        context = plan.applicability
        if context.audience and candidate.audiences and context.audience not in candidate.audiences:
            return False
        if (
            context.nationality
            and candidate.nationalities
            and context.nationality not in candidate.nationalities
        ):
            return False
        if (
            context.residency_status
            and candidate.residency_statuses
            and context.residency_status not in candidate.residency_statuses
        ):
            return False
        return not (
            context.location and candidate.locations and context.location not in candidate.locations
        )
