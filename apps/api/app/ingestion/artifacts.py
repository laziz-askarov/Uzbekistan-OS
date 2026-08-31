from datetime import datetime
from hashlib import sha256
from json import dumps
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ExtractedSection(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    heading: str = Field(min_length=1)
    body: str = Field(min_length=1)


class ExtractionArtifact(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    source_id: UUID
    snapshot_id: UUID
    adapter_key: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    media_type: str = Field(min_length=1)
    topic: str | None = Field(default=None, min_length=2, max_length=120)
    filename: str | None = Field(default=None, min_length=1, max_length=255)
    manual_upload: bool = False
    manual_correction: bool = False
    raw_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    normalized_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    extracted_at: datetime
    sections: list[ExtractedSection] = Field(min_length=1)

    def canonical_bytes(self) -> bytes:
        payload = self.model_dump(mode="json")
        return dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()

    @property
    def sha256(self) -> str:
        return sha256(self.canonical_bytes()).hexdigest()
