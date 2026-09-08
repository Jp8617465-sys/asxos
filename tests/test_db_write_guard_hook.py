"""Tests for ``.claude/hooks/db-write-guard.sh`` — the always-on PreToolUse guard for
migration application and destructive-DDL-shaped queries against the read-only DB
connection.

Unlike push-guard.sh / pr-draft-guard.sh, this hook has no attended/STANDING split:
both denies here are absolute exclusions (James, 2026-09-08) — a git revert cannot
undo an applied migration or an executed write against live data, so neither is
conditioned on AUTONOMY the way merge authority is. The destructive-keyword check
is relocated from unattended-guard.sh's former `*execute_sql)` case, which was
ARBI_UNATTENDED-gated and therefore dead code in every attended session (measured,
2026-09-08, every session run so far). Moving it here makes it fire regardless of
who's watching, matching its status as an always-ask exclusion rather than an
unattended-only one.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "db-write-guard.sh"

pytestmark = pytest.mark.skipif(shutil.which("jq") is None, reason="db-write-guard.sh needs jq on PATH")


def run_hook(tool_name: str, tool_input: dict) -> dict:
    proc = subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps({"tool_name": tool_name, "tool_input": tool_input}),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, f"hook exited {proc.returncode}: {proc.stderr}"
    out = proc.stdout.strip()
    return {} if not out else json.loads(out)["hookSpecificOutput"]


def _is_deny(decision: dict) -> bool:
    return decision.get("permissionDecision") == "deny"


def test_missing_jq_fails_closed() -> None:
    proc = subprocess.run(
        [shutil.which("bash") or "/bin/bash", str(HOOK)],
        input=json.dumps({"tool_name": "mcp__supabase__apply_migration", "tool_input": {}}),
        capture_output=True,
        text=True,
        env={"PATH": ""},
    )
    assert proc.returncode == 0
    assert _is_deny(json.loads(proc.stdout)["hookSpecificOutput"])


# --- DENY: migration application, unconditional, any server spelling -----------------


@pytest.mark.parametrize(
    "tool_name",
    [
        "mcp__supabase__apply_migration",
        "mcp__Supabase__apply_migration",
        "mcp__supabase-ro__apply_migration",
    ],
)
def test_apply_migration_always_denied(tool_name: str) -> None:
    decision = run_hook(tool_name, {"migration_name": "0049_x", "query": "ALTER TABLE t ADD COLUMN c int;"})
    assert _is_deny(decision)
    assert "reserved to James" in decision["permissionDecisionReason"]


# --- DENY: destructive/write-shaped query against the READ-ONLY server --------------


@pytest.mark.parametrize(
    "query",
    [
        "DROP TABLE signals;",
        "TRUNCATE signals;",
        "ALTER TABLE signals ADD COLUMN x int;",
        "INSERT INTO signals (a) VALUES (1);",
        "UPDATE signals SET a = 1;",
        "DELETE FROM signals;",
        "GRANT SELECT ON signals TO anon;",
        "SELECT approve_object('t', 1);",
        "select nextval('some_seq');",
        "-- a sneaky comment\nDROP TABLE signals;",
        "/* block comment */ TRUNCATE signals;",
    ],
)
def test_destructive_query_denied_on_ro_server(query: str) -> None:
    decision = run_hook("mcp__supabase-ro__execute_sql", {"query": query})
    assert _is_deny(decision)
    assert "read-only DB connection" in decision["permissionDecisionReason"]


def test_destructive_query_denied_on_ro_server_case_insensitive_name() -> None:
    decision = run_hook("mcp__Supabase-ro__execute_sql", {"query": "drop table signals;"})
    assert _is_deny(decision)


# --- ALLOW (silent, falls through): ordinary reads and non-matching tools ------------


@pytest.mark.parametrize(
    "query",
    [
        "SELECT * FROM signals LIMIT 10;",
        "SELECT count(*) FROM job_runs;",
        "-- just a read\nSELECT id FROM theses;",
    ],
)
def test_ordinary_read_falls_through(query: str) -> None:
    decision = run_hook("mcp__supabase-ro__execute_sql", {"query": query})
    assert decision == {}


def test_write_server_execute_sql_is_out_of_scope_for_this_hook() -> None:
    # The write-capable server's execute_sql is NOT hard-blocked here — that stays
    # unattended-guard.sh's job (deny when ARBI_UNATTENDED=1) so that, once
    # AUTONOMY=STANDING, an ordinary non-destructive production write through an
    # existing job is not caught by an absolute exclusion it was never meant to be
    # in. Only content matching the destructive-keyword list is denied, and only
    # against the read-only server's own tool name.
    decision = run_hook("mcp__supabase__execute_sql", {"query": "SELECT 1;"})
    assert decision == {}


def test_unrelated_tool_falls_through() -> None:
    decision = run_hook("mcp__supabase-ro__list_tables", {})
    assert decision == {}
    decision = run_hook("Read", {"file_path": "foo.py"})
    assert decision == {}


def test_missing_tool_name_falls_through() -> None:
    proc = subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps({"tool_input": {}}),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert proc.stdout.strip() == ""
