from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.ai.context import ConversationContextAssembler
from app.ai.gateway import ModelGatewayError, ModelRouteRegistry, load_model_route_registry
from app.ai.prompts import PromptRegistry, load_prompt_registry
from app.config import Settings

SUPPORTED_LANGUAGES = ("en", "uz", "ru")
MVP_DOMAINS = (
    "immigration",
    "tourism",
    "business-registration",
    "healthcare",
    "everyday-living",
)


class AiRuntimeConfigurationError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class MvpAiPolicy(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    supported_languages: tuple[Literal["en", "uz", "ru"], ...] = SUPPORTED_LANGUAGES
    domains: tuple[
        Literal[
            "immigration",
            "tourism",
            "business-registration",
            "healthcare",
            "everyday-living",
        ],
        ...,
    ] = MVP_DOMAINS
    official_sources_only: Literal[True] = True
    citations_required: Literal[True] = True
    provider_response_storage: Literal[False] = False
    retrieval_limit: int = Field(ge=1, le=20)
    evidence_max_items: int = Field(ge=1, le=12)
    evidence_max_characters: int = Field(ge=500, le=30_000)
    conversation_recent_turns: int = Field(ge=2, le=20)
    conversation_summary_trigger_turns: int = Field(ge=4, le=40)
    conversation_summary_max_characters: int = Field(ge=500, le=12_000)
    conversation_context_max_characters: int = Field(ge=12_000, le=48_000)
    stream_start_target_ms: int = Field(ge=100, le=10_000)
    first_content_target_ms: int = Field(ge=500, le=15_000)
    response_target_ms: int = Field(ge=1_000, le=30_000)
    citation_coverage_target: float = Field(ge=0.95, le=1)

    @model_validator(mode="after")
    def validate_mvp_budgets(self) -> "MvpAiPolicy":
        if not (
            self.stream_start_target_ms <= self.first_content_target_ms < self.response_target_ms
        ):
            raise ValueError("stream start, first content, and response targets must be ordered")
        if self.conversation_summary_trigger_turns <= self.conversation_recent_turns:
            raise ValueError("summary trigger must exceed the recent-turn window")
        if self.conversation_summary_max_characters >= self.conversation_context_max_characters:
            raise ValueError("summary character limit must be below the context limit")
        if self.evidence_max_items > self.retrieval_limit:
            raise ValueError("evidence item limit cannot exceed the retrieval limit")
        return self

    @classmethod
    def from_settings(cls, settings: Settings) -> "MvpAiPolicy":
        return cls(
            retrieval_limit=settings.ai_retrieval_limit,
            evidence_max_items=settings.ai_evidence_max_items,
            evidence_max_characters=settings.ai_evidence_max_characters,
            conversation_recent_turns=settings.ai_conversation_recent_turns,
            conversation_summary_trigger_turns=(settings.ai_conversation_summary_trigger_turns),
            conversation_summary_max_characters=(settings.ai_conversation_summary_max_characters),
            conversation_context_max_characters=(settings.ai_conversation_context_max_characters),
            stream_start_target_ms=settings.ai_stream_start_target_ms,
            first_content_target_ms=settings.ai_first_content_target_ms,
            response_target_ms=settings.ai_response_target_ms,
            citation_coverage_target=settings.ai_citation_coverage_target,
            provider_response_storage=settings.openai_store_responses,
        )

    def build_context_assembler(self) -> ConversationContextAssembler:
        return ConversationContextAssembler(
            recent_turns=self.conversation_recent_turns,
            summary_max_characters=self.conversation_summary_max_characters,
            context_max_characters=self.conversation_context_max_characters,
        )


class AiRuntimeConfiguration(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    generation_enabled: bool
    policy: MvpAiPolicy
    prompts: PromptRegistry
    routes: ModelRouteRegistry
    provider_model_by_role: dict[str, str]


def _resolve_configured_path(value: str) -> Path:
    configured = Path(value)
    if configured.is_absolute():
        return configured
    for base in (Path.cwd(), *Path(__file__).resolve().parents):
        candidate = base / configured
        if candidate.is_file():
            return candidate
    return configured


def load_ai_runtime_configuration(settings: Settings) -> AiRuntimeConfiguration:
    policy = MvpAiPolicy.from_settings(settings)
    prompts = load_prompt_registry(_resolve_configured_path(settings.ai_prompt_registry_path))
    routes = load_model_route_registry(
        _resolve_configured_path(settings.ai_model_route_registry_path)
    )
    prompt = prompts.resolve("grounded-answer")
    route = next(
        (candidate for candidate in routes.routes if candidate.key == prompt.model_route), None
    )
    if route is None:
        raise AiRuntimeConfigurationError(
            "prompt_route_missing", "the active grounded-answer prompt has no configured route"
        )
    if route.timeout_seconds * route.max_attempts * 1_000 > policy.response_target_ms:
        raise AiRuntimeConfigurationError(
            "route_latency_budget_exceeded",
            "the model route attempt budget exceeds the MVP response target",
        )
    if settings.ai_generation_enabled:
        try:
            routes.resolve(prompt.model_route)
        except ModelGatewayError as exc:
            raise AiRuntimeConfigurationError("generation_route_unapproved", str(exc)) from exc
        if route.provider_key == "openai" and settings.openai_api_key is None:
            raise AiRuntimeConfigurationError(
                "provider_credentials_missing",
                "AI generation is enabled but the configured provider credential is missing",
            )
    return AiRuntimeConfiguration(
        generation_enabled=settings.ai_generation_enabled,
        policy=policy,
        prompts=prompts,
        routes=routes,
        provider_model_by_role={
            candidate.model_role: settings.openai_generation_model
            for candidate in routes.routes
            if candidate.provider_key == "openai"
        },
    )
