from pathlib import Path

from pydantic import PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path.home() / "Projects" / "asxos-secrets" / ".env.production"
_MODEL_CONFIG = SettingsConfigDict(
    env_file=_ENV_FILE,
    env_file_encoding="utf-8",
    extra="ignore",
)


class CoreSettings(BaseSettings):
    """Settings required by every Render service (API, cron jobs, workers).

    Only ``database_url`` is unconditionally required. ``eodhd_api_key`` has a
    safe default of ``""`` so that DB-only jobs (generate_signals, compose_brief,
    ingest_regulatory, build_portfolio, retrain_model_a) can start without it.
    EODHD ingest jobs validate the key at call time via ``get_client()``.
    """

    model_config = _MODEL_CONFIG

    # Required — present on every Render service
    database_url: PostgresDsn

    # Optional at CoreSettings level — only EODHD ingest jobs need this.
    # generate_signals, compose_brief, ingest_regulatory etc. never call EODHD;
    # they should not crash on startup if the key is absent on their service.
    # get_client() in eodhd.py guards against an empty key before any API call.
    eodhd_api_key: str = ""

    # Optional operational fields
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
    healthcheck_url_build_portfolio: str = ""  # M13.7
    healthcheck_url_ingest_news: str = ""      # M14a
    healthcheck_url_ingest_sentiment: str = ""  # M14b
    healthcheck_url_snapshot_portfolio: str = ""     # M-Thesis-0
    healthcheck_url_check_cron_health: str = ""      # Phase-0
    healthcheck_url_ingest_market_context: str = ""  # M-Market-Context
    healthcheck_url_ingest_underlyings: str = ""     # M-Underlyings
    healthcheck_url_check_us_positions: str = ""        # M-Position-Monitor
    healthcheck_url_check_au_positions: str = ""        # M-Position-Monitor AU
    healthcheck_url_check_thesis_invalidations: str = ""  # thesis invalidation checker

    # Local dev only — skips migration drift check when Supabase branch is absent
    skip_migration_drift_check: bool = False

    @field_validator("database_url", mode="before")
    @classmethod
    def require_database_url(cls, v: str) -> str:
        if not v:
            raise ValueError("DATABASE_URL is required and must not be empty")
        return v


class BriefSettings(BaseSettings):
    """Settings required by the API and compose_brief services only.

    All fields are required — no defaults. Importing this class in a service
    that lacks these env vars will raise a hard ValidationError at startup,
    preserving the hard-fail guarantee for the API and email delivery path.
    """

    model_config = _MODEL_CONFIG

    # Supabase client (API service)
    supabase_url: str
    supabase_anon_key: str

    # Email delivery (compose_brief)
    resend_api_key: str
    brief_from_email: str
    brief_to_email: str


core_settings = CoreSettings()  # type: ignore[call-arg]  # pydantic-settings reads from env vars

# BriefSettings is NOT instantiated here — only asxos/brief/email.py and
# asxos/api/main.py import and instantiate it. This means job-only services
# (ingest_news, ingest_regulatory, etc.) that import asxos.config never
# trigger BriefSettings validation, so they don't need the brief env vars.

# Backwards-compat alias — all existing imports of `from asxos.config import settings`
# continue to resolve to CoreSettings without touching every file.
settings = core_settings
