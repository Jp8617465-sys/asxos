"""The value screen (F-E2E r2 S4, demoted by #306): four gates, symbol order, no plan, no rank."""
from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal as D

import pytest

from asxos.domain.discovery import ranker, types
from asxos.domain.research.registry import vp
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


def test_cheap_name_passes_and_carries_every_figure_it_passed_on() -> None:
    (o,) = ranker.passing([CHEAP, DEAR], _screened("CHEAP.AU", "DEAR.AU"), screening_run_id=7)
    assert o.symbol == "CHEAP.AU" and o.screening_run_id == 7
    assert o.value_to_price_registered >= 1 and o.value_to_price_average_roe >= 1
    assert o.value_to_price_min == min(o.value_to_price_registered, o.value_to_price_average_roe)
    assert o.run_id == CHEAP.run_id and o.run_content_hash == CHEAP.content_hash
    assert o.value_registered == CHEAP.value_per_share and o.adv_aud == D("2000000")


def test_expensive_name_is_excluded_by_the_value_gate() -> None:
    assert ranker.passing([DEAR], _screened("DEAR.AU"), screening_run_id=1) == []


def test_peak_cycle_trailing_roe_is_caught_by_the_average() -> None:
    """Trailing ROE 60% but a 3-period average of 4%: value on the average is below price."""
    peak = _run("PEAK.AU", book=D("10"), roe=D("0.60"), roe_avg=D("0.04"), close=D("12"))
    assert ranker.passing([peak], _screened("PEAK.AU"), screening_run_id=1) == []


def test_quality_gate_uses_the_average_roe_against_ke() -> None:
    low = _run("LOW.AU", book=D("10"), roe=D("0.20"), roe_avg=D("0.05"), close=D("3"))  # cheap but avg ROE < Ke
    assert ranker.passing([low], _screened("LOW.AU"), screening_run_id=1) == []


def test_missing_average_falls_back_to_trailing_and_is_flagged() -> None:
    noavg = _run("NOAVG.AU", book=D("10"), roe=D("0.20"), roe_avg=None, close=D("8"))
    (o,) = ranker.passing([noavg], _screened("NOAVG.AU"), screening_run_id=1)
    assert o.roe_average_is_fallback and ranker.FLAG_ROE_AVERAGE_FALLBACK in o.flags
    assert o.value_average_roe == o.value_registered


def test_currency_unverified_is_excluded_unless_asked() -> None:
    unv = _run("UNV.AU", book=D("10"), roe=D("0.20"), roe_avg=D("0.18"), close=D("8"), currency=None)
    assert ranker.passing([unv], _screened("UNV.AU"), screening_run_id=1) == []
    (o,) = ranker.passing([unv], _screened("UNV.AU"), screening_run_id=1, include_currency_unverified=True)
    assert sweep.FLAG_CURRENCY_UNVERIFIED in o.flags


@pytest.mark.parametrize(
    ("adv", "cap"),
    [(D("249999"), D("500000000")), (D("2000000"), D("99999999"))],
)
def test_liquidity_and_cap_floors_exclude(adv: D, cap: D) -> None:
    assert ranker.passing([CHEAP], _screened("CHEAP.AU", adv=adv, cap=cap), screening_run_id=1) == []


def test_unscreened_blocked_and_unvalued_runs_are_skipped() -> None:
    blocked = _run("BLK.AU", book=D("10"), roe=D("-0.1"), roe_avg=None, close=D("8"))
    assert blocked.outcome == "blocked"
    assert ranker.passing([CHEAP, blocked], _screened("BLK.AU"), screening_run_id=1) == []


# --- the demotion (#306) --------------------------------------------------------------


def test_passing_set_is_symbol_ordered_not_ranked() -> None:
    """A cheaper name and a thinner name do not move: the order is the symbol, nothing else."""
    cheaper = _run("ZZZ.AU", book=D("10"), roe=D("0.20"), roe_avg=D("0.18"), close=D("4"))  # 2x cheaper than CHEAP
    thin = {
        "CHEAP.AU": ranker.Screened("CHEAP.AU", adv_aud=D("500000"), market_cap_aud=D("500000000")),
        "ZZZ.AU": ranker.Screened("ZZZ.AU", adv_aud=D("2000000"), market_cap_aud=D("500000000")),
    }
    out = ranker.passing([cheaper, CHEAP], thin, screening_run_id=1)
    assert [o.symbol for o in out] == ["CHEAP.AU", "ZZZ.AU"]
    assert out[1].value_to_price_min > out[0].value_to_price_min  # the cheaper name is NOT first


def test_the_demotion_removed_every_target_band_stop_and_rank_surface() -> None:
    """#306 pins the sealed response rule to the code: no plan, no constants, no score, no rank."""
    assert "stops emitting target prices, entry bands and ranked 'opportunities'" in vp.RESPONSE_RULE
    for name in (
        "plan_for", "rank", "liquidity_factor", "thesis_text_for", "invalidation_conditions_for",
        "ENTRY_UPPER_OF_TARGET", "ENTRY_LOWER_OF_TARGET", "STOP_OF_ENTRY_UPPER", "TIMELINE_DAYS",
        "LIQUIDITY_NEUTRAL_ADV_AUD",
    ):
        assert not hasattr(ranker, name), name
    assert not hasattr(types, "ThesisPlan")
    fields = set(types.Opportunity.model_fields)
    assert not fields & {"plan", "score", "liquidity_factor", "target_price", "entry_band_lower", "stop_price"}
    # the gates the packet builder and the screening rule still read are intact
    assert int(ranker.MIN_ADV_AUD) == 250000 and int(ranker.MIN_MARKET_CAP_AUD) == 100000000
