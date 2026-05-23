"""
Loss-harvest tagging for the M13 portfolio overlay (M13.5).

Covers spec §5.2 (loss-harvest tagging) only. The §5.1 boundary-defer logic
was moved to M13.6 (compute_deltas) per plan amendment I.4 so that reductions,
full exits, and universe_inactive forced-sells all receive the same treatment.

Part IVA / TR 2008/1 disclaimer (plan amendment I.5):
    The rationale_tags['reason']='loss_harvest' tag is INFORMATION ONLY.
    It does not endorse harvesting; it does not assess wash-sale risk under
    TR 2008/1; it does not advise on Part IVA ITAA36 application. The user
    (James) is solely responsible for ATO compliance on any rebuy after a
    harvest sale. The system does not track or warn on rebuy timing.

All arithmetic is Decimal; no numpy (plan Part C).
"""
from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from asxos.domain.portfolio.types import HoldingSnapshot, ProposedTrade


def near_boundary_lots(
    holdings: list[HoldingSnapshot],
    window_days: int = 30,
) -> dict[str, list[HoldingSnapshot]]:
    """Return lots within ``window_days`` of CGT discount eligibility, grouped by symbol.

    Spec §5.1 (calendar arithmetic): a lot is *near-boundary* if::

        0 < days_to_cgt_discount <= window_days

    Lots with ``days_to_cgt_discount == 0`` are already CGT-discount-eligible
    (≥ 12 months held) and are excluded — no deferral benefit remains; they
    already qualify for the 50% / 33⅓% discount at disposal.

    The returned dict contains only symbols with at least one near-boundary lot.
    An empty dict means no holdings are within the window.
    """
    result: dict[str, list[HoldingSnapshot]] = {}
    for h in holdings:
        if 0 < h.days_to_cgt_discount <= window_days:
            result.setdefault(h.symbol, []).append(h)
    return result


def unrealised_losses(
    holdings: list[HoldingSnapshot],
) -> dict[str, list[HoldingSnapshot]]:
    """Return lots with an unrealised loss, grouped by symbol.

    Spec §5.2: a lot has an unrealised loss when::

        current_price_aud × quantity < cost_base_normal

    Lots exactly at cost (no gain, no loss) are excluded — there is nothing to
    harvest. The returned dict maps symbol → [lot, ...] for symbols where at
    least one lot is loss-making. Gain lots on the same symbol are omitted.
    """
    result: dict[str, list[HoldingSnapshot]] = {}
    for h in holdings:
        market_value = h.current_price_aud * h.quantity
        if market_value < h.cost_base_normal:
            result.setdefault(h.symbol, []).append(h)
    return result


def tag_loss_harvest(
    trades: list[ProposedTrade],
    losses: dict[str, list[HoldingSnapshot]],
) -> list[ProposedTrade]:
    """Populate rationale_tags and lot_hints on sell trades for loss-making symbols.

    For each sell trade on a symbol present in ``losses`` (spec §5.2):

    - ``rationale_tags['reason']``      → ``'loss_harvest'``
    - ``rationale_tags['spec_ref']``    → ``'§5.2'``
    - ``lot_hints['preferred_lot_ids']`` → lot_ids sorted **largest loss first**
      (ascending unrealised gain: most negative unrealised gain = largest loss at
      the front of the list)

    Part IVA / TR 2008/1 disclaimer (plan amendment I.5):
        This tag is INFORMATION ONLY. It does not endorse harvesting; it does not
        assess wash-sale risk under TR 2008/1; it does not advise on Part IVA
        ITAA36 application. The user is solely responsible for ATO compliance on
        any rebuy after a harvest sale. The system does not track or warn on
        rebuy timing.

    Invariants (no-new-names, sum-preserving):
    - The symbol set in the returned list equals the symbol set in the input.
    - No trade's ``delta_qty`` or ``delta_aud`` is modified — tag-only operation.
    - Trades that are not sells, or sells on symbols not in ``losses``, pass
      through unchanged.
    """
    result: list[ProposedTrade] = []
    for trade in trades:
        if trade.side != "sell" or trade.symbol not in losses:
            result.append(trade)
            continue

        # Sort loss lots: ascending unrealised gain = largest loss first.
        loss_lots = losses[trade.symbol]
        sorted_lots = sorted(
            loss_lots,
            key=lambda h: h.current_price_aud * h.quantity - h.cost_base_normal,
        )

        tags = dict(trade.rationale_tags)
        tags["reason"] = "loss_harvest"
        tags["spec_ref"] = "§5.2"

        hints = dict(trade.lot_hints)
        hints["preferred_lot_ids"] = [h.lot_id for h in sorted_lots]

        result.append(replace(trade, rationale_tags=tags, lot_hints=hints))

    return result
