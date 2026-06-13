"""
Regression coverage for the asxos-backup-irreplaceable Render build failure.

Root cause: the backup cron's buildCommand ran
``apt-get update && apt-get install -y postgresql-client && pip install -e .``
On Render's native (non-Docker) runtime the build environment mounts
``/var/lib/apt`` read-only, so apt-get fails with::

    E: List directory /var/lib/apt/lists/partial is missing.
       - Acquire (30: Read-only file system)

The fix removes the apt-get path and relies on pg_dump being present on the
native image, asserting its presence at build time via ``pg_dump --version``.

This test is static (parses render.yaml) and needs no database or network.
"""
from __future__ import annotations

import pathlib

import pytest

yaml = pytest.importorskip("yaml")

RENDER_YAML = pathlib.Path(__file__).resolve().parent.parent / "render.yaml"
BACKUP_SERVICE = "asxos-backup-irreplaceable"


def _backup_service() -> dict:
    doc = yaml.safe_load(RENDER_YAML.read_text())
    services = {s["name"]: s for s in doc["services"]}
    assert BACKUP_SERVICE in services, (
        f"{BACKUP_SERVICE} missing from render.yaml services"
    )
    return services[BACKUP_SERVICE]


def test_backup_build_command_has_no_apt_get():
    """The buildCommand must not shell out to apt-get on the native runtime."""
    build = _backup_service()["buildCommand"]
    assert "apt-get" not in build, (
        f"{BACKUP_SERVICE} buildCommand still uses apt-get (fails on Render's "
        f"read-only apt filesystem): {build!r}"
    )
    assert "apt-get install" not in build


def test_backup_build_command_still_installs_repo():
    """The fix must preserve repo installation so the package is importable."""
    build = _backup_service()["buildCommand"]
    assert "pip install -e ." in build, (
        f"{BACKUP_SERVICE} buildCommand must still install the repo: {build!r}"
    )


def test_backup_runtime_command_unchanged():
    """The backup script entrypoint must remain the runtime command."""
    svc = _backup_service()
    assert svc["command"] == "bash scripts/backup_irreplaceable.sh"
    # Schedule is not the subject of this fix but guard against accidental drift.
    assert svc["schedule"] == "30 13 * * *"


def test_backup_declares_expected_env_var_names():
    """The backup service must still wire the env vars the script requires
    (names only — values are sync:false / fromService and never checked here)."""
    svc = _backup_service()
    declared: set[str] = set()
    for entry in svc["envVars"]:
        if "key" in entry:
            declared.add(entry["key"])
        elif "fromService" in entry:
            declared.add(entry["fromService"]["envVarKey"])
    for required in ("DATABASE_URL", "BACKUP_GITHUB_TOKEN", "BACKUP_REPO"):
        assert required in declared, (
            f"{BACKUP_SERVICE} no longer declares {required}: {sorted(declared)}"
        )
