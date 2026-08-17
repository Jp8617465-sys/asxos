"""Pins on scripts/backup_irreplaceable.sh — content assertions, no execution.

The script runs only in the backup workflow with real credentials, so these
tests pin the two 2026-08-08 fixes at the text level, where regressions of
both kinds (a table quietly dropped from the dump list, the token moving back
into a URL) are visible and cheap to catch.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).parent.parent / "scripts" / "backup_irreplaceable.sh"
_TEXT = _SCRIPT.read_text(encoding="utf-8")
_WORKFLOW = Path(__file__).parent.parent / ".github" / "workflows" / "backup.yml"
_WORKFLOW_TEXT = _WORKFLOW.read_text(encoding="utf-8")


def test_script_parses() -> None:
    """bash -n: the script must at least be syntactically valid shell."""
    proc = subprocess.run(
        ["bash", "-n", str(_SCRIPT)], capture_output=True, text=True
    )
    assert proc.returncode == 0, proc.stderr


@pytest.mark.parametrize(
    "table",
    [
        # pre-existing set
        "holding_lots", "decisions", "screening_rules", "model_versions",
        "profiles", "themes", "theses", "thesis_revisions", "theme_holdings",
        # the four CLAUDE.md calls irreplaceable that were MISSING from the
        # dump until 2026-08-08 — the governance audit trail among them
        "macro_theses", "agent_runs", "agent_evidence", "governance_events",
        # migration 0043 creates an irreplaceable revision ledger. The script
        # includes it conditionally so this backup change can deploy first.
        "price_revisions",
    ],
)
def test_irreplaceable_table_is_in_dump_list(table: str) -> None:
    assert f"--table={table}" in _TEXT, (
        f"{table} is irreplaceable per CLAUDE.md and must be in the pg_dump list"
    )


def test_token_never_rides_in_a_git_url() -> None:
    """git echoes remote URLs verbatim in fatal messages (CWE-532).

    The clone previously embedded the contents:rw PAT as
    https://x-access-token:${TOKEN}@github.com/... — one repository-not-found
    away from the token in the runner log. The token may only reach git via a
    credential-store file inside $WORK (cleaned by the existing trap).
    """
    assert "@github.com/${BACKUP_REPO}" not in _TEXT, (
        "token-bearing clone URL reintroduced"
    )
    assert 'credential.helper="store --file=' in _TEXT
    assert "umask 077" in _TEXT, "credential file must not be world-readable"
    # The credential file lives inside $WORK so the trap removes it.
    assert 'CRED="$WORK/.git-credentials"' in _TEXT
    assert "trap 'rm -rf \"$WORK\"' EXIT" in _TEXT


def test_clone_url_is_clean() -> None:
    """The remote URL git sees (and may echo) carries no userinfo at all."""
    assert '"https://github.com/${BACKUP_REPO}.git" repo' in _TEXT


def test_price_revision_backup_is_pre_migration_compatible() -> None:
    """The backup must stay green both before and after 0043 is applied."""
    assert "to_regclass('public.price_revisions') IS NOT NULL" in _TEXT
    assert "OPTIONAL_TABLE_ARGS=()" in _TEXT
    assert "OPTIONAL_TABLE_ARGS+=(--table=price_revisions)" in _TEXT
    assert '"${OPTIONAL_TABLE_ARGS[@]}"' in _TEXT


def test_restore_drill_covers_revision_rows_and_sequence() -> None:
    """Restore proof includes ledger contents and keeps BIGSERIAL usable."""
    assert "governance_events, price_revisions RESTART IDENTITY" in _WORKFLOW_TEXT
    assert "agent_evidence governance_events price_revisions" in _WORKFLOW_TEXT
    assert "pg_get_serial_sequence('public.price_revisions', 'revision_id')" in (
        _WORKFLOW_TEXT
    )
    assert "all 14 table counts match" in _WORKFLOW_TEXT
