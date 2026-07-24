#!/usr/bin/env python
"""Macro-thesis falsifier/catalyst evaluator — daily.

Layer A of the macro-thesis learning loop
(docs/proposals/macro-thesis-learning-loop-2026-07-21.md §3). For each approved,
non-retired macro thesis, evaluate its structured ``machine_conditions``
(migration 0041) against the accumulating ``market_context_current`` history and
UPSERT one outcome row into ``macro_thesis_outcomes``.

These are multi-day conditions ("pct_above_200d_ma >= 0.50 on 10 consecutive
daily rows"), so the evaluator reads HISTORY — every market_context row from the
thesis's created_at through the run's as_of — not just the latest snapshot.

Discipline (mirrors check_thesis_invalidations.py): a falsifier trigger does NOT
auto-retire and does NOT touch governance_status. It records the outcome and
sends James a best-effort alert email to review. Retirement stays a human
governance act (system proposes, human decides).

Conservative-on-missing-data invariant: a NULL signal value in the window counts
as does-NOT-satisfy — the loop never confirms or falsifies a thesis on absent
data. Fewer than ``window`` rows of history also means a condition cannot yet be
met (status stays open).
"""
from __future__ import annotations

import asyncio
import json
import operator
import os
from datetime import date
from decimal import Decimal
from typing import Any, get_args

from dateutil.relativedelta import relativedelta

from asxos.db import acquire, close_pool, init_pool
from asxos.domain.theses.schemas import MacroSignal
from asxos.jobs._helpers import require_personal_use_job
from asxos.jobs.utils.job_monitor import JobMonitor

JOB_NAME = "score_macro_theses"

# Signal name -> market_context_current column is IDENTITY (the Literal values
# are the column names verbatim, migration 0013). This frozenset is the
# raw-SQL / stale-annotation guard: a machine_conditions row citing a signal
# outside it hard-fails rather than silently reading a missing column as NULL
# (which would masquerade as "not satisfied" and hide a broken annotation).
_VALID_SIGNALS: frozenset[str] = frozenset(get_args(MacroSignal))

_OPS = {
    "gt": operator.gt,
    "gte": operator.ge,
    "lt": operator.lt,
    "lte": operator.le,
}

# Quantum for catalyst_progress — matches NUMERIC(18,6) so the stored value is
# deterministic (1/3 -> 0.333333) rather than carrying Decimal-context tail.
_Q6 = Decimal("0.000001")


def _as_decimal(v: object) -> Decimal:
    """Coerce a JSON-carried threshold to Decimal. Thresholds are JSON strings
    (Pydantic model_dump_json contract, CLAUDE.md #5); a float would already
    have lost precision, so reject it loud rather than launder it."""
    if isinstance(v, Decimal):
        return v
    if isinstance(v, float):
        raise RuntimeError(
            f"machine_conditions threshold {v!r} is a float; thresholds must be "
            "decimal strings (float loses precision, CLAUDE.md #5)"
        )
    return Decimal(str(v))


def _row_value(row: dict[str, Any], signal: str) -> Decimal | None:
    """The signal's value on a single market_context row, or None if absent."""
    val = row.get(signal)
    if val is None:
        return None
    return val if isinstance(val, Decimal) else Decimal(str(val))


def _condition_satisfied(rows: list[dict[str, Any]], condition: dict[str, Any]) -> bool:
    """Evaluate one MachineCondition over the market_context history ``rows``
    (ordered oldest-first). A NULL value counts as not-satisfied; fewer than
    ``window`` rows means the condition cannot be met."""
    signal = condition["signal"]
    if signal not in _VALID_SIGNALS:
        raise RuntimeError(
            f"machine_conditions references unknown signal {signal!r} — not a "
            f"market_context_current column (valid: {sorted(_VALID_SIGNALS)})"
        )
    op_fn = _OPS[condition["op"]]
    threshold = _as_decimal(condition["threshold"])
    window = int(condition["window"])
    aggregation = condition["aggregation"]

    if len(rows) < window:
        return False

    window_rows = rows[-window:]
    flags: list[bool] = []
    for r in window_rows:
        v = _row_value(r, signal)
        flags.append(v is not None and op_fn(v, threshold))

    if aggregation == "consecutive":
        return all(flags)
    if aggregation == "any":
        return any(flags)
    if aggregation == "majority":
        return sum(flags) * 2 > len(flags)  # strict >50%
    raise RuntimeError(f"unknown aggregation {aggregation!r}")


