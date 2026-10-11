"""Security configuration using Pydantic Settings.

All secrets must come from environment variables or a secret manager.
Never hardcode credentials.
"""

from __future__ import annotations

import os
from typing import Optional, List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class SecuritySettings(BaseSettings):
    """Security configuration loaded from environment variables."""

    # JWT Configuration
    jwt_secret_key: str = Field(
        default="",
        env="JWT_SECRET_KEY",
        description="Secret key for JWT token signing. MUST be set in production.",
    )
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_access_token_expire_minutes: int = Field(
        default=30, ge=5, le=1440, env="JWT_ACCESS_TOKEN_EXPIRE_MINUTES"
    )
    jwt_refresh_token_expire_days: int = Field(
        default=7, ge=1, le=90, env="JWT_REFRESH_TOKEN_EXPIRE_DAYS"
    )

    # Password Hashing (Argon2id)
    argon2_time_cost: int = Field(default=3, ge=1, le=10, env="ARGON2_TIME_COST")
    argon2_memory_cost: int = Field(default=65536, ge=8192, le=1048576, env="ARGON2_MEMORY_COST")
    argon2_parallelism: int = Field(default=4, ge=1, le=16, env="ARGON2_PARALLELISM")
    argon2_hash_len: int = Field(default=32, ge=16, le=64, env="ARGON2_HASH_LEN")
    argon2_salt_len: int = Field(default=16, ge=8, le=32, env="ARGON2_SALT_LEN")

    # Session Configuration
    session_cookie_name: str = Field(default="session", env="SESSION_COOKIE_NAME")
    session_cookie_secure: bool = Field(default=True, env="SESSION_COOKIE_SECURE")
    session_cookie_httponly: bool = Field(default=True, env="SESSION_COOKIE_HTTPONLY")
    session_cookie_samesite: str = Field(default="lax", env="SESSION_COOKIE_SAMESITE")
    session_cookie_domain: Optional[str] = Field(default=None, env="SESSION_COOKIE_DOMAIN")
    session_cookie_path: str = Field(default="/", env="SESSION_COOKIE_PATH")
    session_max_age_seconds: int = Field(
        default=1800, ge=300, le=86400, env="SESSION_MAX_AGE_SECONDS"
    )
    session_idle_timeout_seconds: int = Field(
        default=900, ge=60, le=3600, env="SESSION_IDLE_TIMEOUT_SECONDS"
    )

    # MFA Configuration
    mfa_issuer_name: str = Field(default="India Macro AI", env="MFA_ISSUER_NAME")
    mfa_totp_digits: int = Field(default=6, ge=6, le=8, env="MFA_TOTP_DIGITS")
    mfa_totp_period: int = Field(default=30, ge=15, le=60, env="MFA_TOTP_PERIOD")
    mfa_recovery_codes_count: int = Field(default=10, ge=5, le=20, env="MFA_RECOVERY_CODES_COUNT")
    mfa_recovery_code_length: int = Field(default=16, ge=12, le=32, env="MFA_RECOVERY_CODE_LENGTH")

    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    rate_limit_storage_url: str = Field(default="memory://", env="RATE_LIMIT_STORAGE_URL")
    rate_limit_default_limit: str = Field(default="100/minute", env="RATE_LIMIT_DEFAULT_LIMIT")
    rate_limit_login_limit: str = Field(default="5/minute", env="RATE_LIMIT_LOGIN_LIMIT")
    rate_limit_register_limit: str = Field(default="3/minute", env="RATE_LIMIT_REGISTER_LIMIT")
    rate_limit_password_reset_limit: str = Field(default="2/hour", env="RATE_LIMIT_PASSWORD_RESET_LIMIT")
    rate_limit_upload_limit: str = Field(default="10/minute", env="RATE_LIMIT_UPLOAD_LIMIT")
    rate_limit_chat_limit: str = Field(default="30/minute", env="RATE_LIMIT_CHAT_LIMIT")
    rate_limit_research_limit: str = Field(default="10/minute", env="RATE_LIMIT_RESEARCH_LIMIT")
    rate_limit_admin_limit: str = Field(default="60/minute", env="RATE_LIMIT_ADMIN_LIMIT")

    # Resource Quotas
    quota_max_concurrent_research_runs: int = Field(default=3, ge=1, le=20, env="QUOTA_MAX_CONCURRENT_RESEARCH_RUNS")
    quota_max_active_jobs_per_tenant: int = Field(default=10, ge=1, le=100, env="QUOTA_MAX_ACTIVE_JOBS_PER_TENANT")
    quota_max_agent_iterations: int = Field(default=50, ge=1, le=200, env="QUOTA_MAX_AGENT_ITERATIONS")
    quota_max_agent_tool_calls: int = Field(default=100, ge=1, le=500, env="QUOTA_MAX_AGENT_TOOL_CALLS")
    quota_max_llm_requests_per_minute: int = Field(default=20, ge=1, le=200, env="QUOTA_MAX_LLM_REQUESTS_PER_MINUTE")
    quota_max_request_duration_seconds: int = Field(default=300, ge=30, le=3600, env="QUOTA_MAX_REQUEST_DURATION_SECONDS")
    quota_max_monte_carlo_draws: int = Field(default=10000, ge=100, le=100000, env="QUOTA_MAX_MONTE_CARLO_DRAWS")
    quota_max_uploaded_file_count: int = Field(default=20, ge=1, le=100, env="QUOTA_MAX_UPLOADED_FILE_COUNT")
    quota_max_upload_size_mb: int = Field(default=50, ge=1, le=500, env="QUOTA_MAX_UPLOAD_SIZE_MB")

    # File Upload Security
    upload_allowed_extensions: List[str] = Field(
        default=[".pdf", ".csv", ".xlsx", ".json", ".txt", ".md"],
        env="UPLOAD_ALLOWED_EXTENSIONS",
    )
    upload_max_file_size_mb: int = Field(default=50, ge=1, le=1024, env="UPLOAD_MAX_FILE_SIZE_MB")
    upload_max_files_per_request: int = Field(default=20, ge=1, le=100, env="UPLOAD_MAX_FILES_PER_REQUEST")
    upload_quarantine_path: str = Field(default="/tmp/uploads/quarantine", env="UPLOAD_QUARANTINE_PATH")
    upload_storage_path: str = Field(default="/data/uploads", env="UPLOAD_STORAGE_PATH")
    upload_scan_malware: bool = Field(default=False, env="UPLOAD_SCAN_MALWARE")
    upload_clamav_socket: Optional[str] = Field(default=None, env="UPLOAD_CLAMAV_SOCKET")
    upload_parser_timeout_seconds: int = Field(default=30, ge=5, le=300, env="UPLOAD_PARSER_TIMEOUT_SECONDS")
    upload_parser_memory_limit_mb: int = Field(default=256, ge=64, le=2048, env="UPLOAD_PARSER_MEMORY_LIMIT_MB")
    upload_xlsx_max_uncompressed_mb: int = Field(default=100, ge=10, le=1000, env="UPLOAD_XLSX_MAX_UNCOMPRESSED_MB")
    upload_xlsx_max_compression_ratio: float = Field(default=100.0, ge=10.0, le=1000.0, env="UPLOAD_XLSX_MAX_COMPRESSION_RATIO")

    # Network Policy (SSRF Protection)
    network_allowed_domains: List[str] = Field(
        default=[
            "api.rbi.org.in",
            "www.mospi.gov.in",
            "api.eia.gov",
            "api.stlouisfed.org",
            "api.worldbank.org",
            "api.imf.org",
            "integrate.api.nvidia.com",
        ],
        env="NETWORK_ALLOWED_DOMAINS",
    )
    network_allowed_schemes: List[str] = Field(default=["https"], env="NETWORK_ALLOWED_SCHEMES")
    network_block_private_ips: bool = Field(default=True, env="NETWORK_BLOCK_PRIVATE_IPS")
    network_block_metadata_endpoints: bool = Field(default=True, env="NETWORK_BLOCK_METADATA_ENDPOINTS")
    network_max_redirects: int = Field(default=3, ge=0, le=10, env="NETWORK_MAX_REDIRECTS")
    network_request_timeout_seconds: int = Field(default=30, ge=5, le=120, env="NETWORK_REQUEST_TIMEOUT_SECONDS")
    network_max_response_size_mb: int = Field(default=10, ge=1, le=100, env="NETWORK_MAX_RESPONSE_SIZE_MB")

    # Model Artifact Security
    model_quarantine_path: str = Field(default="/tmp/models/quarantine", env="MODEL_QUARANTINE_PATH")
    model_registry_path: str = Field(default="/data/models/registry", env="MODEL_REGISTRY_PATH")
    model_allowed_formats: List[str] = Field(
        default=["joblib", "onnx", "safetensors"],
        env="MODEL_ALLOWED_FORMATS",
    )
    model_max_size_mb: int = Field(default=500, ge=10, le=5000, env="MODEL_MAX_SIZE_MB")
    model_require_backtest: bool = Field(default=True, env="MODEL_REQUIRE_BACKTEST")
    model_backtest_min_samples: int = Field(default=100, ge=10, le=10000, env="MODEL_BACKTEST_MIN_SAMPLES")

    # Database Security
    database_url: Optional[str] = Field(default=None, env="DATABASE_URL")
    database_pool_size: int = Field(default=10, ge=1, le=100, env="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=20, ge=0, le=100, env="DATABASE_MAX_OVERFLOW")
    database_pool_timeout: int = Field(default=30, ge=5, le=120, env="DATABASE_POOL_TIMEOUT")
    database_echo: bool = Field(default=False, env="DATABASE_ECHO")

    # Audit Logging
    audit_log_enabled: bool = Field(default=True, env="AUDIT_LOG_ENABLED")
    audit_log_path: str = Field(default="/var/log/security/audit.log", env="AUDIT_LOG_PATH")
    audit_log_max_size_mb: int = Field(default=100, ge=10, le=1000, env="AUDIT_LOG_MAX_SIZE_MB")
    audit_log_backup_count: int = Field(default=10, ge=1, le=100, env="AUDIT_LOG_BACKUP_COUNT")
    audit_log_format: str = Field(default="json", env="AUDIT_LOG_FORMAT")

    # Security Headers
    security_headers_enabled: bool = Field(default=True, env="SECURITY_HEADERS_ENABLED")
    csp_policy: str = Field(
        default="default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self' https://integrate.api.nvidia.com; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
        env="CSP_POLICY",
    )
    hsts_max_age: int = Field(default=31536000, env="HSTS_MAX_AGE")
    hsts_include_subdomains: bool = Field(default=True, env="HSTS_INCLUDE_SUBDOMAINS")
    hsts_preload: bool = Field(default=True, env="HSTS_PRELOAD")

    # CORS
    cors_allowed_origins: List[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        env="CORS_ALLOWED_ORIGINS",
    )
    cors_allow_credentials: bool = Field(default=False, env="CORS_ALLOW_CREDENTIALS")
    cors_allowed_methods: List[str] = Field(default=["GET", "POST", "DELETE", "OPTIONS"], env="CORS_ALLOWED_METHODS")
    cors_allowed_headers: List[str] = Field(default=["Content-Type", "Authorization", "X-Request-ID"], env="CORS_ALLOWED_HEADERS")
    cors_expose_headers: List[str] = Field(default=["X-Request-ID", "Retry-After"], env="CORS_EXPOSE_HEADERS")

    # Environment
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")

    class Config:
        env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
        env_file_encoding = "utf-8"
        case_sensitive = False
        protected_namespaces = ("settings_",)
        extra = "allow"

    @field_validator("jwt_secret_key")
    @classmethod
    def _validate_jwt_secret(cls, v: str) -> str:
        if not v or v == "your_jwt_secret_key_here" or len(v) < 32:
            if cls._is_production():
                raise ValueError("JWT_SECRET_KEY must be at least 32 characters in production")
        return v

    @field_validator("session_cookie_samesite")
    @classmethod
    def _validate_samesite(cls, v: str) -> str:
        if v.lower() not in ("strict", "lax", "none"):
            raise ValueError("SESSION_COOKIE_SAMESITE must be 'strict', 'lax', or 'none'")
        return v.lower()

    @field_validator("environment")
    @classmethod
    def _validate_environment(cls, v: str) -> str:
        if v.lower() not in ("development", "staging", "production"):
            raise ValueError("ENVIRONMENT must be 'development', 'staging', or 'production'")
        return v.lower()

    @staticmethod
    def _is_production() -> bool:
        return os.getenv("ENVIRONMENT", "development").lower() == "production"


_security_settings: Optional[SecuritySettings] = None


def get_security_settings() -> SecuritySettings:
    """Get singleton instance of SecuritySettings."""
    global _security_settings
    if _security_settings is None:
        _security_settings = SecuritySettings()
    return _security_settings