"""Configuration loader for the Agentic Monetary Policy project.

This module uses :class:`pydantic.BaseSettings` to load environment variables
required for the LLM integration.  The settings are validated at import time
so that missing or malformed values are caught early.

Only non‑secret configuration values are exposed via the public API.  The
``NVIDIA_API_KEY`` is intentionally omitted from any representation to
prevent accidental leakage.
"""

from __future__ import annotations

import os
from typing import Optional

from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration loaded from environment variables.

    The class is a thin wrapper around :class:`pydantic.BaseSettings` that
    validates the presence of the required NVIDIA configuration values.
    NVIDIA settings are optional to allow the application to start without
    LLM configuration; they are validated at request time.
    """

    nvidia_api_key: Optional[str] = Field(default=None, env="NVIDIA_API_KEY")
    nvidia_base_url: Optional[str] = Field(default=None, env="NVIDIA_BASE_URL")
    nvidia_model: Optional[str] = Field(default=None, env="NVIDIA_MODEL")
    # Timeout configuration (seconds)
    nvidia_timeout_seconds: float = Field(default=120.0, env="NVIDIA_TIMEOUT_SECONDS")
    nvidia_connect_timeout: float = Field(default=10.0, env="NVIDIA_CONNECT_TIMEOUT")
    nvidia_max_retries: int = Field(default=1, env="NVIDIA_MAX_RETRIES")
    nvidia_max_concurrent_requests: int = Field(default=2, env="NVIDIA_MAX_CONCURRENT_REQUESTS")
    cors_allowed_origins: list[str] = Field(
        default=[
            "http://localhost:3000", "http://127.0.0.1:3000",
            "http://localhost:3001", "http://127.0.0.1:3001",
        ],
        env="CORS_ALLOWED_ORIGINS"
    )
    eia_api_key: Optional[str] = Field(default=None, env="EIA_API_KEY")
    fred_api_key: Optional[str] = Field(default=None, env="FRED_API_KEY")

    # Evidence upload limits
    max_upload_mb: int = Field(default=50, ge=1, le=1024, env="MAX_UPLOAD_MB")
    max_files_per_run: int = Field(default=20, ge=1, le=1000, env="MAX_FILES_PER_RUN")
    max_pdf_pages: int = Field(default=500, ge=1, le=100_000, env="MAX_PDF_PAGES")
    max_csv_rows: int = Field(default=100000, ge=1, le=10_000_000, env="MAX_CSV_ROWS")
    max_xlsx_sheets: int = Field(default=50, ge=1, le=1000, env="MAX_XLSX_SHEETS")
    max_json_bytes: int = Field(default=10_000_000, ge=1, le=1_000_000_000, env="MAX_JSON_BYTES")
    evidence_retention_hours: int = Field(default=24, ge=1, le=87600, env="EVIDENCE_RETENTION_HOURS")
    embedding_provider: str = Field(default="local", env="EMBEDDING_PROVIDER")
    embedding_model: Optional[str] = Field(default=None, env="EMBEDDING_MODEL")

    class Config:
        # Use absolute path to .env file relative to this file's location
        # This ensures .env is found regardless of working directory
        env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "allow"

    @validator("nvidia_base_url")
    def _validate_base_url(cls, v: Optional[str]) -> Optional[str]:  # pragma: no cover - trivial
        if v is not None and not v.startswith("http://") and not v.startswith("https://"):
            raise ValueError("NVIDIA_BASE_URL must start with http:// or https://")
        return v

    def is_llm_configured(self) -> bool:
        """Check if all required NVIDIA settings are present and valid."""
        if not self.nvidia_api_key or not self.nvidia_api_key.strip():
            return False
        if self.nvidia_api_key == "your_nvidia_api_key_here":
            return False
        if not self.nvidia_base_url or not self.nvidia_base_url.strip():
            return False
        if not self.nvidia_model or not self.nvidia_model.strip():
            return False
        return True


def get_settings() -> Settings:
    """Return a singleton instance of :class:`Settings`.

    The function lazily creates the settings object on first call and caches
    it for subsequent calls.  This avoids re‑reading the environment on
    every import.
    """

    if not hasattr(get_settings, "_instance"):
        get_settings._instance = Settings()  # type: ignore[attr-defined]
    return get_settings._instance


def validate_llm_config() -> None:
    """Validate LLM configuration for operations that require it.

    Raises:
        RuntimeError: If required LLM configuration is missing or invalid.
    """
    settings = get_settings()
    if not settings.is_llm_configured():
        raise RuntimeError("NVIDIA_API_KEY is not configured. Add it to .env.")
    # Additional validation for base URL format
    if settings.nvidia_base_url and not (settings.nvidia_base_url.startswith("http://") or settings.nvidia_base_url.startswith("https://")):
        raise RuntimeError("NVIDIA_BASE_URL must start with http:// or https://")


# Convenience accessors for evidence limits
def get_evidence_limits() -> dict:
    """Get evidence upload limits from settings."""
    settings = get_settings()
    return {
        "max_upload_mb": settings.max_upload_mb,
        "max_upload_bytes": settings.max_upload_mb * 1024 * 1024,
        "max_files_per_run": settings.max_files_per_run,
        "max_pdf_pages": settings.max_pdf_pages,
        "max_csv_rows": settings.max_csv_rows,
        "max_xlsx_sheets": settings.max_xlsx_sheets,
        "max_json_bytes": settings.max_json_bytes,
        "evidence_retention_hours": settings.evidence_retention_hours,
    }
