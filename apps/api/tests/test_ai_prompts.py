import json
from pathlib import Path

import pytest

from app.ai.prompts import PromptRegistry, PromptRegistryError, load_prompt_registry

PROMPT_REGISTRY = Path(__file__).parents[3] / "data/prompts/registry.v1.json"


def registry_payload() -> dict:
    return json.loads(PROMPT_REGISTRY.read_text(encoding="utf-8"))


def test_checked_in_prompt_registry_resolves_immutable_active_prompt() -> None:
    registry = load_prompt_registry(PROMPT_REGISTRY)

    prompt = registry.resolve("grounded-answer")

    assert prompt.version == "1.0.0"
    assert prompt.layers[0].role == "system"
    assert len(prompt.fingerprint) == 64
    assert prompt.fingerprint == registry.resolve("grounded-answer").fingerprint


def test_prompt_fingerprint_does_not_change_when_only_status_changes() -> None:
    active = PromptRegistry.model_validate(registry_payload()).prompts[0]
    draft = active.model_copy(update={"status": "draft"})

    assert active.fingerprint == draft.fingerprint


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda payload: payload["prompts"].append(payload["prompts"][0]), "must be unique"),
        (
            lambda payload: payload["prompts"].append(
                {**payload["prompts"][0], "version": "1.1.0"}
            ),
            "only one active",
        ),
        (
            lambda payload: payload["prompts"][0]["layers"].reverse(),
            "first prompt layer",
        ),
    ],
)
def test_invalid_prompt_registry_invariants_are_rejected(mutation, message) -> None:
    payload = registry_payload()
    mutation(payload)

    with pytest.raises(ValueError, match=message):
        PromptRegistry.model_validate(payload)


def test_retired_prompt_cannot_be_resolved_even_by_version() -> None:
    payload = registry_payload()
    payload["prompts"][0]["status"] = "retired"
    registry = PromptRegistry.model_validate(payload)

    with pytest.raises(PromptRegistryError) as failure:
        registry.resolve("grounded-answer", "1.0.0")
    assert failure.value.code == "prompt_retired"


def test_malformed_prompt_registry_fails_with_stable_error(tmp_path) -> None:
    path = tmp_path / "prompts.json"
    path.write_text("not-json", encoding="utf-8")

    with pytest.raises(PromptRegistryError) as failure:
        load_prompt_registry(path)
    assert failure.value.code == "prompt_registry_invalid"
