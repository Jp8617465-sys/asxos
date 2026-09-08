"""Staged asxos-control cores: fail-closed classification, state, drills, specs."""

from __future__ import annotations

import ast
import json
import sys
from datetime import date
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONTROL = ROOT / "docs" / "proposals" / "asxos-control"
sys.path.insert(0, str(CONTROL))

from asxos_control.activate import (  # noqa: E402
    PRE_ACTIVATION_GATES,
    ActivationRecord,
    GateEvidence,
    evaluate_activation,
)
from asxos_control.breaker import TelemetryPoint, evaluate_breaker, load_registry  # noqa: E402
from asxos_control.classify import CHECK_NAME, classify  # noqa: E402
from asxos_control.codeowners import drift_errors  # noqa: E402
from asxos_control.digest import DIGEST_CRON_UTC, digest_template  # noqa: E402
from asxos_control.drills import (  # noqa: E402
    CanaryRevision,
    canary_revert_restored,
    negative_observation_reasons,
)
from asxos_control.hashes import sha256_hex  # noqa: E402
from asxos_control.observation import LedgerAC, Observation, Review  # noqa: E402
from asxos_control.pin import ControlPin, require_live_pin  # noqa: E402
from asxos_control.publish import PublishError, prepare_check_post  # noqa: E402
from asxos_control.registry import PathRegistry  # noqa: E402
from asxos_control.restore import RestoreEvidence, evaluate_restore  # noqa: E402
from asxos_control.ruleset import RulesetSpec, action_allowed, spec_errors  # noqa: E402

SHA = "a" * 40
SHA2 = "b" * 40
AGENTS = b"# AGENTS.md\nSTANDING grant text\n"
DIGEST = sha256_hex(AGENTS)
JAMES = "Jp8617465-sys"
PUBLISHER = "asxos-risk-classify-publisher"
REGISTRY = PathRegistry.load()


def _obs(**overrides: object) -> Observation:
    base = {
        "product_repo": "Jp8617465-sys/asxos",
        "pr_number": 1,
        "head_sha": SHA,
        "check_sha": SHA,
        "ref_kind": "head",
        "changed_paths": ("tests/test_foo.py",),
        "paths_complete": True,
        "reviews": (),
        "codeowners_text": (CONTROL / "registries" / "expected-codeowners").read_text(encoding="utf-8"),
        "agents_md_bytes": AGENTS,
        "claimed_agents_md_digest": DIGEST,
        "verifier_ref": SHA2,
        "publisher_app_slug": PUBLISHER,
        "expected_publisher_app_slug": PUBLISHER,
        "james_login": JAMES,
    }
    base.update(overrides)
    return Observation(**base)  # type: ignore[arg-type]


def _approve(sha: str = SHA) -> Review:
    return Review(user_login=JAMES, state="APPROVED", commit_id=sha, submitted_at="2026-09-08T00:00:00Z")


def test_green_allowlist_passes_without_review() -> None:
    result = classify(_obs())
    assert result.ok
    assert result.tier == "green"
    assert result.conclusion == "success"
    assert result.as_check() == {"name": CHECK_NAME, "head_sha": SHA, "conclusion": "success"}


def test_unknown_path_defaults_to_amber() -> None:
    result = classify(_obs(changed_paths=("jobs/daily_brief.py",)))
    assert not result.ok
    assert result.tier == "amber"
    assert result.reason == "amber_needs_current_head_approval"


def test_application_code_outside_protected_paths_is_green() -> None:
    result = classify(_obs(changed_paths=("asxos/domain/screening/rules.py",)))
    assert result.ok and result.tier == "green"


def test_docs_product_is_amber_even_though_docs_is_green() -> None:
    result = classify(_obs(changed_paths=("docs/product/north-star.md",)))
    assert result.reason == "amber_needs_current_head_approval"


def test_amber_passes_with_james_current_head_approval() -> None:
    result = classify(_obs(changed_paths=("migrations/0053_x.sql",), reviews=(_approve(),)))
    assert result.ok and result.tier == "amber"


