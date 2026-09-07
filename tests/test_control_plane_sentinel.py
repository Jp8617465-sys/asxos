"""Pure Sentinel lifecycle and label-projection tests."""

from __future__ import annotations

from datetime import UTC, datetime

from asxos.control_plane.finding import build_finding
from asxos.control_plane.sentinel import ProbeRunEvidence, project_probe_run


def _finding(run_id: str = "100"):
    return build_finding(
        probe="full_check",
        failure_class="unit_test_failure",
        severity="L2",
        title="test_price_contract failed",
        identifiers={"test_id": "tests/test_prices.py::test_price_contract"},
        run_url=f"https://github.com/Jp8617465-sys/asxos/actions/runs/{run_id}",
        log_excerpt="assert expected == actual",
        file_hints=("asxos/domain/prices/coverage.py",),
        observed_at=datetime(2026, 9, 8, 0, 0, tzinfo=UTC),
    )


def _run(
    run_id: str | None,
    conclusion: str,
    *,
    findings=(),
    output_valid: bool = False,
) -> ProbeRunEvidence:
    return ProbeRunEvidence(
        schema_version=1,
        run_id=run_id,
        run_url=(
            f"https://github.com/Jp8617465-sys/asxos/actions/runs/{run_id}"
            if run_id is not None
            else None
        ),
        probe="full_check",
        conclusion=conclusion,
        output_valid=output_valid,
        provenance_valid=True,
        completed_at=datetime(2026, 9, 8, 1, 0, tzinfo=UTC),
        findings=findings,
    )


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
