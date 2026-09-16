"""The deterministic discovery ranker (F-E2E r2 S4): gates, score, plan, prose."""
from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal as D

import pytest

from asxos.domain.discovery import ranker
from asxos.domain.valuation import sweep
from asxos.domain.valuation.contracts import ValuationRun
from asxos.domain.valuation.preregistration import load_bundled_preregistration
from asxos.domain.valuation.universe import MarketInputs, UniverseRow

PREREG = load_bundled_preregistration()
MARKET = MarketInputs(D("0.04831"), date(2026, 9, 15), D("0.7134"), date(2026, 9, 14))
KE = sweep.ke_band_for(MARKET, PREREG)  # ke_mid 0.086810
CUTOFF = datetime(2026, 9, 19, 16, 0, tzinfo=UTC)


def _run(symbol: str, *, book: D, roe: D, roe_avg: D | None, close: D, currency: str | None = "AUD") -> ValuationRun:
    row = UniverseRow(
        symbol=symbol, pit_as_of=date(2026, 6, 30), pit_knowledge_date=date(2026, 8, 30),
        book_value_ps=book, roe=roe, eps_ttm=D("1"), dividend_ttm=D("0.5"), franking_avg_pct=D("100"),
        currency=currency, roe_average=roe_avg, roe_periods=3 if roe_avg is not None else 0,
        last_close_dt=date(2026, 9, 18), last_close=close,
    )
    return sweep.value_row(row, market=MARKET, ke=KE, prereg=PREREG, cutoff=CUTOFF, created_at=CUTOFF)


def _screened(*symbols: str, adv: D = D("2000000"), cap: D = D("500000000")) -> dict[str, ranker.Screened]:
    return {s: ranker.Screened(s, adv_aud=adv, market_cap_aud=cap) for s in symbols}


# A cheap, high-quality name: book 10, ROE 20% on both bases, close 8 -> value well above price.
CHEAP = _run("CHEAP.AU", book=D("10"), roe=D("0.20"), roe_avg=D("0.18"), close=D("8"))
# Expensive: same fundamentals, close 40.
DEAR = _run("DEAR.AU", book=D("10"), roe=D("0.20"), roe_avg=D("0.18"), close=D("40"))


def test_cheap_name_ranks_and_carries_every_figure() -> None:
    (o,) = ranker.rank([CHEAP, DEAR], _screened("CHEAP.AU", "DEAR.AU"), screening_run_id=7)
    assert o.symbol == "CHEAP.AU" and o.screening_run_id == 7
    assert o.value_to_price_registered >= 1 and o.value_to_price_average_roe >= 1
    assert o.value_to_price_min == min(o.value_to_price_registered, o.value_to_price_average_roe)
    assert o.liquidity_factor == D("1.000000") and o.score == o.value_to_price_min
    assert o.run_id == CHEAP.run_id and o.run_content_hash == CHEAP.content_hash
    assert o.plan.target_price == CHEAP.value_per_share
    assert o.plan.entry_band_upper == (CHEAP.value_per_share * D("0.80")).quantize(D("0.000001"))  # type: ignore[operator]
    assert o.plan.stop_price == (o.plan.entry_band_upper * D("0.80")).quantize(D("0.000001"))
    assert o.plan.timeline_days == 365


def test_expensive_name_is_excluded_by_the_value_gate() -> None:
    assert ranker.rank([DEAR], _screened("DEAR.AU"), screening_run_id=1) == []


def test_peak_cycle_trailing_roe_is_caught_by_the_average() -> None:
    """Trailing ROE 60% but a 3-period average of 4%: value on the average is below price."""
    peak = _run("PEAK.AU", book=D("10"), roe=D("0.60"), roe_avg=D("0.04"), close=D("12"))
    assert ranker.rank([peak], _screened("PEAK.AU"), screening_run_id=1) == []


def test_quality_gate_uses_the_average_roe_against_ke() -> None:
    low = _run("LOW.AU", book=D("10"), roe=D("0.20"), roe_avg=D("0.05"), close=D("3"))  # cheap but avg ROE < Ke
    assert ranker.rank([low], _screened("LOW.AU"), screening_run_id=1) == []


