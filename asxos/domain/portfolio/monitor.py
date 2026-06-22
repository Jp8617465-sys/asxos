"""
Paper-portfolio performance monitor — pure analytics layer (M13.8+).

This module is the *scoreboard* for persisted paper-trade builds. It answers
"did the model portfolio actually perform?" — distinct from "did the pipeline
run?". It is deliberately a strategy-incubation tracker, NOT a backtester and
NOT proof of alpha. A single run's realised P&L is one noisy data point.

Design contract (institutional discipline)
-------------------------------------------
* Decimal-only arithmetic (portfolio-conventions.md — no numpy/pandas here).
* No I/O. Every function is pure and unit-testable on synthetic data. The DB
  loader lives in ``monitor_loader.py`` and only assembles the typed inputs.
* No lookahead. Callers pass only price observations with ``dt <= eval_as_of``;
  ``compute_report`` asserts this and refuses otherwise.
* No silent forward-fill. When a held name has no price on a trading day, a
  ``MissingPrice`` event is recorded. If ``forward_fill`` is enabled the last
  observed price is carried AND the carry is flagged on the NAV point and in
  the event log — never hidden.
* Total return uses ``adj_close`` (dividend/split adjusted) where available and
  records ``used_adj_close`` per position; price return uses raw ``close``.
* Every reported figure is paired, in the report, with one of three evidence
  states by the caller: VERIFIED (computed from data), INFERRED (assumption,
  e.g. cost bps), or MISSING (not yet measurable / data absent).

Builds on ``paper_trade.evaluate`` (the existing single-point P&L-vs-cash
evaluator) — this module adds the NAV time-series, benchmark framing,
attribution, signal-bucket diagnostics, and cost estimates around it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, getcontext
from typing import Literal

# Wide precision for chained Decimal multiplies/divides (vol, drawdown, sqrt).
getcontext().prec = 40

_ZERO = Decimal("0")
_ONE = Decimal("1")
_HUNDRED = Decimal("100")
# Trading days per year for annualising realised volatility (ASX convention).
_TRADING_DAYS_YEAR = Decimal("252")

EvidenceState = Literal["VERIFIED", "INFERRED", "MISSING"]


# ---------------------------------------------------------------------------
# Inputs (assembled by monitor_loader; plain typed data — no DB types leak in)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Position:
    """One entered paper position as of the build date.

    ``qty`` is the (possibly fractional) share count from proposed_trades.
    ``entry_close`` is the raw close at the build date (== reference_price).
    ``entry_adj_close`` is the adjusted close at the build date; the total-return
    anchor. ``target_weight`` is the fraction of capital from target_allocations.
    """

    symbol: str
    sector: str | None
    qty: Decimal
    entry_close: Decimal
    entry_adj_close: Decimal
    target_weight: Decimal
    target_aud: Decimal
    signal_label: str
    prob_up: Decimal
    expected_return: Decimal


@dataclass(frozen=True)
class PriceBar:
    """A single (close, adj_close) observation. adj_close may be None."""

    close: Decimal
    adj_close: Decimal | None


# price_panel[dt][symbol] -> PriceBar. Caller guarantees every dt <= eval_as_of.
PricePanel = dict[date, dict[str, PriceBar]]


@dataclass(frozen=True)
class BenchmarkSeries:
    """Benchmark levels over the evaluation window.

    ``available`` is False when no benchmark source produced data (e.g.
    AXJO.INDX not yet ingested). ``source`` and ``note`` document provenance
    so the report can flag the gap rather than fabricate a comparison.
    ``levels`` maps trading date -> index/proxy level (entry-date inclusive).
    """

    available: bool
    source: str
    note: str
    levels: dict[date, Decimal] = field(default_factory=dict)


@dataclass(frozen=True)
class CostModel:
    """Configurable transaction-cost assumptions (INFERRED, not measured).

    Applied to traded notional = sum(abs(delta_aud)). Defaults are deliberately
    conservative placeholders for a retail ASX account; override per broker.
    """

    commission_bps: Decimal = Decimal("8")
    slippage_bps: Decimal = Decimal("5")


@dataclass(frozen=True)
class MonitorInputs:
    """Everything ``compute_report`` needs for one run. Pure data."""

    run_id: int
    run_as_of: date          # build / entry date
    signals_as_of: date
    eval_as_of: date         # report date (>= run_as_of); no price dt may exceed it
    model_version: str
    capital_aud: Decimal
    cash_aud: Decimal
    positions: list[Position]
    price_panel: PricePanel
    benchmark: BenchmarkSeries
    total_traded_aud: Decimal   # sum abs(delta_aud) over buy/sell trades
    cost_model: CostModel = field(default_factory=CostModel)
    forward_fill: bool = False
    prob_up_edges: tuple[Decimal, ...] = (
        Decimal("0.55"), Decimal("0.65"), Decimal("0.75"), Decimal("0.85"),
    )
    expected_return_edges: tuple[Decimal, ...] = (
        Decimal("0"), Decimal("0.05"), Decimal("0.5"), Decimal("2"),
    )


# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MissingPrice:
    """A held symbol had no price on a trading day in the window."""

    symbol: str
    dt: date
    detail: str  # 'no_bar' | 'forward_filled' | 'no_adj_close'


@dataclass(frozen=True)
class PositionPerf:
    symbol: str
    sector: str | None
    weight: Decimal
    entry_close: Decimal
    last_close: Decimal | None
    last_dt: date | None
    price_return_pct: Decimal | None     # close-based
    total_return_pct: Decimal | None     # adj_close-based (dividend/split adj)
    pnl_aud: Decimal | None              # price-based MV - entry cost
    contribution_pct: Decimal | None     # contribution to portfolio return
    signal_label: str
    prob_up: Decimal
    expected_return: Decimal
    used_adj_close: bool
    priced: bool


@dataclass(frozen=True)
class NavPoint:
    dt: date
    invested_mv_aud: Decimal
    cash_aud: Decimal
    total_nav_aud: Decimal
    cum_return_pct: Decimal
    daily_return_pct: Decimal | None
    n_priced: int
    n_missing: int
    forward_filled: bool
    benchmark_level: Decimal | None
    benchmark_cum_return_pct: Decimal | None


@dataclass(frozen=True)
class BucketPerf:
    label: str
    n: int
    n_priced: int
    mean_total_return_pct: Decimal | None
    hit_rate_pct: Decimal | None
    total_pnl_aud: Decimal


@dataclass(frozen=True)
class CostEstimate:
    traded_notional_aud: Decimal
    commission_bps: Decimal
    slippage_bps: Decimal
    est_cost_aud: Decimal
    est_cost_bps_of_capital: Decimal


@dataclass(frozen=True)
class PerfReport:
    # provenance
    run_id: int
    run_as_of: date
    signals_as_of: date
    eval_as_of: date
    model_version: str
    capital_aud: Decimal
    cash_aud: Decimal
    n_positions: int

    # measurability gate
    measurable: bool
    n_forward_days: int
    measurability_note: str

    # headline performance (None when not measurable)
    total_nav_aud: Decimal | None
    price_return_pct: Decimal | None      # NAV-based (close)
    total_return_pct: Decimal | None      # dividend-adjusted (adj_close)
    benchmark_available: bool
    benchmark_source: str
    benchmark_return_pct: Decimal | None
    benchmark_relative_pct: Decimal | None

    # baselines / selection quality
    equal_weight_return_pct: Decimal | None
    model_weight_return_pct: Decimal | None

    # risk / quality
    hit_rate_pct: Decimal | None
    avg_winner_pct: Decimal | None
    avg_loser_pct: Decimal | None
    payoff_ratio: Decimal | None
    max_drawdown_pct: Decimal | None
    realised_vol_pct: Decimal | None
    turnover_pct: Decimal

    # cost
    cost: CostEstimate

    # detail
    nav_series: list[NavPoint]
    positions: list[PositionPerf]
    sector_attribution: list[BucketPerf]
    by_signal_label: list[BucketPerf]
    by_prob_up_bucket: list[BucketPerf]
    by_expected_return_bucket: list[BucketPerf]
    missing_events: list[MissingPrice]


# ---------------------------------------------------------------------------
# Decimal helpers
# ---------------------------------------------------------------------------


def _q2(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.01"))


def _q6(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.000001"))


def _pct(x: Decimal) -> Decimal:
    return _q2(x * _HUNDRED)


def _mean(xs: list[Decimal]) -> Decimal | None:
    if not xs:
        return None
    return sum(xs, _ZERO) / Decimal(len(xs))


def _sample_stdev(xs: list[Decimal]) -> Decimal | None:
    """Sample standard deviation (n-1). None if fewer than 2 points."""
    n = len(xs)
    if n < 2:
        return None
    m = sum(xs, _ZERO) / Decimal(n)
    var = sum(((x - m) ** 2 for x in xs), _ZERO) / Decimal(n - 1)
    return var.sqrt()


# ---------------------------------------------------------------------------
# Core computations (pure)
# ---------------------------------------------------------------------------


def trading_dates(panel: PricePanel, entry: date, eval_as_of: date) -> list[date]:
    """Sorted trading dates in [entry, eval_as_of] that appear in the panel."""
    return sorted(d for d in panel if entry <= d <= eval_as_of)


def n_forward_trading_days(panel: PricePanel, entry: date, eval_as_of: date) -> int:
    """Trading dates strictly AFTER entry with at least one bar. The
    measurability driver: 0 means nothing has happened since entry yet."""
    return sum(1 for d in panel if entry < d <= eval_as_of and panel[d])


def _value_position(
    pos: Position,
    bar: PriceBar | None,
    carried: PriceBar | None,
) -> tuple[Decimal, bool, str | None]:
    """Return (market_value_aud, priced, missing_detail).

    Valuation rule (explicit, never silent):
      * bar present       -> qty * close, priced=True
      * bar absent, carry -> qty * carried.close, priced=True, detail='forward_filled'
      * bar absent, no carry -> qty * entry_close (cost), priced=False, detail='no_bar'
    """
    if bar is not None:
        return pos.qty * bar.close, True, None
    if carried is not None:
        return pos.qty * carried.close, True, "forward_filled"
    return pos.qty * pos.entry_close, False, "no_bar"


def build_nav_series(inp: MonitorInputs) -> tuple[list[NavPoint], list[MissingPrice]]:
    """NAV time series from entry to eval, with explicit missing-data accounting.

    The entry-date NAV equals capital by construction (invested at entry close +
    residual cash). Subsequent points reflect realised price moves. Forward-fill
    is applied only when ``inp.forward_fill`` is True and is always flagged.
    """
    dates = trading_dates(inp.price_panel, inp.run_as_of, inp.eval_as_of)
    nav: list[NavPoint] = []
    missing: list[MissingPrice] = []
    last_seen: dict[str, PriceBar] = {}
    prev_nav: Decimal | None = None
    bench0: Decimal | None = inp.benchmark.levels.get(inp.run_as_of)

    for d in dates:
        bars = inp.price_panel.get(d, {})
        invested = _ZERO
        n_priced = 0
        n_missing = 0
        ff_used = False
        for pos in inp.positions:
            bar = bars.get(pos.symbol)
            carry = last_seen.get(pos.symbol) if inp.forward_fill else None
            mv, priced, detail = _value_position(pos, bar, carry)
            invested += mv
            if bar is not None:
                last_seen[pos.symbol] = bar
                n_priced += 1
            else:
                n_missing += 1
                if detail == "forward_filled":
                    ff_used = True
                missing.append(MissingPrice(symbol=pos.symbol, dt=d, detail=detail or "no_bar"))
                if not priced:
                    # not priced and no carry -> still counts toward priced=False
                    pass
                elif detail == "forward_filled":
                    n_priced += 1
                    n_missing -= 1

        total_nav = invested + inp.cash_aud
        cum = (total_nav / inp.capital_aud - _ONE) if inp.capital_aud > _ZERO else _ZERO
        daily = None
        if prev_nav is not None and prev_nav > _ZERO:
            daily = _pct(total_nav / prev_nav - _ONE)
        bench_level = inp.benchmark.levels.get(d)
        bench_cum = None
        if bench_level is not None and bench0 is not None and bench0 > _ZERO:
            bench_cum = _pct(bench_level / bench0 - _ONE)

        nav.append(
            NavPoint(
                dt=d,
                invested_mv_aud=_q6(invested),
                cash_aud=_q6(inp.cash_aud),
                total_nav_aud=_q6(total_nav),
                cum_return_pct=_pct(cum),
                daily_return_pct=daily,
                n_priced=n_priced,
                n_missing=n_missing,
                forward_filled=ff_used,
                benchmark_level=bench_level,
                benchmark_cum_return_pct=bench_cum,
            )
        )
        prev_nav = total_nav
    return nav, missing


def position_perfs(inp: MonitorInputs) -> list[PositionPerf]:
    """Per-position performance at eval_as_of using the latest available bar
    on-or-before eval (no lookahead; panel is already bounded)."""
    dates = trading_dates(inp.price_panel, inp.run_as_of, inp.eval_as_of)
    # latest bar per symbol within the window
    latest: dict[str, tuple[date, PriceBar]] = {}
    for d in dates:
        for sym, bar in inp.price_panel[d].items():
            latest[sym] = (d, bar)

    # portfolio total NAV at eval (price-based) for contribution denominator
    total_pnl_all = _ZERO
    rows: list[PositionPerf] = []
    for pos in inp.positions:
        lb = latest.get(pos.symbol)
        if lb is None:
            rows.append(
                PositionPerf(
                    symbol=pos.symbol, sector=pos.sector, weight=_q6(pos.target_weight),
                    entry_close=pos.entry_close, last_close=None, last_dt=None,
                    price_return_pct=None, total_return_pct=None, pnl_aud=None,
                    contribution_pct=None, signal_label=pos.signal_label,
                    prob_up=pos.prob_up, expected_return=pos.expected_return,
                    used_adj_close=False, priced=False,
                )
            )
            continue
        ldt, bar = lb
        price_ret = (bar.close / pos.entry_close - _ONE) if pos.entry_close > _ZERO else _ZERO
        used_adj = bar.adj_close is not None and pos.entry_adj_close > _ZERO
        total_ret = (bar.adj_close / pos.entry_adj_close - _ONE) if used_adj else price_ret
        pnl = pos.qty * (bar.close - pos.entry_close)
        total_pnl_all += pnl
        rows.append(
            PositionPerf(
                symbol=pos.symbol, sector=pos.sector, weight=_q6(pos.target_weight),
                entry_close=pos.entry_close, last_close=bar.close, last_dt=ldt,
                price_return_pct=_pct(price_ret), total_return_pct=_pct(total_ret),
                pnl_aud=_q6(pnl), contribution_pct=None,
                signal_label=pos.signal_label, prob_up=pos.prob_up,
                expected_return=pos.expected_return, used_adj_close=used_adj, priced=True,
            )
        )

    # contribution = position pnl / capital (so contributions sum to portfolio price-return)
    out: list[PositionPerf] = []
    for r in rows:
        if r.pnl_aud is None or inp.capital_aud <= _ZERO:
            out.append(r)
        else:
            contrib = _pct(r.pnl_aud / inp.capital_aud)
            out.append(PositionPerf(**{**r.__dict__, "contribution_pct": contrib}))
    return out


def equal_vs_model_weight_return(
    perfs: list[PositionPerf], positions: list[Position]
) -> tuple[Decimal | None, Decimal | None]:
    """Selection-quality controls: equal-weight vs model (target) weight return,
    both over priced names only, using total return (adj_close)."""
    priced = [p for p in perfs if p.priced and p.total_return_pct is not None]
    if not priced:
        return None, None
    eq = _mean([p.total_return_pct for p in priced])
    wmap = {pos.symbol: pos.target_weight for pos in positions}
    wsum = sum((wmap.get(p.symbol, _ZERO) for p in priced), _ZERO)
    if wsum <= _ZERO:
        model = None
    else:
        model = sum((p.total_return_pct * wmap.get(p.symbol, _ZERO) for p in priced), _ZERO) / wsum
        model = _q2(model)
    return (_q2(eq) if eq is not None else None), model


def hit_rate_and_payoff(
    perfs: list[PositionPerf],
) -> tuple[Decimal | None, Decimal | None, Decimal | None, Decimal | None]:
    """(hit_rate_pct, avg_winner_pct, avg_loser_pct, payoff_ratio) on priced names."""
    rets = [p.total_return_pct for p in perfs if p.priced and p.total_return_pct is not None]
    if not rets:
        return None, None, None, None
    winners = [r for r in rets if r > _ZERO]
    losers = [r for r in rets if r < _ZERO]
    hit = _q2(Decimal(len(winners)) / Decimal(len(rets)) * _HUNDRED)
    avg_w = _q2(_mean(winners)) if winners else None
    avg_l = _q2(_mean(losers)) if losers else None
    payoff = None
    if avg_w is not None and avg_l is not None and avg_l != _ZERO:
        payoff = _q2(abs(avg_w / avg_l))
    return hit, avg_w, avg_l, payoff


def max_drawdown_pct(nav: list[NavPoint]) -> Decimal | None:
    """Peak-to-trough max drawdown on the NAV path, as a (negative) percent."""
    if len(nav) < 2:
        return None
    peak = nav[0].total_nav_aud
    mdd = _ZERO
    for pt in nav:
        if pt.total_nav_aud > peak:
            peak = pt.total_nav_aud
        if peak > _ZERO:
            dd = pt.total_nav_aud / peak - _ONE
            if dd < mdd:
                mdd = dd
    return _pct(mdd)


def realised_vol_pct(nav: list[NavPoint]) -> Decimal | None:
    """Annualised realised volatility from daily NAV returns (None if <2 returns)."""
    daily = [pt.daily_return_pct / _HUNDRED for pt in nav if pt.daily_return_pct is not None]
    sd = _sample_stdev(daily)
    if sd is None:
        return None
    return _pct(sd * _TRADING_DAYS_YEAR.sqrt())


def turnover_pct(total_traded_aud: Decimal, capital_aud: Decimal) -> Decimal:
    """One-way turnover at the build = traded notional / capital."""
    if capital_aud <= _ZERO:
        return _ZERO
    return _pct(total_traded_aud / capital_aud)


def estimate_costs(inp: MonitorInputs) -> CostEstimate:
    bps = inp.cost_model.commission_bps + inp.cost_model.slippage_bps
    cost = inp.total_traded_aud * bps / Decimal("10000")
    cost_bps_cap = (
        cost / inp.capital_aud * Decimal("10000") if inp.capital_aud > _ZERO else _ZERO
    )
    return CostEstimate(
        traded_notional_aud=_q6(inp.total_traded_aud),
        commission_bps=inp.cost_model.commission_bps,
        slippage_bps=inp.cost_model.slippage_bps,
        est_cost_aud=_q6(cost),
        est_cost_bps_of_capital=_q2(cost_bps_cap),
    )


def _bucket(perfs: list[PositionPerf], label: str) -> BucketPerf:
    priced = [p for p in perfs if p.priced and p.total_return_pct is not None]
    rets = [p.total_return_pct for p in priced]
    pnl = sum((p.pnl_aud for p in perfs if p.pnl_aud is not None), _ZERO)
    hit = None
    if rets:
        winners = sum(1 for r in rets if r > _ZERO)
        hit = _q2(Decimal(winners) / Decimal(len(rets)) * _HUNDRED)
    return BucketPerf(
        label=label, n=len(perfs), n_priced=len(priced),
        mean_total_return_pct=_q2(_mean(rets)) if rets else None,
        hit_rate_pct=hit, total_pnl_aud=_q6(pnl),
    )


def sector_attribution(perfs: list[PositionPerf]) -> list[BucketPerf]:
    by: dict[str, list[PositionPerf]] = {}
    for p in perfs:
        by.setdefault(p.sector or "Unknown", []).append(p)
    return [_bucket(v, k) for k, v in sorted(by.items())]


def by_signal_label(perfs: list[PositionPerf]) -> list[BucketPerf]:
    order = ["STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL"]
    by: dict[str, list[PositionPerf]] = {}
    for p in perfs:
        by.setdefault(p.signal_label, []).append(p)
    keys = [k for k in order if k in by] + sorted(k for k in by if k not in order)
    return [_bucket(by[k], k) for k in keys]


def _edge_label(edges: tuple[Decimal, ...], idx: int) -> str:
    if idx == 0:
        return f"<{edges[0]}"
    if idx == len(edges):
        return f">={edges[-1]}"
    return f"{edges[idx - 1]}-{edges[idx]}"


def _bucket_by_value(
    perfs: list[PositionPerf], edges: tuple[Decimal, ...], value
) -> list[BucketPerf]:
    groups: dict[int, list[PositionPerf]] = {}
    for p in perfs:
        v = value(p)
        idx = 0
        while idx < len(edges) and v >= edges[idx]:
            idx += 1
        groups.setdefault(idx, []).append(p)
    return [_bucket(groups[i], _edge_label(edges, i)) for i in sorted(groups)]


def by_prob_up_bucket(perfs: list[PositionPerf], edges: tuple[Decimal, ...]) -> list[BucketPerf]:
    return _bucket_by_value(perfs, edges, lambda p: p.prob_up)


def by_expected_return_bucket(
    perfs: list[PositionPerf], edges: tuple[Decimal, ...]
) -> list[BucketPerf]:
    return _bucket_by_value(perfs, edges, lambda p: p.expected_return)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def compute_report(inp: MonitorInputs) -> PerfReport:
    """Assemble the full PerfReport from typed inputs. Pure.

    Enforces no-lookahead (raises ValueError if any price dt > eval_as_of) and
    cleanly degrades to a 'not yet measurable' report when no forward trading
    day exists — the honest state for a brand-new build.
    """
    if inp.eval_as_of < inp.run_as_of:
        raise ValueError("eval_as_of precedes run_as_of")
    for d in inp.price_panel:
        if d > inp.eval_as_of:
            raise ValueError(
                f"lookahead: price panel contains dt {d} > eval_as_of {inp.eval_as_of}"
            )

    fwd = n_forward_trading_days(inp.price_panel, inp.run_as_of, inp.eval_as_of)
    turnover = turnover_pct(inp.total_traded_aud, inp.capital_aud)
    cost = estimate_costs(inp)

    if fwd == 0:
        note = (
            f"Not yet measurable: 0 forward trading days since entry "
            f"{inp.run_as_of} (latest priced date <= {inp.eval_as_of} is the entry "
            f"date or earlier). Performance is undefined until prices accrue."
        )
        return PerfReport(
            run_id=inp.run_id, run_as_of=inp.run_as_of, signals_as_of=inp.signals_as_of,
            eval_as_of=inp.eval_as_of, model_version=inp.model_version,
            capital_aud=inp.capital_aud, cash_aud=inp.cash_aud, n_positions=len(inp.positions),
            measurable=False, n_forward_days=0, measurability_note=note,
            total_nav_aud=None, price_return_pct=None, total_return_pct=None,
            benchmark_available=inp.benchmark.available, benchmark_source=inp.benchmark.source,
            benchmark_return_pct=None, benchmark_relative_pct=None,
            equal_weight_return_pct=None, model_weight_return_pct=None,
            hit_rate_pct=None, avg_winner_pct=None, avg_loser_pct=None, payoff_ratio=None,
            max_drawdown_pct=None, realised_vol_pct=None, turnover_pct=turnover, cost=cost,
            nav_series=[], positions=[], sector_attribution=[], by_signal_label=[],
            by_prob_up_bucket=[], by_expected_return_bucket=[], missing_events=[],
        )

    nav, missing = build_nav_series(inp)
    perfs = position_perfs(inp)
    last = nav[-1]
    price_return = last.cum_return_pct

    # dividend-adjusted (total-return) portfolio return = capital-weighted position TR
    tr_terms: list[Decimal] = []
    inv_weight_sum = _ZERO
    for pos, pf in zip(inp.positions, _align(perfs, inp.positions), strict=False):
        if pf is not None and pf.total_return_pct is not None:
            w = pos.target_aud
            inv_weight_sum += w
            tr_terms.append(pf.total_return_pct * w)
    total_return = (
        _q2(sum(tr_terms, _ZERO) / inv_weight_sum) if inv_weight_sum > _ZERO else None
    )

    eq_ret, model_ret = equal_vs_model_weight_return(perfs, inp.positions)
    hit, avg_w, avg_l, payoff = hit_rate_and_payoff(perfs)
    mdd = max_drawdown_pct(nav)
    vol = realised_vol_pct(nav)

    bench_ret = last.benchmark_cum_return_pct if inp.benchmark.available else None
    bench_rel = None
    if bench_ret is not None:
        bench_rel = _q2(price_return - bench_ret)

    return PerfReport(
        run_id=inp.run_id, run_as_of=inp.run_as_of, signals_as_of=inp.signals_as_of,
        eval_as_of=inp.eval_as_of, model_version=inp.model_version,
        capital_aud=inp.capital_aud, cash_aud=inp.cash_aud, n_positions=len(inp.positions),
        measurable=True, n_forward_days=fwd,
        measurability_note=f"{fwd} forward trading day(s) since entry {inp.run_as_of}.",
        total_nav_aud=last.total_nav_aud, price_return_pct=price_return,
        total_return_pct=total_return,
        benchmark_available=inp.benchmark.available, benchmark_source=inp.benchmark.source,
        benchmark_return_pct=bench_ret, benchmark_relative_pct=bench_rel,
        equal_weight_return_pct=eq_ret, model_weight_return_pct=model_ret,
        hit_rate_pct=hit, avg_winner_pct=avg_w, avg_loser_pct=avg_l, payoff_ratio=payoff,
        max_drawdown_pct=mdd, realised_vol_pct=vol, turnover_pct=turnover, cost=cost,
        nav_series=nav, positions=perfs, sector_attribution=sector_attribution(perfs),
        by_signal_label=by_signal_label(perfs),
        by_prob_up_bucket=by_prob_up_bucket(perfs, inp.prob_up_edges),
        by_expected_return_bucket=by_expected_return_bucket(perfs, inp.expected_return_edges),
        missing_events=missing,
    )


def _align(perfs: list[PositionPerf], positions: list[Position]) -> list[PositionPerf | None]:
    """Map perfs back to positions order by symbol (perfs preserve order already,
    but be explicit so total-return weighting can't silently misalign)."""
    by_sym = {p.symbol: p for p in perfs}
    return [by_sym.get(pos.symbol) for pos in positions]
