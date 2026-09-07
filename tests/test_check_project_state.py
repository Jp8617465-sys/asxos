"""Tests for ``scripts/check_project_state.py`` — the snapshot validator seam.

Complements ``tests/test_project_state_snapshot_schema.py`` (which pins the
frozen SB1-01 schema itself). This file pins the *consumer*: the CLI that CI
and wakes run against ``docs/product/state/latest-snapshot.json``.

The load-bearing test is :func:`test_checked_in_snapshot_validates`: the real
checked-in artifact must always validate against the frozen v1 schema, so a
schema drift or a hand-mangled snapshot fails the ordinary pytest lane
(``full-check``) with **no workflow-file change needed**. Freshness is
deliberately NOT tested here — a snapshot ages by the clock, and a test that
reddens from time passing trains people to ignore it (the validator's
``--schema-only`` flag exists for exactly this split).
"""

from __future__ import annotations

# Import the script as a module. scripts/ is not a package; load by path so
# the test exercises the exact file CI runs, not a copy.
import importlib.util
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from asxos.secondbrain.project_state import ProjectStateSnapshot

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_project_state.py"
_spec = importlib.util.spec_from_file_location("check_project_state", _SCRIPT)
assert _spec is not None and _spec.loader is not None
check_project_state = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check_project_state)

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SNAPSHOT_PATH = _REPO_ROOT / "docs" / "product" / "state" / "latest-snapshot.json"


def _minimal_snapshot(observed_at: str = "2026-08-20T04:40:00Z") -> dict[str, Any]:
    """A minimal, synthetic, schema-valid snapshot dict (never live data).

    Each leaf is a fresh dict (not one shared alias) so a future test that
    mutates a leaf in place cannot silently change all eleven.
    """

    def leaf() -> dict[str, Any]:
        return {"status": "observed", "value": "x"}

    return {
        "snapshot_id": "snap-test",
        "schema_version": 1,
        "observed_at": observed_at,
        "repository": {"base_sha": leaf(), "branch": leaf(), "dirty_state": leaf()},
        "github": {"open_prs": leaf(), "recent_merges": leaf(), "workflow_runs": leaf()},
        "production": {"release_identity": leaf(), "scheduler_owners": leaf()},
        "data": {"migrations": leaf(), "freshness": leaf(), "coverage": leaf()},
        "probes": [],
    }


def test_checked_in_snapshot_validates() -> None:
    """The real artifact must always validate against the frozen v1 schema."""
    snapshot = check_project_state.load_snapshot(_SNAPSHOT_PATH)
    assert isinstance(snapshot, ProjectStateSnapshot)
    assert snapshot.schema_version == 1


def test_valid_snapshot_passes_schema_only(tmp_path: Path) -> None:
    path = tmp_path / "snap.json"
    path.write_text(json.dumps(_minimal_snapshot()))
    assert check_project_state.main([str(path), "--schema-only"]) == 0


def test_extra_field_fails_the_freeze(tmp_path: Path) -> None:
    """extra="forbid" is the mechanical half of the freeze rule — the
    validator must reject a snapshot smuggling an undeclared field."""
    data = _minimal_snapshot()
    data["smuggled"] = True
    path = tmp_path / "snap.json"
    path.write_text(json.dumps(data))
    assert check_project_state.main([str(path), "--schema-only"]) == 1


def test_stale_snapshot_fails_freshness(tmp_path: Path) -> None:
    old = (datetime.now(UTC) - timedelta(days=30)).isoformat()
    path = tmp_path / "snap.json"
    path.write_text(json.dumps(_minimal_snapshot(observed_at=old)))
    assert check_project_state.main([str(path), "--max-age-days", "7"]) == 1
    # ...but the same stale file passes schema-only (CI mode).
    assert check_project_state.main([str(path), "--schema-only"]) == 0


def test_missing_file_is_cannot_run_not_fail(tmp_path: Path) -> None:
    """Exit 2 (cannot run) is distinct from exit 1 (checked and failed) —
    same convention as check_ledger_coverage.sh / check_doc_expiry.sh."""
    assert check_project_state.main([str(tmp_path / "nope.json")]) == 2


