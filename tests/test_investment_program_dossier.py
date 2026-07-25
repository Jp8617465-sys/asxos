"""Executable integrity checks for the investment-engine implementation dossier."""

from __future__ import annotations

import json
from copy import deepcopy

import pytest

from scripts.validate_investment_program import (
    CONSTRUCTION_CAP_ORDER,
    FIXTURE_DIR,
    MISSION_TEMPLATE_PATH,
    MODEL_A_DECOMMISSION_PATH,
    MODEL_A_FAIL_CLOSED_TOKEN,
    MODEL_A_M02_RECORD_PATHS,
    ROADMAP_PATH,
    ROADMAP_VIEW_PATH,
    SCHEMA_DIR,
    SPRINT_COMMAND_PATH,
    TAILORED_OUTPUT_AUTHORITY_DOCUMENTS,
    DossierError,
    SchemaStore,
    _format_error,
    _object_payload_sha256,
    _validate_accounting_semantics,
    _validate_contract_name_references,
    _validate_evaluator_semantics,
    _validate_fixture_chronology,
    _validate_fixture_hash_convention,
    _validate_lineage_semantics,
    _validate_locally_resolvable_reference_hashes,
    _validate_model_a_archive_semantics,
    _validate_model_a_decommission_controls,
    _validate_numeric_wire_shapes,
    _validate_origin_snapshot_semantics,
    _validate_portfolio_semantics,
    _validate_promotion_semantics,
    _validate_review_semantics,
    _validate_staging_semantics,
    find_forbidden_capital_tokens,
    fixture_payload_sha256,
    load_fixture_documents,
    render_roadmap_view,
    required_contract_names,
    review_context_payload_sha256,
    rewrite_fixture_hashes,
    validate_program,
)


def test_investment_program_dossier_is_internally_consistent() -> None:
    report = validate_program()
    roadmap = json.loads(ROADMAP_PATH.read_text(encoding="utf-8"))

    assert report["sprints"] == 12
    assert report["schemas"] >= 10
    assert report["fixtures"] >= 9
    assert report["contracts"] == len(roadmap["contracts"])
    assert report["mission_controls"] >= 8


def test_generated_roadmap_view_matches_canonical_manifest() -> None:
    roadmap = json.loads(ROADMAP_PATH.read_text(encoding="utf-8"))

    assert ROADMAP_VIEW_PATH.read_text(encoding="utf-8") == render_roadmap_view(roadmap)


def test_contract_registry_expectations_follow_every_roadmap_contract() -> None:
    roadmap = json.loads(ROADMAP_PATH.read_text(encoding="utf-8"))

    assert required_contract_names(roadmap) == tuple(
        contract["name"] for contract in roadmap["contracts"]
    )

    duplicate = deepcopy(roadmap)
    duplicate["contracts"].append(deepcopy(duplicate["contracts"][0]))
    with pytest.raises(DossierError, match="duplicate names"):
        required_contract_names(duplicate)


def test_mission_records_are_per_mission_and_authority_list_is_complete() -> None:
    template = MISSION_TEMPLATE_PATH.read_text(encoding="utf-8")
    command = SPRINT_COMMAND_PATH.read_text(encoding="utf-8")

    for path in (
        "docs/programs/investment-engine/missions/SXX/MXX/mission.yaml",
        "docs/programs/investment-engine/missions/SXX/MXX/close.md",
        "docs/programs/investment-engine/missions/S01/M01/mission.yaml",
        "docs/programs/investment-engine/missions/S01/M01/close.md",
    ):
        assert path in template
        assert path in command

    assert len(TAILORED_OUTPUT_AUTHORITY_DOCUMENTS) == 7
    assert "docs/product/portfolio-policy.md" in TAILORED_OUTPUT_AUTHORITY_DOCUMENTS
    for authority_path in TAILORED_OUTPUT_AUTHORITY_DOCUMENTS:
        assert authority_path in template
        assert authority_path in command

    assert MODEL_A_FAIL_CLOSED_TOKEN in template
    assert MODEL_A_FAIL_CLOSED_TOKEN in command
    assert "model-a-decommission.md" in template
    assert "model-a-decommission.md" in command
    for record_path in MODEL_A_M02_RECORD_PATHS:
        assert record_path in template
        assert record_path in command


def test_model_a_target_is_fail_closed_decommission_not_passive_observation() -> None:
    template = MISSION_TEMPLATE_PATH.read_text(encoding="utf-8")
    command = SPRINT_COMMAND_PATH.read_text(encoding="utf-8")
    s01_path = FIXTURE_DIR.parent / "sprints/s01-programme-guardrails-and-proposal-registry.md"
    registry_path = FIXTURE_DIR.parent / "contracts/proposal-registry.md"
    prompt_paths = sorted((FIXTURE_DIR.parent / "prompts").glob("*.md"))

    _validate_model_a_decommission_controls(
        template,
        command,
        s01_path.read_text(encoding="utf-8"),
        registry_path.read_text(encoding="utf-8"),
        prompt_paths,
    )

    passive = template + "\npassive_observation_only_until_S04\n"
    with pytest.raises(DossierError, match="passive Model A target is superseded"):
        _validate_model_a_decommission_controls(
            passive,
            command,
            s01_path.read_text(encoding="utf-8"),
            registry_path.read_text(encoding="utf-8"),
            prompt_paths,
        )


def test_model_a_decommission_dossier_does_not_authorize_production_mutation() -> None:
    contract = MODEL_A_DECOMMISSION_PATH.read_text(encoding="utf-8").lower()

    assert "recommended target state" in contract
    assert "separate james-approved mission" in contract
    assert "does not authorise" in contract
    assert "destructive data deletion" in contract
    assert "production configuration changes" in contract
    assert "migration apply" in contract
    assert "deploy" in contract


def test_model_a_archive_restore_proof_is_recomputed() -> None:
    _validate_model_a_archive_semantics(load_fixture_documents())


def test_model_a_archive_restore_rejects_producer_hash_flag_spoof() -> None:
    fixtures = load_fixture_documents()
    comparison = fixtures["model-a-archive-restore-evidence-valid.json"]["comparisons"][0]
    comparison["observed_raw_sha256"] = "0" * 64

    with pytest.raises(DossierError, match="raw_hash_match.*recomputation"):
        _validate_model_a_archive_semantics(fixtures)