def _predicate_satisfied(rows: list[dict[str, Any]], predicate: dict[str, Any]) -> bool:
    """Combine a predicate's conditions: combine='all' = AND, 'any' = OR."""
    flags = [_condition_satisfied(rows, c) for c in predicate["conditions"]]
    if predicate.get("combine", "all") == "any":
        return any(flags)
    return all(flags)


def _catalyst_progress(rows: list[dict[str, Any]], predicate: dict[str, Any]) -> Decimal:
    """Fraction of catalyst conditions currently satisfied, in [0, 1]."""
    conditions = predicate["conditions"]
    n_ok = sum(1 for c in conditions if _condition_satisfied(rows, c))
    return (Decimal(n_ok) / Decimal(len(conditions))).quantize(_Q6)


def score_thesis(
    machine_conditions: dict[str, Any] | None,
    rows: list[dict[str, Any]],
    *,
    created_at: date,
    eval_as_of: date,
    horizon_months: int | None,
) -> dict[str, Any]:
    """Pure scoring core (no DB). Returns the fields written to one
    macro_thesis_outcomes row.

    Status precedence: falsifier True -> 'falsified'; else catalyst True ->
    'confirmed'; else past the calendar horizon -> 'expired'; else 'open'.
    Horizon is calendar arithmetic (relativedelta, CLAUDE.md #6). A thesis with
    no evaluable predicate scores 'open' with reason='no_machine_conditions'.
    """
    catalyst = (machine_conditions or {}).get("catalyst")
    falsifier = (machine_conditions or {}).get("falsifier")

    if catalyst is None and falsifier is None:
        return {
            "status": "open",
            "catalyst_progress": None,
            "falsifier_triggered": False,
            "evaluation_detail": {"reason": "no_machine_conditions"},
        }

    falsifier_hit = _predicate_satisfied(rows, falsifier) if falsifier else False
    catalyst_hit = _predicate_satisfied(rows, catalyst) if catalyst else False
    catalyst_progress = _catalyst_progress(rows, catalyst) if catalyst else None

    if falsifier_hit:
        status = "falsified"
    elif catalyst_hit:
        status = "confirmed"
    elif (
        horizon_months is not None
        and eval_as_of > created_at + relativedelta(months=horizon_months)
    ):
        status = "expired"
    else:
        status = "open"

    return {
        "status": status,
        "catalyst_progress": catalyst_progress,
        "falsifier_triggered": status == "falsified",
        "evaluation_detail": {
            "catalyst_hit": catalyst_hit,
            "falsifier_hit": falsifier_hit,
            "rows_evaluated": len(rows),
        },
    }


def _parse_machine_conditions(raw: object) -> dict[str, Any] | None:
    """machine_conditions round-trips as JSONB text (no asyncpg codec); NULL
    stays None. Thresholds are JSON strings, so no parse_float hazard."""
    if raw is None:
        return None
    if isinstance(raw, str):
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else None
    return raw if isinstance(raw, dict) else None  # defensive: always a dict in practice


def _send_alert(subject: str, body: str) -> None:
    # Best-effort — mirrors check_thesis_invalidations._send_alert. A dead email
    # channel must never fail the scoring run.
    try:
        import resend  # type: ignore[import-not-found]

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


async def _fetch_approved_theses(conn) -> list[dict[str, Any]]:  # type: ignore[no-untyped-def]
    rows = await conn.fetch(
        """
        SELECT macro_thesis_id, title, horizon_months, created_at, machine_conditions
        FROM   macro_theses
        WHERE  governance_status = 'approved'
          AND  retired_at IS NULL
        ORDER  BY macro_thesis_id
        """
    )
    return [dict(r) for r in rows]


