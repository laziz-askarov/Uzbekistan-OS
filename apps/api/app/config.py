from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    app_name: str = "Uzbekistan OS API"
    app_version: str = "0.1.0"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    readiness_timeout_seconds: int = Field(default=2, ge=1, le=10)
    api_cors_origins: str = "http://localhost:3000"
    api_allowed_hosts: str = "localhost,127.0.0.1,testserver,*.vercel.app"
    database_url: str = (
        "postgresql+psycopg://uzbekistan_os:local-development-only@localhost:5432/uzbekistan_os"
    )
    redis_url: str = "redis://localhost:6379/0"
    worker_stream: str = "uzbekistan-os:ingestion"
    worker_group: str = "ingestion-workers"
    worker_consumer_name: str | None = None
    worker_dead_letter_stream: str = "uzbekistan-os:ingestion:dead"
    worker_retry_set: str = "uzbekistan-os:ingestion:retries"
    worker_block_ms: int = Field(default=5000, ge=1)
    worker_stale_after_ms: int = Field(default=120000, ge=1000)
    worker_retry_base_seconds: int = Field(default=30, ge=1)
    worker_retry_max_seconds: int = Field(default=900, ge=1)
    worker_scheduler_poll_seconds: int = Field(default=60, ge=1, le=3600)
    worker_registry_path: str = "data/sources/registry.development.json"
    ai_generation_enabled: bool = False
    ai_prompt_registry_path: str = "data/prompts/registry.v1.json"
    ai_model_route_registry_path: str = "data/models/registry.mvp.json"
    ai_retrieval_limit: int = Field(default=8, ge=1, le=20)
    ai_evidence_max_items: int = Field(default=6, ge=1, le=12)
    ai_evidence_max_characters: int = Field(default=9_000, ge=500, le=30_000)
    ai_conversation_recent_turns: int = Field(default=8, ge=2, le=20)
    ai_conversation_summary_trigger_turns: int = Field(default=12, ge=4, le=40)
    ai_conversation_summary_max_characters: int = Field(default=4_000, ge=500, le=12_000)
    ai_conversation_context_max_characters: int = Field(default=16_000, ge=12_000, le=48_000)
    ai_stream_start_target_ms: int = Field(default=2_000, ge=100, le=10_000)
    ai_first_content_target_ms: int = Field(default=3_000, ge=500, le=15_000)
    ai_response_target_ms: int = Field(default=8_000, ge=1_000, le=30_000)
    ai_citation_coverage_target: float = Field(default=0.95, ge=0.95, le=1)
    ingestion_max_pdf_pages: int = Field(default=250, ge=1, le=2000)
    ingestion_max_normalized_characters: int = Field(default=2_000_000, ge=1000)
    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "uzbekistan-os"
    s3_secret_key: str = "local-development-only"
    s3_bucket: str = "uzbekistan-os-ingestion"
    s3_region: str = "us-east-1"
    s3_auto_create_bucket: bool = False
    openai_api_key: SecretStr | None = None
    openai_generation_model: str = Field(
        default="gpt-5.4-mini",
        min_length=1,
        validation_alias=AliasChoices(
            "OPENAI_GENERATION_MODEL", "OPENAI_MODEL", "openai_generation_model"
        ),
    )
    openai_store_responses: Literal[False] = Field(
        default=False,
        validation_alias=AliasChoices("OPENAI_STORE_RESPONSES", "openai_store_responses"),
    )
    supabase_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "SUPABASE_URL", "NEXT_PUBLIC_SUPABASE_URL", "supabase_url"
        ),
    )
    supabase_anon_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "SUPABASE_ANON_KEY",
            "NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY",
            "NEXT_PUBLIC_SUPABASE_ANON_KEY",
            "supabase_anon_key",
        ),
    )

    @field_validator("openai_api_key", "supabase_anon_key", mode="before")
    @classmethod
    def normalize_optional_provider_key(cls, value: object) -> object:
        if value is None:
            return None
        if isinstance(value, SecretStr):
            return value if value.get_secret_value().strip() else None
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("openai_store_responses", mode="before")
    @classmethod
    def enforce_disabled_provider_storage(cls, value: object) -> object:
        if value is False:
            return False
        if isinstance(value, str) and value.strip().lower() in {"0", "false", "no", "off"}:
            return False
        raise ValueError("provider response storage must remain disabled")

    @field_validator("openai_generation_model")
    @classmethod
    def normalize_generation_model(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("generation model must not be blank")
        return normalized

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.api_cors_origins.split(",") if origin.strip()]

    @property
    def allowed_hosts(self) -> list[str]:
        return [host.strip() for host in self.api_allowed_hosts.split(",") if host.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
