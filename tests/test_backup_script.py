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


def test_backup_workflow_schedule_unchanged() -> None:
    """Pins the daily backup cron so a silent schedule drift fails the same PR

    instead of only surfacing on the next missed day. Replaces the coverage
    lost when tests/test_render_backup_build.py was deleted (Render's cron
    declaration is gone; the workflow's own schedule is now the single
    source of truth).
    """
    assert 'cron: "30 13 * * *"' in _WORKFLOW_TEXT


def test_backup_workflow_entrypoint_unchanged() -> None:
    """The backup job must still invoke the pinned script, not an inline dump."""
    assert "run: bash scripts/backup_irreplaceable.sh" in _WORKFLOW_TEXT


def test_backup_workflow_declares_expected_env_vars() -> None:
    """The three secrets the script needs must stay wired to the job env."""
    assert "DATABASE_URL: ${{ secrets.DATABASE_URL }}" in _WORKFLOW_TEXT
    assert "BACKUP_GITHUB_TOKEN: ${{ secrets.BACKUP_GITHUB_TOKEN }}" in _WORKFLOW_TEXT
    assert "BACKUP_REPO: ${{ secrets.BACKUP_REPO }}" in _WORKFLOW_TEXT


def test_restore_drill_covers_revision_rows_and_sequence() -> None:
    """Restore proof includes ledger contents and keeps BIGSERIAL usable."""
    assert "governance_events, price_revisions RESTART IDENTITY" in _WORKFLOW_TEXT
    assert "agent_evidence governance_events price_revisions" in _WORKFLOW_TEXT
    assert "pg_get_serial_sequence('public.price_revisions', 'revision_id')" in (
        _WORKFLOW_TEXT
    )
    assert "all 14 table counts match" in _WORKFLOW_TEXT


# --- 2026-09-02 (campaign node H0-B): the 11-day silent outage --------------
#
# From 2026-08-23 to 2026-09-01 the frozen-evidence sha256 assertion exited
# BEFORE the dump was copied into the backup repo: 12 consecutive red scheduled
# runs, and not one dump pushed. Nothing below executes the script; these pins
# make the ORDER and the coverage visible at review time, which is the only
# place a bash script's control flow actually gets reviewed.


@pytest.mark.parametrize(
    "table",
    [
        # migration 0048 — the decision spine. Append-only and content-addressed,
        # recording what James saw and decided; not re-derivable from anything
        # else (arbi decision D-1 under Amendment H).
        "evidence_packets",
        "thesis_versions",
        "challenge_results",
        "portfolio_assessments",
        "decision_packets",
    ],
)
def test_decision_engine_table_is_in_dump_list(table: str) -> None:
    assert f"--table={table}" in _TEXT, (
        f"{table} (0048) is irreplaceable and must be in the pg_dump list"
    )


def test_decision_engine_tables_are_conditional_like_price_revisions() -> None:
    """The script must stay green against a schema where 0048 is not applied."""
    assert "to_regclass('public.decision_packets') IS NOT NULL" in _TEXT
    assert "DECISION_ENGINE_TABLE_ARGS=()" in _TEXT
    assert '"${DECISION_ENGINE_TABLE_ARGS[@]}"' in _TEXT


def test_dump_is_pushed_before_the_frozen_evidence_check_runs() -> None:
    """Contain irreversible loss first (target-architecture.md Errata E7).

    Verifying a FROZEN archive must never withhold the backup of the LIVE
    tables that archive does not cover. Pin: the cp and push of today's dump
    both precede the digest loop, and the failure path says so out loud.
    """
    cp_at = _TEXT.index('cp "$DUMP_GZ" "$WORK/repo/"')
    push_at = _TEXT.index("git push origin HEAD")
    loop_at = _TEXT.index('for pair in "signals:$SIGNALS_SHA256"')
    assert cp_at < push_at < loop_at
    assert "WAS pushed before this check ran" in _TEXT


def test_frozen_evidence_check_accepts_raw_or_gunzipped_bytes() -> None:
    """The recorded digests do not say whether they were taken pre- or post-gzip.

    Matching either representation keeps the assertion strict — the bytes must
    still equal a recorded digest — while removing the one ambiguity that the
    very first scheduled run of this check failed on.
    """
    assert "gzip -dc" in _TEXT
    for digest in (
        "e61ee6a4d1774194b86ff2072c362315142ed31bb1d66db7a2a21b5f30d57828",
        "7aef52345d4d93d50e10428a3233b725d677f26873077b2b00e2623a0b7f3b8f",
    ):
        # once in the header, once in the constant — they must not drift apart
        assert _TEXT.count(digest) == 2


def test_verification_failure_tells_the_deadman_it_failed() -> None:
    """A red verification pings /fail; only a clean run pings success.

    Silence is reserved for "never ran" — that is the whole point of a deadman
    (docs/RUNBOOK.md, deadman section).
    """
    assert 'ping_deadman "/fail"' in _TEXT
    assert 'ping_deadman ""' in _TEXT
    assert _TEXT.index('ping_deadman "/fail"') < _TEXT.index('ping_deadman ""')
