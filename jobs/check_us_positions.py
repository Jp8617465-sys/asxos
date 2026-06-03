#!/usr/bin/env python
"""
US position post-close alert cron — M-Position-Monitor.

Runs Mon-Fri 13:30 UTC (after NYSE close the previous evening; sync_prices
loaded the prior session's close at 20:30 UTC last night).

Reads from the prices table (not EODHD API — no double-calling).

Alert triggers (per active US thesis):
  - close < stop_price            → [STOP BREACH] <SYM> closed below stop
  - close < stop_price * 1.05     → [WATCH] <SYM> within 5% of stop
  - abs(daily_move_pct) > 3%      → [VOL ALERT] <SYM> moved >3% today
  - next_earnings_date within 5d  → [EARNINGS] <SYM> reports in Nd

No alert = no email (quiet by default).
"""
from __future__ import annotations

import asyncio
import os
from datetime import date, timedelta
from decimal import Decimal

from asxos.db import acquire, close_pool, init_pool
from asxos.jobs.utils.job_monitor import JobMonitor

JOB_NAME = "check_us_positions"


async def _fetch_us_theses(conn) -> list[dict]:  # type: ignore[no-untyped-def, type-arg]
    """Return active theses for US symbols with stop + earnings data."""
    rows = await conn.fetch(
        """
        SELECT thesis_id, symbol, stop_price, next_earnings_date
        FROM   theses
        WHERE  status = 'active'
          AND  symbol LIKE '%.US'
        ORDER  BY symbol
        """
    )
    return [dict(r) for r in rows]


async def _fetch_last_two_closes(conn, symbol: str, as_of: date) -> tuple[Decimal | None, Decimal | None]:  # type: ignore[no-untyped-def]
    """Return (today_close, prev_close) for the symbol on and before as_of."""
    rows = await conn.fetch(
        """
        SELECT dt, close
        FROM   prices
        WHERE  symbol = $1
          AND  dt    <= $2
        ORDER  BY dt DESC
        LIMIT  2
        """,
        symbol,
        as_of,
    )
    if not rows:
        return None, None
    today_close = Decimal(str(rows[0]["close"]))
    prev_close = Decimal(str(rows[1]["close"])) if len(rows) >= 2 else None
    return today_close, prev_close


def _build_alerts(
    symbol: str,
    close: Decimal,
    prev_close: Decimal | None,
    stop_price: Decimal | None,
    next_earnings_date: date | None,
    as_of: date,
) -> list[tuple[str, str]]:
    """Return list of (subject_tag, message_line) for each triggered alert."""
    alerts: list[tuple[str, str]] = []

    if stop_price is not None and stop_price > 0:
        if close < stop_price:
            alerts.append((
                f"[STOP BREACH] {symbol}",
                f"{symbol}: CLOSED BELOW STOP — close ${close} < stop ${stop_price}",
            ))
        elif close < stop_price * Decimal("1.05"):
            pct_buffer = ((close - stop_price) / close * 100).quantize(Decimal("0.1"))
            alerts.append((
                f"[WATCH] {symbol}",
                f"{symbol}: within 5% of stop — close ${close} vs stop ${stop_price} ({pct_buffer}% buffer)",
            ))

    if prev_close is not None and prev_close > 0:
        daily_move = ((close - prev_close) / prev_close * 100).quantize(Decimal("0.1"))
        if abs(daily_move) > 3:
            direction = "▲" if daily_move > 0 else "▼"
            alerts.append((
                f"[VOL ALERT] {symbol}",
                f"{symbol}: moved {direction}{abs(daily_move):.1f}% today (${prev_close} → ${close})",
            ))

    if next_earnings_date is not None:
        days_to_earnings = (next_earnings_date - as_of).days
        if 0 <= days_to_earnings <= 5:
            alerts.append((
                f"[EARNINGS] {symbol}",
                f"{symbol}: reports in {days_to_earnings}d ({next_earnings_date})",
            ))

    return alerts


def _send_alert(subject: str, body: str) -> None:
    """Send email via Resend. Never raises."""
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
    healthcheck_url = os.environ.get("HEALTHCHECK_URL_CHECK_US_POSITIONS", "")
    async with JobMonitor(JOB_NAME, as_of, healthcheck_url) as monitor:
        await init_pool()
        try:
            async with acquire() as conn:
                theses = await _fetch_us_theses(conn)

            all_alerts: list[tuple[str, str]] = []
            for t in theses:
                symbol = t["symbol"]
                stop_price = t["stop_price"]
                next_ed_raw = t["next_earnings_date"]
                next_ed = next_ed_raw.date() if hasattr(next_ed_raw, "date") else next_ed_raw

                async with acquire() as conn:
                    close, prev_close = await _fetch_last_two_closes(conn, symbol, as_of)

                if close is None:
                    continue

                stop_d = Decimal(str(stop_price)) if stop_price is not None else None
                alerts = _build_alerts(symbol, close, prev_close, stop_d, next_ed, as_of)
                all_alerts.extend(alerts)

            for subject, body in all_alerts:
                _send_alert(f"asxos {subject} — {as_of}", body)

            monitor.rows_written = len(all_alerts)
        finally:
            await close_pool()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="US position post-close alert")
    parser.add_argument("--as-of", metavar="YYYY-MM-DD", help="Date override (default: yesterday)")
    args = parser.parse_args()

    as_of = date.fromisoformat(args.as_of) if args.as_of else date.today() - timedelta(days=1)
    asyncio.run(_run(as_of))
