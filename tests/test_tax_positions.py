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


def test_smsf_election_no_depreciated_assets_emits_advisory() -> None:
    # §6.5: election made but no lots → data-driven check finds nothing → brief advisory.
    tv = tax_view_smsf(
        lots=[],
        realised_gains=[],
        dividends=[],
        config=SMSFConfig(fund_pension_proportion=Decimal("0"), div296_election_made=True),
        tsb_ref=None,
    )
    assert tv.franking_warnings
    assert "no depreciated" in tv.franking_warnings[0].lower()


def test_smsf_election_depreciated_lot_warns_with_symbol_and_cost_bases() -> None:
    # §6.5: lot where cost_base_div296 < cost_base_normal → per-lot warning with
    # symbol, lot ID, and both cost bases.
    lot = HoldingLot(
        lot_id=1,
        symbol="BHP.AU",
        acquired_at=date(2020, 1, 1),
        quantity=Decimal("100"),
        cost_base_normal=Decimal("50000"),
        cost_base_div296=Decimal("40000"),  # depreciated: MV(30-Jun-2026) < cost
    )
    tv = tax_view_smsf(
        lots=[lot],
        realised_gains=[],
        dividends=[],
        config=SMSFConfig(fund_pension_proportion=Decimal("0"), div296_election_made=True),
        tsb_ref=None,
    )
    assert len(tv.franking_warnings) == 1
    assert "BHP.AU" in tv.franking_warnings[0]
    assert "lot 1" in tv.franking_warnings[0]
    assert "50000" in tv.franking_warnings[0]
    assert "40000" in tv.franking_warnings[0]


# ---------------------------------------------------------------------------
# §5.3 / §7 — Medicare + income tax on the net capital gain (the conformance fix)
# ---------------------------------------------------------------------------


def test_tc11_individual_cgt_income_tax_plus_medicare() -> None:
    # TC-11 (spec §5.1/§5.3/§7): $10,000 discountable gain, individual 37%.
    # net gain $5,000 → income tax 5000*0.37=1850, medicare 5000*0.02=100,
    # total $1,950 (the spec's stated figure).
    gain = CapitalGain("AAA", Decimal("10000"), discountable=True, holding_period_days=400)
    tv = tax_view_individual(
        lots=[],
        realised_gains=[gain],
        dividends=[],
        config=IndividualConfig(marginal_rate=Decimal("0.37")),
        today=date(2026, 6, 1),
    )
    assert tv.cgt_tax_outcome is not None
    assert tv.cgt_tax_outcome.income_tax == Decimal("1850.00")
    assert tv.cgt_tax_outcome.medicare == Decimal("100.00")
    assert tv.cgt_tax_outcome.total_tax == Decimal("1950.00")


def test_individual_cgt_medicare_honours_zero_config_rate() -> None:
    # §7.1: a low-income individual (medicare_levy_rate=0) pays no Medicare on the
    # CGT branch — must match the dividend path, not the bare statutory constant.
    gain = CapitalGain("AAA", Decimal("10000"), discountable=True, holding_period_days=400)
    tv = tax_view_individual(
        lots=[],
        realised_gains=[gain],
        dividends=[],
        config=IndividualConfig(marginal_rate=Decimal("0.37"), medicare_levy_rate=Decimal("0")),
        today=date(2026, 6, 1),
    )
    assert tv.cgt_tax_outcome is not None
    assert tv.cgt_tax_outcome.medicare == Decimal("0")
    assert tv.cgt_tax_outcome.total_tax == Decimal("1850.00")  # income tax only


def test_tc10_individual_medicare_on_non_discount_gain() -> None:
    # TC-10 (spec §5.1; §7 makes Medicare base-wide): $10,000 non-discountable gain,
    # individual 37%. net gain $10,000 → 3700 income + 200 medicare = $3,900.
    gain = CapitalGain("AAA", Decimal("10000"), discountable=False, holding_period_days=100)
    tv = tax_view_individual(
        lots=[],
        realised_gains=[gain],
        dividends=[],
        config=IndividualConfig(marginal_rate=Decimal("0.37")),
        today=date(2026, 6, 1),
    )
    assert tv.cgt_tax_outcome is not None
    assert tv.cgt_tax_outcome.total_tax == Decimal("3900.00")


