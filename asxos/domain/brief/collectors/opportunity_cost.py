"""
Section 10: Opportunity cost — M-Brief-V2-Sections.

Reads pre-computed CGT-adjusted opportunity-cost scenarios. Returns no_data
gracefully when the table does not yet exist (Phase 5 migration adds it) or
when no scenarios have been computed.

SeverityItem levels:
  - yellow: an alternative's *absolute* CGT-adjusted net expected return exceeds
            5%. This is a LEVEL screen, NOT a delta vs the current holding — no
            current-holding baseline is fetched or subtracted here.
  - green:  no alternative clears the absolute net-return level.
Section status:
  - no_data: table not yet populated (Phase 5 not yet run)

NOTE (the real delta is a Phase-5 producer responsibility): a true
"advantage over the current holding" requires the held position's net expected
return on the SAME CGT-adjusted basis. That belongs in a
`current_net_expected_return` column on `opportunity_cost_scenarios`, populated
by the Phase-5 producer (which already applies the CGT-friction model). The
collector cannot reconstruct it from `signals.expected_return` (gross / different
horizon) or `theses.target` (a price, not a return) without manufacturing a delta
from incomparable quantities. Until that column exists this stays a level screen.
See docs/design-med-2026-06-28.md Item 2.
"""
from __future__ import annotations

import time
from datetime import date
from decimal import Decimal

from asxos.db import acquire
from asxos.domain.brief.types import SectionResult, SectionStatus, SeverityItem, SeverityLevel

_SECTION = "opportunity_cost"
# Absolute net-return LEVEL above which an alternative is flagged yellow. NOT a
# delta vs the current holding (see the module docstring) — renamed from the
# misleading `_MEANINGFUL_DELTA` to reflect what the code actually tests.
_MEANINGFUL_NET_LEVEL = Decimal("0.05")


async def collect_opportunity_cost(as_of: date) -> SectionResult:
    start_ms = int(time.monotonic() * 1000)

    try:
        async with acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT oc.thesis_id, t.symbol,
                       oc.alternative_symbol, oc.alternative_source,
                       oc.gross_expected_return, oc.estimated_cgt_friction,
                       oc.net_expected_return, oc.notes
                FROM opportunity_cost_scenarios oc
                JOIN theses t ON t.thesis_id = oc.thesis_id
                WHERE oc.as_of = $1
                  AND t.status = 'active'
                ORDER BY oc.net_expected_return DESC
                """,
                as_of,
            )
    except Exception as exc:
        # Table does not exist yet (Phase 5 migration pending)
        elapsed_ms = int(time.monotonic() * 1000) - start_ms
        if "does not exist" in str(exc) or "relation" in str(exc).lower():
            return SectionResult(
                name=_SECTION, status=SectionStatus.no_data,
                items=(), elapsed_ms=elapsed_ms,
                error="opportunity_cost_scenarios table not yet created (Phase 5 pending)",
            )
        raise

    elapsed_ms = int(time.monotonic() * 1000) - start_ms

    if not rows:
        return SectionResult(
            name=_SECTION, status=SectionStatus.no_data,
            items=(), elapsed_ms=elapsed_ms,
            error="no opportunity cost scenarios computed for this date",
        )

    items: list[SeverityItem] = []
    for row in rows:
        symbol = row["symbol"]
        alt = row["alternative_symbol"]
        source = row["alternative_source"]
        gross = row["gross_expected_return"]
        cgt_friction = row["estimated_cgt_friction"]
        net = row["net_expected_return"]
        notes = row["notes"] or ""

        gross_str = f"{Decimal(str(gross)):+.1%}" if gross is not None else "—"
        cgt_str = f"{Decimal(str(cgt_friction)):.1%}" if cgt_friction is not None else "—"
        net_str = f"{Decimal(str(net)):+.1%}" if net is not None else "—"

        msg = (
            f"{symbol} → {alt} ({source})\n"
            f"  Gross: {gross_str} | CGT friction: {cgt_str} | Net: {net_str}"
        )
        if notes:
            msg += f"\n  {notes}"

        level = (
            SeverityLevel.yellow
            if net is not None and Decimal(str(net)) > _MEANINGFUL_NET_LEVEL
            else SeverityLevel.green
        )
        items.append(SeverityItem(level=level, message=msg, section=_SECTION))

    return SectionResult(
        name=_SECTION, status=SectionStatus.ok,
        items=tuple(items), elapsed_ms=elapsed_ms,
    )
