"""Closed-loop Finding contract and deterministic classifier tests."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from asxos.control_plane.finding import (
    ActionabilityReason,
    Finding,
    build_finding,
    canonical_json,
    classify_actionability,
    finding_fingerprint,
    parse_finding_json,
)


def _finding(**overrides: object) -> Finding:
    base: dict[str, object] = {
        "probe": "full_check",
        "failure_class": "unit_test_failure",
        "severity": "L2",
        "title": "test_price_contract failed",
        "identifiers": {"test_id": "tests/test_prices.py::test_price_contract"},
        "run_url": "https://github.com/Jp8617465-sys/asxos/actions/runs/100",
        "log_excerpt": "assert expected == actual",
        "file_hints": ("asxos/domain/prices/coverage.py",),
        "observed_at": datetime(2026, 9, 7, 18, 2, 11, tzinfo=UTC),
    }
    return build_finding(**(base | overrides))  # type: ignore[arg-type]


def test_same_failure_has_stable_fingerprint_across_run_metadata() -> None:
    common = {
        "probe": "pipeline_health",
        "failure_class": "data_contract_breach",
        "severity": "L3",
        "title": "sync_prices: NO_EQUITY_DATA (ASX)",
        "identifiers": {
            "job": "sync_prices",
            "contract": "NO_EQUITY_DATA",
            "market": "ASX",
        },
        "file_hints": ("asxos/jobs/sync_prices.py",),
    }

    first = build_finding(
        **common,
        run_url="https://github.com/Jp8617465-sys/asxos/actions/runs/100",
        log_excerpt="first run: zero rows",
        observed_at=datetime(2026, 9, 7, 18, 2, 11, tzinfo=UTC),
    )
    later = build_finding(
        **common,
        run_url="https://github.com/Jp8617465-sys/asxos/actions/runs/101",
        log_excerpt="later run: still zero rows",
        observed_at=datetime(2026, 9, 8, 18, 2, 11, tzinfo=UTC),
    )

    assert first.fingerprint == later.fingerprint


def test_fingerprint_formula_is_exact_canonical_json() -> None:
    identity = {
        "probe": "pipeline_health",
        "failure_class": "data_contract_breach",
        "identifiers": {"market": "ASX", "attempt": 1, "complete": False},
    }
    expected = "sha256:" + hashlib.sha256(
        canonical_json(identity).encode("utf-8")
    ).hexdigest()

    assert (
        finding_fingerprint(
            probe="pipeline_health",
            failure_class="data_contract_breach",
            identifiers={"complete": False, "attempt": 1, "market": "ASX"},
        )
        == expected
    )


def test_identifier_types_are_preserved_in_fingerprint() -> None:
    numeric = finding_fingerprint(
        probe="full_check",
        failure_class="lint_failure",
        identifiers={"attempt": 1},
    )
    textual = finding_fingerprint(
        probe="full_check",
        failure_class="lint_failure",
        identifiers={"attempt": "1"},
    )

    assert numeric != textual


def test_missing_stable_identity_produces_null_non_actionable_finding() -> None:
    finding = _finding(identifiers={})

    assert finding.fingerprint is None
    assert finding.actionable_in_code is False


def test_actionability_allows_only_parsed_code_owned_failures() -> None:
    finding = _finding()
    decision = classify_actionability(
        failure_class=finding.failure_class,
        identifiers=finding.identifiers,
        file_hints=finding.file_hints,
    )

    assert finding.actionable_in_code is True
    assert decision.reason is ActionabilityReason.ACTIONABLE_UNIT_TEST


@pytest.mark.parametrize(
    ("failure_class", "identifiers", "reason"),
    [
        (
            "lint_failure",
            {"check_id": "ruff:F401"},
            ActionabilityReason.ACTIONABLE_LINT,
        ),
        (
            "type_check_failure",
            {"check_id": "mypy:arg-type"},
            ActionabilityReason.ACTIONABLE_TYPE_CHECK,
        ),
        (
            "code_invariant_failure",
            {"invariant_id": "invariant:price-completeness"},
            ActionabilityReason.ACTIONABLE_CODE_INVARIANT,
        ),
    ],
)
def test_each_allowlisted_failure_requires_its_parsed_identity(
    failure_class: str,
    identifiers: dict[str, str],
    reason: ActionabilityReason,
) -> None:
    decision = classify_actionability(
        failure_class=failure_class,
        identifiers=identifiers,
        file_hints=("asxos/domain/prices/coverage.py",),
    )

    assert decision.actionable is True
    assert decision.reason is reason


@pytest.mark.parametrize(
    "failure_class",
    [
        "provider_outage",
        "rate_limit",
        "timeout",
        "environment_failure",
        "config_failure",
        "data_absence",
        "data_contract_breach",
        "schema_drift",
        "migration_required",
        "production_data_defect",
        "ambiguous_traceback",
    ],
)
def test_provider_data_migration_and_ambiguous_failures_are_never_actionable(
    failure_class: str,
) -> None:
    decision = classify_actionability(
        failure_class=failure_class,
        identifiers={"check_id": "a-real-check"},
        file_hints=("asxos/jobs/sync_prices.py",),
    )

    assert decision.actionable is False
    assert decision.reason is ActionabilityReason.DENY_FAILURE_CLASS


def test_actionability_rejects_missing_parsed_check_identity() -> None:
    decision = classify_actionability(
        failure_class="unit_test_failure",
        identifiers={"test_id": "traceback mentions pytest"},
        file_hints=("asxos/domain/prices/coverage.py",),
    )

    assert decision.actionable is False
    assert decision.reason is ActionabilityReason.DENY_MISSING_IDENTITY


@pytest.mark.parametrize(
    ("failure_class", "identity_key", "identity"),
    [
        ("unit_test_failure", "test_id", "tests/test_x.py::../../escape"),
        ("lint_failure", "check_id", "F401"),
        ("type_check_failure", "check_id", "mypy"),
        ("code_invariant_failure", "invariant_id", "price-completeness"),
    ],
)
def test_actionability_rejects_unparsed_identity_shapes(
    failure_class: str,
    identity_key: str,
    identity: str,
) -> None:
    decision = classify_actionability(
        failure_class=failure_class,
        identifiers={identity_key: identity},
        file_hints=("asxos/domain/prices/coverage.py",),
    )

    assert decision.actionable is False
    assert decision.reason is ActionabilityReason.DENY_MISSING_IDENTITY


@pytest.mark.parametrize(
    "path",
    [
        ".github/workflows/full-check.yml",
        ".claude/settings.json",
        "asxos/control_plane/finding.py",
        "docs/product/arbi-authority.md",
        "migrations/0053_example.sql",
        "tests/test_prices.py",
        "CLAUDE.md",
    ],
)
def test_actionability_rejects_every_protected_or_test_path(path: str) -> None:
    decision = classify_actionability(
        failure_class="lint_failure",
        identifiers={"check_id": "ruff:F401"},
        file_hints=(path,),
    )

    assert decision.actionable is False
    assert decision.reason is ActionabilityReason.DENY_PROTECTED_PATH


def test_actionability_rejects_non_code_and_missing_hints() -> None:
    non_code = classify_actionability(
        failure_class="lint_failure",
        identifiers={"check_id": "ruff:F401"},
        file_hints=("docs/ops/report.md",),
    )
    missing = classify_actionability(
        failure_class="lint_failure",
        identifiers={"check_id": "ruff:F401"},
        file_hints=(),
    )

    assert non_code.reason is ActionabilityReason.DENY_NON_CODE_PATH
    assert missing.reason is ActionabilityReason.DENY_NO_FILE_HINT


def test_public_classifier_denies_traversal_before_prefix_classification() -> None:
    decision = classify_actionability(
        failure_class="lint_failure",
        identifiers={"check_id": "ruff:F401"},
        file_hints=("asxos/../outside.py",),
    )

    assert decision.actionable is False
    assert decision.reason is ActionabilityReason.DENY_INVALID_FILE_HINT


def test_builder_redacts_before_bounding_and_hashing_excerpt() -> None:
    secret = "ghp_1234567890abcdef"
    finding = _finding(log_excerpt=f"Bearer {secret}\n" + ("x" * 2_100))

    assert len(finding.evidence.log_excerpt) == 2_000
    assert secret not in finding.evidence.log_excerpt
    assert finding.evidence.log_excerpt_sha256 == "sha256:" + hashlib.sha256(
        finding.evidence.log_excerpt.encode("utf-8")
    ).hexdigest()


def test_direct_validation_rejects_recognized_secret_anywhere_in_finding() -> None:
    payload = _finding().model_dump(mode="json")
    payload["title"] = "failed with ghp_1234567890abcdef"

    with pytest.raises(ValidationError, match="recognized credential"):
        Finding.model_validate(payload)


def test_derived_fingerprint_and_actionability_cannot_be_forged() -> None:
    payload = _finding().model_dump(mode="json")
    payload["fingerprint"] = "sha256:" + "0" * 64
    with pytest.raises(ValidationError, match="fingerprint does not match"):
        Finding.model_validate(payload)

    payload = _finding().model_dump(mode="json")
    payload["actionable_in_code"] = False
    with pytest.raises(ValidationError, match="deterministic classifier"):
        Finding.model_validate(payload)


@pytest.mark.parametrize(
    "path",
    ["/etc/passwd", "../outside.py", "asxos/../outside.py", "asxos\\file.py"],
)
def test_file_hints_reject_absolute_parent_and_non_posix_paths(path: str) -> None:
    with pytest.raises(ValidationError, match="file hint"):
        _finding(file_hints=(path,))


def test_file_hints_must_be_sorted_and_unique() -> None:
    payload = _finding().model_dump(mode="json")
    payload["file_hints"] = ["jobs/z.py", "asxos/a.py", "jobs/z.py"]

    with pytest.raises(ValidationError, match="sorted and unique"):
        Finding.model_validate(payload)


def test_contract_rejects_extra_fields_float_identifiers_and_wrong_schema() -> None:
    payload = _finding().model_dump(mode="json")
    payload["unexpected"] = "no"
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        Finding.model_validate(payload)

    with pytest.raises((ValidationError, ValueError), match="float"):
        _finding(identifiers={"test_id": "tests/test_x.py::test_x", "ratio": 0.1})

    payload = _finding().model_dump(mode="json")
    payload["schema_version"] = 2
    with pytest.raises(ValidationError):
        Finding.model_validate(payload)


@pytest.mark.parametrize(
    "run_url",
    [
        "http://github.com/Jp8617465-sys/asxos/actions/runs/100",
        "https://github.com/other/asxos/actions/runs/100",
        "https://github.com/Jp8617465-sys/asxos/actions/runs/latest",
        "https://example.com/run/100",
    ],
)
def test_evidence_rejects_malformed_or_wrong_repository_urls(run_url: str) -> None:
    with pytest.raises(ValidationError, match="run_url"):
        _finding(run_url=run_url)


def test_canonical_json_rejects_floats_and_preserves_utf8() -> None:
    assert canonical_json({"name": "café", "ok": True}) == '{"name":"café","ok":true}'
    with pytest.raises(ValueError, match="float"):
        canonical_json({"ratio": 0.1})


def test_complete_finding_serialization_is_deterministic() -> None:
    first = _finding(identifiers={"test_id": "tests/test_x.py::test_x", "symbol": "WES"})
    second = _finding(identifiers={"symbol": "WES", "test_id": "tests/test_x.py::test_x"})

    assert first.canonical_json() == second.canonical_json()


def test_canonical_serialization_revalidates_mutated_nested_identifiers() -> None:
    finding = _finding()
    finding.identifiers["run_id"] = 101

    with pytest.raises(ValidationError, match="fingerprint does not match"):
        finding.canonical_json()


def test_jsonl_parser_accepts_only_the_canonical_record() -> None:
    finding = _finding()
    canonical = finding.canonical_json()

    assert parse_finding_json(canonical + "\n") == finding
    with pytest.raises(ValueError, match="not canonical"):
        parse_finding_json("  " + canonical)
    with pytest.raises(ValueError, match="exactly one"):
        parse_finding_json(canonical + "\n" + canonical)


def test_finding_field_set_is_frozen() -> None:
    assert set(Finding.model_fields) == {
        "schema_version",
        "probe",
        "failure_class",
        "fingerprint",
        "severity",
        "title",
        "identifiers",
        "evidence",
        "actionable_in_code",
        "file_hints",
        "observed_at",
    }
