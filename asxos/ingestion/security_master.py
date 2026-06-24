"""Security-master ingestion — research store `rs_security_master`.

Survivorship-free: one row per security EVER listed on ASX (active + delisted).
This is the research mirror, SEPARATE from the production `universe` table
(current-only, the tradable set). **This module must never read or write
`universe`** — they diverge intentionally (universe = "what we trade",
rs_security_master = "everything that ever existed, for backtests").

Source availability + field semantics were settled by the read-only gate-closure
probe on 2026-06-24 (docs/research/probes/2026-06-24-eodhd-gate-closure.md):

  * `exchange-symbol-list/AU` -> active (2,382 rows); `?delisted=1` -> delisted (1,986)
  * the delisted payload carries NO date field -> `delisted_date` stays NULL in v1
  * `Type` set = {Common Stock, ETF, Preferred Stock, FUND, Notes, BOND} -> store ALL
    types (unlike `universe`, which filters to Common Stock)
  * 0 duplicate `Code`s across the two lists -> `_to_symbol` is collision-free here

The symbol-list payload does not expose prior tickers, so a renamed security simply
updates `name` in place (we cannot record an old->new ticker map EODHD does not give).
`listed_date` and `gics_*` are deliberately NOT written here so a later enrichment
pass (from `/fundamentals`) is never clobbered.
"""
from __future__ import annotations

import asyncpg

from asxos.ingestion.eodhd import EODHDClient
from asxos.ingestion.universe import _to_symbol  # reuse the proven .AU suffix mapper

# Idempotent UPSERT. `delisted_date` is never set here (no source field); `is_active`
# always takes the freshest list membership; `isin` is COALESCEd so a sparser later
# payload never nulls a value we already learned. `listed_date`/`gics_*` are omitted
# from both the INSERT and the DO UPDATE so the enrichment pass owns them.
_UPSERT = """
INSERT INTO rs_security_master
    (symbol, name, exchange, currency, security_type, isin, delisted_date,
     is_active, source, updated_at)
VALUES ($1, $2, 'AU', $3, $4, $5, NULL, $6, 'eodhd', now())
ON CONFLICT (symbol) DO UPDATE SET
    name          = EXCLUDED.name,
    currency      = EXCLUDED.currency,
    security_type = EXCLUDED.security_type,
    isin          = COALESCE(EXCLUDED.isin, rs_security_master.isin),
    is_active     = EXCLUDED.is_active,
    updated_at    = now()
"""

_SELECT_EXISTING = "SELECT symbol, is_active FROM rs_security_master"


async def refresh_security_master(
    client: EODHDClient, conn: asyncpg.Connection
) -> dict[str, int]:
    """Sync `rs_security_master` from EODHD active + delisted symbol lists.

    Idempotent UPSERT keyed on `symbol`. When a code appears in both lists,
    **active membership wins** (the security is currently listed) — and any prior
    `delisted_date` is preserved, since this job never writes that column.

    Returns a count breakdown: active / delisted (distinct incoming), inserted /
    updated / relisted, and skipped_no_code (rows with a missing/blank `Code`).
    """
    active = await client.exchange_symbols("AU")
    delisted = await client.exchange_symbols_delisted("AU")

    # Build the incoming map keyed by symbol. Process delisted FIRST so a code in
    # both lists is overwritten by its active entry (is_active = True wins).
    incoming: dict[str, dict[str, object]] = {}
    skipped_no_code = 0
    for is_active, rows in ((False, delisted), (True, active)):
        for r in rows:
            code = (r.get("Code") or "").strip()
            if not code:
                skipped_no_code += 1
                continue
            incoming[_to_symbol(code)] = {
                "name": r.get("Name") or "",
                "currency": r.get("Currency") or "AUD",
                "security_type": r.get("Type") or None,
                "isin": r.get("Isin") or None,
                "is_active": is_active,
            }

    existing = {
        r["symbol"]: r["is_active"]
        for r in await conn.fetch(_SELECT_EXISTING)
    }

    counts = {
        "active": sum(1 for v in incoming.values() if v["is_active"]),
        "delisted": sum(1 for v in incoming.values() if not v["is_active"]),
        "inserted": 0,
        "updated": 0,
        "relisted": 0,
        "skipped_no_code": skipped_no_code,
    }

    for sym, v in incoming.items():
        await conn.execute(
            _UPSERT,
            sym,
            v["name"],
            v["currency"],
            v["security_type"],
            v["isin"],
            v["is_active"],
        )
        if sym not in existing:
            counts["inserted"] += 1
        else:
            counts["updated"] += 1
            if v["is_active"] and existing[sym] is False:
                counts["relisted"] += 1

    return counts
