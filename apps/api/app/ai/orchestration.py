from typing import Any

from pydantic import ConfigDict, ValidationError

from app.ai.answers import (
    AnswerValidationIssue,
    GroundedAnswer,
    GroundedAnswerValidator,
    ValidatedAnswer,
)
from app.ai.context import ConversationContext
from app.ai.gateway import ModelGateway, ModelGatewayError
from app.ai.prompts import PromptRegistry
from app.retrieval.evidence import EvidencePack
from app.retrieval.planning import QueryLanguage, RetrievalRisk


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


class GroundedAnswerOrchestrator:
    def __init__(
        self,
        *,
        prompts: PromptRegistry,
        gateway: ModelGateway,
        validator: GroundedAnswerValidator | None = None,
    ) -> None:
        self.prompts = prompts
        self.gateway = gateway
        self.validator = validator or GroundedAnswerValidator()

    def answer(
        self,
        *,
        question: str,
        language: QueryLanguage,
        risk: RetrievalRisk,
        evidence: EvidencePack,
        request_id: str,
        context: ConversationContext | None = None,
    ) -> OrchestrationOutcome:
        if evidence.status != "sufficient":
            return self._insufficient(language, "evidence_insufficient")
        if context is not None and context.language != language:
            return self._insufficient(
                language,
                "conversation_language_mismatch",
                context_fingerprint=context.fingerprint,
            )

        prompt = self.prompts.resolve("grounded-answer")
        structured_input: dict[str, Any] = {
            "question": question,
            "language": language.value,
            "risk": risk.value,
            "evidence": [item.model_dump(mode="json") for item in evidence.items],
            "conversation_context": context.to_model_input() if context else None,
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
            return self._insufficient(language, exc.code, prompt_fingerprint=prompt.fingerprint)
        except ValidationError:
            return self._insufficient(
                language, "answer_schema_invalid", prompt_fingerprint=prompt.fingerprint
            )

        validated = self.validator.validate(
            answer=raw_answer,
            evidence=evidence,
            expected_language=language,
            risk=risk,
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
        )

    @staticmethod
    def _insufficient(
        language: QueryLanguage,
        code: str,
        *,
        prompt_fingerprint: str | None = None,
        context_fingerprint: str | None = None,
    ) -> OrchestrationOutcome:
        return OrchestrationOutcome(
            answer=GroundedAnswer.safe_insufficiency(language),
            accepted=False,
            issues=[AnswerValidationIssue(code=code)],
            prompt_fingerprint=prompt_fingerprint,
            context_fingerprint=context_fingerprint,
        )
