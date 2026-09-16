"""Cross-sectional value-to-price evaluator — the test the sealed hypothesis names.

Sibling of `evaluate_momentum_12_1`, and deliberately the same shape: pure
function of its inputs, Decimal-only, every figure quantised to six places,
ties broken by symbol, JSON-native output so the hash is stable across
processes. Two runs over the same inputs MUST hash identically.

ONE STRUCTURAL DIFFERENCE from the momentum harness. Momentum is computed FROM
the price panel, so the panel is the only input. Value-to-price cannot be: it
comes from the residual-income model replayed at each cutoff against
point-in-time fundamentals. So `scores` is supplied, and `panel` supplies only
the returns. This keeps the valuation code and the evaluation code apart —
the evaluator cannot quietly change how a name was valued.

WHAT IS JUDGED, AND WHY IT IS THE LADDER. The primary endpoint is the mean
across cutoffs of the per-cutoff cross-sectional Spearman rank correlation
between value-to-price and forward return. Monotonicity is judged on the whole
quintile ladder rather than on the top quintile or a top-minus-bottom spread,
because Model A's failure was precisely an inverted ladder under a strong
headline: its STRONG_BUY bucket returned -0.09% at 21d while HOLD returned
+5.07%. A test that reads only the extreme bucket cannot see that.

THIS EVALUATOR DOES NOT DECIDE ANYTHING. It reports statistics and a verdict
label computed against thresholds fixed here. The consequence of that verdict
is the pre-committed `RESPONSE_RULE` in `vp.py`, applied by a human-visible
step — not by this module.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Final

from asxos.domain.research.registry.harness import HarnessError, q
from asxos.domain.results_review.contracts import hash_document_payload

#: A ladder is called monotone only if the rank correlation between quintile
#: index and that quintile's mean forward return is at least this strong. With
#: five buckets a perfect ladder scores 1.0, so 0.9 admits one adjacent
#: inversion and no more. Fixed here, before the run, for the same reason the
#: hypothesis fixes its primary endpoint.
LADDER_MONOTONE_MIN: Final[Decimal] = Decimal("0.9")

VERDICT_POSITIVE: Final[str] = "positive_monotonic"
VERDICT_NEGATIVE: Final[str] = "negative_monotonic"
VERDICT_NULL: Final[str] = "null"


def _avg_ranks(values: list[Decimal]) -> list[Decimal]:
    """Ranks with ties averaged — the standard Spearman tie correction."""
    order = sorted(range(len(values)), key=lambda i: (values[i], i))
    ranks = [Decimal(0)] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        # Ranks are 1-based; a tie group shares the mean of its positions.
        shared = (Decimal(i + 1) + Decimal(j + 1)) / Decimal(2)
        for k in range(i, j + 1):
            ranks[order[k]] = shared
        i = j + 1
    return ranks


def _pearson(xs: list[Decimal], ys: list[Decimal]) -> Decimal | None:
    """Pearson correlation, Decimal-only. None when either series is constant."""
    n = Decimal(len(xs))
    if n < 2:
        return None
    mx, my = sum(xs, Decimal(0)) / n, sum(ys, Decimal(0)) / n
    sxy = sum(((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True)), Decimal(0))
    sxx = sum(((x - mx) ** 2 for x in xs), Decimal(0))
    syy = sum(((y - my) ** 2 for y in ys), Decimal(0))
    if sxx <= 0 or syy <= 0:
        return None
    return sxy / (sxx.sqrt() * syy.sqrt())


def spearman(xs: list[Decimal], ys: list[Decimal]) -> Decimal | None:
    """Rank correlation with ties averaged."""
    if len(xs) != len(ys):
        raise HarnessError("spearman: series length mismatch")
    return _pearson(_avg_ranks(xs), _avg_ranks(ys))


def median(values: list[Decimal]) -> Decimal:
    """Exact median, Decimal-only. The ladder's central statistic, not the mean.

    Cross-sectional equity returns are violently right-tailed: measured on this
    panel at 2025-03-31, the mean 126-session return across all 1,782 priced
    names was +632% against a median of +13.9%, with a maximum of +833,230% on a
    stock quoted at A$0.0001. A bucket mean under that tail reports the largest
    quotation artefact in the bucket, not the bucket.
    """
    ordered = sorted(values)
    n = len(ordered)
    if n == 0:
        raise HarnessError("median of an empty bucket")
    mid = n // 2
    if n % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / Decimal(2)


def _quintile_bounds(n: int, buckets: int) -> list[tuple[int, int]]:
    """Contiguous, near-equal slices of a sorted list — no name is dropped."""
    edges = [(n * b) // buckets for b in range(buckets + 1)]
    return [(edges[b], edges[b + 1]) for b in range(buckets)]


def evaluate_value_to_price(
    scores: dict[date, dict[str, Decimal]],
    panel: dict[str, list[tuple[date, Decimal]]],
    *,
    horizon_trading_days: int,
    cost_bps_per_side: Decimal = Decimal("25"),
    buckets: int = 5,
    min_symbols_per_cutoff: int = 50,
    marked_book: dict[str, str] | None = None,
    screen: str = "none declared",
) -> dict[str, object]:
    """Evaluate the V/P ladder across cutoffs. Returns a JSON-native payload.

    `scores` maps cutoff date -> symbol -> value_to_price (value / price at that
    cutoff, computed point-in-time). `panel` maps symbol -> ascending
    (date, close). `marked_book` maps symbol -> reason for instruments whose
    accounting makes the model mis-specified (LICs, LITs, A-REITs); they are
    FLAGGED and reported separately, never silently dropped — excluding them
    after seeing a candidate set would be a choice made on the data.
    """
    if not scores:
        raise HarnessError("no cutoffs supplied")
    for sym, series in panel.items():
        for _, px in series:
            if isinstance(px, float):
                raise HarnessError(f"float price in panel for {sym}")

    marked = marked_book or {}
    calendar = sorted({d for series in panel.values() for d, _ in series})
    by_symbol = {sym: dict(series) for sym, series in panel.items()}
    cost_rate = cost_bps_per_side / Decimal(10000)
    # Long the cheap quintile, funded at cost: two sides in, two sides out.
    round_trip_cost = cost_rate * Decimal(4)

    cutoff_rows: list[dict[str, object]] = []

    for cutoff in sorted(scores):
        if cutoff not in calendar:
            cutoff_rows.append({
                "cutoff": cutoff.isoformat(), "status": "skipped_not_a_session",
            })
            continue
        i = calendar.index(cutoff)
        if i + horizon_trading_days >= len(calendar):
            cutoff_rows.append({
                "cutoff": cutoff.isoformat(), "status": "skipped_no_forward_window",
                "sessions_available": len(calendar) - i - 1,
                "sessions_required": horizon_trading_days,
            })
            continue
        forward = calendar[i + horizon_trading_days]

        paired: list[tuple[str, Decimal, Decimal]] = []
        no_forward_price = 0
        for sym in sorted(scores[cutoff]):
            px_map = by_symbol.get(sym)
            if px_map is None or cutoff not in px_map:
                continue
            if forward not in px_map:
                # Priced at the cutoff, gone by the forward date. Delisting or a
                # data gap — indistinguishable without delisted_date, which
                # rs_security_master does not carry. Counted, never imputed.
                no_forward_price += 1
                continue
            p0, p1 = px_map[cutoff], px_map[forward]
            if p0 <= 0:
                continue
            paired.append((sym, scores[cutoff][sym], p1 / p0 - Decimal(1)))

        if len(paired) < min_symbols_per_cutoff:
            cutoff_rows.append({
                "cutoff": cutoff.isoformat(), "status": "skipped_thin",
                "paired": len(paired), "required": min_symbols_per_cutoff,
                "dropped_no_forward_price": no_forward_price,
            })
            continue

        vps = [vp for _, vp, _ in paired]
        rets = [r for _, _, r in paired]
        rho = spearman(vps, rets)

        # Ladder: sort ascending by V/P so the LAST bucket is the cheapest.
        ordered = sorted(paired, key=lambda t: (t[1], t[0]))
        ladder: list[dict[str, object]] = []
        for b, (lo, hi) in enumerate(_quintile_bounds(len(ordered), buckets)):
            slice_ = ordered[lo:hi]
            if not slice_:
                continue
            rets_b = [r for _, _, r in slice_]
            med_ret = median(rets_b)
            mean_ret = sum(rets_b, Decimal(0)) / Decimal(len(slice_))
            ladder.append({
                "bucket": b + 1,
                "n": len(slice_),
                # Median on both axes: a bucket's mean V/P is as tail-dominated as
                # its mean return (a single 94x artefact moves it by orders).
                "median_value_to_price": format(q(median([vp for _, vp, _ in slice_])), "f"),
                "median_forward_return": format(q(med_ret), "f"),
                "median_forward_return_net": format(q(med_ret - round_trip_cost), "f"),
                # Reported for comparison only. NOT the ladder statistic.
                "mean_forward_return": format(q(mean_ret), "f"),
            })

        ladder_rho = spearman(
            [Decimal(row["bucket"]) for row in ladder],  # type: ignore[arg-type]
            [Decimal(str(row["median_forward_return"])) for row in ladder],
        )
        cheap, dear = ladder[-1], ladder[0]
        spread = (
            Decimal(str(cheap["median_forward_return"]))
            - Decimal(str(dear["median_forward_return"]))
        )

        flagged = [s for s, _, _ in paired if s in marked]
        cutoff_rows.append({
            "cutoff": cutoff.isoformat(), "forward": forward.isoformat(),
            "status": "evaluated",
            "paired": len(paired),
            "dropped_no_forward_price": no_forward_price,
            "spearman_vp_vs_forward_return": None if rho is None else format(q(rho), "f"),
            "ladder": ladder,
            "ladder_rank_correlation": None if ladder_rho is None else format(q(ladder_rho), "f"),
            "cheapest_minus_dearest": format(q(spread), "f"),
            "cheapest_minus_dearest_net": format(q(spread - round_trip_cost), "f"),
            "marked_book_in_sample": len(flagged),
        })

    evaluated = [r for r in cutoff_rows if r["status"] == "evaluated"]
    if not evaluated:
        raise HarnessError(
            "no evaluable cutoff: every cutoff was thin, not a session, or lacked "
            f"a {horizon_trading_days}-session forward window"
        )

    rhos = [
        Decimal(str(r["spearman_vp_vs_forward_return"]))
        for r in evaluated
        if r["spearman_vp_vs_forward_return"] is not None
    ]
    mean_rho = sum(rhos, Decimal(0)) / Decimal(len(rhos)) if rhos else None
    ladder_rhos = [
        Decimal(str(r["ladder_rank_correlation"]))
        for r in evaluated
        if r["ladder_rank_correlation"] is not None
    ]
    mean_ladder_rho = (
        sum(ladder_rhos, Decimal(0)) / Decimal(len(ladder_rhos)) if ladder_rhos else None
    )
    spreads = [Decimal(str(r["cheapest_minus_dearest_net"])) for r in evaluated]
    mean_spread = sum(spreads, Decimal(0)) / Decimal(len(spreads))

    verdict = VERDICT_NULL
    if mean_rho is not None and mean_ladder_rho is not None:
        if mean_rho > 0 and mean_ladder_rho >= LADDER_MONOTONE_MIN and mean_spread > 0:
            verdict = VERDICT_POSITIVE
        elif mean_rho < 0 and mean_ladder_rho <= -LADDER_MONOTONE_MIN and mean_spread < 0:
            verdict = VERDICT_NEGATIVE

    half = max(1, len(evaluated) // 2)
    train, holdout = evaluated[:half], evaluated[half:]

    def _mean_rho_of(rows: list[dict[str, object]]) -> str | None:
        vals = [
            Decimal(str(r["spearman_vp_vs_forward_return"]))
            for r in rows
            if r["spearman_vp_vs_forward_return"] is not None
        ]
        return format(q(sum(vals, Decimal(0)) / Decimal(len(vals))), "f") if vals else None

    return {
        "harness": "value_to_price/v1",
        "parameters": {
            "horizon_trading_days": horizon_trading_days,
            "cost_bps_per_side": format(cost_bps_per_side, "f"),
            "buckets": buckets,
            "min_symbols_per_cutoff": min_symbols_per_cutoff,
            "ladder_monotone_min": format(LADDER_MONOTONE_MIN, "f"),
            "ladder_statistic": "median",
            "screen": screen,
        },
        "calendar": {
            "first": calendar[0].isoformat(), "last": calendar[-1].isoformat(),
            "sessions": len(calendar),
        },
        "cutoffs": cutoff_rows,
        "n_evaluated": len(evaluated),
        "primary_endpoint": {
            "name": "mean cross-sectional Spearman(value_to_price, forward return)",
            "value": None if mean_rho is None else format(q(mean_rho), "f"),
            "n_cutoffs": len(rhos),
        },
        "ladder_monotonicity": {
            "mean_rank_correlation": (
                None if mean_ladder_rho is None else format(q(mean_ladder_rho), "f")
            ),
            "threshold": format(LADDER_MONOTONE_MIN, "f"),
            "note": (
                "judged on the whole ladder by MEDIAN, not on the top bucket and not "
                "on bucket means — an inverted ladder under a strong headline is what "
                "Model A hid, and a bucket mean here reports its largest sub-cent "
                "quotation artefact rather than the bucket"
            ),
        },
        "mean_cheapest_minus_dearest_net": format(q(mean_spread), "f"),
        "verdict": verdict,
        "walk_forward": {
            "train_cutoffs": len(train), "holdout_cutoffs": len(holdout),
            "train_mean_spearman": _mean_rho_of(train),
            "holdout_mean_spearman": _mean_rho_of(holdout) if holdout else None,
            "note": "single chronological split; a handful of cutoffs is not a test of edge",
        },
        "survivorship": {
            "membership_rule": (
                "traded at the cutoff (close in the pre-registered window) AND "
                "rs_security_master.security_type = 'Common Stock' — NOT universe.is_active"
            ),
            "dropped_no_forward_price_total": sum(
                int(str(r.get("dropped_no_forward_price", 0))) for r in evaluated
            ),
            "caveat": (
                "rs_security_master carries 2,040 inactive rows and ZERO delisted_date "
                "values, so a name delisting inside a forward window is dropped rather "
                "than assigned its delisting return. The literature puts performance-"
                "related delistings near -30%, so the residual bias is UPWARD. The "
                "dropped count bounds it; it is not imputed."
            ),
        },
    }


def evaluation_hash(payload: dict[str, object]) -> str:
    return hash_document_payload(payload)