def test_malformed_json_is_cannot_run(tmp_path: Path) -> None:
    path = tmp_path / "snap.json"
    path.write_text("{not json")
    assert check_project_state.main([str(path)]) == 2


def test_staleness_boundary() -> None:
    now = datetime(2026, 8, 20, tzinfo=UTC)
    snap = ProjectStateSnapshot.model_validate(
        _minimal_snapshot(observed_at=(now - timedelta(days=7)).isoformat())
    )
    assert check_project_state.freshness_problem(snap, now=now, max_age_days=7) is None
    snap_old = ProjectStateSnapshot.model_validate(
        _minimal_snapshot(observed_at=(now - timedelta(days=7, seconds=1)).isoformat())
    )
    problem = check_project_state.freshness_problem(snap_old, now=now, max_age_days=7)
    assert problem is not None and "7d old" in problem


def test_future_dated_snapshot_fails_freshness() -> None:
    """A snapshot claiming observation in the future is corrupt evidence and
    must FAIL the freshness lane, never PASS (refactoring-expert review)."""
    now = datetime(2026, 8, 20, tzinfo=UTC)
    snap_future = ProjectStateSnapshot.model_validate(
        _minimal_snapshot(observed_at=(now + timedelta(days=365)).isoformat())
    )
    problem = check_project_state.freshness_problem(snap_future, now=now, max_age_days=7)
    assert problem is not None and "future" in problem
    # ...while honest clock skew inside the allowance stays fresh.
    snap_skew = ProjectStateSnapshot.model_validate(
        _minimal_snapshot(observed_at=(now + timedelta(minutes=2)).isoformat())
    )
    assert check_project_state.freshness_problem(snap_skew, now=now, max_age_days=7) is None


def test_non_utf8_file_is_cannot_run(tmp_path: Path) -> None:
    """A binary/non-UTF-8 file is 'unreadable' (exit 2), not 'checked and
    failed' (exit 1) — UnicodeDecodeError must not escape as a traceback."""
    path = tmp_path / "snap.json"
    path.write_bytes(b"\xff\xfe\x00\x01 not utf-8")
    assert check_project_state.main([str(path)]) == 2


def test_observed_null_leaf_rejected(tmp_path: Path) -> None:
    """A null-valued 'observed' leaf must fail — the schema's own invariant,
    re-asserted through the CLI so the seam can't silently weaken it."""
    data = _minimal_snapshot()
    data["data"]["freshness"] = {"status": "observed", "value": None}
    path = tmp_path / "snap.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ValidationError):
        check_project_state.load_snapshot(path)


# --------------------------------------------------------------------------
# SB2 contradiction wiring
# --------------------------------------------------------------------------


def _snapshot_with_critical_contradiction() -> dict[str, Any]:
    """A leaf and its backing probe disagree on a scalar — `leaf_probe_value_mismatch`,
    the two-sources-disagree class SB2 exists for. (Until v3 this helper used
    `migration_drift`; that rule was retired with `REQUIRED_MIGRATIONS`, #189.)"""
    snap = _minimal_snapshot()
    snap["repository"]["base_sha"] = {"status": "observed", "value": "aaaa"}
    snap["probes"] = [
        {
            "name": "repository.base_sha",
            "status": "observed",
            "source": "test",
            "observed_at": snap["observed_at"],
            "value": "bbbb",
        }
    ]
    return snap


def test_critical_contradiction_fails_even_when_schema_and_freshness_pass(
    tmp_path: Path,
) -> None:
    path = tmp_path / "snap.json"
    path.write_text(json.dumps(_snapshot_with_critical_contradiction()), encoding="utf-8")

    assert check_project_state.main([str(path), "--schema-only"]) == 1


def test_contradiction_check_can_be_skipped(tmp_path: Path) -> None:
    """--no-contradictions leaves the pre-SB2 behaviour exactly as it was."""
    path = tmp_path / "snap.json"
    path.write_text(json.dumps(_snapshot_with_critical_contradiction()), encoding="utf-8")

    assert check_project_state.main([str(path), "--schema-only", "--no-contradictions"]) == 0


def test_the_checked_in_snapshot_has_no_critical_contradictions() -> None:
    """Guards the real artifact, not a fixture — this is the file wakes trust."""
    assert check_project_state.main(["--schema-only"]) == 0
