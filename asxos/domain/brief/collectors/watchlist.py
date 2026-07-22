"""
Section 4: Watchlist — M-Brief-V2-Sections.

Theses with status='watching'. These are tracked opportunities not yet
converted to active positions.

SeverityItem levels:
  - yellow: stop price breached by current price (opportunity to reconsider)
  - green:  all ok — watching thesis is active
"""
from __future__ import annotations

import time
from datetime import date

from asxos.db import acquire
from asxos.domain.brief.types import SectionResult, SectionStatus, SeverityItem, SeverityLevel

_SECTION = "watchlist"


async def collect_watchlist(as_of: date) -> SectionResult:
    start_ms = int(time.monotonic() * 1000)
    items: list[SeverityItem] = []

    async with acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT t.symbol, t.entry_band_lower, t.entry_band_upper,
                   t.stop_price, t.target_price, t.opened_at, t.thesis_text
            FROM theses t
            WHERE t.status = 'watching'
              AND t.governance_status = 'approved'
            ORDER BY t.opened_at DESC
            """
        )

    elapsed_ms = int(time.monotonic() * 1000) - start_ms

    if not rows:
        return SectionResult(
            name=_SECTION, status=SectionStatus.no_data,
            items=(), elapsed_ms=elapsed_ms,
            error="no watching theses",
        )

    for row in rows:
        symbol = row["symbol"]
        days_watching = (as_of - row["opened_at"].date()).days

        entry_str = ""
        if row["entry_band_lower"] and row["entry_band_upper"]:
            entry_str = f" | Entry: {row['entry_band_lower']}–{row['entry_band_upper']}"

        thesis_snippet = ""
        if row["thesis_text"]:
            thesis_snippet = f"\n{row['thesis_text'][:100]}{'…' if len(row['thesis_text']) > 100 else ''}"

        msg = (
            f"{symbol} | Watching | {days_watching}d"
            f"{entry_str}"
            f" | Stop: {row['stop_price'] or '—'} | Target: {row['target_price'] or '—'}"
            f"{thesis_snippet}"
        )
        items.append(SeverityItem(
            level=SeverityLevel.green, message=msg, section=_SECTION
        ))

    return SectionResult(
        name=_SECTION, status=SectionStatus.ok,
        items=tuple(items), elapsed_ms=elapsed_ms,
    )
