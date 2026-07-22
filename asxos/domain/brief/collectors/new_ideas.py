"""
Section 6: New ideas — M-Brief-V2-Sections.

Research-stage theses (status='research'). Suppressed when the market regime
is risk_off_orderly or risk_off_disorderly — capital preservation takes priority
over new idea evaluation during market stress.

SeverityItem levels:
  - green: research thesis (informational)
Section status:
  - suppressed: risk-off regime active
  - no_data:    no research theses
"""
from __future__ import annotations

import time
from datetime import date

from asxos.db import acquire
from asxos.domain.brief.types import SectionResult, SectionStatus, SeverityItem, SeverityLevel

_SECTION = "new_ideas"
_RISK_OFF_REGIMES = {"risk_off_orderly", "risk_off_disorderly"}


async def collect_new_ideas(as_of: date, regime_label: str | None = None) -> SectionResult:
    """Collect research theses. Suppressed under risk-off regimes.

    regime_label is passed from the market_context collector result to avoid
    a second DB round-trip. If None, current regime is fetched from the DB.
    """
    start_ms = int(time.monotonic() * 1000)

    effective_regime = regime_label

    # Fetch regime from DB only if not provided by caller
    if effective_regime is None:
        async with acquire() as conn:
            row = await conn.fetchrow(
                "SELECT regime_label FROM market_context_current WHERE as_of = $1", as_of
            )
            effective_regime = row["regime_label"] if row else None

    if effective_regime in _RISK_OFF_REGIMES:
        elapsed_ms = int(time.monotonic() * 1000) - start_ms
        return SectionResult(
            name=_SECTION, status=SectionStatus.suppressed,
            items=(), elapsed_ms=elapsed_ms,
            error=f"regime={effective_regime}",
        )

    async with acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT symbol, opened_at, thesis_text
            FROM theses
            WHERE status = 'research'
              AND governance_status = 'approved'
            ORDER BY opened_at DESC
            """
        )

    elapsed_ms = int(time.monotonic() * 1000) - start_ms

    if not rows:
        return SectionResult(
            name=_SECTION, status=SectionStatus.no_data,
            items=(), elapsed_ms=elapsed_ms,
            error="no research theses",
        )

    items: list[SeverityItem] = []
    for row in rows:
        days_in_research = (as_of - row["opened_at"].date()).days
        thesis_snippet = ""
        if row["thesis_text"]:
            thesis_snippet = f"\n{row['thesis_text'][:100]}{'…' if len(row['thesis_text']) > 100 else ''}"
        msg = (
            f"{row['symbol']} | Research | {days_in_research}d"
            f"{thesis_snippet}"
        )
        items.append(SeverityItem(
            level=SeverityLevel.green, message=msg, section=_SECTION
        ))

    return SectionResult(
        name=_SECTION, status=SectionStatus.ok,
        items=tuple(items), elapsed_ms=elapsed_ms,
    )
