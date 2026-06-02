"""
Section 2: Market context — M-Brief-V2-Sections.

Reads from market_context_current view for the as_of date.
Returns no_data if no row exists (market context job has not run yet).

SeverityItems:
  - red/yellow: risk-off regime signals
  - green: regime label + key indicators (ASX200, AVIX, AUD/USD)
"""
from __future__ import annotations

import time
from datetime import date
from decimal import Decimal

from asxos.db import acquire
from asxos.domain.brief.severity import regime_warning
from asxos.domain.brief.types import SectionResult, SectionStatus, SeverityItem, SeverityLevel

_SECTION = "market_context"


async def collect_market_context(as_of: date) -> SectionResult:
    start_ms = int(time.monotonic() * 1000)

    async with acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT regime_label, asx200_close, asx200_daily_change_pct,
                   avix, aud_usd, ingestion_warnings
            FROM market_context_current
            WHERE as_of = $1
            """,
            as_of,
        )

    elapsed_ms = int(time.monotonic() * 1000) - start_ms

    if row is None:
        return SectionResult(
            name=_SECTION, status=SectionStatus.no_data,
            items=(), elapsed_ms=elapsed_ms,
            error="no market context for this date (ingest_market_context may not have run)",
        )

    label = row["regime_label"] or "neutral_mixed"
    items: list[SeverityItem] = []

    # Regime severity
    regime_item = regime_warning(label, section=_SECTION)
    if regime_item:
        items.append(regime_item)
    else:
        items.append(SeverityItem(
            level=SeverityLevel.green,
            message=f"Regime: {label}",
            section=_SECTION,
        ))

    # Key indicators (informational, green)
    asx200 = row.get("asx200_close")
    asx200_chg = row.get("asx200_daily_change_pct")
    avix = row.get("avix")
    aud_usd = row.get("aud_usd")

    indicator_parts: list[str] = []
    if asx200 is not None:
        chg_str = f" ({Decimal(str(asx200_chg)):+.2f}%)" if asx200_chg is not None else ""
        indicator_parts.append(f"ASX200 {Decimal(str(asx200)):,.0f}{chg_str}")
    if avix is not None:
        indicator_parts.append(f"AVIX {Decimal(str(avix)):.1f}")
    if aud_usd is not None:
        indicator_parts.append(f"AUD/USD {Decimal(str(aud_usd)):.4f}")

    if indicator_parts:
        items.append(SeverityItem(
            level=SeverityLevel.green,
            message=" · ".join(indicator_parts),
            section=_SECTION,
        ))

    return SectionResult(
        name=_SECTION, status=SectionStatus.ok,
        items=tuple(items), elapsed_ms=elapsed_ms,
        metadata={"regime_label": label},
    )
