"""Stage 4 delivery chain — campaign node H6-A (target-architecture.md §15 Stage 4).

Exit gate: evidence, thesis, challenge, portfolio, packet, render, delivery and
disposition identities resolve; missing evidence forces abstention; renderers
contain no financial logic; no Model A input; the process is non-executing.
"""
from __future__ import annotations

import json
import os
import re
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from asxos.cli import decision as decision_cli
from asxos.domain.decision_engine import builder, repository
from asxos.domain.decision_engine.builder import ChallengeContext
from asxos.domain.decision_engine.challenge import PortfolioState
from asxos.domain.decision_engine.delivery import (
    Disposition,
    PaperIntent,
    disposition_for,
    load_receipts,
    paper_intent_for,
    persist_receipt,
    receipt_for,
    render_decision_case,
    render_sha256,
)
from asxos.domain.decision_engine.portfolio_state import (
    NEGATIVE_CONTROLS,
    PersonalUseRequired,
    load_annualised_vol,
    load_portfolio_state,
    load_sizing_policy,
    rank_positive_controls,
    select_positive_control,
)
from asxos.domain.decision_engine.sizer import SizingPolicy, VolInput
from asxos.domain.decision_engine.types import EvidenceItem, verify_content_hash
from asxos.domain.themes.candidates.builder import cutoff_instant
from asxos.domain.themes.candidates.types import CandidateSnapshot
from tests.test_decision_builder_wave5 import _candidate as _cba_candidate
from tests.test_decision_builder_wave5 import _Conn, _thesis_row
from tests.test_decision_engine_persistence import _FakeRepoConn