def test_stale_head_approval_fails() -> None:
    result = classify(_obs(changed_paths=("migrations/0053_x.sql",), reviews=(_approve(SHA2),)))
    assert result.reason == "amber_needs_current_head_approval"


def test_red_path_never_passes_even_with_approval() -> None:
    result = classify(
        _obs(changed_paths=("asxos/capital/broker.py",), reviews=(_approve(),))
    )
    assert not result.ok
    assert result.tier == "red"
    assert result.reason == "red_path_never_passes"


def test_insights_reserved_path_is_red() -> None:
    result = classify(_obs(changed_paths=("asxos/insights/personal/memo.py",), reviews=(_approve(),)))
    assert result.reason == "red_path_never_passes"


def test_investment_output_requires_digest_bound_approval() -> None:
    ac = LedgerAC(digest="c" * 64, frozen=True, explicit_yes=True, owner_comment=f"APPROVE-AC sha256:{'c'*64}")
    missing = classify(_obs(changed_paths=("asxos/brief/email.py",), reviews=(_approve(),)))
    assert missing.reason == "investment_output_needs_digest_bound_approval"
    ok = classify(
        _obs(changed_paths=("asxos/brief/email.py",), reviews=(_approve(),), ledger_ac=ac)
    )
    assert ok.ok and ok.tier == "amber"


def test_stale_ac_comment_fails() -> None:
    ac = LedgerAC(digest="c" * 64, frozen=True, explicit_yes=True, owner_comment="APPROVE-AC sha256:" + "d" * 64)
    result = classify(_obs(changed_paths=("asxos/domain/decision_engine/x.py",), reviews=(_approve(),), ledger_ac=ac))
    assert result.reason == "investment_output_needs_digest_bound_approval"


@pytest.mark.parametrize(
    ("kwargs", "reason"),
    [
        ({"product_repo": "other/repo"}, "wrong_repository"),
        ({"head_sha": "main"}, "malformed_head_sha"),
        ({"check_sha": SHA2}, "stale_or_non_head_sha"),
        ({"ref_kind": "merge"}, "merge_or_non_head_ref"),
        ({"verifier_ref": "main"}, "mutable_verifier_ref"),
        ({"paths_complete": False}, "incomplete_changed_paths"),
        ({"claimed_agents_md_digest": "e" * 64}, "agents_md_digest_mismatch"),
        ({"publisher_app_slug": "wrong-app"}, "publisher_identity_mismatch"),
        ({"labels": ("relocation",), "pure_relocation": False}, "relocation_not_pure_move"),
    ],
)
def test_fail_closed_observation_defects(kwargs: dict, reason: str) -> None:
    assert classify(_obs(**kwargs)).reason == reason


def test_classify_never_emits_skipped_or_neutral() -> None:
    result = classify(_obs(ref_kind="merge"))
    assert result.conclusion == "failure"
    assert result.as_check()["conclusion"] in {"success", "failure"}


def test_publisher_posts_only_exact_head_binary_result() -> None:
    result = classify(_obs())
    post = prepare_check_post(
        result,
        repo="Jp8617465-sys/asxos",
        requested_sha=SHA,
        publisher_app_slug=PUBLISHER,
        expected_publisher_app_slug=PUBLISHER,
    )
    assert post.conclusion == "success"
    assert post.head_sha == SHA
    with pytest.raises(PublishError, match="wrong_app"):
        prepare_check_post(
            result,
            repo="Jp8617465-sys/asxos",
            requested_sha=SHA,
            publisher_app_slug="other-app",
            expected_publisher_app_slug=PUBLISHER,
        )
    with pytest.raises(PublishError, match="exact_head_mismatch"):
        prepare_check_post(
            result,
            repo="Jp8617465-sys/asxos",
            requested_sha=SHA2,
            publisher_app_slug=PUBLISHER,
            expected_publisher_app_slug=PUBLISHER,
        )


