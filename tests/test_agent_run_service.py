"""Tests for asxos/domain/governance/agent_run_service.py — Phase 2b.

This is the one genuinely new mechanism in Phase 2 (the write side of
agent_runs/agent_evidence Phase 1 never built) — the bulk of new test
surface for this phase lives here.

Mocks asyncpg connections; no real DB required.
asyncio_mode = "auto" in pyproject.toml — no @pytest.mark.asyncio needed.
"""
from __future__ import annotations

import json
from contextlib import asynccontextmanager
from datetime import UTC, datetime

import pydantic
import pytest

from asxos.domain.governance import agent_run_service as svc
from asxos.domain.governance.agent_run_service import (
    _canonical_json,
    _resolve_evidence_citations,
    _snapshot_hash,
)


class _FakeConn:
    """A connection stub that actually tracks agent_evidence inserts, so the
    tier round-trip check (fetch()) sees real data — the simple sequential
    _make_conn() pattern used elsewhere in this suite can't express this
    two-step insert-then-read-back shape."""

    def __init__(self) -> None:
        self._next_evidence_id = 1
        self.evidence_rows: dict[int, dict] = {}
        self.run_insert_args: tuple | None = None

    @asynccontextmanager
    async def _tx(self):
        yield

    def transaction(self):
        return self._tx()

    async def fetchrow(self, query: str, *args):
        if "INSERT INTO agent_evidence" in query:
            eid = self._next_evidence_id
            self._next_evidence_id += 1
            self.evidence_rows[eid] = {"tier": args[2]}
            return {"evidence_id": eid}
        if "INSERT INTO agent_runs" in query:
            self.run_insert_args = args
            return {"run_id": 42}
        raise AssertionError(f"unexpected fetchrow: {query}")

    async def fetch(self, query: str, *args):
        if "SELECT evidence_id, tier FROM agent_evidence" in query:
            ids = args[0]
            return [
                {"evidence_id": i, "tier": self.evidence_rows[i]["tier"]}
                for i in ids
                if i in self.evidence_rows
            ]
        raise AssertionError(f"unexpected fetch: {query}")


_MACRO_PROPOSAL = {
    "title": "Risk-off regime persists",
    "thesis_text": "Elevated vol and soft iron ore point to a defensive tilt.",
    "regime_quadrant": "falling_growth_falling_inflation",
    "horizon_months": 6,
    "catalyst": "RBA pause",
    "falsifier": "AVIX below 15 for 5 sessions",
    "data_signals": ["avix", "iron_ore_62fe"],
    "evidence_citation_ids": ["local:0", "local:1"],
}

_EVIDENCE = [
    {
        "claim": "AVIX at 22, up 18% over 5 days",
        "tier": "verified",
        "source_type": "db_query",
        "source_table": "market_context_current",
        "snapshot_data": {"avix": 22, "avix_5d_change_pct": 18.0},
    },
    {
        "claim": "Iron ore soft, weighing on Materials",
        "tier": "inferred",
        "source_type": "db_query",
        "source_table": "market_context_current",
        "snapshot_data": {"iron_ore_62fe": 98},
    },
]


# ---------------------------------------------------------------------------
# Pure helper functions
# ---------------------------------------------------------------------------

def test_canonical_json_stable_across_key_order() -> None:
    assert _canonical_json({"b": 1, "a": 2}) == _canonical_json({"a": 2, "b": 1})


def test_snapshot_hash_format() -> None:
    h = _snapshot_hash({"avix": 22})
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)


def test_snapshot_hash_deterministic() -> None:
    assert _snapshot_hash({"a": 1, "b": 2}) == _snapshot_hash({"b": 2, "a": 1})


def test_resolve_evidence_citations_mixes_local_and_preexisting() -> None:
    resolved = _resolve_evidence_citations(["local:0", 999, "local:1"], {0: 10, 1: 11})
    assert resolved == [10, 999, 11]


def test_resolve_evidence_citations_unknown_local_raises() -> None:
    with pytest.raises(ValueError, match="local:5"):
        _resolve_evidence_citations(["local:5"], {0: 10})


def test_resolve_evidence_citations_malformed_type_raises() -> None:
    with pytest.raises(ValueError, match="int or a 'local:N'"):
        _resolve_evidence_citations([3.5], {})


# ---------------------------------------------------------------------------
# log_agent_run — validation guards
# ---------------------------------------------------------------------------

async def test_unknown_agent_name_raises() -> None:
    conn = _FakeConn()
    with pytest.raises(ValueError, match="Unknown agent_name"):
        await svc.log_agent_run(
            conn, "not-a-real-agent",
            subject=None, summary="x", object_type=None,
            proposal_raw=None, evidence_raw=None,
        )


async def test_object_type_without_proposal_raises() -> None:
    conn = _FakeConn()
    with pytest.raises(ValueError, match="must be given together"):
        await svc.log_agent_run(
            conn, "macro-economist",
            subject=None, summary="x", object_type="macro_thesis",
            proposal_raw=None, evidence_raw=None,
        )