def test_tc12_smsf_accumulation_fund_tax_15pct() -> None:
    # TC-12 (spec §4.2/§5): $10,000 discountable gain, SMSF accumulation (ECPI 0).
    # SMSF 1/3 discount → net gain $6,666.67 → fund tax 0.15 = $1,000.00. Medicare 0.
    gain = CapitalGain("BBB", Decimal("10000"), discountable=True, holding_period_days=400)
    tv = tax_view_smsf(
        lots=[],
        realised_gains=[gain],
        dividends=[],
        config=SMSFConfig(fund_pension_proportion=Decimal("0")),
        tsb_ref=None,
    )
    assert tv.cgt_tax_outcome is not None
    assert tv.cgt_tax_outcome.income_tax == Decimal("1000.00")
    assert tv.cgt_tax_outcome.medicare == Decimal("0")
    assert tv.cgt_tax_outcome.total_tax == Decimal("1000.00")


def test_smsf_ecpi_reduces_cgt_fund_tax() -> None:
    # INFERRED (no §11 worked example): ECPI exempt proportion reduces the CGT
    # fund-tax base. $10,000 non-discountable gain, SMSF 60% pension →
    # taxable_base 4000, fund tax 0.15 = $600. Flagged for spec confirmation.
    gain = CapitalGain("BBB", Decimal("10000"), discountable=False, holding_period_days=100)
    tv = tax_view_smsf(
        lots=[],
        realised_gains=[gain],
        dividends=[],
        config=SMSFConfig(fund_pension_proportion=Decimal("0.6")),
        tsb_ref=None,
    )
    assert tv.cgt_tax_outcome is not None
    assert tv.cgt_tax_outcome.taxable_base == Decimal("4000.0")
    assert tv.cgt_tax_outcome.income_tax == Decimal("600.00")


def test_individual_net_loss_produces_zero_cgt_tax() -> None:
    # A net capital loss (losses exceed gains) → net_capital_gain 0, so zero CGT
    # income tax / Medicare, and the residual loss is carried forward (§5.2 Step 4).
    loss = CapitalGain("AAA", Decimal("-8000"), discountable=False, holding_period_days=100)
    gain = CapitalGain("BBB", Decimal("3000"), discountable=False, holding_period_days=100)
    tv = tax_view_individual(
        lots=[],
        realised_gains=[loss, gain],
        dividends=[],
        config=IndividualConfig(marginal_rate=Decimal("0.37")),
        today=date(2026, 6, 1),
    )
    assert tv.cgt_tax_outcome is not None
    assert tv.cgt_tax_outcome.total_tax == Decimal("0.00")
    assert tv.net_capital_gain is not None
    assert tv.net_capital_gain.net_capital_loss_cf == Decimal("5000")


# ---------------------------------------------------------------------------
# TC-24 (spec §5.2, v1.4) — SMSF ECPI-on-CGT numeric verification
# ---------------------------------------------------------------------------


def test_tc24_smsf_ecpi_stacks_with_cgt_discount() -> None:
    # TC-24 (spec §5.2, v1.4): $10,000 discountable gain, SMSF fund_pension_proportion=0.60.
    # Step 1: 1/3 discount → net gain ≈ $6,666.67.
    # Step 2: ECPI (60%) → taxable base ≈ $2,666.67.
    # Step 3: fund tax 15% = $400.00. Medicare 0.
    # Confirms §5.2: CGT discount and ECPI exemption are independent and stack.
    gain = CapitalGain("BHP.AU", Decimal("10000"), discountable=True, holding_period_days=400)
    tv = tax_view_smsf(
        lots=[],
        realised_gains=[gain],
        dividends=[],
        config=SMSFConfig(fund_pension_proportion=Decimal("0.6")),
        tsb_ref=None,
    )
    assert tv.cgt_tax_outcome is not None
    assert tv.cgt_tax_outcome.income_tax == Decimal("400.00")
    assert tv.cgt_tax_outcome.medicare == Decimal("0")
    # taxable_base keeps full Decimal precision; use tolerance per §11 spec phrasing "≈"
    assert abs(tv.cgt_tax_outcome.taxable_base - Decimal("2666.67")) <= Decimal("0.01")


