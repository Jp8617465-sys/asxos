"""
Aggregator: turns a portfolio + tax config into a TaxView for `asx tax-view`.

Pure function — takes already-loaded holdings, signal/price hints, and the
tax config. The CLI layer handles DB I/O.
"""
from __future__ import annotations

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from asxos.domain.tax.cgt import days_to_eligibility, net_capital_gain
from asxos.domain.tax.div_296 import div296_liability
from asxos.domain.tax.dividends import (
    after_tax_dividend_individual,
    after_tax_dividend_smsf,
)
from asxos.domain.tax.medicare import medicare_levy_on
from asxos.domain.tax.types import (
    SMSF_TAX_RATE,
    CapitalGain,
    CgtTaxOutcome,
    Div296Outcome,
    Dividend,
    HoldingLot,
    IndividualConfig,
    NetCapitalGain,
    SMSFConfig,
    TaxView,
)

_CENTS = Decimal("0.01")


def _q(x: Decimal) -> Decimal:
    """Quantize a tax *ledger line* to cents (ROUND_HALF_UP), matching the
    cgt_break_even_price convention. Policy: ledger lines (income_tax, medicare,
    total_tax) are quantized; bases (net_capital_gain, taxable_base) keep full
    precision. (The dividend ledger does not quantize — CgtTaxOutcome does.)"""
    return x.quantize(_CENTS, rounding=ROUND_HALF_UP)


def tax_view_individual(
    *,
    lots: list[HoldingLot],
    realised_gains: list[CapitalGain],
    dividends: list[Dividend],
    config: IndividualConfig,
    today: date | None = None,
) -> TaxView:
    today = today or date.today()
    ncg: NetCapitalGain | None = None
    cgt_tax: CgtTaxOutcome | None = None
    if realised_gains:
        ncg = net_capital_gain(
            realised_gains,
            current_year_losses=Decimal("0"),
            carried_forward_losses=config.carried_forward_capital_loss,
            account_type="individual",
        )
        # spec §5.3/§7: income tax + Medicare on the post-discount net gain.
        base = ncg.net_capital_gain
        income_tax = _q(base * config.marginal_rate)
        # honour the taxpayer's configured rate (0 for low-income per §7.1), matching
        # the dividend path — not the bare statutory constant.
        medicare = _q(
            medicare_levy_on(base, account_type="individual", rate=config.medicare_levy_rate)
        )
        cgt_tax = CgtTaxOutcome(
            net_capital_gain=base,
            exempt_proportion=Decimal("0"),
            taxable_base=base,
            income_tax=income_tax,
            medicare=medicare,
            total_tax=income_tax + medicare,
        )

    after_tax = Decimal("0")
    for div in dividends:
        after_tax += after_tax_dividend_individual(div, config).after_tax_cash

    alerts: list[str] = []
    for lot in lots:
        if lot.disposed_at is not None:
            continue
        days = days_to_eligibility(lot.acquired_at, today)
        if 0 < days <= 30:
            alerts.append(
                f"{lot.symbol} (lot {lot.lot_id}) crosses 12-month CGT discount in {days}d"
            )

    return TaxView(
        account_type="individual",
        holdings_count=sum(1 for lot in lots if lot.disposed_at is None),
        realised_gain_aud=sum((g.gain_aud for g in realised_gains), Decimal("0")),
        net_capital_gain=ncg,
        dividends_after_tax=after_tax,
        eligibility_alerts=alerts,
        cgt_tax_outcome=cgt_tax,
    )


def tax_view_smsf(
    *,
    lots: list[HoldingLot],
    realised_gains: list[CapitalGain],
    dividends: list[Dividend],
    config: SMSFConfig,
    tsb_ref: Decimal | None = None,
    div296_lsbt: Decimal = Decimal("3000000"),
    div296_vlsbt: Decimal = Decimal("10000000"),
    div296_provisional: bool = False,
    today: date | None = None,
) -> TaxView:
    today = today or date.today()
    ncg: NetCapitalGain | None = None
    cgt_tax: CgtTaxOutcome | None = None
    if realised_gains:
        ncg = net_capital_gain(
            realised_gains,
            current_year_losses=Decimal("0"),
            carried_forward_losses=config.carried_forward_capital_loss,
            account_type="smsf",
        )
        # spec §4.2 fund rate (15%) on the post-discount net gain, less the ECPI
        # exempt proportion. §5.2 states ECPI applies to the post-discount net
        # capital gain ("independent and stack"); it is ignored only for the Div
        # 296 base (§6.2), so the two paths do not double-count. Medicare is 0 for
        # funds (§7). TC-24 (§5.2, §4.2) is the numeric lock for the stacking path
        # (discountable gain + non-zero fund_pension_proportion).
        base = ncg.net_capital_gain
        taxable_base = base * (Decimal("1") - config.fund_pension_proportion)
        income_tax = _q(taxable_base * SMSF_TAX_RATE)
        cgt_tax = CgtTaxOutcome(
            net_capital_gain=base,
            exempt_proportion=config.fund_pension_proportion,
            taxable_base=taxable_base,
            income_tax=income_tax,
            medicare=_q(medicare_levy_on(base, account_type="smsf")),
            total_tax=income_tax,
        )

    after_tax = Decimal("0")
    for div in dividends:
        after_tax += after_tax_dividend_smsf(div, config).after_tax_cash

    div296: Div296Outcome | None = None
    if tsb_ref is not None and ncg is not None:
        # spec §6.2: ECPI is ignored for Div 296 — use the pre-ECPI net gain
        # (here ncg.net_capital_gain is already post-discount per s 115-100).
        div296 = div296_liability(
            tsb_ref=tsb_ref,
            earnings=ncg.net_capital_gain,
            lsbt=div296_lsbt,
            vlsbt=div296_vlsbt,
            is_provisional=div296_provisional,
        )

    alerts: list[str] = []
    for lot in lots:
        if lot.disposed_at is not None:
            continue
        days = days_to_eligibility(lot.acquired_at, today)
        if 0 < days <= 30:
            alerts.append(
                f"{lot.symbol} (lot {lot.lot_id}) crosses 12-month CGT discount in {days}d"
            )

    warnings: list[str] = []
    if config.div296_election_made:
        # spec §6.5: warn on any depreciated asset locked in by the election
        # (caller must supply current MV via lots; we surface a hint only here)
        warnings.append(
            "Div 296 election locks cost_base_div296 at MV(30-Jun-2026); "
            "depreciated assets eliminate pre-2026 capital loss from Div 296 earnings."
        )

    return TaxView(
        account_type="smsf",
        holdings_count=sum(1 for lot in lots if lot.disposed_at is None),
        realised_gain_aud=sum((g.gain_aud for g in realised_gains), Decimal("0")),
        net_capital_gain=ncg,
        dividends_after_tax=after_tax,
        div296_outcome=div296,
        eligibility_alerts=alerts,
        franking_warnings=warnings,
        cgt_tax_outcome=cgt_tax,
    )
