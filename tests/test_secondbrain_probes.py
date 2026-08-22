"""Tests for the SB1-02 read-only probe adapters.

The packet's completion proof for SB1-02 is "Deterministic normalized
snapshot; unavailable/error tests" — so the three properties pinned hardest
here are determinism, the unavailable path, and the error path (including its
secret-safety guarantee).
"""

from __future__ import annotations

import subprocess
from collections.abc import Sequence
from datetime import UTC, datetime

import pytest
from pydantic import JsonValue

from asxos.secondbrain.probes import (
    FIELD_PATHS,
    ProbeSpec,
    ProbeUnavailable,
    build_snapshot,
    classify_error,
    execute_probe,
    git_repository_probes,
    run_probes,
    sql_data_probes,
)
from asxos.secondbrain.project_state import ProjectStateSnapshot, leaves

OBSERVED_AT = datetime(2026, 8, 21, 6, 0, tzinfo=UTC)


def _const(value: JsonValue) -> ProbeSpec:
    return ProbeSpec("data.coverage", "test:const", lambda: value)


# --------------------------------------------------------------------------
# execute_probe — the three statuses
# --------------------------------------------------------------------------


def test_successful_probe_is_observed_and_carries_its_value() -> None:
    record = execute_probe(_const({"universe_active": 2384}), observed_at=OBSERVED_AT)

    assert record.status == "observed"
    assert record.value == {"universe_active": 2384}
    assert record.error_class is None


def test_falsy_but_real_values_are_observed_not_unavailable() -> None:
    """0 / "" / [] are genuine observations — only None means "nothing to report"."""
    for falsy in (0, "", [], False):
        record = execute_probe(_const(falsy), observed_at=OBSERVED_AT)
        assert record.status == "observed", f"{falsy!r} should be a real observation"
        assert record.value == falsy


def test_probe_raising_unavailable_is_recorded_unavailable() -> None:
    def unreadable() -> JsonValue:
        raise ProbeUnavailable("no credentials in this environment")

    spec = ProbeSpec("github.open_prs", "test:unreadable", unreadable)
    record = execute_probe(spec, observed_at=OBSERVED_AT)

    assert record.status == "unavailable"
    assert record.value is None
    assert record.error_class is None


def test_probe_returning_none_is_unavailable_not_a_schema_violation() -> None:
    record = execute_probe(_const(None), observed_at=OBSERVED_AT)
    assert record.status == "unavailable"


def test_probe_raising_is_recorded_as_error_with_a_category() -> None:
    def boom() -> JsonValue:
        raise TimeoutError("connection to postgres://user:hunter2@host timed out")

    spec = ProbeSpec("data.migrations", "sql:test", boom)
    record = execute_probe(spec, observed_at=OBSERVED_AT)

    assert record.status == "error"
    assert record.error_class == "timeout"
    assert record.value is None


def test_error_record_never_leaks_the_exception_message() -> None:
    """The whole point of error_class: raw failure text is where secrets live."""
    secret = "postgres://user:hunter2@db.example.com:5432/asxos"

    def boom() -> JsonValue:
        raise ConnectionError(f"could not connect to {secret}")

    spec = ProbeSpec("data.freshness", "sql:test", boom)
    record = execute_probe(spec, observed_at=OBSERVED_AT)

    serialized = record.model_dump_json()
    assert "hunter2" not in serialized
    assert secret not in serialized
    assert record.error_class == "connection_failed"


@pytest.mark.parametrize(
    ("exc", "expected"),
    [
        (subprocess.TimeoutExpired(cmd="git", timeout=1), "timeout"),
        (TimeoutError(), "timeout"),
        (FileNotFoundError(), "tool_not_found"),
        (PermissionError(), "permission_denied"),
        (subprocess.CalledProcessError(1, "git"), "command_failed"),
        (ConnectionError(), "connection_failed"),
        (OSError(), "os_error"),
        (ValueError(), "malformed_response"),
        (RuntimeError(), "unexpected_error"),
    ],
)
def test_classify_error_categories(exc: BaseException, expected: str) -> None:
    assert classify_error(exc) == expected


def test_classify_error_ignores_the_message_entirely() -> None:
    assert classify_error(RuntimeError("token=abc123")) == "unexpected_error"


# --------------------------------------------------------------------------
# build_snapshot — leaf resolution by the probe-name convention
# --------------------------------------------------------------------------


def _echo_probe(path: str) -> ProbeSpec:
    """A probe whose observed value IS its own field path, so leaf resolution is visible."""
    return ProbeSpec(path, f"test:{path}", lambda: path)


def _all_field_probes() -> list[ProbeSpec]:
    return [_echo_probe(path) for path in FIELD_PATHS]


