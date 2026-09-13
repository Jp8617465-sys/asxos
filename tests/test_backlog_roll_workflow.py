"""Pins on ``backlog-roll.yml`` after the 2026-09-10 chief-of-staff rollout.

The lane collapsed from ``roll -> verify(matrix) -> publish(matrix) -> record`` to one
job plus the ledger job. What the old four-job split bought — keeping a checkout
credential away from the verification of agent-authored code — stopped paying once arbi
lands its own work under a single scoped PAT.

What did NOT change, and is still pinned here:

* the deterministic picker runs first and its input is validated, not interpolated;
* branch names are validated against a strict pattern before anything is pushed or opened;
* verification is a workflow STEP against an immutable SHA, re-asserted against the remote
  ref — an agent saying "tests pass" and a CI step saying so are not the same claim;
* the deadman fails the run when ``HC_BACKLOG_URL`` is unset. That is observability, not
  autonomy: both prior loops died as unobserved silence (backlog item A-20).
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = (ROOT / ".github/workflows/backlog-roll.yml").read_text(encoding="utf-8")


def test_backlog_roll_is_manual_only_with_no_armed_cadence() -> None:
    """Dispatch-only. No cadence is armed until ARBI_GITHUB_TOKEN exists."""
    trigger_block = WORKFLOW.split("concurrency:", 1)[0]
    assert "workflow_dispatch:" in trigger_block
    assert "\n  schedule:" not in trigger_block
    assert "\n  workflow_run:" not in trigger_block
    # The owner/actor gate and the per-run risk acknowledgement went with the
    # attended-vs-unattended split (AGENTS.md §0, retired 2026-09-10).
    assert "acknowledge_write_token_risk" not in WORKFLOW
    assert "github.actor ==" not in WORKFLOW
    assert "ARBI_UNATTENDED" not in WORKFLOW


def test_picker_input_and_agent_branch_outputs_are_validated() -> None:
    assert "MAX_ITEMS: ${{ inputs.max_items }}" in WORKFLOW
    assert '"$MAX_ITEMS" =~ ^[1-3]$' in WORKFLOW
    assert 'scripts/backlog_next.py --max "$MAX_ITEMS"' in WORKFLOW
    assert 'scripts/backlog_next.py --max "${{ inputs.max_items }}"' not in WORKFLOW
    assert "^claude/backlog-[a-e]-[0-9]+[a-z]?-[0-9]{8}$" in WORKFLOW
    assert '"refs/heads/$branch"' in WORKFLOW
    assert "duplicate backlog id in branch list" in WORKFLOW
    assert "agent returned more branches than the lane limit" in WORKFLOW


def test_the_lane_runs_in_auto_mode_with_the_pat() -> None:
    assert "--permission-mode auto" in WORKFLOW
    assert "--allowedTools" not in WORKFLOW
    assert "token: ${{ secrets.ARBI_GITHUB_TOKEN }}" in WORKFLOW
    assert "persist-credentials: true" in WORKFLOW


def test_verification_is_a_step_against_a_re_asserted_immutable_sha() -> None:
    """The SHA re-assertion survives the job collapse — it is what "verified" means."""
    assert "python -m pytest -q" in WORKFLOW
    assert "ruff check ." in WORKFLOW
    assert "mypy asxos" in WORKFLOW
    assert 'test "$remote_sha" = "$VERIFIED_SHA"' in WORKFLOW
    assert 'test "$(git rev-parse HEAD)" = "$VERIFIED_SHA"' in WORKFLOW


def test_ledger_and_deadman_still_observe_the_run() -> None:
    record = WORKFLOW.split("\n  record:\n", 1)[1]
    assert "needs: [roll]" in record
    assert "if: always()" in record
    assert '"$HC_BACKLOG_URL/fail"' in record
    # Fail-closed at STEP 0: the lane refuses to run where nobody will see the heartbeat.
    assert "this lane refuses to run unwatched" in WORKFLOW
