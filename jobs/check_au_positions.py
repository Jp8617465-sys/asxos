#!/usr/bin/env python
"""
ASX post-close position alerts — runs after the daily sync pipeline.

Runs Mon-Fri 21:05 UTC (after sync_prices 20:30, snapshot_portfolio 20:40,
generate_signals 20:50). Prices for the current ASX session are available
by the time this runs.

Alert triggers (per active AU thesis):
  - close < stop_price            → [STOP BREACH] <SYM> closed below stop
  - close < stop_price * 1.05     → [WATCH] <SYM> within 5% of stop
  - close >= target_price         → [TARGET HIT] <SYM> closed at/above target
  - close >= target_price * 0.95  → [TARGET NEAR] <SYM> within 5% of target
  - abs(daily_move_pct) > 3%      → [VOL ALERT] <SYM> moved >3% today
  - next_earnings_date within 5d  → [EARNINGS] <SYM> reports in Nd

No alert = no email (quiet by default).
"""
from __future__ import annotations

import asyncio
import os
from datetime import date
from decimal import Decimal

from asxos import clock
from asxos.db import acquire, close_pool, init_pool
from asxos.jobs._helpers import require_personal_use_job

# The one Resend alert path (asxos/jobs/utils/alert_email.py): never raises,
# escapes the body, and RETURNS a redacted failure note for JobMonitor.note.
from asxos.jobs.utils.alert_email import send_alert as _send_alert
from asxos.jobs.utils.job_monitor import JobMonitor

JOB_NAME = "check_au_positions"


async def _fetch_au_theses(conn) -> list[dict]:  # type: ignore[no-untyped-def, type-arg]
    """Return active theses for AU symbols with stop + target + earnings data."""
    rows = await conn.fetch(
        """
        SELECT thesis_id, symbol, stop_price, target_price, next_earnings_date
        FROM   theses
        WHERE  status = 'active'
          AND  symbol LIKE '%.AU'
        ORDER  BY symbol
        """
    )
    return [dict(r) for r in rows]


async def _fetch_last_two_closes(
    conn, symbol: str, as_of: date
) -> tuple[Decimal | None, Decimal | None]:  # type: ignore[no-untyped-def]
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
    target_price: Decimal | None,
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

    if target_price is not None and target_price > 0:
        if close >= target_price:
            alerts.append((
                f"[TARGET HIT] {symbol}",
                f"{symbol}: TARGET REACHED — close ${close} >= target ${target_price} — review thesis",
            ))
        elif close >= target_price * Decimal("0.95"):
            pct_gap = ((target_price - close) / target_price * 100).quantize(Decimal("0.1"))
            alerts.append((
                f"[TARGET NEAR] {symbol}",
                f"{symbol}: within 5% of target — close ${close} vs target ${target_price} ({pct_gap}% remaining)",
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


async def _run(as_of: date) -> None:
    # Personal-use firewall (Part 0 Q1 / CLAUDE.md #10). In-code backstop so a
    # missing flag fails loud rather than relying on the workflow's env: block alone.
    require_personal_use_job()
    healthcheck_url = os.environ.get("HEALTHCHECK_URL_CHECK_AU_POSITIONS", "")
    await init_pool()
    try:
        async with JobMonitor(JOB_NAME, as_of, healthcheck_url) as monitor:
            async with acquire() as conn:
                theses = await _fetch_au_theses(conn)

            all_alerts: list[tuple[str, str]] = []
            for t in theses:
                symbol = t["symbol"]
                stop_price = t["stop_price"]
                target_price = t["target_price"]
                next_ed_raw = t["next_earnings_date"]
                next_ed = next_ed_raw.date() if hasattr(next_ed_raw, "date") else next_ed_raw

                async with acquire() as conn:
                    close, prev_close = await _fetch_last_two_closes(conn, symbol, as_of)

                if close is None:
                    continue

                stop_d = Decimal(str(stop_price)) if stop_price is not None else None
                target_d = Decimal(str(target_price)) if target_price is not None else None
                alerts = _build_alerts(symbol, close, prev_close, stop_d, target_d, next_ed, as_of)
                all_alerts.extend(alerts)

            # Collect every send failure, not just the last: with several
            # alerts a single overwritten note would understate how much of the
            # batch never arrived.
            send_failures = [
                note
                for subject, body in all_alerts
                if (note := _send_alert(f"asxos {subject} — {as_of}", body)) is not None
            ]
            if send_failures:
                monitor.note = (
                    f"{len(send_failures)}/{len(all_alerts)} alerts undelivered: "
                    + "; ".join(sorted(set(send_failures)))
                )

            monitor.rows_written = len(all_alerts)
    finally:
        await close_pool()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="ASX position post-close alert")
    parser.add_argument("--as-of", metavar="YYYY-MM-DD", help="Date override (default: today)")
    args = parser.parse_args()

    # Default to today — prices for the current ASX session are loaded by sync_prices
    # at 20:30 UTC, which runs 35 min before this job at 21:05 UTC.
    as_of = date.fromisoformat(args.as_of) if args.as_of else clock.today()
    asyncio.run(_run(as_of))