CUTOFF = datetime(2026, 9, 1, 23, 59, 59, tzinfo=UTC)
AS_OF = CUTOFF.date()
ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _personal_use(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")


def _context() -> ChallengeContext:
    return ChallengeContext(
        portfolio_state=PortfolioState(
            capital_aud=Decimal("500000"), cash_pct=Decimal("20"), gross_exposure_pct=Decimal("80"),
            borrowing_aud=Decimal("0"), sector_weights_pct={"Financials": Decimal("22")},
            position_weights_pct={}, evidence_id="cba-thesis-narrative",
        ),
        sizing=SizingPolicy(capital_aud=Decimal("500000"), position_cap_pct=Decimal("10"), min_position_aud=Decimal("5000")),
        proposed_annualised_vol=Decimal("0.20"),
        peers=(VolInput(symbol="NAB.AU", annualised_vol=Decimal("0.25")),),
        base_rate_evidence_ids=("cba-income-prior",),
    )


async def _case(*, band: tuple[str, str] = ("150", "165")):  # type: ignore[no-untyped-def]
    row = _thesis_row(entry_band_lower=Decimal(band[0]), entry_band_upper=Decimal(band[1]), stop_price=Decimal("140"), target_price=Decimal("185"))
    conn = _Conn(thesis_row=row, close=Decimal("159.15"), close_dt=AS_OF)
    return await builder.build_decision_case(conn, cutoff=CUTOFF, thesis_id=1, candidate=_cba_candidate(), context=_context())


# --- identical CLI / email render, receipts ------------------------------------------


async def test_cli_and_email_render_are_the_same_bytes_and_receipts_share_the_hash() -> None:
    case = await _case()
    html_cli = render_decision_case(case, evaluated_at=CUTOFF)
    html_email = render_decision_case(case, evaluated_at=CUTOFF)
    assert html_cli == html_email
    cli = receipt_for(case, html_cli, channel="cli", delivered_at=CUTOFF)
    email = receipt_for(case, html_email, channel="email", delivered_at=CUTOFF, resend_message_id="re_123")
    assert cli.render_sha256 == email.render_sha256 == render_sha256(html_cli)
    assert cli.decision_content_hash == case.decision.content_hash
    assert verify_content_hash(cli) and verify_content_hash(email)
    assert case.decision.decision_packet_id in html_cli and case.decision.content_hash in html_cli
    assert case.challenge.outcome.upper() in html_cli
    with pytest.raises(ValueError, match="CLI delivery"):
        receipt_for(case, html_cli, channel="cli", delivered_at=CUTOFF, resend_message_id="x")
    with pytest.raises(ValueError, match="provider message id"):
        receipt_for(case, html_email, channel="email", delivered_at=CUTOFF)
    pending = receipt_for(
        case,
        html_email,
        channel="email",
        delivered_at=CUTOFF,
        delivery_status="pending",
    )
    assert pending.resend_message_id is None and pending.delivery_status == "pending"


async def test_email_attempt_is_persisted_before_provider_send(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = await _case()
    html = render_decision_case(case, evaluated_at=CUTOFF)
    events: list[str] = []

    async def fake_persist(conn: object, receipt: object, rendered: str) -> None:
        events.append(receipt.delivery_status)  # type: ignore[attr-defined]

    def fake_send(rendered: str, *, case: object) -> str:
        events.append("provider")
        return "re_123"

    monkeypatch.setattr(decision_cli, "persist_receipt", fake_persist)
    monkeypatch.setattr(decision_cli, "send_decision_case", fake_send)
    pending, sent = await decision_cli._send_with_receipts(object(), case, html)
    assert events == ["pending", "provider", "sent"]
    assert pending.delivery_status == "pending"
    assert sent.delivery_status == "sent" and sent.resend_message_id == "re_123"


async def test_render_is_deterministic_and_changes_with_the_packet() -> None:
    a = await _case()
    b = await _case(band=("100", "110"))
    assert render_sha256(render_decision_case(a, evaluated_at=CUTOFF)) == render_sha256(render_decision_case(a, evaluated_at=CUTOFF))
    assert render_sha256(render_decision_case(a, evaluated_at=CUTOFF)) != render_sha256(render_decision_case(b, evaluated_at=CUTOFF))


def test_renderer_and_template_contain_no_financial_logic() -> None:
    src = (ROOT / "asxos" / "domain" / "decision_engine" / "delivery.py").read_text()
    body = src.split('"""', 2)[2]
    assert "Decimal(" not in body and "inverse_vol" not in body and "apply_constraints" not in body
    assert re.search(r"^\s*(?:from|import)\s+asxos\.domain\.(?:models|portfolio|tax)", src, re.MULTILINE) is None
    tpl = (ROOT / "asxos" / "brief" / "templates" / "decision_case.html.j2").read_text()
    for expr in re.findall(r"\{\{(.*?)\}\}", tpl):
        assert not re.search(r"[-+*/]\s*\d|\d\s*[-+*/]|\bround\b|\bsum\b", expr), expr


async def test_receipts_persist_to_their_own_append_only_table() -> None:
    """W7-0: receipts live in `delivery_receipts` (0052), never in `brief_runs`
    — a receipt row there was indistinguishable from a composed brief to
    `asxos/brief/deltas.py`. Round-trip and integrity are covered in depth by
    tests/test_decision_outcomes.py; this pins the delivery-side contract."""
    case = await _case()
    html = render_decision_case(case, evaluated_at=CUTOFF)

    class Conn:
        def __init__(self) -> None:
            self.rows: list[tuple[object, ...]] = []

        async def execute(self, query: str, *args: object) -> str:
            assert "INSERT INTO delivery_receipts" in query
            self.rows.append(args)
            return "INSERT 0 1"

        async def fetch(self, query: str, *args: object) -> list[Any]:
            assert "FROM delivery_receipts" in query
            return [{"payload": r[10], "rendered_html": r[9]} for r in self.rows if r[2] == args[0]]

    conn = Conn()
    r1 = receipt_for(case, html, channel="cli", delivered_at=CUTOFF)
    r2 = receipt_for(case, html, channel="email", delivered_at=CUTOFF + timedelta(seconds=1), resend_message_id="re_9")
    await persist_receipt(conn, r1, html)
    await persist_receipt(conn, r2, html)
    assert conn.rows[0][9] == html and conn.rows[1][8] == "re_9"
    assert await load_receipts(conn, case.decision.decision_packet_id) == (r1, r2)
    assert await load_receipts(conn, "dpk-other") == ()


# --- disposition, paper intent, identity resolution -------------------------------------


async def test_disposition_binds_to_packet_content_and_no_paper_intent_below_action() -> None:
    case = await _case()
    assert case.decision.recommendation_state == "watch"
    d = disposition_for(case, verdict="accept", note="Reviewed; hold as watch.", recorded_at=CUTOFF)
    assert d.decision_content_hash == case.decision.content_hash and d.recorded_by == "james" and verify_content_hash(d)
    assert paper_intent_for(case, d, created_at=CUTOFF) is None  # watch is non-action: no intent
    other = Disposition.model_validate({**d.model_dump(), "decision_content_hash": "0" * 64, "content_hash": ""})
    with pytest.raises(ValueError, match="different packet content"):
        paper_intent_for(case, other, created_at=CUTOFF)
    with pytest.raises(ValueError, match="action state"):
        PaperIntent(intent_id="i", decision_packet_id="p", disposition_id="d", recommendation_state="watch", created_at=CUTOFF)


async def test_every_identity_in_the_chain_resolves_through_the_repository() -> None:
    case = await _case()
    repo = _FakeRepoConn()
    await repository.save(case, conn=repo)
    loaded = await repository.load_case(case.decision.decision_packet_id, conn=repo)
    html = render_decision_case(loaded, evaluated_at=CUTOFF)
    receipt = receipt_for(loaded, html, channel="cli", delivered_at=CUTOFF)
    disposition = disposition_for(loaded, verdict="defer", note="await tax feed", recorded_at=CUTOFF)
    assert receipt.decision_packet_id == disposition.decision_packet_id == case.decision.decision_packet_id
    assert receipt.decision_content_hash == disposition.decision_content_hash == case.decision.content_hash
    assert loaded.decision.upstream_hashes.challenge_result == loaded.challenge.content_hash
    assert loaded.decision.upstream_hashes.evidence_packet == loaded.evidence.content_hash


async def test_missing_evidence_forces_abstention_in_the_delivered_render() -> None:
    row = _thesis_row(entry_band_lower=Decimal("150"), entry_band_upper=Decimal("165"), stop_price=Decimal("140"), target_price=Decimal("185"))
    conn = _Conn(thesis_row=row, close=None, close_dt=None)
    case = await builder.build_decision_case(conn, cutoff=CUTOFF, thesis_id=1, candidate=_cba_candidate(), context=_context())
    assert case.decision.recommendation_state == "abstain"
    html = render_decision_case(case, evaluated_at=CUTOFF)
    assert "ABSTAIN" in html and "missing data" in html


# --- measured portfolio state (gated) ---------------------------------------------------


class _StateConn:
    def __init__(
        self,
        *,
        snapshot: Mapping[str, object] | None,
        holdings: Sequence[Mapping[str, object]],
        closes: Mapping[str, Sequence[Decimal]],
        fx: Decimal | None,
        profile: Mapping[str, object] | None,
        holdings_changed_at: datetime | None,
        sectors_changed_at: datetime | None,
        candidates: Sequence[Mapping[str, object]] = (),
    ) -> None:
        self.snapshot, self.holdings, self.closes, self.fx, self.profile, self.candidates = snapshot, holdings, closes, fx, profile, candidates
        self.holdings_changed_at = holdings_changed_at
        self.sectors_changed_at = sectors_changed_at

    async def fetchrow(self, query: str, *args: object) -> Any:
        if "FROM portfolio_daily_snapshots" in query:
            return self.snapshot
        if "MAX(updated_at) AS changed_at FROM holding_lots" in query:
            return {"changed_at": self.holdings_changed_at}
        if "MAX(u.updated_at) AS changed_at" in query:
            return {"changed_at": self.sectors_changed_at}
        if "FROM fx_rates" in query:
            return {"rate": self.fx} if self.fx is not None else None
        if "FROM prices" in query and "LIMIT 1" in query:
            series = self.closes.get(str(args[0]))
            return {"dt": args[1], "close": series[-1]} if series else None
        if "FROM profiles" in query:
            return self.profile
        raise AssertionError(query)

    async def fetch(self, query: str, *args: object) -> list[Any]:
        if "FROM current_holdings" in query:
            return list(self.holdings)
        if "FROM prices" in query:
            series = list(self.closes.get(str(args[0]), ()))
            return [{"close": c} for c in reversed(series)][: int(args[2])]  # type: ignore[call-overload]
        if "FROM candidate_snapshots" in query:
            return [{"payload": c} for c in self.candidates]
        raise AssertionError(query)


def _state_conn(**kw: Any) -> _StateConn:
    base: dict[str, Any] = {
        "snapshot": {"as_of": AS_OF, "capital_aud": Decimal("500000"), "holdings_mv_aud": Decimal("400000"), "cash_aud": Decimal("100000"), "ingested_at": CUTOFF},
        "holdings": [
            {"symbol": "NAB.AU", "quantity": Decimal("1000"), "sector": "Financials"},
            {"symbol": "HUBS.NYSE", "quantity": Decimal("24"), "sector": None},
        ],
        "closes": {"NAB.AU": [Decimal("40")] * 61, "HUBS.NYSE": [Decimal("250")] * 61},
        "fx": Decimal("0.65"),
        "profile": {"capital_aud": Decimal("500000"), "cash_floor_pct": Decimal("0.05"), "per_name_cap_pct": Decimal("0.10"), "sector_cap_pct": Decimal("0.40"), "min_position_aud": Decimal("5000"), "updated_at": CUTOFF - timedelta(days=1)},
        "holdings_changed_at": CUTOFF - timedelta(days=1),
        "sectors_changed_at": CUTOFF - timedelta(days=1),
    }
    base.update(kw)
    return _StateConn(**base)


async def test_portfolio_state_is_measured_from_the_snapshot_holdings_prices_and_fx() -> None:
    state = await load_portfolio_state(_state_conn(), AS_OF)
    assert state.capital_aud == Decimal("500000") and state.cash_pct == Decimal("20")
    assert state.position_weights_pct["NAB.AU"] == Decimal("8")  # 1000 × 40 / 500000
    assert state.position_weights_pct["HUBS.NYSE"] == Decimal("1.846154")  # 24 × 250 / 0.65 / 500000
    assert state.sector_weights_pct == {"Financials": Decimal("8"), "UNKNOWN": Decimal("1.846154")}
    assert state.gross_exposure_pct == Decimal("9.846154") and state.borrowing_aud == 0
    assert state.evidence_id == "portfolio-state-2026-09-01"


async def test_portfolio_state_hard_fails_on_missing_snapshot_price_or_fx() -> None:
    with pytest.raises(RuntimeError, match="no portfolio_daily_snapshots"):
        await load_portfolio_state(_state_conn(snapshot=None), AS_OF)
    with pytest.raises(RuntimeError, match="no price"):
        await load_portfolio_state(_state_conn(closes={"NAB.AU": [Decimal("40")]}), AS_OF)
    with pytest.raises(RuntimeError, match="AUDUSD"):
        await load_portfolio_state(_state_conn(fx=None), AS_OF)


async def test_sizing_policy_is_never_looser_than_the_register() -> None:
    policy = await load_sizing_policy(_state_conn(), AS_OF)
    assert policy.cash_floor_pct == Decimal("7.5")  # profile 5% is tightened to D1
    assert policy.sector_cap_pct == Decimal("30")  # profile 40% is tightened to D8
    assert policy.position_cap_pct == Decimal("10") and policy.min_position_aud == Decimal("5000")


async def test_vol_loader_needs_a_full_window() -> None:
    assert await load_annualised_vol(_state_conn(), "NAB.AU", AS_OF) == Decimal("0")  # flat series
    assert await load_annualised_vol(_state_conn(closes={"NAB.AU": [Decimal("40")] * 10}), "NAB.AU", AS_OF) is None


async def test_loaders_refuse_without_the_personal_use_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ASXOS_PERSONAL_USE", raising=False)
    with pytest.raises(PersonalUseRequired):
        await load_portfolio_state(_state_conn(), AS_OF)
    with pytest.raises(PersonalUseRequired):
        await load_sizing_policy(_state_conn(), AS_OF)


async def test_portfolio_state_refuses_historical_or_post_snapshot_current_rows() -> None:
    with pytest.raises(RuntimeError, match="latest exact snapshot"):
        await load_portfolio_state(_state_conn(), AS_OF - timedelta(days=1))
    with pytest.raises(RuntimeError, match="holding lots changed"):
        await load_portfolio_state(
            _state_conn(holdings_changed_at=CUTOFF + timedelta(seconds=1)), AS_OF
        )
    with pytest.raises(RuntimeError, match="held-symbol sectors changed"):
        await load_portfolio_state(
            _state_conn(sectors_changed_at=CUTOFF + timedelta(seconds=1)), AS_OF
        )
    with pytest.raises(RuntimeError, match="active profile changed"):
        await load_sizing_policy(
            _state_conn(
                profile={
                    "capital_aud": Decimal("500000"),
                    "cash_floor_pct": Decimal("0.05"),
                    "per_name_cap_pct": Decimal("0.10"),
                    "sector_cap_pct": Decimal("0.40"),
                    "min_position_aud": Decimal("5000"),
                    "updated_at": CUTOFF + timedelta(seconds=1),
                }
            ),
            AS_OF,
        )


# --- positive control (D-5) --------------------------------------------------------------


def _candidate(symbol: str, *, adv: str, checks: dict[str, str] | None = None) -> CandidateSnapshot:
    cutoff = cutoff_instant(AS_OF)
    ev = EvidenceItem(evidence_id=f"candidate:price:{symbol}", evidence_type="market_fact", title="x", claim="y",
                      source_uri="db://prices", observed_at=AS_OF, known_at=cutoff, evidence_tier="verified", data_mode="real")
    return CandidateSnapshot(
        candidate_id=f"cand-t-{symbol}-{AS_OF}", symbol=symbol, theme_version_id="tv-t", theme_code="t", exposure_direction="positive",
        measures={"median_dollar_volume_60d": adv}, quality_checks=checks or {"has_sector": "pass", "liquid_enough": "pass"},
        as_of=AS_OF, knowledge_cutoff=cutoff, expires_at=cutoff + timedelta(days=30), evidence=(ev,), data_mode="real", created_at=cutoff,
    )


def test_positive_control_ranking_excludes_negative_controls_and_prefers_quality_then_liquidity() -> None:
    cands = (
        _candidate("CBA.AU", adv="900000000"),
        _candidate("NAB.AU", adv="200000000"),
        _candidate("WES.AU", adv="300000000"),
        _candidate("ZIP.AU", adv="50000000", checks={"has_sector": "pass", "liquid_enough": "fail"}),
        _candidate("HUBS.NYSE", adv="100000000"),
    )
    ranked = rank_positive_controls(cands)
    assert [c.symbol for c in ranked] == ["WES.AU", "NAB.AU"]
    assert NEGATIVE_CONTROLS >= {"CBA.AU", "HUBS.NYSE", "ESS.AU"}


async def test_positive_control_is_none_when_only_cba_is_governed() -> None:
    only_cba = _state_conn(candidates=[json.dumps(_candidate("CBA.AU", adv="1").model_dump(mode="json"))])
    assert await select_positive_control(only_cba, AS_OF, now=AS_OF) is None
    with_nab = _state_conn(candidates=[json.dumps(_candidate("NAB.AU", adv="1").model_dump(mode="json"))])
    pick = await select_positive_control(with_nab, AS_OF, now=AS_OF)
    assert pick is not None and pick.symbol == "NAB.AU"


def test_cli_module_gates_every_command_and_imports_no_model_a() -> None:
    src = (ROOT / "asxos" / "cli" / "decision.py").read_text()
    body = src.split('"""', 2)[2]
    commands = body.count("@decision_app.command(")
    assert commands == 6, "build, record-t0, observe, positive-control, dispose, report"
    assert body.count("_require_personal_use()") == commands, "every command gates first"
    assert re.search(r"^\s*(?:from|import)\s+asxos\.domain\.models", src, re.MULTILINE) is None
    assert "signals" not in body.lower()
    assert os.environ.get("ASXOS_PERSONAL_USE") == "1"
