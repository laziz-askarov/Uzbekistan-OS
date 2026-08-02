from pathlib import Path

import pytest

from app.ai.gateway import (
    ModelGateway,
    ModelGatewayError,
    ModelProviderError,
    ModelRoute,
    ModelRouteRegistry,
    ProviderRequest,
    ProviderResult,
)
from app.ai.prompts import load_prompt_registry

PROMPT_REGISTRY = Path(__file__).parents[3] / "data/prompts/registry.v1.json"


def route(**updates) -> ModelRoute:
    values = {
        "key": "grounded-answer-default",
        "status": "approved",
        "provider_key": "test-provider",
        "model_role": "grounded-answer-model",
        "reasoning_effort": "low",
        "timeout_seconds": 2,
        "max_attempts": 2,
        "max_input_tokens": 10_000,
        "max_output_tokens": 2_000,
        "max_cost_usd": 0.5,
        "store": False,
    }
    values.update(updates)
    return ModelRoute.model_validate(values)


class RecordingProvider:
    def __init__(self, results) -> None:
        self.results = list(results)
        self.calls: list[tuple[ProviderRequest, float]] = []

    def generate(self, request, *, timeout_seconds):
        self.calls.append((request, timeout_seconds))
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def success(**updates) -> ProviderResult:
    values = {
        "output": {"status": "insufficient"},
        "response_id": "response-1",
        "input_tokens": 100,
        "output_tokens": 20,
        "duration_ms": 25,
        "cost_usd": 0.01,
    }
    values.update(updates)
    return ProviderResult.model_validate(values)


def gateway(provider, **route_updates) -> ModelGateway:
    return ModelGateway(
        routes=ModelRouteRegistry(routes=[route(**route_updates)]),
        providers={"test-provider": provider},
    )


def invoke(model_gateway: ModelGateway, **updates):
    values = {
        "prompt": load_prompt_registry(PROMPT_REGISTRY).resolve("grounded-answer"),
        "structured_input": {"question": "Visa?", "evidence": []},
        "request_id": "request-1",
        "max_output_tokens": 500,
    }
    values.update(updates)
    return model_gateway.invoke(**values)


def test_gateway_enforces_configured_route_and_non_storage_boundary() -> None:
    provider = RecordingProvider([success()])

    result = invoke(gateway(provider))

    request, timeout = provider.calls[0]
    assert timeout == 2
    assert request.store is False
    assert request.model_role == "grounded-answer-model"
    assert request.prompt_layers[0]["role"] == "system"
    assert result.route_key == "grounded-answer-default"
    assert result.attempts == 1
    assert result.cost_usd == 0.01


def test_gateway_retries_only_bounded_retryable_provider_failures() -> None:
    provider = RecordingProvider(
        [ModelProviderError("temporary", "temporary failure", retryable=True), success()]
    )

    result = invoke(gateway(provider))

    assert result.attempts == 2
    assert len(provider.calls) == 2


def test_non_retryable_provider_failure_stops_immediately() -> None:
    provider = RecordingProvider([ModelProviderError("bad_request", "invalid")])

    with pytest.raises(ModelGatewayError) as failure:
        invoke(gateway(provider))

    assert failure.value.code == "model_provider_failed"
    assert len(provider.calls) == 1


def test_unapproved_route_and_missing_provider_fail_closed() -> None:
    provider = RecordingProvider([success()])
    with pytest.raises(ModelGatewayError) as unapproved:
        invoke(gateway(provider, status="proposed"))
    assert unapproved.value.code == "model_route_not_approved"
    assert provider.calls == []

    missing = ModelGateway(
        routes=ModelRouteRegistry(routes=[route()]),
        providers={},
    )
    with pytest.raises(ModelGatewayError) as unavailable:
        invoke(missing)
    assert unavailable.value.code == "model_provider_unavailable"


def test_input_output_and_provider_reported_budgets_fail_closed() -> None:
    provider = RecordingProvider([success()])
    with pytest.raises(ModelGatewayError) as requested_output:
        invoke(gateway(provider, max_output_tokens=100), max_output_tokens=101)
    assert requested_output.value.code == "model_output_budget_exceeded"
    assert provider.calls == []

    provider = RecordingProvider([success()])
    with pytest.raises(ModelGatewayError) as estimated_input:
        invoke(gateway(provider, max_input_tokens=256), structured_input={"evidence": "x" * 2_000})
    assert estimated_input.value.code == "model_input_budget_exceeded"
    assert provider.calls == []

    provider = RecordingProvider([success(cost_usd=0.51)])
    with pytest.raises(ModelGatewayError) as reported_cost:
        invoke(gateway(provider))
    assert reported_cost.value.code == "model_provider_failed"
