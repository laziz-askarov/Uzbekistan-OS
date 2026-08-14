import json
from enum import StrEnum
from hashlib import sha256
from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from app.ai.context import ConversationMessage
from app.retrieval.planning import (
    ApplicabilityContext,
    QueryLanguage,
    QueryRequest,
    RetrievalIntent,
)


class ConversationStateError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class ConversationField(StrEnum):
    AUDIENCE = "audience"
    NATIONALITY = "nationality"
    RESIDENCY_STATUS = "residency_status"
    LOCATION = "location"
    ACCOMMODATION_TYPE = "accommodation_type"
    ARRIVAL_DATE = "arrival_date"
    LENGTH_OF_STAY = "length_of_stay"
    APPLICANT_ROLE = "applicant_role"


class FactStatus(StrEnum):
    CONFIRMED = "confirmed"
    INFERRED = "inferred"


class FactConfidence(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ConversationFact(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    field: ConversationField
    value: str = Field(min_length=1, max_length=240)
    status: FactStatus
    source_message_id: str = Field(pattern=r"^message-[a-z0-9-]{1,80}$")
    quote: str = Field(min_length=1, max_length=2_000)
    confidence: FactConfidence | None = None

    @model_validator(mode="after")
    def validate_confidence(self) -> "ConversationFact":
        if self.status is FactStatus.INFERRED and self.confidence is None:
            raise ValueError("inferred conversation facts require confidence")
        if self.status is FactStatus.CONFIRMED and self.confidence is not None:
            raise ValueError("confirmed conversation facts cannot carry model confidence")
        if self.field is ConversationField.NATIONALITY and (
            len(self.value) != 2 or not self.value.isascii() or not self.value.isupper()
        ):
            raise ValueError("nationality facts must use uppercase ISO alpha-2 codes")
        return self


class MissingContext(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    field: ConversationField
    reason: str = Field(min_length=1, max_length=500)


class ContextConflict(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    field: ConversationField
    previous: ConversationFact
    proposed: ConversationFact
    resolution: Literal["pending"] = "pending"


class ConversationState(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    version: Literal["1.0"] = "1.0"
    workflow: RetrievalIntent | None = None
    goal: str | None = Field(default=None, min_length=1, max_length=160)
    language: QueryLanguage
    facts: list[ConversationFact] = Field(default_factory=list, max_length=32)
    missing_context: list[MissingContext] = Field(default_factory=list, max_length=16)
    conflicts: list[ContextConflict] = Field(default_factory=list, max_length=16)
    current_step: str | None = Field(
        default=None,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    )
    completed_steps: list[str] = Field(default_factory=list, max_length=64)
    last_evidence_fingerprint: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    last_document_version_ids: list[str] = Field(default_factory=list, max_length=32)

    @model_validator(mode="after")
    def validate_state(self) -> "ConversationState":
        fact_fields = [fact.field for fact in self.facts]
        if len(fact_fields) != len(set(fact_fields)):
            raise ValueError("conversation state can contain only one active fact per field")
        missing_fields = [item.field for item in self.missing_context]
        if len(missing_fields) != len(set(missing_fields)):
            raise ValueError("missing conversation fields must be unique")
        if set(fact_fields).intersection(missing_fields):
            raise ValueError("a conversation field cannot be both active and missing")
        conflict_fields = [conflict.field for conflict in self.conflicts]
        if len(conflict_fields) != len(set(conflict_fields)):
            raise ValueError("conversation conflicts must be unique by field")
        if set(fact_fields).intersection(conflict_fields):
            raise ValueError("a conflicted conversation field cannot remain active")
        if len(self.completed_steps) != len(set(self.completed_steps)):
            raise ValueError("completed conversation steps must be unique")
        if len(self.last_document_version_ids) != len(set(self.last_document_version_ids)):
            raise ValueError("document version lineage must be unique")
        return self

    @computed_field
    @property
    def fingerprint(self) -> str:
        payload = self.model_dump(mode="json", exclude={"fingerprint"})
        canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return sha256(canonical.encode()).hexdigest()


class ConversationFactUpdate(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    mode: Literal["observe", "correct", "remove"] = "observe"
    field: ConversationField
    value: str | None = Field(default=None, min_length=1, max_length=240)
    status: FactStatus | None = None
    source_message_id: str = Field(pattern=r"^message-[a-z0-9-]{1,80}$")
    quote: str = Field(min_length=1, max_length=2_000)
    confidence: FactConfidence | None = None

    @model_validator(mode="after")
    def validate_update(self) -> "ConversationFactUpdate":
        if self.mode == "remove":
            if self.value is not None or self.status is not None or self.confidence is not None:
                raise ValueError("remove updates cannot include a value, status, or confidence")
            return self
        if self.value is None or self.status is None:
            raise ValueError("observed and corrected facts require value and status")
        ConversationFact(
            field=self.field,
            value=self.value,
            status=self.status,
            source_message_id=self.source_message_id,
            quote=self.quote,
            confidence=self.confidence,
        )
        return self

    def as_fact(self) -> ConversationFact:
        if self.value is None or self.status is None:
            raise ConversationStateError("fact_update_invalid", "update does not contain a fact")
        return ConversationFact(
            field=self.field,
            value=self.value,
            status=self.status,
            source_message_id=self.source_message_id,
            quote=self.quote,
            confidence=self.confidence,
        )


class ConversationStateResolver:
    def apply(
        self,
        state: ConversationState,
        *,
        updates: list[ConversationFactUpdate],
        messages: list[ConversationMessage],
    ) -> ConversationState:
        message_by_id = {message.id: message for message in messages}
        facts = {fact.field: fact for fact in state.facts}
        conflicts = {conflict.field: conflict for conflict in state.conflicts}
        missing = {item.field: item for item in state.missing_context}

        for update in updates:
            self._validate_message_support(update, message_by_id)
            if update.mode == "remove":
                facts.pop(update.field, None)
                conflicts.pop(update.field, None)
                continue

            proposed = update.as_fact()
            existing = facts.get(update.field)
            if update.mode == "correct":
                facts[update.field] = proposed
                conflicts.pop(update.field, None)
                missing.pop(update.field, None)
                continue
            if existing is not None and existing.value != proposed.value:
                facts.pop(update.field)
                conflicts[update.field] = ContextConflict(
                    field=update.field,
                    previous=existing,
                    proposed=proposed,
                )
                missing.pop(update.field, None)
                continue
            facts[update.field] = proposed
            conflicts.pop(update.field, None)
            missing.pop(update.field, None)

        return ConversationState.model_validate(
            state.model_dump(mode="json", exclude={"fingerprint"})
            | {
                "facts": [fact.model_dump(mode="json") for fact in facts.values()],
                "conflicts": [conflict.model_dump(mode="json") for conflict in conflicts.values()],
                "missing_context": [item.model_dump(mode="json") for item in missing.values()],
            }
        )

    @staticmethod
    def _validate_message_support(
        update: ConversationFactUpdate,
        message_by_id: dict[str, ConversationMessage],
    ) -> None:
        message = message_by_id.get(update.source_message_id)
        if message is None or message.deleted_at is not None or message.role != "user":
            raise ConversationStateError(
                "fact_source_message_invalid",
                "conversation fact updates require an active user message",
            )
        normalized_quote = " ".join(update.quote.casefold().split())
        normalized_content = " ".join(message.content.casefold().split())
        if normalized_quote not in normalized_content:
            raise ConversationStateError(
                "fact_quote_mismatch",
                "conversation fact quote is not present in the source message",
            )


class ContextualQueryResolution(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    request: QueryRequest
    intent_hint: RetrievalIntent | None
    inherited_fields: list[ConversationField]
    overridden_fields: list[ConversationField]
    state_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")


class ContextualQueryResolver:
    _RETRIEVAL_FIELDS: ClassVar[dict[ConversationField, str]] = {
        ConversationField.AUDIENCE: "audience",
        ConversationField.NATIONALITY: "nationality",
        ConversationField.RESIDENCY_STATUS: "residency_status",
        ConversationField.LOCATION: "location",
    }

    def resolve(
        self,
        request: QueryRequest,
        state: ConversationState,
    ) -> ContextualQueryResolution:
        applicability = request.applicability.model_dump()
        inherited: list[ConversationField] = []
        overridden: list[ConversationField] = []
        for fact in state.facts:
            target = self._RETRIEVAL_FIELDS.get(fact.field)
            if target is None or fact.status is not FactStatus.CONFIRMED:
                continue
            if applicability[target] is None:
                applicability[target] = fact.value
                inherited.append(fact.field)
            elif applicability[target] != fact.value:
                overridden.append(fact.field)
        resolved = request.model_copy(
            update={"applicability": ApplicabilityContext.model_validate(applicability)}
        )
        return ContextualQueryResolution(
            request=resolved,
            intent_hint=state.workflow,
            inherited_fields=inherited,
            overridden_fields=overridden,
            state_fingerprint=state.fingerprint,
        )