async def _fetch_market_context_history(conn, eval_as_of: date) -> list[dict[str, Any]]:  # type: ignore[no-untyped-def]
    """All market_context_current rows through eval_as_of, oldest-first. Read
    from the VIEW (latest ingested row per as_of), never the base table."""
    rows = await conn.fetch(
        """
        SELECT * FROM market_context_current
        WHERE  as_of <= $1
        ORDER  BY as_of ASC
        """,
        eval_as_of,
    )
    return [dict(r) for r in rows]


async def _run(as_of: date) -> None:
    # Personal-use firewall (Part 0 Q1 / CLAUDE.md #10) — first statement,
    # before any pool/monitor opens.
    require_personal_use_job()
    healthcheck_url = os.environ.get("HEALTHCHECK_URL_SCORE_MACRO_THESES", "")
    await init_pool()
    try:
        async with JobMonitor(JOB_NAME, as_of, healthcheck_url) as monitor:
            async with acquire() as conn:
                theses = await _fetch_approved_theses(conn)
                history = await _fetch_market_context_history(conn, as_of)

            # Hard-fail if market_context is empty (upstream ingest broken).
            # Scoring against zero history would silently record every thesis as
            # 'open' forever and hide a dead feed (CLAUDE.md #1/#10).
            if not history:
                raise RuntimeError(
                    "market_context_current returned zero rows through "
                    f"{as_of} — the market-context ingest is broken; refusing "
                    "to score macro theses against empty history."
                )

            scored = 0
            for t in theses:
                created_at_date = t["created_at"].date()
                horizon_months = t["horizon_months"]
                machine_conditions = _parse_machine_conditions(t["machine_conditions"])

                # Slice to this thesis's own life window: created_at .. as_of.
                rows = [r for r in history if r["as_of"] >= created_at_date]

                result = score_thesis(
                    machine_conditions,
                    rows,
                    created_at=created_at_date,
                    eval_as_of=as_of,
                    horizon_months=horizon_months,
                )

                days_elapsed = (as_of - created_at_date).days
                days_to_horizon = (
                    (
                        created_at_date + relativedelta(months=horizon_months) - as_of
                    ).days
                    if horizon_months is not None
                    else None
                )

                async with acquire() as conn:
                    await conn.execute(
                        """
                        INSERT INTO macro_thesis_outcomes
                            (macro_thesis_id, as_of, status, catalyst_progress,
                             falsifier_triggered, days_elapsed, days_to_horizon,
                             evaluation_detail)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb)
                        ON CONFLICT (macro_thesis_id, as_of) DO UPDATE SET
                            status              = EXCLUDED.status,
                            catalyst_progress   = EXCLUDED.catalyst_progress,
                            falsifier_triggered = EXCLUDED.falsifier_triggered,
                            days_elapsed        = EXCLUDED.days_elapsed,
                            days_to_horizon     = EXCLUDED.days_to_horizon,
                            evaluation_detail   = EXCLUDED.evaluation_detail
                        """,
                        t["macro_thesis_id"],
                        as_of,
                        result["status"],
                        result["catalyst_progress"],
                        result["falsifier_triggered"],
                        days_elapsed,
                        days_to_horizon,
                        json.dumps(result["evaluation_detail"]),
                    )

                if result["status"] == "falsified":
                    body = (
                        f"Macro thesis #{t['macro_thesis_id']} FALSIFIED on {as_of}:\n\n"
                        f"  {t['title']}\n\n"
                        f"  {json.dumps(result['evaluation_detail'])}\n\n"
                        "The falsifier predicate triggered against market_context "
                        "history. This is NOT auto-retired — review and decide.\n"
                        f"Run: asx macro-thesis retire {t['macro_thesis_id']}"
                    )
                    _send_alert(
                        f"asxos [MACRO FALSIFIED] #{t['macro_thesis_id']} — {as_of}",
                        body,
                    )

                scored += 1

            monitor.rows_written = scored
    finally:
        await close_pool()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Score approved macro theses")
    parser.add_argument("--as-of", metavar="YYYY-MM-DD", help="Date override (default: today)")
    args = parser.parse_args()

    as_of = date.fromisoformat(args.as_of) if args.as_of else date.today()
    asyncio.run(_run(as_of))
