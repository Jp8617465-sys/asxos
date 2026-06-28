"""Corporate-actions ingestion — research store `rs_corporate_actions`.

Dividends (`/div`) + splits (`/splits`) for every security in `rs_security_master`
(survivorship-free). SEPARATE from production tables — this module never touches
`universe` or `prices`.

Field semantics verified by the read-only probes (docs/research/probes/
2026-06-24-eodhd-gate-closure.md and the 2026-06-24 corporate-actions probe):

  * `/div` object: `date` (ex-date), `value` (split-adjusted), `unadjustedValue`
    (as-paid cash/share — the PIT-correct figure -> `dividend_amount`), `paymentDate`,
    `recordDate`, `period`, `currency`, and (AU only) `franking` as a "<float>%"
    string. US names carry no `franking` key. No-dividend names return [].
  * `franking` parses to NUMERIC: "100%"->100, "0%"->0, "25.03%"->25.03. **NULL means
    undeclared/unknown — NOT 0** (0% = explicitly unfranked; the tax distinction is
    material). Out-of-range values parse to NULL.
  * `/splits` object: `date` (ex-date), `split` = "new/old" string
    ("4.000000/1.000000" = 4:1) -> `split_ratio` = new/old.

Decimal throughout (NUMERIC columns; never float for money).
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

import asyncpg

from asxos.ingestion.eodhd import EODHDClient

log = logging.getLogger(__name__)

# (symbol, ex_date, action_type, split_ratio, dividend_amount, franking_pct,
#  pay_date, record_date) — `source` is the literal below. franking_pct is COALESCEd
# so a later run returning NULL never wipes a known franking value.
_UPSERT = """
INSERT INTO rs_corporate_actions
    (symbol, ex_date, action_type, split_ratio, dividend_amount, franking_pct,
     pay_date, record_date, source)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'eodhd')
ON CONFLICT (symbol, ex_date, action_type) DO UPDATE SET
    split_ratio     = EXCLUDED.split_ratio,
    dividend_amount = EXCLUDED.dividend_amount,
    franking_pct    = COALESCE(EXCLUDED.franking_pct, rs_corporate_actions.franking_pct),
    pay_date        = EXCLUDED.pay_date,
    record_date     = EXCLUDED.record_date,
    source          = 'eodhd'
"""

_HUNDRED = Decimal(100)


def parse_franking(raw: Any) -> Decimal | None:
    """AU franking "<float>%" -> Decimal(0..100); NULL when undeclared/unknown.

    NULL is NOT 0 — 0% is explicitly unfranked, NULL is "no franking info". Values
    outside [0, 100] (data error) parse to NULL.
    """
    if raw is None:
        return None
    s = str(raw).strip().rstrip("%").strip()
    if not s:
        return None
    try:
        v = Decimal(s)
    except InvalidOperation:
        return None
    return v if Decimal(0) <= v <= _HUNDRED else None


def parse_split_ratio(raw: Any) -> Decimal | None:
    """EODHD "new/old" split string -> Decimal(new/old). NULL on malformed/zero-div."""
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    try:
        if "/" in s:
            new, old = s.split("/", 1)
            n, o = Decimal(new.strip()), Decimal(old.strip())
            return (n / o) if o != 0 else None
        return Decimal(s)
    except (InvalidOperation, ValueError):
        return None


def _dec(x: Any) -> Decimal | None:
    if x is None:
        return None
    try:
        return Decimal(str(x))
    except InvalidOperation:
        return None


def _d(s: Any) -> date | None:
    try:
        return date.fromisoformat(str(s)[:10]) if s else None
    except (TypeError, ValueError):
        return None


# Row tuple order matches _UPSERT params $1..$8.
_Row = tuple[str, date, str, Decimal | None, Decimal | None, Decimal | None, date | None, date | None]


def to_dividend_rows(raw: Any, symbol: str) -> list[_Row]:
    """EODHD /div payload -> rs_corporate_actions dividend rows. Rows without an
    ex-date (the PK component) are skipped. dividend_amount = unadjustedValue
    (as-paid), falling back to value."""
    rows: list[_Row] = []
    if not isinstance(raw, list):
        return rows
    for r in raw:
        if not isinstance(r, dict):
            continue
        ex = _d(r.get("date"))
        if ex is None:
            continue
        amount = r.get("unadjustedValue")
        if amount is None:
            amount = r.get("value")
        rows.append((
            symbol, ex, "dividend",
            None,                                   # split_ratio
            _dec(amount),                           # dividend_amount
            parse_franking(r.get("franking")),
            _d(r.get("paymentDate")),
            _d(r.get("recordDate")),
        ))
    return rows


def to_split_rows(raw: Any, symbol: str) -> list[_Row]:
    """EODHD /splits payload -> rs_corporate_actions split rows."""
    rows: list[_Row] = []
    if not isinstance(raw, list):
        return rows
    for r in raw:
        if not isinstance(r, dict):
            continue
        ex = _d(r.get("date"))
        if ex is None:
            continue
        rows.append((
            symbol, ex, "split",
            parse_split_ratio(r.get("split")),
            None, None, None, None,                 # dividend_amount, franking, pay, record
        ))
    return rows


async def refresh_corporate_actions(
    client: EODHDClient,
    conn: asyncpg.Connection,
    symbols: list[str],
    *,
    concurrency: int = 8,
) -> dict[str, int]:
    """Ingest dividends + splits for `symbols` into rs_corporate_actions.

    Fetches concurrently (bounded by `concurrency`; the client's own semaphore is the
    hard cap) and writes serially through the single connection (asyncpg connections
    are not concurrency-safe). Idempotent UPSERT on (symbol, ex_date, action_type) —
    safe to re-run and resumable after a partial failure. A symbol whose BOTH endpoints
    error is counted as failed and skipped, never aborting the run.
    """
    sem = asyncio.Semaphore(concurrency)

    async def fetch(sym: str) -> tuple[str, Any, Any]:
        async with sem:
            try:
                div = await client.dividends(sym)
            except Exception:
                log.warning("dividends fetch failed for %s", sym, exc_info=True)
                div = None
            try:
                spl = await client.splits(sym)
            except Exception:
                log.warning("splits fetch failed for %s", sym, exc_info=True)
                spl = None
        return sym, div, spl

    counts = {
        "symbols": len(symbols),
        "dividends": 0,
        "splits": 0,
        "symbols_with_actions": 0,
        "failed": 0,
    }

    tasks = [asyncio.ensure_future(fetch(s)) for s in symbols]
    for coro in asyncio.as_completed(tasks):
        sym, div, spl = await coro
        if div is None and spl is None:
            counts["failed"] += 1
            continue
        rows = to_dividend_rows(div or [], sym) + to_split_rows(spl or [], sym)
        if rows:
            counts["symbols_with_actions"] += 1
        for row in rows:
            await conn.execute(_UPSERT, *row)
            counts["dividends" if row[2] == "dividend" else "splits"] += 1

    return counts
