"""
Section 5: Underlying drivers — M-Brief-V2-Sections.

For each active/watching thesis: load commodity/currency/rate dependencies,
score 5-day movement, report confirming/mixed/diverging. Appends cross-layer
observations when regime context is available.

SeverityItem levels:
  - yellow: any diverging underlying on a bullish thesis
  - green:  confirming or mixed
"""
from __future__ import annotations

import time
from datetime import date

from asxos.db import acquire
from asxos.domain.brief.cross_layer import cross_layer_observations
from asxos.domain.brief.types import SectionResult, SectionStatus, SeverityItem, SeverityLevel
from asxos.domain.underlyings.attribution import score_thesis_underlying
from asxos.domain.underlyings.service import bulk_list_thesis_underlyings, get_5d_moves

_SECTION = "underlying_drivers"


async def collect_underlying_drivers(
    as_of: date, regime_label: str | None = None
) -> SectionResult:
    """Score underlying drivers for all active/watching theses.

    regime_label is passed from the market_context collector to avoid a
    second DB round-trip. If None, skips cross-layer regime observations.
    """
    start_ms = int(time.monotonic() * 1000)
    items: list[SeverityItem] = []

    async with acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT thesis_id, symbol, status
            FROM theses
            WHERE status IN ('active', 'watching')
            ORDER BY opened_at DESC
            """
        )

        if not rows:
            elapsed_ms = int(time.monotonic() * 1000) - start_ms
            return SectionResult(
                name=_SECTION, status=SectionStatus.no_data,
                items=(), elapsed_ms=elapsed_ms,
                error="no active/watching theses",
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

        thesis_scores = []
        for row in rows:
            thesis_id = row["thesis_id"]
            symbol = row["symbol"]

            thesis_underlyings = tu_by_thesis.get(thesis_id, [])
            if not thesis_underlyings:
                continue

            moves = {uid: all_moves.get(uid) for uid in [tu.underlying_id for tu in thesis_underlyings]}
            score = score_thesis_underlying(thesis_underlyings, moves)

            thesis_scores.append((symbol, row["status"], score))

            level = SeverityLevel.yellow if score.label == "diverging" else SeverityLevel.green
            driver_parts = []
            for tu in thesis_underlyings:
                move = moves.get(tu.underlying_id)
                if move is not None:
                    driver_parts.append(f"{tu.underlying_id}:{move:+.1f}%")

            drivers_str = ", ".join(driver_parts) if driver_parts else "no price data"
            msg = (
                f"{symbol} | {score.label} (weighted {score.weighted_movement:+.2f}%)"
                f"\n  Drivers: {drivers_str}"
            )
            items.append(SeverityItem(level=level, message=msg, section=_SECTION))

    # Cross-layer observations (pure, no DB)
    cross_obs = cross_layer_observations(regime_label, thesis_scores)
    for obs in cross_obs:
        items.append(SeverityItem(level=SeverityLevel.green, message=obs, section=_SECTION))

    elapsed_ms = int(time.monotonic() * 1000) - start_ms

    if not items:
        return SectionResult(
            name=_SECTION, status=SectionStatus.no_data,
            items=(), elapsed_ms=elapsed_ms,
            error="no underlyings configured for any active/watching thesis",
        )

    return SectionResult(
        name=_SECTION, status=SectionStatus.ok,
        items=tuple(items), elapsed_ms=elapsed_ms,
    )
