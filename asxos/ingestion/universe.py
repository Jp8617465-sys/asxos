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


# EODHD Type -> universe.security_kind (multi-instrument Phase 2). Only these types are
# ingested; anything else (rights, warrants, unclassified) is skipped. REITs and many LICs
# are typed "Common Stock" by EODHD and so land as au_equity — the safe default that keeps
# their existing Model A/thesis eligibility (proposal §7.3); a curated LIC/REIT reclassification
# is a later refinement. ETF/FUND/hybrid kinds are kept OUT of the ML universe by the
# `security_kind = 'au_equity'` reader filters (migration 0037), so ingesting them cannot
# pollute Model A.
_TYPE_TO_KIND: dict[str, str] = {
    "Common Stock": "au_equity",
    "ETF": "etf",
    "FUND": "lic",
    "Preferred Stock": "hybrid",
    "Notes": "hybrid",
    "BOND": "hybrid",
}


async def refresh_universe(client: EODHDClient, conn: asyncpg.Connection) -> dict[str, int]:
    """
    Sync universe from EODHD exchange symbol list.
    Returns counts: added, reactivated, delisted, unchanged.

    Ingests every `_TYPE_TO_KIND` instrument type (equities + ETFs/LICs/hybrids), tagging
    `security_kind` so funds are held/valued/taxed without entering Model A's universe. The
    delisting sweep is safe across kinds: it only flips an `is_active` symbol absent from the
    (now kind-broad) incoming set, and out-of-band rows (us_equity/index) are already
    is_active=FALSE, so `and is_active` skips them.
    """
    raw = await client.exchange_symbols("AU")
    incoming = {
        _to_symbol(r["Code"]): r
        for r in raw
        if r.get("Type") in _TYPE_TO_KIND
    }

    existing = {
        r["symbol"]: r["is_active"]
        for r in await conn.fetch("SELECT symbol, is_active FROM universe")
    }

    counts = {"added": 0, "reactivated": 0, "delisted": 0, "unchanged": 0}

    for sym, r in incoming.items():
        kind = _TYPE_TO_KIND.get(r.get("Type", ""), "au_equity")
        if sym not in existing:
            await conn.execute(
                # security_kind is NOT NULL with no default (migration 0037) — classify by the
                # EODHD Type via _TYPE_TO_KIND (funds stay out of Model A by kind, not is_active).
                """
                INSERT INTO universe (symbol, name, sector, currency, security_kind)
                VALUES ($1, $2, $3, 'AUD', $4)
                """,
                sym,
                r.get("Name") or "",
                r.get("Sector") or "",
                kind,
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