def test_model_a_archive_restore_rejects_count_flag_spoof() -> None:
    fixtures = load_fixture_documents()
    comparison = fixtures["model-a-archive-restore-evidence-valid.json"]["comparisons"][0]
    comparison["observed_record_count"] = "19"

    with pytest.raises(DossierError, match="count_match.*recomputation"):
        _validate_model_a_archive_semantics(fixtures)


def test_model_a_archive_restore_rejects_class_order_drift() -> None:
    fixtures = load_fixture_documents()
    manifest = fixtures["model-a-archive-manifest-valid.json"]
    manifest["archive_classes"][0], manifest["archive_classes"][1] = (
        manifest["archive_classes"][1],
        manifest["archive_classes"][0],
    )

    with pytest.raises(DossierError, match="class order/set"):
        _validate_model_a_archive_semantics(fixtures)


def test_model_a_archive_restore_rejects_impossible_chronology() -> None:
    fixtures = load_fixture_documents()
    fixtures["model-a-archive-restore-evidence-valid.json"]["started_at"] = "2026-07-24T02:05:00Z"

    with pytest.raises(DossierError, match="chronology is not monotonic"):
        _validate_model_a_archive_semantics(fixtures)


@pytest.mark.parametrize(
    "filename",
    [
        "model-a-archive-manifest-valid.json",
        "model-a-archive-restore-evidence-valid.json",
    ],
)
def test_synthetic_model_a_archive_cannot_claim_production_evidence(filename: str) -> None:
    fixtures = load_fixture_documents()
    item = fixtures[filename]
    item["controls"]["production_evidence_claimed"] = True
    if filename == "model-a-archive-manifest-valid.json":
        item["deployment_environment"] = "production"
    store = SchemaStore(SCHEMA_DIR)

    with pytest.raises(DossierError, match="schema validation failed"):
        store.validate(
            item,
            SCHEMA_DIR / f"{item['contract_name']}.schema.json",
            f"{filename}-production-masquerade",
        )


@pytest.mark.parametrize(
    "value",
    [
        "2026-07-20T06:12:00",
        "2026-07-20T06:12:00+10:00",
        "2026-07-20 06:12:00Z",
    ],
)
def test_date_time_format_rejects_non_utc_or_timezone_less_values(value: str) -> None:
    assert "UTC date-time" in (_format_error(value, "date-time") or "")


@pytest.mark.parametrize(
    "value",
    [
        "2026-07-20T06:12:00Z",
        "2026-07-20T06:12:00.123456Z",
        "2026-07-20T06:12:00+00:00",
    ],
)
def test_date_time_format_accepts_explicit_utc_values(value: str) -> None:
    assert _format_error(value, "date-time") is None


def test_schema_validation_applies_utc_date_time_rule() -> None:
    store = SchemaStore(SCHEMA_DIR)
    proposal = json.loads((FIXTURE_DIR / "thesis-proposal-valid.json").read_text(encoding="utf-8"))
    proposal["created_at"] = "2026-07-20T06:12:00"

    with pytest.raises(DossierError, match="UTC date-time"):
        store.validate(
            proposal,
            SCHEMA_DIR / "thesis-proposal-v1.schema.json",
            "negative-timezone-self-test",
        )


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("broker account", "broker_account"),
        ("broker API", "broker_api"),
        ("broker client", "broker_client"),
        ("broker connection", "broker_connection"),
        ("broker credential", "broker_credential"),
        ("broker endpoint", "broker_endpoint"),
        ("broker route", "broker_route"),
        ("broker-session", "broker_session"),
        ("broker token", "broker_token"),
        ("AUTH_TOKEN", "auth_token"),
        ("authentication required", "authentication"),
        ("authorization scope", "authorization"),
        ("multi-user field", "multi_user"),
        ("tenant_id", "tenant_id"),
        ("tenancy", "tenancy"),
        ("RLS policy", "rls"),
        ("user-id", "user_id"),
        ("place order", "place_order"),
        ("modify-order", "modify_order"),
        ("cancel order", "cancel_order"),
        ("execute order", "execute_order"),
        ("route order", "route_order"),
        ("submit order", "submit_order"),
    ],
)
def test_capital_boundary_deny_tokens_have_negative_self_tests(text: str, expected: str) -> None:
    assert expected in find_forbidden_capital_tokens(text)


def test_capital_boundary_token_matching_avoids_authority_and_urls_false_positives() -> None:
    assert find_forbidden_capital_tokens("James retains authority and cited source URLs.") == []


def test_root_fixture_hashes_are_recomputed_not_trusted() -> None:
    fixtures = load_fixture_documents()
    staged = fixtures["staged-order-valid.json"]

    assert staged["canonical_hash"]["payload_sha256"] == fixture_payload_sha256(staged)
    staged["canonical_hash"]["payload_sha256"] = "0" * 64
    with pytest.raises(DossierError, match="canonical_hash payload mismatch"):
        _validate_fixture_hash_convention(fixtures)

    assert rewrite_fixture_hashes(fixtures) == 1
    _validate_fixture_hash_convention(fixtures)


def test_every_contract_fixture_requires_a_root_hash_envelope() -> None:
    fixtures = load_fixture_documents()
    del fixtures["staged-order-valid.json"]["canonical_hash"]

    with pytest.raises(DossierError, match="missing its root canonical_hash"):
        _validate_fixture_hash_convention(fixtures)


def test_canonical_fixture_subset_rejects_binary_float() -> None:
    item = {
        "contract_name": "example-v1",
        "binary_float": 0.1,
        "canonical_hash": {
            "canonicalization": "RFC8785",
            "hash_algorithm": "SHA-256",
            "excluded_json_pointer": "/canonical_hash/payload_sha256",
            "payload_sha256": "0" * 64,
        },
    }

    with pytest.raises(DossierError, match="JSON float"):
        fixture_payload_sha256(item)


def test_fixture_hash_uses_sorted_compact_json_and_exact_exclusion() -> None:
    item = {
        "z": 1,
        "canonical_hash": {
            "hash_algorithm": "SHA-256",
            "payload_sha256": "0" * 64,
            "excluded_json_pointer": "/canonical_hash/payload_sha256",
            "canonicalization": "RFC8785",
        },
        "a": "x",
    }

    assert (
        fixture_payload_sha256(item)
        == "c75acb266628448d8b37f927b8e949e0757fc93089f9695fabd693106de5bbf3"
    )


