from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.ai.answers import GroundedAnswer
from app.ai.context import ConversationContextAssembler, ConversationMessage
from app.ai.orchestration import GroundedAnswerOrchestrator
from app.retrieval.evidence import EvidencePack, EvidencePackBuilder
from app.retrieval.planning import (
    ApplicabilityContext,
    QueryLanguage,
    QueryRequest,
    RetrievalPlanner,
    RetrievalPlanningError,
)
from app.retrieval.service import HybridRetrievalService


class AssistantError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class AssistantMessage(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2_000)


class AssistantAnswerRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    messages: list[AssistantMessage] = Field(min_length=1, max_length=24)
    language: QueryLanguage | None = None
    applicability: ApplicabilityContext = Field(default_factory=ApplicabilityContext)

    @model_validator(mode="after")
    def require_user_question(self) -> "AssistantAnswerRequest":
        if not any(message.role == "user" for message in self.messages):
            raise ValueError("at least one user message is required")
        return self


class AssistantAnswerData(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    answer: GroundedAnswer
    evidence: EvidencePack
    intent: str
    risk: str
    accepted: bool
    issues: list[str]
    generated: bool


class GroundedAssistantService:
    def __init__(
        self,
        *,
        retrieval: HybridRetrievalService,
        evidence_builder: EvidencePackBuilder,
        orchestrator: GroundedAnswerOrchestrator,
        context_assembler: ConversationContextAssembler,
        retrieval_limit: int,
    ) -> None:
        self.retrieval = retrieval
        self.evidence_builder = evidence_builder
        self.orchestrator = orchestrator
        self.context_assembler = context_assembler
        self.retrieval_limit = retrieval_limit

    def answer(self, payload: AssistantAnswerRequest, *, request_id: str) -> AssistantAnswerData:
        latest_question = next(
            message.content for message in reversed(payload.messages) if message.role == "user"
        )
        try:
            plan = RetrievalPlanner().plan(
                QueryRequest(
                    query=latest_question,
                    language=payload.language,
                    applicability=payload.applicability,
                )
            )
        except RetrievalPlanningError as error:
            raise AssistantError(error.code, str(error)) from error
        retrieval = self.retrieval.retrieve(plan, limit=self.retrieval_limit)
        evidence = self.evidence_builder.build(retrieval)
        created_at = datetime.now(UTC)
        context = self.context_assembler.assemble(
            language=plan.language,
            messages=[
                ConversationMessage(
                    id=f"message-{index}",
                    ordinal=index,
                    role=message.role,
                    language=plan.language,
                    content=message.content,
                    created_at=created_at,
                )
                for index, message in enumerate(payload.messages, start=1)
            ],
        )
        outcome = self.orchestrator.answer(
            question=latest_question,
            language=plan.language,
            risk=plan.risk,
            evidence=evidence,
            request_id=request_id,
            context=context,
        )
        return AssistantAnswerData(
            answer=outcome.answer,
            evidence=evidence,
            intent=plan.intent.value,
            risk=plan.risk.value,
            accepted=outcome.accepted,
            issues=[issue.code for issue in outcome.issues],
            generated=outcome.route_key is not None and outcome.accepted,
        )
