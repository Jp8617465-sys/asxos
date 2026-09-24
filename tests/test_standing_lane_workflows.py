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


def test_standing_lanes_keep_a_manual_path_and_never_arm_workflow_run() -> None:
    """A cadence may be armed; `workflow_run` may not, and dispatch must survive.

    REWRITTEN 2026-09-20 with the arming PR. It previously read "Dispatch-only. No
    cadence is armed until ARBI_GITHUB_TOKEN exists" and asserted no `schedule:`
    at all — a premise that expired on 2026-09-14 when James created that secret.
    A guard whose stated reason has lapsed is not a guard, it is a tripwire nobody
    can act on, so it is re-derived here rather than deleted or loosened.

    What survives, and why each half is load-bearing:

    `workflow_run` stays banned, and this is the stronger of the two. It is a
    PR-head trigger by `tools/workflow_inventory.py`'s classification, and
    `test_live_repo_exposure_set_is_pinned` holds the repo's exposure set empty —
    no workflow reaching a repository secret at a pull-request head, which is ACP
    phase P1's requirement. These two lanes carry ARBI_GITHUB_TOKEN. The obvious
    reactive design for `nightly-triage` is `workflow_run` on `nightly-check`, and
    it was the arming PR's first draft; the guard caught it. A clock is used
    instead, with a deterministic gate job standing in for the cost saving.

    `workflow_dispatch` stays, so a human can always run a lane now rather than
    waiting for its slot.

    Arming a `schedule:` remains Amber (AGENTS.md §6) and still needs A-22's
    second proof — this test does not grant that, it only stops asserting a reason
    that no longer holds.
    """
    for workflow in (NIGHTLY, TOOLWATCH):
        assert "workflow_dispatch:" in workflow

        trigger_block = workflow.split("concurrency:", 1)[0]
        assert "\n  workflow_run:" not in trigger_block, (
            "workflow_run is a PR-head trigger; arming it on a PAT-bearing lane "
            "would re-open the exposure surface P1 closed"
        )

        # The owner/actor gate and the per-run risk acknowledgement went with the
        # attended-vs-unattended split (retired 2026-09-10).
        assert "acknowledge_write_token_risk" not in workflow
        assert "github.actor ==" not in workflow
        assert "ARBI_UNATTENDED" not in workflow


def test_a_scheduled_nightly_triage_cannot_reach_the_agent_on_a_green_night() -> None:
    """A daily clock is only affordable because a cheap job stands in front of it.

    An agent run costs roughly US$2.50 (measured: weekly-toolwatch run
    34846052898, 44 turns, $2.52). Firing it every night to discover nothing is
    broken is how the two previous scheduled loops in this repo earned being
    switched off. If `nightly-triage` ever carries a `schedule:`, the agent job
    must sit behind a deterministic gate.
    """
    trigger_block = NIGHTLY.split("concurrency:", 1)[0]
    if "\n  schedule:" not in trigger_block:
        return  # not armed; nothing to constrain
    assert "\n  gate:" in NIGHTLY, "a scheduled nightly-triage needs its STEP 0 gate job"
    assert "needs: gate" in NIGHTLY
    assert "if: needs.gate.outputs.red == 'true'" in NIGHTLY
    # The gate must be deterministic and read-only: no agent, no write scope.
    gate_block = NIGHTLY.split("\n  gate:", 1)[1].split("\n  triage:", 1)[0]
    assert "claude-code-action" not in gate_block
    assert "ARBI_GITHUB_TOKEN" not in gate_block
    assert "actions: read" in gate_block


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
