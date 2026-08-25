import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.ai.state import ConversationField, ConversationState
from app.retrieval.evidence import EvidenceItem, EvidencePack
from app.retrieval.planning import QueryLanguage, RetrievalIntent, RetrievalRisk

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


class ContextUsedItem(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    field: ConversationField
    value: str = Field(min_length=1, max_length=240)
    source_message_id: str = Field(pattern=r"^message-[a-z0-9-]{1,80}$")


class ClarificationOption(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    value: str = Field(min_length=1, max_length=120)
    label: str = Field(min_length=1, max_length=160)


class ClarificationRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    field: ConversationField
    question: str = Field(min_length=3, max_length=500)
    reason: str = Field(min_length=3, max_length=500)
    response_type: Literal["single_choice", "text"]
    options: list[ClarificationOption] = Field(default_factory=list, max_length=8)

    @model_validator(mode="after")
    def validate_options(self) -> "ClarificationRequest":
        if self.response_type == "single_choice" and len(self.options) < 2:
            raise ValueError("single-choice clarification requires at least two options")
        if self.response_type == "text" and self.options:
            raise ValueError("text clarification cannot include fixed options")
        values = [option.value for option in self.options]
        if len(values) != len(set(values)):
            raise ValueError("clarification option values must be unique")
        return self


class AnswerLimitation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    code: Literal[
        "source_missing_detail",
        "applicability_uncertain",
        "source_conflict",
        "context_missing",
    ]
    message: str = Field(min_length=3, max_length=500)
    evidence_ids: list[str] = Field(default_factory=list, max_length=8)


class NextAction(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    type: Literal["continue_flow", "change_context", "view_evidence"]
    label: str = Field(min_length=1, max_length=160)
    workflow: RetrievalIntent | None = None
    field: ConversationField | None = None

    @model_validator(mode="after")
    def validate_target(self) -> "NextAction":
        if self.type == "continue_flow" and self.workflow is None:
            raise ValueError("continue-flow actions require a workflow")
        if self.type == "change_context" and self.field is None:
            raise ValueError("change-context actions require a field")
        if self.type == "view_evidence" and (self.workflow is not None or self.field is not None):
            raise ValueError("view-evidence actions cannot carry workflow or field targets")
        return self


class GroundedAnswer(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    status: Literal["answered", "needs_clarification", "insufficient"]
    language: QueryLanguage
    summary: str = Field(min_length=1, max_length=2_000)
    sections: list[AnswerSection] = Field(default_factory=list, max_length=12)
    clarification: ClarificationRequest | None = None
    context_used: list[ContextUsedItem] = Field(default_factory=list, max_length=16)
    limitations: list[AnswerLimitation] = Field(default_factory=list, max_length=12)
    next_actions: list[NextAction] = Field(default_factory=list, max_length=8)

    @model_validator(mode="after")
    def validate_status_shape(self) -> "GroundedAnswer":
        if self.status == "answered" and not self.sections:
            raise ValueError("answered responses require at least one section")
        if self.status != "answered" and self.sections:
            raise ValueError("non-answer responses cannot include factual sections")
        if self.status == "needs_clarification" and self.clarification is None:
            raise ValueError("clarification responses require a clarification request")
        if self.status != "needs_clarification" and self.clarification is not None:
            raise ValueError("only clarification responses can include a clarification request")
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

    @classmethod
    def out_of_scope(cls, language: QueryLanguage) -> "GroundedAnswer":
        messages = {
            QueryLanguage.EN: (
                "I can only help with Uzbekistan-related questions about immigration, "
                "tourism, business registration, healthcare, and everyday living."
            ),
            QueryLanguage.UZ: (
                "Men faqat Oʻzbekistonga oid immigratsiya, turizm, biznesni roʻyxatdan "  # noqa: RUF001
                "oʻtkazish, sogʻliqni saqlash va kundalik hayot savollariga yordam bera olaman."  # noqa: RUF001
            ),
            QueryLanguage.RU: (
                "Я могу помочь только с вопросами об Узбекистане: иммиграция, туризм, "  # noqa: RUF001
                "регистрация бизнеса, здравоохранение и повседневная жизнь."
            ),
        }
        return cls(status="insufficient", language=language, summary=messages[language])

    @classmethod
    def clarification_needed(
        cls,
        language: QueryLanguage,
        clarification: ClarificationRequest,
    ) -> "GroundedAnswer":
        messages = {
            QueryLanguage.EN: "I need one detail to determine which guidance applies.",
            QueryLanguage.UZ: (
                "Qaysi yoʻriqnoma mos kelishini aniqlash uchun bir maʼlumot kerak."  # noqa: RUF001
            ),
            QueryLanguage.RU: "Нужна одна деталь, чтобы определить применимые правила.",
        }
        return cls(
            status="needs_clarification",
            language=language,
            summary=messages[language],
            clarification=clarification,
            next_actions=[
                NextAction(
                    id="change-requested-context",
                    type="change_context",
                    label=clarification.question,
                    field=clarification.field,
                )
            ],
        )


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
        state: ConversationState | None = None,
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
        issues.extend(self._validate_context(answer, state))
        for limitation in answer.limitations:
            for evidence_id in limitation.evidence_ids:
                if evidence_id not in evidence_by_id:
                    issues.append(AnswerValidationIssue(code="limitation_evidence_unknown"))

        if issues:
            return ValidatedAnswer(
                answer=GroundedAnswer.safe_insufficiency(expected_language),
                accepted=False,
                issues=issues,
            )
        return ValidatedAnswer(answer=answer, accepted=True, issues=[])

    @staticmethod
    def _validate_context(
        answer: GroundedAnswer,
        state: ConversationState | None,
    ) -> list[AnswerValidationIssue]:
        if not answer.context_used:
            return []
        if state is None:
            return [AnswerValidationIssue(code="answer_context_without_state")]
        confirmed = {fact.field: fact for fact in state.facts if fact.status.value == "confirmed"}
        issues: list[AnswerValidationIssue] = []
        for item in answer.context_used:
            fact = confirmed.get(item.field)
            if (
                fact is None
                or fact.value != item.value
                or fact.source_message_id != item.source_message_id
            ):
                issues.append(AnswerValidationIssue(code="answer_context_mismatch"))
        return issues

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
