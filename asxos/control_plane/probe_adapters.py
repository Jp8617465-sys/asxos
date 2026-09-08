"""Pure adapters from trusted probe results to canonical Finding artifacts.

The adapters accept structured probe output, never free-form GitHub Issue text.
Run provenance is validated before a Finding is built; Sentinel separately
revalidates the corresponding Actions run and artifact digest before projecting
anything to GitHub.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from enum import StrEnum
from typing import Final, Literal

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StrictStr,
    field_validator,
    model_validator,
)

from asxos.control_plane.asx_calendar import MarketSession, asx_session
from asxos.control_plane.finding import Finding, build_finding

_REPOSITORY: Final = "Jp8617465-sys/asxos"
_PROTECTED_MAIN_REF: Final = "refs/heads/main"
_RUN_ID_RE: Final = re.compile(r"^[1-9][0-9]{0,19}$")
_SHA_RE: Final = re.compile(r"^[0-9a-f]{40}$")
_SLUG_RE: Final = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_CONTRACT_RE: Final = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")
_TEST_ID_RE: Final = re.compile(
    r"^tests/(?:[A-Za-z0-9_]+/)*test_[A-Za-z0-9_]+\.py::"
    r"(?:Test[A-Za-z0-9_]*::)?test_[A-Za-z0-9_]+(?:\[[^\]\r\n]{1,128}\])?$"
)
_SOURCE_FRAME_RE: Final = re.compile(
    r"(?m)^(?P<path>(?:asxos|jobs|scripts)/(?:[A-Za-z0-9_.-]+/)*"
    r"[A-Za-z0-9_.-]+\.py):[1-9][0-9]*:"
)
_MAX_JUNIT_BYTES: Final = 4 * 1024 * 1024
_MAX_JUNIT_ELEMENTS: Final = 20_000
_WORKFLOW_FILES: Final = {
    "nightly_check": "nightly-check.yml",
    "pipeline_health": "pipeline-health.yml",
}
_JOB_FILE_HINTS: Final = {
    "check_au_positions": "jobs/check_au_positions.py",
    "check_cron_health": "jobs/check_cron_health.py",
    "check_thesis_invalidations": "jobs/check_thesis_invalidations.py",
    "check_us_positions": "jobs/check_us_positions.py",
    "compose_brief": "asxos/brief/compose.py",
    "ingest_market_context": "jobs/ingest_market_context.py",
    "ingest_regulatory": "jobs/ingest_regulatory.py",
    "ingest_underlyings": "jobs/ingest_underlyings.py",
    "snapshot_portfolio": "jobs/snapshot_portfolio.py",
    "sync_prices": "jobs/sync_prices.py",
    "validate_price_data": "jobs/validate_price_data.py",
}


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ProbeRunContext(_FrozenModel):
    """GitHub-provided identity for one protected-main probe execution."""

    run_id: StrictStr
    run_url: StrictStr
    repository: Literal["Jp8617465-sys/asxos"]
    ref: Literal["refs/heads/main"]
    ref_protected: Literal["true"]
    event_name: Literal["schedule", "workflow_dispatch"]
    workflow: Literal["nightly_check", "pipeline_health"]
    workflow_ref: StrictStr
    head_sha: StrictStr
    observed_at: AwareDatetime

    @field_validator("run_id")
    @classmethod
    def _run_id_is_numeric(cls, value: str) -> str:
        if not _RUN_ID_RE.fullmatch(value):
            raise ValueError("run_id must be a positive GitHub Actions run ID")
        return value

    @field_validator("head_sha")
    @classmethod
    def _head_sha_is_full_lowercase_sha(cls, value: str) -> str:
        if not _SHA_RE.fullmatch(value):
            raise ValueError("head_sha must be a full lowercase commit SHA")
        return value

    @field_validator("observed_at")
    @classmethod
    def _observed_at_is_utc(cls, value: datetime) -> datetime:
        offset = value.utcoffset()
        if offset is None or offset.total_seconds() != 0:
            raise ValueError("observed_at must carry a UTC offset")
        return value

    @model_validator(mode="after")
    def _run_identity_is_self_consistent(self) -> ProbeRunContext:
        expected_url = f"https://github.com/{_REPOSITORY}/actions/runs/{self.run_id}"
        if self.run_url != expected_url:
            raise ValueError("run_url does not match repository and run_id")
        workflow_file = _WORKFLOW_FILES[self.workflow]
        expected_ref = (
            f"{_REPOSITORY}/.github/workflows/{workflow_file}@{_PROTECTED_MAIN_REF}"
        )
        if self.workflow_ref != expected_ref:
            raise ValueError("workflow_ref is not the protected-main probe workflow")
        return self


class NightlyCheckFailure(_FrozenModel):
    """One pytest failure extracted from the nightly JUnit report."""

    test_id: StrictStr | None
    log_excerpt: StrictStr = Field(max_length=16_000)
    source_paths: tuple[StrictStr, ...] = Field(max_length=20)

    @field_validator("test_id")
    @classmethod
    def _test_id_is_exact_pytest_node(cls, value: str | None) -> str | None:
        if value is not None and not _TEST_ID_RE.fullmatch(value):
            raise ValueError("test_id must be one exact repository pytest node")
        return value


def _junit_test_id(classname: str | None, name: str | None) -> str | None:
    if classname is None or name is None:
        return None
    parts = classname.split(".")
    if len(parts) < 2 or parts[0] != "tests":
        return None
    class_name: str | None = None
    if parts[-1].startswith("Test"):
        class_name = parts.pop()
    module = parts[-1]
    if not module.startswith("test_"):
        return None
    path = "/".join(parts) + ".py"
    candidate = f"{path}::{name}"
    if class_name is not None:
        candidate = f"{path}::{class_name}::{name}"
    return candidate if _TEST_ID_RE.fullmatch(candidate) else None


def parse_nightly_junit(document: bytes) -> tuple[NightlyCheckFailure, ...]:
    """Extract bounded failures from one pytest JUnit document.

    DTDs and entities are refused before the standard-library parser is called;
    only failure/error text is retained and it is redacted later by
    :func:`build_finding`.
    """

    if not document or len(document) > _MAX_JUNIT_BYTES:
        raise ValueError("nightly JUnit document is empty or too large")
    if b"<!DOCTYPE" in document.upper() or b"<!ENTITY" in document.upper():
        raise ValueError("nightly JUnit document contains a forbidden declaration")
    try:
        root = ET.fromstring(document)
    except ET.ParseError:
        raise ValueError("nightly JUnit document is malformed") from None
    if root.tag not in {"testsuite", "testsuites"}:
        raise ValueError("nightly JUnit document has an unexpected root")
    if sum(1 for _ in root.iter()) > _MAX_JUNIT_ELEMENTS:
        raise ValueError("nightly JUnit document contains too many elements")

    failures: list[NightlyCheckFailure] = []
    for testcase in root.iter("testcase"):
        failed = [
            child for child in testcase if child.tag in {"failure", "error"}
        ]
        if not failed:
            continue
        excerpt = "\n".join((child.text or "") for child in failed)[:16_000]
        source_paths = tuple(
            sorted(set(_SOURCE_FRAME_RE.findall(excerpt)))
        )
        failures.append(
            NightlyCheckFailure(
                test_id=_junit_test_id(
                    testcase.attrib.get("classname"), testcase.attrib.get("name")
                ),
                log_excerpt=excerpt or "pytest reported a failure without text",
                source_paths=source_paths,
            )
        )
    return tuple(failures)


class PipelineHealthKind(StrEnum):
    STUCK_JOB = "stuck_job"
    MISSING_SUCCESS = "missing_success"
    CONSECUTIVE_FAILURES = "consecutive_failures"
    DEGRADED_SUCCESS = "degraded_success"
    DATA_ABSENCE = "data_absence"


class PipelineHealthFailure(_FrozenModel):
    """One typed result from the pipeline-health database probe."""

    kind: PipelineHealthKind
    job_name: StrictStr
    contract: StrictStr | None = None
    market: Literal["ASX"] | None = None
    as_of: date | None = None
    log_excerpt: StrictStr = Field(max_length=16_000)

    @field_validator("job_name")
    @classmethod
    def _job_name_is_canonical(cls, value: str) -> str:
        if not _SLUG_RE.fullmatch(value):
            raise ValueError("job_name must be a lowercase snake_case identifier")
        return value

    @field_validator("contract")
    @classmethod
    def _contract_is_canonical(cls, value: str | None) -> str | None:
        if value is not None and not _CONTRACT_RE.fullmatch(value):
            raise ValueError("contract must be an uppercase snake_case identifier")
        return value

    @model_validator(mode="after")
    def _data_absence_fields_are_closed(self) -> PipelineHealthFailure:
        if self.kind is PipelineHealthKind.DATA_ABSENCE:
            if self.contract is None or self.market is None or self.as_of is None:
                raise ValueError(
                    "data_absence requires contract, market, and as_of"
                )
        elif self.contract is not None or self.market is not None:
            raise ValueError("contract and market are reserved for data_absence")
        return self


def context_from_github_environment(
    *,
    workflow: Literal["nightly_check", "pipeline_health"],
    environment: Mapping[str, str],
    observed_at: datetime,
) -> ProbeRunContext:
    """Build context from the seven non-secret GitHub runner identity variables."""

    required = (
        "GITHUB_RUN_ID",
        "GITHUB_REPOSITORY",
        "GITHUB_REF",
        "GITHUB_REF_PROTECTED",
        "GITHUB_EVENT_NAME",
        "GITHUB_WORKFLOW_REF",
        "GITHUB_SHA",
    )
    missing = [name for name in required if not environment.get(name)]
    if missing:
        raise ValueError(f"GitHub probe context is missing variables: {missing}")
    run_id = environment["GITHUB_RUN_ID"]
    repository = environment["GITHUB_REPOSITORY"]
    ref = environment["GITHUB_REF"]
    if repository != _REPOSITORY or ref != _PROTECTED_MAIN_REF:
        raise ValueError("probe must run in the asxos repository on refs/heads/main")
    if environment["GITHUB_REF_PROTECTED"] != "true":
        raise ValueError("probe main ref must be protected")
    raw_event_name = environment["GITHUB_EVENT_NAME"]
    if raw_event_name not in {"schedule", "workflow_dispatch"}:
        raise ValueError("probe event must be schedule or workflow_dispatch")
    event_name: Literal["schedule", "workflow_dispatch"] = (
        "schedule" if raw_event_name == "schedule" else "workflow_dispatch"
    )
    return ProbeRunContext(
        run_id=run_id,
        run_url=f"https://github.com/{repository}/actions/runs/{run_id}",
        repository="Jp8617465-sys/asxos",
        ref="refs/heads/main",
        ref_protected="true",
        event_name=event_name,
        workflow=workflow,
        workflow_ref=environment["GITHUB_WORKFLOW_REF"],
        head_sha=environment["GITHUB_SHA"],
        observed_at=observed_at,
    )


def _require_probe(context: ProbeRunContext, expected: str) -> None:
    if context.workflow != expected:
        raise ValueError(f"adapter requires the {expected} workflow")


def _unique_findings(findings: Sequence[Finding]) -> tuple[Finding, ...]:
    ordered = tuple(
        sorted(
            findings,
            key=lambda finding: (
                finding.fingerprint or "",
                finding.failure_class,
                finding.title,
            ),
        )
    )
    keys = [
        finding.fingerprint or f"unfingerprinted:{finding.title}" for finding in ordered
    ]
    if len(keys) != len(set(keys)):
        raise ValueError("probe output contains duplicate Finding identities")
    return ordered


def adapt_nightly_check(
    *, context: ProbeRunContext, failures: Sequence[NightlyCheckFailure]
) -> tuple[Finding, ...]:
    """Convert structured nightly pytest failures into stable Findings."""

    _require_probe(context, "nightly_check")
    findings: list[Finding] = []
    for failure in failures:
        if failure.test_id is None:
            failure_class = "test_harness_failure"
            identifiers = {}
            title = "nightly-check could not identify a failing test"
        else:
            failure_class = "unit_test_failure"
            identifiers = {"test_id": failure.test_id}
            title = f"{failure.test_id.rsplit('::', 1)[-1]} failed"
        findings.append(
            build_finding(
                probe="nightly_check",
                failure_class=failure_class,
                severity="L2",
                title=title,
                identifiers=identifiers,
                run_url=context.run_url,
                log_excerpt=failure.log_excerpt,
                file_hints=failure.source_paths,
                observed_at=context.observed_at,
            )
        )
    return _unique_findings(findings)


def adapt_nightly_junit(
    *, context: ProbeRunContext, document: bytes, probe_failed: bool
) -> tuple[Finding, ...]:
    """Build Findings directly from the bounded pytest JUnit artifact."""

    _require_probe(context, "nightly_check")
    try:
        failures = parse_nightly_junit(document)
    except ValueError:
        if not probe_failed:
            raise
        failures = (
            NightlyCheckFailure(
                test_id=None,
                log_excerpt="nightly JUnit report could not be parsed safely",
                source_paths=(),
            ),
        )
    if failures and not probe_failed:
        raise ValueError("successful nightly run cannot carry failing test cases")
    if not failures and probe_failed:
        failures = (
            NightlyCheckFailure(
                test_id=None,
                log_excerpt="nightly run failed without a reported failing test",
                source_paths=(),
            ),
        )
    return adapt_nightly_check(context=context, failures=failures)


_PIPELINE_FAILURE_CLASS: Final = {
    PipelineHealthKind.STUCK_JOB: "job_stuck",
    PipelineHealthKind.MISSING_SUCCESS: "job_missing_success",
    PipelineHealthKind.CONSECUTIVE_FAILURES: "job_consecutive_failures",
    PipelineHealthKind.DEGRADED_SUCCESS: "job_degraded",
}


def adapt_pipeline_health(
    *, context: ProbeRunContext, failures: Sequence[PipelineHealthFailure]
) -> tuple[Finding, ...]:
    """Convert typed pipeline-health failures, suppressing closed-market noise."""

    _require_probe(context, "pipeline_health")
    findings: list[Finding] = []
    for failure in failures:
        file_hint = _JOB_FILE_HINTS.get(failure.job_name)
        file_hints = (file_hint,) if file_hint is not None else ()
        identifiers: dict[str, str | int | bool | None]
        if failure.kind is PipelineHealthKind.DATA_ABSENCE:
            assert failure.as_of is not None
            assert failure.contract is not None
            assert failure.market is not None
            assessment = asx_session(failure.as_of)
            if assessment.session is MarketSession.CLOSED:
                continue
            if assessment.session is MarketSession.UNKNOWN:
                failure_class = "calendar_unknown"
                identifiers = {
                    "market": failure.market,
                    "source_year": failure.as_of.year,
                }
                title = f"ASX calendar does not cover {failure.as_of.year}"
            else:
                failure_class = "data_absence"
                identifiers = {
                    "contract": failure.contract,
                    "job_name": failure.job_name,
                    "market": failure.market,
                }
                title = (
                    f"{failure.job_name}: {failure.contract} ({failure.market})"
                )
        else:
            failure_class = _PIPELINE_FAILURE_CLASS[failure.kind]
            identifiers = {"job_name": failure.job_name}
            title = f"{failure.job_name}: {failure.kind.value}"
        findings.append(
            build_finding(
                probe="pipeline_health",
                failure_class=failure_class,
                severity="L2",
                title=title,
                identifiers=identifiers,
                run_url=context.run_url,
                log_excerpt=failure.log_excerpt,
                file_hints=file_hints,
                observed_at=context.observed_at,
            )
        )
    return _unique_findings(findings)


def findings_jsonl(findings: Sequence[Finding]) -> str:
    """Return deterministic canonical JSON Lines with exactly one final newline."""

    ordered = _unique_findings(findings)
    if not ordered:
        return ""
    return "".join(f"{finding.canonical_json()}\n" for finding in ordered)


__all__ = [
    "NightlyCheckFailure",
    "PipelineHealthFailure",
    "PipelineHealthKind",
    "ProbeRunContext",
    "adapt_nightly_check",
    "adapt_nightly_junit",
    "adapt_pipeline_health",
    "context_from_github_environment",
    "findings_jsonl",
    "parse_nightly_junit",
]
