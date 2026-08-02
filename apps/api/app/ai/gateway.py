from collections.abc import Mapping
from dataclasses import dataclass
from time import monotonic
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.ai.prompts import CompiledPrompt


class ModelGatewayError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class ModelProviderError(RuntimeError):
    def __init__(self, code: str, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable


class ModelRoute(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    key: str = Field(pattern=r"^[a-z][a-z0-9-]{1,63}$")
    status: Literal["proposed", "approved", "disabled"]
    provider_key: str = Field(pattern=r"^[a-z][a-z0-9-]{1,63}$")
    model_role: str = Field(pattern=r"^[a-z][a-z0-9-]{1,63}$")
    reasoning_effort: Literal["low", "medium", "high"] = "low"
    timeout_seconds: float = Field(gt=0, le=120)
    max_attempts: int = Field(ge=1, le=3)
    max_input_tokens: int = Field(ge=256, le=200_000)
    max_output_tokens: int = Field(ge=64, le=32_000)
    max_cost_usd: float = Field(gt=0, le=25)
    store: Literal[False] = False


class ModelRouteRegistry(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    routes: list[ModelRoute] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_route_keys(self) -> "ModelRouteRegistry":
        keys = [route.key for route in self.routes]
        if len(keys) != len(set(keys)):
            raise ValueError("model route keys must be unique")
        return self

    def resolve(self, key: str) -> ModelRoute:
        route = next((candidate for candidate in self.routes if candidate.key == key), None)
        if route is None:
            raise ModelGatewayError("model_route_not_found", f"model route {key!r} was not found")
        if route.status != "approved":
            raise ModelGatewayError(
                "model_route_not_approved", f"model route {key!r} is not approved"
            )
        return route


class ProviderRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    model_role: str
    reasoning_effort: str
    prompt_layers: list[dict[str, str]]
    structured_input: dict[str, Any]
    output_schema: str
    max_output_tokens: int
    store: Literal[False] = False
    request_id: str = Field(min_length=1, max_length=160)


class ProviderResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    output: dict[str, Any]
    response_id: str | None = None
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    duration_ms: float = Field(ge=0)
    cost_usd: float = Field(ge=0)


class ModelProvider(Protocol):
    def generate(self, request: ProviderRequest, *, timeout_seconds: float) -> ProviderResult: ...


class GatewayResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    output: dict[str, Any]
    route_key: str
    prompt_fingerprint: str
    attempts: int
    response_id: str | None
    input_tokens: int
    output_tokens: int
    duration_ms: float
    cost_usd: float


@dataclass(frozen=True)
class _AttemptFailure:
    error: ModelProviderError
    attempt: int


class ModelGateway:
    def __init__(
        self,
        *,
        routes: ModelRouteRegistry,
        providers: Mapping[str, ModelProvider],
    ) -> None:
        self.routes = routes
        self.providers = providers

    def invoke(
        self,
        *,
        prompt: CompiledPrompt,
        structured_input: dict[str, Any],
        request_id: str,
        max_output_tokens: int,
    ) -> GatewayResult:
        route = self.routes.resolve(prompt.model_route)
        provider = self.providers.get(route.provider_key)
        if provider is None:
            raise ModelGatewayError(
                "model_provider_unavailable", f"provider {route.provider_key!r} is not configured"
            )
        if max_output_tokens > route.max_output_tokens:
            raise ModelGatewayError(
                "model_output_budget_exceeded", "requested output exceeds route budget"
            )
        estimated_input_tokens = self._estimate_tokens(prompt, structured_input)
        if estimated_input_tokens > route.max_input_tokens:
            raise ModelGatewayError(
                "model_input_budget_exceeded", "estimated input exceeds route budget"
            )

        request = ProviderRequest(
            model_role=route.model_role,
            reasoning_effort=route.reasoning_effort,
            prompt_layers=[layer.model_dump(mode="json") for layer in prompt.layers],
            structured_input=structured_input,
            output_schema=prompt.output_schema,
            max_output_tokens=max_output_tokens,
            store=False,
            request_id=request_id,
        )
        last_failure: _AttemptFailure | None = None
        for attempt in range(1, route.max_attempts + 1):
            started = monotonic()
            try:
                result = provider.generate(request, timeout_seconds=route.timeout_seconds)
                elapsed_ms = (monotonic() - started) * 1000
                self._validate_result(route, result, elapsed_ms)
                return GatewayResult(
                    output=result.output,
                    route_key=route.key,
                    prompt_fingerprint=prompt.fingerprint,
                    attempts=attempt,
                    response_id=result.response_id,
                    input_tokens=result.input_tokens,
                    output_tokens=result.output_tokens,
                    duration_ms=result.duration_ms,
                    cost_usd=result.cost_usd,
                )
            except ModelProviderError as exc:
                last_failure = _AttemptFailure(error=exc, attempt=attempt)
                if not exc.retryable:
                    break
        assert last_failure is not None
        raise ModelGatewayError(
            "model_provider_failed",
            f"provider failed after {last_failure.attempt} attempt(s): {last_failure.error.code}",
        ) from last_failure.error

    @staticmethod
    def _estimate_tokens(prompt: CompiledPrompt, structured_input: dict[str, Any]) -> int:
        prompt_chars = sum(len(layer.content) for layer in prompt.layers)
        input_chars = len(str(structured_input))
        return max(1, (prompt_chars + input_chars + 3) // 4)

    @staticmethod
    def _validate_result(route: ModelRoute, result: ProviderResult, elapsed_ms: float) -> None:
        if elapsed_ms > route.timeout_seconds * 1000:
            raise ModelProviderError("provider_timeout", "provider exceeded route timeout")
        if result.input_tokens > route.max_input_tokens:
            raise ModelProviderError(
                "provider_input_budget_exceeded", "provider exceeded input budget"
            )
        if result.output_tokens > route.max_output_tokens:
            raise ModelProviderError(
                "provider_output_budget_exceeded", "provider exceeded output budget"
            )
        if result.cost_usd > route.max_cost_usd:
            raise ModelProviderError(
                "provider_cost_budget_exceeded", "provider exceeded cost budget"
            )
