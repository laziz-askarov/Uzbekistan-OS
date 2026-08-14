from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.ai.answers import (
    AnswerValidationIssue,
    ClarificationRequest,
    GroundedAnswer,
    GroundedAnswerValidator,
    ValidatedAnswer,
)
from app.ai.context import ConversationContext
from app.ai.dialogue import ClarificationPlanner
from app.ai.gateway import ModelGateway, ModelGatewayError
from app.ai.prompts import PromptRegistry
from app.ai.state import ConversationState
from app.retrieval.evidence import EvidencePack
from app.retrieval.planning import QueryLanguage, RetrievalRisk


class EvidenceFeedback(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    evidence_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    official_source_count: int = Field(ge=0)
    document_version_ids: list[str]


class OrchestrationOutcome(ValidatedAnswer):
    model_config = ConfigDict(frozen=True, extra="forbid")

    prompt_fingerprint: str | None = None
    route_key: str | None = None
    attempts: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    duration_ms: float = 0
    cost_usd: float = 0
    context_fingerprint: str | None = None
    state_fingerprint: str | None = None
    evidence_feedback: EvidenceFeedback | None = None


class GroundedAnswerOrchestrator:
    def __init__(
        self,
        *,
        prompts: PromptRegistry,
        gateway: ModelGateway,
        validator: GroundedAnswerValidator | None = None,
        clarification_planner: ClarificationPlanner | None = None,
    ) -> None:
        self.prompts = prompts
        self.gateway = gateway
        self.validator = validator or GroundedAnswerValidator()
        self.clarification_planner = clarification_planner or ClarificationPlanner()

    def answer(
        self,
        *,
        question: str,
        language: QueryLanguage,
        risk: RetrievalRisk,
        evidence: EvidencePack,
        request_id: str,
        context: ConversationContext | None = None,
        state: ConversationState | None = None,
        clarification: ClarificationRequest | None = None,
    ) -> OrchestrationOutcome:
        evidence_feedback = self._evidence_feedback(evidence)
        if state is not None and state.language != language:
            return self._insufficient(
                language,
                "conversation_state_language_mismatch",
                state_fingerprint=state.fingerprint,
                evidence_feedback=evidence_feedback,
            )
        clarification = clarification or self.clarification_planner.plan(state)
        if clarification is not None:
            return OrchestrationOutcome(
                answer=GroundedAnswer.clarification_needed(language, clarification),
                accepted=True,
                issues=[],
                context_fingerprint=context.fingerprint if context else None,
                state_fingerprint=state.fingerprint if state else None,
                evidence_feedback=evidence_feedback,
            )
        if evidence.status != "sufficient":
            return self._insufficient(
                language,
                "evidence_insufficient",
                state_fingerprint=state.fingerprint if state else None,
                evidence_feedback=evidence_feedback,
            )
        if context is not None and context.language != language:
            return self._insufficient(
                language,
                "conversation_language_mismatch",
                context_fingerprint=context.fingerprint,
                state_fingerprint=state.fingerprint if state else None,
                evidence_feedback=evidence_feedback,
            )

        prompt = self.prompts.resolve("grounded-answer")
        structured_input: dict[str, Any] = {
            "question": question,
            "language": language.value,
            "risk": risk.value,
            "evidence": [item.model_dump(mode="json") for item in evidence.items],
            "conversation_context": context.to_model_input() if context else None,
            "conversation_state": self._state_input(state),
        }
        try:
            result = self.gateway.invoke(
                prompt=prompt,
                structured_input=structured_input,
                request_id=request_id,
                max_output_tokens=2_000,
            )
            raw_answer = GroundedAnswer.model_validate(result.output)
        except ModelGatewayError as exc:
            return self._insufficient(
                language,
                exc.code,
                prompt_fingerprint=prompt.fingerprint,
                context_fingerprint=context.fingerprint if context else None,
                state_fingerprint=state.fingerprint if state else None,
                evidence_feedback=evidence_feedback,
            )
        except ValidationError:
            return self._insufficient(
                language,
                "answer_schema_invalid",
                prompt_fingerprint=prompt.fingerprint,
                context_fingerprint=context.fingerprint if context else None,
                state_fingerprint=state.fingerprint if state else None,
                evidence_feedback=evidence_feedback,
            )

        validated = self.validator.validate(
            answer=raw_answer,
            evidence=evidence,
            expected_language=language,
            risk=risk,
            state=state,
        )
        return OrchestrationOutcome(
            **validated.model_dump(),
            prompt_fingerprint=result.prompt_fingerprint,
            route_key=result.route_key,
            attempts=result.attempts,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            duration_ms=result.duration_ms,
            cost_usd=result.cost_usd,
            context_fingerprint=context.fingerprint if context else None,
            state_fingerprint=state.fingerprint if state else None,
            evidence_feedback=evidence_feedback,
        )

    @staticmethod
    def _insufficient(
        language: QueryLanguage,
        code: str,
        *,
        prompt_fingerprint: str | None = None,
        context_fingerprint: str | None = None,
        state_fingerprint: str | None = None,
        evidence_feedback: EvidenceFeedback | None = None,
    ) -> OrchestrationOutcome:
        return OrchestrationOutcome(
            answer=GroundedAnswer.safe_insufficiency(language),
            accepted=False,
            issues=[AnswerValidationIssue(code=code)],
            prompt_fingerprint=prompt_fingerprint,
            context_fingerprint=context_fingerprint,
            state_fingerprint=state_fingerprint,
            evidence_feedback=evidence_feedback,
        )

    @staticmethod
    def _state_input(state: ConversationState | None) -> dict[str, Any] | None:
        if state is None:
            return None
        return {
            "context_is_untrusted": True,
            "workflow": state.workflow.value if state.workflow else None,
            "goal": state.goal,
            "facts": [fact.model_dump(mode="json") for fact in state.facts],
            "missing_context": [item.model_dump(mode="json") for item in state.missing_context],
            "conflicts": [item.model_dump(mode="json") for item in state.conflicts],
            "current_step": state.current_step,
        }

    @staticmethod
    def _evidence_feedback(evidence: EvidencePack) -> EvidenceFeedback:
        source_ids = {
            str(citation.source_id) for item in evidence.items for citation in item.citations
        }
        version_ids = list(dict.fromkeys(item.document_version_id for item in evidence.items))
        return EvidenceFeedback(
            evidence_fingerprint=evidence.evidence_fingerprint,
            official_source_count=len(source_ids),
            document_version_ids=version_ids,
        )
