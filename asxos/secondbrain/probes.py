"""Read-only probe adapters that produce a validated snapshot — mission SB1-02.

WHY THIS EXISTS
    SB1-01 froze ``ProjectStateSnapshot`` (``project_state.py``) and
    ``scripts/check_project_state.py`` validates a checked-in snapshot — but
    nothing *produced* one. Every wake hand-rolled state into prose, which is
    why ``roadmap-state.md`` carries its own freshness-correction box and why
    a single 2026-08-21 session found four independent doc-rot instances
    (migration 0044 recorded as an open blocker hours after it was applied;
    ``REQUIRED_MIGRATIONS`` one behind production; an obsolete
    test-environment-gaps section; ``signal_sentiment`` described as empty
    while holding rows). This module is the producing seam.

WHAT IT DOES NOT DO — and must never do
    Every probe is READ-ONLY (freeze doc, "No write probes"). Nothing here
    mutates a row, calls a mutating API, or writes any file this repo tracks.
    It also never writes the snapshot to disk: producing the artifact stays a
    wake-time act, for the same reason ``check_project_state.py`` never
    repairs one — a fabricated snapshot is worse than a stale one, because
    the next wake trusts it.

    One honest exception, stated because the guarantee is otherwise absolute:
    plain ``git status`` refreshes ``.git/index`` as a side effect. The git
    probe passes ``--no-optional-locks`` so it does not, but "read-only" for
    any tool means read-only *as invoked*, not by nature.

    It does not JUDGE state. Contradiction detection and staleness evaluation
    are SB2's (``sb2_deferred_contradiction_fields``,
    ``sb2_deferred_staleness_evaluation``). A snapshot that contradicts itself
    is recorded faithfully here and caught there.

ON CLAUDE.md #10 ("no graceful warnings in infra code, fail loudly")
    Degrading a failed probe to ``unavailable``/``error`` is NOT a violation
    of that rule, and the distinction is load-bearing. #10 governs *control*
    paths — code that decides whether the system may proceed (the API
    lifespan, the allocator gates), where swallowing a failure lets a broken
    system run. This is an *observation* path: its entire product is a record
    of what could and could not be read. An observer that dies on its first
    unreadable surface reports nothing about the eleven surfaces it could
    have read, which is strictly worse evidence. ``unavailable`` is
    first-class in the frozen schema precisely so a partial observation stays
    honest rather than becoming a silent gap. The failure IS the output here,
    not a warning suppressed on the way to something else.

SECRET SAFETY (freeze doc, "No secret values")
    ``error_class`` is a short category — ``"timeout"``, ``"command_failed"``
    — and NEVER a raw message, stderr, URL or DSN, because raw failure text is
    where credentials leak (an asyncpg connection error embeds the DSN; a
    failed ``curl`` echoes the token). :func:`classify_error` maps an
    exception to a category by TYPE and discards the instance. ``source`` is
    likewise a stable identity (``"git rev-parse HEAD"``,
    ``"sql:schema_migrations_count"``), never an interpolated connection
    string. Callers must not defeat this by passing secrets in ``source``.

PROBE LINKAGE (``sb1_02_deferred_probe_linkage``)
    SB1-01 left the leaf→probe link structurally deferred and named the
    candidate convention needing no new field: a probe's ``name`` IS the
    dotted field path it backs (``"github.open_prs"``). This module adopts
    that convention: :func:`build_snapshot` resolves each leaf by exact name
    match against :data:`FIELD_PATHS`'s eleven paths. What *enforces* the
    convention is the drift test, not the constant — see the note on
    :data:`FIELD_PATHS`. A probe whose name is not a field path is still
    carried in ``probes[]`` via the generic extension point, exactly as the
    freeze doc requires.

DETERMINISM
    ``observed_at`` and ``snapshot_id`` are injected, never read from the
    clock here, so the same probe results always build the same snapshot —
    the property that makes a snapshot diffable between wakes. ``probes[]`` is
    sorted by name for the same reason.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Final

from pydantic import JsonValue

from asxos.secondbrain.project_state import (
    SCHEMA_VERSION,
    DataState,
    FieldObservation,
    GithubState,
    ProbeRecord,
    ProductionState,
    ProjectStateSnapshot,
    RepositoryState,
)

__all__ = [
    "FIELD_PATHS",
    "ProbeSpec",
    "ProbeUnavailable",
    "build_snapshot",
    "classify_error",
    "execute_probe",
    "git_repository_probes",
    "run_probes",
    "sql_data_probes",
]

FIELD_PATHS: Final[tuple[str, ...]] = (
    "repository.base_sha",
    "repository.branch",
    "repository.dirty_state",
    "github.open_prs",
    "github.recent_merges",
    "github.workflow_runs",
    "production.release_identity",
    "production.scheduler_owners",
    "data.migrations",
    "data.freshness",
    "data.coverage",
)
"""Every leaf in the frozen v1 schema, as a dotted path.