async def test_proposal_without_object_type_raises() -> None:
    conn = _FakeConn()
    with pytest.raises(ValueError, match="must be given together"):
        await svc.log_agent_run(
            conn, "macro-economist",
            subject=None, summary="x", object_type=None,
            proposal_raw="{}", evidence_raw=None,
        )


async def test_object_type_thesis_raises_documented_gap() -> None:
    conn = _FakeConn()
    with pytest.raises(ValueError, match="no Pydantic schema"):
        await svc.log_agent_run(
            conn, "macro-economist",
            subject=None, summary="x", object_type="thesis",
            proposal_raw="{}", evidence_raw=None,
        )


async def test_unknown_object_type_raises() -> None:
    conn = _FakeConn()
    with pytest.raises(ValueError, match="Unknown object_type"):
        await svc.log_agent_run(
            conn, "macro-economist",
            subject=None, summary="x", object_type="not_a_real_type",
            proposal_raw="{}", evidence_raw=None,
        )


async def test_empty_summary_raises() -> None:
    conn = _FakeConn()
    with pytest.raises(ValueError, match="summary is required"):
        await svc.log_agent_run(
            conn, "macro-economist",
            subject=None, summary="   ", object_type=None,
            proposal_raw=None, evidence_raw=None,
        )


# ---------------------------------------------------------------------------
# Evidence claim validation
# ---------------------------------------------------------------------------

async def test_evidence_claim_missing_tier_raises() -> None:
    conn = _FakeConn()
    bad_evidence = json.dumps([{"claim": "x", "snapshot_data": {}}])
    with pytest.raises(ValueError, match="must be one of"):
        await svc.log_agent_run(
            conn, "macro-economist",
            subject=None, summary="x", object_type=None,
            proposal_raw=None, evidence_raw=bad_evidence,
        )


async def test_evidence_claim_empty_claim_text_raises() -> None:
    conn = _FakeConn()
    bad_evidence = json.dumps([{"claim": "", "tier": "verified", "snapshot_data": {"a": 1}}])
    with pytest.raises(ValueError, match="non-empty 'claim'"):
        await svc.log_agent_run(
            conn, "macro-economist",
            subject=None, summary="x", object_type=None,
            proposal_raw=None, evidence_raw=bad_evidence,
        )


async def test_evidence_claim_non_speculative_without_snapshot_raises() -> None:
    conn = _FakeConn()
    bad_evidence = json.dumps([{"claim": "x", "tier": "verified"}])
    with pytest.raises(ValueError, match="no snapshot_data"):
        await svc.log_agent_run(
            conn, "macro-economist",
            subject=None, summary="x", object_type=None,
            proposal_raw=None, evidence_raw=bad_evidence,
        )


async def test_speculative_claim_without_snapshot_data_is_allowed() -> None:
    conn = _FakeConn()
    evidence = json.dumps([{"claim": "gut feel", "tier": "speculative"}])
    run_id = await svc.log_agent_run(
        conn, "macro-economist",
        subject=None, summary="x", object_type=None,
        proposal_raw=None, evidence_raw=evidence,
    )
    assert run_id == 42
    assert conn.run_insert_args[3] == 1  # claim_count
    assert conn.run_insert_args[6] == 1  # speculative_count


# ---------------------------------------------------------------------------
# Full evidence + proposal happy path
# ---------------------------------------------------------------------------

async def test_happy_path_logs_evidence_and_proposal() -> None:
    conn = _FakeConn()
    run_id = await svc.log_agent_run(
        conn, "macro-economist",
        subject=None,
        summary="Proposed 1 macro thesis for the current regime.",
        object_type="macro_thesis",
        proposal_raw=json.dumps(_MACRO_PROPOSAL),
        evidence_raw=json.dumps(_EVIDENCE),
    )
    assert run_id == 42
    assert len(conn.evidence_rows) == 2

    args = conn.run_insert_args
    assert args[0] == "macro-economist"
    assert args[3] == 2  # claim_count
    assert args[4] == 1  # verified_count
    assert args[5] == 1  # inferred_count
    assert args[6] == 0  # speculative_count
    assert args[7] == "macro_thesis"
    proposed_object = json.loads(args[8])
    assert proposed_object["evidence_citation_ids"] == [1, 2]
    assert proposed_object["title"] == _MACRO_PROPOSAL["title"]


async def test_proposal_citing_preexisting_bare_int_alongside_local() -> None:
    """A proposal can cite a fresh local: claim AND a pre-existing
    evidence_id from an earlier run in the same evidence_citation_ids list."""
    conn = _FakeConn()
    conn.evidence_rows[500] = {"tier": "verified"}  # pre-existing row

    proposal = dict(_MACRO_PROPOSAL, evidence_citation_ids=["local:0", 500])
    run_id = await svc.log_agent_run(
        conn, "macro-economist",
        subject=None, summary="x", object_type="macro_thesis",
        proposal_raw=json.dumps(proposal),
        evidence_raw=json.dumps([_EVIDENCE[0]]),
    )
    assert run_id == 42
    proposed_object = json.loads(conn.run_insert_args[8])
    assert proposed_object["evidence_citation_ids"] == [1, 500]


