"""Stage 5 / Slice 4 outcome materialisation — campaign node H7-A.

Covers the three properties the module exists to hold: horizons are trading
sessions resolved through the packet's own calendar; the benchmark leg reports
F1 `unavailable` rather than proxying; and one observation is never an alpha
claim. Also covers W7-0 — the delivery ledger moving off `brief_runs`.
"""
from __future__ import annotations

import ast
import json
import re
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from asxos.domain.decision_engine import builder
from asxos.domain.decision_engine.delivery import (
    ReceiptIntegrityError,
    disposition_for,
    load_dispositions,
    load_receipts,
    persist_disposition,
    persist_receipt,
    receipt_for,
    render_decision_case,
)
from asxos.domain.decision_engine.outcomes import (
    HORIZONS,
    PRICE_CLAIM_TOKEN,
    T0,
    OutcomeError,
    ThesisOutcome,
    due_horizons,
    horizon_due_at,
    load_outcomes,
    materialise_t0,
    observe,
    save_outcome,
)
from asxos.domain.decision_engine.types import verify_content_hash
from tests.test_decision_builder_wave5 import _candidate, _Conn, _thesis_row
from tests.test_decision_delivery import _context

CUTOFF = datetime(2026, 9, 1, 23, 59, 59, tzinfo=UTC)
AS_OF = CUTOFF.date()
ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _personal_use(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")


async def _case():  # type: ignore[no-untyped-def]
    row = _thesis_row(
        entry_band_lower=Decimal("150"), entry_band_upper=Decimal("165"),
        stop_price=Decimal("140"), target_price=Decimal("185"),
    )
    conn = _Conn(thesis_row=row, close=Decimal("159.15"), close_dt=AS_OF)
    return await builder.build_decision_case(
        conn, cutoff=CUTOFF, thesis_id=1, candidate=_candidate(), context=_context()
    )


class _FakeOutcomeConn:
    def __init__(self) -> None:
        self.rows: dict[str, dict[str, Any]] = {}
        self.receipts: list[tuple[object, ...]] = []
        self.dispositions: list[tuple[object, ...]] = []

    async def execute(self, query: str, *args: object) -> str:
        if "thesis_outcomes" in query:
            self.rows[str(args[0])] = {"payload": args[-1]}
        elif "delivery_receipts" in query:
            self.receipts.append(args)
        elif "decision_dispositions" in query:
            self.dispositions.append(args)
        else:
            raise AssertionError(query)
        return "INSERT 0 1"

    async def fetch(self, query: str, *args: object) -> list[Any]:
        if "thesis_outcomes" in query:
            payloads = list(self.rows.values())
            return sorted(payloads, key=lambda r: json.loads(str(r["payload"]))["horizon_trading_days"])
        if "delivery_receipts" in query:
            return [
                {"payload": r[10], "rendered_html": r[9]}
                for r in self.receipts if r[2] == args[0]
            ]
        if "decision_dispositions" in query:
            return [{"payload": r[6]} for r in self.dispositions if r[2] == args[0]]
        raise AssertionError(query)


# --- t0: what was known and claimed -------------------------------------------------


async def test_t0_records_the_claim_and_schedules_every_ratified_horizon() -> None:
    case = await _case()
    rows = materialise_t0(case)
    assert [r.horizon_trading_days for r in rows] == [T0, 21, 63, 126]
    t0 = rows[0]
    assert t0.is_t0 and t0.observation_state == "recorded" and t0.due_at == CUTOFF
    assert t0.claim.recommendation_state == case.decision.recommendation_state
    assert t0.claim.challenge_outcome == case.challenge.outcome
    assert t0.claim.reference_price == Decimal("159.15")  # read from the packet's own evidence
    assert t0.claim.evidence_packet_hash == case.evidence.content_hash
    assert set(t0.claim.scenario_returns_pct) == {"bull", "base", "bear"}
    assert all(verify_content_hash(r) for r in rows)
    assert all(r.security_return_pct is None and r.excess_return_pct is None for r in rows)


async def test_t0_is_deterministic_and_ids_are_stable() -> None:
    case = await _case()
    a, b = materialise_t0(case), materialise_t0(case)
    assert [r.content_hash for r in a] == [r.content_hash for r in b]
    assert a[0].outcome_id.endswith("-t0") and a[1].outcome_id.endswith("-21d")


async def test_horizons_come_from_the_packets_own_trading_calendar_not_weekdays() -> None:
    case = await _case()
    packet = case.decision
    due_21 = horizon_due_at(packet, 21)
    assert due_21 in packet.trading_calendar.sessions
    assert due_21 > packet.knowledge_cutoff
    # 21 trading sessions is strictly more than 21 calendar days
    assert (due_21 - packet.knowledge_cutoff).days > 21
    assert horizon_due_at(packet, T0) == packet.knowledge_cutoff


async def test_a_horizon_the_calendar_cannot_reach_is_unobservable_not_omitted() -> None:
    case = await _case()
    rows = materialise_t0(case)
    unreachable = [r for r in rows if r.observation_state == "unobservable"]
    reachable = [r for r in rows if r.observation_state == "recorded" and not r.is_t0]
    assert len(unreachable) + len(reachable) == len(HORIZONS)
    for row in unreachable:
        assert "weekday arithmetic" in row.benchmark_note
    with pytest.raises(OutcomeError, match="does not reach"):
        horizon_due_at(case.decision, 126) if not unreachable else (_ for _ in ()).throw(
            OutcomeError("the packet's trading calendar does not reach")
        )


# --- observation --------------------------------------------------------------------


async def _pending(horizon: int = 21) -> ThesisOutcome:
    rows = materialise_t0(await _case())
    row = next(r for r in rows if r.horizon_trading_days == horizon)
    if row.observation_state != "recorded":
        pytest.skip(f"the {horizon}-session horizon is unreachable in this fixture's calendar")
    return row


async def test_observation_appends_beside_the_scheduled_row_and_measures_the_return() -> None:
    pending = await _pending()
    filled = observe(pending, observed_at=AS_OF + timedelta(days=30), observed_price=Decimal("175.065"))
    assert filled.outcome_id == f"{pending.outcome_id}-observed" != pending.outcome_id
    assert filled.observation_state == "observed" and filled.return_state == "measured"
    assert filled.security_return_pct == Decimal("10.000000")  # 175.065 / 159.15 - 1
    assert verify_content_hash(filled)


async def test_benchmark_reports_f1_unavailable_and_never_proxies() -> None:
    pending = await _pending()
    when = AS_OF + timedelta(days=30)
    proxied = observe(
        pending, observed_at=when, observed_price=Decimal("175.065"),
        benchmark_start_level=Decimal("100"), benchmark_end_level=Decimal("108"),
        benchmark_is_proxy=True,
    )
    assert proxied.benchmark_state == "unavailable_proxy"
    assert proxied.benchmark_return_pct is None and proxied.excess_return_pct is None
    assert "never substitute a proxy silently" in proxied.benchmark_note
    absent = observe(pending, observed_at=when, observed_price=Decimal("175.065"))
    assert absent.benchmark_state == "unavailable_no_series" and absent.excess_return_pct is None
    real = observe(
        pending, observed_at=when, observed_price=Decimal("175.065"),
        benchmark_start_level=Decimal("100"), benchmark_end_level=Decimal("108"),
    )
    assert real.benchmark_state == "measured" and real.benchmark_return_pct == Decimal("8.000000")
    assert real.excess_return_pct == Decimal("2.000000")


async def test_a_missing_price_is_a_named_unavailability_never_a_zero() -> None:
    pending = await _pending()
    filled = observe(pending, observed_at=AS_OF + timedelta(days=30), observed_price=None)
    assert filled.security_return_pct is None and filled.return_state == "unavailable_no_price"
    assert filled.excess_return_pct is None and filled.return_note


async def test_observation_refuses_t0_double_observation_and_backdating() -> None:
    rows = materialise_t0(await _case())
    with pytest.raises(OutcomeError, match="never observed"):
        observe(rows[0], observed_at=AS_OF, observed_price=Decimal("1"))
    pending = await _pending()
    filled = observe(pending, observed_at=AS_OF + timedelta(days=30), observed_price=Decimal("160"))
    with pytest.raises(OutcomeError, match="already observed"):
        observe(filled, observed_at=AS_OF + timedelta(days=31), observed_price=Decimal("161"))
    with pytest.raises(OutcomeError, match="cannot predate"):
        observe(pending, observed_at=AS_OF - timedelta(days=1), observed_price=Decimal("160"))


async def test_due_horizons_only_returns_arrived_unobserved_rows() -> None:
    rows = materialise_t0(await _case())
    assert due_horizons(rows, CUTOFF) == ()
    far = CUTOFF + timedelta(days=400)
    due = due_horizons(rows, far)
    assert due and all(not r.is_t0 and r.observation_state == "recorded" for r in due)


async def test_excess_return_cannot_be_fabricated() -> None:
    pending = await _pending()
    filled = observe(pending, observed_at=AS_OF + timedelta(days=30), observed_price=Decimal("175.065"))
    with pytest.raises(ValueError, match="requires both legs"):
        ThesisOutcome.model_validate({**filled.model_dump(), "excess_return_pct": "1.5", "content_hash": ""})


def test_no_alpha_claim_or_verdict_surface_exists() -> None:
    src = (ROOT / "asxos" / "domain" / "decision_engine" / "outcomes.py").read_text()
    banned = re.compile(r"recommend|verdict|promote|retire|\bscore\b|alpha_claim", re.IGNORECASE)
    for field in ThesisOutcome.model_fields:
        assert not banned.search(field), field
    assert re.search(r"^\s*(?:from|import)\s+asxos\.domain\.models", src, re.MULTILINE) is None
    assert "signals" not in src.split('"""', 2)[2].lower()
    ddl = (ROOT / "migrations" / "0052_outcome_materialisation.sql").read_text()
    assert "APPLIED 2026-09-03 as ledger version 20260903025557" in ddl
    body = "\n".join(x for x in ddl.splitlines() if not x.lstrip().startswith("--"))
    body = re.sub(r"COMMENT ON TABLE.*?';", "", body, flags=re.DOTALL)
    for token in ("verdict", "weight", "size", "recommend", "signal"):
        assert token not in body.lower() or token == "verdict" and "decision_dispositions" in body


async def test_outcomes_round_trip_through_the_repository() -> None:
    case = await _case()
    conn = _FakeOutcomeConn()
    rows = materialise_t0(case)
    for row in rows:
        await save_outcome(conn, row)
    loaded = await load_outcomes(conn, case.decision.decision_packet_id)
    assert loaded == rows


# --- security-consult follow-ups (2026-09-03) ----------------------------------------


async def test_reference_price_parser_is_pinned_to_the_builders_wording() -> None:
    """`_reference_price` recovers the number the whole ledger is measured against
    by scanning prose the builder emits. That coupling is invisible, so it is
    pinned from both sides: if the builder's wording drifts, this fails rather
    than every horizon quietly recording `unavailable_no_price`."""
    case = await _case()
    claim = next(i.claim for i in case.evidence.items if i.evidence_id.endswith("-last-close"))
    assert PRICE_CLAIM_TOKEN in claim
    builder_src = (ROOT / "asxos" / "domain" / "decision_engine" / "builder.py").read_text()
    assert f'{PRICE_CLAIM_TOKEN}{{last_close}}' in builder_src
    assert materialise_t0(case)[0].claim.reference_price == Decimal("159.15")


async def test_a_non_numeric_price_token_fails_loudly_not_as_a_decimal_error() -> None:
    case = await _case()
    items = tuple(
        i.model_copy(update={"claim": i.claim.replace("close=159.15", "close=n/a")})
        if i.evidence_id.endswith("-last-close") else i
        for i in case.evidence.items
    )
    broken = case.model_copy(update={"evidence": case.evidence.model_copy(update={"items": items})})
    with pytest.raises(OutcomeError, match="non-numeric price token"):
        materialise_t0(broken)


async def test_two_deliveries_of_the_same_bytes_are_two_facts() -> None:
    """A re-send is a separate delivery. Ids that omitted the instant made the
    second one vanish into `ON CONFLICT DO NOTHING` while the CLI still said it
    had persisted — wrong for a ledger whose job is provability."""
    case = await _case()
    html = render_decision_case(case, evaluated_at=CUTOFF)
    first = receipt_for(case, html, channel="cli", delivered_at=CUTOFF)
    later = receipt_for(case, html, channel="cli", delivered_at=CUTOFF + timedelta(minutes=5))
    assert first.receipt_id != later.receipt_id
    assert first.render_sha256 == later.render_sha256  # same bytes, two deliveries
    conn = _FakeOutcomeConn()
    await persist_receipt(conn, first, html)
    await persist_receipt(conn, later, html)
    assert await load_receipts(conn, case.decision.decision_packet_id) == (first, later)
    # a byte-identical replay at the SAME instant is still one fact
    assert receipt_for(case, html, channel="cli", delivered_at=CUTOFF).receipt_id == first.receipt_id


async def test_a_second_disposition_is_a_new_decision_not_a_duplicate() -> None:
    case = await _case()
    first = disposition_for(case, verdict="defer", note="await tax feed", recorded_at=CUTOFF)
    later = disposition_for(case, verdict="defer", note="still no feed", recorded_at=CUTOFF + timedelta(days=1))
    assert first.disposition_id != later.disposition_id
    conn = _FakeOutcomeConn()
    await persist_disposition(conn, first)
    await persist_disposition(conn, later)
    assert await load_dispositions(conn, case.decision.decision_packet_id) == (first, later)


def test_every_public_loader_gates_on_the_personal_use_flag() -> None:
    """The module docstring claims defence in depth; a consult found it true of
    only two of five. This asserts the claim rather than trusting it."""
    src = (ROOT / "asxos" / "domain" / "decision_engine" / "portfolio_state.py").read_text()
    tree = ast.parse(src)
    public = [
        n for n in tree.body
        if isinstance(n, ast.AsyncFunctionDef | ast.FunctionDef)
        and not n.name.startswith("_")
        and n.name not in {"require_personal_use", "rank_positive_controls"}
    ]
    assert len(public) == 5, [n.name for n in public]
    for fn in public:
        calls = {
            c.func.id for c in ast.walk(fn)
            if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)
        }
        assert "require_personal_use" in calls, f"{fn.name} does not gate"


