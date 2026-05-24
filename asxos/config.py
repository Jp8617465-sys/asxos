from pathlib import Path

from pydantic import PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path.home() / "Projects" / "asxos-secrets" / ".env.production",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Required for all services
    database_url: PostgresDsn
    eodhd_api_key: str

    # Required for API / compose_brief — optional with empty defaults so that
    # job-only services (ingest_news, ingest_regulatory, etc.) don't need them.
    supabase_url: str = ""
    supabase_anon_key: str = ""
    resend_api_key: str = ""
    brief_from_email: str = ""
    brief_to_email: str = ""

    # Optional with defaults
    fred_api_key: str = ""
    asxos_tz: str = "Australia/Sydney"
    asxos_api_host: str = "127.0.0.1"
    asxos_api_port: int = 8788
    asxos_api_token: str = ""
    asxos_models_dir: Path = Path("./models")
    asxos_data_dir: Path = Path("./data")

    # Backup cron (M12+)
    backup_github_token: str = ""
    backup_repo: str = ""

    # Healthchecks ping URLs
    healthchecks_write_key: str = ""
    healthcheck_url_sync_prices: str = ""
    healthcheck_url_sync_fundamentals: str = ""
    healthcheck_url_generate_signals: str = ""
    healthcheck_url_ingest_regulatory: str = ""
    healthcheck_url_compose_brief: str = ""
    healthcheck_url_retrain_model_a: str = ""
    healthcheck_url_sync_universe: str = ""
    healthcheck_url_backup_irreplaceable: str = ""

    # M13.7 — portfolio cron healthcheck
    healthcheck_url_build_portfolio: str = ""

    # M14a — news ingestion healthcheck
    healthcheck_url_ingest_news: str = ""

    # Local dev only — skips migration drift check when Supabase branch is absent
    skip_migration_drift_check: bool = False

    @field_validator("database_url", mode="before")
    @classmethod
    def require_database_url(cls, v: str) -> str:
        if not v:
            raise ValueError("DATABASE_URL is required and must not be empty")
        return v


settings = Settings()
