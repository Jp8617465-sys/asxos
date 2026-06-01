"""
Section 3: Active theses — M-Brief-V2-Sections.

For each active thesis: format a thesis card, compute underlying score,
detect hidden risk. Severity based on revisit overdue / underlying divergence.

SeverityItem levels:
  - red:    revisit overdue
  - yellow: underlying diverging OR revisit due within 7d OR hidden risk
  - green:  all ok
"""
from __future__ import annotations

import time
from datetime import date

from asxos.db import acquire
from asxos.domain.brief.severity import thesis_revisit_overdue
from asxos.domain.brief.types import SectionResult, SectionStatus, SeverityItem, SeverityLevel
from asxos.domain.underlyings.attribution import score_thesis_underlying
from asxos.domain.underlyings.divergence import detect_hidden_risk
from asxos.domain.underlyings.service import get_5d_moves, list_thesis_underlyings

_SECTION = "active_theses"


async def collect_active_theses(as_of: date) -> SectionResult:
    start_ms = int(time.monotonic() * 1000)
    items: list[SeverityItem] = []

    async with acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT thesis_id, symbol, status, opened_at, stop_price, target_price,
                   timeline_days, entry_band_lower, entry_band_upper, revisit_due_at
            FROM theses
            WHERE status = 'active'
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

        for row in rows:
            thesis_id = row["thesis_id"]
            symbol = row["symbol"]
            revisit_due = row["revisit_due_at"]
            opened = row["opened_at"]

            # Underlying score
            thesis_underlyings = await list_thesis_underlyings(conn, thesis_id)
            underlying_ids = [tu.underlying_id for tu in thesis_underlyings]
            moves = await get_5d_moves(conn, underlying_ids, as_of) if underlying_ids else {}
            score = score_thesis_underlying(thesis_underlyings, moves)

            # Overdue check
            overdue_item = thesis_revisit_overdue(
                symbol, revisit_due.date(), as_of, section=_SECTION
            )

            days_since = (as_of - opened.date()).days
            days_to_revisit = (revisit_due.date() - as_of).days

            entry_str = ""
            if row["entry_band_lower"] and row["entry_band_upper"]:
                entry_str = f"Entry: {row['entry_band_lower']}–{row['entry_band_upper']} | "

            timeline_mo = f"{row['timeline_days'] // 30}mo" if row["timeline_days"] else "—"

            msg = (
                f"{symbol} | Active | {days_since}d\n"
                f"{entry_str}"
                f"Stop: {row['stop_price'] or '—'} | Target: {row['target_price'] or '—'} | {timeline_mo}\n"
                f"Underlying: {score.label} (weighted {score.weighted_movement:+.2f}%)\n"
                f"Revisit: {'overdue' if days_to_revisit < 0 else f'due in {days_to_revisit}d'}"
            )

            # Determine severity
            if overdue_item:
                items.append(overdue_item)
            elif score.label == "diverging" or days_to_revisit <= 7:
                items.append(SeverityItem(
                    level=SeverityLevel.yellow, message=msg, section=_SECTION
                ))
            else:
                items.append(SeverityItem(
                    level=SeverityLevel.green, message=msg, section=_SECTION
                ))

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
