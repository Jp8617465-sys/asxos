"""Pure Sentinel lifecycle and label-projection tests."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from asxos.control_plane.finding import build_finding
from asxos.control_plane.sentinel import (
    ProbeRunEvidence,
    SentinelProjection,
    bind_created_issue,
    project_probe_run,
    sentinel_machine_block,
)

START = datetime(2026, 9, 8, 0, 0, tzinfo=UTC)


def _finding(
    run_id: str = "100",
    *,
    observed_at: datetime = START,
    severity: str = "L2",
    failure_class: str = "unit_test_failure",
    identifiers=None,
    file_hints=("asxos/domain/prices/coverage.py",),
):
    return build_finding(
        probe="full_check",
        failure_class=failure_class,
        severity=severity,
        title="test_price_contract failed",
        identifiers=(
            {"test_id": "tests/test_prices.py::test_price_contract"}
            if identifiers is None
            else identifiers
        ),
        run_url=f"https://github.com/Jp8617465-sys/asxos/actions/runs/{run_id}",
        log_excerpt="assert expected == actual",
        file_hints=file_hints,
        observed_at=observed_at,
    )


def _run(
    run_id: str | None,
    conclusion: str,
    *,
    findings=(),
    output_valid: bool = False,
    provenance_valid: bool = True,
    probe: str = "full_check",
    completed_at: datetime | None = None,
) -> ProbeRunEvidence:
    return ProbeRunEvidence(
        schema_version=1,
        run_id=run_id,
        run_url=(
            f"https://github.com/Jp8617465-sys/asxos/actions/runs/{run_id}"
            if run_id is not None
            else None
        ),
        probe=probe,
        conclusion=conclusion,
        output_valid=output_valid,
        provenance_valid=provenance_valid,
        completed_at=completed_at or START + timedelta(hours=1),
        findings=findings,
    )


def _bind_result(result, *, first_issue_number: int = 42):
    """Model the adapter feeding provider-assigned numbers back to Sentinel."""

    bound = tuple(
        bind_created_issue(projection, issue_number=first_issue_number + index)
        for index, projection in enumerate(result.projections)
    )
    return result.model_copy(update={"projections": bound})


def test_failed_or_missing_probe_runs_do_not_advance_recovery_streak() -> None:
    opened = project_probe_run(
        prior=(),
        run=_run("100", "success", findings=(_finding(),), output_valid=True),
    )
    failed = project_probe_run(
        prior=opened.projections,
        run=_run("101", "failure"),
    )
    missing = project_probe_run(
        prior=failed.projections,
        run=_run(None, "missing"),
    )

    assert failed.projections[0].recovery_run_ids == ()
    assert missing.projections[0].recovery_run_ids == ()


def test_new_stable_finding_creates_one_issue_with_owned_labels_and_machine_block() -> None:
    finding = _finding()
    result = project_probe_run(
        prior=(),
        run=_run("100", "success", findings=(finding,), output_valid=True),
    )

    assert len(result.projections) == 1
    projection = result.projections[0]
    assert projection.labels == ("arbi-ready", "probe:full_check", "sentinel", "sev:L2")
    assert projection.occurrence_count == 1
    assert projection.recovery_run_ids == ()
    assert [command.kind for command in result.commands] == ["create_issue"]
    command = result.commands[0]
    assert command.title == finding.title
    assert command.body is not None
    assert command.body.splitlines()[0] == sentinel_machine_block(finding, run_id="100")


def test_machine_block_is_versioned_canonical_json() -> None:
    block = sentinel_machine_block(_finding(), run_id="100")
    match = re.fullmatch(r"<!-- sentinel:v1 (\{.*\}) -->", block)

    assert match is not None
    payload = json.loads(match.group(1))
    assert list(payload) == ["finding_digest", "fingerprint", "probe", "run_id"]
    assert payload["probe"] == "full_check"
    assert payload["run_id"] == "100"


def test_reappearance_comments_once_and_resets_partial_recovery() -> None:
    opened = _bind_result(
        project_probe_run(
            prior=(),
            run=_run("100", "success", findings=(_finding(),), output_valid=True),
        )
    )
    one_clear = project_probe_run(
        prior=opened.projections,
        run=_run(
            "101",
            "success",
            output_valid=True,
            completed_at=START + timedelta(days=1),
        ),
    )
    reappeared_finding = _finding("102", observed_at=START + timedelta(days=2))
    reappeared = project_probe_run(
        prior=one_clear.projections,
        run=_run(
            "102",
            "success",
            findings=(reappeared_finding,),
            output_valid=True,
            completed_at=START + timedelta(days=2, hours=1),
        ),
    )

    assert one_clear.projections[0].recovery_run_ids == ("101",)
    assert reappeared.projections[0].recovery_run_ids == ()
    assert reappeared.projections[0].occurrence_count == 2
    assert [command.kind for command in reappeared.commands] == ["comment_occurrence"]


def test_replaying_same_occurrence_run_is_idempotent() -> None:
    run = _run("100", "success", findings=(_finding(),), output_valid=True)
    opened = project_probe_run(prior=(), run=run)
    replayed = project_probe_run(prior=opened.projections, run=run)

    assert replayed.projections == opened.projections
    assert replayed.commands == ()


def test_three_distinct_successful_absences_close_with_all_run_urls() -> None:
    result = _bind_result(
        project_probe_run(
            prior=(),
            run=_run("100", "success", findings=(_finding(),), output_valid=True),
        )
    )
    for offset, run_id in enumerate(("101", "102", "103"), start=1):
        result = project_probe_run(
            prior=result.projections,
            run=_run(
                run_id,
                "success",
                output_valid=True,
                completed_at=START + timedelta(days=offset),
            ),
        )

    projection = result.projections[0]
    assert projection.issue_open is False
    assert projection.recovery_run_ids == ("101", "102", "103")
    assert "arbi-ready" not in projection.labels
    assert [command.kind for command in result.commands] == [
        "comment_recovery",
        "close_issue",
        "update_labels",
    ]
    recovery_body = result.commands[0].body
    assert recovery_body is not None
    assert all(f"/runs/{run_id}" in recovery_body for run_id in ("101", "102", "103"))
    assert all(command.issue_number == 42 for command in result.commands)


def test_duplicate_success_run_does_not_advance_recovery_twice() -> None:
    opened = _bind_result(
        project_probe_run(
            prior=(),
            run=_run("100", "success", findings=(_finding(),), output_valid=True),
        )
    )
    clear_run = _run(
        "101",
        "success",
        output_valid=True,
        completed_at=START + timedelta(days=1),
    )
    first = project_probe_run(prior=opened.projections, run=clear_run)
    replay = project_probe_run(prior=first.projections, run=clear_run)

    assert first.projections[0].recovery_run_ids == ("101",)
    assert replay.projections == first.projections


def test_out_of_order_probe_run_fails_closed() -> None:
    opened = project_probe_run(
        prior=(),
        run=_run(
            "100",
            "success",
            findings=(_finding(),),
            output_valid=True,
            completed_at=START + timedelta(days=2),
        ),
    )

    with pytest.raises(ValueError, match="completion order"):
        project_probe_run(
            prior=opened.projections,
            run=_run(
                "101",
                "success",
                output_valid=True,
                completed_at=START + timedelta(days=1),
            ),
        )


@pytest.mark.parametrize("conclusion", ["failure", "cancelled", "skipped"])
def test_non_success_conclusions_do_not_change_projection(conclusion: str) -> None:
    opened = project_probe_run(
        prior=(),
        run=_run("100", "success", findings=(_finding(),), output_valid=True),
    )
    result = project_probe_run(
        prior=opened.projections,
        run=_run("101", conclusion),
    )

    assert result.projections == opened.projections
    assert result.commands == ()


def test_invalid_output_or_provenance_does_not_change_projection() -> None:
    opened = project_probe_run(
        prior=(),
        run=_run("100", "success", findings=(_finding(),), output_valid=True),
    )
    invalid_output = project_probe_run(
        prior=opened.projections,
        run=_run("101", "success", output_valid=False),
    )
    invalid_provenance = project_probe_run(
        prior=opened.projections,
        run=_run("102", "success", output_valid=True, provenance_valid=False),
    )

    assert invalid_output.projections == opened.projections
    assert invalid_provenance.projections == opened.projections


def test_other_probe_success_does_not_advance_originating_probe_recovery() -> None:
    opened = project_probe_run(
        prior=(),
        run=_run("100", "success", findings=(_finding(),), output_valid=True),
    )
    other = project_probe_run(
        prior=opened.projections,
        run=_run("101", "success", output_valid=True, probe="pipeline_health"),
    )

    assert other.projections == opened.projections


def test_unfingerprinted_finding_creates_run_scoped_diagnostic_only() -> None:
    finding = _finding(
        identifiers={},
        failure_class="ambiguous_traceback",
        file_hints=(),
    )
    result = project_probe_run(
        prior=(),
        run=_run("100", "success", findings=(finding,), output_valid=True),
    )

    assert result.projections == ()
    assert [command.kind for command in result.commands] == ["create_diagnostic_issue"]
    assert result.commands[0].labels == (
        "probe:full_check",
        "sentinel",
        "sev:L2",
        "unfingerprinted",
    )
    assert "arbi-ready" not in result.commands[0].labels


@pytest.mark.parametrize(
    ("finding", "forbidden_label"),
    [
        (_finding(severity="L3"), "arbi-ready"),
        (
            _finding(
                failure_class="data_absence",
                identifiers={"contract": "NO_EQUITY_DATA", "market": "ASX"},
            ),
            "arbi-ready",
        ),
    ],
)
def test_l3_and_nonactionable_findings_never_project_arbi_ready(
    finding,
    forbidden_label: str,
) -> None:
    result = project_probe_run(
        prior=(),
        run=_run("100", "success", findings=(finding,), output_valid=True),
    )

    assert forbidden_label not in result.projections[0].labels


def _close_projection(projections, *, first_run_id: int, start_day: int):
    result = None
    for offset in range(3):
        result = project_probe_run(
            prior=projections,
            run=_run(
                str(first_run_id + offset),
                "success",
                output_valid=True,
                completed_at=START + timedelta(days=start_day + offset),
            ),
        )
        projections = result.projections
    assert result is not None
    return result


def test_third_reopen_inside_rolling_thirty_days_marks_flaky_and_removes_ready() -> None:
    result = _bind_result(
        project_probe_run(
            prior=(),
            run=_run("100", "success", findings=(_finding(),), output_valid=True),
        )
    )
    for cycle in range(3):
        close_start = 101 + cycle * 10
        day = 1 + cycle * 5
        result = _close_projection(
            result.projections,
            first_run_id=close_start,
            start_day=day,
        )
        reopen_id = str(close_start + 3)
        reopen_time = START + timedelta(days=day + 3)
        finding = _finding(reopen_id, observed_at=reopen_time)
        result = project_probe_run(
            prior=result.projections,
            run=_run(
                reopen_id,
                "success",
                findings=(finding,),
                output_valid=True,
                completed_at=reopen_time + timedelta(hours=1),
            ),
        )

    projection = result.projections[0]
    assert projection.flaky is True
    assert "flaky" in projection.labels
    assert "arbi-ready" not in projection.labels
    assert "update_labels" in [command.kind for command in result.commands]


def test_created_issue_must_be_bound_once_before_a_later_transition() -> None:
    opened = project_probe_run(
        prior=(),
        run=_run("100", "success", findings=(_finding(),), output_valid=True),
    )

    assert opened.projections[0].issue_number is None
    with pytest.raises(ValueError, match="bind the created issue_number"):
        project_probe_run(
            prior=opened.projections,
            run=_run(
                "101",
                "success",
                output_valid=True,
                completed_at=START + timedelta(days=1),
            ),
        )

    bound = bind_created_issue(opened.projections[0], issue_number=42)
    assert bound.issue_number == 42
    with pytest.raises(ValueError, match="only once"):
        bind_created_issue(bound, issue_number=43)
    with pytest.raises(ValueError, match="positive integer"):
        bind_created_issue(opened.projections[0], issue_number=0)


def test_issue_bodies_never_use_github_closing_keywords() -> None:
    opened = project_probe_run(
        prior=(),
        run=_run("100", "success", findings=(_finding(),), output_valid=True),
    )

    bodies = [command.body for command in opened.commands if command.body is not None]
    assert not any(re.search(r"(?i)\b(?:closes|fixes|resolves)\s+#", body) for body in bodies)


def test_run_contract_rejects_duplicate_fingerprint_and_cross_probe_finding() -> None:
    finding = _finding()
    with pytest.raises(ValidationError, match="repeat a stable fingerprint"):
        _run("100", "success", findings=(finding, finding), output_valid=True)

    with pytest.raises(ValidationError, match="originating probe"):
        _run(
            "100",
            "success",
            findings=(finding,),
            output_valid=True,
            probe="pipeline_health",
        )


def test_batch_projection_is_stable_under_finding_and_prior_permutation() -> None:
    first = _finding(
        identifiers={"test_id": "tests/test_prices.py::test_a"},
    )
    second = _finding(
        identifiers={"test_id": "tests/test_prices.py::test_b"},
    )
    forward = project_probe_run(
        prior=(),
        run=_run("100", "success", findings=(first, second), output_valid=True),
    )
    reverse = project_probe_run(
        prior=(),
        run=_run("100", "success", findings=(second, first), output_valid=True),
    )

    assert reverse == forward

    bound_forward = _bind_result(forward)
    bound_reverse = _bind_result(reverse)
    absent_forward = project_probe_run(
        prior=bound_forward.projections,
        run=_run(
            "101",
            "success",
            output_valid=True,
            completed_at=START + timedelta(days=1),
        ),
    )
    absent_reverse = project_probe_run(
        prior=reversed(bound_reverse.projections),
        run=_run(
            "101",
            "success",
            output_valid=True,
            completed_at=START + timedelta(days=1),
        ),
    )

    assert absent_reverse == absent_forward


def test_projection_field_set_is_frozen() -> None:
    assert set(SentinelProjection.model_fields) == {
        "schema_version",
        "fingerprint",
        "probe",
        "issue_number",
        "issue_open",
        "severity",
        "actionable_in_code",
        "labels",
        "occurrence_count",
        "first_seen",
        "last_seen",
        "last_occurrence_run_id",
        "last_evaluated_run_id",
        "last_evaluated_at",
        "recovery_run_ids",
        "recovery_run_urls",
        "reopened_at",
        "flaky",
        "last_finding_digest",
    }