def test_hash_repair_synchronizes_locally_resolvable_references() -> None:
    fixtures = load_fixture_documents()
    integrated = fixtures["integrated-investment-chain.json"]
    staged = fixtures["staged-order-valid.json"]
    integrated["lineage"]["staged_order_set_ref"]["sha256"] = "f" * 64
    integrated["canonical_hash"]["payload_sha256"] = fixture_payload_sha256(integrated)

    rewrite_fixture_hashes(fixtures)

    assert (
        integrated["lineage"]["staged_order_set_ref"]["sha256"]
        == staged["canonical_hash"]["payload_sha256"]
    )
    assert integrated["canonical_hash"]["payload_sha256"] == fixture_payload_sha256(integrated)


def test_review_context_narrow_digest_is_recomputed_and_distinct() -> None:
    fixtures = load_fixture_documents()
    context = fixtures["review-context-valid.json"]

    assert context["context_sha256"] == review_context_payload_sha256(context)
    assert context["context_sha256"] != context["canonical_hash"]["payload_sha256"]

    context["context_sha256"] = "0" * 64
    context["canonical_hash"]["payload_sha256"] = fixture_payload_sha256(context)
    with pytest.raises(DossierError, match="context_sha256 subset mismatch"):
        _validate_fixture_hash_convention(fixtures)


def test_hash_repair_updates_review_context_narrow_hash_and_consumers() -> None:
    fixtures = load_fixture_documents()
    context = fixtures["review-context-valid.json"]
    eligibility = fixtures["review-eligibility-valid.json"]
    previous_context_digest = context["context_sha256"]
    context["claims"][0]["text"] += " Recomputed fixture."

    rewrite_fixture_hashes(fixtures)

    assert context["context_sha256"] == review_context_payload_sha256(context)
    assert context["context_sha256"] != previous_context_digest
    assert eligibility["context_sha256"] == context["context_sha256"]
    assert context["canonical_hash"]["payload_sha256"] == fixture_payload_sha256(context)
    assert context["context_sha256"] != context["canonical_hash"]["payload_sha256"]


def test_review_decision_is_recomputed_from_exact_assessments() -> None:
    fixtures = load_fixture_documents()

    _validate_review_semantics(fixtures)


def test_review_rejects_copied_verdict_after_assessment_changes() -> None:
    fixtures = load_fixture_documents()
    assessments = fixtures["reviewer-assessments-blind.json"]
    assessments[0]["verdict"] = "FAIL"
    rewrite_fixture_hashes(fixtures)

    with pytest.raises(DossierError, match="assessment_refs"):
        _validate_review_semantics(fixtures)


def test_review_rejects_paper_eligibility_after_fail_verdict_is_propagated() -> None:
    fixtures = load_fixture_documents()
    assessments = fixtures["reviewer-assessments-blind.json"]
    eligibility = fixtures["review-eligibility-valid.json"]
    assessments[0]["verdict"] = "FAIL"
    eligibility["assessment_refs"][0]["verdict"] = "FAIL"
    rewrite_fixture_hashes(fixtures)

    with pytest.raises(DossierError, match="deterministic synthesis"):
        _validate_review_semantics(fixtures)


def test_review_rejects_missing_or_reordered_mandatory_role() -> None:
    fixtures = load_fixture_documents()
    assessments = fixtures["reviewer-assessments-blind.json"]
    assessments[0], assessments[1] = assessments[1], assessments[0]

    with pytest.raises(DossierError, match="mandatory role order/set"):
        _validate_review_semantics(fixtures)


def test_review_rejects_paper_eligibility_with_open_high_finding() -> None:
    fixtures = load_fixture_documents()
    assessments = fixtures["reviewer-assessments-blind.json"]
    eligibility = fixtures["review-eligibility-valid.json"]
    assessments[2]["findings"][0]["severity"] = "high"
    eligibility["finding_summary"]["open_medium"] = 0
    eligibility["finding_summary"]["open_high"] = 1
    rewrite_fixture_hashes(fixtures)

    with pytest.raises(DossierError, match="deterministic synthesis"):
        _validate_review_semantics(fixtures)


def test_review_rejects_complete_context_when_blocking_data_is_missing() -> None:
    fixtures = load_fixture_documents()
    context = fixtures["review-context-valid.json"]
    context["missing_data"][0]["severity"] = "blocking"
    context["freshness"]["overall_state"] = "INCOMPLETE"
    rewrite_fixture_hashes(fixtures)

    with pytest.raises(DossierError, match="context_state"):
        _validate_review_semantics(fixtures)


def test_review_rejects_report_or_thesis_identity_drift() -> None:
    fixtures = load_fixture_documents()
    fixtures["review-context-valid.json"]["thesis_id"] = "thesis-not-in-report"

    with pytest.raises(DossierError, match="report/thesis identity"):
        _validate_review_semantics(fixtures)


def test_review_rejects_cross_case_eligibility_replay() -> None:
    fixtures = load_fixture_documents()
    fixtures["integrated-investment-chain.json"]["lineage"]["investment_case_id"] = (
        "case-other-20260724"
    )
    rewrite_fixture_hashes(fixtures)

    with pytest.raises(DossierError, match="investment_case_id.*eligibility case"):
        _validate_review_semantics(fixtures)


def test_review_candidate_hash_must_resolve_exact_report_bytes() -> None:
    fixtures = load_fixture_documents()
    forged_hash = "9" * 64
    fixtures["review-eligibility-valid.json"]["report_candidate_sha256"] = forged_hash
    for assessment in fixtures["reviewer-assessments-blind.json"]:
        assessment["report_candidate_sha256"] = forged_hash
    for document in fixtures.values():
        if isinstance(document, dict) and isinstance(document.get("lineage"), dict):
            document["lineage"]["research"]["report_candidate_sha256"] = forged_hash
    rewrite_fixture_hashes(fixtures)

    with pytest.raises(DossierError, match="exact broker-report bytes"):
        _validate_review_semantics(fixtures)


def test_review_rejects_dangling_finding_claim_reference() -> None:
    fixtures = load_fixture_documents()
    finding = fixtures["reviewer-assessments-blind.json"][2]["findings"][0]
    finding["claim_ids"] = ["CLM-999"]
    rewrite_fixture_hashes(fixtures)

    with pytest.raises(DossierError, match="claim/evidence references"):
        _validate_review_semantics(fixtures)


