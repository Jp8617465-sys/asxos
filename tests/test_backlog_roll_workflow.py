from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = (ROOT / ".github/workflows/backlog-roll.yml").read_text(encoding="utf-8")


def test_backlog_roll_is_owner_only_manual_and_risk_acknowledged() -> None:
    trigger_block = WORKFLOW.split("concurrency:", 1)[0]
    assert "workflow_dispatch:" in trigger_block
    assert "acknowledge_write_token_risk:" in trigger_block
    assert "\n  schedule:" not in trigger_block
    assert "\n  workflow_run:" not in trigger_block
    assert "github.actor == 'Jp8617465-sys'" in WORKFLOW
    assert "inputs.acknowledge_write_token_risk == true" in WORKFLOW


def test_picker_input_and_agent_branch_outputs_are_validated() -> None:
    assert "MAX_ITEMS: ${{ inputs.max_items }}" in WORKFLOW
    assert '"$MAX_ITEMS" =~ ^[1-3]$' in WORKFLOW
    assert 'scripts/backlog_next.py --max "$MAX_ITEMS"' in WORKFLOW
    assert 'scripts/backlog_next.py --max "${{ inputs.max_items }}"' not in WORKFLOW
    assert "^claude/backlog-[a-e]-[0-9]+[a-z]?-[0-9]{8}$" in WORKFLOW
    assert '"refs/heads/$branch"' in WORKFLOW
    assert "^[-0-9]" not in WORKFLOW
    assert "duplicate backlog id in branch list" in WORKFLOW
    assert "agent returned more branches than the lane limit" in WORKFLOW


def test_agent_authored_code_runs_only_in_read_only_matrix() -> None:
    verify = WORKFLOW.split("\n  verify:\n", 1)[1].split("\n  publish:\n", 1)[0]
    assert "contents: read" in verify
    assert "contents: write" not in verify
    assert "pull-requests: write" not in verify
    assert "persist-credentials: false" in verify
    assert "CLAUDE_CODE_OAUTH_TOKEN" not in verify
    assert "GH_TOKEN" not in verify
    assert "python -m pytest -q" in verify
    assert 'test "$(git rev-parse HEAD)" = "$EXPECTED_SHA"' in verify


def test_publisher_rechecks_each_verified_sha() -> None:
    publish = WORKFLOW.split("\n  publish:\n", 1)[1].split("\n  record:\n", 1)[0]
    assert "needs: [roll, verify]" in publish
    assert "needs.verify.result == 'success'" in publish
    assert "pull-requests: write" in publish
    assert "contents: write" not in publish
    assert 'test "$remote_sha" = "$VERIFIED_SHA"' in publish


def test_ledger_and_deadman_observe_the_complete_pipeline() -> None:
    record = WORKFLOW.split("\n  record:\n", 1)[1]
    assert "needs: [roll, verify, publish]" in record
    assert "if: always()" in record
    assert "needs.verify.result" in record
    assert "needs.publish.result" in record
    assert '"$HC_BACKLOG_URL/fail"' in record
