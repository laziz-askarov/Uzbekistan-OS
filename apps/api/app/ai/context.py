import json
import re
from datetime import datetime
from hashlib import sha256
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from app.retrieval.planning import QueryLanguage

_TOKEN_PATTERN = re.compile(r"[^\W_]+", flags=re.UNICODE)
_CONTROL_PATTERNS = (
    "<|system|>",
    "<|assistant|>",
    "[system]",
    "begin system message",
    "end system message",
    "ignore previous instructions",
    "reveal the system prompt",
)


class ConversationContextError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class ConversationMessage(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(pattern=r"^message-[a-z0-9-]{1,80}$")
    ordinal: int = Field(ge=1)
    role: Literal["user", "assistant"]
    language: QueryLanguage
    content: str = Field(min_length=1, max_length=12_000)
    created_at: datetime
    deleted_at: datetime | None = None

    @computed_field
    @property
    def content_hash(self) -> str:
        return sha256(self.content.encode()).hexdigest()


class SummaryCitation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    message_id: str = Field(pattern=r"^message-[a-z0-9-]{1,80}$")
    quote: str = Field(min_length=3, max_length=2_000)


class SummaryStatement(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(pattern=r"^summary-[a-z0-9-]{1,80}$")
    text: str = Field(min_length=3, max_length=1_000)
    citations: list[SummaryCitation] = Field(min_length=1, max_length=4)


class ConversationSummary(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    version: Literal["1.0"] = "1.0"
    language: QueryLanguage
    through_ordinal: int = Field(ge=1)
    statements: list[SummaryStatement] = Field(min_length=1, max_length=32)

    @model_validator(mode="after")
    def unique_statement_ids(self) -> "ConversationSummary":
        ids = [statement.id for statement in self.statements]
        if len(ids) != len(set(ids)):
            raise ValueError("summary statement identifiers must be unique")
        return self


class ContextIssue(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    code: str
    reference_id: str | None = None


class ConversationTurn(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    user: ConversationMessage
    assistant: ConversationMessage | None = None


class ConversationContext(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    language: QueryLanguage
    status: Literal["ready", "empty"]
    context_is_untrusted: Literal[True] = True
    use_as_official_evidence: Literal[False] = False
    summary: ConversationSummary | None
    turns: list[ConversationTurn]
    quarantined_message_ids: list[str]
    issues: list[ContextIssue]
    total_characters: int = Field(ge=0)
    fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")

    def to_model_input(self) -> dict:
        return {
            "language": self.language.value,
            "status": self.status,
            "context_is_untrusted": True,
            "use_as_official_evidence": False,
            "summary_statements": [statement.text for statement in self.summary.statements]
            if self.summary
            else [],
            "turns": [
                {
                    "user": {
                        "language": turn.user.language.value,
                        "content": turn.user.content,
                    },
                    "assistant": {
                        "language": turn.assistant.language.value,
                        "content": turn.assistant.content,
                    }
                    if turn.assistant
                    else None,
                }
                for turn in self.turns
            ],
        }


class ConversationContextAssembler:
    def __init__(
        self,
        *,
        recent_turns: int = 8,
        summary_max_characters: int = 4_000,
        context_max_characters: int = 16_000,
    ) -> None:
        if not 1 <= recent_turns <= 20:
            raise ValueError("recent turn limit must be between 1 and 20")
        if not 500 <= summary_max_characters <= 12_000:
            raise ValueError("summary character limit is outside the supported range")
        if context_max_characters < 12_000:
            raise ValueError("context character limit must fit one maximum user message")
        if summary_max_characters >= context_max_characters:
            raise ValueError("summary character limit must be below the context limit")
        self.recent_turns = recent_turns
        self.summary_max_characters = summary_max_characters
        self.context_max_characters = context_max_characters

    def assemble(
        self,
        *,
        language: QueryLanguage,
        messages: list[ConversationMessage],
        summary: ConversationSummary | None = None,
    ) -> ConversationContext:
        self._validate_message_identity(messages)
        ordered = sorted(messages, key=lambda message: message.ordinal)
        quarantined = [
            message.id
            for message in ordered
            if message.deleted_at is None and self._contains_control_pattern(message.content)
        ]
        eligible = [
            message
            for message in ordered
            if message.deleted_at is None and message.id not in quarantined
        ]
        issues = [
            ContextIssue(code="message_quarantined", reference_id=item) for item in quarantined
        ]
        turns = self._turns(eligible)[-self.recent_turns :]
        turns, budget_issues = self._fit_recent_turns(turns)
        issues.extend(budget_issues)
        recent_ids = {
            message.id
            for turn in turns
            for message in (turn.user, turn.assistant)
            if message is not None
        }
        accepted_summary, summary_issues = self._validate_summary(
            summary=summary,
            language=language,
            messages=eligible,
            recent_ids=recent_ids,
        )
        issues.extend(summary_issues)
        turn_characters = sum(
            len(message.content)
            for turn in turns
            for message in (turn.user, turn.assistant)
            if message is not None
        )
        summary_characters = self._summary_characters(accepted_summary)
        if turn_characters + summary_characters > self.context_max_characters:
            accepted_summary = None
            summary_characters = 0
            issues.append(ContextIssue(code="summary_context_budget_exceeded"))
        total_characters = turn_characters + summary_characters
        canonical = json.dumps(
            {
                "language": language.value,
                "messages": [
                    {"id": message.id, "hash": message.content_hash}
                    for turn in turns
                    for message in (turn.user, turn.assistant)
                    if message is not None
                ],
                "summary": accepted_summary.model_dump(mode="json") if accepted_summary else None,
                "quarantined": quarantined,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return ConversationContext(
            language=language,
            status="ready" if turns or accepted_summary else "empty",
            summary=accepted_summary,
            turns=turns,
            quarantined_message_ids=quarantined,
            issues=issues,
            total_characters=total_characters,
            fingerprint=sha256(canonical.encode()).hexdigest(),
        )

    @staticmethod
    def _validate_message_identity(messages: list[ConversationMessage]) -> None:
        ids = [message.id for message in messages]
        ordinals = [message.ordinal for message in messages]
        if len(ids) != len(set(ids)):
            raise ConversationContextError("duplicate_message_id", "message IDs must be unique")
        if len(ordinals) != len(set(ordinals)):
            raise ConversationContextError(
                "duplicate_message_ordinal", "message ordinals must be unique"
            )

    @staticmethod
    def _turns(messages: list[ConversationMessage]) -> list[ConversationTurn]:
        turns: list[ConversationTurn] = []
        for message in messages:
            if message.role == "user":
                turns.append(ConversationTurn(user=message))
            elif turns and turns[-1].assistant is None:
                turns[-1] = turns[-1].model_copy(update={"assistant": message})
        return turns

    def _fit_recent_turns(
        self, turns: list[ConversationTurn]
    ) -> tuple[list[ConversationTurn], list[ContextIssue]]:
        selected: list[ConversationTurn] = []
        issues: list[ContextIssue] = []
        used = 0
        for turn in reversed(turns):
            size = len(turn.user.content) + (len(turn.assistant.content) if turn.assistant else 0)
            if used + size > self.context_max_characters:
                if turn.assistant and used + len(turn.user.content) <= self.context_max_characters:
                    selected.append(ConversationTurn(user=turn.user))
                    used += len(turn.user.content)
                    issues.append(
                        ContextIssue(
                            code="assistant_context_budget_exceeded",
                            reference_id=turn.assistant.id,
                        )
                    )
                else:
                    issues.append(
                        ContextIssue(
                            code="turn_context_budget_exceeded",
                            reference_id=turn.user.id,
                        )
                    )
                continue
            selected.append(turn)
            used += size
        return list(reversed(selected)), issues

    def _validate_summary(
        self,
        *,
        summary: ConversationSummary | None,
        language: QueryLanguage,
        messages: list[ConversationMessage],
        recent_ids: set[str],
    ) -> tuple[ConversationSummary | None, list[ContextIssue]]:
        if summary is None:
            return None, []
        issues: list[ContextIssue] = []
        if summary.language != language:
            issues.append(ContextIssue(code="summary_language_mismatch"))
        if self._summary_characters(summary) > self.summary_max_characters:
            issues.append(ContextIssue(code="summary_size_exceeded"))
        by_id = {message.id: message for message in messages}
        for statement in summary.statements:
            valid_quotes: list[str] = []
            for citation in statement.citations:
                message = by_id.get(citation.message_id)
                if message is None or message.ordinal > summary.through_ordinal:
                    issues.append(
                        ContextIssue(code="summary_message_unknown", reference_id=statement.id)
                    )
                    continue
                if citation.message_id in recent_ids:
                    issues.append(
                        ContextIssue(code="summary_overlaps_recent", reference_id=statement.id)
                    )
                    continue
                if self._normalized(citation.quote) not in self._normalized(message.content):
                    issues.append(
                        ContextIssue(code="summary_quote_mismatch", reference_id=statement.id)
                    )
                    continue
                valid_quotes.append(citation.quote)
            if valid_quotes and self._coverage(statement.text, valid_quotes) < 0.6:
                issues.append(
                    ContextIssue(code="summary_statement_unsupported", reference_id=statement.id)
                )
        return (None, issues) if issues else (summary, [])

    @staticmethod
    def _summary_characters(summary: ConversationSummary | None) -> int:
        return sum(len(statement.text) for statement in summary.statements) if summary else 0

    @staticmethod
    def _normalized(value: str) -> str:
        return " ".join(value.casefold().split())

    @staticmethod
    def _coverage(text: str, quotes: list[str]) -> float:
        text_tokens = set(_TOKEN_PATTERN.findall(text.casefold()))
        if not text_tokens:
            return 0
        quote_tokens = set(_TOKEN_PATTERN.findall(" ".join(quotes).casefold()))
        return len(text_tokens.intersection(quote_tokens)) / len(text_tokens)

    @staticmethod
    def _contains_control_pattern(content: str) -> bool:
        normalized = content.casefold()
        return any(pattern in normalized for pattern in _CONTROL_PATTERNS)
