from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

DomainSlug = Literal[
    "immigration",
    "tourism",
    "business-registration",
    "healthcare",
    "everyday-living",
]
LanguageCode = Literal["en", "uz", "ru"]


class SourceType(StrEnum):
    HTML = "html"
    PDF = "pdf"
    FEED = "feed"
    MANUAL = "manual"


class CrawlPolicy(StrEnum):
    ALLOWED = "allowed"
    MANUAL_ONLY = "manual_only"
    BLOCKED = "blocked"
    PENDING_REVIEW = "pending_review"


class RegistryStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    REJECTED = "rejected"


class SourceOrganizationEntry(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: UUID
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    name: str = Field(min_length=1)
    website_url: HttpUrl
    is_official: bool


class SourceRegistryEntry(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: UUID
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    organization: SourceOrganizationEntry
    title: str = Field(min_length=1)
    url: HttpUrl
    source_type: SourceType
    domains: list[DomainSlug] = Field(min_length=1)
    languages: list[LanguageCode] = Field(min_length=1)
    crawl_policy: CrawlPolicy
    adapter_key: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    trust_tier: int = Field(ge=1, le=3)
    status: RegistryStatus
    owner: str | None = Field(default=None, min_length=1)
    reviewed_at: datetime | None = None
    production_eligible: bool = False

    @model_validator(mode="after")
    def validate_approval_state(self) -> "SourceRegistryEntry":
        if self.crawl_policy is CrawlPolicy.ALLOWED and self.status is not RegistryStatus.APPROVED:
            raise ValueError("automatically crawlable sources must be approved")
        if self.status is RegistryStatus.APPROVED and (
            self.owner is None or self.reviewed_at is None
        ):
            raise ValueError("approved sources require an owner and review timestamp")
        if self.production_eligible and (
            self.status is not RegistryStatus.APPROVED
            or self.crawl_policy not in {CrawlPolicy.ALLOWED, CrawlPolicy.MANUAL_ONLY}
        ):
            raise ValueError(
                "production-eligible sources must be approved for crawling or manual use"
            )
        if len(self.domains) != len(set(self.domains)):
            raise ValueError("source domains must be unique")
        if len(self.languages) != len(set(self.languages)):
            raise ValueError("source languages must be unique")
        return self

    @property
    def automatic_fetch_eligible(self) -> bool:
        return (
            self.status is RegistryStatus.APPROVED
            and self.crawl_policy is CrawlPolicy.ALLOWED
            and self.production_eligible
        )


class SourceRegistry(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    registry_version: Literal["1.0"]
    environment: Literal["development", "staging", "production"]
    sources: list[SourceRegistryEntry]

    @model_validator(mode="after")
    def validate_unique_sources(self) -> "SourceRegistry":
        for field in ("id", "slug", "url"):
            values = [str(getattr(source, field)) for source in self.sources]
            if len(values) != len(set(values)):
                raise ValueError(f"source registry contains duplicate {field} values")
        return self
