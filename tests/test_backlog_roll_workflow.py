"""Pins on ``backlog-roll.yml`` — the build loop's scheduled lane (AGENTS.md §8a).

Rewired onto GitHub Issues on 2026-09-26. One job runs the four layers in order —
eligibility (code) → readiness (the agent, bounded) → apply (code, under the brakes) →
pick (code) → build (the agent) — plus the ledger job. What is pinned here:

* the layers run in that order and only two steps use a model;
* the brakes are repository variables, never literals in the workflow;
* the picker's input is validated, not interpolated; branch names match a strict
  pattern before anything is pushed or opened;
* verification is a workflow STEP against an immutable SHA, re-asserted against the
  remote ref — an agent saying "tests pass" and a CI step saying so are not the same claim;
* the `record` job reads only jobs that exist (the old `needs.verify` / `needs.publish`
  references made every fire that produced a branch report failure);
* the deadman fails the run when ``HC_BACKLOG_URL`` is unset (A-20), and no cadence is
  armed until A-22 passes.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = (ROOT / ".github/workflows/backlog-roll.yml").read_text(encoding="utf-8")


def _step_names() -> list[str]:
    return [
        line.strip()[len("- name: ") :]
        for line in WORKFLOW.splitlines()
        if line.strip().startswith("- name: ")
    ]


def test_backlog_roll_is_manual_only_with_no_armed_cadence() -> None:
    """Dispatch-only until A-22 passes and HC_BACKLOG_URL exists (AGENTS.md §8a)."""
    trigger_block = WORKFLOW.split("concurrency:", 1)[0]
    assert "workflow_dispatch:" in trigger_block
    assert "\n  schedule:" not in trigger_block
    assert "\n  workflow_run:" not in trigger_block
    assert "\n  issues:" not in trigger_block and "\n  issue_comment:" not in trigger_block
    assert "acknowledge_write_token_risk" not in WORKFLOW
    assert "github.actor ==" not in WORKFLOW
    assert "ARBI_UNATTENDED" not in WORKFLOW


def test_layer_order_is_eligibility_readiness_apply_pick_build() -> None:
    names = _step_names()
    order = [
        "Eligibility (Layer 1)",
        "Readiness (Layer 2)",
        "Apply readiness (Layer 3)",
        "Pick (Layer 4)",
        "Build the picked issues (no PR)",
        "Read branch list",
        "Verify each pushed issue, then open its PR",
    ]
    positions = [names.index(n) for n in order]
    assert positions == sorted(positions), names
    assert names.index("Deadman self-check (STEP 0)") < positions[0]


def test_only_readiness_and_build_use_the_agent_and_readiness_is_bounded() -> None:
    agent_steps = WORKFLOW.split("uses: anthropics/claude-code-action@")
    assert len(agent_steps) == 3, "exactly two agent steps: readiness and build"
    readiness = WORKFLOW.split("- name: Readiness (Layer 2)", 1)[1].split("- name: ", 1)[0]
    assert "--max-turns 25" in readiness
    assert ".eligible-issues.json" in readiness and ".readiness-verdicts.json" in readiness
    assert "Apply NO labels" in readiness
    for layer in ("Eligibility (Layer 1)", "Apply readiness (Layer 3)", "Pick (Layer 4)"):
        block = WORKFLOW.split(f"- name: {layer}", 1)[1].split("- name: ", 1)[0]
        assert "claude-code-action" not in block, f"{layer} must not run a model"


def test_brakes_are_repo_variables_not_literals() -> None:
    apply = WORKFLOW.split("- name: Apply readiness (Layer 3)", 1)[1].split("- name: ", 1)[0]
    for var in ("AUTO_READY", "AUTO_READY_DAILY_CAP", "AUTO_READY_WIP_LIMIT"):
        assert f"{var}: ${{{{ vars.{var} }}}}" in apply, var
    assert 'AUTO_READY: "on"' not in WORKFLOW and "AUTO_READY: on" not in WORKFLOW


def test_picker_input_and_agent_branch_outputs_are_validated() -> None:
    assert "MAX_ITEMS: ${{ inputs.max_items }}" in WORKFLOW
    assert '"$MAX_ITEMS" =~ ^[1-3]$' in WORKFLOW
    assert 'scripts/issue_next.py --max "$MAX_ITEMS"' in WORKFLOW
    assert 'scripts/issue_next.py --max "${{ inputs.max_items }}"' not in WORKFLOW
    assert "scripts/backlog_next.py" not in WORKFLOW
    assert "^claude/issue-[0-9]+-[0-9]{8}$" in WORKFLOW
    assert '"refs/heads/$branch"' in WORKFLOW
    assert "duplicate issue number in branch list" in WORKFLOW
    assert "agent returned more branches than the lane limit" in WORKFLOW
    assert "Closes #$ISSUE_NUMBER" in WORKFLOW


def test_the_lane_runs_in_auto_mode_with_the_pat() -> None:
    assert "--permission-mode auto" in WORKFLOW
    assert "--allowedTools" not in WORKFLOW
    assert "token: ${{ secrets.ARBI_GITHUB_TOKEN }}" in WORKFLOW
    assert "persist-credentials: true" in WORKFLOW
    assert "issues: write" in WORKFLOW


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


def test_record_job_reads_only_jobs_that_exist() -> None:
    """`needs.verify` and `needs.publish` named jobs that did not exist, so every fire
    that produced a branch was reported as a failure by the ledger and the deadman."""
    record = WORKFLOW.split("\n  record:\n", 1)[1]
    assert "needs.verify" not in record and "needs.publish" not in record
    assert "needs.roll.result" in record
