import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.retrieval.evidence import EvidenceItem, EvidencePack
from app.retrieval.planning import QueryLanguage, RetrievalRisk

_TOKEN_PATTERN = re.compile(r"[^\W_]+", flags=re.UNICODE)
_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "for",
    "is",
    "of",
    "the",
    "to",
    "with",
    "bu",
    "uchun",
    "va",
    "ham",
    "bir",
    "для",
    "это",
    "как",
    "и",
    "в",
    "на",
}


class ClaimCitation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    evidence_id: str = Field(min_length=1)
    quote: str = Field(min_length=3, max_length=2_000)


class GeneratedClaim(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(pattern=r"^claim-[a-z0-9-]{1,63}$")
    text: str = Field(min_length=3, max_length=2_000)
    citations: list[ClaimCitation] = Field(min_length=1, max_length=8)


class AnswerSection(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(pattern=r"^section-[a-z0-9-]{1,63}$")
    heading: str = Field(min_length=1, max_length=160)
    claims: list[GeneratedClaim] = Field(min_length=1, max_length=24)


class GroundedAnswer(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    status: Literal["answered", "insufficient"]
    language: QueryLanguage
    summary: str = Field(min_length=1, max_length=2_000)
    sections: list[AnswerSection] = Field(default_factory=list, max_length=12)
    next_recommended_flow: str | None = Field(default=None, max_length=120)

    @model_validator(mode="after")
    def validate_status_shape(self) -> "GroundedAnswer":
        if self.status == "answered" and not self.sections:
            raise ValueError("answered responses require at least one section")
        if self.status == "insufficient" and self.sections:
            raise ValueError("insufficient responses cannot include factual sections")
        claim_ids = [claim.id for section in self.sections for claim in section.claims]
        if len(claim_ids) != len(set(claim_ids)):
            raise ValueError("claim identifiers must be unique")
        return self

    @classmethod
    def safe_insufficiency(cls, language: QueryLanguage) -> "GroundedAnswer":
        messages = {
            QueryLanguage.EN: "I could not find enough current official evidence to answer safely.",
            QueryLanguage.UZ: "Xavfsiz javob berish uchun yetarli amaldagi rasmiy dalil topilmadi.",
            QueryLanguage.RU: (
                "Не удалось найти достаточно актуальных официальных данных "  # noqa: RUF001
                "для безопасного ответа."
            ),
        }
        return cls(status="insufficient", language=language, summary=messages[language])


class AnswerValidationIssue(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    code: str
    claim_id: str | None = None


class ValidatedAnswer(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    answer: GroundedAnswer
    accepted: bool
    issues: list[AnswerValidationIssue]


class GroundedAnswerValidator:
    def validate(
        self,
        *,
        answer: GroundedAnswer,
        evidence: EvidencePack,
        expected_language: QueryLanguage,
        risk: RetrievalRisk,
    ) -> ValidatedAnswer:
        issues: list[AnswerValidationIssue] = []
        if answer.language != expected_language:
            issues.append(AnswerValidationIssue(code="answer_language_mismatch"))
        if answer.status == "answered" and evidence.status != "sufficient":
            issues.append(AnswerValidationIssue(code="answer_without_sufficient_evidence"))

        evidence_by_id = {item.chunk_id: item for item in evidence.items}
        for section in answer.sections:
            for claim in section.claims:
                issues.extend(self._validate_claim(claim, evidence_by_id, risk))

        if issues:
            return ValidatedAnswer(
                answer=GroundedAnswer.safe_insufficiency(expected_language),
                accepted=False,
                issues=issues,
            )
        return ValidatedAnswer(answer=answer, accepted=True, issues=[])

    def _validate_claim(
        self,
        claim: GeneratedClaim,
        evidence_by_id: dict[str, EvidenceItem],
        risk: RetrievalRisk,
    ) -> list[AnswerValidationIssue]:
        issues: list[AnswerValidationIssue] = []
        valid_quotes: list[str] = []
        for citation in claim.citations:
            evidence = evidence_by_id.get(citation.evidence_id)
            if evidence is None:
                issues.append(
                    AnswerValidationIssue(code="citation_evidence_unknown", claim_id=claim.id)
                )
                continue
            if self._normalized(citation.quote) not in self._normalized(evidence.content):
                issues.append(
                    AnswerValidationIssue(code="citation_quote_mismatch", claim_id=claim.id)
                )
                continue
            valid_quotes.append(citation.quote)
        if valid_quotes:
            threshold = 0.65 if risk is RetrievalRisk.HIGH else 0.45
            if self._lexical_coverage(claim.text, valid_quotes) < threshold:
                issues.append(AnswerValidationIssue(code="claim_not_supported", claim_id=claim.id))
        return issues

    @staticmethod
    def _normalized(value: str) -> str:
        return " ".join(value.casefold().split())

    @staticmethod
    def _meaningful_tokens(value: str) -> set[str]:
        return {
            token
            for token in _TOKEN_PATTERN.findall(value.casefold())
            if len(token) > 1 and token not in _STOPWORDS
        }

    def _lexical_coverage(self, claim: str, quotes: list[str]) -> float:
        claim_tokens = self._meaningful_tokens(claim)
        if not claim_tokens:
            return 0.0
        quote_tokens = self._meaningful_tokens(" ".join(quotes))
        return len(claim_tokens.intersection(quote_tokens)) / len(claim_tokens)
