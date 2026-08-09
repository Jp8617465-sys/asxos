#!/usr/bin/env python
"""
Thesis invalidation condition checker — daily (0042 rules-integrity core, D1/R2).

Evaluates the STORED machine baseline on thesis_conditions
(enforcement_kind / enforcement_threshold) — never re-parsing condition text
at runtime. The baseline is what the shared parser
(asxos/domain/theses/condition_parser.py) echoed to James at authoring, and
that promise is the thing being enforced; the R8 sweep
(jobs/sweep_rule_integrity.py) detects baseline-vs-current-parser drift.

Scope: theses with status IN ('active', 'watching') — widened from
active-only during the 0042 rewrite (design divergence #3, register #22:
a watching thesis' rules rotting silently is the CBA blind spot).

State machine per condition (asxos/domain/theses/conditions.py, one
transaction per transition, idempotent via the events UNIQUE):
  active|re_armed + breaching close  → triggered   (event + revision + alert)
  triggered + recaptured close (v1: single close) → re_armed (event + revision)
  triggered + still breached         → no-op (duration is DERIVED from events,
                                      never a counter — no daily spam)

Stale-price guard (SP): if the latest close's dt < as_of − 5 calendar days
the symbol is NOT evaluated — no transition on stale tape; the skip is a
loud JobMonitor.note finding, as is a symbol with no price rows at all.

Unparseable (not_machine_checkable) conditions are counted and surfaced in
JobMonitor.note — a skip is never silent (register #5).

Alerts (asxos/domain/theses/alerts.py): action verbs appear only for
underwritten + hard_exit + not disposal-locked; otherwise review-framed with
the demotion reason on the face. Alert bodies are html-escaped by the
builder. DB transitions are committed BEFORE any send, so the email is
at-most-once and a send retry cannot double-write. _send_alert RAISES on
missing RESEND env and lets send exceptions propagate → JobMonitor 'failure'
→ Healthchecks /fail (design divergence #1; register #20's silent swallow is
gone).
"""
from __future__ import annotations

import asyncio
import os
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from asxos.db import acquire, close_pool, init_pool
from asxos.domain.portfolio.locks import get_disposal_locks
from asxos.domain.theses import conditions as conditions_svc
from asxos.domain.theses.alerts import build_invalidation_alert
from asxos.domain.theses.condition_parser import evaluate
from asxos.jobs._helpers import require_personal_use_job
from asxos.jobs.utils.job_monitor import JobMonitor

JOB_NAME = "check_thesis_invalidations"
_STALE_CLOSE_DAYS = 5


async def _fetch_conditions(conn) -> list[dict[str, Any]]:  # type: ignore[no-untyped-def]
    """All open conditions (machine-checkable AND unparseable — the latter are
    counted, never silently dropped) for live theses."""
    rows = await conn.fetch(
        """
        SELECT c.condition_id, c.thesis_id, c.ordinal, c.condition_text,
               c.trigger_semantics, c.status AS condition_status,
               c.enforcement_kind, c.enforcement_threshold,
               t.symbol, t.attestation
        FROM   thesis_conditions c
        JOIN   theses t ON t.thesis_id = c.thesis_id
        WHERE  t.status IN ('active', 'watching')
          AND  c.status IN ('active', 'triggered', 're_armed')
        ORDER  BY t.symbol, c.ordinal
        """
    )
    return [dict(r) for r in rows]


async def _fetch_latest_close(conn, symbol: str, as_of: date) -> tuple[Decimal, date] | None:  # type: ignore[no-untyped-def]
    """(close, dt) — the dt is the price-date provenance every event carries
    (register #21: the pre-0042 note stamped the RUN date)."""
    row = await conn.fetchrow(
        """
        SELECT close, dt FROM prices
        WHERE  symbol = $1 AND dt <= $2
        ORDER  BY dt DESC LIMIT 1
        """,
        symbol,
        as_of,
    )
    return (Decimal(str(row["close"])), row["dt"]) if row else None


def _send_alert(subject: str, escaped_body: str) -> None:
    """Send one invalidation email. escaped_body is already html-escaped by
    the alert builder — interpolated into <pre> verbatim.

    Hard-fails (CLAUDE.md #10) on missing env and lets resend exceptions
    propagate: a discipline event must reach James before it costs money, and
    an unsendable alert is a job FAILURE, not a shrug (register #20). The DB
    transitions are already committed and idempotent, so the retry path is
    safe.
    """
    api_key = os.environ.get("RESEND_API_KEY", "")
    to = os.environ.get("BRIEF_TO_EMAIL", "")
    sender = os.environ.get("BRIEF_FROM_EMAIL", "")
    if not (api_key and to and sender):
        raise RuntimeError(
            "check_thesis_invalidations: RESEND_API_KEY / BRIEF_TO_EMAIL / "
            "BRIEF_FROM_EMAIL must all be set — an invalidation alert with "
            "nowhere to go is a silent discipline failure"
        )

    import resend  # deferred: only needed once there is something to send

    resend.api_key = api_key
    resend.Emails.send({
        "from": sender,
        "to": to,
        "subject": subject,
        "html": f"<pre>{escaped_body}</pre>",
    })