def test_review_rejects_dangling_finding_evidence_reference() -> None:
    fixtures = load_fixture_documents()
    finding = fixtures["reviewer-assessments-blind.json"][2]["findings"][0]
    finding["evidence_ids"] = [999999]
    rewrite_fixture_hashes(fixtures)

    with pytest.raises(DossierError, match="evidence_ids"):
        _validate_review_semantics(fixtures)


def test_review_rejects_unapproved_prompt_identity() -> None:
    fixtures = load_fixture_documents()
    reviewer = fixtures["reviewer-assessments-blind.json"][0]["reviewer"]
    reviewer["prompt_ref"] = {
        "id": "attacker-prompt",
        "version": "9.9.9",
        "sha256": "f" * 64,
    }
    rewrite_fixture_hashes(fixtures)

    with pytest.raises(DossierError, match="approved role identity bundle"):
        _validate_review_semantics(fixtures)


def test_review_rejects_resolution_laundering() -> None:
    fixtures = load_fixture_documents()
    assessment = fixtures["reviewer-assessments-blind.json"][1]
    finding = assessment["findings"][0]
    eligibility = fixtures["review-eligibility-valid.json"]
    finding["severity"] = "critical"
    finding["status"] = "ACCEPTED_RISK"
    finding["resolution_ref"] = {
        "resolution_id": "forged-resolution",
        "resolution_type": "ACCEPTED_RISK",
        "resolved_by": "Mallory",
        "resolved_at": "2027-01-01T00:00:00Z",
        "resolution_sha256": "f" * 64,
    }
    eligibility["finding_summary"]["resolved_count"] = 0
    eligibility["finding_summary"]["accepted_risk_count"] = 1
    rewrite_fixture_hashes(fixtures)

    with pytest.raises(DossierError, match="approved immutable James/governance resolution"):
        _validate_review_semantics(fixtures)


def test_review_recomputes_freshness_instead_of_trusting_label() -> None:
    fixtures = load_fixture_documents()
    freshness_item = fixtures["review-context-valid.json"]["freshness"]["items"][0]
    freshness_item["age_seconds"] = 999999999
    rewrite_fixture_hashes(fixtures)

    with pytest.raises(DossierError, match="freshness state/age"):
        _validate_review_semantics(fixtures)


def test_review_rejects_future_retrieved_evidence() -> None:
    fixtures = load_fixture_documents()
    evidence = fixtures["review-context-valid.json"]["evidence"][0]
    evidence["retrieved_at"] = "2026-07-20T06:13:00Z"
    rewrite_fixture_hashes(fixtures)

    with pytest.raises(DossierError, match="future or non-monotonic"):
        _validate_review_semantics(fixtures)


def test_review_rejects_context_generated_before_cutoff() -> None:
    fixtures = load_fixture_documents()
    fixtures["review-context-valid.json"]["generated_at"] = "2026-07-20T06:11:59Z"
    rewrite_fixture_hashes(fixtures)

    with pytest.raises(DossierError, match="point-in-time monotonic"):
        _validate_review_semantics(fixtures)


def test_review_rejects_assessment_submitted_before_context_exists() -> None:
    fixtures = load_fixture_documents()
    assessment = fixtures["reviewer-assessments-blind.json"][0]
    assessment["submitted_at"] = "2026-07-20T06:12:59Z"
    rewrite_fixture_hashes(fixtures)

    with pytest.raises(DossierError, match="outside context/decision chronology"):
        _validate_review_semantics(fixtures)


def test_locally_resolvable_reference_hash_drift_is_rejected() -> None:
    fixtures = load_fixture_documents()
    rewrite_fixture_hashes(fixtures)
    fixtures["paper-intent-valid.json"]["origin_ref"]["sha256"] = "f" * 64

    with pytest.raises(DossierError, match="local artifact reference hash"):
        _validate_locally_resolvable_reference_hashes(fixtures)


def test_reference_created_after_consumer_is_rejected() -> None:
    fixtures = load_fixture_documents()
    fixtures["paper-intent-valid.json"]["origin_ref"]["created_at"] = "2027-01-01T00:00:00Z"

    with pytest.raises(DossierError, match="created after"):
        _validate_fixture_chronology(fixtures)


def test_created_at_before_as_of_is_rejected() -> None:
    fixtures = load_fixture_documents()
    fixtures["branch-nav-valid.json"]["created_at"] = "2026-07-27T05:59:59Z"

    with pytest.raises(DossierError, match="precedes data_as_of"):
        _validate_fixture_chronology(fixtures)


def test_evaluator_episode_count_drift_is_rejected() -> None:
    fixtures = load_fixture_documents()
    fixtures["paper-episode-golden.json"]["episode_counts"]["matured"] = "2"

    with pytest.raises(DossierError, match="episode_counts drifted"):
        _validate_evaluator_semantics(fixtures)


def test_operational_gate_cannot_pass_with_one_session() -> None:
    fixtures = load_fixture_documents()
    fixtures["paper-episode-golden.json"]["operational_gate"]["passed"] = True

    with pytest.raises(DossierError, match="operational gate boolean"):
        _validate_evaluator_semantics(fixtures)


def test_strategy_gate_cannot_pass_with_one_session_and_one_episode() -> None:
    fixtures = load_fixture_documents()
    fixtures["paper-episode-golden.json"]["strategy_gate"]["passed"] = True

    with pytest.raises(DossierError, match="strategy gate boolean"):
        _validate_evaluator_semantics(fixtures)


@pytest.mark.parametrize(
    ("field", "bad_value"),
    [
        ("bit_identical_replay", False),
        ("genuine_xjo_tr_present", False),
        ("effective_fee_schedule_present", False),
        ("ratified_risk_policy_present", False),
        ("dependency_isolation_passed", False),
        ("evidence_chain_complete", False),
    ],
)
def test_operational_gate_refuses_missing_prerequisite(field: str, bad_value: bool) -> None:
    fixtures = load_fixture_documents()
    evaluator = fixtures["paper-episode-golden.json"]
    evaluator["evaluation_window"]["observed_sessions"] = "30"
    evaluator["strategy_gate"]["evidence"]["observed_sessions"] = "30"
    evidence = evaluator["operational_gate"]["evidence"]
    evidence["consecutive_complete_sessions"] = "30"
    evidence["unresolved_material_defects"] = {
        key: "0" for key in evidence["unresolved_material_defects"]
    }
    evaluator["unresolved_material_defects"] = deepcopy(evidence["unresolved_material_defects"])
    for prerequisite in (
        "bit_identical_replay",
        "genuine_xjo_tr_present",
        "effective_fee_schedule_present",
        "ratified_risk_policy_present",
        "dependency_isolation_passed",
        "evidence_chain_complete",
    ):
        evidence[prerequisite] = True
    evaluator["operational_gate"]["passed"] = True
    evidence[field] = bad_value

    with pytest.raises(DossierError, match="operational gate boolean"):
        _validate_evaluator_semantics(fixtures)


