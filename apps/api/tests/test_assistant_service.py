from hashlib import sha256
from pathlib import Path
from uuid import UUID, uuid4

from app.ai.context import ConversationContextAssembler
from app.ai.gateway import ModelGateway, ModelRoute, ModelRouteRegistry, ProviderResult
from app.ai.orchestration import GroundedAnswerOrchestrator
from app.ai.prompts import load_prompt_registry
from app.assistant.service import AssistantAnswerRequest, GroundedAssistantService
from app.retrieval.evidence import EvidenceItem, EvidencePack, EvidencePackBuilder
from app.retrieval.planning import QueryLanguage
from app.retrieval.service import (
    CitationReference,
    HybridRetrievalService,
    RankedCandidate,
    RetrievalCandidate,
)

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


class EmptyRepository:
    def search_lexical(self, plan, *, limit):
        del plan, limit
        return ()

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


def test_assistant_rejects_questions_outside_uzbekistan_scope_before_retrieval() -> None:
    service, provider = assistant_service()

    result = service.answer(
        AssistantAnswerRequest(
            messages=[{"role": "user", "content": "What is the capital of France?"}]
        ),
        request_id="request-out-of-scope",
    )

    assert result.accepted is False
    assert result.generated is False
    assert result.answer.status == "insufficient"
    assert result.issues == ["question_out_of_scope"]
    assert "Uzbekistan-related" in result.answer.summary
    assert provider.calls == 0


class EnglishGroundedProvider:
    def __init__(self, chunk_id: str, content: str) -> None:
        self.chunk_id = chunk_id
        self.content = content
        self.calls = 0

    def generate(self, request, *, timeout_seconds):
        del request, timeout_seconds
        self.calls += 1
        return ProviderResult(
            output={
                "status": "answered",
                "language": "en",
                "summary": self.content,
                "sections": [
                    {
                        "id": "section-overstay",
                        "heading": "Overstay",
                        "claims": [
                            {
                                "id": "claim-overstay",
                                "text": self.content,
                                "citations": [
                                    {"evidence_id": self.chunk_id, "quote": self.content}
                                ],
                            }
                        ],
                    }
                ],
            },
            response_id="response-web-1",
            input_tokens=100,
            output_tokens=50,
            duration_ms=10,
            cost_usd=0.001,
        )


class StubWebFallback:
    def __init__(self, evidence: EvidencePack) -> None:
        self.evidence = evidence
        self.calls = 0

    def retrieve(self, plan, *, request_id):
        del plan, request_id
        self.calls += 1
        return self.evidence


def test_assistant_uses_web_fallback_only_when_local_evidence_is_missing() -> None:
    content = "Overstaying an authorized stay may result in an administrative fine."
    chunk_id = uuid4()
    evidence = EvidencePack(
        plan_fingerprint="web-plan",
        evidence_fingerprint=sha256(b"web-evidence").hexdigest(),
        status="sufficient",
        reason=None,
        total_characters=len(content),
        quarantined_chunk_ids=[],
        items=[
            EvidenceItem(
                chunk_id=str(chunk_id),
                document_id=str(uuid4()),
                document_version_id=str(uuid4()),
                title="Official overstay guidance",
                heading="Overstay penalties",
                content=content,
                content_hash=sha256(content.encode()).hexdigest(),
                retrieval_score=1,
                citations=[
                    CitationReference(
                        source_id=SOURCE_ID,
                        locator="Live official page",
                        source_url="https://gov.uz/en/overstay",
                        source_title="Official overstay guidance",
                    )
                ],
            )
        ],
    )
    provider = EnglishGroundedProvider(str(chunk_id), content)
    fallback = StubWebFallback(evidence)
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
    service = GroundedAssistantService(
        retrieval=HybridRetrievalService(EmptyRepository()),
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
        web_fallback=fallback,
    )

    result = service.answer(
        AssistantAnswerRequest(
            messages=[
                {
                    "role": "user",
                    "content": "What are the penalties for overstaying in Uzbekistan?",
                }
            ],
            language=QueryLanguage.EN,
        ),
        request_id="request-web-fallback",
    )

    assert result.accepted is True
    assert result.generated is True
    assert result.answer.status == "answered"
    assert result.intent == "stay_extension"
    assert result.evidence.items[0].citations[0].source_url is not None
    assert fallback.calls == 1
    assert provider.calls == 1


def test_assistant_does_not_search_web_when_local_evidence_is_available() -> None:
    service, provider = assistant_service()
    fallback = StubWebFallback(
        EvidencePack(
            plan_fingerprint="unused",
            evidence_fingerprint=sha256(b"unused").hexdigest(),
            status="insufficient",
            reason="unused",
            total_characters=0,
            quarantined_chunk_ids=[],
            items=[],
        )
    )
    service.web_fallback = fallback

    result = service.answer(
        AssistantAnswerRequest(messages=[{"role": "user", "content": "Viza qanday olinadi?"}]),
        request_id="request-local-first",
    )

    assert result.accepted is True
    assert fallback.calls == 0
    assert provider.calls == 1