async def _run(as_of: date) -> None:
    # Personal-use firewall (Part 0 Q1 / CLAUDE.md #10). In-code backstop so a
    # missing flag fails loud rather than relying on the scheduler env alone.
    require_personal_use_job()
    healthcheck_url = os.environ.get("HEALTHCHECK_URL_CHECK_THESIS_INVALIDATIONS", "")
    await init_pool()
    try:
        async with JobMonitor(JOB_NAME, as_of, healthcheck_url) as monitor:
            async with acquire() as conn:
                conds = await _fetch_conditions(conn)

            by_symbol: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for c in conds:
                by_symbol[c["symbol"]].append(c)

            notes: list[str] = []
            transitions = 0
            # (symbol, condition-row, close, price_date) for post-commit sends.
            pending_alerts: list[tuple[str, dict[str, Any], Decimal, date]] = []

            for symbol in sorted(by_symbol):
                async with acquire() as conn:
                    got = await _fetch_latest_close(conn, symbol, as_of)
                if got is None:
                    notes.append(f"{symbol}: NO price rows — not evaluated")
                    continue
                close, price_date = got
                if price_date < as_of - timedelta(days=_STALE_CLOSE_DAYS):
                    # SP guard: no transition on stale tape — loud, counted.
                    notes.append(
                        f"{symbol}: stale tape (latest close {price_date}, "
                        f"as_of {as_of}) — not evaluated"
                    )
                    continue

                for c in by_symbol[symbol]:
                    if c["enforcement_kind"] == "not_machine_checkable":
                        continue  # counted + surfaced below, never transitioned
                    threshold = Decimal(str(c["enforcement_threshold"]))
                    breached = evaluate(c["enforcement_kind"], threshold, close)

                    if c["condition_status"] in ("active", "re_armed") and breached:
                        async with acquire() as conn:
                            applied = await conditions_svc.record_trigger(
                                conn,
                                c["condition_id"],
                                price_date=price_date,
                                observed_close=close,
                                source="job",
                            )
                        if applied:
                            transitions += 1
                            pending_alerts.append((symbol, c, close, price_date))
                    elif c["condition_status"] == "triggered" and not breached:
                        async with acquire() as conn:
                            applied = await conditions_svc.record_re_arm(
                                conn,
                                c["condition_id"],
                                price_date=price_date,
                                observed_close=close,
                                source="job",
                            )
                        if applied:
                            transitions += 1
                    # triggered + still breached → deliberate no-op (no spam;
                    # breach duration is derived from events, never counted).

            unparseable = [c for c in conds if c["enforcement_kind"] == "not_machine_checkable"]
            if unparseable:
                syms = ", ".join(sorted({c["symbol"] for c in unparseable}))
                notes.append(
                    f"{len(unparseable)} condition(s) NOT machine-checked — "
                    f"manual review only ({syms})"
                )

            # Alerts AFTER all transitions are committed (at-most-once email;
            # the events UNIQUE makes the DB side idempotent on retry).
            if pending_alerts:
                alert_symbols = sorted({s for s, _c, _cl, _d in pending_alerts})
                async with acquire() as conn:
                    locks = await get_disposal_locks(conn, alert_symbols, as_of)
                for symbol, c, close, price_date in pending_alerts:
                    alert = build_invalidation_alert(
                        thesis={
                            "symbol": symbol,
                            "thesis_id": c["thesis_id"],
                            "attestation": c["attestation"],
                        },
                        condition=c,
                        event={
                            "price_date": price_date,
                            "observed_close": close,
                            "threshold": c["enforcement_threshold"],
                        },
                        lock=locks.get(symbol),
                    )
                    _send_alert(alert.subject, alert.body)

            monitor.rows_written = transitions
            if notes:
                monitor.note = "; ".join(notes)
    finally:
        await close_pool()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Check thesis invalidation conditions")
    parser.add_argument("--as-of", metavar="YYYY-MM-DD", help="Date override (default: today)")
    args = parser.parse_args()

    as_of = date.fromisoformat(args.as_of) if args.as_of else date.today()
    asyncio.run(_run(as_of))