def test_operational_gate_refuses_any_material_defect() -> None:
    fixtures = load_fixture_documents()
    evaluator = fixtures["paper-episode-golden.json"]
    evaluator["evaluation_window"]["observed_sessions"] = "30"
    evaluator["strategy_gate"]["evidence"]["observed_sessions"] = "30"
    evidence = evaluator["operational_gate"]["evidence"]
    evidence["consecutive_complete_sessions"] = "30"
    evidence["unresolved_material_defects"] = {
        key: "0" for key in evidence["unresolved_material_defects"]
    }
    evidence["unresolved_material_defects"]["tax"] = "1"
    evaluator["unresolved_material_defects"] = deepcopy(evidence["unresolved_material_defects"])
    for prerequisite in (
        "bit_identical_replay",
        "genuine_xjo_tr_present",
        "effective_fee_schedule_present",
        "ratified_risk_policy_present",
        "dependency_isolation_passed",
        "evidence_chain_complete",
    ):
        evidence[prerequisite] = True
    evaluator["operational_gate"]["passed"] = True

    with pytest.raises(DossierError, match="operational gate boolean"):
        _validate_evaluator_semantics(fixtures)


def test_ledger_imbalance_is_rejected() -> None:
    fixtures = load_fixture_documents()
    event = fixtures["branch-ledger-valid.json"]["branches"][0]["events"][0]
    event["legs"][0]["amount"] = "99999.000000"

    with pytest.raises(DossierError, match="debit_total.*arithmetic mismatch"):
        _validate_accounting_semantics(fixtures)


def test_nav_component_arithmetic_drift_is_rejected() -> None:
    fixtures = load_fixture_documents()
    entry = fixtures["branch-nav-valid.json"]["branches"][0]["entries"][0]
    entry["ending_nav_aud"] = "99981.100000"

    with pytest.raises(DossierError, match="ending_nav_aud.*arithmetic mismatch"):
        _validate_accounting_semantics(fixtures)


def test_sized_decision_cannot_contain_rejected_line() -> None:
    fixtures = load_fixture_documents()
    fixtures["sizing-valid.json"]["line_items"][0]["decision"] = "REJECTED"

    with pytest.raises(DossierError, match="SIZED contains a rejected line"):
        _validate_portfolio_semantics(fixtures)


def test_proposal_cannot_embed_its_own_unhashed_reference() -> None:
    fixtures = load_fixture_documents()
    proposal = fixtures["portfolio-proposal-valid.json"]
    proposal["lineage"]["portfolio_proposal_ref"] = {
        "id": proposal["proposal_id"],
        "sha256": proposal["canonical_hash"]["payload_sha256"],
    }

    with pytest.raises(DossierError, match="future-stage reference|cannot self-reference"):
        _validate_lineage_semantics(fixtures)


def test_sizing_cannot_embed_its_own_unhashed_reference() -> None:
    fixtures = load_fixture_documents()
    sizing = fixtures["sizing-valid.json"]
    sizing["lineage"]["sizing_decision_ref"] = {
        "id": sizing["sizing_decision_id"],
        "sha256": sizing["canonical_hash"]["payload_sha256"],
    }

    with pytest.raises(DossierError, match="future-stage reference|cannot self-reference"):
        _validate_lineage_semantics(fixtures)


def test_staged_set_cannot_advance_lineage_before_it_is_hashed() -> None:
    fixtures = load_fixture_documents()
    staged = fixtures["staged-order-valid.json"]
    staged["lineage"]["lineage_stage"] = "ORDER_STAGED"
    staged["lineage"]["case_state"] = "ORDER_STAGED"
    staged["lineage"]["staging_policy_ref"] = staged["staging_policy_ref"]
    staged["lineage"]["promotion_decision_ref"] = staged["promotion_evidence"][
        "promotion_decision_ref"
    ]
    staged["lineage"]["staged_order_set_ref"] = {
        "id": staged["order_set_id"],
        "sha256": staged["canonical_hash"]["payload_sha256"],
    }

    with pytest.raises(DossierError, match="predecessor SIZE_DECIDED|cannot self-reference"):
        _validate_staging_semantics(fixtures)


def test_sizing_requires_whole_board_lots() -> None:
    fixtures = load_fixture_documents()
    fixtures["sizing-valid.json"]["line_items"][0]["board_lot_quantity"] = "3"

    with pytest.raises(DossierError, match="whole board lot"):
        _validate_portfolio_semantics(fixtures)


def test_portfolio_status_and_eligibility_cannot_disagree() -> None:
    fixtures = load_fixture_documents()
    fixtures["portfolio-proposal-valid.json"]["eligible_for_sizing"] = False

    with pytest.raises(DossierError, match="eligible_for_sizing disagree"):
        _validate_portfolio_semantics(fixtures)


def test_built_proposal_rejects_tampered_classification_identity() -> None:
    fixtures = load_fixture_documents()
    fixtures["portfolio-proposal-valid.json"]["candidate_inputs"][0]["issuer_id"] = (
        "issuer-tampered"
    )

    with pytest.raises(DossierError, match="frozen classification"):
        _validate_portfolio_semantics(fixtures)


def test_built_proposal_rejects_unresolved_classification_snapshot_hash() -> None:
    fixtures = load_fixture_documents()
    fixtures["portfolio-proposal-valid.json"]["classification_snapshot_ref"]["sha256"] = "0" * 64

    with pytest.raises(DossierError, match="classification snapshot reference"):
        _validate_portfolio_semantics(fixtures)


