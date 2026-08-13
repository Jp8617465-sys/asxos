"""
Section 3: Active theses — M-Brief-V2-Sections.

For each active thesis: format a thesis card, compute underlying score,
detect hidden risk. Severity based on revisit overdue / underlying divergence.

SeverityItem levels:
  - red:    timeline expired (takes priority) OR revisit overdue
  - yellow: underlying diverging OR revisit due within 7d OR hidden risk
  - green:  all ok

**Model-independent by construction (mission P1-04, manifest A5).** The
contamination-isolation model gate and the ``FROM signals`` batch read that fed
each card's ``Model A: <label> | Top drivers: …`` line are gone. Every card now
carries a :class:`~asxos.domain.review.status.ReviewStatus` in their place —
``CLEAR`` / ``ATTENTION`` / ``BLOCKED`` / ``EVIDENCE_THIN`` (packet P1
required-work item 4) — computed from the thesis's own revisit cadence,
timeline and linked underlyings. The severity ladder (red/yellow/green) and the
items this section emits are unchanged. The card *text* has two deliberate
changes: a trailing ``Review: <STATUS>`` line, and an ``Underlying: unavailable``
variant where a fabricated ``+0.00%`` used to print.

**Explicit unknowns (packet P1 required-work item 5).** ``score_thesis_underlying``
returns ``label="mixed", weighted_movement=0`` for a thesis with *no* linked
underlyings, and the same for one whose every underlying has a stale move. Both
read on a card as a measured neutral. This collector distinguishes them: when
there is nothing to measure, the card says ``Underlying: unavailable`` and the
card's review status is ``EVIDENCE_THIN``, never a silent zero.
"""
from __future__ import annotations

import time
from dataclasses import replace
from datetime import date, datetime

from asxos.db import acquire
from asxos.domain.brief.severity import (
    earnings_risk,
    thesis_revisit_overdue,
    thesis_timeline_expired,
)
from asxos.domain.brief.types import SectionResult, SectionStatus, SeverityItem, SeverityLevel
from asxos.domain.review.status import classify
from asxos.domain.underlyings.attribution import score_thesis_underlying
from asxos.domain.underlyings.divergence import detect_hidden_risk
from asxos.domain.underlyings.service import bulk_list_thesis_underlyings, get_5d_moves

_SECTION = "active_theses"


