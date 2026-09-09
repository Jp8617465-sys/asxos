from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).parents[1]
CALLER_PATH = ROOT / ".github/workflows/risk-classify.yml"
SIGNAL_PATH = ROOT / ".github/workflows/risk-review-signal.yml"
CONTROL_PIN = "c0ada5074aca902afb514958f6e041f2f7afe305"
LEDGER_PLACEHOLDER = "0" * 40


def _load(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as handle:
        document = yaml.safe_load(handle)
    assert isinstance(document, dict)
    return document


def test_review_signal_is_credential_free_and_executes_no_repository_code() -> None:
    source = SIGNAL_PATH.read_text(encoding="utf-8")
    document = _load(SIGNAL_PATH)
    assert document[True] == {
        "pull_request_review": {"types": ["submitted", "edited", "dismissed"]}
    }
    assert document["permissions"] == {}
    jobs = document["jobs"]
    assert isinstance(jobs, dict)
    signal = jobs["signal"]
    assert isinstance(signal, dict)
    assert signal["steps"] == [{"name": "Emit no authority", "run": "/usr/bin/true"}]
    assert "secrets." not in source
    assert "secrets:" not in source
    assert "actions/checkout" not in source
    assert "uses:" not in source


def test_base_owned_caller_is_pinned_and_never_inherits_secrets() -> None:
    source = CALLER_PATH.read_text(encoding="utf-8")
    document = _load(CALLER_PATH)
    jobs = document["jobs"]
    assert isinstance(jobs, dict)
    classify = jobs["classify"]
    assert isinstance(classify, dict)
    assert classify["uses"] == (
        "Jp8617465-sys/asxos-control/.github/workflows/risk-classify.yml@"
        + CONTROL_PIN
    )
    assert document["permissions"] == {
        "contents": "read",
        "pull-requests": "read",
    }
    assert "secrets: inherit" not in source
    assert "secrets." not in source
    assert "actions/checkout" not in source
    assert re.search(r"@[0-9a-f]{40}$", str(classify["uses"]))


def test_review_wake_is_reobserved_only_from_protected_main_caller() -> None:
    source = CALLER_PATH.read_text(encoding="utf-8")
    assert "pull_request_review:" not in source
    assert "pull_request_target:" in source
    assert "workflow_run:" in source
    assert "workflows: [Risk Review Signal]" in source
    assert "github.event.workflow_run.conclusion == 'success'" in source
    assert "github.event.workflow_run.event == 'pull_request_review'" in source
    assert source.count("head.repo.id == 1243449658") == 2
    assert source.count("base.repo.id == 1243449658") == 2
    assert "github.event.workflow_run.pull_requests[0].number" in source
    assert "github.event.workflow_run.pull_requests[0].head.sha" in source


def test_ledger_root_placeholder_keeps_draft_inoperable_until_owner_bootstrap() -> None:
    document = _load(CALLER_PATH)
    jobs = document["jobs"]
    assert isinstance(jobs, dict)
    classify = jobs["classify"]
    assert isinstance(classify, dict)
    inputs = classify["with"]
    assert isinstance(inputs, dict)
    assert inputs["ledger-genesis-parent-sha"] == LEDGER_PLACEHOLDER
    source = CALLER_PATH.read_text(encoding="utf-8")
    assert "Fail-closed bootstrap placeholder" in source


def test_product_workflow_inventory_recognises_signal_as_secretless() -> None:
    from tools import workflow_inventory

    inventory = workflow_inventory.build_inventory(
        ROOT / ".github/workflows", root=ROOT
    )
    by_path = {item["path"]: item for item in inventory["workflows"]}
    signal = by_path[".github/workflows/risk-review-signal.yml"]
    caller = by_path[".github/workflows/risk-classify.yml"]
    assert signal["secret_refs"] == []
    assert signal["secrets_inherit"] is False
    assert signal["exposed_to_authored_pr"] is False
    assert caller["secret_refs"] == []
    assert caller["secrets_inherit"] is False