def test_missing_average_falls_back_to_trailing_and_is_flagged() -> None:
    noavg = _run("NOAVG.AU", book=D("10"), roe=D("0.20"), roe_avg=None, close=D("8"))
    (o,) = ranker.rank([noavg], _screened("NOAVG.AU"), screening_run_id=1)
    assert o.roe_average_is_fallback and ranker.FLAG_ROE_AVERAGE_FALLBACK in o.flags
    assert o.value_average_roe == o.value_registered


def test_currency_unverified_is_never_proposed_unless_asked() -> None:
    unv = _run("UNV.AU", book=D("10"), roe=D("0.20"), roe_avg=D("0.18"), close=D("8"), currency=None)
    assert ranker.rank([unv], _screened("UNV.AU"), screening_run_id=1) == []
    (o,) = ranker.rank([unv], _screened("UNV.AU"), screening_run_id=1, include_currency_unverified=True)
    assert sweep.FLAG_CURRENCY_UNVERIFIED in o.flags


@pytest.mark.parametrize(
    ("adv", "cap"),
    [(D("249999"), D("500000000")), (D("2000000"), D("99999999"))],
)
def test_liquidity_and_cap_floors_exclude(adv: D, cap: D) -> None:
    assert ranker.rank([CHEAP], _screened("CHEAP.AU", adv=adv, cap=cap), screening_run_id=1) == []


def test_unscreened_blocked_and_unvalued_runs_are_skipped() -> None:
    blocked = _run("BLK.AU", book=D("10"), roe=D("-0.1"), roe_avg=None, close=D("8"))
    assert blocked.outcome == "blocked"
    assert ranker.rank([CHEAP, blocked], _screened("BLK.AU"), screening_run_id=1) == []


def test_liquidity_factor_discounts_thin_names_and_orders_the_list() -> None:
    thin = {"CHEAP.AU": ranker.Screened("CHEAP.AU", adv_aud=D("500000"), market_cap_aud=D("500000000"))}
    (o,) = ranker.rank([CHEAP], thin, screening_run_id=1)
    assert o.liquidity_factor == D("0.500000")
    assert o.score == (o.value_to_price_min * D("0.5")).quantize(D("0.000001"))
    # Two names: the liquid one ranks first on score, ties break on symbol.
    other = _run("AAA.AU", book=D("10"), roe=D("0.20"), roe_avg=D("0.18"), close=D("8"))
    both = {**thin, "AAA.AU": ranker.Screened("AAA.AU", adv_aud=D("2000000"), market_cap_aud=D("500000000"))}
    ranked = ranker.rank([CHEAP, other], both, screening_run_id=1)
    assert [o.symbol for o in ranked] == ["AAA.AU", "CHEAP.AU"]
    same = ranker.rank([CHEAP, other], _screened("CHEAP.AU", "AAA.AU"), screening_run_id=1)
    assert [o.symbol for o in same] == ["AAA.AU", "CHEAP.AU"]


def test_plan_conventions_and_close_inside_band() -> None:
    plan = ranker.plan_for(D("100"), D("70"))
    assert (plan.entry_band_lower, plan.entry_band_upper, plan.stop_price) == (D("65"), D("80"), D("64"))
    assert plan.close_inside_band is True
    assert ranker.plan_for(D("100"), D("90")).close_inside_band is False


def test_prose_is_template_only_and_conditions_are_measurable() -> None:
    (o,) = ranker.rank([CHEAP], _screened("CHEAP.AU"), screening_run_id=7)
    text = ranker.thesis_text_for(o)
    assert "not a recommendation" in text and o.run_id in text and str(o.value_registered) in text
    conditions = ranker.invalidation_conditions_for(o)
    assert len(conditions) == 3 and all(any(ch.isdigit() for ch in c["condition"]) for c in conditions)
    assert all(c["status"] == "open" for c in conditions)