def test_built_proposal_rejects_expired_classification_interval() -> None:
    fixtures = load_fixture_documents()
    fixtures["security-classification-snapshot-valid.json"]["assets"][0]["effective_interval"][
        "effective_to"
    ] = "2026-07-24T03:20:59Z"

    with pytest.raises(DossierError, match="not effective at decision time"):
        _validate_portfolio_semantics(fixtures)


def test_construction_cap_order_is_exact_not_merely_contiguous() -> None:
    fixtures = load_fixture_documents()
    caps = fixtures["portfolio-proposal-valid.json"]["targets"][0]["cap_checks"]
    caps[2], caps[3] = caps[3], caps[2]

    with pytest.raises(DossierError, match="sequence is not exact|policy order exactly"):
        _validate_portfolio_semantics(fixtures)


def test_construction_dependency_order_locks_admission_before_stop_and_exposure() -> None:
    assert CONSTRUCTION_CAP_ORDER == (
        "ELIGIBILITY",
        "CLASSIFICATION",
        "STOP_RISK",
        "ISSUER",
        "CORPORATE_GROUP",
        "SINGLE_NAME",
        "SECTOR",
        "THEME",
        "PORTFOLIO_LOSS_AT_STOP",
        "GROSS_EXPOSURE",
        "NET_EXPOSURE",
        "CASH_RESERVE",
        "TURNOVER",
        "RESERVATIONS",
        "LIQUIDITY_ADV_SPREAD",
        "TAX",
        "MINIMUM_TARGET",
    )


def test_sizing_constraint_set_cannot_omit_a_required_check() -> None:
    fixtures = load_fixture_documents()
    checks = fixtures["sizing-valid.json"]["line_items"][0]["constraint_checks"]
    checks.pop(8)

    with pytest.raises(DossierError, match="constraint-check sequence is not exact"):
        _validate_portfolio_semantics(fixtures)


def test_complete_known_empty_theme_membership_is_schema_representable() -> None:
    fixtures = load_fixture_documents()
    store = SchemaStore(SCHEMA_DIR)
    proposal = fixtures["portfolio-proposal-valid.json"]
    proposal["candidate_inputs"][0]["theme_ids"] = []
    proposal["targets"][0]["theme_ids"] = []
    proposal["summary"]["theme_exposures"] = []
    store.validate(
        proposal,
        SCHEMA_DIR / "portfolio-proposal-v1.schema.json",
        "portfolio-proposal-empty-theme",
    )

    sizing = fixtures["sizing-valid.json"]
    sizing["line_items"][0]["theme_ids"] = []
    sizing["summary"]["projected_theme_exposures"] = []
    store.validate(
        sizing,
        SCHEMA_DIR / "sizing-decision-v1.schema.json",
        "sizing-decision-empty-theme",
    )


def test_portfolio_loss_at_stop_summary_cannot_drift() -> None:
    fixtures = load_fixture_documents()
    fixtures["portfolio-proposal-valid.json"]["summary"]["portfolio_loss_at_stop_fraction"] = (
        "0.020000"
    )

    with pytest.raises(DossierError, match="portfolio_loss_at_stop_fraction.*arithmetic mismatch"):
        _validate_portfolio_semantics(fixtures)


def test_staging_refuses_false_sizing_eligibility() -> None:
    fixtures = load_fixture_documents()
    fixtures["staged-order-valid.json"]["sizing_decision_ref"]["eligible_for_staging"] = False

    with pytest.raises(DossierError, match="not staging-eligible"):
        _validate_staging_semantics(fixtures)


def test_staged_order_price_times_quantity_is_reconciled() -> None:
    fixtures = load_fixture_documents()
    fixtures["staged-order-valid.json"]["orders"][0]["estimated_notional_aud"] = "10049.000000"

    with pytest.raises(DossierError, match="estimated_notional_aud.*arithmetic mismatch"):
        _validate_staging_semantics(fixtures)


def test_every_nested_contract_name_must_resolve_to_a_schema() -> None:
    fixtures = load_fixture_documents()
    fixtures["paper-order-valid.json"]["intent_ref"]["contract_name"] = "unknown-v1"

    with pytest.raises(DossierError, match="no local schema resolves"):
        _validate_contract_name_references(fixtures, SchemaStore(SCHEMA_DIR))


def test_integrated_lineage_requires_every_final_stage_reference() -> None:
    fixtures = load_fixture_documents()
    fixtures["integrated-investment-chain.json"]["lineage"]["staging_policy_ref"] = None

    with pytest.raises(DossierError, match="ORDER_STAGED requires staging_policy_ref"):
        _validate_lineage_semantics(fixtures)


def test_integrated_final_lineage_resolves_real_staged_set_hash() -> None:
    fixtures = load_fixture_documents()
    fixtures["integrated-investment-chain.json"]["lineage"]["staged_order_set_ref"]["sha256"] = (
        "f" * 64
    )

    with pytest.raises(DossierError, match="does not resolve to staged-order-valid.json"):
        _validate_lineage_semantics(fixtures)


def test_lineage_rejects_future_reference_at_earlier_stage() -> None:
    fixtures = load_fixture_documents()
    lineage = fixtures["investment-case-lineage-valid.json"]["lineage"]
    lineage["staging_policy_ref"] = {
        "id": "future-policy",
        "version": "1.0.0",
        "sha256": "a" * 64,
    }

    with pytest.raises(DossierError, match="future-stage reference"):
        _validate_lineage_semantics(fixtures)


def test_evidence_backed_language_cannot_bypass_james() -> None:
    fixtures = load_fixture_documents()
    staged = fixtures["staged-order-valid.json"]
    staged["evidence_tier"] = "EVIDENCE_BACKED"
    staged["promotion_evidence"]["decision"] = "APPROVE_EVIDENCE_BACKED_LANGUAGE"
    staged["promotion_evidence"]["permitted_evidence_tier"] = "EVIDENCE_BACKED"
    staged["promotion_evidence"]["decided_by"] = "Arbi"
    staged["gate_evidence"]["strategy_gate_passed"] = True

    with pytest.raises(DossierError, match="lacks James approval"):
        _validate_staging_semantics(fixtures)


def test_promotion_contract_cannot_grant_evidence_backed_without_james() -> None:
    fixtures = load_fixture_documents()
    promotion = fixtures["promotion-decision-valid.json"]
    promotion["requested_evidence_tier"] = "EVIDENCE_BACKED"
    promotion["permitted_evidence_tier"] = "EVIDENCE_BACKED"
    promotion["decision"] = "APPROVE_EVIDENCE_BACKED_LANGUAGE"
    promotion["gate_evidence"]["strategy_gate_passed"] = True
    promotion["decided_by"] = "Arbi"

    with pytest.raises(DossierError, match="lacks James approval"):
        _validate_promotion_semantics(fixtures)


