"""`log_evidence` and `asx evidence` — the write path for research a human did.

What these tests hold, in order of what would hurt most if it broke:

1. **Logging never moves a clock.** No `thesis_revisions` row, no
   `last_revisited_at`, no `revisit_due_at`, and no UPDATE of any existing row's
   `retrieved_at`. `approve_object()`'s staleness gate reads `retrieved_at`, so a
   logging path that refreshed it would launder a stale thesis into approvable —
   the same shape as `0060`'s "an answering-type revision buys another N days".

2. **NULL is not neutral.** Omitting `--stance` records NULL; only an explicit
   `neutral` records a judgement of non-diagnostic. The CLI renders an unmarked
   row as an em dash rather than as a stance.

3. **The hash is the one the screen already uses.** sha256 over canonical JSON,
   sorted keys, no whitespace, Decimals as strings — so a human citation and a
   screen citation are comparable rather than merely both hashed.
"""
from __future__ import annotations

import hashlib
import json
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from decimal import Decimal as D
from typing import Any

import pytest
from typer.testing import CliRunner

from asxos.domain.theses import service as svc

AS_OF = datetime(2026, 9, 20, 0, 0, tzinfo=UTC)

#: `FakeConn` captures positional bind args; this names `add_thesis_evidence`'s
#: INSERT order so a reorder fails readably instead of comparing the wrong types.
_EV = {
    "thesis_id": 0,
    "source_agent": 1,
    "tier": 2,
    "claim_text": 3,
    "source_type": 4,
    "source_table": 5,
    "source_as_of": 6,
    "snapshot_data": 7,
    "snapshot_hash": 8,
    "source_url": 9,
    "stance": 10,
}


class FakeConn:
    """Enough of asyncpg for the evidence path, and nothing else."""

    def __init__(self, *, thesis_exists: bool = True) -> None:
        self.thesis_exists = thesis_exists
        self.executed: list[tuple[str, tuple[object, ...]]] = []
        self.evidence: list[tuple[object, ...]] = []
        self.fetched: list[tuple[str, tuple[object, ...]]] = []

    async def execute(self, query: str, *args: object) -> str:
        self.executed.append((query, args))
        return "INSERT 0 1"

    async def fetchrow(self, query: str, *args: object) -> dict[str, Any] | None:
        self.fetched.append((query, args))
        if "INSERT INTO thesis_evidence" in query:
            self.evidence.append(args)
            return {"evidence_id": len(self.evidence)}
        if "FROM theses" in query:
            return {"symbol": "CBA.AU"} if self.thesis_exists else None
        return None

    async def fetch(self, query: str, *args: object) -> list[Any]:
        self.fetched.append((query, args))
        return []

    def transaction(self) -> Any:
        @asynccontextmanager
        async def _tx() -> Any:
            yield

        return _tx()


# --- the invariant: logging is not revising ----------------------------------------


async def test_logging_writes_no_revision_and_touches_no_clock() -> None:
    conn = FakeConn()
    await svc.log_evidence(
        conn,  # type: ignore[arg-type]
        thesis_id=1,
        claim_text="RBA held; deposit repricing lag is narrower than assumed",
        tier="inferred",
        stance="contradicts",
        snapshot_data={"cash_rate": D("3.85")},
    )
    all_sql = " ".join(q for q, _ in conn.executed) + " ".join(q for q, _ in conn.fetched)
    assert "thesis_revisions" not in all_sql, "citing is not revising"
    assert "last_revisited_at" not in all_sql, "citing is not revisiting"
    assert "revisit_due_at" not in all_sql, "a citation must not buy another cadence of silence"


async def test_logging_never_updates_an_existing_retrieved_at() -> None:
    """`approve_object`'s staleness gate reads `retrieved_at`. A write path that
    refreshed it would turn a stale thesis into an approvable one silently."""
    conn = FakeConn()
    await svc.log_evidence(
        conn,  # type: ignore[arg-type]
        thesis_id=1, claim_text="c", tier="verified", snapshot_data={"a": 1},
    )
    for q, _ in conn.executed + conn.fetched:
        assert "UPDATE thesis_evidence" not in q
        assert "retrieved_at" not in q, (
            "the new row takes the column DEFAULT; no statement should name retrieved_at at all"
        )


