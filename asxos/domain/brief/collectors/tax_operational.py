"""
Section 9: Tax and regulatory — M-Brief-Skeleton.

Queries:
  - holding_lots for lots approaching the 12-month CGT boundary (30-day window)
  - regulatory_events for recent hits on current holdings

Converts to SeverityItems via severity.cgt_boundary_approaching().
"""
from __future__ import annotations

import time
from datetime import date
from typing import Any

from asxos.domain.brief.severity import cgt_boundary_approaching
from asxos.domain.brief.types import SectionResult, SectionStatus, SeverityItem, SeverityLevel
from asxos.domain.tax.cgt import days_to_eligibility

_SECTION = "tax_operational"


async def collect_tax_operational(conn: Any, as_of: date) -> SectionResult:
    start_ms = int(time.monotonic() * 1000)
    items: list[SeverityItem] = []

    # CGT boundary alerts
    try:
        lot_rows = await conn.fetch(
            """
            SELECT id, symbol, acquired_at
            FROM current_holdings
            ORDER BY acquired_at
            """
        )
        for r in lot_rows:
            days = days_to_eligibility(r["acquired_at"], as_of)
            item = cgt_boundary_approaching(
                symbol=r["symbol"],
                lot_id=r["id"],
                days_to_eligibility=days,
                section=_SECTION,
            )
            if item is not None:
                items.append(item)
    except Exception as exc:
        elapsed_ms = int(time.monotonic() * 1000) - start_ms
        return SectionResult(
            name=_SECTION, status=SectionStatus.failed, items=(),
            elapsed_ms=elapsed_ms, error=f"CGT query: {exc}",
        )

    # Regulatory events
    try:
        reg_rows = await conn.fetch(
            """
            SELECT r.source, r.title, r.published_at, r.relevance_tags
            FROM regulatory_events r
            WHERE r.published_at >= $1::date - INTERVAL '2 days'
              AND r.ingested_at >= $1::date - INTERVAL '24 hours'
            ORDER BY r.published_at DESC
            """,
            as_of,
        )
        holdings_rows = await conn.fetch("SELECT symbol FROM current_holdings")
        holdings = {r["symbol"] for r in holdings_rows}

        for r in reg_rows:
            tags = r["relevance_tags"] or {}
            if isinstance(tags, str):
                import json
                tags = json.loads(tags)
            symbols = tags.get("symbols", []) if isinstance(tags, dict) else []
            for sym in (symbols or []):
                if sym in holdings:
                    items.append(SeverityItem(
                        level=SeverityLevel.green,
                        message=f"{sym}: {r['source']} — {r['title'][:80]}",
                        section=_SECTION,
                    ))
                    break
    except Exception as exc:
        elapsed_ms = int(time.monotonic() * 1000) - start_ms
        return SectionResult(
            name=_SECTION, status=SectionStatus.degraded, items=tuple(items),
            elapsed_ms=elapsed_ms, error=f"Regulatory query: {exc}",
        )

    elapsed_ms = int(time.monotonic() * 1000) - start_ms
    return SectionResult(
        name=_SECTION,
        status=SectionStatus.ok,
        items=tuple(items),
        elapsed_ms=elapsed_ms,
    )
