"""Mechanical guard for the D10 issue-snapshot retirement.

GitHub Issues are the work-state authority.  The former checked-in snapshot had
no reader, so neither its writer nor CI special-casing may return silently.
"""

from __future__ import annotations

from pathlib import Path

from asxos.secondbrain.contradictions import SCHEDULED_LANES

_ROOT = Path(__file__).parent.parent
_RETIRED_PATHS = (
    _ROOT / ".github" / "workflows" / "issue-snapshot.yml",
    _ROOT / "scripts" / "export_github_issues.sh",
    _ROOT / "docs" / "ops" / "github-issues-snapshot.json",
    _ROOT / "tests" / "test_issue_snapshot.py",
)


def test_issue_snapshot_runtime_surface_is_absent() -> None:
    assert [str(path.relative_to(_ROOT)) for path in _RETIRED_PATHS if path.exists()] == []


def test_full_check_has_no_snapshot_exclusion() -> None:
    full_check = (_ROOT / ".github" / "workflows" / "full-check.yml").read_text(
        encoding="utf-8"
    )
    assert "docs/ops/github-issues-snapshot.json" not in full_check


def test_issue_snapshot_is_not_a_scheduled_lane() -> None:
    assert "issue-snapshot" not in SCHEDULED_LANES