# ---------------------------------------------------------------------------
# TC-20 (spec §6.4, v1.5) — Div 296 cost-base reset (s 296-50 ITTPA)
# ---------------------------------------------------------------------------


def test_tc20_smsf_div296_election_uses_cost_base_div296() -> None:
    # TC-20 (spec §6.4, v1.5): SMSF with s 296-50 election. Dual-path disposal.
    # Acquired 2020-01-01 $50,000; MV at 30-Jun-2026 $80,000; disposed 2027-01-01 $100,000.
    # SMSF accumulation (fund_pension_proportion=0), election made, tsb_ref 3.2M.
    #
    # Fund CGT (cost_base_normal): gross $50,000 discountable → 1/3 discount → net ≈ $33,333
    # → fund tax 15% = $5,000 (cgt_tax_outcome.income_tax).
    # Div 296 earnings (cost_base_div296): gross $20,000 → 1/3 discount → ≈ $13,333
    # (div296_outcome.earnings) — NOT $33,333 from the cost_base_normal path.
    fund_cgt_gain = CapitalGain(
        "BHP.AU", Decimal("50000"), discountable=True, holding_period_days=2557
    )
    div296_gain = CapitalGain(
        "BHP.AU", Decimal("20000"), discountable=True, holding_period_days=2557
    )
    tv = tax_view_smsf(
        lots=[],
        realised_gains=[fund_cgt_gain],
        dividends=[],
        config=SMSFConfig(
            fund_pension_proportion=Decimal("0"),
            div296_election_made=True,
        ),
        tsb_ref=Decimal("3200000"),
        div296_realised_gains=[div296_gain],
    )
    # Fund CGT: net gain ≈ 50,000 × 2/3 ≈ 33,333; tax at 15% = $5,000
    assert tv.cgt_tax_outcome is not None
    assert abs(tv.cgt_tax_outcome.income_tax - Decimal("5000")) < Decimal("0.01")
    # Div 296 earnings come from cost_base_div296 path: ≈ 20,000 × 2/3 ≈ 13,333
    assert tv.div296_outcome is not None
    assert abs(tv.div296_outcome.earnings - Decimal("13333.33")) < Decimal("0.01")


def test_tc20_without_election_uses_normal_ncg_for_div296() -> None:
    # Regression: when div296_election_made=False, Div 296 earnings still come from
    # the ordinary cost_base_normal path (spec §6.2), even if div296_realised_gains
    # is supplied.
    fund_cgt_gain = CapitalGain(
        "BHP.AU", Decimal("50000"), discountable=True, holding_period_days=2557
    )
    div296_gain = CapitalGain(
        "BHP.AU", Decimal("20000"), discountable=True, holding_period_days=2557
    )
    tv = tax_view_smsf(
        lots=[],
        realised_gains=[fund_cgt_gain],
        dividends=[],
        config=SMSFConfig(
            fund_pension_proportion=Decimal("0"),
            div296_election_made=False,
        ),
        tsb_ref=Decimal("3200000"),
        div296_realised_gains=[div296_gain],  # supplied but election not made → ignored
    )
    assert tv.div296_outcome is not None
    # Earnings should use ordinary ncg (≈ 33,333), not the div296 gains (≈ 13,333)
    assert abs(tv.div296_outcome.earnings - Decimal("33333.33")) < Decimal("0.01")
