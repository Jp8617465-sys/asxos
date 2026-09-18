"""
Snapshot valuation arithmetic — `asxos/domain/portfolio/snapshot.py`.

NO MOCKS, NO CONNECTION. That is the point of the module these cover: until
2026-09-18 this arithmetic lived inside `jobs/snapshot_portfolio.py`
interleaved with three `conn.fetch` calls, so the only way to exercise
`holdings_mv_aud` / `us_mv_aud` / `unrealised_fx_pnl_aud` — the columns the
brief and every performance read are built on — was through a fake asyncpg
connection. See `docs/proposals/hybrid-tdd-assessment-2026-09-17.md` §7 action 3.

The job-level tests in `tests/test_snapshot_portfolio_job.py` still cover the
wiring (query sequence, UPSERT, gates) and are what proves the extraction
preserved behaviour; these cover the maths.

Defends: the USD→AUD direction (dividing by USD-per-AUD, not multiplying),
the hard-fail when a foreign holding has no rate, the sign of the currency
slice of P&L, the suppress-on-data-gap rule, and risk R10 — that
`cost_base_normal` is AUD while `close` is native.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from asxos.domain.portfolio.snapshot import (
    ForeignLot,
    HoldingPrice,
    compute_foreign_cost_basis,
    compute_holdings_mv,
)

_AS_OF = date(2026, 9, 17)


def D(x: str) -> Decimal:
    return Decimal(x)


# ---------------------------------------------------------------------------
# compute_holdings_mv
# ---------------------------------------------------------------------------


def test_empty_book_is_zero_not_none() -> None:
    """An empty book values at 0, not NULL — we know it is worth nothing."""
    mv = compute_holdings_mv([], D("0.6450"), _AS_OF)
    assert mv.total_mv_aud == D("0")
    assert mv.holdings_count == 0
    assert mv.us_mv_aud is None


def test_domestic_only_applies_no_fx() -> None:
    """An ASX close is already AUD; the rate must not touch it."""
    mv = compute_holdings_mv(
        [HoldingPrice("CBA.AU", D("100"), D("105.50"))], D("0.6450"), _AS_OF
    )
    assert mv.total_mv_aud == D("10550.000000")
    assert mv.holdings_count == 1
    assert mv.us_mv_aud is None, "an ASX holding must not register a foreign sleeve"


def test_domestic_only_needs_no_fx_rate_at_all() -> None:
    """No rate is required while nothing foreign is held."""
    mv = compute_holdings_mv(
        [HoldingPrice("CBA.AU", D("100"), D("105.50"))], None, _AS_OF
    )
    assert mv.total_mv_aud == D("10550.000000")


def test_foreign_close_is_divided_by_usd_per_aud() -> None:
    """USD→AUD DIVIDES by the AUDUSD rate. Multiplying would understate a US
    position by ~35% at a 0.645 rate — the direction is the whole test."""
    mv = compute_holdings_mv(
        [HoldingPrice("HUBS.NYSE", D("24"), D("500.00"))], D("0.6450"), _AS_OF
    )
    # 24 × 500 ÷ 0.6450 = 18,604.651163 AUD (not 24 × 500 × 0.645 = 7,740)
    assert mv.total_mv_aud == D("18604.651163")
    assert mv.us_mv_aud == D("18604.651163")
    assert mv.total_mv_aud > D("18000"), "a divide, not a multiply"


@pytest.mark.parametrize("suffix", [".NYSE", ".NASDAQ", ".AMEX", ".US"])
def test_every_foreign_suffix_is_converted(suffix: str) -> None:
    """The stale-copy bug this guards: one site matching only `.US` and
    silently mishandling `.NYSE`/`.NASDAQ`/`.AMEX` (fx.py's own header)."""
    mv = compute_holdings_mv(
        [HoldingPrice(f"FOO{suffix}", D("10"), D("100.00"))], D("0.5000"), _AS_OF
    )
    assert mv.us_mv_aud == D("2000.000000"), f"{suffix} was not FX-converted"


def test_mixed_book_isolates_the_foreign_sleeve() -> None:
    """Total spans both; us_mv_aud is the foreign slice only."""
    mv = compute_holdings_mv(
        [
            HoldingPrice("CBA.AU", D("100"), D("105.50")),
            HoldingPrice("HUBS.NYSE", D("24"), D("500.00")),
        ],
        D("0.6450"),
        _AS_OF,
    )
    assert mv.us_mv_aud == D("18604.651163")
    assert mv.total_mv_aud == D("29154.651163")
    assert mv.total_mv_aud == D("10550.000000") + mv.us_mv_aud
    assert mv.holdings_count == 2


def test_foreign_holding_without_fx_rate_hard_fails() -> None:
    """CLAUDE.md #10: never value a US position at its USD number."""
    with pytest.raises(RuntimeError, match="No AUDUSD FX rate on or before 2026-09-17"):
        compute_holdings_mv(
            [HoldingPrice("HUBS.NYSE", D("24"), D("500.00"))], None, _AS_OF
        )


def test_hard_fail_names_the_date_and_the_remedy() -> None:
    """The message is what an operator reads at 2am."""
    with pytest.raises(RuntimeError) as exc:
        compute_holdings_mv([HoldingPrice("X.NYSE", D("1"), D("1"))], None, _AS_OF)
    assert "2026-09-17" in str(exc.value)
    assert "sync_prices" in str(exc.value)


def test_counts_holdings_not_just_the_priced_foreign_ones() -> None:
    mv = compute_holdings_mv(
        [
            HoldingPrice("CBA.AU", D("1"), D("1")),
            HoldingPrice("BHP.AU", D("1"), D("1")),
            HoldingPrice("X.NYSE", D("1"), D("1")),
        ],
        D("0.65"),
        _AS_OF,
    )
    assert mv.holdings_count == 3


def test_figures_quantise_to_six_places() -> None:
    """NUMERIC(18,6) is the storage type (CLAUDE.md #5)."""
    mv = compute_holdings_mv(
        [HoldingPrice("X.NYSE", D("1"), D("1.00"))], D("0.3333"), _AS_OF
    )
    assert mv.total_mv_aud.as_tuple().exponent == -6
    assert mv.us_mv_aud is not None
    assert mv.us_mv_aud.as_tuple().exponent == -6


# ---------------------------------------------------------------------------
# compute_foreign_cost_basis
# ---------------------------------------------------------------------------


def test_no_lots_reports_nothing_rather_than_zero() -> None:
    """No lots means unknown, not zero: a 0 cost base would read as a 100% gain."""
    cost = compute_foreign_cost_basis([], D("0.6450"))
    assert cost.us_cost_aud is None
    assert cost.us_fx_pnl_aud is None
    assert cost.lots_missing_acquisition_fx == 0


def test_cost_base_is_summed_in_aud_r10() -> None:
    """R10: `cost_base_normal` is ALREADY AUD — sum it, never convert it.

    The real HUBS.NYSE lot from `.claude/rules/portfolio-conventions.md`:
    24 sh × US$187.54 ÷ 0.6450 acquisition FX = 6,978.23 AUD. In the
    2026-07-11 /pm-review, dividing this by quantity and comparing to a USD
    close reported the position at −29% when it was roughly flat.
    """
    cost = compute_foreign_cost_basis(
        [ForeignLot(D("24"), D("6978.23"), D("0.6450"), D("187.54"))], D("0.6450")
    )
    assert cost.us_cost_aud == D("6978.23")


def test_fx_pnl_is_zero_when_rate_is_unchanged() -> None:
    """No currency move, no currency effect — whatever the price did."""
    cost = compute_foreign_cost_basis(
        [ForeignLot(D("24"), D("6978.23"), D("0.6450"), D("500.00"))], D("0.6450")
    )
    assert cost.us_fx_pnl_aud == D("0.000000")


def test_weaker_aud_is_a_currency_gain() -> None:
    """AUD 0.6450 → 0.60 means each USD buys more AUD: a gain on a US asset."""
    cost = compute_foreign_cost_basis(
        [ForeignLot(D("24"), D("6978.23"), D("0.6450"), D("500.00"))], D("0.60")
    )
    assert cost.us_fx_pnl_aud == D("1395.348837")
    assert cost.us_fx_pnl_aud > 0


def test_stronger_aud_is_a_currency_loss() -> None:
    """AUD 0.6450 → 0.70 works against a US holding. The sign must flip."""
    cost = compute_foreign_cost_basis(
        [ForeignLot(D("24"), D("6978.23"), D("0.6450"), D("500.00"))], D("0.70")
    )
    assert cost.us_fx_pnl_aud == D("-1461.794020")
    assert cost.us_fx_pnl_aud < 0


def test_one_lot_missing_acquisition_fx_suppresses_the_whole_figure() -> None:
    """A partial FX sum would read as a complete one, so it is withheld — but
    the cost base still totals, and the gap is counted for the caller to log."""
    cost = compute_foreign_cost_basis(
        [
            ForeignLot(D("24"), D("6978.23"), D("0.6450"), D("500.00")),
            ForeignLot(D("10"), D("1000.00"), None, D("120.00")),
        ],
        D("0.60"),
    )
    assert cost.us_fx_pnl_aud is None, "a partial currency sum must not be reported"
    assert cost.us_cost_aud == D("7978.23"), "cost base is unaffected by the gap"
    assert cost.lots_missing_acquisition_fx == 1


def test_missing_count_is_returned_not_logged() -> None:
    """These functions take no side effects; the job owns the warning."""
    cost = compute_foreign_cost_basis(
        [
            ForeignLot(D("1"), D("1"), None, D("1")),
            ForeignLot(D("1"), D("1"), None, D("1")),
        ],
        D("0.65"),
    )
    assert cost.lots_missing_acquisition_fx == 2
    assert cost.us_fx_pnl_aud is None


def test_fx_pnl_sums_across_lots_with_different_acquisition_rates() -> None:
    """Each lot carries its own entry rate; the effects add."""
    lots = [
        ForeignLot(D("24"), D("6978.23"), D("0.6450"), D("500.00")),
        ForeignLot(D("10"), D("1500.00"), D("0.7000"), D("200.00")),
    ]
    combined = compute_foreign_cost_basis(lots, D("0.60"))
    first = compute_foreign_cost_basis(lots[:1], D("0.60"))
    second = compute_foreign_cost_basis(lots[1:], D("0.60"))
    assert first.us_fx_pnl_aud is not None and second.us_fx_pnl_aud is not None
    assert combined.us_fx_pnl_aud == first.us_fx_pnl_aud + second.us_fx_pnl_aud
    assert combined.us_cost_aud == D("8478.23")


def test_fx_pnl_is_the_currency_slice_only_not_total_pnl() -> None:
    """A lot flat in USD but moved in FX has zero price P&L and non-zero FX
    P&L. Conflating the two is what this column exists to prevent."""
    cost = compute_foreign_cost_basis(
        [ForeignLot(D("24"), D("6978.23"), D("0.6450"), D("187.54"))], D("0.60")
    )
    assert cost.us_fx_pnl_aud is not None
    assert cost.us_fx_pnl_aud > 0, "FX moved, so the currency slice is non-zero"
    # Native value is unchanged from acquisition, so the entire AUD gain here
    # is currency: cost base + fx effect ≈ today's AUD market value.
    todays_mv_aud = (D("24") * D("187.54") / D("0.60")).quantize(D("0.01"))
    assert (cost.us_cost_aud + cost.us_fx_pnl_aud).quantize(D("0.01")) == todays_mv_aud


def test_fx_pnl_quantises_to_six_places() -> None:
    cost = compute_foreign_cost_basis(
        [ForeignLot(D("3"), D("100"), D("0.6667"), D("33.33"))], D("0.3333")
    )
    assert cost.us_fx_pnl_aud is not None
    assert cost.us_fx_pnl_aud.as_tuple().exponent == -6
