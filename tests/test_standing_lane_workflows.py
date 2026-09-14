"""Pins on the ``nightly-triage`` and ``weekly-toolwatch`` lanes after the 2026-09-10 rollout.

Both collapsed to one job. ``nightly-triage`` previously ran
``triage -> verify -> publish`` across three credentials so that agent-authored code was
executed by a read-only job; with arbi landing its own work under a single scoped PAT that
separation bought nothing.

What survives, and is pinned here: agent-controlled values are still validated before they
reach a shell, verification is still a workflow STEP against a re-asserted immutable SHA
rather than an agent's self-report, and the diagnosis artifact still lands on the ledger
branch so a run leaves evidence even when it finds nothing.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NIGHTLY = (ROOT / ".github/workflows/nightly-triage.yml").read_text()
TOOLWATCH = (ROOT / ".github/workflows/weekly-toolwatch.yml").read_text()


def test_standing_lanes_are_manual_only_with_no_armed_cadence() -> None:
    """Dispatch-only. No cadence is armed until ARBI_GITHUB_TOKEN exists."""
    for workflow in (NIGHTLY, TOOLWATCH):
        assert "workflow_dispatch:" in workflow

        trigger_block = workflow.split("concurrency:", 1)[0]
        assert "\n  schedule:" not in trigger_block
        assert "\n  workflow_run:" not in trigger_block

        # The owner/actor gate and the per-run risk acknowledgement went with the
        # attended-vs-unattended split (retired 2026-09-10).
        assert "acknowledge_write_token_risk" not in workflow
        assert "github.actor ==" not in workflow
        assert "ARBI_UNATTENDED" not in workflow


def test_standing_lanes_run_in_auto_mode_with_the_pat() -> None:
    for workflow in (NIGHTLY, TOOLWATCH):
        assert "--permission-mode auto" in workflow
        assert "--allowedTools" not in workflow
        assert "token: ${{ secrets.ARBI_GITHUB_TOKEN }}" in workflow
        assert "persist-credentials: true" in workflow


def test_nightly_validates_agent_controlled_inputs_before_shell_use() -> None:
    assert "^claude/triage-[0-9]{8}-[a-z0-9-]+$" in NIGHTLY
    assert '"$name"' in NIGHTLY
    assert '"refs/heads/$name"' in NIGHTLY
    assert '"$REQUESTED_RUN_ID" =~ ^[0-9]+$' in NIGHTLY
    assert "REQUESTED_RUN_ID: ${{ inputs.run_id }}" in NIGHTLY
    assert '"${{ steps.branch.outputs.name }}"' not in NIGHTLY


def test_nightly_verifies_a_re_asserted_immutable_sha_as_a_workflow_step() -> None:
    """"Verified" has to mean a specific commit, not "whatever the branch head is now"."""
    assert "python -m pytest -q" in NIGHTLY
    assert "ruff check ." in NIGHTLY
    assert "mypy asxos" in NIGHTLY
    assert 'test "$(git rev-parse HEAD)" = "$EXPECTED_SHA"' in NIGHTLY
    assert 'test "$remote_sha" = "$VERIFIED_SHA"' in NIGHTLY


def test_diagnosis_is_persisted_on_the_ledger_branch() -> None:
    assert "docs/ops/triage-diagnoses/${GITHUB_RUN_ID}.md" in NIGHTLY
    assert ".triage-diagnosis.md must be a regular, non-symlink file" in NIGHTLY
    assert ".triage-diagnosis.md exceeds 64 KiB" in NIGHTLY
