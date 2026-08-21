#!/usr/bin/env python
"""
Thesis invalidation condition checker — daily.

For each active thesis, evaluates price-based invalidation conditions against
the most recent close price. On a match:
  1. Sets status='triggered' in the JSONB array (direct UPDATE — no revision
     event since this is automated bookkeeping, not a user discipline event)
  2. Sends an interrupt email so the user can review and decide to exit

Patterns recognized (case-insensitive, first match wins per condition):
  "Price falls below $150"   → trigger if close < 150
  "Close under 45.50"        → trigger if close < 45.50
  "Price above $300"         → trigger if close > 300
  "Stock rises above 8.20"   → trigger if close > 8.20

Conditions that don't match a price pattern are skipped (manual check required).
Already-triggered or resolved conditions are not re-evaluated.

Entries may be {"condition", "status", ...} dicts (the service-layer write
contract) or bare strings (legacy manually seeded rows). Strings are read as
active conditions, and the whole array is rewritten in dict shape whenever a
trigger fires — see _normalize_conditions().
"""
from __future__ import annotations

import asyncio
import json
import os
import re
from collections.abc import Iterable
from datetime import date
from decimal import Decimal
from typing import Any

from asxos.db import acquire, close_pool, init_pool
from asxos.jobs._helpers import require_personal_use_job
from asxos.jobs.utils.job_monitor import JobMonitor

JOB_NAME = "check_thesis_invalidations"

_PRICE_BELOW_RE = re.compile(
    r'(?i)\b(?:price|close|stock)\b.{0,40}(?:below|under|falls?\s+below|<|<=)\s*\$?\s*(\d+(?:\.\d+)?)'
)
_PRICE_ABOVE_RE = re.compile(
    r'(?i)\b(?:price|close|stock)\b.{0,40}(?:above|over|rises?\s+above|>|>=)\s*\$?\s*(\d+(?:\.\d+)?)'
)


def _normalize_conditions(raw: str | Iterable[Any]) -> list[dict[str, Any]]:
    """Return invalidation_conditions as a list of {"condition", "status", ...} dicts.

    The service layer writes dicts, but manually seeded theses store bare
    strings (e.g. thesis #2 HUBS.NYSE — found by this job's first live run,
    2026-07-03). A bare string means an active, never-evaluated condition, so
    coerce rather than crash; the dict shape is written back on any trigger,
    normalizing the row permanently.
    """
    entries = json.loads(raw) if isinstance(raw, str) else raw
    return [
        e if isinstance(e, dict) else {"condition": str(e), "status": "active"}
        for e in entries
    ]


def _parse_price_condition(condition: str) -> tuple[str, Decimal] | None:
    """Return ('below', threshold) or ('above', threshold), or None if not parseable."""
    m = _PRICE_BELOW_RE.search(condition)
    if m:
        return ("below", Decimal(m.group(1)))
    m = _PRICE_ABOVE_RE.search(condition)
    if m:
        return ("above", Decimal(m.group(1)))
    return None


async def _fetch_active_theses_with_conditions(conn) -> list[dict]:  # type: ignore[no-untyped-def, type-arg]
    rows = await conn.fetch(
        """
        SELECT thesis_id, symbol, invalidation_conditions
        FROM   theses
        WHERE  status = 'active'
          AND  invalidation_conditions IS NOT NULL
          AND  jsonb_array_length(invalidation_conditions) > 0
        ORDER  BY symbol
        """
    )
    return [dict(r) for r in rows]


async def _fetch_latest_close(conn, symbol: str, as_of: date) -> Decimal | None:  # type: ignore[no-untyped-def]
    row = await conn.fetchrow(
        """
        SELECT close FROM prices
        WHERE  symbol = $1 AND dt <= $2
        ORDER  BY dt DESC LIMIT 1
        """,
        symbol,
        as_of,
    )
    return Decimal(str(row["close"])) if row else None


def _send_alert(subject: str, body: str) -> None:
    try:
        import resend

        api_key = os.environ.get("RESEND_API_KEY", "")
        to = os.environ.get("BRIEF_TO_EMAIL", "")
        sender = os.environ.get("BRIEF_FROM_EMAIL", "")
        if not (api_key and to and sender):
            return

        resend.api_key = api_key
        resend.Emails.send({
            "from": sender,
            "to": to,
            "subject": subject,
            "html": f"<pre>{body}</pre>",
        })
    except Exception:
        pass


async def _run(as_of: date) -> None:
    # Personal-use firewall (Part 0 Q1 / CLAUDE.md #10). In-code backstop so a
    # missing flag fails loud rather than relying on the workflow's env: block alone.
    require_personal_use_job()
    healthcheck_url = os.environ.get("HEALTHCHECK_URL_CHECK_THESIS_INVALIDATIONS", "")
    await init_pool()
    try:
        async with JobMonitor(JOB_NAME, as_of, healthcheck_url) as monitor:
            async with acquire() as conn:
                theses = await _fetch_active_theses_with_conditions(conn)

            triggered_count = 0
            for t in theses:
                symbol = t["symbol"]
                thesis_id = t["thesis_id"]
                conditions = _normalize_conditions(t["invalidation_conditions"])

                async with acquire() as conn:
                    close = await _fetch_latest_close(conn, symbol, as_of)

                if close is None:
                    continue

                newly_triggered: list[str] = []
                updated = False

                for i, cond in enumerate(conditions):
                    if cond.get("status") != "active":
                        continue
                    parsed = _parse_price_condition(cond["condition"])
                    if parsed is None:
                        continue
                    direction, threshold = parsed
                    hit = (direction == "below" and close < threshold) or (
                        direction == "above" and close > threshold
                    )
                    if hit:
                        conditions[i] = {
                            **cond,
                            "status": "triggered",
                            "note": f"auto: close={close} {direction} {threshold} on {as_of}",
                        }
                        newly_triggered.append(
                            f"{cond['condition']}  (close={close})"
                        )
                        updated = True

                if updated:
                    async with acquire() as conn:
                        await conn.execute(
                            "UPDATE theses SET invalidation_conditions = $1::jsonb WHERE thesis_id = $2",
                            json.dumps(conditions),
                            thesis_id,
                        )
                    body = (
                        f"{symbol} invalidation condition triggered:\n\n"
                        + "\n".join(f"  • {m}" for m in newly_triggered)
                        + "\n\nReview thesis and consider exit.\n"
                        + f"Run: asx thesis exit {symbol}"
                    )
                    _send_alert(f"asxos [INVALIDATION] {symbol} — {as_of}", body)
                    triggered_count += 1

            monitor.rows_written = triggered_count
    finally:
        await close_pool()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Check thesis invalidation conditions")
    parser.add_argument("--as-of", metavar="YYYY-MM-DD", help="Date override (default: today)")
    args = parser.parse_args()

    as_of = date.fromisoformat(args.as_of) if args.as_of else date.today()
    asyncio.run(_run(as_of))
