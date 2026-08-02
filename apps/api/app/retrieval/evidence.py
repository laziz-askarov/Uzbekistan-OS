from hashlib import sha256

from pydantic import BaseModel, ConfigDict, Field

from app.retrieval.service import CitationReference, RetrievalResult

_RETRIEVED_CONTROL_PATTERNS = (
    "<|system|>",
    "<|assistant|>",
    "ignore previous instructions",
    "ignore all previous instructions",
    "reveal the system prompt",
    "assistant:",
)


class EvidenceItem(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    chunk_id: str
    document_id: str
    document_version_id: str
    title: str
    heading: str
    content: str
    content_hash: str
    retrieval_score: float
    citations: list[CitationReference] = Field(min_length=1)


class EvidencePack(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    plan_fingerprint: str
    evidence_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    status: str
    reason: str | None
    total_characters: int = Field(ge=0)
    quarantined_chunk_ids: list[str]
    items: list[EvidenceItem]


class EvidencePackBuilder:
    def __init__(self, *, max_items: int = 6, max_characters: int = 9_000) -> None:
        if max_items < 1:
            raise ValueError("evidence item limit must be positive")
        if max_characters < 500:
            raise ValueError("evidence character limit must be at least 500")
        self.max_items = max_items
        self.max_characters = max_characters

    def build(self, result: RetrievalResult) -> EvidencePack:
        items: list[EvidenceItem] = []
        quarantined: list[str] = []
        seen_hashes: set[str] = set()
        total = 0
        for retrieved in result.items:
            candidate = retrieved.candidate
            chunk_id = str(candidate.chunk_id)
            if self._contains_control_pattern(candidate.content):
                quarantined.append(chunk_id)
                continue
            if not candidate.citations or candidate.content_hash in seen_hashes:
                continue
            if len(items) >= self.max_items or total + len(candidate.content) > self.max_characters:
                continue
            seen_hashes.add(candidate.content_hash)
            total += len(candidate.content)
            items.append(
                EvidenceItem(
                    chunk_id=chunk_id,
                    document_id=str(candidate.document_id),
                    document_version_id=str(candidate.document_version_id),
                    title=candidate.title,
                    heading=candidate.heading,
                    content=candidate.content,
                    content_hash=candidate.content_hash,
                    retrieval_score=retrieved.retrieval_score,
                    citations=candidate.citations,
                )
            )
        status = "sufficient" if items else "insufficient"
        reason = None
        if not items:
            reason = (
                "retrieved evidence was quarantined"
                if quarantined
                else "no eligible cited evidence matched the retrieval plan"
            )
        canonical = "|".join(
            [
                result.plan_fingerprint,
                status,
                *[item.content_hash for item in items],
                *quarantined,
            ]
        )
        return EvidencePack(
            plan_fingerprint=result.plan_fingerprint,
            evidence_fingerprint=sha256(canonical.encode()).hexdigest(),
            status=status,
            reason=reason,
            total_characters=total,
            quarantined_chunk_ids=quarantined,
            items=items,
        )

    @staticmethod
    def _contains_control_pattern(content: str) -> bool:
        normalized = content.casefold()
        return any(pattern in normalized for pattern in _RETRIEVED_CONTROL_PATTERNS)
