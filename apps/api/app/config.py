from functools import lru_cache

from pydantic import AliasChoices, Field
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
    api_cors_origins: str = "http://localhost:3000"
    database_url: str = "postgresql+psycopg://uzbekistan_os:local-development-only@localhost:5432/uzbekistan_os"
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
    ingestion_max_pdf_pages: int = Field(default=250, ge=1, le=2000)
    ingestion_max_normalized_characters: int = Field(default=2_000_000, ge=1000)
    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "uzbekistan-os"
    s3_secret_key: str = "local-development-only"
    s3_bucket: str = "uzbekistan-os-ingestion"
    s3_region: str = "us-east-1"
    s3_auto_create_bucket: bool = False
    openai_api_key: str | None = None
    openai_model: str = "gpt-5.6-terra"
    openai_store_responses: bool = Field(
        default=False,
        validation_alias=AliasChoices("OPENAI_STORE_RESPONSES", "openai_store_responses"),
    )

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.api_cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
