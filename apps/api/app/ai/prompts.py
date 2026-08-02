import json
from hashlib import sha256
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator


class PromptRegistryError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class PromptLayer(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    key: str = Field(pattern=r"^[a-z][a-z0-9-]{1,63}$")
    role: Literal["system", "developer"]
    content: str = Field(min_length=20, max_length=12_000)


class PromptDefinition(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    key: str = Field(pattern=r"^[a-z][a-z0-9-]{1,63}$")
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    status: Literal["draft", "active", "retired"]
    model_route: str = Field(pattern=r"^[a-z][a-z0-9-]{1,63}$")
    output_schema: str = Field(pattern=r"^[a-z][a-z0-9.-]{1,95}$")
    layers: list[PromptLayer] = Field(min_length=2, max_length=12)

    @model_validator(mode="after")
    def validate_layers(self) -> "PromptDefinition":
        if self.layers[0].role != "system":
            raise ValueError("the first prompt layer must have the system role")
        keys = [layer.key for layer in self.layers]
        if len(keys) != len(set(keys)):
            raise ValueError("prompt layer keys must be unique")
        return self

    @property
    def fingerprint(self) -> str:
        immutable = self.model_dump(exclude={"status"}, mode="json")
        canonical = json.dumps(immutable, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return sha256(canonical.encode()).hexdigest()


class CompiledPrompt(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    key: str
    version: str
    model_route: str
    output_schema: str
    fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    layers: list[PromptLayer]

    @classmethod
    def from_definition(cls, definition: PromptDefinition) -> "CompiledPrompt":
        return cls(
            key=definition.key,
            version=definition.version,
            model_route=definition.model_route,
            output_schema=definition.output_schema,
            fingerprint=definition.fingerprint,
            layers=definition.layers,
        )


class PromptRegistry(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    registry_version: Literal["1.0"]
    prompts: list[PromptDefinition] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_registry(self) -> "PromptRegistry":
        identities = [(prompt.key, prompt.version) for prompt in self.prompts]
        if len(identities) != len(set(identities)):
            raise ValueError("prompt key and version pairs must be unique")
        active_keys = [prompt.key for prompt in self.prompts if prompt.status == "active"]
        if len(active_keys) != len(set(active_keys)):
            raise ValueError("only one active prompt version is allowed per key")
        return self

    def resolve(self, key: str, version: str | None = None) -> CompiledPrompt:
        matches = [
            prompt
            for prompt in self.prompts
            if prompt.key == key and (version is None or prompt.version == version)
        ]
        if version is None:
            matches = [prompt for prompt in matches if prompt.status == "active"]
        if not matches:
            raise PromptRegistryError("prompt_not_found", f"no eligible prompt found for {key!r}")
        if len(matches) != 1:
            raise PromptRegistryError(
                "prompt_ambiguous", f"prompt resolution is ambiguous for {key!r}"
            )
        if matches[0].status == "retired":
            raise PromptRegistryError("prompt_retired", f"prompt {key!r} is retired")
        return CompiledPrompt.from_definition(matches[0])


def load_prompt_registry(path: Path) -> PromptRegistry:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return PromptRegistry.model_validate(payload)
    except OSError as exc:
        raise PromptRegistryError("prompt_registry_unavailable", str(exc)) from exc
    except (json.JSONDecodeError, ValidationError) as exc:
        raise PromptRegistryError("prompt_registry_invalid", str(exc)) from exc
