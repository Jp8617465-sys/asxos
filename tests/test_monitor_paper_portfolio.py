"""
Tests for the paper-portfolio performance monitor (M13.8+).

Pure-function tests on synthetic data — no DB, mirroring the repo's domain-test
convention (test_portfolio_constraints.py). Covers every reported metric plus
the discipline-critical edge cases:

  * not-yet-measurable (0 forward trading days) — the honest state for run_id=1
  * no-lookahead guard (price dt > eval raises)
  * eval before entry raises
  * missing prices recorded explicitly; default does NOT silently forward-fill
  * forward-fill is applied only when enabled AND is flagged
  * total return uses adj_close; price return uses close
  * contribution_pct reconciles to the headline price return
  * hit rate / payoff / drawdown / vol / turnover / costs
  * sector / signal-label / prob_up / expected_return bucket attribution
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from asxos.domain.portfolio.monitor import (
    BenchmarkSeries,
    CostModel,
    MonitorInputs,
    Position,
    PriceBar,
    compute_report,
)

D = Decimal
_D0 = date(2026, 1, 5)   # entry / build date
_D1 = date(2026, 1, 6)
_D2 = date(2026, 1, 7)


def _pos(
    symbol: str,
    *,
    qty: float,
    entry: float,
    weight: float,
    target_aud: float,
    sector: str | None = "Industrials",
    label: str = "STRONG_BUY",
    prob_up: float = 0.8,
    expected_return: float = 0.5,
    entry_adj: float | None = None,
) -> Position:
    return Position(
        symbol=symbol,
        sector=sector,
        qty=D(str(qty)),
        entry_close=D(str(entry)),
        entry_adj_close=D(str(entry if entry_adj is None else entry_adj)),
        target_weight=D(str(weight)),
        target_aud=D(str(target_aud)),
        signal_label=label,
        prob_up=D(str(prob_up)),
        expected_return=D(str(expected_return)),
    )


def _bar(close: float, adj: float | None = None) -> PriceBar:
    return PriceBar(close=D(str(close)), adj_close=None if adj is None else D(str(adj)))


def _inp(
    positions: list[Position],
    panel: dict[date, dict[str, PriceBar]],
    *,
    eval_as_of: date,
    capital: float,
    cash: float,
    traded: float,
    benchmark: BenchmarkSeries | None = None,
    forward_fill: bool = False,
    run_as_of: date = _D0,
) -> MonitorInputs:
    return MonitorInputs(
        run_id=1,
        run_as_of=run_as_of,
        signals_as_of=run_as_of,
        eval_as_of=eval_as_of,
        model_version="v1_5",
        capital_aud=D(str(capital)),
        cash_aud=D(str(cash)),
        positions=positions,
        price_panel=panel,
        benchmark=benchmark or BenchmarkSeries(available=False, source="AXJO.INDX", note="gap"),
        total_traded_aud=D(str(traded)),
        cost_model=CostModel(),
        forward_fill=forward_fill,
    )


# ---------------------------------------------------------------------------
# Measurability gate
# ---------------------------------------------------------------------------


def test_not_measurable_zero_forward_days():
    """Entry-day-only panel => not yet measurable; headline metrics are None,
    but turnover and cost (which don't need forward data) are still computed."""
    pos = [_pos("AAA", qty=100, entry=10, weight=1.0, target_aud=1000)]
    panel = {_D0: {"AAA": _bar(10, 10)}}
    rep = compute_report(_inp(pos, panel, eval_as_of=_D0, capital=1000, cash=0, traded=1000))
    assert rep.measurable is False
    assert rep.n_forward_days == 0
    assert rep.price_return_pct is None
    assert rep.total_return_pct is None
    assert rep.hit_rate_pct is None
    assert rep.turnover_pct == D("100.00")
    assert rep.cost.est_cost_aud == D("1.300000")
    assert "Not yet measurable" in rep.measurability_note


def test_measurable_with_one_forward_day():
    pos = [_pos("AAA", qty=100, entry=10, weight=1.0, target_aud=1000)]
    panel = {_D0: {"AAA": _bar(10, 10)}, _D1: {"AAA": _bar(11, 11)}}
    rep = compute_report(_inp(pos, panel, eval_as_of=_D1, capital=1000, cash=0, traded=1000))
    assert rep.measurable is True
    assert rep.n_forward_days == 1
    assert rep.price_return_pct == D("10.00")
    assert rep.total_return_pct == D("10.00")
    assert rep.total_nav_aud == D("1100.000000")


# ---------------------------------------------------------------------------
# Guards
# ---------------------------------------------------------------------------


def test_lookahead_raises():
    pos = [_pos("AAA", qty=100, entry=10, weight=1.0, target_aud=1000)]
    panel = {_D0: {"AAA": _bar(10, 10)}, _D2: {"AAA": _bar(12, 12)}}  # D2 > eval D1
    with pytest.raises(ValueError, match="lookahead"):
        compute_report(_inp(pos, panel, eval_as_of=_D1, capital=1000, cash=0, traded=1000))


def test_eval_before_entry_raises():
    pos = [_pos("AAA", qty=100, entry=10, weight=1.0, target_aud=1000)]
    panel = {_D0: {"AAA": _bar(10, 10)}}
    with pytest.raises(ValueError, match="precedes"):
        compute_report(_inp(pos, panel, eval_as_of=date(2026, 1, 1), capital=1000, cash=0, traded=1000))


# ---------------------------------------------------------------------------
# Returns: close vs adj_close
# ---------------------------------------------------------------------------


def test_total_return_uses_adj_close_price_return_uses_close():
    """A dividend makes adj_close diverge from close: total_return > price_return."""
    pos = [_pos("AAA", qty=100, entry=10, weight=1.0, target_aud=1000, entry_adj=10)]
    # close flat at 10 but adj_close rose to 10.5 (dividend reinvested)
    panel = {_D0: {"AAA": _bar(10, 10)}, _D1: {"AAA": _bar(10, 10.5)}}
    rep = compute_report(_inp(pos, panel, eval_as_of=_D1, capital=1000, cash=0, traded=1000))
    p = rep.positions[0]
    assert p.used_adj_close is True
    assert p.price_return_pct == D("0.00")
    assert p.total_return_pct == D("5.00")


def test_total_return_falls_back_to_close_when_adj_missing():
    pos = [_pos("AAA", qty=100, entry=10, weight=1.0, target_aud=1000)]
    panel = {_D0: {"AAA": _bar(10, 10)}, _D1: {"AAA": _bar(11, None)}}  # adj missing
    rep = compute_report(_inp(pos, panel, eval_as_of=_D1, capital=1000, cash=0, traded=1000))
    p = rep.positions[0]
    assert p.used_adj_close is False
    assert p.total_return_pct == D("10.00")  # falls back to price return


# ---------------------------------------------------------------------------
# Contribution reconciles to headline (institutional self-check)
# ---------------------------------------------------------------------------


def test_contribution_reconciles_to_price_return():
    pos = [
        _pos("AAA", qty=100, entry=10, weight=0.5, target_aud=1000, sector="Tech"),
        _pos("BBB", qty=50, entry=20, weight=0.5, target_aud=1000, sector="Energy"),
    ]
    panel = {
        _D0: {"AAA": _bar(10, 10), "BBB": _bar(20, 20)},
        _D1: {"AAA": _bar(12, 12), "BBB": _bar(19, 19)},
    }
    # capital 2000, fully invested, cash 0
    rep = compute_report(_inp(pos, panel, eval_as_of=_D1, capital=2000, cash=0, traded=2000))
    contribs = sum((p.contribution_pct for p in rep.positions), D("0"))
    assert contribs == rep.price_return_pct  # contributions sum to NAV return


# ---------------------------------------------------------------------------
# Missing data — explicit, never silent
# ---------------------------------------------------------------------------


def test_missing_price_recorded_not_silently_filled():
    pos = [
        _pos("AAA", qty=100, entry=10, weight=0.5, target_aud=1000),
        _pos("BBB", qty=50, entry=20, weight=0.5, target_aud=1000),
    ]
    # BBB has no bar on D1
    panel = {_D0: {"AAA": _bar(10, 10), "BBB": _bar(20, 20)}, _D1: {"AAA": _bar(11, 11)}}
    rep = compute_report(_inp(pos, panel, eval_as_of=_D1, capital=2000, cash=0, traded=2000))
    assert any(e.symbol == "BBB" and e.detail == "no_bar" for e in rep.missing_events)
    # BBB position is unpriced at eval (no bar in window after entry)... it has D0 bar
    bbb = next(p for p in rep.positions if p.symbol == "BBB")
    assert bbb.priced is True  # D0 bar is the latest available within window
    last_nav = rep.nav_series[-1]
    assert last_nav.n_missing >= 1  # D1 NAV point flags BBB missing


def test_forward_fill_is_flagged_when_enabled():
    pos = [
        _pos("AAA", qty=100, entry=10, weight=0.5, target_aud=1000),
        _pos("BBB", qty=50, entry=20, weight=0.5, target_aud=1000),
    ]
    panel = {_D0: {"AAA": _bar(10, 10), "BBB": _bar(20, 20)}, _D1: {"AAA": _bar(11, 11)}}
    rep = compute_report(
        _inp(pos, panel, eval_as_of=_D1, capital=2000, cash=0, traded=2000, forward_fill=True)
    )
    d1 = rep.nav_series[-1]
    assert d1.forward_filled is True
    assert any(e.detail == "forward_filled" for e in rep.missing_events)


# ---------------------------------------------------------------------------
# Risk / quality metrics
# ---------------------------------------------------------------------------


def test_hit_rate_and_payoff():
    pos = [
        _pos("AAA", qty=100, entry=10, weight=0.5, target_aud=1000),  # +20%
        _pos("BBB", qty=100, entry=10, weight=0.5, target_aud=1000),  # -10%
    ]
    panel = {
        _D0: {"AAA": _bar(10, 10), "BBB": _bar(10, 10)},
        _D1: {"AAA": _bar(12, 12), "BBB": _bar(9, 9)},
    }
    rep = compute_report(_inp(pos, panel, eval_as_of=_D1, capital=2000, cash=0, traded=2000))
    assert rep.hit_rate_pct == D("50.00")
    assert rep.avg_winner_pct == D("20.00")
    assert rep.avg_loser_pct == D("-10.00")
    assert rep.payoff_ratio == D("2.00")


def test_max_drawdown_and_vol():
    pos = [_pos("AAA", qty=100, entry=10, weight=1.0, target_aud=1000)]
    panel = {
        _D0: {"AAA": _bar(10, 10)},
        _D1: {"AAA": _bar(11, 11)},     # +10%
        _D2: {"AAA": _bar(9.9, 9.9)},   # -10% -> drawdown
    }
    rep = compute_report(_inp(pos, panel, eval_as_of=_D2, capital=1000, cash=0, traded=1000))
    assert rep.max_drawdown_pct == D("-10.00")
    assert rep.realised_vol_pct is not None
    assert D("200") < rep.realised_vol_pct < D("250")  # ~224% annualised on 2 swings


def test_turnover_and_costs():
    pos = [_pos("AAA", qty=100, entry=10, weight=0.95, target_aud=950)]
    panel = {_D0: {"AAA": _bar(10, 10)}, _D1: {"AAA": _bar(10, 10)}}
    inp = _inp(pos, panel, eval_as_of=_D1, capital=1000, cash=50, traded=950)
    rep = compute_report(inp)
    assert rep.turnover_pct == D("95.00")
    # 13 bps on 950 traded = 1.235 AUD; 1.235/1000*10000 = 12.35 bps of capital
    assert rep.cost.est_cost_aud == D("1.235000")
    assert rep.cost.est_cost_bps_of_capital == D("12.35")


# ---------------------------------------------------------------------------
# Benchmark
# ---------------------------------------------------------------------------


def test_benchmark_relative_when_available():
    pos = [_pos("AAA", qty=100, entry=10, weight=1.0, target_aud=1000)]
    panel = {_D0: {"AAA": _bar(10, 10)}, _D1: {"AAA": _bar(11, 11)}}  # +10%
    bench = BenchmarkSeries(
        available=True, source="AXJO.INDX", note="",
        levels={_D0: D("8000"), _D1: D("8240")},  # +3%
    )
    rep = compute_report(
        _inp(pos, panel, eval_as_of=_D1, capital=1000, cash=0, traded=1000, benchmark=bench)
    )
    assert rep.benchmark_return_pct == D("3.00")
    assert rep.benchmark_relative_pct == D("7.00")  # 10 - 3


def test_benchmark_gap_reported_not_fabricated():
    pos = [_pos("AAA", qty=100, entry=10, weight=1.0, target_aud=1000)]
    panel = {_D0: {"AAA": _bar(10, 10)}, _D1: {"AAA": _bar(11, 11)}}
    rep = compute_report(_inp(pos, panel, eval_as_of=_D1, capital=1000, cash=0, traded=1000))
    assert rep.benchmark_available is False
    assert rep.benchmark_return_pct is None
    assert rep.benchmark_relative_pct is None


# ---------------------------------------------------------------------------
# Attribution & buckets
# ---------------------------------------------------------------------------


def test_sector_and_label_and_prob_buckets():
    pos = [
        _pos("AAA", qty=100, entry=10, weight=0.4, target_aud=1000, sector="Tech",
             label="STRONG_BUY", prob_up=0.9),
        _pos("BBB", qty=100, entry=10, weight=0.3, target_aud=1000, sector="Tech",
             label="BUY", prob_up=0.6),
        _pos("CCC", qty=100, entry=10, weight=0.3, target_aud=1000, sector="Energy",
             label="STRONG_BUY", prob_up=0.7),
    ]
    panel = {
        _D0: {s: _bar(10, 10) for s in ("AAA", "BBB", "CCC")},
        _D1: {"AAA": _bar(12, 12), "BBB": _bar(11, 11), "CCC": _bar(9, 9)},
    }
    rep = compute_report(_inp(pos, panel, eval_as_of=_D1, capital=3000, cash=0, traded=3000))

    sectors = {b.label: b for b in rep.sector_attribution}
    assert sectors["Tech"].n == 2
    assert sectors["Energy"].n == 1

    labels = {b.label: b for b in rep.by_signal_label}
    assert labels["STRONG_BUY"].n == 2  # AAA + CCC
    assert labels["BUY"].n == 1

    # prob_up edges default (0.55, 0.65, 0.75, 0.85): 0.6 -> '0.55-0.65',
    # 0.7 -> '0.65-0.75', 0.9 -> '>=0.85'
    pbuckets = {b.label: b for b in rep.by_prob_up_bucket}
    assert pbuckets["0.55-0.65"].n == 1
    assert pbuckets["0.65-0.75"].n == 1
    assert pbuckets[">=0.85"].n == 1


def test_equal_vs_model_weight():
    pos = [
        _pos("AAA", qty=100, entry=10, weight=0.8, target_aud=1600),  # +20%, heavy weight
        _pos("BBB", qty=100, entry=10, weight=0.2, target_aud=400),   # -10%, light weight
    ]
    panel = {
        _D0: {"AAA": _bar(10, 10), "BBB": _bar(10, 10)},
        _D1: {"AAA": _bar(12, 12), "BBB": _bar(9, 9)},
    }
    rep = compute_report(_inp(pos, panel, eval_as_of=_D1, capital=2000, cash=0, traded=2000))
    # equal-weight = mean(20, -10) = 5.00
    assert rep.equal_weight_return_pct == D("5.00")
    # model-weight by target_weight: 20*0.8 + (-10)*0.2 = 16 - 2 = 14.00
    assert rep.model_weight_return_pct == D("14.00")
