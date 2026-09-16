"""The V/P evaluator must see the ladder, not the headline.

Model A's decay analysis found STRONG_BUY returning -0.09% at 21d against
HOLD's +5.07% — conviction inverted at the top, under a model that looked
confident. Any evaluator that reads only the extreme bucket, or only a
top-minus-bottom spread, is blind to that. The decisive test here is
`test_strong_top_bucket_does_not_rescue_an_inverted_ladder`.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from asxos.domain.research.registry.harness import HarnessError
from asxos.domain.research.registry.vp_harness import (
    VERDICT_NEGATIVE,
    VERDICT_NULL,
    VERDICT_POSITIVE,
    evaluate_value_to_price,
    evaluation_hash,
    spearman,
)

HORIZON = 5
N_SYMBOLS = 100


def _calendar(n: int, start: date = date(2025, 1, 6)) -> list[date]:
    """n consecutive weekday sessions."""
    out: list[date] = []
    d = start
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out


def _build(
    forward_return_for_rank,
    *,
    n_symbols: int = N_SYMBOLS,
    sessions: int = 20,
    cutoff_index: int = 0,
    omit_forward: set[str] | None = None,
):
    """A panel and scores where symbol i has V/P rank i and a chosen forward return.

    Every symbol carries a price on EVERY session, because the evaluator derives
    its trading calendar from the union of panel dates — a two-point panel would
    make any horizon longer than one session unreachable.
    """
    cal = _calendar(sessions)
    cutoff = cal[cutoff_index]
    forward_i = cutoff_index + HORIZON
    omit = omit_forward or set()
    panel: dict[str, list[tuple[date, Decimal]]] = {}
    scores: dict[date, dict[str, Decimal]] = {cutoff: {}}
    for i in range(n_symbols):
        sym = f"S{i:03d}.AU"
        p0 = Decimal("10")
        ret = forward_return_for_rank(i, n_symbols)
        p1 = (p0 * (Decimal(1) + ret)).quantize(Decimal("0.000001"))
        series: list[tuple[date, Decimal]] = []
        for j, d in enumerate(cal):
            if j == forward_i and sym in omit:
                continue  # priced at the cutoff, gone by the forward date
            series.append((d, p0 if j < forward_i else p1))
        panel[sym] = series
        # V/P ascending in i: S000 is the dearest, S099 the cheapest.
        scores[cutoff][sym] = Decimal("0.2") + Decimal(i) / Decimal(100)
    return scores, panel


def _run(scores, panel, **kw):
    return evaluate_value_to_price(
        scores, panel, horizon_trading_days=HORIZON, min_symbols_per_cutoff=10, **kw
    )


# --- the decisive one -------------------------------------------------------

def test_strong_top_bucket_does_not_rescue_an_inverted_ladder() -> None:
    """The Model A signature: a great top bucket over an otherwise inverted ladder.

    Buckets 1-4 decline as V/P rises (wrong direction); bucket 5 is excellent.
    A top-bucket or spread-only reading would call this a pass. It is not one.
    """
    def shape(i: int, n: int) -> Decimal:
        if i >= 80:  # cheapest quintile — strong
            return Decimal("0.30")
        return Decimal("0.20") - Decimal(i) * Decimal("0.002")  # 0.20 -> 0.042, inverted

    out = _run(*_build(shape))
    assert out["verdict"] != VERDICT_POSITIVE
    # The spread alone WOULD have looked positive — that is the trap.
    assert Decimal(out["mean_cheapest_minus_dearest_net"]) > 0
    # The ladder correlation is what refuses it.
    assert Decimal(out["ladder_monotonicity"]["mean_rank_correlation"]) < Decimal("0.9")


# --- verdict classification -------------------------------------------------

def test_perfect_monotone_ladder_reads_positive() -> None:
    out = _run(*_build(lambda i, n: Decimal(i) * Decimal("0.001")))
    assert out["verdict"] == VERDICT_POSITIVE
    assert Decimal(out["primary_endpoint"]["value"]) > 0
    assert Decimal(out["ladder_monotonicity"]["mean_rank_correlation"]) == Decimal("1")


def test_inverted_ladder_reads_negative() -> None:
    out = _run(*_build(lambda i, n: Decimal(n - i) * Decimal("0.001")))
    assert out["verdict"] == VERDICT_NEGATIVE
    assert Decimal(out["primary_endpoint"]["value"]) < 0


def test_flat_returns_read_null_not_positive() -> None:
    out = _run(*_build(lambda i, n: Decimal("0.05")))
    assert out["verdict"] == VERDICT_NULL


def test_ladder_has_one_bucket_per_quintile_and_drops_no_name() -> None:
    out = _run(*_build(lambda i, n: Decimal(i) * Decimal("0.001")))
    ladder = out["cutoffs"][0]["ladder"]
    assert [row["bucket"] for row in ladder] == [1, 2, 3, 4, 5]
    assert sum(row["n"] for row in ladder) == N_SYMBOLS


def test_cheapest_bucket_is_last() -> None:
    """Bucket 5 must be the high-V/P (cheap) end, or every sign flips."""
    out = _run(*_build(lambda i, n: Decimal(i) * Decimal("0.001")))
    ladder = out["cutoffs"][0]["ladder"]
    assert Decimal(ladder[-1]["mean_value_to_price"]) > Decimal(ladder[0]["mean_value_to_price"])


# --- survivorship accounting ------------------------------------------------

def test_names_without_a_forward_price_are_counted_not_imputed() -> None:
    omitted = {f"S{i:03d}.AU" for i in range(90, 100)}  # cheapest, i.e. worst case
    scores, panel = _build(lambda i, n: Decimal(i) * Decimal("0.001"), omit_forward=omitted)
    out = _run(scores, panel)
    row = out["cutoffs"][0]
    assert row["dropped_no_forward_price"] == 10
    assert row["paired"] == N_SYMBOLS - 10
    assert out["survivorship"]["dropped_no_forward_price_total"] == 10
    # The bias direction must be stated, not left for the reader to infer.
    assert "UPWARD" in out["survivorship"]["caveat"]
    assert "not imputed" in out["survivorship"]["caveat"]


def test_membership_rule_is_recorded_and_is_not_is_active() -> None:
    out = _run(*_build(lambda i, n: Decimal(i) * Decimal("0.001")))
    rule = out["survivorship"]["membership_rule"]
    assert "NOT universe.is_active" in rule


# --- marked book ------------------------------------------------------------

def test_marked_book_names_are_flagged_and_still_evaluated() -> None:
    scores, panel = _build(lambda i, n: Decimal(i) * Decimal("0.001"))
    marked = {f"S{i:03d}.AU": "LIC — ROE is a portfolio return" for i in range(0, 20)}
    out = _run(scores, panel, marked_book=marked)
    assert out["cutoffs"][0]["marked_book_in_sample"] == 20
    assert out["cutoffs"][0]["paired"] == N_SYMBOLS  # flagged, never dropped


# --- skips are reported, not silent ----------------------------------------

def test_cutoff_without_a_forward_window_is_reported() -> None:
    scores, panel = _build(lambda i, n: Decimal(i) * Decimal("0.001"), sessions=20, cutoff_index=18)
    with pytest.raises(HarnessError, match="no evaluable cutoff"):
        _run(scores, panel)


def test_thin_cutoff_is_an_error_not_a_quiet_pass() -> None:
    """Below the minimum, a cutoff must not be evaluated on a handful of names."""
    scores, panel = _build(lambda i, n: Decimal(i) * Decimal("0.001"), n_symbols=12)
    with pytest.raises(HarnessError, match="no evaluable cutoff"):
        evaluate_value_to_price(
            scores, panel, horizon_trading_days=HORIZON, min_symbols_per_cutoff=50
        )


# --- determinism and hygiene ------------------------------------------------

def test_two_runs_over_the_same_inputs_hash_identically() -> None:
    scores, panel = _build(lambda i, n: Decimal(i) * Decimal("0.001"))
    assert evaluation_hash(_run(scores, panel)) == evaluation_hash(_run(scores, panel))


def test_float_prices_are_refused() -> None:
    scores, panel = _build(lambda i, n: Decimal(i) * Decimal("0.001"))
    panel["S000.AU"] = [(d, 1.5) for d, _ in panel["S000.AU"]]  # type: ignore[misc]
    with pytest.raises(HarnessError, match="float price"):
        _run(scores, panel)


def test_no_floats_reach_the_payload() -> None:
    out = _run(*_build(lambda i, n: Decimal(i) * Decimal("0.001")))

    def walk(v: object) -> None:
        assert not isinstance(v, float), f"float in payload: {v!r}"
        if isinstance(v, dict):
            for item in v.values():
                walk(item)
        elif isinstance(v, list | tuple):
            for item in v:
                walk(item)

    walk(out)


def test_empty_scores_is_an_error_not_an_empty_pass() -> None:
    with pytest.raises(HarnessError, match="no cutoffs"):
        evaluate_value_to_price({}, {}, horizon_trading_days=HORIZON)


# --- the statistic itself ---------------------------------------------------

def test_spearman_is_exact_on_a_perfect_ladder() -> None:
    xs = [Decimal(i) for i in range(10)]
    assert spearman(xs, xs) == Decimal(1)
    assert spearman(xs, [Decimal(-i) for i in range(10)]) == Decimal(-1)


def test_spearman_handles_ties_without_blowing_up() -> None:
    xs = [Decimal(1), Decimal(1), Decimal(2), Decimal(2)]
    ys = [Decimal(5), Decimal(5), Decimal(9), Decimal(9)]
    assert spearman(xs, ys) == Decimal(1)


def test_spearman_is_none_on_a_constant_series() -> None:
    assert spearman([Decimal(3)] * 5, [Decimal(i) for i in range(5)]) is None