def test_open_origin_cannot_omit_required_snapshot_class() -> None:
    fixtures = load_fixture_documents()
    manifest = fixtures["evaluation-origin-valid.json"]["snapshot_manifest"]
    fixtures["evaluation-origin-valid.json"]["snapshot_manifest"] = [
        entry for entry in manifest if entry["snapshot_class"] != "SIZING"
    ]

    with pytest.raises(DossierError, match="lacks required snapshot classes"):
        _validate_origin_snapshot_semantics(fixtures)


def test_snapshot_class_must_match_referenced_contract() -> None:
    fixtures = load_fixture_documents()
    portfolio = next(
        entry
        for entry in fixtures["evaluation-origin-valid.json"]["snapshot_manifest"]
        if entry["snapshot_class"] == "PORTFOLIO"
    )
    portfolio["ref"]["contract_name"] = "benchmark-snapshot-v1"

    with pytest.raises(DossierError, match="PORTFOLIO does not map"):
        _validate_origin_snapshot_semantics(fixtures)


def test_recorded_intent_cannot_bridge_a_different_sizing_snapshot() -> None:
    fixtures = load_fixture_documents()
    early_sizing = fixtures["sizing-valid.json"]
    fixtures["paper-intent-valid.json"]["sizing_decision_ref"] = {
        "contract_name": "sizing-decision-v1",
        "artifact_id": early_sizing["sizing_decision_id"],
        "schema_version": early_sizing["schema_version"],
        "sha256": early_sizing["canonical_hash"]["payload_sha256"],
        "created_at": early_sizing["created_at"],
    }

    with pytest.raises(DossierError, match="sizing portfolio snapshot does not match"):
        _validate_origin_snapshot_semantics(fixtures)


def test_s11_protocol_cannot_drift_between_policy_config_and_cohort() -> None:
    fixtures = load_fixture_documents()
    fixtures["evaluation-policy-valid.json"]["bootstrap"]["repetitions"] = "99999"

    with pytest.raises(DossierError, match="S11 statistical protocol drifted"):
        _validate_evaluator_semantics(fixtures)


def test_share_quantity_rejects_six_place_decimal_wire_shape() -> None:
    fixtures = load_fixture_documents()
    fixtures["sizing-valid.json"]["line_items"][0]["approved_quantity"] = "200.000000"

    with pytest.raises(DossierError, match="canonical non-negative integer string"):
        _validate_numeric_wire_shapes(fixtures)


def test_money_and_rate_reject_non_six_place_wire_shape() -> None:
    fixtures = load_fixture_documents()
    fixtures["branch-nav-valid.json"]["branches"][0]["entries"][0]["ending_nav_aud"] = "99980.1"

    with pytest.raises(DossierError, match="six-place Decimal string"):
        _validate_numeric_wire_shapes(fixtures)


def _bhp_check(fixtures: dict, code: str) -> dict:
    """Return the named constraint check on the BHP sizing line."""
    checks = fixtures["sizing-valid.json"]["line_items"][0]["constraint_checks"]
    return next(check for check in checks if check["constraint_code"] == code)


def _reseal_sizing_lines(fixtures: dict) -> None:
    """Re-sign mutated sizing lines.

    An unsigned tamper is already caught by the line digest; the adversarial
    case these tests cover is a tamper that is consistently re-signed.
    """
    for filename in ("sizing-valid.json", "sizing-origin-valid.json"):
        for line in fixtures[filename]["line_items"]:
            line["line_item_sha256"] = _object_payload_sha256(line, "line_item_sha256", filename)
    rewrite_fixture_hashes(fixtures)


def test_sizing_check_must_declare_the_normative_comparison() -> None:
    fixtures = load_fixture_documents()
    _bhp_check(fixtures, "LOSS_HEADROOM")["comparison"] = "MAXIMUM"
    _reseal_sizing_lines(fixtures)

    with pytest.raises(DossierError, match=r"comparison: expected MINIMUM"):
        _validate_portfolio_semantics(fixtures)


def test_minimum_constraint_cannot_pass_below_its_limit() -> None:
    fixtures = load_fixture_documents()
    check = _bhp_check(fixtures, "MINIMUM_ORDER")
    check["observed_value"] = "400.000000"
    _reseal_sizing_lines(fixtures)

    with pytest.raises(DossierError, match=r"observed_value.*arithmetic mismatch"):
        _validate_portfolio_semantics(fixtures)


def test_maximum_constraint_cannot_pass_above_its_limit() -> None:
    fixtures = load_fixture_documents()
    check = _bhp_check(fixtures, "SECTOR")
    check["limit_value"] = "0.050000"
    _reseal_sizing_lines(fixtures)

    with pytest.raises(DossierError, match=r"PASS violates its declared MAXIMUM comparison"):
        _validate_portfolio_semantics(fixtures)


def test_pass_violating_declared_direction_is_rejected() -> None:
    fixtures = load_fixture_documents()
    check = _bhp_check(fixtures, "LOSS_HEADROOM")
    check["observed_value"] = "-1.000000"
    check["applied_value"] = "-1.000000"
    _reseal_sizing_lines(fixtures)

    with pytest.raises(DossierError, match=r"PASS violates its declared MINIMUM comparison"):
        _validate_portfolio_semantics(fixtures)


def test_constraint_limit_must_resolve_from_the_ratified_policy() -> None:
    fixtures = load_fixture_documents()
    _bhp_check(fixtures, "ISSUER")["limit_value"] = "0.900000"
    _reseal_sizing_lines(fixtures)

    with pytest.raises(DossierError, match=r"ISSUER\].limit_value.*arithmetic mismatch"):
        _validate_portfolio_semantics(fixtures)


def test_adv_participation_limit_resolves_from_the_sizing_liquidity_cap() -> None:
    fixtures = load_fixture_documents()
    # The risk policy's 0.10 ADV fraction is a non-binding mandate ceiling;
    # sizing-policy-v1 freezes the binding liquidity cap at 0.02.
    _bhp_check(fixtures, "ADV_PARTICIPATION")["limit_value"] = "2000000.000000"
    _reseal_sizing_lines(fixtures)

    with pytest.raises(DossierError, match=r"ADV_PARTICIPATION\].limit_value"):
        _validate_portfolio_semantics(fixtures)


