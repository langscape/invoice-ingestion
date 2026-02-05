"""Application configuration via environment variables with INVOICE_ prefix."""

from __future__ import annotations

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Invoice ingestion pipeline configuration.

    All settings are read from environment variables prefixed with ``INVOICE_``.
    Secrets (API keys, connection strings) are wrapped in ``SecretStr`` so they
    are never accidentally logged or serialised.
    """

    model_config = SettingsConfigDict(env_prefix="INVOICE_")

    # ── Azure AI (Claude models via Azure AI Foundry) ───────────────────
    azure_ai_endpoint: str = ""
    azure_ai_api_key: SecretStr = SecretStr("")

    # ── Azure OpenAI (GPT models) ────────────────────────────────────────
    azure_openai_endpoint: str = ""
    azure_openai_api_key: SecretStr = SecretStr("")

    # ── Model Names (Azure deployment names) ─────────────────────────────
    classification_model: str = "claude-haiku-4-5-20251001"
    extraction_model: str = "claude-sonnet-4-5-20250929"
    schema_mapping_model: str = "claude-haiku-4-5-20251001"
    audit_model: str = "gpt-4o"

    # ── Database ───────────────────────────────────────────────────────────
    database_url: SecretStr = SecretStr(
        "postgresql+asyncpg://invoice:invoice@localhost:5432/invoice_ingestion"
    )

    # ── Blob Storage ───────────────────────────────────────────────────────
    blob_connection_string: SecretStr = SecretStr("")
    blob_imported_container: str = "imported"
    blob_extracted_container: str = "extracted"

    # ── Confidence Thresholds ──────────────────────────────────────────────
    auto_accept_simple: float = Field(default=0.95, ge=0.0, le=1.0)
    auto_accept_complex: float = Field(default=0.90, ge=0.0, le=1.0)
    targeted_review_simple: float = Field(default=0.80, ge=0.0, le=1.0)
    targeted_review_complex: float = Field(default=0.70, ge=0.0, le=1.0)

    # ── Pipeline ───────────────────────────────────────────────────────────
    dpi: int = 300
    quality_threshold: float = Field(default=0.3, ge=0.0, le=1.0)
    llm_temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    llm_timeout: int = 120

    # ── Feature Flags ──────────────────────────────────────────────────────
    enable_failover: bool = True
    enable_learning_loop: bool = True
    enable_drift_detection: bool = True

    # ── API ─────────────────────────────────────────────────────────────────
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: list[str] = Field(default=["http://localhost:3000"])
