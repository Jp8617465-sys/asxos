#!/usr/bin/env python
"""
Daily price validation — runs at 20:33 UTC (Sun-Thu) after sync_prices (20:30)
and before snapshot_portfolio (20:40).

Three checks:
  1. Large daily moves (>25%) — potential splits or data errors.
  2. Active symbols missing a price row for as_of — data gaps.
  3. Any close <= 0 in the last 7 days — corrupt rows.

Alert behaviour:
  - 1–10 anomalies: send email, still record success + ping Healthchecks.io.
  - >10 anomalies: send email AND raise RuntimeError (Healthchecks.io misses ping).
  - 0 anomalies: silent success.
"""
from __future__ import annotations

import asyncio
import os
from datetime import date

from asxos.config import settings
from asxos.db import acquire, close_pool, init_pool
from asxos.jobs.utils.job_monitor import JobMonitor

JOB_NAME = "validate_price_data"
_LARGE_MOVE_THRESHOLD = 0.25
_HARD_FAIL_THRESHOLD = 10


def _send_alert(subject: str, body: str) -> None:
    """Best-effort Resend alert. Never raises."""
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


async def _query_anomalies(conn, as_of: date) -> list[str]:  # type: ignore[type-arg]
    issues: list[str] = []

    # 1. Large daily moves on as_of (potential split or data error)
    large_moves = await conn.fetch(
        """
        SELECT p.symbol,
               p.close                                   AS today_close,
               prev.close                                AS prev_close,
               ABS(p.close / NULLIF(prev.close, 0) - 1) AS move_pct
        FROM prices p
        JOIN universe u ON u.symbol = p.symbol
        JOIN LATERAL (
            SELECT close
            FROM   prices p2
            WHERE  p2.symbol = p.symbol
              AND  p2.dt < $1
            ORDER  BY p2.dt DESC
            LIMIT  1
        ) prev ON TRUE
        WHERE p.dt = $1
          AND u.is_active = TRUE
          AND ABS(p.close / NULLIF(prev.close, 0) - 1) > $2
        ORDER BY move_pct DESC
        """,
        as_of,
        _LARGE_MOVE_THRESHOLD,
    )
    for r in large_moves:
        pct = float(r["move_pct"]) * 100
        issues.append(
            f"LARGE_MOVE: {r['symbol']} moved {pct:.1f}% "
            f"({r['prev_close']} → {r['today_close']})"
        )

    # 2. Active symbols missing a price for as_of (aggregated — one issue entry)
    missing = await conn.fetch(
        """
        SELECT u.symbol
        FROM   universe u
        LEFT JOIN prices p ON p.symbol = u.symbol AND p.dt = $1
        WHERE  u.is_active = TRUE
          AND  p.symbol IS NULL
        ORDER  BY u.symbol
        """,
        as_of,
    )
    if missing:
        syms = [r["symbol"] for r in missing]
        issues.append(
            f"MISSING_PRICES: {len(syms)} active symbols have no price for {as_of} "
            f"— first 10: {syms[:10]}"
        )

    # 3. Any close <= 0 for active symbols in the last 7 days
    bad_closes = await conn.fetch(
        """
        SELECT p.symbol, p.dt, p.close
        FROM prices p
        JOIN universe u ON u.symbol = p.symbol
        WHERE u.is_active = TRUE
          AND p.close <= 0
          AND p.dt >= $1::date - INTERVAL '7 days'
        ORDER BY p.dt DESC, p.symbol
        LIMIT 50
        """,
        as_of,
    )
    for r in bad_closes:
        issues.append(
            f"BAD_CLOSE: {r['symbol']} has close={r['close']} on {r['dt']}"
        )

    return issues


async def _run(as_of: date) -> None:
    healthcheck_url = settings.healthcheck_url_validate_price_data
    async with JobMonitor(JOB_NAME, as_of, healthcheck_url) as monitor:
        await init_pool()
        try:
            async with acquire() as conn:
                issues = await _query_anomalies(conn, as_of)

            monitor.rows_written = len(issues)

            if not issues:
                return

            body = "\n".join(f"• {i}" for i in issues)
            if len(issues) <= _HARD_FAIL_THRESHOLD:
                _send_alert(
                    f"[asxos] price anomalies detected — {as_of}",
                    body,
                )
                return
            else:
                _send_alert(
                    f"[asxos] PRICE VALIDATION HARD FAIL — {len(issues)} anomalies — {as_of}",
                    body,
                )
                raise RuntimeError(
                    f"price validation failed: {len(issues)} anomalies on {as_of}"
                )
        finally:
            await close_pool()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Validate price data quality")
    parser.add_argument("--as-of", metavar="YYYY-MM-DD", help="Date override (default: today)")
    args = parser.parse_args()
    as_of = date.fromisoformat(args.as_of) if args.as_of else date.today()
    asyncio.run(_run(as_of))