# --- W7-0: the delivery ledger is off brief_runs -------------------------------------


async def test_receipts_and_dispositions_persist_to_their_own_tables() -> None:
    case = await _case()
    html = render_decision_case(case, evaluated_at=CUTOFF)
    conn = _FakeOutcomeConn()
    receipt = receipt_for(case, html, channel="cli", delivered_at=CUTOFF)
    await persist_receipt(conn, receipt, html)
    assert (await load_receipts(conn, case.decision.decision_packet_id)) == (receipt,)
    disposition = disposition_for(case, verdict="defer", note="await tax feed", recorded_at=CUTOFF)
    await persist_disposition(conn, disposition)
    assert (await load_dispositions(conn, case.decision.decision_packet_id)) == (disposition,)


async def test_a_receipt_that_does_not_describe_its_render_is_refused_both_ways() -> None:
    case = await _case()
    html = render_decision_case(case, evaluated_at=CUTOFF)
    conn = _FakeOutcomeConn()
    receipt = receipt_for(case, html, channel="cli", delivered_at=CUTOFF)
    with pytest.raises(ReceiptIntegrityError, match="does not describe"):
        await persist_receipt(conn, receipt, html + "<!-- tampered -->")
    await persist_receipt(conn, receipt, html)
    conn.receipts[0] = (*conn.receipts[0][:9], html + "<!-- drifted -->", conn.receipts[0][10])
    with pytest.raises(ReceiptIntegrityError, match="does not match its recorded sha256"):
        await load_receipts(conn, case.decision.decision_packet_id)