def test_every_field_path_resolves_from_its_matching_probe() -> None:
    records = run_probes(_all_field_probes(), observed_at=OBSERVED_AT)
    snapshot = build_snapshot(records, snapshot_id="snap-test", observed_at=OBSERVED_AT)

    assert snapshot.repository.base_sha.value == "repository.base_sha"
    assert snapshot.github.open_prs.value == "github.open_prs"
    assert snapshot.production.scheduler_owners.value == "production.scheduler_owners"
    assert snapshot.data.coverage.value == "data.coverage"
    assert all(leaf.status == "observed" for leaf in leaves(snapshot).values())


def test_field_paths_covers_exactly_the_schema_leaves() -> None:
    """A schema change is a version bump — it must break here, not silently remap."""
    snapshot = build_snapshot([], snapshot_id="snap-empty", observed_at=OBSERVED_AT)
    assert set(leaves(snapshot)) == set(FIELD_PATHS)


def test_unprobed_leaf_is_unavailable_rather_than_omitted() -> None:
    snapshot = build_snapshot([], snapshot_id="snap-empty", observed_at=OBSERVED_AT)

    assert all(leaf.status == "unavailable" for leaf in leaves(snapshot).values())
    assert all(leaf.value is None for leaf in leaves(snapshot).values())


def test_failed_probe_propagates_its_status_to_the_leaf() -> None:
    def boom() -> JsonValue:
        raise RuntimeError("nope")

    specs = [ProbeSpec("data.migrations", "sql:test", boom)]
    records = run_probes(specs, observed_at=OBSERVED_AT)
    snapshot = build_snapshot(records, snapshot_id="snap-err", observed_at=OBSERVED_AT)

    assert snapshot.data.migrations.status == "error"
    assert snapshot.data.migrations.value is None
    assert snapshot.probes[0].error_class == "unexpected_error"


def test_non_field_path_probe_is_carried_but_backs_no_leaf() -> None:
    """The generic extension point: extra observations ride in probes[], not new fields."""
    specs = [*_all_field_probes(), ProbeSpec("adhoc.table_census", "sql:census", lambda: 41)]
    records = run_probes(specs, observed_at=OBSERVED_AT)
    snapshot = build_snapshot(records, snapshot_id="snap-extra", observed_at=OBSERVED_AT)

    assert len(snapshot.probes) == len(FIELD_PATHS) + 1
    assert any(p.name == "adhoc.table_census" and p.value == 41 for p in snapshot.probes)


def test_duplicate_probe_names_are_rejected() -> None:
    specs = [_const("a"), _const("b")]
    records = run_probes(specs, observed_at=OBSERVED_AT)

    with pytest.raises(ValueError, match="duplicate probe name"):
        build_snapshot(records, snapshot_id="snap-dup", observed_at=OBSERVED_AT)


# --------------------------------------------------------------------------
# Determinism
# --------------------------------------------------------------------------


def test_snapshot_is_byte_identical_across_runs_and_probe_ordering() -> None:
    """The property that makes two wakes diffable."""
    forward = run_probes(_all_field_probes(), observed_at=OBSERVED_AT)
    reverse = run_probes(list(reversed(_all_field_probes())), observed_at=OBSERVED_AT)

    first = build_snapshot(forward, snapshot_id="snap-det", observed_at=OBSERVED_AT)
    second = build_snapshot(reverse, snapshot_id="snap-det", observed_at=OBSERVED_AT)

    assert first.model_dump_json() == second.model_dump_json()


def test_probes_are_sorted_by_name() -> None:
    records = run_probes(list(reversed(_all_field_probes())), observed_at=OBSERVED_AT)
    assert [r.name for r in records] == sorted(FIELD_PATHS)


def test_built_snapshot_validates_against_the_frozen_schema() -> None:
    records = run_probes(_all_field_probes(), observed_at=OBSERVED_AT)
    snapshot = build_snapshot(records, snapshot_id="snap-valid", observed_at=OBSERVED_AT)

    round_tripped = ProjectStateSnapshot.model_validate_json(snapshot.model_dump_json())
    assert round_tripped == snapshot
    assert round_tripped.schema_version == 1


# --------------------------------------------------------------------------
# Concrete adapters
# --------------------------------------------------------------------------


def test_git_probes_read_expected_state_via_injected_runner() -> None:
    calls: list[Sequence[str]] = []

    def fake_runner(argv: Sequence[str]) -> str:
        calls.append(argv)
        return {
            ("git", "rev-parse", "HEAD"): "ae28dbe1234\n",
            ("git", "rev-parse", "--abbrev-ref", "HEAD"): "claude/x\n",
            ("git", "--no-optional-locks", "status", "--porcelain"): "",
        }[tuple(argv)]

    records = run_probes(git_repository_probes(runner=fake_runner), observed_at=OBSERVED_AT)
    snapshot = build_snapshot(records, snapshot_id="snap-git", observed_at=OBSERVED_AT)

    assert snapshot.repository.base_sha.value == "ae28dbe1234"
    assert snapshot.repository.branch.value == "claude/x"
    assert snapshot.repository.dirty_state.value == "clean"
    assert all("git" == argv[0] for argv in calls)


