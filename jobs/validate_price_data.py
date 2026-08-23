#!/usr/bin/env python
"""
Daily price validation — runs at 20:33 UTC (Sun-Thu) after sync_prices (20:30)
and before snapshot_portfolio (20:40).

Three checks:
  1. Large daily moves (>25%) on stocks priced >= $0.02 — potential splits or
     data errors. The price floor excludes sub-2-cent nano-caps: at a $0.001 tick
     a single-tick move is 25-100%+, which is quantization noise, not a split or
     data error (2026-07-09: 14 of 14 large-move flags were sub-cent nano-caps,
     hard-failing the job daily and masking real issues — see the arbi wake
     2026-07-11 triage).
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
from asxos.domain.prices.coverage import latest_complete_trading_day
from asxos.jobs.utils.job_monitor import JobMonitor

JOB_NAME = "validate_price_data"
_LARGE_MOVE_THRESHOLD = 0.25
# Ignore large %-moves on sub-2-cent nano-caps: at a $0.001 tick, a single-tick move
# is 25-100%+ (price quantization, not a split/data error). Applied to the PRIOR close
# so a genuine crash from a meaningful price (e.g. $0.06 -> $0.001) is still flagged.
_LARGE_MOVE_MIN_PRICE = 0.02
_HARD_FAIL_THRESHOLD = 10


def _send_alert(subject: str, body: str) -> str | None:
    """Best-effort Resend alert. Never raises; RETURNS a failure note or None.

    The swallow is correct and stays: a dead notification channel must not
    crash the validation run that found the anomalies. What was wrong is that
    the failure left no trace anywhere. If Resend is down, the API key rotates,
    or BRIEF_TO_EMAIL is wrong, the alert evaporates and the operator
    experiences it as "the system has been quiet lately" — silence from an
    alerting system being indistinguishable from good news is the one failure
    mode it cannot afford.

    So the outcome is returned rather than discarded, and the caller records it
    on JobMonitor.note, which lands in job_runs.error_message on an otherwise
    successful run. That makes undelivered alerts queryable after the fact.

    Returns the exception CLASS NAME, never str(exc): a Resend/httpx error
    embeds the request URL, and the API key rides in the Authorization header
    or query string depending on the client path. job_runs is queryable and
    agent-readable (CWE-532). JobMonitor redacts known secret shapes on the way
    in, but not leaking them in the first place is the stronger position.
    """
    try:
        import resend

        api_key = os.environ.get("RESEND_API_KEY", "")
        to = os.environ.get("BRIEF_TO_EMAIL", "")
        sender = os.environ.get("BRIEF_FROM_EMAIL", "")
        if not (api_key and to and sender):
            # A deliberate no-send (local runs, --no-send style configs) is not
            # the same event as a failed send, but it is still an alert that did
            # not arrive, so it is reported — named distinctly so the two are
            # never conflated when reading job_runs.
            return "alert not sent: RESEND_API_KEY/BRIEF_TO_EMAIL/BRIEF_FROM_EMAIL not all set"

        resend.api_key = api_key
        resend.Emails.send({
            "from": sender,
            "to": to,
            "subject": subject,
            "html": f"<pre>{body}</pre>",
        })
    except Exception as exc:
        return f"alert send failed: {type(exc).__name__}"
    return None


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
          AND u.is_active = TRUE AND u.security_kind = 'au_equity'
          AND prev.close >= $3
          AND ABS(p.close / NULLIF(prev.close, 0) - 1) > $2
        ORDER BY move_pct DESC
        """,
        as_of,
        _LARGE_MOVE_THRESHOLD,
        _LARGE_MOVE_MIN_PRICE,
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
        WHERE  u.is_active = TRUE AND u.security_kind = 'au_equity'
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
        WHERE u.is_active = TRUE AND u.security_kind = 'au_equity'
          AND p.close <= 0
          AND p.dt >= $1::date - 7
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


async def _run(as_of: date, *, anchor: bool = True) -> None:
    healthcheck_url = settings.healthcheck_url_validate_price_data
    await init_pool()
    try:
        async with JobMonitor(JOB_NAME, as_of, healthcheck_url) as monitor:
            async with acquire() as conn:
                # Anchor to the latest COMPLETE trading day (same util and
                # rationale as the brief): asking "who is missing a price for
                # <calendar today>" on a weekend/holiday reports every active
                # symbol missing — a Saturday manual dispatch paged
                # "MISSING_PRICES: 1880" about a day the ASX never traded.
                # A day with no complete data is not a data-quality finding
                # about the SYMBOLS; validate the last day that actually was.
                #
                # Deliberate trade-off, stated: if the whole pipeline stops,
                # the anchor walks back to the last good day and this check
                # stays quiet — the day-gap alarm is the workflow ordering
                # (a failed sync blocks this step entirely) plus
                # pipeline-health's degraded check reading the note that
                # sync_prices now attaches to any non-COMPLETE day (R1: that
                # note is what makes this sentence true — without it a
                # PARTIAL day was invisible to every check).
                # An explicit --as-of bypasses anchoring (anchor=False).
                effective = as_of
                if anchor:
                    latest = await latest_complete_trading_day(conn)
                    if latest is not None and latest != as_of:
                        print(
                            f"[validate] anchoring to latest complete trading "
                            f"day {latest} (as_of {as_of} has no complete data)"
                        )
                        effective = latest
                issues = await _query_anomalies(conn, effective)

            monitor.rows_written = len(issues)

            if not issues:
                return

            body = "\n".join(f"• {i}" for i in issues)
            if len(issues) <= _HARD_FAIL_THRESHOLD:
                monitor.note = _send_alert(
                    f"[asxos] price anomalies detected — {effective}",
                    body,
                )
                return
            else:
                # Deliberately NOT recorded on the monitor: this branch raises,
                # and JobMonitor's exit gives the exception string priority over
                # note, so assigning here would be dead. The RuntimeError below
                # already makes the run 'failure' and visible; an undelivered
                # alert on an already-failing run is not the silent case this
                # change exists to expose.
                _send_alert(
                    f"[asxos] PRICE VALIDATION HARD FAIL — {len(issues)} anomalies — {effective}",
                    body,
                )
                raise RuntimeError(
                    f"price validation failed: {len(issues)} anomalies on {effective}"
                )
    finally:
        await close_pool()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Validate price data quality")
    parser.add_argument("--as-of", metavar="YYYY-MM-DD", help="Date override (default: today)")
    args = parser.parse_args()
    as_of = date.fromisoformat(args.as_of) if args.as_of else date.today()
    # An explicit --as-of means "validate exactly this day" — no anchoring.
    asyncio.run(_run(as_of, anchor=args.as_of is None))
