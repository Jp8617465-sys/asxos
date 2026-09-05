"""Reproducible, cost-aware, Decimal-only evaluation harness.

One hypothesis is implemented — cross-sectional 12-1 momentum, monthly
rebalance, top-decile equal weight, per-side transaction cost — because the
Stage 2 exit gate asks for ONE hypothesis reproducible from raw data through
evaluation, with failed variants visible. Breadth is Stage 3's problem.

Determinism is the property under test: the evaluation is a pure function of
the panel and the parameters, every figure is a `Decimal` quantised to six
places, ties are broken by symbol, and the output is JSON-native so its hash
is stable across processes. Two runs over the same panel MUST hash
identically; the CLI checks exactly that.

What this deliberately does not do: claim alpha. The live panel starts on
2025-01-02, so after a 252-session lookback there are a handful of rebalance
dates. The result reports its own sample size and carries a walk-forward
split so a reader can see in-sample and holdout side by side — and the
`alpha_claim` on the run is "none".
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_EVEN, Decimal
from typing import Final

from asxos.domain.results_review.contracts import hash_document_payload

Q6: Final = Decimal("0.000001")
_MOM_LONG_TD: Final[int] = 252
_MOM_SKIP_TD: Final[int] = 21


class HarnessError(RuntimeError):
    """The panel cannot support the requested evaluation. Reported, not hidden."""


def q(value: Decimal) -> Decimal:
    return value.quantize(Q6, rounding=ROUND_HALF_EVEN)


@dataclass(frozen=True)
class EvaluationResult:
    payload: dict[str, object]

    @property
    def hash(self) -> str:
        return hash_document_payload(self.payload)


def panel_hash(panel: dict[str, list[tuple[date, Decimal]]]) -> str:
    """Hash of the raw inputs, so a run records exactly which data it saw."""
    flat = {
        sym: [[d.isoformat(), format(px, "f")] for d, px in sorted(series)]
        for sym, series in sorted(panel.items())
    }
    return hash_document_payload({"panel": flat})


def _month_ends(dates: list[date]) -> list[date]:
    """Last trading date of each calendar month present in `dates` (sorted)."""
    ends: list[date] = []
    for i, d in enumerate(dates):
        nxt = dates[i + 1] if i + 1 < len(dates) else None
        if nxt is None or (nxt.year, nxt.month) != (d.year, d.month):
            ends.append(d)
    return ends


def _momentum(series: list[Decimal], idx: int) -> Decimal | None:
    """12-1 momentum at position `idx` of an ascending adj_close series."""
    if idx - _MOM_LONG_TD < 0:
        return None
    recent = series[idx - _MOM_SKIP_TD]
    old = series[idx - _MOM_LONG_TD]
    if old <= 0 or recent <= 0:
        return None
    return recent / old - Decimal(1)


def evaluate_momentum_12_1(
    panel: dict[str, list[tuple[date, Decimal]]],
    *,
    horizon_trading_days: int = 21,
    cost_bps_per_side: Decimal = Decimal("25"),
    top_fraction: Decimal = Decimal("0.1"),
    min_symbols_per_date: int = 20,
) -> EvaluationResult:
    """Evaluate top-decile 12-1 momentum, equal weight, monthly, after costs.

    `panel` maps symbol -> ascending (date, adj_close). Symbols with gaps are
    aligned on the union calendar; a symbol missing a price on a rebalance
    date is simply not ranked that month.
    """
    if not panel:
        raise HarnessError("empty panel")
    for sym, series in panel.items():
        for _, px in series:
            if isinstance(px, float):
                raise HarnessError(f"float price in panel for {sym}")

    calendar = sorted({d for series in panel.values() for d, _ in series})
    by_symbol = {sym: dict(series) for sym, series in panel.items()}
    rebalances = [d for d in _month_ends(calendar) if calendar.index(d) >= _MOM_LONG_TD]
    if not rebalances:
        raise HarnessError(
            f"panel too short: {len(calendar)} sessions, need > {_MOM_LONG_TD} for one rebalance"
        )

    periods: list[dict[str, object]] = []
    prev_weights: dict[str, Decimal] = {}
    cost_rate = cost_bps_per_side / Decimal(10000)

    for rb in rebalances:
        i = calendar.index(rb)
        if i + horizon_trading_days >= len(calendar):
            break  # no forward window yet — not a failure, just not evaluable
        fwd = calendar[i + horizon_trading_days]
        scored: list[tuple[str, Decimal]] = []
        for sym in sorted(by_symbol):
            px_map = by_symbol[sym]
            if rb not in px_map or fwd not in px_map:
                continue
            series_dates = [d for d in calendar if d in px_map]
            try:
                idx = series_dates.index(rb)
            except ValueError:
                continue
            closes = [px_map[d] for d in series_dates]
            m = _momentum(closes, idx)
            if m is not None:
                scored.append((sym, m))
        if len(scored) < min_symbols_per_date:
            periods.append({
                "rebalance": rb.isoformat(), "forward": fwd.isoformat(),
                "status": "skipped_thin", "ranked": len(scored),
            })
            continue
        scored.sort(key=lambda t: (-t[1], t[0]))
        n_top = max(1, int(Decimal(len(scored)) * top_fraction))
        chosen = [sym for sym, _ in scored[:n_top]]
        w = q(Decimal(1) / Decimal(n_top))
        weights = dict.fromkeys(chosen, w)

        gross = Decimal(0)
        for sym in chosen:
            gross += weights[sym] * (by_symbol[sym][fwd] / by_symbol[sym][rb] - Decimal(1))
        universe = set(prev_weights) | set(weights)
        turnover = sum(
            abs(weights.get(s, Decimal(0)) - prev_weights.get(s, Decimal(0))) for s in universe
        ) / Decimal(2)
        cost = turnover * Decimal(2) * cost_rate
        net = gross - cost
        periods.append({
            "rebalance": rb.isoformat(), "forward": fwd.isoformat(),
            "status": "evaluated", "ranked": len(scored), "held": n_top,
            "gross_return": format(q(gross), "f"),
            "turnover_one_way": format(q(turnover), "f"),
            "cost": format(q(cost), "f"),
            "net_return": format(q(net), "f"),
            "top": chosen[:5],
        })
        prev_weights = weights

    evaluated = [p for p in periods if p["status"] == "evaluated"]
    if not evaluated:
        raise HarnessError("no evaluable rebalance period: every month was thin or lacked a forward window")

    def _mean(key: str, rows: list[dict[str, object]]) -> str:
        vals = [Decimal(str(r[key])) for r in rows]
        return format(q(sum(vals, Decimal(0)) / Decimal(len(vals))), "f") if vals else "0"

    half = max(1, len(evaluated) // 2)
    train, holdout = evaluated[:half], evaluated[half:]
    payload: dict[str, object] = {
        "harness": "momentum_12_1/v1",
        "parameters": {
            "horizon_trading_days": horizon_trading_days,
            "cost_bps_per_side": format(cost_bps_per_side, "f"),
            "top_fraction": format(top_fraction, "f"),
            "min_symbols_per_date": min_symbols_per_date,
            "lookback_sessions": _MOM_LONG_TD,
            "skip_sessions": _MOM_SKIP_TD,
        },
        "calendar": {"first": calendar[0].isoformat(), "last": calendar[-1].isoformat(),
                     "sessions": len(calendar)},
        "symbols_in_panel": len(panel),
        "periods": periods,
        "n_evaluated": len(evaluated),
        "mean_net_return_per_period": _mean("net_return", evaluated),
        "mean_gross_return_per_period": _mean("gross_return", evaluated),
        "walk_forward": {
            "train_periods": len(train), "holdout_periods": len(holdout),
            "train_mean_net": _mean("net_return", train),
            "holdout_mean_net": _mean("net_return", holdout) if holdout else None,
            "note": "single chronological split; a handful of periods is a process check, not a test of edge",
        },
        "multiple_testing": {"variants_in_this_run": 1},
    }
    return EvaluationResult(payload=payload)
