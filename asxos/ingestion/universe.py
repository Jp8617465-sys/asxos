"""Universe ingestion logic — separated from the job script."""
from __future__ import annotations

from datetime import UTC, datetime

import asyncpg

from asxos.ingestion.eodhd import EODHDClient


def _to_symbol(code: str, *, exchange: str = "AU") -> str:
    """Append exchange suffix when the raw EODHD code has no dot.

    EODHD bulk endpoints return bare codes (e.g. "BHP", "AAPL") without
    an exchange suffix. For AU calls the default ".AU" is always correct;
    US calls must pass exchange="US" so "AAPL" → "AAPL.US" not "AAPL.AU".
    """
    return code if "." in code else f"{code}.{exchange}"


async def refresh_universe(client: EODHDClient, conn: asyncpg.Connection) -> dict[str, int]:
    """
    Sync universe from EODHD exchange symbol list.
    Returns counts: added, reactivated, delisted, unchanged.
    """
    raw = await client.exchange_symbols("AU")
    incoming = {
        _to_symbol(r["Code"]): r
        for r in raw
        if r.get("Type") == "Common Stock"
    }

    existing = {
        r["symbol"]: r["is_active"]
        for r in await conn.fetch("SELECT symbol, is_active FROM universe")
    }

    counts = {"added": 0, "reactivated": 0, "delisted": 0, "unchanged": 0}

    for sym, r in incoming.items():
        if sym not in existing:
            await conn.execute(
                # security_kind is NOT NULL with no default (migration 0037) — every writer
                # must classify explicitly. This branch only ingests `Type == "Common Stock"`
                # (see the filter above), so 'au_equity' is correct. When this grows to ingest
                # ETF/FUND types (multi-instrument Phase 2), replace the literal with a
                # Type->kind map.
                """
                INSERT INTO universe (symbol, name, sector, currency, security_kind)
                VALUES ($1, $2, $3, 'AUD', 'au_equity')
                """,
                sym,
                r.get("Name") or "",
                r.get("Sector") or "",
            )
            counts["added"] += 1
        elif not existing[sym]:
            await conn.execute(
                "UPDATE universe SET is_active = TRUE, updated_at = NOW() WHERE symbol = $1",
                sym,
            )
            counts["reactivated"] += 1
        else:
            counts["unchanged"] += 1

    now = datetime.now(UTC)
    for sym, is_active in existing.items():
        if sym not in incoming and is_active:
            await conn.execute(
                "UPDATE universe SET is_active = FALSE, updated_at = $2 WHERE symbol = $1",
                sym,
                now,
            )
            counts["delisted"] += 1

    return counts
