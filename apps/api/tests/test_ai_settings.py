import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.ai.settings import (
    MVP_DOMAINS,
    SUPPORTED_LANGUAGES,
    AiRuntimeConfigurationError,
    MvpAiPolicy,
    load_ai_runtime_configuration,
)
from app.config import Settings

REPOSITORY_ROOT = Path(__file__).parents[3]
PROMPT_REGISTRY = REPOSITORY_ROOT / "data/prompts/registry.v1.json"
MODEL_REGISTRY = REPOSITORY_ROOT / "data/models/registry.mvp.json"


def configured_settings(**updates) -> Settings:
    values = {
        "ai_prompt_registry_path": str(PROMPT_REGISTRY),
        "ai_model_route_registry_path": str(MODEL_REGISTRY),
    }
    values.update(updates)
    return Settings.model_validate(values)


def test_mvp_ai_defaults_match_prd_scope_quality_and_latency_targets() -> None:
    settings = configured_settings()

    policy = MvpAiPolicy.from_settings(settings)

    assert policy.supported_languages == SUPPORTED_LANGUAGES
    assert policy.domains == MVP_DOMAINS
    assert policy.official_sources_only is True
    assert policy.citations_required is True
    assert policy.provider_response_storage is False
    assert policy.stream_start_target_ms == 2_000
    assert policy.first_content_target_ms == 3_000
    assert policy.response_target_ms == 8_000
    assert policy.citation_coverage_target == 0.95
    assert settings.openai_generation_model == "gpt-5.6-terra"


def test_runtime_loads_proposed_route_but_keeps_generation_disabled() -> None:
    runtime = load_ai_runtime_configuration(configured_settings())

    assert runtime.generation_enabled is False
    assert runtime.prompts.resolve("grounded-answer").version == "1.0.0"
    assert runtime.routes.routes[0].status == "proposed"
    assert runtime.routes.routes[0].reasoning_effort == "low"
    assert runtime.routes.routes[0].store is False
    assert runtime.provider_model_by_role == {"grounded-answer-balanced": "gpt-5.6-terra"}


def test_api_construction_validates_and_exposes_ai_runtime() -> None:
    from app.main import create_app

    runtime = create_app().state.ai_runtime

    assert runtime.generation_enabled is False
    assert runtime.policy.supported_languages == SUPPORTED_LANGUAGES


def test_enabling_generation_with_unapproved_route_fails_closed() -> None:
    with pytest.raises(AiRuntimeConfigurationError) as failure:
        load_ai_runtime_configuration(configured_settings(ai_generation_enabled=True))

    assert failure.value.code == "generation_route_unapproved"


def test_provider_response_storage_cannot_be_enabled() -> None:
    with pytest.raises(ValidationError):
        Settings.model_validate({"OPENAI_STORE_RESPONSES": True})


def test_blank_provider_key_is_treated_as_missing(tmp_path) -> None:
    payload = json.loads(MODEL_REGISTRY.read_text(encoding="utf-8"))
    payload["routes"][0]["status"] = "approved"
    path = tmp_path / "routes.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(AiRuntimeConfigurationError) as failure:
        load_ai_runtime_configuration(
            configured_settings(
                ai_generation_enabled=True,
                ai_model_route_registry_path=str(path),
                openai_api_key="",
            )
        )

    assert failure.value.code == "provider_credentials_missing"


@pytest.mark.parametrize(
    "updates",
    [
        {"ai_stream_start_target_ms": 4_000},
        {"ai_first_content_target_ms": 9_000},
        {"ai_conversation_summary_trigger_turns": 8},
        {"ai_evidence_max_items": 9, "ai_retrieval_limit": 8},
    ],
)
def test_invalid_cross_setting_budgets_are_rejected(updates) -> None:
    with pytest.raises(ValidationError):
        MvpAiPolicy.from_settings(configured_settings(**updates))


def test_route_attempt_budget_must_fit_response_target(tmp_path) -> None:
    payload = json.loads(MODEL_REGISTRY.read_text(encoding="utf-8"))
    payload["routes"][0]["timeout_seconds"] = 5
    payload["routes"][0]["max_attempts"] = 2
    path = tmp_path / "routes.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(AiRuntimeConfigurationError) as failure:
        load_ai_runtime_configuration(configured_settings(ai_model_route_registry_path=str(path)))

    assert failure.value.code == "route_latency_budget_exceeded"
