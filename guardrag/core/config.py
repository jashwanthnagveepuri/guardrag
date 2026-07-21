"""Pydantic-Settings configuration for GuardRAG."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    All environment variables use the GUARDRAG_ prefix.
    """

    model_config = SettingsConfigDict(
        env_prefix="GUARDRAG_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App settings
    app_name: str = Field(default="GuardRAG", description="Application name")
    app_version: str = Field(default="1.0.0", description="Application version")
    app_debug: bool = Field(default=False, description="Debug mode")
    app_env: Literal["development", "staging", "production", "testing"] = Field(
        default="production", description="Deployment environment"
    )

    # API settings
    api_host: str = Field(default="0.0.0.0", description="API bind host")
    api_port: int = Field(default=8000, ge=1, le=65535, description="API port")
    api_workers: int = Field(default=1, ge=1, description="Number of API workers")

    # Database settings
    database_url: str = Field(
        default="postgresql+asyncpg://guardrag:guardrag@localhost:5432/guardrag",
        description="Async PostgreSQL connection URL",
    )

    # ChromaDB settings
    chromadb_host: str = Field(default="localhost", description="ChromaDB host")
    chromadb_port: int = Field(default=8000, ge=1, le=65535, description="ChromaDB port")
    chromadb_collection_name: str = Field(
        default="guardrag_chunks", description="ChromaDB collection name"
    )

    # OpenAI settings
    openai_api_key: str = Field(default="", description="OpenAI API key")
    openai_model: str = Field(default="gpt-4o", description="LLM model name")
    openai_embedding_model: str = Field(
        default="text-embedding-3-large", description="Embedding model name"
    )
    openai_temperature: float = Field(default=0.1, ge=0.0, le=2.0)

    # Chunking settings
    chunking_chunk_size: int = Field(default=512, ge=128, le=2048)
    chunking_chunk_overlap: int = Field(default=50, ge=0, le=256)
    chunking_strategy: Literal["recursive", "semantic"] = Field(default="recursive")

    # Retrieval settings
    retrieval_top_k: int = Field(default=5, ge=1, le=50)
    retrieval_mmr_fetch_k: int = Field(default=20, ge=1, le=100)
    retrieval_mmr_lambda: float = Field(default=0.5, ge=0.0, le=1.0)
    retrieval_rerank_top_k: int = Field(default=3, ge=1, le=20)

    # Guardrail settings
    guardrail_input_threshold: float = Field(default=0.75, ge=0.0, le=1.0)
    guardrail_output_threshold: float = Field(default=0.5, ge=0.0, le=1.0)

    # Upload settings
    upload_max_file_size: int = Field(
        default=52_428_800,  # 50MB
        ge=1_048_576,  # 1MB min
        le=1_073_741_824,  # 1GB max
        description="Maximum upload file size in bytes",
    )
    upload_allowed_types: str = Field(
        default="application/pdf,text/plain,text/markdown,application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        description="Comma-separated list of allowed MIME types",
    )

    # Redis settings
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis connection URL")

    @field_validator("upload_allowed_types", mode="before")
    @classmethod
    def _parse_allowed_types(cls, v: str | list[str]) -> str:
        if isinstance(v, list):
            return ",".join(v)
        return v

    @property
    def allowed_mime_types_list(self) -> list[str]:
        """Return allowed MIME types as a list."""
        return [t.strip() for t in self.upload_allowed_types.split(",") if t.strip()]

    @property
    def max_file_size_mb(self) -> float:
        """Return max file size in megabytes."""
        return self.upload_max_file_size / (1024 * 1024)

    @property
    def database_url_async(self) -> str:
        """Return the async database URL."""
        return self.database_url


# Global settings instance
_settings: Settings | None = None


def get_settings() -> Settings:
    """Return cached settings instance.

    The instance is created lazily on first call and reused thereafter.
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