def test_spread_observed_must_resolve_from_the_proposal_candidate() -> None:
    fixtures = load_fixture_documents()
    _bhp_check(fixtures, "SPREAD")["observed_value"] = "0.001000"
    _reseal_sizing_lines(fixtures)

    with pytest.raises(DossierError, match=r"SPREAD\].observed_value.*arithmetic mismatch"):
        _validate_portfolio_semantics(fixtures)


def test_reduce_action_cannot_bypass_the_direction_assertion() -> None:
    """A REDUCE must land inside its limit; it is not an exemption."""
    fixtures = load_fixture_documents()
    check = _bhp_check(fixtures, "LOSS_HEADROOM")
    check["action"] = "REDUCE"
    check["observed_value"] = "-1.000000"
    check["applied_value"] = "-1.000000"
    _reseal_sizing_lines(fixtures)

    with pytest.raises(DossierError, match=r"REDUCE violates its declared MINIMUM comparison"):
        _validate_portfolio_semantics(fixtures)


def test_available_cash_limit_resolves_from_snapshot_and_reserve() -> None:
    fixtures = load_fixture_documents()
    _bhp_check(fixtures, "AVAILABLE_CASH")["limit_value"] = "999999999.000000"
    _reseal_sizing_lines(fixtures)

    with pytest.raises(DossierError, match=r"AVAILABLE_CASH\].limit_value"):
        _validate_portfolio_semantics(fixtures)


def test_available_cash_observed_resolves_from_the_frozen_snapshot() -> None:
    fixtures = load_fixture_documents()
    _bhp_check(fixtures, "AVAILABLE_CASH")["observed_value"] = "1.000000"
    _reseal_sizing_lines(fixtures)

    with pytest.raises(DossierError, match=r"AVAILABLE_CASH\].observed_value"):
        _validate_portfolio_semantics(fixtures)


def test_target_notional_limit_resolves_from_the_proposal_target() -> None:
    fixtures = load_fixture_documents()
    _bhp_check(fixtures, "TARGET_NOTIONAL")["limit_value"] = "1.000000"
    _reseal_sizing_lines(fixtures)

    with pytest.raises(DossierError, match=r"TARGET_NOTIONAL\]"):
        _validate_portfolio_semantics(fixtures)


def test_unsigned_sizing_line_tamper_is_caught_by_the_line_digest() -> None:
    """The re-seal helper must not be the only thing standing guard."""
    fixtures = load_fixture_documents()
    _bhp_check(fixtures, "SECTOR")["observed_value"] = "0.150000"

    with pytest.raises(DossierError, match=r"line_item_sha256: deterministic line hash mismatch"):
        _validate_portfolio_semantics(fixtures)


def test_reused_artifact_id_with_different_bytes_is_rejected() -> None:
    """A reused ID must fail loudly, not silently disable reference checking."""
    fixtures = load_fixture_documents()
    original = fixtures["risk-policy-valid.json"]
    clone = deepcopy(original)
    clone["policy_version"] = "9.9.9"
    clone["canonical_hash"]["payload_sha256"] = fixture_payload_sha256(clone)
    fixtures["risk-policy-duplicate-id.json"] = clone

    with pytest.raises(DossierError, match=r"is reused for two different payloads"):
        _validate_locally_resolvable_reference_hashes(fixtures)


def test_same_artifact_repeated_verbatim_is_still_allowed() -> None:
    """The guard rejects reuse for DIFFERENT bytes, not honest repetition.

    Without this, tightening the condition to ``previous is not None`` would
    pass the whole suite while breaking the legitimate case of one artifact
    appearing in more than one fixture file.
    """
    fixtures = load_fixture_documents()
    fixtures["risk-policy-repeated.json"] = deepcopy(fixtures["risk-policy-valid.json"])

    _validate_locally_resolvable_reference_hashes(fixtures)


def test_cross_contract_artifact_id_collision_is_rejected() -> None:
    """The exact defect that hid two placeholder digests in the shipped set.

    broker-report-v1 and review-eligibility-v1 once shared one artifact id, so
    the id dropped out of the bare-id index and every reference naming it went
    unchecked.
    """
    fixtures = load_fixture_documents()
    eligibility = fixtures["review-eligibility-valid.json"]
    eligibility["eligibility_decision_id"] = fixtures["broker-report-valid.json"][
        "report_version_id"
    ]
    eligibility["canonical_hash"]["payload_sha256"] = fixture_payload_sha256(eligibility)

    with pytest.raises(DossierError, match="denotes two different payloads across contracts"):
        _validate_locally_resolvable_reference_hashes(fixtures)


@pytest.mark.parametrize("digest", ["d" * 64, "a1" * 32, "9f3c" * 16])
def test_wrong_digest_under_a_wrong_contract_name_is_rejected(digest: str) -> None:
    """A wrong contract_name makes the (contract, id) pair resolve to nothing.

    The id alone still identifies the artifact, so any digest that disagrees
    with the carried one is rejected -- not merely the visually obvious stubs.
    An earlier version tested only a low-entropy shape, which a plausible-looking
    wrong digest walked straight past.
    """
    fixtures = load_fixture_documents()
    report_id = fixtures["broker-report-valid.json"]["report_version_id"]
    fixtures["review-context-valid.json"]["stub_ref"] = {
        "contract_name": "portfolio-snapshot-v1",
        "artifact_id": report_id,
        "sha256": digest,
    }

    with pytest.raises(DossierError, match="but that id is carried by"):
        _validate_locally_resolvable_reference_hashes(fixtures)


def test_reference_to_an_uncarried_artifact_stays_legitimately_opaque() -> None:
    """Opaque references are permitted when the dossier carries no such artifact.

    paper-episode-golden.json legitimately cites an eligibility decision that is
    not a fixture; the check must not force such artifacts into existence.
    """
    fixtures = load_fixture_documents()
    fixtures["review-context-valid.json"]["stub_ref"] = {
        "contract_name": "portfolio-snapshot-v1",
        "artifact_id": "no-such-artifact-in-this-dossier",
        "sha256": "d" * 64,
    }

    _validate_locally_resolvable_reference_hashes(fixtures)
