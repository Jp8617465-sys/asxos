"""Pure Sentinel lifecycle and GitHub Issue projection.

The projector has no GitHub client and performs no I/O. It consumes already
validated Findings plus trusted probe-run evidence, then emits deterministic
state and commands for a credential-owning adapter to apply later.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable
from datetime import datetime, timedelta
from typing import Final, Literal

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictInt,
    StrictStr,
    field_validator,
    model_validator,
)

from asxos.control_plane.finding import Finding, Severity, canonical_json

SENTINEL_SCHEMA_VERSION: Final = 1
RECOVERY_SUCCESSES_REQUIRED: Final = 3
FLAKY_REOPEN_THRESHOLD: Final = 2
FLAKY_WINDOW: Final = timedelta(days=30)

_SLUG_RE: Final = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_SHA256_RE: Final = re.compile(r"^sha256:[0-9a-f]{64}$")
_RUN_ID_RE: Final = re.compile(r"^[1-9][0-9]*$")
_RUN_URL_RE: Final = re.compile(
    r"^https://github\.com/Jp8617465-sys/asxos/actions/runs/([1-9][0-9]*)$"
)

type ProbeConclusion = Literal["success", "failure", "cancelled", "skipped", "missing"]
type CommandKind = Literal[
    "create_issue",
    "create_diagnostic_issue",
    "comment_occurrence",
    "reopen_issue",
    "update_labels",
    "comment_recovery",
    "close_issue",
]


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


def _require_utc(value: datetime, *, field: str) -> datetime:
    offset = value.utcoffset()
    if offset is None or offset.total_seconds() != 0:
        raise ValueError(f"{field} must carry a UTC offset")
    return value


class ProbeRunEvidence(_FrozenModel):
    """One observed probe run; provenance is asserted by the future adapter."""

    schema_version: Literal[1]
    run_id: StrictStr | None
    run_url: StrictStr | None
    probe: str = Field(min_length=1, max_length=64)
    conclusion: ProbeConclusion
    output_valid: StrictBool
    provenance_valid: StrictBool
    completed_at: AwareDatetime
    findings: tuple[Finding, ...] = Field(max_length=100)

    @field_validator("probe")
    @classmethod
    def _probe_is_canonical(cls, value: str) -> str:
        if not _SLUG_RE.fullmatch(value):
            raise ValueError("probe must be lowercase snake_case")
        return value

    @field_validator("completed_at")
    @classmethod
    def _completed_at_is_utc(cls, value: datetime) -> datetime:
        return _require_utc(value, field="completed_at")

    @model_validator(mode="after")
    def _run_identity_and_findings_are_bound(self) -> ProbeRunEvidence:
        if self.conclusion == "missing":
            if self.run_id is not None or self.run_url is not None:
                raise ValueError("missing runs must not claim a run_id or run_url")
        else:
            if self.run_id is None or not _RUN_ID_RE.fullmatch(self.run_id):
                raise ValueError("non-missing runs require a numeric run_id")
            if self.run_url is None:
                raise ValueError("non-missing runs require a run_url")
            match = _RUN_URL_RE.fullmatch(self.run_url)
            if match is None or match.group(1) != self.run_id:
                raise ValueError("run_url must identify the same asxos Actions run as run_id")

        stable_fingerprints: set[str] = set()
        finding_digests: set[str] = set()
        for finding in self.findings:
            if finding.probe != self.probe:
                raise ValueError("every Finding must come from the named originating probe")
            if finding.evidence.run_url != self.run_url:
                raise ValueError("every Finding must bind to the observed run_url")
            if finding.observed_at > self.completed_at:
                raise ValueError("a Finding cannot be observed after its run completed")
            if finding.fingerprint is not None:
                if finding.fingerprint in stable_fingerprints:
                    raise ValueError("a run must not repeat a stable fingerprint")
                stable_fingerprints.add(finding.fingerprint)
            digest = finding_digest(finding)
            if digest in finding_digests:
                raise ValueError("a run must not repeat a complete Finding digest")
            finding_digests.add(digest)
        return self

    @property
    def is_trusted_success(self) -> bool:
        return (
            self.conclusion == "success"
            and self.output_valid
            and self.provenance_valid
            and self.run_id is not None
            and self.run_url is not None
        )


def projected_labels(
    *,
    probe: str,
    severity: Severity,
    actionable_in_code: bool,
    issue_open: bool,
    flaky: bool,
    fingerprint: str | None,
) -> tuple[str, ...]:
    """Return only labels owned by Sentinel, sorted for stable projection."""

    labels = {"sentinel", f"probe:{probe}", f"sev:{severity}"}
    if fingerprint is None:
        labels.add("unfingerprinted")
    elif flaky:
        labels.add("flaky")
    elif issue_open and actionable_in_code and severity in {"L1", "L2"}:
        labels.add("arbi-ready")
    return tuple(sorted(labels))


class SentinelProjection(_FrozenModel):
    """Authoritative pure projection for one stable fingerprint."""

    schema_version: Literal[1]
    fingerprint: str
    probe: str
    issue_number: StrictInt | None = None
    issue_open: StrictBool
    severity: Severity
    actionable_in_code: StrictBool
    labels: tuple[str, ...]
    occurrence_count: StrictInt = Field(ge=1)
    first_seen: AwareDatetime
    last_seen: AwareDatetime
    last_occurrence_run_id: str
    last_evaluated_run_id: str
    last_evaluated_at: AwareDatetime
    recovery_run_ids: tuple[str, ...] = Field(max_length=RECOVERY_SUCCESSES_REQUIRED)
    recovery_run_urls: tuple[str, ...] = Field(max_length=RECOVERY_SUCCESSES_REQUIRED)
    reopened_at: tuple[AwareDatetime, ...] = Field(max_length=100)
    flaky: StrictBool
    last_finding_digest: str

    @field_validator("fingerprint", "last_finding_digest")
    @classmethod
    def _digest_is_pinned(cls, value: str) -> str:
        if not _SHA256_RE.fullmatch(value):
            raise ValueError("must be lowercase sha256:<64 hex>")
        return value

    @field_validator("probe")
    @classmethod
    def _probe_is_canonical(cls, value: str) -> str:
        if not _SLUG_RE.fullmatch(value):
            raise ValueError("probe must be lowercase snake_case")
        return value

    @field_validator("last_occurrence_run_id", "last_evaluated_run_id")
    @classmethod
    def _last_run_id_is_numeric(cls, value: str) -> str:
        if not _RUN_ID_RE.fullmatch(value):
            raise ValueError("last_occurrence_run_id must be numeric")
        return value

    @field_validator("first_seen", "last_seen", "last_evaluated_at")
    @classmethod
    def _seen_times_are_utc(cls, value: datetime) -> datetime:
        return _require_utc(value, field="seen timestamp")

    @field_validator("reopened_at")
    @classmethod
    def _reopen_times_are_canonical(cls, value: tuple[datetime, ...]) -> tuple[datetime, ...]:
        for reopened in value:
            _require_utc(reopened, field="reopened_at")
        if tuple(sorted(set(value))) != value:
            raise ValueError("reopened_at must be sorted and unique")
        return value

    @model_validator(mode="after")
    def _projection_is_self_consistent(self) -> SentinelProjection:
        if self.issue_number is not None and self.issue_number < 1:
            raise ValueError("issue_number must be positive")
        if self.last_seen < self.first_seen:
            raise ValueError("last_seen must not precede first_seen")
        if self.last_evaluated_at < self.last_seen:
            raise ValueError("last_evaluated_at must not precede last_seen")
        if len(self.recovery_run_ids) != len(self.recovery_run_urls):
            raise ValueError("recovery run ids and URLs must have equal length")
        if len(set(self.recovery_run_ids)) != len(self.recovery_run_ids):
            raise ValueError("recovery run ids must be unique")
        for run_id, run_url in zip(self.recovery_run_ids, self.recovery_run_urls, strict=True):
            match = _RUN_URL_RE.fullmatch(run_url)
            if match is None or match.group(1) != run_id:
                raise ValueError("each recovery URL must bind to its run id")
        if self.issue_open and len(self.recovery_run_ids) >= RECOVERY_SUCCESSES_REQUIRED:
            raise ValueError("an open Issue cannot carry a completed recovery streak")
        if not self.issue_open and len(self.recovery_run_ids) != RECOVERY_SUCCESSES_REQUIRED:
            raise ValueError("a closed Issue must carry the three-run recovery evidence")
        expected_labels = projected_labels(
            probe=self.probe,
            severity=self.severity,
            actionable_in_code=self.actionable_in_code,
            issue_open=self.issue_open,
            flaky=self.flaky,
            fingerprint=self.fingerprint,
        )
        if self.labels != expected_labels:
            raise ValueError("labels do not match the deterministic Sentinel projection")
        return self


def bind_created_issue(projection: SentinelProjection, *, issue_number: int) -> SentinelProjection:
    """Bind the GitHub Issue created for a new stable projection.

    The pure projector cannot know the provider-assigned number when it emits a
    ``create_issue`` command.  The adapter must feed that number back exactly
    once before a later run can mutate the Issue.
    """

    if projection.issue_number is not None:
        raise ValueError("a Sentinel projection's issue_number can be bound only once")
    if type(issue_number) is not int or issue_number < 1:
        raise ValueError("issue_number must be a positive integer")
    return SentinelProjection.model_validate(
        projection.model_dump() | {"issue_number": issue_number}
    )


class SentinelCommand(_FrozenModel):
    """One deterministic instruction for the future GitHub adapter."""

    kind: CommandKind
    fingerprint: str | None
    idempotency_key: str
    issue_number: StrictInt | None = None
    title: str | None = None
    body: str | None = None
    labels: tuple[str, ...] = ()

    @field_validator("idempotency_key")
    @classmethod
    def _idempotency_key_is_pinned(cls, value: str) -> str:
        if not _SHA256_RE.fullmatch(value):
            raise ValueError("idempotency_key must be lowercase sha256:<64 hex>")
        return value

    @model_validator(mode="after")
    def _payload_matches_command_kind(self) -> SentinelCommand:
        if self.kind == "create_diagnostic_issue":
            if self.fingerprint is not None:
                raise ValueError("diagnostic Issue commands require a null fingerprint")
        elif self.fingerprint is None:
            raise ValueError("stable-Issue commands require a fingerprint")

        if self.kind in {"create_issue", "create_diagnostic_issue"}:
            if not self.title or not self.body or not self.labels:
                raise ValueError("create commands require title, body, and labels")
            if self.issue_number is not None:
                raise ValueError("create commands must not claim a provider issue_number")
        elif self.issue_number is None:
            raise ValueError("non-create commands require a bound issue_number")
        elif self.kind in {"comment_occurrence", "comment_recovery"}:
            if not self.body or self.title is not None or self.labels:
                raise ValueError("comment commands require only a body payload")
        elif self.kind == "update_labels":
            if not self.labels or self.title is not None or self.body is not None:
                raise ValueError("update_labels requires only a labels payload")
        elif self.title is not None or self.body is not None or self.labels:
            raise ValueError("state-transition commands must not carry content payloads")
        return self


class SentinelResult(_FrozenModel):
    projections: tuple[SentinelProjection, ...]
    commands: tuple[SentinelCommand, ...]


def finding_digest(finding: Finding) -> str:
    return "sha256:" + hashlib.sha256(finding.canonical_json().encode("utf-8")).hexdigest()


def command_idempotency_key(
    kind: CommandKind,
    *,
    fingerprint: str | None,
    run_id: str,
    finding_digest_value: str | None = None,
) -> str:
    """Bind one external command to its immutable lifecycle transition."""

    payload = canonical_json(
        {
            "finding_digest": finding_digest_value,
            "fingerprint": fingerprint,
            "kind": kind,
            "run_id": run_id,
            "schema_version": SENTINEL_SCHEMA_VERSION,
        }
    )
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def sentinel_machine_block(finding: Finding, *, run_id: str) -> str:
    """Return the exact first-line machine block for an occurrence."""

    payload = canonical_json(
        {
            "finding_digest": finding_digest(finding),
            "fingerprint": finding.fingerprint,
            "probe": finding.probe,
            "run_id": run_id,
        }
    )
    return f"<!-- sentinel:v1 {payload} -->"


def _occurrence_body(finding: Finding, *, run_id: str) -> str:
    return (
        f"{sentinel_machine_block(finding, run_id=run_id)}\n\n"
        f"Observed by `{finding.probe}` in run {finding.evidence.run_url}."
    )


def _recovery_body(run_urls: tuple[str, ...]) -> str:
    joined = "\n".join(f"- {url}" for url in run_urls)
    return f"Recovered after three consecutive successful originating-probe runs:\n{joined}"


def _create_stable_issue_command(
    finding: Finding,
    *,
    run_id: str,
    labels: tuple[str, ...],
) -> SentinelCommand:
    assert finding.fingerprint is not None
    return SentinelCommand(
        kind="create_issue",
        fingerprint=finding.fingerprint,
        idempotency_key=command_idempotency_key(
            "create_issue",
            fingerprint=finding.fingerprint,
            run_id=run_id,
        ),
        title=finding.title,
        body=_occurrence_body(finding, run_id=run_id),
        labels=labels,
    )


def _projection_from_finding(finding: Finding, run: ProbeRunEvidence) -> SentinelProjection:
    assert finding.fingerprint is not None
    assert run.run_id is not None
    digest = finding_digest(finding)
    labels = projected_labels(
        probe=finding.probe,
        severity=finding.severity,
        actionable_in_code=finding.actionable_in_code,
        issue_open=True,
        flaky=False,
        fingerprint=finding.fingerprint,
    )
    return SentinelProjection(
        schema_version=SENTINEL_SCHEMA_VERSION,
        fingerprint=finding.fingerprint,
        probe=finding.probe,
        issue_open=True,
        severity=finding.severity,
        actionable_in_code=finding.actionable_in_code,
        labels=labels,
        occurrence_count=1,
        first_seen=finding.observed_at,
        last_seen=finding.observed_at,
        last_occurrence_run_id=run.run_id,
        last_evaluated_run_id=run.run_id,
        last_evaluated_at=run.completed_at,
        recovery_run_ids=(),
        recovery_run_urls=(),
        reopened_at=(),
        flaky=False,
        last_finding_digest=digest,
    )


def _present_transition(
    prior: SentinelProjection,
    finding: Finding,
    run: ProbeRunEvidence,
) -> tuple[SentinelProjection, tuple[SentinelCommand, ...]]:
    assert finding.fingerprint is not None
    assert run.run_id is not None
    if prior.last_evaluated_run_id == run.run_id:
        if finding_digest(finding) != prior.last_finding_digest:
            raise ValueError("a replayed run must carry the original Finding digest")
        if prior.issue_number is None:
            return prior, (
                _create_stable_issue_command(
                    finding,
                    run_id=run.run_id,
                    labels=prior.labels,
                ),
            )
        return prior, ()
    if run.completed_at <= prior.last_evaluated_at:
        raise ValueError("probe runs must be projected in completion order")
    if finding.observed_at < prior.last_seen:
        raise ValueError("Finding observation time must not move backwards")
    if prior.issue_number is None:
        raise ValueError("bind the created issue_number before projecting a later run")

    commands: list[SentinelCommand] = []
    cutoff = run.completed_at - FLAKY_WINDOW
    reopenings = tuple(reopened for reopened in prior.reopened_at if reopened >= cutoff)
    if not prior.issue_open:
        reopenings = (*reopenings, run.completed_at)
        commands.append(
            SentinelCommand(
                kind="reopen_issue",
                fingerprint=prior.fingerprint,
                idempotency_key=command_idempotency_key(
                    "reopen_issue",
                    fingerprint=prior.fingerprint,
                    run_id=run.run_id,
                ),
                issue_number=prior.issue_number,
            )
        )
    flaky = prior.flaky or len(reopenings) > FLAKY_REOPEN_THRESHOLD
    labels = projected_labels(
        probe=finding.probe,
        severity=finding.severity,
        actionable_in_code=finding.actionable_in_code,
        issue_open=True,
        flaky=flaky,
        fingerprint=finding.fingerprint,
    )
    updated = SentinelProjection(
        schema_version=SENTINEL_SCHEMA_VERSION,
        fingerprint=prior.fingerprint,
        probe=prior.probe,
        issue_number=prior.issue_number,
        issue_open=True,
        severity=finding.severity,
        actionable_in_code=finding.actionable_in_code,
        labels=labels,
        occurrence_count=prior.occurrence_count + 1,
        first_seen=prior.first_seen,
        last_seen=finding.observed_at,
        last_occurrence_run_id=run.run_id,
        last_evaluated_run_id=run.run_id,
        last_evaluated_at=run.completed_at,
        recovery_run_ids=(),
        recovery_run_urls=(),
        reopened_at=reopenings,
        flaky=flaky,
        last_finding_digest=finding_digest(finding),
    )
    commands.append(
        SentinelCommand(
            kind="comment_occurrence",
            fingerprint=prior.fingerprint,
            idempotency_key=command_idempotency_key(
                "comment_occurrence",
                fingerprint=prior.fingerprint,
                run_id=run.run_id,
            ),
            issue_number=prior.issue_number,
            body=_occurrence_body(finding, run_id=run.run_id),
        )
    )
    if updated.labels != prior.labels:
        commands.append(
            SentinelCommand(
                kind="update_labels",
                fingerprint=prior.fingerprint,
                idempotency_key=command_idempotency_key(
                    "update_labels",
                    fingerprint=prior.fingerprint,
                    run_id=run.run_id,
                ),
                issue_number=prior.issue_number,
                labels=updated.labels,
            )
        )
    return updated, tuple(commands)


def _absent_transition(
    prior: SentinelProjection,
    run: ProbeRunEvidence,
) -> tuple[SentinelProjection, tuple[SentinelCommand, ...]]:
    assert run.run_id is not None
    assert run.run_url is not None
    if run.run_id == prior.last_evaluated_run_id:
        return prior, ()
    if run.completed_at <= prior.last_evaluated_at:
        raise ValueError("probe runs must be projected in completion order")
    if not prior.issue_open:
        return prior, ()
    if prior.issue_number is None:
        raise ValueError("bind the created issue_number before projecting a later run")

    run_ids = (*prior.recovery_run_ids, run.run_id)
    run_urls = (*prior.recovery_run_urls, run.run_url)
    closes = len(run_ids) == RECOVERY_SUCCESSES_REQUIRED
    labels = projected_labels(
        probe=prior.probe,
        severity=prior.severity,
        actionable_in_code=prior.actionable_in_code,
        issue_open=not closes,
        flaky=prior.flaky,
        fingerprint=prior.fingerprint,
    )
    updated = SentinelProjection(
        **(
            prior.model_dump()
            | {
                "issue_open": not closes,
                "labels": labels,
                "recovery_run_ids": run_ids,
                "recovery_run_urls": run_urls,
                "last_evaluated_run_id": run.run_id,
                "last_evaluated_at": run.completed_at,
            }
        )
    )
    if not closes:
        return updated, ()

    commands: list[SentinelCommand] = [
        SentinelCommand(
            kind="comment_recovery",
            fingerprint=prior.fingerprint,
            idempotency_key=command_idempotency_key(
                "comment_recovery",
                fingerprint=prior.fingerprint,
                run_id=run.run_id,
            ),
            issue_number=prior.issue_number,
            body=_recovery_body(run_urls),
        ),
        SentinelCommand(
            kind="close_issue",
            fingerprint=prior.fingerprint,
            idempotency_key=command_idempotency_key(
                "close_issue",
                fingerprint=prior.fingerprint,
                run_id=run.run_id,
            ),
            issue_number=prior.issue_number,
        ),
    ]
    if labels != prior.labels:
        commands.append(
            SentinelCommand(
                kind="update_labels",
                fingerprint=prior.fingerprint,
                idempotency_key=command_idempotency_key(
                    "update_labels",
                    fingerprint=prior.fingerprint,
                    run_id=run.run_id,
                ),
                issue_number=prior.issue_number,
                labels=labels,
            )
        )
    return updated, tuple(commands)


def _prior_index(prior: Iterable[SentinelProjection]) -> dict[str, SentinelProjection]:
    index: dict[str, SentinelProjection] = {}
    for projection in prior:
        if projection.fingerprint in index:
            raise ValueError(f"duplicate prior fingerprint: {projection.fingerprint}")
        index[projection.fingerprint] = projection
    return index


def project_probe_run(
    *,
    prior: Iterable[SentinelProjection],
    run: ProbeRunEvidence,
) -> SentinelResult:
    """Apply L1-L8 to one probe run without performing an external mutation."""

    projections = _prior_index(prior)
    if not run.is_trusted_success:
        return SentinelResult(
            projections=tuple(sorted(projections.values(), key=lambda item: item.fingerprint)),
            commands=(),
        )

    assert run.run_id is not None
    commands: list[SentinelCommand] = []
    present: set[str] = set()
    ordered_findings = sorted(
        run.findings,
        key=lambda item: (item.fingerprint or "", finding_digest(item)),
    )
    for finding in ordered_findings:
        if finding.fingerprint is None:
            labels = projected_labels(
                probe=finding.probe,
                severity=finding.severity,
                actionable_in_code=False,
                issue_open=True,
                flaky=False,
                fingerprint=None,
            )
            commands.append(
                SentinelCommand(
                    kind="create_diagnostic_issue",
                    fingerprint=None,
                    idempotency_key=command_idempotency_key(
                        "create_diagnostic_issue",
                        fingerprint=None,
                        run_id=run.run_id,
                        finding_digest_value=finding_digest(finding),
                    ),
                    title=finding.title,
                    body=_occurrence_body(finding, run_id=run.run_id),
                    labels=labels,
                )
            )
            continue

        present.add(finding.fingerprint)
        previous = projections.get(finding.fingerprint)
        if previous is None:
            created = _projection_from_finding(finding, run)
            projections[finding.fingerprint] = created
            commands.append(
                _create_stable_issue_command(
                    finding,
                    run_id=run.run_id,
                    labels=created.labels,
                )
            )
            continue
        if previous.probe != run.probe:
            raise ValueError("a fingerprint cannot move between originating probes")
        updated, occurrence_commands = _present_transition(previous, finding, run)
        projections[finding.fingerprint] = updated
        commands.extend(occurrence_commands)

    for fingerprint in sorted(projections):
        projection = projections[fingerprint]
        if projection.probe != run.probe or fingerprint in present:
            continue
        updated, recovery_commands = _absent_transition(projection, run)
        projections[fingerprint] = updated
        commands.extend(recovery_commands)

    return SentinelResult(
        projections=tuple(sorted(projections.values(), key=lambda item: item.fingerprint)),
        commands=tuple(commands),
    )
