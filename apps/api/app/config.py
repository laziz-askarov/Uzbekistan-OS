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