The probe-linkage convention: a :class:`ProbeSpec` named with one of these
backs that leaf. Kept as an explicit tuple rather than derived by reflection
so that a schema change (which is a version bump) breaks the matching test
loudly instead of silently re-mapping leaves.

Honest scope: :func:`build_snapshot` hardcodes the same eleven literals in
keyword position — deliberately, because that is what keeps the tree
strict-typed under mypy, where a reflection-driven ``**kwargs`` build would
type-erase it. So nothing in production actually *reads* this tuple; it is a
convention constant, and ``test_field_paths_covers_exactly_the_schema_leaves``
is what makes the duplication safe by failing loudly on drift. Do not describe
it as the mechanical authority — the test is.
"""

# sb1_02_deferred_github_production_adapters — no concrete adapter exists here
# for the three `github.*` leaves or the two `production.*` ones, so a snapshot
# built ONLY from this module's adapters is 8-of-11 `unavailable`. That is
# correct-and-incomplete, not a bug: GitHub state needs an authenticated client
# whose call surface (and rate limits) belong to the caller, and `production.*`
# is a judgement about deployment identity that no single query returns. Both
# are supplied by the caller as additional specs today. Promote them to adapters
# here when a second caller needs the same shape — one caller is not a pattern.

_GIT_TIMEOUT_SECONDS: Final = 15
"""Bounded so a wedged git invocation becomes a `timeout` probe, not a hang."""


class ProbeUnavailable(Exception):
    """Raised by a probe when its surface genuinely cannot be read.

    Distinct from an error: ``unavailable`` means "there is nothing to
    observe here" (no credentials configured, the surface does not exist in
    this environment), whereas ``error`` means "the read was attempted and
    failed". Both are first-class; conflating them loses the difference
    between an absent surface and a broken one.
    """


def classify_error(exc: BaseException) -> str:
    """Map an exception to a short, secret-free category.

    Deliberately ignores the exception's message and args — see SECRET SAFETY
    in the module docstring. Only the TYPE informs the category.
    """
    if isinstance(exc, subprocess.TimeoutExpired | TimeoutError):
        return "timeout"
    if isinstance(exc, FileNotFoundError):
        return "tool_not_found"
    if isinstance(exc, PermissionError):
        return "permission_denied"
    if isinstance(exc, subprocess.CalledProcessError):
        return "command_failed"
    if isinstance(exc, ConnectionError):
        return "connection_failed"
    if isinstance(exc, OSError):
        return "os_error"
    if isinstance(exc, ValueError):
        return "malformed_response"
    return "unexpected_error"


@dataclass(frozen=True, slots=True)
class ProbeSpec:
    """One read-only observation to attempt.

    ``name`` should be a member of :data:`FIELD_PATHS` to back a schema leaf;
    any other name is carried in ``probes[]`` only. ``source`` is a stable,
    secret-free identity for how the value was obtained.

    A stdlib dataclass, not the package's pydantic ``_FrozenModel`` — this is
    deliberate, do not "fix" it. It carries a ``Callable``, which pydantic
    would only accept under ``arbitrary_types_allowed``, and it is an
    execution *input* rather than a persisted artifact. Everything that gets
    serialized (``ProbeRecord``, the snapshot) stays pydantic-validated.

    Caller responsibility, and the module's real residual exposure: whatever
    ``run()`` RETURNS lands verbatim in the record's ``value`` and is
    serialized into the snapshot. :func:`classify_error` can keep secrets out
    of the failure path, but nothing here can keep them out of a success path
    that was handed them. A probe must return facts, never raw provider
    payloads or anything carrying a credential.
    """

    name: str
    source: str
    run: Callable[[], JsonValue]
    freshness: JsonValue = None


def execute_probe(spec: ProbeSpec, *, observed_at: datetime) -> ProbeRecord:
    """Run one probe, converting any failure into a status rather than raising.

    A probe returning ``None`` is treated as ``unavailable``: the frozen
    schema forbids a null value on an ``observed`` record, and a probe that
    found nothing has, by definition, nothing to report.

    The record CONSTRUCTION is inside the ``try`` on purpose, not only the
    ``run()`` call. A probe returning something not coercible to ``JsonValue``
    (a driver ``Record``, a live connection object) makes pydantic raise a
    ``ValidationError`` whose message embeds the offending value verbatim —
    and a connection object reprs its own DSN, credentials included. Building
    outside the ``try`` would let that escape into a traceback, i.e. into CI
    logs and wake transcripts: the exact leak SECRET SAFETY exists to stop,
    one frame further out. ``ValidationError`` subclasses ``ValueError``, so
    :func:`classify_error` already categorises it as ``malformed_response``.
    It would also abort the whole snapshot over one bad probe, contradicting
    this module's own reason for degrading rather than dying.
    """
    try:
        value = spec.run()
        if value is None:
            return ProbeRecord(
                name=spec.name, status="unavailable", source=spec.source, observed_at=observed_at
            )
        return ProbeRecord(
            name=spec.name,
            status="observed",
            source=spec.source,
            observed_at=observed_at,
            value=value,
            freshness=spec.freshness,
        )
    except ProbeUnavailable:
        return ProbeRecord(
            name=spec.name, status="unavailable", source=spec.source, observed_at=observed_at
        )
    except Exception as exc:  # deliberate breadth: any failure becomes a typed record
        return ProbeRecord(
            name=spec.name,
            status="error",
            source=spec.source,
            observed_at=observed_at,
            error_class=classify_error(exc),
        )


def run_probes(specs: Iterable[ProbeSpec], *, observed_at: datetime) -> list[ProbeRecord]:
    """Execute every probe and return the records sorted by name (determinism)."""
    return sorted(
        (execute_probe(spec, observed_at=observed_at) for spec in specs),
        key=lambda record: record.name,
    )


def _leaf(records: Mapping[str, ProbeRecord], path: str) -> FieldObservation:
    """Resolve one schema leaf from its backing probe, by the name convention.

    A path with no backing probe is ``unavailable`` — an unobserved surface is
    reported as such rather than omitted, so a consumer can never mistake a
    gap in coverage for a healthy reading.
    """
    record = records.get(path)
    if record is None or record.status != "observed":
        return FieldObservation(status="unavailable" if record is None else record.status)
    return FieldObservation(status="observed", value=record.value)


def build_snapshot(
    records: Sequence[ProbeRecord], *, snapshot_id: str, observed_at: datetime
) -> ProjectStateSnapshot:
    """Assemble probe records into a validated snapshot.

    Raises on duplicate probe names: two probes claiming the same leaf makes
    the resolved value depend on ordering, which would silently break the
    determinism this module exists to provide.
    """
    by_name: dict[str, ProbeRecord] = {}
    for record in records:
        if record.name in by_name:
            raise ValueError(f"duplicate probe name {record.name!r} — leaf resolution is ambiguous")
        by_name[record.name] = record

    return ProjectStateSnapshot(
        snapshot_id=snapshot_id,
        schema_version=SCHEMA_VERSION,
        observed_at=observed_at,
        repository=RepositoryState(
            base_sha=_leaf(by_name, "repository.base_sha"),
            branch=_leaf(by_name, "repository.branch"),
            dirty_state=_leaf(by_name, "repository.dirty_state"),
        ),
        github=GithubState(
            open_prs=_leaf(by_name, "github.open_prs"),
            recent_merges=_leaf(by_name, "github.recent_merges"),
            workflow_runs=_leaf(by_name, "github.workflow_runs"),
        ),
        production=ProductionState(
            release_identity=_leaf(by_name, "production.release_identity"),
            scheduler_owners=_leaf(by_name, "production.scheduler_owners"),
        ),
        data=DataState(
            migrations=_leaf(by_name, "data.migrations"),
            freshness=_leaf(by_name, "data.freshness"),
            coverage=_leaf(by_name, "data.coverage"),
        ),
        probes=sorted(by_name.values(), key=lambda record: record.name),
    )


# --------------------------------------------------------------------------
# Concrete adapters
# --------------------------------------------------------------------------

CommandRunner = Callable[[Sequence[str]], str]
"""Runs a read-only argv and returns stdout. Injectable so tests never shell out."""


def _default_command_runner(repo_root: str) -> CommandRunner:
    def run(argv: Sequence[str]) -> str:
        completed = subprocess.run(  # fixed argv, no shell=True, no interpolated input
            argv,
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
            timeout=_GIT_TIMEOUT_SECONDS,
        )
        return completed.stdout

    return run


def git_repository_probes(
    *, repo_root: str = ".", runner: CommandRunner | None = None
) -> tuple[ProbeSpec, ...]:
    """Read-only git probes for the three ``repository`` leaves.

    Every argv is a fixed read-only git command — no ``shell=True``, no
    interpolated user input, nothing that writes to the object store or the
    index. ``dirty_state`` is normalised to ``clean``/``dirty`` rather than
    carrying the porcelain listing, because untracked paths are themselves
    sometimes sensitive and the leaf only needs the state.
    """
    run = runner if runner is not None else _default_command_runner(repo_root)

    def base_sha() -> JsonValue:
        return run(["git", "rev-parse", "HEAD"]).strip()

    def branch() -> JsonValue:
        return run(["git", "rev-parse", "--abbrev-ref", "HEAD"]).strip()

    def dirty_state() -> JsonValue:
        # --no-optional-locks: plain `git status` REFRESHES .git/index (and takes
        # index.lock) as a side effect, which would make this module's "writes
        # nothing" guarantee literally false and can collide with a concurrent
        # git process, surfacing as a spurious `command_failed` probe.
        argv = ["git", "--no-optional-locks", "status", "--porcelain"]
        return "dirty" if run(argv).strip() else "clean"

    return (
        ProbeSpec("repository.base_sha", "git rev-parse HEAD", base_sha),
        ProbeSpec("repository.branch", "git rev-parse --abbrev-ref HEAD", branch),
        ProbeSpec(
            "repository.dirty_state", "git --no-optional-locks status --porcelain", dirty_state
        ),
    )


QueryRunner = Callable[[str], JsonValue]
"""Runs one read-only SQL statement and returns its result as JSON-able data.

Injected rather than constructed here so this module holds no connection, no
credentials, and no import-time dependency on a live database — and so the
caller, not this module, owns the read-only guarantee of its connection.
"""

_MIGRATIONS_SQL: Final = (
    "SELECT count(*) AS applied_count, max(version) AS latest_version "
    "FROM supabase_migrations.schema_migrations"
)


def sql_data_probes(query: QueryRunner, *, freshness: JsonValue = None) -> tuple[ProbeSpec, ...]:
    """Read-only SQL probe for the ``data.migrations`` leaf.

    Only the migration inventory is covered here: it is the one datum with an
    exact, environment-independent SELECT. ``data.freshness`` and
    ``data.coverage`` depend on which tables a given wake cares about, so they
    are supplied by the caller as additional specs rather than hardcoded into
    a shared adapter that would rot the moment the table set changes.

    ``source`` is a query IDENTITY, never the statement's connection — see
    SECRET SAFETY.
    """

    def migrations() -> JsonValue:
        return query(_MIGRATIONS_SQL)

    return (ProbeSpec("data.migrations", "sql:schema_migrations_count", migrations, freshness),)