def test_verifier_module_does_not_import_publisher() -> None:
    source = (CONTROL / "asxos_control" / "classify.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    assert "asxos_control.publish" not in imported
    assert "publish" not in imported


def test_unpinned_control_pin_is_not_live() -> None:
    pin = ControlPin.load()
    assert not pin.is_live
    with pytest.raises(ValueError, match="immutable 40-hex"):
        require_live_pin(pin)


def test_expected_codeowners_covers_registry_including_comms() -> None:
    text = (CONTROL / "registries" / "expected-codeowners").read_text(encoding="utf-8")
    assert drift_errors(text, REGISTRY) == []
    assert "/asxos/comms/**" in text


def test_activation_refuses_incomplete_and_mismatched_checklist() -> None:
    gates = tuple(
        GateEvidence(gate=n, status="PASS", evidence_digest="f" * 64)
        for n in PRE_ACTIVATION_GATES
    )
    record = ActivationRecord(
        agents_md_digest=DIGEST,
        verifier_commit=SHA,
        publisher_identity=PUBLISHER,
        state_controller_identity="asxos-state-controller",
        gates=gates,
    )
    ok = evaluate_activation(
        record,
        agents_md_bytes=AGENTS,
        expected_verifier_commit=SHA,
        expected_publisher_identity=PUBLISHER,
        expected_state_controller_identity="asxos-state-controller",
    )
    assert ok.allow
    bad = evaluate_activation(
        record,
        agents_md_bytes=AGENTS,
        expected_verifier_commit=SHA2,
        expected_publisher_identity=PUBLISHER,
        expected_state_controller_identity="asxos-state-controller",
    )
    assert not bad.allow and bad.reason == "verifier_commit_mismatch"
    incomplete_gates = (*gates[:-1], GateEvidence(16, "OWNER_ACTION", "f" * 64))
    incomplete = ActivationRecord(
        agents_md_digest=DIGEST,
        verifier_commit=SHA,
        publisher_identity=PUBLISHER,
        state_controller_identity="asxos-state-controller",
        gates=incomplete_gates,
    )
    refused = evaluate_activation(
        incomplete,
        agents_md_bytes=AGENTS,
        expected_verifier_commit=SHA,
        expected_publisher_identity=PUBLISHER,
        expected_state_controller_identity="asxos-state-controller",
    )
    assert refused.reason == "gate_16_owner_action"


def test_same_publisher_and_state_controller_identity_fails() -> None:
    gates = tuple(GateEvidence(gate=n, status="PASS", evidence_digest="f" * 64) for n in PRE_ACTIVATION_GATES)
    record = ActivationRecord(
        agents_md_digest=DIGEST,
        verifier_commit=SHA,
        publisher_identity=PUBLISHER,
        state_controller_identity=PUBLISHER,
        gates=gates,
    )
    result = evaluate_activation(
        record,
        agents_md_bytes=AGENTS,
        expected_verifier_commit=SHA,
        expected_publisher_identity=PUBLISHER,
        expected_state_controller_identity=PUBLISHER,
    )
    assert result.reason == "state_controller_not_separated"


def test_breaker_trips_on_missing_stale_and_threshold() -> None:
    registry = load_registry()
    missing = evaluate_breaker(registry, {})
    assert missing.trip and missing.next_state == "ATTENDED" and missing.reason == "missing_telemetry"
    stale_points = {
        rule.workflow: TelemetryPoint(rule.workflow, rule.metric, 0.0, stale=True)
        for rule in registry
    }
    stale = evaluate_breaker(registry, stale_points)
    assert stale.reason == "stale_telemetry"
    clean_points = {
        rule.workflow: TelemetryPoint(rule.workflow, rule.metric, 0.0, stale=False)
        for rule in registry
    }
    assert not evaluate_breaker(registry, clean_points).trip
    tripped_points = dict(clean_points)
    tripped_points["full-check"] = TelemetryPoint("full-check", "main_red_minutes", 30.0, stale=False)
    assert evaluate_breaker(registry, tripped_points).reason == "threshold_exceeded"


def test_restore_refuses_third_in_seven_days() -> None:
    evidence = RestoreEvidence(
        fix_merged=True,
        required_checks_green=True,
        clean_minutes=60,
        incident_updated=True,
        restores_in_last_7_days=2,
    )
    decision = evaluate_restore(evidence)
    assert not decision.allow
    assert decision.reason == "third_restore_refused"
    first = evaluate_restore(
        RestoreEvidence(True, True, 60, True, restores_in_last_7_days=0)
    )
    assert first.allow and first.next_state == "STANDING"
    short = evaluate_restore(
        RestoreEvidence(True, True, 59, True, restores_in_last_7_days=0)
    )
    assert short.reason == "clean_window_below_60m"


def test_digest_is_0700_aest() -> None:
    assert DIGEST_CRON_UTC == "0 21 * * *"
    rendered = digest_template(date(2026, 9, 8), "ATTENDED")
    assert rendered.startswith("## 2026-09-08   AUTONOMY: ATTENDED")


def test_ruleset_spec_rejects_direct_force_admin_stale_and_nonsquash() -> None:
    spec = RulesetSpec.load()
    assert spec_errors(spec) == []
    assert not action_allowed(spec, "direct_push")
    assert not action_allowed(spec, "force_push")
    assert not action_allowed(spec, "admin_bypass")
    assert not action_allowed(spec, "stale_check")
    assert not action_allowed(spec, "non_squash_merge")
    assert action_allowed(spec, "squash_merge_with_required_checks")


def test_canary_revert_and_negative_reasons() -> None:
    assert canary_revert_restored(CanaryRevision(SHA, SHA2, SHA))
    assert not canary_revert_restored(CanaryRevision(SHA, SHA2, SHA2))
    reasons = negative_observation_reasons()
    assert "wrong_repository" in reasons
    assert "missing_telemetry" in reasons


def test_production_environment_spec_requires_james() -> None:
    raw = json.loads((CONTROL / "fixtures" / "production-environment.json").read_text(encoding="utf-8"))
    assert raw["name"] == "production"
    assert raw["required_reviewers"] == ["Jp8617465-sys"]
    assert "daily-brief" in raw["attached_to_spend_jobs"]


def _load_yaml(rel: str) -> dict:
    return yaml.safe_load((CONTROL / rel).read_text(encoding="utf-8"))


def _on(data: dict) -> dict:
    # PyYAML 1.1 treats the GitHub key `on` as boolean true.
    return data.get("on") or data[True]


def test_verifier_workflow_has_no_secrets_and_no_checks_write() -> None:
    data = _load_yaml("workflows/risk-classify-verify.yml")
    assert "secrets" not in _on(data)["workflow_call"]
    assert data["permissions"].get("contents") == "read"
    assert data["permissions"].get("checks") == "read"
    assert data["permissions"].get("checks") != "write"
    jobs = data["jobs"]["verify"]
    assert jobs.get("permissions", {}).get("checks") != "write"


def test_publisher_and_activation_default_dry_run() -> None:
    pub = _load_yaml("workflows/risk-classify-publish.yml")
    assert _on(pub)["workflow_dispatch"]["inputs"]["dry-run"]["default"] is True
    act = _load_yaml("workflows/activate.yml")
    assert _on(act)["workflow_dispatch"]["inputs"]["dry-run"]["default"] is True
    digest = _load_yaml("workflows/digest.yml")
    assert _on(digest)["schedule"][0]["cron"] == "0 21 * * *"


def test_product_caller_never_pins_main() -> None:
    body = (CONTROL / "product-repo" / "risk-classify-caller.yml").read_text(encoding="utf-8")
    assert "@main" not in body
    assert "REPLACE_WITH_COMMIT_SHA" in body
    assert "secrets: inherit" not in body


def test_breaker_registry_covers_scheduled_production_workflows() -> None:
    names = {rule.workflow for rule in load_registry()}
    for workflow in (
        "full-check",
        "daily-brief",
        "us-positions",
        "weekly-research",
        "pipeline-health",
        "backup",
        "nightly-check",
        "migration-drift",
        "rollback-detector",
    ):
        assert workflow in names
    for rule in load_registry():
        assert rule.metric and rule.threshold and rule.window and rule.evidence_query
