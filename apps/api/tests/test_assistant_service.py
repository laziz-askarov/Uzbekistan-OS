from hashlib import sha256
from pathlib import Path
from uuid import UUID, uuid4

from app.ai.context import ConversationContextAssembler
from app.ai.gateway import ModelGateway, ModelRoute, ModelRouteRegistry, ProviderResult
from app.ai.orchestration import GroundedAnswerOrchestrator
from app.ai.prompts import load_prompt_registry
from app.assistant.service import AssistantAnswerRequest, GroundedAssistantService
from app.retrieval.evidence import EvidencePackBuilder
from app.retrieval.service import HybridRetrievalService, RankedCandidate, RetrievalCandidate

PROMPT_REGISTRY = Path(__file__).parents[3] / "data/prompts/registry.v1.json"
SOURCE_ID = UUID("00000000-0000-0000-0000-000000002102")
CONTENT = "Elektron viza olish uchun rasmiy portalda ariza to'ldiriladi."


class MemoryRepository:
    def __init__(self, item: RetrievalCandidate) -> None:
        self.item = item

    def search_lexical(self, plan, *, limit):
        del plan, limit
        return (RankedCandidate(candidate=self.item, score=1),)

    def search_vector(self, plan, query_vector, *, model_key, limit):
        del plan, query_vector, model_key, limit
        return ()


class GroundedProvider:
    def __init__(self, chunk_id: str) -> None:
        self.chunk_id = chunk_id
        self.calls = 0

    def generate(self, request, *, timeout_seconds):
        del request, timeout_seconds
        self.calls += 1
        return ProviderResult(
            output={
                "status": "answered",
                "language": "uz",
                "summary": "Elektron viza arizasi rasmiy portal orqali beriladi.",
                "sections": [
                    {
                        "id": "section-ariza",
                        "heading": "Ariza",
                        "claims": [
                            {
                                "id": "claim-ariza",
                                "text": CONTENT,
                                "citations": [
                                    {
                                        "evidence_id": self.chunk_id,
                                        "quote": CONTENT,
                                    }
                                ],
                            }
                        ],
                    }
                ],
            },
            response_id="response-1",
            input_tokens=100,
            output_tokens=50,
            duration_ms=10,
            cost_usd=0.001,
        )


def assistant_service() -> tuple[GroundedAssistantService, GroundedProvider]:
    chunk_id = uuid4()
    candidate = RetrievalCandidate(
        chunk_id=chunk_id,
        document_id=uuid4(),
        document_version_id=uuid4(),
        document_slug="evisa-uz",
        domain="immigration",
        language="uz",
        risk_level="high",
        source_trust_tier=1,
        title="Elektron viza",
        summary="Rasmiy elektron viza yo'riqnomasi.",
        section_id="ariza",
        heading="Ariza",
        ordinal=0,
        content=CONTENT,
        content_hash=sha256(CONTENT.encode()).hexdigest(),
        citations=[{"source_id": SOURCE_ID, "locator": "Elektron viza haqida"}],
    )
    provider = GroundedProvider(str(chunk_id))
    route = ModelRoute(
        key="grounded-answer-default",
        status="approved",
        provider_key="test-provider",
        model_role="grounded-answer-balanced",
        reasoning_effort="low",
        timeout_seconds=2,
        max_attempts=1,
        max_input_tokens=12_000,
        max_output_tokens=2_000,
        max_cost_usd=0.05,
        store=False,
    )
    return (
        GroundedAssistantService(
            retrieval=HybridRetrievalService(MemoryRepository(candidate)),
            evidence_builder=EvidencePackBuilder(),
            orchestrator=GroundedAnswerOrchestrator(
                prompts=load_prompt_registry(PROMPT_REGISTRY),
                gateway=ModelGateway(
                    routes=ModelRouteRegistry(routes=[route]),
                    providers={"test-provider": provider},
                ),
            ),
            context_assembler=ConversationContextAssembler(),
            retrieval_limit=8,
        ),
        provider,
    )


def test_assistant_answers_only_from_matching_published_evidence() -> None:
    service, provider = assistant_service()

    result = service.answer(
        AssistantAnswerRequest(messages=[{"role": "user", "content": "Viza qanday olinadi?"}]),
        request_id="request-1",
    )

    assert result.accepted is True
    assert result.generated is True
    assert result.answer.status == "answered"
    assert result.answer.language.value == "uz"
    assert result.evidence.items[0].citations[0].source_id == SOURCE_ID
    assert provider.calls == 1


def test_assistant_does_not_generate_when_language_evidence_is_missing() -> None:
    service, provider = assistant_service()

    result = service.answer(
        AssistantAnswerRequest(
            messages=[{"role": "user", "content": "How do I get an electronic visa?"}]
        ),
        request_id="request-2",
    )

    assert result.accepted is False
    assert result.answer.status == "insufficient"
    assert result.evidence.items == []
    assert provider.calls == 0
