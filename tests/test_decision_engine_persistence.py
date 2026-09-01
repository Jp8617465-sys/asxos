"""Slice 1 (D5) persistence + builder tests — ADR SS10.5, verbatim from the
mission plan (`docs/proposals/architecture-decision-record.md` SS6/SS10.5).

Nothing here touches a live database (migration `0048_decision_packets.sql`
was applied to production 2026-09-01 as `20260901062502`, but these tests
stay DB-independent); per `.claude/rules/api-conventions.md`'s testing
convention, every test mocks `asxos.domain.decision_engine.repository`'s
connection seam with a synthetic asyncpg-`Record`-shaped fake rather than
`asxos.db.acquire()` itself, and the builder tests mock the DB connection
the builder is handed directly. Rule #11: nothing here reads `signals`,
`signal_outcomes`, or any Model A surface.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import pytest
from pydantic import ValidationError

from asxos.domain.decision_engine import builder, repository
from asxos.domain.decision_engine.demo import build_demo_brief
from asxos.domain.decision_engine.types import (
    NON_ACTION_STATES,
    ChallengeFinding,
    ChallengeResult,
    DecisionCase,
    DecisionPacket,
    EvidenceItem,
    EvidencePacket,
    verify_content_hash,
)

# asyncio_mode = "auto" (pyproject.toml) — every `async def test_*` below is
# collected as an asyncio test with no per-test marker needed.


# ---------------------------------------------------------------------------
# Shared fakes / helpers
# ---------------------------------------------------------------------------


class _FakeTransaction:
    async def __aenter__(self) -> _FakeTransaction:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        return None


_INSERT_TABLE_RE = re.compile(r"INSERT INTO (\w+)")
_SELECT_TABLE_RE = re.compile(r"FROM (\w+) WHERE")


class _FakeRepoConn:
    """Generic fake satisfying `repository.RepositoryConn`.

    Captures every INSERT by (table, primary key) and serves it back on the
    matching `SELECT payload FROM <table> WHERE <id_column> = $1` — this is
    "the mocked connection captures the inserted payload and returns it on
    load" the mission plan asks for, implemented once for all five tables
    rather than five bespoke fakes.
    """

    def __init__(self) -> None:
        self.executed: list[tuple[str, tuple[object, ...]]] = []
        self.tables: dict[str, dict[object, dict[str, object]]] = {}

    def transaction(self) -> _FakeTransaction:
        return _FakeTransaction()

    async def execute(self, query: str, *args: object) -> str:
        self.executed.append((query, args))
        match = _INSERT_TABLE_RE.search(query)
        assert match, f"could not parse INSERT table from: {query!r}"
        table = match.group(1)
        primary_key = args[0]
        payload_raw = args[-1]
        payload = json.loads(payload_raw) if isinstance(payload_raw, str) else payload_raw
        self.tables.setdefault(table, {})[primary_key] = {"payload": payload}
        return "INSERT 0 1"

    async def fetchrow(self, query: str, *args: object) -> Mapping[str, object] | None:
        self.executed.append((query, args))
        match = _SELECT_TABLE_RE.search(query)
        assert match, f"could not parse SELECT table from: {query!r}"
        table = match.group(1)
        primary_key = args[0]
        return self.tables.get(table, {}).get(primary_key)


def _strip_hash(value: Any) -> Any:
    """Recursively drop every `content_hash` key so a mutated payload
    re-seals to a fresh, internally-consistent digest instead of failing on
    a stale one — the same technique
    `tests/test_decision_engine_prototype.py::_without_hashes` already uses."""
    if isinstance(value, dict):
        return {key: _strip_hash(item) for key, item in value.items() if key != "content_hash"}
    if isinstance(value, list | tuple):
        return type(value)(_strip_hash(item) for item in value)
    return value


def _superseding_case(case: DecisionCase) -> DecisionCase:
    """Build a second `DecisionCase` reusing every upstream artifact from
    `case` unchanged, with a fresh `DecisionPacket` that supersedes it."""
    decision_payload = _strip_hash(case.decision.model_dump(mode="python"))
    old_id = case.decision.decision_packet_id
    decision_payload["decision_packet_id"] = f"{old_id}-v2"
    decision_payload["supersedes_packet_id"] = old_id
    new_decision = DecisionPacket.model_validate(decision_payload)
    return DecisionCase(
        case_id=f"{case.case_id}-v2",
        label=case.label,
        changed_since_prior="Supersedes the prior packet for test coverage.",
        evidence=case.evidence,
        thesis=case.thesis,
        challenge=case.challenge,
        portfolio=case.portfolio,
        decision=new_decision,
    )


# ---------------------------------------------------------------------------
# 1 + 2: round-trip fidelity and verify_content_hash after a DB round trip
# ---------------------------------------------------------------------------


async def test_save_then_load_round_trips_the_decision_packet_identically() -> None:
    case = build_demo_brief().cases[1]  # the abstain / negative-control case
    conn = _FakeRepoConn()

    await repository.save(case, conn=conn)
    loaded = await repository.load(case.decision.decision_packet_id, conn=conn)

    assert loaded == case.decision


async def test_verify_content_hash_is_true_after_a_db_round_trip() -> None:
    case = build_demo_brief().cases[0]  # the initiate / positive-control case
    conn = _FakeRepoConn()

    await repository.save(case, conn=conn)
    loaded = await repository.load(case.decision.decision_packet_id, conn=conn)

    assert verify_content_hash(loaded) is True


async def test_load_case_reconstructs_every_upstream_artifact() -> None:
    case = build_demo_brief().cases[1]
    conn = _FakeRepoConn()

    await repository.save(case, conn=conn)
    loaded_case = await repository.load_case(case.decision.decision_packet_id, conn=conn)

    assert loaded_case.evidence == case.evidence
    assert loaded_case.thesis == case.thesis
    assert loaded_case.challenge == case.challenge
    assert loaded_case.portfolio == case.portfolio
    assert loaded_case.decision == case.decision


async def test_load_raises_for_an_unknown_decision_packet_id() -> None:
    conn = _FakeRepoConn()
    with pytest.raises(repository.DecisionPacketNotFoundError):
        await repository.load("no-such-packet", conn=conn)


async def test_supersede_inserts_a_new_row_and_never_touches_the_old_one() -> None:
    case = build_demo_brief().cases[1]
    conn = _FakeRepoConn()
    await repository.save(case, conn=conn)
    old_payload_before = dict(conn.tables["decision_packets"][case.decision.decision_packet_id])

    new_case = _superseding_case(case)
    await repository.supersede(case.decision.decision_packet_id, new_case, conn=conn)

    # the old row is byte-for-byte unchanged (append-only, never UPDATEd).
    assert conn.tables["decision_packets"][case.decision.decision_packet_id] == old_payload_before
    new_row = conn.tables["decision_packets"][new_case.decision.decision_packet_id]
    assert new_row["payload"]["supersedes_packet_id"] == case.decision.decision_packet_id


async def test_supersede_rejects_a_mismatched_old_id() -> None:
    case = build_demo_brief().cases[1]
    new_case = _superseding_case(case)
    with pytest.raises(ValueError, match="supersedes_packet_id"):
        await repository.supersede("not-the-real-old-id", new_case, conn=_FakeRepoConn())


# ---------------------------------------------------------------------------
# 3: SS3.2 validators still raise (verbatim list from the mission plan)
# ---------------------------------------------------------------------------


def _decision_payload(case_index: int) -> dict[str, Any]:
    decision = build_demo_brief().cases[case_index].decision
    return _strip_hash(decision.model_dump(mode="python"))


def test_a_blocking_finding_with_outcome_pass_still_raises() -> None:
    with pytest.raises(ValidationError):
        ChallengeResult(
            challenge_result_id="chr-violation",
            thesis_version_id="thv-violation",
            evidence_packet_id="evp-violation",
            as_of=date(2026, 1, 1),
            knowledge_cutoff=datetime(2026, 1, 1, tzinfo=UTC),
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
            outcome="pass",
            strongest_bear_case="A blocking finding cannot coexist with a pass outcome.",
            findings=(
                ChallengeFinding(
                    severity="blocking",
                    finding="Sale eligibility is not established.",
                    required_response="Verify plan terms before authoring any rule.",
                    evidence_ids=("evidence-1",),
                ),
            ),
            independent_of_author=True,
        )


def test_as_of_mismatched_with_knowledge_cutoff_date_still_raises() -> None:
    with pytest.raises(ValidationError):
        EvidencePacket(
            evidence_packet_id="evp-violation",
            as_of=date(2026, 1, 2),  # deliberately one day off knowledge_cutoff's date
            knowledge_cutoff=datetime(2026, 1, 1, tzinfo=UTC),
            expires_at=datetime(2026, 1, 10, tzinfo=UTC),
            data_mode="real",
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
            items=(
                EvidenceItem(
                    evidence_id="e1",
                    evidence_type="market_fact",
                    title="t",
                    claim="c",
                    source_uri="asxos://x",
                    observed_at=date(2026, 1, 1),
                    known_at=datetime(2026, 1, 1, tzinfo=UTC),
                    evidence_tier="verified",
                    data_mode="real",
                ),
            ),
        )


def test_action_state_with_nonempty_missing_or_uncertain_inputs_still_raises() -> None:
    payload = _decision_payload(0)  # "initiate" — an ACTION_STATE
    assert payload["recommendation_state"] == "initiate"
    payload["missing_or_uncertain_inputs"] = ("Verified sale eligibility",)
    with pytest.raises(ValidationError):
        DecisionPacket.model_validate(payload)


def test_non_action_state_with_nonzero_size_range_maximum_still_raises() -> None:
    payload = _decision_payload(1)  # "abstain" — a NON_ACTION_STATE
    assert payload["recommendation_state"] == "abstain"
    payload["size_range"] = {"minimum_pct": Decimal("0"), "maximum_pct": Decimal("5")}
    with pytest.raises(ValidationError):
        DecisionPacket.model_validate(payload)


def test_action_state_with_non_pass_tax_readiness_still_raises() -> None:
    payload = _decision_payload(0)  # "initiate" — an ACTION_STATE
    assert payload["recommendation_state"] == "initiate"
    payload["tax_assessment_reference"]["readiness"] = "unknown"
    with pytest.raises(ValidationError):
        DecisionPacket.model_validate(payload)


def test_manifest_entry_matching_model_a_still_raises() -> None:
    payload = _decision_payload(0)
    payload["model_and_prompt_manifest"][0]["version"] = "model_a"
    with pytest.raises(ValidationError):
        DecisionPacket.model_validate(payload)


def test_manifest_entry_matching_v1_5_still_raises() -> None:
    payload = _decision_payload(0)
    payload["model_and_prompt_manifest"][0]["version"] = "v1_5"
    with pytest.raises(ValidationError):
        DecisionPacket.model_validate(payload)


# ---------------------------------------------------------------------------
# 4: one real thesis (CBA.AU) produces one real persisted packet
# ---------------------------------------------------------------------------


class _FakeBuilderConn:
    """Mocked-but-realistic DB for the builder: a `theses` row (thesis_id=1,
    CBA.AU), two yearly `rs_financial_statements` income rows, and the
    latest-period lookup query — nothing else. `fetch()` is never called by
    the builder (see module docstring), so it hard-fails if it is."""

    def __init__(
        self,
        *,
        thesis_row: Mapping[str, object],
        period_end: date,
        income_rows: dict[date, Mapping[str, object] | None],
    ) -> None:
        self._thesis_row = thesis_row
        self._period_end = period_end
        self._income_rows = income_rows

    async def fetchrow(self, query: str, *args: object) -> Mapping[str, object] | None:
        lowered = query.lower()
        if "from theses" in lowered:
            return self._thesis_row
        if "max(period_end)" in lowered:
            return {"period_end": self._period_end}
        if "from rs_financial_statements" in lowered:
            period_end = args[1]
            assert isinstance(period_end, date)
            return self._income_rows.get(period_end)
        raise AssertionError(f"unexpected fetchrow query: {query!r}")

    async def fetch(self, query: str, *args: object) -> Sequence[Mapping[str, object]]:
        raise AssertionError(f"unexpected fetch query: {query!r}")


def _cba_thesis_row(*, last_revisited_at: datetime) -> dict[str, object]:
    return {
        "thesis_id": 1,
        "symbol": "CBA.AU",
        "status": "watching",
        "thesis_text": (
            "CBA's deposit franchise and cost discipline support durable ROE even as "
            "net interest margin normalises; entry is conditional on the stated band."
        ),
        "entry_band_lower": Decimal("100.00"),
        "entry_band_upper": Decimal("105.00"),
        "stop_price": Decimal("90.00"),
        "target_price": Decimal("120.00"),
        "timeline_days": 365,
        "invalidation_conditions": json.dumps(
            [
                {
                    "condition": "Net interest margin compresses below 1.80% for two consecutive halves",
                    "status": "active",
                    "note": None,
                }
            ]
        ),
        "themes": ["banks"],
        "actual_entry_price": None,
        "actual_entry_at": None,
        "actual_exit_price": None,
        "actual_exit_at": None,
        "last_revisited_at": last_revisited_at,
        "revisit_due_at": last_revisited_at,
        "opened_at": last_revisited_at,
        "closed_at": None,
        "analyst_buy_count": None,
        "analyst_neutral_count": None,
        "analyst_sell_count": None,
        "analyst_consensus_target": None,
        "analyst_updated_at": None,
        "next_earnings_date": None,
        "earnings_notes": None,
        "conviction_level": None,
        "tax_notes": None,
        "governance_status": "approved",
        "report_sections": None,
    }


def _income_row(*, period_end: date, report_date: date) -> dict[str, object]:
    return {
        "symbol": "CBA.AU",
        "period_end": period_end,
        "period_type": "yearly",
        "statement_type": "income",
        "filing_date": report_date,
        "report_date": report_date,
        "currency": "AUD",
        "total_revenue": Decimal("28000000000"),
        "net_income": Decimal("10200000000"),
    }


async def test_builder_produces_one_real_honest_abstain_packet_for_cba() -> None:
    cutoff = datetime(2026, 8, 21, 23, 59, 59, tzinfo=UTC)
    last_revisited_at = datetime(2026, 8, 1, tzinfo=UTC)
    period_end = date(2025, 6, 30)
    prior_end = date(2024, 6, 30)

    conn = _FakeBuilderConn(
        thesis_row=_cba_thesis_row(last_revisited_at=last_revisited_at),
        period_end=period_end,
        income_rows={
            period_end: _income_row(period_end=period_end, report_date=date(2025, 8, 11)),
            prior_end: _income_row(period_end=prior_end, report_date=date(2024, 8, 12)),
        },
    )

    case = await builder.build_cba_decision_case(conn, cutoff=cutoff)

    assert case.decision.recommendation_state in NON_ACTION_STATES
    assert case.decision.tax_assessment_reference.readiness == "unknown"
    assert case.evidence.data_mode == "real"
    assert verify_content_hash(case.decision) is True


async def test_builder_persists_through_the_repository() -> None:
    """The honest-abstain case the builder produces round-trips through
    repository.save()/load() exactly like any other DecisionCase."""
    cutoff = datetime(2026, 8, 21, 23, 59, 59, tzinfo=UTC)
    last_revisited_at = datetime(2026, 8, 1, tzinfo=UTC)
    period_end = date(2025, 6, 30)

    conn = _FakeBuilderConn(
        thesis_row=_cba_thesis_row(last_revisited_at=last_revisited_at),
        period_end=period_end,
        income_rows={period_end: _income_row(period_end=period_end, report_date=date(2025, 8, 11))},
    )
    case = await builder.build_cba_decision_case(conn, cutoff=cutoff)

    repo_conn = _FakeRepoConn()
    await repository.save(case, conn=repo_conn)
    loaded = await repository.load(case.decision.decision_packet_id, conn=repo_conn)

    assert loaded == case.decision
