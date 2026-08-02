from hashlib import sha256
from pathlib import Path
from uuid import UUID

from app.ai.context import ConversationContextAssembler, ConversationMessage
from app.ai.gateway import (
    ModelGateway,
    ModelProviderError,
    ModelRoute,
    ModelRouteRegistry,
    ProviderResult,
)
from app.ai.orchestration import GroundedAnswerOrchestrator
from app.ai.prompts import load_prompt_registry
from app.retrieval.evidence import EvidenceItem, EvidencePack
from app.retrieval.planning import QueryLanguage, RetrievalRisk
from app.retrieval.service import CitationReference

PROMPT_REGISTRY = Path(__file__).parents[3] / "data/prompts/registry.v1.json"
CONTENT = "Visa-free entry is permitted for up to 30 days for eligible visitors."


def evidence_pack(*, sufficient: bool = True) -> EvidencePack:
    items = (
        [
            EvidenceItem(
                chunk_id="chunk-1",
                document_id="document-1",
                document_version_id="version-1",
                title="Official visa guidance",
                heading="Visa-free entry",
                content=CONTENT,
                content_hash=sha256(CONTENT.encode()).hexdigest(),
                retrieval_score=1,
                citations=[
                    CitationReference(
                        source_id=UUID("00000000-0000-0000-0000-000000000001"),
                        locator="Visa-free entry",
                    )
                ],
            )
        ]
        if sufficient
        else []
    )
    status = "sufficient" if sufficient else "insufficient"
    return EvidencePack(
        plan_fingerprint="plan-1",
        evidence_fingerprint=sha256(status.encode()).hexdigest(),
        status=status,
        reason=None if sufficient else "no eligible evidence",
        total_characters=sum(len(item.content) for item in items),
        quarantined_chunk_ids=[],
        items=items,
    )


def grounded_output(*, claim_text: str | None = None) -> dict:
    return {
        "status": "answered",
        "language": "en",
        "summary": "Eligible visitors may enter visa-free for up to 30 days.",
        "sections": [
            {
                "id": "section-entry",
                "heading": "Entry",
                "claims": [
                    {
                        "id": "claim-entry",
                        "text": claim_text or "Visa-free entry is permitted for up to 30 days.",
                        "citations": [
                            {
                                "evidence_id": "chunk-1",
                                "quote": "Visa-free entry is permitted for up to 30 days",
                            }
                        ],
                    }
                ],
            }
        ],
    }


class StubProvider:
    def __init__(self, output=None, error: Exception | None = None) -> None:
        self.output = output
        self.error = error
        self.calls = 0
        self.last_request = None

    def generate(self, request, *, timeout_seconds):
        self.calls += 1
        self.last_request = request
        if self.error:
            raise self.error
        return ProviderResult(
            output=self.output,
            response_id="response-1",
            input_tokens=200,
            output_tokens=80,
            duration_ms=50,
            cost_usd=0.02,
        )


def orchestrator(provider: StubProvider) -> GroundedAnswerOrchestrator:
    route = ModelRoute(
        key="grounded-answer-default",
        status="approved",
        provider_key="test-provider",
        model_role="grounded-answer-model",
        reasoning_effort="low",
        timeout_seconds=2,
        max_attempts=1,
        max_input_tokens=10_000,
        max_output_tokens=2_000,
        max_cost_usd=0.5,
        store=False,
    )
    return GroundedAnswerOrchestrator(
        prompts=load_prompt_registry(PROMPT_REGISTRY),
        gateway=ModelGateway(
            routes=ModelRouteRegistry(routes=[route]),
            providers={"test-provider": provider},
        ),
    )


def ask(orchestration: GroundedAnswerOrchestrator, evidence=None):
    return orchestration.answer(
        question="Do I need a visa?",
        language=QueryLanguage.EN,
        risk=RetrievalRisk.HIGH,
        evidence=evidence or evidence_pack(),
        request_id="request-1",
    )


def test_orchestration_accepts_schema_valid_evidence_supported_answer() -> None:
    provider = StubProvider(grounded_output())

    outcome = ask(orchestrator(provider))

    assert outcome.accepted is True
    assert outcome.answer.status == "answered"
    assert outcome.route_key == "grounded-answer-default"
    assert outcome.prompt_fingerprint is not None
    assert outcome.input_tokens == 200
    assert outcome.cost_usd == 0.02


def test_insufficient_evidence_never_calls_provider() -> None:
    provider = StubProvider(grounded_output())

    outcome = ask(orchestrator(provider), evidence_pack(sufficient=False))

    assert provider.calls == 0
    assert outcome.accepted is False
    assert outcome.answer.status == "insufficient"
    assert outcome.issues[0].code == "evidence_insufficient"


def test_invalid_schema_and_unsupported_claim_degrade_safely() -> None:
    invalid = ask(orchestrator(StubProvider({"status": "answered"})))
    unsupported = ask(
        orchestrator(
            StubProvider(
                grounded_output(
                    claim_text="Applicants must buy insurance and register an apartment."
                )
            )
        )
    )

    assert invalid.answer.status == "insufficient"
    assert invalid.issues[0].code == "answer_schema_invalid"
    assert unsupported.answer.status == "insufficient"
    assert unsupported.issues[0].code == "claim_not_supported"


def test_provider_failure_does_not_leak_provider_error_to_answer() -> None:
    provider = StubProvider(error=ModelProviderError("secret-provider-code", "secret detail"))

    outcome = ask(orchestrator(provider))

    assert outcome.answer.status == "insufficient"
    assert outcome.answer.summary == (
        "I could not find enough current official evidence to answer safely."
    )
    assert outcome.issues[0].code == "model_provider_failed"


def test_bounded_conversation_context_is_supplied_as_untrusted_non_evidence() -> None:
    provider = StubProvider(grounded_output())
    context = ConversationContextAssembler().assemble(
        language=QueryLanguage.EN,
        messages=[
            ConversationMessage(
                id="message-1",
                ordinal=1,
                role="user",
                language="en",
                content="I am planning a short visit.",
                created_at="2026-08-02T12:00:00Z",
            )
        ],
    )

    outcome = orchestrator(provider).answer(
        question="Do I need a visa?",
        language=QueryLanguage.EN,
        risk=RetrievalRisk.HIGH,
        evidence=evidence_pack(),
        request_id="request-1",
        context=context,
    )

    supplied = provider.last_request.structured_input["conversation_context"]
    assert supplied["context_is_untrusted"] is True
    assert supplied["use_as_official_evidence"] is False
    assert outcome.context_fingerprint == context.fingerprint
