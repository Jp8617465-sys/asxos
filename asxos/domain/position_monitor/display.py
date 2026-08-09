"""
Terminal display for MonitorResult — M-Position-Monitor.

format_monitor(result) → str   (plain text; matches hubs_monitor.py output style)
format_history(runs)   → str   (rich-compatible table markup)

No I/O; pure functions. The CLI layer calls console.print(format_monitor(result)).
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from asxos.domain.position_monitor.types import MonitorInput, MonitorResult
from asxos.domain.prices.fx import is_foreign_symbol

# Canonical, version-stamped regime thresholds — quoted (never restated) so the
# monitor's prose can't drift from the classifier (red-team register #18). The
# private-name import is deliberate: these are the single source of truth and
# D6's classifier v1.1 work will re-export them publicly.
from asxos.domain.regime.classifier import (
    _AVIX_RISK_OFF as _AVIX_RISK_OFF,
)
from asxos.domain.regime.classifier import (
    _HY_OAS_ELEVATED as _HY_OAS_ELEVATED,
)
from asxos.domain.regime.classifier import (
    CLASSIFIER_VERSION,
)
from asxos.domain.tax.cgt import cgt_break_even_price
from asxos.domain.themes.stage_classifier import StageThresholds

_T = StageThresholds()


def _break_even_lot(inp: MonitorInput) -> tuple[Decimal, date] | None:
    """Per-share AUD cost + acquired of the earliest-still-ineligible lot, or None.

    The break-even is a single-lot CGT-friction comparison (sell now at the full
    rate vs wait for the discount on that lot), so it must use ONE lot's economics
    — the earliest-maturing ineligible lot, the one with a live deferral decision —
    NOT the position weighted-average `cost_native`, which would mix two lots'
    costs against one lot's acquisition date and produce a meaningless number.

    The returned cost is the lot's AUD CGT base per share (`cost_base_normal`):
    §5.4 requires both legs in one currency, and CGT math is AUD, so the caller
    must supply an AUD price leg (native close ÷ AUDUSD for foreign symbols).
    """
    pending = [lot for lot in inp.lots if not lot.is_eligible]  # lots are acquired ASC
    if not pending:
        return None
    lot = pending[0]
    return lot.cost_base_normal / lot.quantity, lot.acquired_at


def _break_even_price_leg(inp: MonitorInput) -> Decimal | None:
    """The §5.4 price leg in AUD, or None when it cannot be honestly produced.

    Previously the native close was passed straight in against the AUD lot cost —
    the documented R10 currency error, which made `cgt_break_even_price` silently
    return None for every foreign lot (AUD cost/share > USD price) and suppressed
    the hint on exactly the position that needed it (2026-08-09 red-team register
    #11). A missing FX rate now yields a NAMED refusal line, never a silent skip.
    """
    if not is_foreign_symbol(inp.symbol):
        return inp.current_price  # .AU: native IS AUD
    if inp.fx_rate_audusd is None or inp.fx_rate_audusd == 0:
        return None
    return inp.current_price / inp.fx_rate_audusd


_STAGE_EMOJI: dict[str, str] = {
    "early": "🌱",
    "early-institutional": "🔵",
    "broad-institutional": "🔵🔵",
    "mainstream": "📈",
    "late-retail": "⚠️",
    "mature": "🔴",
    "insufficient_data": "❓",
}
_SCORE_EMOJI: dict[str, str] = {
    "confirming": "✅",
    "mixed": "⚡",
    "diverging": "❌",
}
_STATUS_ICON: dict[str, str] = {
    "confirmed": "✅",
    "ON TRACK": "✅",
    "ELIGIBLE NOW": "✅",
    "AT TARGET": "🎯",
    "active": "🟡",
    "available": "🟡",
    "pending": "⏳",
    "in progress": "🔵",
    "TRIGGERED": "🔴",
    "risky": "⚠️",
}


def format_monitor(result: MonitorResult) -> str:
    inp = result.inputs
    lines: list[str] = []

    # ── Header ─────────────────────────────────────────────────────────────
    price = inp.current_price
    lines.append("")
    header_date = str(inp.as_of)
    intraday_flag = " [INTRADAY]" if inp.price_type == "intraday" else ""
    # Pad to fixed width — account for intraday flag in the title
    pad = max(0, 65 - len(header_date) - len(intraday_flag))
    lines.append(f"╔{'═' * 66}╗")
    lines.append(
        f"║  {inp.symbol}{intraday_flag} — Weekly Monitor{' ' * (pad - 13)}{header_date}  ║"
    )

    if inp.cost_native is not None and inp.shares is not None:
        # Native-vs-native legs (R10): cost_native shares the symbol's listing
        # currency with current_price, so this P&L is currency-consistent.
        unrealised_pct = (
            (price - inp.cost_native) / inp.cost_native * Decimal("100")
        ).quantize(Decimal("0.1"))
        sign = "+" if unrealised_pct >= 0 else ""
        lines.append(
            f"║  Position: {inp.shares}×  Cost: ${inp.cost_native}  "
            f"Current: ${price}  P&L: {sign}{unrealised_pct}%"
        )
        if inp.cgt_date:
            days_to_cgt = (inp.cgt_date - inp.as_of).days
            lines.append(
                f"║  CGT discount in: {max(0, days_to_cgt)} days  ({inp.cgt_date})"
            )
        elif inp.all_eligible:
            lines.append("║  CGT discount: all lots eligible now")

    lines.append(f"╚{'═' * 66}╝")
    lines.append("")

    # ── Stage classifier ───────────────────────────────────────────────────
    lines.append("── STAGE CLASSIFIER " + "─" * 47)
    stage_ico = _STAGE_EMOJI.get(result.stage_label, "")
    lines.append(f"  Stage: {stage_ico} {result.stage_label.upper()}")
    lines.append("")
    lines.append("  Signals status:")

    above_50 = price > inp.ma_50d
    above_200 = price > inp.ma_200d
    retail_spike = inp.retail_ratio >= _T.retail_mention_spike_pct
    sentiment_high = inp.news_sentiment >= _T.news_sentiment_high
    momentum_slow = inp.avg_weekly_move < _T.momentum_slowdown_threshold

    lines.append(
        f"    {'✅' if above_50 else '❌'} Above 50d MA   "
        f"${price} {'>' if above_50 else '<'} ${inp.ma_50d}  "
        f"(need >${inp.ma_50d} to stay emerging)"
    )
    lines.append(
        f"    {'✅' if above_200 else '❌'} Above 200d MA  "
        f"${price} {'>' if above_200 else '<'} ${inp.ma_200d}  "
        f"(need >${inp.ma_200d} for MAINSTREAM)"
    )
    retail_note = "⚠ high retail — watch for fade" if retail_spike else "normalising — good"
    lines.append(
        f"    {'✅' if retail_spike else '❌'} Retail spike   "
        f"{inp.retail_ratio}× 90d avg  (threshold: {_T.retail_mention_spike_pct}×)  "
        f"{retail_note}"
    )
    lines.append(
        f"    {'✅' if sentiment_high else '❌'} Sentiment high  "
        f"{inp.news_sentiment}  (threshold: {_T.news_sentiment_high})"
    )
    mom_icon = "⚠" if momentum_slow else "  "
    lines.append(
        f"    {mom_icon} Momentum slow  "
        f"{inp.avg_weekly_move:.0%}/wk  "
        f"(< {_T.momentum_slowdown_threshold:.0%} = mature signal"
        + (" — firing" if momentum_slow else " — not firing")
        + ")"
    )

    # Volume and short interest (optional — only shown when provided)
    if inp.volume_vs_avg_pct is not None:
        vol_note = (
            "elevated — confirms move" if inp.volume_vs_avg_pct > Decimal("150")
            else "below avg — shake-out likely"
        )
        lines.append(
            f"    📊 Volume:      {inp.volume_vs_avg_pct:.0f}% of 30d avg  ({vol_note})"
        )
    if inp.short_interest_pct is not None:
        si_note = "elevated" if inp.short_interest_pct > Decimal("5") else "normal"
        lines.append(
            f"    📉 Short int:   {inp.short_interest_pct:.1f}% of float  ({si_note})"
        )

    lines.append("")
    lines.append("  What would change the stage:")
    pct_to_200d = (
        (inp.ma_200d - price) / price * Decimal("100")
    ).quantize(Decimal("0.1"))
    lines.append(
        f"    → MAINSTREAM:   price crosses ${inp.ma_200d}  (you're {pct_to_200d}% away)"
    )
    lines.append(
        f"    → EARLY-INST:   retail ratio falls below "
        f"{_T.retail_mention_spike_pct}× AND sentiment stays high"
    )
    lines.append(
        f"    → EARLY:        retail fades AND price breaks below 50d MA (${inp.ma_50d})"
    )

    # ── Underlying attribution ─────────────────────────────────────────────
    lines.append("")
    lines.append("── UNDERLYING ATTRIBUTION " + "─" * 41)
    score_ico = _SCORE_EMOJI.get(result.underlying_label, "")
    lines.append(
        f"  Score: {score_ico} {result.underlying_label.upper()}  "
        f"(weighted movement: {result.weighted_movement:+.2f}%)"
    )
    lines.append("")
    for comp in result.component_moves:
        direction_note = (
            "falling = good" if comp["code"] == "vix" else "tightening = good"
        )
        move = comp.get("move_5d_pct", "n/a")
        contrib = comp.get("contribution", "n/a")
        contrib_f = float(contrib) if contrib not in (None, "n/a") else 0.0
        lines.append(
            f"  {'✅' if contrib_f > 0 else '❌'} {comp['code']:<12} "
            f"5d move: {move}%   contribution: {contrib}%   ({direction_note})"
        )
    lines.append("")
    lines.append("  What would flip to DIVERGING:")
    lines.append("    → VIX spikes above ~22–25 (risk-off event)")
    lines.append("    → US HY OAS widens above ~350bps (credit stress)")
    lines.append("    → Either 5d move turns positive (vol rising / spreads widening)")

    # ── Cross-layer ────────────────────────────────────────────────────────
    lines.append("")
    lines.append("── CROSS-LAYER " + "─" * 52)
    if inp.regime_label:
        lines.append(f"  Regime: {inp.regime_label}")
    if inp.analyst_consensus_target is not None:
        b = inp.analyst_buy_count or 0
        n = inp.analyst_neutral_count or 0
        s = inp.analyst_sell_count or 0
        lines.append(f"  Consensus: {b}B/{n}N/{s}S  target: ${inp.analyst_consensus_target}")
    for obs in result.cross_layer_obs:
        lines.append(f"  · {obs}")
    if not result.cross_layer_obs:
        lines.append("  (no cross-layer signals fired)")

    # ── Scenarios ──────────────────────────────────────────────────────────
    if result.scenarios:
        lines.append("")
        lines.append("── SCENARIO CONFIRMATION MATRIX " + "─" * 35)
        for sc in result.scenarios:
            ico = _STATUS_ICON.get(sc.status, "·")
            lines.append(f"\n  {ico} Scenario {sc.code}: {sc.name}  [{sc.status}]")
            lines.append(f"     Confirmation:  {sc.confirmation}")
            lines.append(f"     Invalidation:  {sc.invalidation}")

    # ── Decision ───────────────────────────────────────────────────────────
    lines.append("")
    lines.append("── WEEKLY DECISION " + "─" * 48)
    lines.append("")
    lines.append(f"  Stage:      {result.stage_label.upper()} {_STAGE_EMOJI.get(result.stage_label,'')}")
    lines.append(
        f"  Underlying: {result.underlying_label.upper()} "
        f"{_SCORE_EMOJI.get(result.underlying_label,'')} "
        f"({result.weighted_movement:+.2f}%)"
    )
    if inp.stop_price:
        pct_to_stop = (
            (price - inp.stop_price) / price * Decimal("100")
        ).quantize(Decimal("0.1"))
        lines.append(f"  Stop gap:   {pct_to_stop}% above ${inp.stop_price}")
    lines.append(f"  To 200d MA: {pct_to_200d}% above current price")
    be_lot = _break_even_lot(inp)
    if be_lot is not None and inp.cgt_date is not None:
        lot_cost, lot_acquired = be_lot
        price_aud = _break_even_price_leg(inp)
        if price_aud is None:
            # Named refusal (register #11 acceptance: never a silent None on a
            # foreign lot) — the hint needs an AUDUSD rate that isn't available.
            lines.append(
                "  CGT break-even: unavailable — no AUDUSD rate to convert the"
                " price leg (both §5.4 legs must be AUD)"
            )
        else:
            be = cgt_break_even_price(
                price_aud, lot_cost,
                inp.account_type, lot_acquired, inp.as_of,
            )
            if be is not None:
                days = max(0, (inp.cgt_date - inp.as_of).days)
                lines.append(
                    f"  CGT break-even: A${be} — selling below this (AUD) today"
                    f" loses vs holding to {inp.cgt_date} ({days}d)"
                )
    if inp.price_type == "intraday" and inp.stop_price is not None:
        pct_to_stop_intraday = (
            (price - inp.stop_price) / price * Decimal("100")
        ).quantize(Decimal("0.1"))
        if pct_to_stop_intraday < Decimal("2"):
            lines.append(
                f"  ⚠ INTRADAY — within {pct_to_stop_intraday}% of stop ${inp.stop_price}."
                " Confirm on close before acting."
            )
    lines.append("")

    if inp.cgt_date:
        days_to_cgt = (inp.cgt_date - inp.as_of).days
        # 2026-08-09 (red-team register #18, D5/D6): this box previously said
        # "HOLD — CGT clock ticking. Macro confirming." unconditionally — an
        # action verb about a live position (the wording firewall strips those
        # from every other discipline surface) plus a static macro claim that
        # printed straight through risk-off days, and watch-thresholds ("VIX
        # below 20", "OAS below 300bps") that existed nowhere else in the
        # system. The header now states the COMPUTED macro read, and the
        # threshold line quotes the regime classifier's canonical, version-
        # stamped constants so the numbers cannot drift from the classifier.
        macro_line = f"Macro: {result.underlying_label} (computed this run)."
        watch = [
            f"CGT clock: {max(0, days_to_cgt)}d to discount. {macro_line}",
            "",
            "Watch this week:",
            f"· Price vs 50d MA (${inp.ma_50d})",
            f"· Retail ratio: watch for fade below {_T.retail_mention_spike_pct}×",
            f"· Regime flips risk-off above A-VIX {_AVIX_RISK_OFF}"
            f" / US HY OAS {_HY_OAS_ELEVATED}bps ({CLASSIFIER_VERSION})",
        ]
        width = max(len(w) for w in watch) + 2
        lines.append(f"  ┌{'─' * width}┐")
        for w in watch:
            lines.append(f"  │ {w.ljust(width - 2)} │")
        lines.append(f"  └{'─' * width}┘")
        lines.append("")
        lines.append(f"  CGT discount: {max(0, days_to_cgt)} days to {inp.cgt_date}")
    elif inp.all_eligible:
        lines.append("  CGT discount: all open lots are already eligible.")
    else:
        lines.append("  No active thesis context — showing classifier outputs only.")

    lines.append("")
    return "\n".join(lines)


def format_history(runs: list[dict[str, Any]]) -> str:
    """Plain-text table of historical runs."""
    if not runs:
        return "No monitor runs found for this symbol."

    header = (
        f"{'DATE':<12}  {'PRICE':>8}  {'STAGE':<22}  {'UNDERLYING':<12}  "
        f"{'WTDMOV':>8}  {'RETAIL':>8}  {'SENTMT':>8}"
    )
    sep = "─" * len(header)
    lines = [sep, header, sep]
    for r in runs:
        stage = (r.get("stage_label") or "")[:22]
        underlying = (r.get("underlying_label") or "")[:12]
        wm = float(r.get("weighted_movement") or 0)
        lines.append(
            f"{r['as_of']!s:<12}  "
            f"${float(r['current_price']):>7.2f}  "
            f"{stage:<22}  "
            f"{underlying:<12}  "
            f"{wm:>+7.2f}%  "
            f"{float(r['retail_ratio']):>7.2f}×  "
            f"{float(r['news_sentiment']):>7.2f}"
        )
    lines.append(sep)
    return "\n".join(lines)