def test_git_dirty_state_reports_dirty_without_leaking_paths() -> None:
    def fake_runner(argv: Sequence[str]) -> str:
        if tuple(argv) == ("git", "--no-optional-locks", "status", "--porcelain"):
            return " M secret_internal_filename.py\n?? .env.local\n"
        return "x\n"

    records = run_probes(git_repository_probes(runner=fake_runner), observed_at=OBSERVED_AT)
    dirty = next(r for r in records if r.name == "repository.dirty_state")

    assert dirty.value == "dirty"
    assert "secret_internal_filename" not in dirty.model_dump_json()
    assert ".env.local" not in dirty.model_dump_json()


def test_git_probe_failure_becomes_an_error_record_not_an_exception() -> None:
    def fake_runner(argv: Sequence[str]) -> str:
        raise subprocess.CalledProcessError(128, list(argv))

    records = run_probes(git_repository_probes(runner=fake_runner), observed_at=OBSERVED_AT)

    assert {r.status for r in records} == {"error"}
    assert {r.error_class for r in records} == {"command_failed"}


def test_sql_probe_uses_a_secret_free_source_identity() -> None:
    seen: list[str] = []

    def fake_query(sql: str) -> JsonValue:
        seen.append(sql)
        return {"applied_count": 97, "latest_version": "20260821080458"}

    records = run_probes(sql_data_probes(fake_query), observed_at=OBSERVED_AT)
    snapshot = build_snapshot(records, snapshot_id="snap-sql", observed_at=OBSERVED_AT)

    assert snapshot.data.migrations.value == {
        "applied_count": 97,
        "latest_version": "20260821080458",
    }
    assert snapshot.probes[0].source == "sql:schema_migrations_count"
    assert "://" not in snapshot.probes[0].source
    assert seen and "schema_migrations" in seen[0]
    assert seen[0].upper().startswith("SELECT "), "the one SQL this module owns must be read-only"


# --------------------------------------------------------------------------
# Regression: a probe returning a non-JsonValue must not escape or leak
# (security-engineer MEDIUM, reproduced before fixing: the record construction
# sat outside the try, so pydantic's ValidationError propagated with the raw
# offending value — a connection object reprs its own DSN — in its message.)
# --------------------------------------------------------------------------


def test_unserialisable_probe_value_becomes_an_error_not_an_exception() -> None:
    class FakeConnection:
        def __repr__(self) -> str:
            return "<Connection dsn='postgres://user:hunter2@db.example.com/asxos'>"

    spec = ProbeSpec("data.freshness", "sql:test", lambda: FakeConnection())  # type: ignore[return-value]
    record = execute_probe(spec, observed_at=OBSERVED_AT)

    assert record.status == "error"
    assert record.error_class == "malformed_response"
    assert "hunter2" not in record.model_dump_json()


def test_one_unserialisable_probe_does_not_abort_the_whole_snapshot() -> None:
    """The module degrades rather than dying — one bad probe must not lose the other ten."""
    specs = [*_all_field_probes()[1:], ProbeSpec("repository.base_sha", "x", lambda: object())]  # type: ignore[return-value]
    records = run_probes(specs, observed_at=OBSERVED_AT)
    snapshot = build_snapshot(records, snapshot_id="snap-partial", observed_at=OBSERVED_AT)

    assert snapshot.repository.base_sha.status == "error"
    observed = [name for name, leaf in leaves(snapshot).items() if leaf.status == "observed"]
    assert len(observed) == len(FIELD_PATHS) - 1


# --------------------------------------------------------------------------
# freshness pass-through (refactoring-expert: load-bearing and unpinned)
# --------------------------------------------------------------------------


def test_freshness_rides_an_observed_record() -> None:
    spec = ProbeSpec("data.coverage", "test:c", lambda: 1, freshness="probed 2026-08-21")
    record = execute_probe(spec, observed_at=OBSERVED_AT)

    assert record.status == "observed"
    assert record.freshness == "probed 2026-08-21"


def test_freshness_is_dropped_when_the_probe_fails_or_is_unavailable() -> None:
    """ProbeRecord's validator REJECTS freshness on a non-observed status — so a probe
    that carries freshness and then fails would raise from inside execute_probe's own
    except block if this were ever regressed."""

    def boom() -> JsonValue:
        raise RuntimeError("x")

    def absent() -> JsonValue:
        raise ProbeUnavailable("x")

    failed = execute_probe(
        ProbeSpec("data.coverage", "t", boom, freshness="f"), observed_at=OBSERVED_AT
    )
    missing = execute_probe(
        ProbeSpec("data.coverage", "t", absent, freshness="f"), observed_at=OBSERVED_AT
    )

    assert failed.status == "error" and failed.freshness is None
    assert missing.status == "unavailable" and missing.freshness is None
