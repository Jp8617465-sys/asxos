"""
Aggregator: turns a portfolio + tax config into a TaxView for `asx tax-view`.

Pure function — takes already-loaded holdings, signal/price hints, and the
tax config. The CLI layer handles DB I/O.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from asxos.domain.tax.cgt import days_to_eligibility, net_capital_gain
from asxos.domain.tax.div_296 import div296_liability
from asxos.domain.tax.dividends import (
    after_tax_dividend_individual,
    after_tax_dividend_smsf,
)
from asxos.domain.tax.types import (
    CapitalGain,
    Div296Outcome,
    Dividend,
    HoldingLot,
    IndividualConfig,
    NetCapitalGain,
    SMSFConfig,
    TaxView,
)


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
    if realised_gains:
        ncg = net_capital_gain(
            realised_gains,
            current_year_losses=Decimal("0"),
            carried_forward_losses=config.carried_forward_capital_loss,
            account_type="individual",
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
    if realised_gains:
        ncg = net_capital_gain(
            realised_gains,
            current_year_losses=Decimal("0"),
            carried_forward_losses=config.carried_forward_capital_loss,
            account_type="smsf",
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
    )