async def test_speculative_tier_citation_raises() -> None:
    conn = _FakeConn()
    evidence = [dict(_EVIDENCE[0], tier="speculative", snapshot_data=None)]
    proposal = dict(_MACRO_PROPOSAL, evidence_citation_ids=["local:0"])
    with pytest.raises(ValueError, match="speculative"):
        await svc.log_agent_run(
            conn, "macro-economist",
            subject=None, summary="x", object_type="macro_thesis",
            proposal_raw=json.dumps(proposal),
            evidence_raw=json.dumps(evidence),
        )


async def test_citation_to_nonexistent_evidence_id_raises() -> None:
    conn = _FakeConn()
    proposal = dict(_MACRO_PROPOSAL, evidence_citation_ids=[99999])
    with pytest.raises(ValueError, match="does not exist"):
        await svc.log_agent_run(
            conn, "macro-economist",
            subject=None, summary="x", object_type="macro_thesis",
            proposal_raw=json.dumps(proposal), evidence_raw=None,
        )


async def test_proposal_missing_required_field_raises_pydantic_error() -> None:
    conn = _FakeConn()
    proposal = dict(_MACRO_PROPOSAL)
    del proposal["catalyst"]
    with pytest.raises(pydantic.ValidationError):
        await svc.log_agent_run(
            conn, "macro-economist",
            subject=None, summary="x", object_type="macro_thesis",
            proposal_raw=json.dumps(proposal),
            evidence_raw=json.dumps(_EVIDENCE),
        )


async def test_source_as_of_iso_string_is_bound_as_datetime() -> None:
    """The agent output contract (.claude/agents/macro-economist.md) emits
    source_as_of as an ISO-8601 JSON string, but asyncpg's TIMESTAMPTZ codec
    accepts only datetime objects — a raw str bind raises at execute time
    against a real connection, invisibly to mocked tests (the same failure
    class as the transition-order incident in transitions.py). Pin that the
    string is parsed to an aware datetime before binding."""
    evidence = [dict(_EVIDENCE[0], source_as_of="2026-06-29T00:00:00+00:00")]
    captured: dict[str, object] = {}

    class _CapturingConn(_FakeConn):
        async def fetchrow(self, query: str, *args):
            if "INSERT INTO agent_evidence" in query:
                captured["source_as_of"] = args[5]
            return await super().fetchrow(query, *args)

    await svc.log_agent_run(
        _CapturingConn(), "macro-economist",
        subject=None, summary="x", object_type=None,
        proposal_raw=None, evidence_raw=json.dumps(evidence),
    )
    assert captured["source_as_of"] == datetime(2026, 6, 29, tzinfo=UTC)


async def test_source_as_of_malformed_string_raises_with_position() -> None:
    evidence = [dict(_EVIDENCE[0], source_as_of="yesterday-ish")]
    with pytest.raises(ValueError, match=r"position 0 .* non-ISO-8601 source_as_of"):
        await svc.log_agent_run(
            _FakeConn(), "macro-economist",
            subject=None, summary="x", object_type=None,
            proposal_raw=None, evidence_raw=json.dumps(evidence),
        )


async def test_decimal_in_snapshot_data_survives_high_precision_round_trip() -> None:
    """log_agent_run() parses evidence_raw with json.loads(parse_float=Decimal)
    (schemas.py's documented hazard) — confirm a JSON number literal with
    more significant digits than a float can exactly hold (float64 holds
    ~15-17) round-trips losslessly through to the stored snapshot_data JSON,
    not silently truncated by an intermediate float parse."""
    high_precision = "0.123456789012345678"  # 18 significant digits
    # Raw JSON with a bare number literal (not a quoted string) — this is
    # exactly the case a bare json.loads() would coerce to float and lose
    # precision on, before Pydantic/anything else ever sees it.
    evidence_raw = (
        '[{"claim": "precise avix reading", "tier": "verified", '
        f'"snapshot_data": {{"value": {high_precision}}}}}]'
    )
    inserted_snapshot: dict[str, object] = {}

    class _CapturingConn(_FakeConn):
        async def fetchrow(self, query: str, *args):
            if "INSERT INTO agent_evidence" in query:
                inserted_snapshot["raw"] = args[7]
            return await super().fetchrow(query, *args)

    conn = _CapturingConn()
    await svc.log_agent_run(
        conn, "macro-economist",
        subject=None, summary="x", object_type=None,
        proposal_raw=None, evidence_raw=evidence_raw,
    )
    stored = json.loads(inserted_snapshot["raw"])
    assert stored["value"] == high_precision, (
        f"expected exact high-precision string {high_precision!r}, got {stored['value']!r} "
        "— precision was lost somewhere in the pipeline (likely a bare json.loads() "
        "coercing the literal to float before Decimal ever saw it)"
    )