# --- NULL is not neutral -----------------------------------------------------------


async def test_omitting_stance_records_null_not_neutral() -> None:
    conn = FakeConn()
    await svc.log_evidence(
        conn,  # type: ignore[arg-type]
        thesis_id=1, claim_text="c", tier="verified", snapshot_data={"a": 1},
    )
    (args,) = conn.evidence
    assert args[_EV["stance"]] is None


@pytest.mark.parametrize("stance", ["supports", "contradicts", "neutral"])
async def test_each_stance_is_recorded_verbatim(stance: str) -> None:
    conn = FakeConn()
    await svc.log_evidence(
        conn,  # type: ignore[arg-type]
        thesis_id=1, claim_text="c", tier="verified", stance=stance, snapshot_data={"a": 1},
    )
    (args,) = conn.evidence
    assert args[_EV["stance"]] == stance


async def test_an_unknown_stance_is_refused_before_the_insert() -> None:
    conn = FakeConn()
    with pytest.raises(ValueError, match="stance"):
        await svc.log_evidence(
            conn,  # type: ignore[arg-type]
            thesis_id=1, claim_text="c", tier="verified", stance="refutes",
            snapshot_data={"a": 1},
        )
    assert conn.evidence == []


async def test_the_service_vocabulary_matches_the_migration() -> None:
    """The Python constants and migration 0061's CHECK must not drift apart."""
    sql = (
        __import__("pathlib").Path(__file__).resolve().parent.parent
        / "migrations/0061_evidence_stance.sql"
    ).read_text()
    for value in svc.EVIDENCE_STANCES:
        assert f"'{value}'" in sql
    assert len(svc.EVIDENCE_STANCES) == 3


# --- hashing and shape -------------------------------------------------------------


async def test_hash_is_sha256_over_canonical_json_with_decimals_as_strings() -> None:
    conn = FakeConn()
    await svc.log_evidence(
        conn,  # type: ignore[arg-type]
        thesis_id=1, claim_text="c", tier="verified", stance="supports",
        snapshot_data={"b": D("1.50"), "a": "x"},
    )
    (args,) = conn.evidence
    canonical = '{"a":"x","b":"1.50"}'
    assert args[_EV["snapshot_data"]] == canonical
    assert args[_EV["snapshot_hash"]] == hashlib.sha256(canonical.encode()).hexdigest()


def test_canonical_snapshot_is_stable_under_key_order_and_float_formatting() -> None:
    a, ha = svc.canonical_snapshot({"x": D("2.500"), "y": 1})
    b, hb = svc.canonical_snapshot({"y": 1, "x": D("2.500")})
    assert (a, ha) == (b, hb)
    assert "2.500" in a, "a Decimal must serialise as its exact string, never as a float"


async def test_a_nonspeculative_citation_must_carry_a_snapshot() -> None:
    conn = FakeConn()
    with pytest.raises(ValueError, match="snapshot_data"):
        await svc.log_evidence(
            conn,  # type: ignore[arg-type]
            thesis_id=1, claim_text="c", tier="verified",
        )
    assert conn.evidence == []


async def test_a_speculative_citation_may_omit_the_snapshot() -> None:
    conn = FakeConn()
    await svc.log_evidence(
        conn,  # type: ignore[arg-type]
        thesis_id=1, claim_text="a hunch", tier="speculative",
    )
    (args,) = conn.evidence
    assert args[_EV["snapshot_data"]] is None and args[_EV["snapshot_hash"]] is None


async def test_a_source_url_requires_the_external_source_type() -> None:
    conn = FakeConn()
    with pytest.raises(ValueError, match="external_url"):
        await svc.log_evidence(
            conn,  # type: ignore[arg-type]
            thesis_id=1, claim_text="c", tier="verified", snapshot_data={"a": 1},
            source_url="https://example.com/ann", source_type="db_query",
        )


