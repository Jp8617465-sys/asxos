"""Probe-output adapters for canonical closed-loop Findings."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from asxos.control_plane.probe_adapters import (
    NightlyCheckFailure,
    PipelineHealthFailure,
    ProbeRunContext,
    adapt_nightly_check,
    adapt_nightly_junit,
    adapt_pipeline_health,
    context_from_github_environment,
    findings_jsonl,
)


def test_no_equity_data_fixture_yields_one_non_actionable_finding() -> None:
    context = ProbeRunContext(
        run_id="34100000001",
        run_url=(
            "https://github.com/Jp8617465-sys/asxos/actions/runs/34100000001"
        ),
        repository="Jp8617465-sys/asxos",
        ref="refs/heads/main",
        ref_protected="true",
        event_name="schedule",
        workflow="pipeline_health",
        workflow_ref=(
            "Jp8617465-sys/asxos/.github/workflows/"
            "pipeline-health.yml@refs/heads/main"
        ),
        head_sha="a" * 40,
        observed_at=datetime(2026, 9, 8, 22, 0, tzinfo=UTC),
    )
    failure = PipelineHealthFailure(
        kind="data_absence",
        job_name="sync_prices",
        contract="NO_EQUITY_DATA",
        market="ASX",
        as_of=date(2026, 9, 8),
        log_excerpt="NO_EQUITY_DATA — ASX=0; provider returned no rows",
    )

    findings = adapt_pipeline_health(context=context, failures=(failure,))

    assert len(findings) == 1
    finding = findings[0]
    assert finding.probe == "pipeline_health"
    assert finding.failure_class == "data_absence"
    assert finding.identifiers == {
        "contract": "NO_EQUITY_DATA",
        "job_name": "sync_prices",
        "market": "ASX",
    }
    assert finding.file_hints == ("jobs/sync_prices.py",)
    assert finding.actionable_in_code is False


def _nightly_context() -> ProbeRunContext:
    return ProbeRunContext(
        run_id="34100000002",
        run_url=(
            "https://github.com/Jp8617465-sys/asxos/actions/runs/34100000002"
        ),
        repository="Jp8617465-sys/asxos",
        ref="refs/heads/main",
        ref_protected="true",
        event_name="schedule",
        workflow="nightly_check",
        workflow_ref=(
            "Jp8617465-sys/asxos/.github/workflows/"
            "nightly-check.yml@refs/heads/main"
        ),
        head_sha="b" * 40,
        observed_at=datetime(2026, 9, 8, 15, 17, tzinfo=UTC),
    )


def _pipeline_context() -> ProbeRunContext:
    return ProbeRunContext(
        run_id="34100000004",
        run_url=(
            "https://github.com/Jp8617465-sys/asxos/actions/runs/34100000004"
        ),
        repository="Jp8617465-sys/asxos",
        ref="refs/heads/main",
        ref_protected="true",
        event_name="schedule",
        workflow="pipeline_health",
        workflow_ref=(
            "Jp8617465-sys/asxos/.github/workflows/"
            "pipeline-health.yml@refs/heads/main"
        ),
        head_sha="d" * 40,
        observed_at=datetime(2026, 9, 8, 22, 0, tzinfo=UTC),
    )


def test_nightly_unit_failure_is_actionable_only_with_owned_source_path() -> None:
    failure = NightlyCheckFailure(
        test_id="tests/test_prices.py::test_price_contract",
        log_excerpt="asxos/domain/prices/coverage.py:42: assertion failed",
        source_paths=("asxos/domain/prices/coverage.py",),
    )

    finding = adapt_nightly_check(context=_nightly_context(), failures=(failure,))[0]

    assert finding.failure_class == "unit_test_failure"
    assert finding.actionable_in_code is True
    assert finding.identifiers == {
        "test_id": "tests/test_prices.py::test_price_contract"
    }


def test_nightly_unidentified_failure_is_unfingerprinted_and_non_actionable() -> None:
    failure = NightlyCheckFailure(
        test_id=None,
        log_excerpt="pytest collection failed before a node was identified",
        source_paths=(),
    )

    finding = adapt_nightly_check(context=_nightly_context(), failures=(failure,))[0]

    assert finding.fingerprint is None
    assert finding.actionable_in_code is False


def test_closed_asx_session_suppresses_no_equity_data_noise() -> None:
    failure = PipelineHealthFailure(
        kind="data_absence",
        job_name="sync_prices",
        contract="NO_EQUITY_DATA",
        market="ASX",
        as_of=date(2026, 12, 25),
        log_excerpt="NO_EQUITY_DATA — ASX=0",
    )

    assert adapt_pipeline_health(context=_pipeline_context(), failures=(failure,)) == ()


def test_out_of_horizon_data_absence_becomes_calendar_diagnostic() -> None:
    failure = PipelineHealthFailure(
        kind="data_absence",
        job_name="sync_prices",
        contract="NO_EQUITY_DATA",
        market="ASX",
        as_of=date(2028, 1, 3),
        log_excerpt="NO_EQUITY_DATA — ASX=0",
    )

    finding = adapt_pipeline_health(
        context=_pipeline_context(), failures=(failure,)
    )[0]

    assert finding.failure_class == "calendar_unknown"
    assert finding.identifiers == {"market": "ASX", "source_year": 2028}
    assert finding.actionable_in_code is False


def test_jsonl_is_deterministic_and_contains_no_raw_secret() -> None:
    failures = (
        NightlyCheckFailure(
            test_id="tests/test_prices.py::test_b",
            log_excerpt="token=ghp_abcdefghijklmnopqrstuvwxyz1234567890",
            source_paths=("asxos/domain/prices/coverage.py",),
        ),
        NightlyCheckFailure(
            test_id="tests/test_prices.py::test_a",
            log_excerpt="assert 1 == 2",
            source_paths=("asxos/domain/prices/coverage.py",),
        ),
    )

    findings = adapt_nightly_check(context=_nightly_context(), failures=failures)
    payload = findings_jsonl(findings)

    assert payload == findings_jsonl(tuple(reversed(findings)))
    assert payload.endswith("\n")
    assert payload.count("\n") == 2
    assert "ghp_" not in payload


def test_nightly_junit_extracts_exact_test_and_owned_source_frame() -> None:
    document = b"""\
