"""Segment-key resolution — research store `segment_map` (D3/S3).

Segment-valuation architecture doc (docs/proposals/segment-valuation-portfolio-
architecture-2026-08-18.md), defect D3: `universe.sector` (Morningstar) and
`rs_security_master.gics_sector` coexist as two sector vocabularies, and
`gics_sector` itself is not purely GICS -- it mixes canonical GICS names with
Morningstar-style leakage (verified live 2026-08-19, see _ALIASES below). A
naive `coalesce(gics_sector, universe.sector)` therefore splits one real
segment into duplicate buckets ("Financials" and "Financial Services" both
appearing in the same aggregate).

`resolve_segment_key()` is the pure normalization function: GICS-preferred,
Morningstar variants mapped to their GICS equivalent, unresolvable values
(EODHD's "Other" bucket, blank, NULL) left NULL with source='unresolved'
rather than faked into a plausible-looking segment. `refresh_segment_map()`
is the DB-to-DB orchestrator that materialises this into the `segment_map`
table for every symbol in `rs_security_master`.

Pure DB-to-DB (no EODHD): reads rs_security_master + universe, writes only
segment_map. SEPARATE from production `universe.sector`, which stays
untouched -- this table is additive, not a migration of the source columns.
"""
from __future__ import annotations

from datetime import date
from typing import Literal, TypedDict

import asyncpg

# The 11 canonical GICS sector names this repo's data actually observes.
# Any raw value not in this set and not a recognised alias below is
# unresolved, not guessed.
_CANONICAL_GICS = frozenset(
    {
        "Communication Services",
        "Consumer Discretionary",
        "Consumer Staples",
        "Energy",
        "Financials",
        "Health Care",
        "Industrials",
        "Information Technology",
        "Materials",
        "Real Estate",
        "Utilities",
    }
)

# Morningstar-style variants -> canonical GICS name. Verified live 2026-08-19
# against both universe.sector (pure Morningstar) and rs_security_master.
# gics_sector (mixed -- these same variants leak into that column too,
# alongside 752 NULL rows and a few data artefacts: "Financial" (truncated),
# "Industrial Goods" (single row, not a real GICS sector)).
_ALIASES: dict[str, str] = {
    "Basic Materials": "Materials",
    "Consumer Cyclical": "Consumer Discretionary",
    "Consumer Defensive": "Consumer Staples",
    "Financial": "Financials",
    "Financial Services": "Financials",
    "Healthcare": "Health Care",
    "Industrial Goods": "Industrials",
    "Technology": "Information Technology",
}

# Values observed live that are not a real sector and must not be mapped to
# one: EODHD's own "doesn't fit a sector" bucket, plus blank/whitespace.
_UNRESOLVABLE = frozenset({"Other", "", None})

Source = Literal["gics", "morningstar_alias", "unresolved"]


def normalize_segment_name(raw: str | None) -> str | None:
    """Map a raw sector string (from either source column) to its canonical GICS name,
    or None if it is not a recognised value.

    Does not know which source column `raw` came from -- that's resolve_segment_key's
    job, since the same alias table applies to both (gics_sector leaks Morningstar
    values too)."""
    if raw is None:
        return None
    raw = raw.strip()
    if raw in _UNRESOLVABLE:
        return None
    if raw in _CANONICAL_GICS:
        return raw
    return _ALIASES.get(raw)


def resolve_segment_key(
    gics_sector: str | None, universe_sector: str | None
) -> tuple[str | None, Source]:
    """Resolve one symbol's segment key: prefer gics_sector, fall back to universe_sector,
    else unresolved.

    Both inputs pass through the same normalizer since gics_sector itself carries
    Morningstar leakage."""
    normalized_gics = normalize_segment_name(gics_sector)
    if normalized_gics is not None:
        return normalized_gics, "gics"
    normalized_universe = normalize_segment_name(universe_sector)
    if normalized_universe is not None:
        return normalized_universe, "morningstar_alias"
    return None, "unresolved"


class SegmentMapCounts(TypedDict):
    symbols: int
    resolved_gics: int
    resolved_alias: int
    unresolved: int


_SOURCE_ROWS = """
SELECT s.symbol, s.gics_sector, u.sector AS universe_sector
FROM rs_security_master s
LEFT JOIN universe u ON u.symbol = s.symbol
"""

_UPSERT = """
INSERT INTO segment_map
    (symbol, taxonomy_version, segment_key, source, effective_from, computed_at)
VALUES ($1, $2, $3, $4, $5, now())
ON CONFLICT (symbol, taxonomy_version) DO UPDATE SET
    segment_key = EXCLUDED.segment_key,
    source = EXCLUDED.source,
    effective_from = EXCLUDED.effective_from,
    computed_at = now()
"""


async def refresh_segment_map(
    conn: asyncpg.Connection,
    *,
    as_of: date,
    taxonomy_version: str = "gics_alias_v1",
) -> SegmentMapCounts:
    """Resolve and UPSERT segment_map for every symbol in rs_security_master.

    Idempotent on (symbol, taxonomy_version). Reads rs_security_master +
    universe; writes only segment_map."""
    rows = await conn.fetch(_SOURCE_ROWS)
    counts = SegmentMapCounts(symbols=0, resolved_gics=0, resolved_alias=0, unresolved=0)
    upsert_rows: list[tuple[object, ...]] = []
    for row in rows:
        segment_key, source = resolve_segment_key(row["gics_sector"], row["universe_sector"])
        upsert_rows.append((row["symbol"], taxonomy_version, segment_key, source, as_of))
        counts["symbols"] += 1
        if source == "gics":
            counts["resolved_gics"] += 1
        elif source == "morningstar_alias":
            counts["resolved_alias"] += 1
        else:
            counts["unresolved"] += 1
    if upsert_rows:
        await conn.executemany(_UPSERT, upsert_rows)
    return counts
