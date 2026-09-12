"""Application settings loaded from environment variables.

Mirrors `architecture.md` §10.1. Secrets and operational knobs come from
environment variables only; shipping `.env.example` documents every key.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven configuration for the backend service."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Core
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    database_url: str = "postgresql+asyncpg://user:pass@postgres:5432/reunionai"
    jwt_private_key: str = ""
    jwt_public_key: str = ""
    jwt_access_ttl_minutes: int = 15
    refresh_ttl_days: int = 30
    refresh_grace_seconds: int = 30
    argon2_memory_cost: int = 65536
    argon2_time_cost: int = 3
    argon2_parallelism: int = 4

    # Rate limiting
    rate_limit_login_ip: int = 5
    rate_limit_login_user: int = 20
    rate_limit_register_ip: int = 3
    rate_limit_refresh_ip: int = 30
    rate_limit_refresh_user: int = 60
    rate_limit_mfa_ip: int = 10
    rate_limit_mfa_user: int = 20

    # CORS
    cors_allow_origins: str = "http://localhost:3000,http://localhost:4321"

    # Bootstrap
    bootstrap_superadmin_email: str = "admin@reunionai.local"
    bootstrap_superadmin_password: str = "changeme"

    # Frontend
    frontend_url: str = "http://localhost:4321"

    @property
    def cors_allow_origins_list(self) -> list[str]:
        """Parse the comma-separated CORS origins into a list."""
        return [origin.strip() for origin in self.cors_allow_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