<testsuites>
  <testsuite name="pytest" tests="1" failures="1">
    <testcase classname="tests.test_prices" name="test_price_contract">
      <failure>asxos/domain/prices/coverage.py:42: AssertionError</failure>
    </testcase>
  </testsuite>
</testsuites>
"""

    finding = adapt_nightly_junit(
        context=_nightly_context(), document=document, probe_failed=True
    )[0]

    assert finding.identifiers == {
        "test_id": "tests/test_prices.py::test_price_contract"
    }
    assert finding.file_hints == ("asxos/domain/prices/coverage.py",)
    assert finding.actionable_in_code is True


def test_malformed_failed_junit_emits_fixed_unfingerprinted_diagnostic() -> None:
    findings = adapt_nightly_junit(
        context=_nightly_context(),
        document=b"<!DOCTYPE x [<!ENTITY leak SYSTEM 'file:///etc/passwd'>]><x/>",
        probe_failed=True,
    )

    assert len(findings) == 1
    assert findings[0].fingerprint is None
    assert findings[0].evidence.log_excerpt == (
        "nightly JUnit report could not be parsed safely"
    )


def test_successful_nightly_junit_emits_no_findings() -> None:
    document = b'<testsuite name="pytest" tests="1"><testcase classname="tests.test_prices" name="test_ok"/></testsuite>'

    assert (
        adapt_nightly_junit(
            context=_nightly_context(), document=document, probe_failed=False
        )
        == ()
    )


def _github_environment() -> dict[str, str]:
    return {
        "GITHUB_RUN_ID": "34100000006",
        "GITHUB_REPOSITORY": "Jp8617465-sys/asxos",
        "GITHUB_REF": "refs/heads/main",
        "GITHUB_REF_PROTECTED": "true",
        "GITHUB_EVENT_NAME": "schedule",
        "GITHUB_WORKFLOW_REF": (
            "Jp8617465-sys/asxos/.github/workflows/"
            "nightly-check.yml@refs/heads/main"
        ),
        "GITHUB_SHA": "f" * 40,
    }


def test_context_requires_github_to_report_main_as_protected() -> None:
    environment = _github_environment()
    environment["GITHUB_REF_PROTECTED"] = "false"

    with pytest.raises(ValueError, match="must be protected"):
        context_from_github_environment(
            workflow="nightly_check",
            environment=environment,
            observed_at=datetime(2026, 9, 8, 15, 17, tzinfo=UTC),
        )


def test_context_requires_protection_claim_to_be_present() -> None:
    environment = _github_environment()
    del environment["GITHUB_REF_PROTECTED"]

    with pytest.raises(ValueError, match="missing variables"):
        context_from_github_environment(
            workflow="nightly_check",
            environment=environment,
            observed_at=datetime(2026, 9, 8, 15, 17, tzinfo=UTC),
        )


def test_context_rejects_unexpected_workflow_trigger() -> None:
    environment = _github_environment()
    environment["GITHUB_EVENT_NAME"] = "push"

    with pytest.raises(ValueError, match="event must be"):
        context_from_github_environment(
            workflow="nightly_check",
            environment=environment,
            observed_at=datetime(2026, 9, 8, 15, 17, tzinfo=UTC),
        )