async def collect_active_theses(as_of: date) -> SectionResult:
    start_ms = int(time.monotonic() * 1000)
    items: list[SeverityItem] = []

    async with acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT thesis_id, symbol, status, opened_at, stop_price, target_price,
                   timeline_days, entry_band_lower, entry_band_upper, revisit_due_at,
                   analyst_buy_count, analyst_neutral_count, analyst_sell_count,
                   analyst_consensus_target, next_earnings_date, earnings_notes
            FROM theses
            WHERE status = 'active'
              AND governance_status = 'approved'
            ORDER BY opened_at DESC
            """
        )

        if not rows:
            elapsed_ms = int(time.monotonic() * 1000) - start_ms
            return SectionResult(
                name=_SECTION, status=SectionStatus.no_data,
                items=(), elapsed_ms=elapsed_ms,
                error="no active theses",
            )

        # Batch-load all underlyings and moves in two queries (avoids N+1)
        all_thesis_ids = [r["thesis_id"] for r in rows]
        tu_by_thesis = await bulk_list_thesis_underlyings(conn, all_thesis_ids)
        all_underlying_ids = list({
            tu.underlying_id
            for tus in tu_by_thesis.values()
            for tu in tus
        })
        all_moves = await get_5d_moves(conn, all_underlying_ids, as_of) if all_underlying_ids else {}

        for row in rows:
            thesis_id = row["thesis_id"]
            symbol = row["symbol"]
            revisit_due = row["revisit_due_at"]
            opened = row["opened_at"]

            # Underlying score (uses pre-fetched data)
            thesis_underlyings = tu_by_thesis.get(thesis_id, [])
            moves = {tu.underlying_id: all_moves.get(tu.underlying_id) for tu in thesis_underlyings}
            score = score_thesis_underlying(thesis_underlyings, moves)

            # Overdue check
            overdue_item = thesis_revisit_overdue(
                symbol, revisit_due.date(), as_of, section=_SECTION
            )

            # Timeline expiry check
            expiry_item = thesis_timeline_expired(
                symbol, opened.date(), row["timeline_days"], as_of, section=_SECTION
            )

            days_since = (as_of - opened.date()).days
            days_to_revisit = (revisit_due.date() - as_of).days

            entry_str = ""
            if row["entry_band_lower"] and row["entry_band_upper"]:
                entry_str = f"Entry: {row['entry_band_lower']}–{row['entry_band_upper']} | "

            timeline_mo = f"{row['timeline_days'] // 30}mo" if row["timeline_days"] else "—"

            # A weighted movement of 0.00% means one of two very different
            # things: every underlying moved and they cancelled, or there was
            # nothing to measure. Only the first is a result. `score` cannot tell
            # them apart (it returns "mixed"/0 for both), so decide here from the
            # inputs and say "unavailable" rather than print a fabricated neutral.
            measured = any(move is not None for move in moves.values())
            if measured:
                underlying_line = (
                    f"Underlying: {score.label} (weighted {score.weighted_movement:+.2f}%)"
                )
                card_unknowns: list[str] = []
            else:
                underlying_line = "Underlying: unavailable — no current 5d move to measure"
                card_unknowns = [
                    "no linked underlying has a current 5d move"
                    if thesis_underlyings
                    else "no underlyings linked to this thesis"
                ]

            # The card's own review state (packet P1 item 4). Advisory evidence
            # about the thesis's upkeep — never a direction to act.
            card_attention: list[str] = []
            if expiry_item and expiry_item.level == SeverityLevel.red:
                card_attention.append("timeline expired")
            if overdue_item:
                card_attention.append("revisit overdue")
            if measured and score.label == "diverging":
                card_attention.append("underlyings diverging")
            if days_to_revisit <= 7:
                card_attention.append("revisit due within 7d")
            review = classify(attention=card_attention, unknowns=card_unknowns)

            msg = (
                f"{symbol} | Active | {days_since}d\n"
                f"{entry_str}"
                f"Stop: {row['stop_price'] or '—'} | Target: {row['target_price'] or '—'} | {timeline_mo}\n"
                f"{underlying_line}\n"
                f"Revisit: {'overdue' if days_to_revisit < 0 else f'due in {days_to_revisit}d'}"
            )

            # Determine severity — expiry and overdue both red; expiry takes priority
            if expiry_item and expiry_item.level == SeverityLevel.red:
                card = expiry_item
            elif overdue_item:
                card = overdue_item
            elif expiry_item:
                card = expiry_item
            elif score.label == "diverging" or days_to_revisit <= 7:
                card = SeverityItem(
                    level=SeverityLevel.yellow, message=msg, section=_SECTION
                )
            else:
                card = SeverityItem(
                    level=SeverityLevel.green, message=msg, section=_SECTION
                )
            # Append the review state to whichever card won, not to `msg`. The
            # red branches render the severity helper's own message and never
            # touch `msg` at all — so a Review line written into `msg` would be
            # invisible on exactly the overdue and expired cards that most need
            # a state on them.
            items.append(
                replace(card, message=f"{card.message}\nReview: {review.status}")
            )

            # Earnings risk
            next_ed = row.get("next_earnings_date")
            earnings_date = next_ed.date() if isinstance(next_ed, datetime) else next_ed
            earnings_item = earnings_risk(
                symbol,
                earnings_date,
                cgt_date=None,
                as_of=as_of,
                section=_SECTION,
            )
            if earnings_item:
                items.append(earnings_item)

            # Hidden risk alert
            hidden = detect_hidden_risk(row["status"], score)
            if hidden:
                items.append(SeverityItem(
                    level=SeverityLevel.yellow, message=hidden, section=_SECTION
                ))

    elapsed_ms = int(time.monotonic() * 1000) - start_ms
    return SectionResult(
        name=_SECTION, status=SectionStatus.ok,
        items=tuple(items), elapsed_ms=elapsed_ms,
    )
