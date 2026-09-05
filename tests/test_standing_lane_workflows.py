from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NIGHTLY = (ROOT / ".github/workflows/nightly-triage.yml").read_text()
TOOLWATCH = (ROOT / ".github/workflows/weekly-toolwatch.yml").read_text()


def test_standing_lanes_remain_manual_and_risk_acknowledged() -> None:
    for workflow in (NIGHTLY, TOOLWATCH):
        assert "workflow_dispatch:" in workflow
        assert "acknowledge_write_token_risk:" in workflow
        assert "github.actor == 'Jp8617465-sys'" in workflow
        assert "inputs.acknowledge_write_token_risk == true" in workflow

        trigger_block = workflow.split("concurrency:", 1)[0]
        assert "\n  schedule:" not in trigger_block
        assert "\n  workflow_run:" not in trigger_block


def test_nightly_validates_agent_controlled_inputs_before_shell_use() -> None:
    assert "^claude/triage-[0-9]{8}-[a-z0-9-]+$" in NIGHTLY
    assert '"$name"' in NIGHTLY
    assert '"refs/heads/$name"' in NIGHTLY
    assert "^[-0-9]" not in NIGHTLY
    assert '"$REQUESTED_RUN_ID" =~ ^[0-9]+$' in NIGHTLY
    assert "REQUESTED_RUN_ID: ${{ inputs.run_id }}" in NIGHTLY
    assert '"${{ steps.branch.outputs.name }}"' not in NIGHTLY


def test_nightly_executes_agent_code_only_in_read_only_job() -> None:
    verify = NIGHTLY.split("\n  verify:\n", 1)[1].split("\n  publish:\n", 1)[0]
    assert "contents: read" in verify
    assert "contents: write" not in verify
    assert "pull-requests: write" not in verify
    assert "persist-credentials: false" in verify
    assert "CLAUDE_CODE_OAUTH_TOKEN" not in verify
    assert "GH_TOKEN" not in verify
    assert "python -m pytest -q" in verify
    assert 'test "$(git rev-parse HEAD)" = "$EXPECTED_SHA"' in verify


def test_publisher_requires_verified_immutable_sha() -> None:
    publish = NIGHTLY.split("\n  publish:\n", 1)[1]
    assert "needs: [triage, verify]" in publish
    assert "needs.verify.result == 'success'" in publish
    assert "pull-requests: write" in publish
    assert "contents: write" not in publish
    assert 'test "$remote_sha" = "$VERIFIED_SHA"' in publish


def test_diagnosis_is_persisted_on_the_ledger_branch() -> None:
    assert "docs/ops/triage-diagnoses/${GITHUB_RUN_ID}.md" in NIGHTLY
    assert ".triage-diagnosis.md must be a regular, non-symlink file" in NIGHTLY
    assert ".triage-diagnosis.md exceeds 64 KiB" in NIGHTLY
