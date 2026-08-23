import json

import pytest

from app.ai.gateway import ModelProviderError, ProviderRequest
from app.ai.openai_provider import OpenAIResponsesProvider


def provider_request() -> ProviderRequest:
    return ProviderRequest(
        model_role="grounded-answer-balanced",
        reasoning_effort="low",
        prompt_layers=[{"key": "safety", "role": "system", "content": "Use evidence."}],
        structured_input={"question": "Viza kerakmi?", "evidence": []},
        output_schema="grounded-answer.v2",
        max_output_tokens=500,
        store=False,
        request_id="request-1",
    )


def test_provider_uses_non_stored_schema_constrained_responses_request() -> None:
    captured = {}

    def transport(payload, timeout_seconds, request_id):
        captured.update(
            payload=payload,
            timeout_seconds=timeout_seconds,
            request_id=request_id,
        )
        output = {
            "status": "insufficient",
            "language": "uz",
            "summary": "Rasmiy dalil yetarli emas.",
        }
        return {
            "id": "resp_1",
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": json.dumps(output)}],
                }
            ],
            "usage": {"input_tokens": 100, "output_tokens": 20},
        }

    result = OpenAIResponsesProvider(
        api_key="test-key",
        model_by_role={"grounded-answer-balanced": "gpt-5.4-mini"},
        transport=transport,
    ).generate(provider_request(), timeout_seconds=7)

    assert captured["payload"]["store"] is False
    assert captured["payload"]["reasoning"] == {"effort": "low"}
    assert captured["payload"]["text"]["format"]["type"] == "json_schema"
    assert captured["payload"]["text"]["format"]["strict"] is True
    schema = captured["payload"]["text"]["format"]["schema"]
    assert set(schema["required"]) == set(schema["properties"])
    assert "default" not in json.dumps(schema)
    assert captured["request_id"] == "request-1"
    assert result.output["language"] == "uz"
    assert result.input_tokens == 100
    assert result.cost_usd > 0


def test_provider_fails_closed_for_unknown_schema_or_missing_output() -> None:
    request = provider_request().model_copy(update={"output_schema": "unknown.v1"})
    provider = OpenAIResponsesProvider(
        api_key="test-key",
        model_by_role={"grounded-answer-balanced": "gpt-5.4-mini"},
        transport=lambda *_: {},
    )

    with pytest.raises(ModelProviderError, match="schema"):
        provider.generate(request, timeout_seconds=7)

    with pytest.raises(ModelProviderError, match="output"):
        provider.generate(provider_request(), timeout_seconds=7)
