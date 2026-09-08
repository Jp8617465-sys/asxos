"""Executable nightly-check Finding adapter tests."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from asxos.control_plane.finding import parse_finding_json
from asxos.control_plane.probe_cli import main


def _environment() -> dict[str, str]:
    return {
        "GITHUB_RUN_ID": "34100000003",
        "GITHUB_REPOSITORY": "Jp8617465-sys/asxos",
        "GITHUB_REF": "refs/heads/main",
        "GITHUB_REF_PROTECTED": "true",
        "GITHUB_EVENT_NAME": "schedule",
        "GITHUB_WORKFLOW_REF": (
            "Jp8617465-sys/asxos/.github/workflows/"
            "nightly-check.yml@refs/heads/main"
        ),
        "GITHUB_SHA": "c" * 40,
    }


def test_cli_writes_reparseable_canonical_finding_artifact(tmp_path: Path) -> None:
    junit = tmp_path / "junit.xml"
    output = tmp_path / "findings.jsonl"
    junit.write_bytes(
        b'<testsuite name="pytest" tests="1" failures="1">'
        b'<testcase classname="tests.test_prices" name="test_price_contract">'
        b'<failure>asxos/domain/prices/coverage.py:42: AssertionError</failure>'
        b"</testcase></testsuite>"
    )

    result = main(
        [
            "--junit",
            str(junit),
            "--pytest-exit-code",
            "1",
            "--output",
            str(output),
        ],
        environment=_environment(),
        clock=lambda: datetime(2026, 9, 8, 15, 17, tzinfo=UTC),
    )

    assert result == 0
    finding = parse_finding_json(output.read_text().removesuffix("\n"))
    assert finding.identifiers == {
        "test_id": "tests/test_prices.py::test_price_contract"
    }


def test_cli_refuses_a_non_main_or_mutable_workflow_identity(tmp_path: Path) -> None:
    junit = tmp_path / "junit.xml"
    output = tmp_path / "findings.jsonl"
    junit.write_bytes(b'<testsuite name="pytest" tests="0"/>')
    environment = _environment()
    environment["GITHUB_REF"] = "refs/pull/42/merge"

    with pytest.raises(ValueError):
        main(
            [
                "--junit",
                str(junit),
                "--pytest-exit-code",
                "0",
                "--output",
                str(output),
            ],
            environment=environment,
            clock=lambda: datetime(2026, 9, 8, 15, 17, tzinfo=UTC),
        )
    assert not output.exists()
