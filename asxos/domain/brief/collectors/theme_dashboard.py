"""
Section 8: Theme dashboard — M-Brief-V2-Sections.

Reads active themes + their holdings + linked theses. Flags when
stage_suggested diverges from stage (AI classifier has a new recommendation).

SeverityItem levels:
  - yellow: stage_suggested != stage (AI disagrees with user-confirmed stage)
  - green:  all ok — theme summary
Section status:
  - no_data: no themes defined
"""
from __future__ import annotations

import time
from datetime import date

from asxos.db import acquire
from asxos.domain.brief.types import SectionResult, SectionStatus, SeverityItem, SeverityLevel

_SECTION = "theme_dashboard"


async def collect_theme_dashboard(as_of: date) -> SectionResult:
    start_ms = int(time.monotonic() * 1000)
    items: list[SeverityItem] = []

    async with acquire() as conn:
        themes = await conn.fetch(
            """
            SELECT t.theme_id, t.theme_code, t.stage, t.stage_suggested,
                   t.conviction, t.adjacency,
                   COUNT(DISTINCT th.symbol) AS holding_count,
                   COUNT(DISTINCT theses.thesis_id) AS thesis_count
            FROM themes t
            LEFT JOIN theme_holdings th ON th.theme_id = t.theme_id
            LEFT JOIN theses ON theses.symbol = th.symbol
                AND theses.status IN ('active', 'watching', 'research')
            GROUP BY t.theme_id, t.theme_code, t.stage, t.stage_suggested,
                     t.conviction, t.adjacency
            ORDER BY t.theme_code
            """
        )

    elapsed_ms = int(time.monotonic() * 1000) - start_ms

    if not themes:
        return SectionResult(
            name=_SECTION, status=SectionStatus.no_data,
            items=(), elapsed_ms=elapsed_ms,
            error="no themes defined",
        )

    for row in themes:
        theme_code = row["theme_code"]
        stage = row["stage"] or "—"
        stage_suggested = row["stage_suggested"]
        conviction = row["conviction"] or "—"
        holding_count = row["holding_count"] or 0
        thesis_count = row["thesis_count"] or 0

        stage_str = stage
        if stage_suggested and stage_suggested != stage:
            stage_str = f"{stage} → {stage_suggested} (AI suggests)"
            level = SeverityLevel.yellow
        else:
            level = SeverityLevel.green

        msg = (
            f"{theme_code} | Stage: {stage_str} | Conviction: {conviction}\n"
            f"  {holding_count} holding(s), {thesis_count} thesis(es)"
        )
        items.append(SeverityItem(level=level, message=msg, section=_SECTION))

    return SectionResult(
        name=_SECTION, status=SectionStatus.ok,
        items=tuple(items), elapsed_ms=elapsed_ms,
    )
