"""
Tax-view aggregator tests (asxos/domain/tax/positions.py).

`tax_view_individual` / `tax_view_smsf` are the output layer surfaced by
`asx tax-view`. They were previously untested. These tests pin the aggregator's
actual contract: it surfaces *components* (dividends-after-tax, the §5.2 net
capital gain structure, Div 296 for SMSF, eligibility alerts) — it does not emit
a single combined tax figure.

Cites spec §4.1 (dividends), §5 (CGT), §6.3 (Div 296), §7 (Medicare folded into
the individual dividend path).
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from asxos.domain.tax.positions import tax_view_individual, tax_view_smsf
from asxos.domain.tax.types import (
    CapitalGain,
    Dividend,
    HoldingLot,
    IndividualConfig,
    SMSFConfig,
)


def _approx(actual: Decimal, expected_str: str, tol: str = "0.01") -> bool:
    return abs(actual - Decimal(expected_str)) <= Decimal(tol)


def _div(cash: str) -> Dividend:
    return Dividend(
        symbol="X.AU",
        pay_date=date(2026, 5, 1),
        cash_dividend=Decimal(cash),
        franking_pct=Decimal("1.0"),
        corporate_tax_rate=Decimal("0.30"),
    )


def _lot(symbol: str, acquired_at: date) -> HoldingLot:
    return HoldingLot(
        lot_id=1,
        symbol=symbol,
        acquired_at=acquired_at,
        quantity=Decimal("100"),
        cost_base_normal=Decimal("1000"),
        cost_base_div296=Decimal("1000"),
    )


def test_individual_view_surfaces_components() -> None:
    # §4.1: one TC-01 dividend ($1000 ff @30%, 37% marginal) → after-tax 871.43.
    # §5: one discountable $10,000 gain, no losses, individual 50% discount → 5000.
    # §5.1: a lot 10 days from the 12-month boundary raises one eligibility alert.
    today = date(2026, 6, 1)
    near_boundary = _lot("AAA", date(2025, 6, 10))  # earliest-qualifying = today + 10d
    gain = CapitalGain("AAA", Decimal("10000"), discountable=True, holding_period_days=400)

    tv = tax_view_individual(
        lots=[near_boundary],
        realised_gains=[gain],
        dividends=[_div("1000")],
        config=IndividualConfig(marginal_rate=Decimal("0.37")),
        today=today,
    )

    assert tv.account_type == "individual"
    assert tv.holdings_count == 1
    assert tv.realised_gain_aud == Decimal("10000")
    assert tv.net_capital_gain is not None
    assert tv.net_capital_gain.net_capital_gain == Decimal("5000")
    assert _approx(tv.dividends_after_tax, "871.43")
    assert len(tv.eligibility_alerts) == 1
    assert "AAA" in tv.eligibility_alerts[0]


def test_individual_view_no_gains_leaves_ncg_none() -> None:
    tv = tax_view_individual(
        lots=[],
        realised_gains=[],
        dividends=[_div("1000")],
        config=IndividualConfig(marginal_rate=Decimal("0.37")),
        today=date(2026, 6, 1),
    )
    assert tv.net_capital_gain is None
    assert tv.holdings_count == 0
    assert _approx(tv.dividends_after_tax, "871.43")


def test_smsf_view_wires_div296_on_net_gain() -> None:
    # §6.3 / TC-13: tsb_ref 3.2M, earnings = net gain 160k → tier_1 1500, tier_2 0.
    # gain is non-discountable so net_capital_gain == 160000 feeds Div 296.
    gain = CapitalGain("BBB", Decimal("160000"), discountable=False, holding_period_days=100)

    tv = tax_view_smsf(
        lots=[],
        realised_gains=[gain],
        dividends=[],
        config=SMSFConfig(fund_pension_proportion=Decimal("0")),
        tsb_ref=Decimal("3200000"),
    )

    assert tv.account_type == "smsf"
    assert tv.div296_outcome is not None
    assert tv.div296_outcome.tier_1 == Decimal("1500")  # exact: 160000 * 0.0625 * 0.15
    assert tv.div296_outcome.tier_2 == Decimal("0")


def test_smsf_view_no_tsb_skips_div296() -> None:
    gain = CapitalGain("BBB", Decimal("160000"), discountable=False, holding_period_days=100)
    tv = tax_view_smsf(
        lots=[],
        realised_gains=[gain],
        dividends=[],
        config=SMSFConfig(fund_pension_proportion=Decimal("0")),
        tsb_ref=None,
    )
    assert tv.div296_outcome is None


def test_smsf_election_emits_franking_warning() -> None:
    # §6.5: with the election flagged, the aggregator surfaces a static advisory
    # hint. NOTE: the locking behaviour itself (pinning cost_base_div296 at
    # MV(30-Jun-2026), eliminating pre-2026 losses) is NOT yet implemented — this
    # only asserts the hint is surfaced, not that the lock is computed.
    tv = tax_view_smsf(
        lots=[],
        realised_gains=[],
        dividends=[],
        config=SMSFConfig(fund_pension_proportion=Decimal("0"), div296_election_made=True),
        tsb_ref=None,
    )
    assert tv.franking_warnings
    assert "cost_base_div296" in tv.franking_warnings[0]