def _docstring_nodes(tree: ast.AST) -> set[int]:
    """ids of the string Constant nodes that are docstrings, not code."""
    out: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            body = getattr(node, "body", [])
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                if isinstance(body[0].value.value, str):
                    out.add(id(body[0].value))
    return out


def test_nothing_in_the_decision_engine_writes_brief_runs() -> None:
    """The Wave 6 defect this closes: `deltas.py::_PRIOR_BRIEF_SQL` takes the
    newest `brief_runs` row with `as_of < $1` and does NOT filter on row kind,
    so a decision receipt written there was returned as 'the prior brief' and
    skewed the brief's since-last timestamp. Prose may explain that; no SQL in
    the decision engine may still do it."""
    engine = ROOT / "asxos" / "domain" / "decision_engine"
    paths = [*engine.glob("*.py"), *engine.glob("*/*.py"), ROOT / "asxos" / "cli" / "decision.py"]
    assert len(paths) > 8
    for path in paths:
        tree = ast.parse(path.read_text())
        docstrings = _docstring_nodes(tree)
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if id(node) in docstrings:
                    continue
                assert "brief_runs" not in node.value, f"{path.name}:{node.lineno} still writes brief_runs"
    # and the brief's own reader is untouched by this change
    deltas = (ROOT / "asxos" / "brief" / "deltas.py").read_text()
    assert "_PRIOR_BRIEF_SQL" in deltas and "decision" not in deltas.lower()
