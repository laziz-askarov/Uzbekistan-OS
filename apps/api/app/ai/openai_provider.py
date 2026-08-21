import json
from collections.abc import Callable, Mapping
from time import monotonic
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.ai.answers import GroundedAnswer
from app.ai.gateway import ModelProviderError, ProviderRequest, ProviderResult

ProviderTransport = Callable[[dict[str, Any], float, str], Mapping[str, Any]]


class OpenAIResponsesProvider:
    """Provider adapter for schema-constrained, non-stored grounded answers."""

    def __init__(
        self,
        *,
        api_key: str,
        model_by_role: Mapping[str, str],
        transport: ProviderTransport | None = None,
        input_cost_per_million: float = 0.75,
        output_cost_per_million: float = 4.5,
    ) -> None:
        if not api_key.strip():
            raise ValueError("OpenAI API key must not be blank")
        self.api_key = api_key
        self.model_by_role = dict(model_by_role)
        self.transport = transport or self._post
        self.input_cost_per_million = input_cost_per_million
        self.output_cost_per_million = output_cost_per_million

    def generate(self, request: ProviderRequest, *, timeout_seconds: float) -> ProviderResult:
        model = self.model_by_role.get(request.model_role)
        if model is None:
            raise ModelProviderError(
                "provider_model_unavailable",
                "no provider model is configured for the requested model role",
            )
        if request.output_schema not in {"grounded-answer.v1", "grounded-answer.v2"}:
            raise ModelProviderError(
                "provider_schema_unavailable",
                "the requested structured output schema is not registered",
            )
        input_messages = [
            {"role": layer["role"], "content": layer["content"]}
            for layer in request.prompt_layers
        ]
        input_messages.append(
            {
                "role": "user",
                "content": json.dumps(
                    request.structured_input,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ),
            }
        )
        payload = {
            "model": model,
            "input": input_messages,
            "reasoning": {"effort": request.reasoning_effort},
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": request.output_schema.replace(".", "_"),
                    "strict": True,
                    "schema": _strict_output_schema(GroundedAnswer.model_json_schema()),
                }
            },
            "max_output_tokens": request.max_output_tokens,
            "store": False,
        }
        started = monotonic()
        try:
            response = self.transport(payload, timeout_seconds, request.request_id)
        except ModelProviderError:
            raise
        except Exception as error:
            raise ModelProviderError(
                "provider_transport_error",
                "provider request failed",
                retryable=True,
            ) from error
        duration_ms = (monotonic() - started) * 1000
        output = self._structured_output(response)
        usage = response.get("usage")
        usage = usage if isinstance(usage, Mapping) else {}
        input_tokens = _nonnegative_int(usage.get("input_tokens"))
        output_tokens = _nonnegative_int(usage.get("output_tokens"))
        cost = (
            input_tokens * self.input_cost_per_million
            + output_tokens * self.output_cost_per_million
        ) / 1_000_000
        response_id = response.get("id")
        return ProviderResult(
            output=output,
            response_id=response_id if isinstance(response_id, str) else None,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            duration_ms=duration_ms,
            cost_usd=cost,
        )

    def _post(
        self,
        payload: dict[str, Any],
        timeout_seconds: float,
        request_id: str,
    ) -> Mapping[str, Any]:
        http_request = Request(
            "https://api.openai.com/v1/responses",
            data=json.dumps(payload, ensure_ascii=False).encode(),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "X-Client-Request-Id": request_id,
            },
            method="POST",
        )
        try:
            with urlopen(http_request, timeout=timeout_seconds) as response:
                parsed = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            raise ModelProviderError(
                "provider_http_error",
                f"provider returned HTTP {error.code}",
                retryable=error.code == 429 or error.code >= 500,
            ) from error
        except (URLError, TimeoutError) as error:
            raise ModelProviderError(
                "provider_transport_error",
                "provider request failed",
                retryable=True,
            ) from error
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ModelProviderError(
                "provider_response_invalid",
                "provider returned an invalid response",
            ) from error
        if not isinstance(parsed, dict):
            raise ModelProviderError(
                "provider_response_invalid",
                "provider returned an invalid response",
            )
        return parsed

    @staticmethod
    def _structured_output(response: Mapping[str, Any]) -> dict[str, Any]:
        output = response.get("output")
        if not isinstance(output, list):
            raise ModelProviderError("provider_output_missing", "provider output is missing")
        for item in output:
            if not isinstance(item, Mapping) or item.get("type") != "message":
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for part in content:
                if not isinstance(part, Mapping) or part.get("type") != "output_text":
                    continue
                text = part.get("text")
                if not isinstance(text, str):
                    continue
                try:
                    parsed = json.loads(text)
                except json.JSONDecodeError as error:
                    raise ModelProviderError(
                        "provider_output_invalid_json",
                        "provider structured output is invalid",
                    ) from error
                if isinstance(parsed, dict):
                    return parsed
        raise ModelProviderError("provider_output_missing", "provider output is missing")


def _nonnegative_int(value: object) -> int:
    return value if isinstance(value, int) and value >= 0 else 0


def _strict_output_schema(value: object) -> object:
    """Convert Pydantic defaults to the required-key subset used by strict outputs."""
    if isinstance(value, list):
        return [_strict_output_schema(item) for item in value]
    if not isinstance(value, dict):
        return value
    result = {
        key: _strict_output_schema(item)
        for key, item in value.items()
        if key not in {"default", "title"}
    }
    properties = result.get("properties")
    if isinstance(properties, dict):
        result["required"] = list(properties)
        result["additionalProperties"] = False
    return result
