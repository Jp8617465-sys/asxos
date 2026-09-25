"""The one ``SettingsConfigDict`` every settings class in this package shares.

A leaf module: it instantiates nothing. ``asxos.config`` builds ``CoreSettings()`` at import
time and hard-fails without ``DATABASE_URL`` (CLAUDE.md rule #1) — right for every job that
has a database, fatal for the GitHub-only lanes (``daily-digest``, ``backlog-roll``'s script
steps), which hold a PAT and nothing else. A settings class that must be importable there
(``asxos.clock``) takes its config from here, never from ``asxos.config``. Incident #389.
"""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import SettingsConfigDict

ENV_FILE = Path.home() / "Projects" / "asxos-secrets" / ".env.production"
MODEL_CONFIG = SettingsConfigDict(
    env_file=ENV_FILE,
    env_file_encoding="utf-8",
    extra="ignore",
)