async def test_an_external_citation_records_its_url(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = FakeConn()
    await svc.log_evidence(
        conn,  # type: ignore[arg-type]
        thesis_id=1, claim_text="guidance withdrawn", tier="verified",
        stance="contradicts", snapshot_data={"quote": "FY27 guidance is withdrawn"},
        source_type="external_url", source_url="https://example.com/ann",
    )
    (args,) = conn.evidence
    assert args[_EV["source_url"]] == "https://example.com/ann"
    assert args[_EV["source_type"]] == "external_url"
    assert args[_EV["stance"]] == "contradicts"


async def test_a_missing_thesis_is_named_not_left_to_the_foreign_key() -> None:
    conn = FakeConn(thesis_exists=False)
    with pytest.raises(ValueError, match="not found"):
        await svc.log_evidence(
            conn,  # type: ignore[arg-type]
            thesis_id=999, claim_text="c", tier="verified", snapshot_data={"a": 1},
        )
    assert conn.evidence == []


async def test_an_empty_claim_is_refused() -> None:
    conn = FakeConn()
    with pytest.raises(ValueError, match="claim_text"):
        await svc.log_evidence(
            conn,  # type: ignore[arg-type]
            thesis_id=1, claim_text="   ", tier="verified", snapshot_data={"a": 1},
        )


# --- CLI ---------------------------------------------------------------------------


def _cli_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setenv("TERM", "dumb")
    monkeypatch.setenv("COLUMNS", "200")


def test_cli_evidence_log_requires_the_personal_use_firewall(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """s766B gate, same as every other thesis-touching command."""
    monkeypatch.delenv("ASXOS_PERSONAL_USE", raising=False)
    monkeypatch.setenv("NO_COLOR", "1")
    from asxos.cli.main import app

    result = CliRunner().invoke(app, ["evidence", "log", "CBA.AU", "--claim", "c"])
    assert result.exit_code != 0
    assert "ASXOS_PERSONAL_USE" in result.output


def test_cli_refuses_both_a_url_and_a_table(monkeypatch: pytest.MonkeyPatch) -> None:
    _cli_env(monkeypatch)
    from asxos.cli.main import app

    result = CliRunner().invoke(
        app,
        [
            "evidence", "log", "CBA.AU", "--claim", "c",
            "--source-url", "https://example.com", "--source-table", "prices",
        ],
    )
    assert result.exit_code != 0
    assert "not both" in result.output


def test_cli_refuses_two_snapshot_sources(monkeypatch: pytest.MonkeyPatch) -> None:
    _cli_env(monkeypatch)
    from asxos.cli.main import app

    result = CliRunner().invoke(
        app,
        ["evidence", "log", "CBA.AU", "--claim", "c", "--quote", "q", "--snapshot", "{}"],
    )
    assert result.exit_code != 0
    assert "at most one" in result.output


def test_cli_refuses_a_naive_as_of(monkeypatch: pytest.MonkeyPatch) -> None:
    """A timestamp with no offset would make the citation claim a precision the
    source never supplied, so it is refused rather than assumed to be UTC."""
    import typer

    from asxos.cli.evidence import _parse_as_of

    with pytest.raises(typer.BadParameter, match="no timezone"):
        _parse_as_of("2026-09-20T04:00:00")
    assert _parse_as_of("2026-09-20") == datetime(2026, 9, 20, tzinfo=UTC)
    assert _parse_as_of(None) is None


def test_cli_quote_becomes_the_hashed_snapshot() -> None:
    from asxos.cli.evidence import _load_snapshot

    assert _load_snapshot(None, None, "FY27 guidance is withdrawn") == {
        "quote": "FY27 guidance is withdrawn"
    }
    assert _load_snapshot(json.dumps({"a": 1}), None, None) == {"a": 1}
    assert _load_snapshot(None, None, None) is None


def test_cli_snapshot_must_be_a_json_object() -> None:
    import typer

    from asxos.cli.evidence import _load_snapshot

    with pytest.raises(typer.BadParameter, match="JSON object"):
        _load_snapshot("[1, 2]", None, None)
    with pytest.raises(typer.BadParameter, match="not valid JSON"):
        _load_snapshot("{oops", None, None)


def test_evidence_is_registered_on_the_cli() -> None:
    from asxos.cli.main import app

    names = {g.name for g in app.registered_groups}
    assert "evidence" in names
