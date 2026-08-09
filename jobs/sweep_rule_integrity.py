#!/usr/bin/env python
"""
Rule-integrity sweep — weekly (0042, R8 per D7).

SCHEDULING LIVES IN GITHUB ACTIONS (.github/workflows/weekly-research.yml,
last step of the Saturday chain) — NOT render.yaml: Render is being
decommissioned. Env needed: DATABASE_URL + ASXOS_PERSONAL_USE=1 (this job
writes integrity flags + JobMonitor notes only; no alert email).

Per live rule (theses.status NOT IN ('exited', 'expired') — includes
'watching' AND 'research', closing the CBA blind spot, register #22):

  1. Re-lint (asxos/domain/theses/lint.py): ladder incoherence — placeholder
     rows included, flagged not blocked — degenerate bands, born/currently-
     breached stop on underwritten rows, capital-against-placeholder.
  2. Re-parse each condition_text with the CURRENT parser and compare to the
     stored baseline. Identical kind+threshold → silently refresh
     parser_version; different → PARSE_DRIFT flag. The baseline is NEVER
     auto-changed on drift — the enforced promise only changes by human
     re-authoring.
  3. Re-derive frozen embedded values (embedded_figures with recognised
     labels, e.g. a 50d MA from prices); drift beyond 1% → FROZEN_VALUE_DRIFT
     flag quoting authored vs current. Decimal-only arithmetic.
  4. Tape replay of triggered/re_armed conditions since their last event: any
     missed transitions (dark-machinery gaps, register #6) are REPAIRED — the
     missing triggered/re_armed events are written with correct price_dates,
     source='sweep', plus a STALE_TRIGGER_STATE flag recording the gap
     (design divergence #6: a flag about a stale state that stays stale fails
     the north star; the repair is fully provenance-marked). First production
     run performs the HUBS E05 episode backfill.
  5. Doc-vs-profile drift: profiles.capital_aud vs the latest
     portfolio_daily_snapshots.capital_aud (>1% → thesis-less finding in
     JobMonitor.note). Cap-constant reconciliation against a canonical
     limits table is STUBBED pending D3 — deliberately noted here, not
     silently absent.

Writes: per-thesis findings → thesis_revisions rows with
revision_type='integrity_flag', diff = {"flag": {"code": ..., "detail":
{...}, "fingerprint": <sha256-16>}} (a documented extension of the diff
contract for non-field-change rows). Dedupe: a re-run writes nothing when
the newest integrity_flag row for (thesis, code) carries the same
fingerprint — the append-only log never spams. rows_written = flags +
repaired events. All writes idempotent (events UNIQUE + fingerprint dedupe).

Stale-price guard (SP), same bar as the daily job: latest close older than
as_of − 5 calendar days → that symbol's close-dependent checks (born-breach,
tape replay) are skipped with a loud note; no transition on stale tape.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from asxos.db import acquire, close_pool, init_pool
from asxos.domain.theses import lint
from asxos.domain.theses.condition_parser import (
    PARSER_VERSION,
    evaluate,
    parse_condition,
)
from asxos.jobs._helpers import require_personal_use_job
from asxos.jobs.utils.job_monitor import JobMonitor

JOB_NAME = "sweep_rule_integrity"
_STALE_CLOSE_DAYS = 5
_FROZEN_VALUE_TOLERANCE = Decimal("0.01")  # 1% relative drift
_PROFILE_DRIFT_TOLERANCE = Decimal("0.01")

# Flag codes (shared vocabulary with lint.py where applicable).
STALE_TRIGGER_STATE = "STALE_TRIGGER_STATE"
PARSE_DRIFT = "PARSE_DRIFT"
FROZEN_VALUE_DRIFT = "FROZEN_VALUE_DRIFT"


def _fingerprint(detail: dict[str, Any]) -> str:
    """Stable 16-hex fingerprint of a finding's detail — the dedupe key."""
    return hashlib.sha256(
        json.dumps(detail, sort_keys=True, default=str).encode()
    ).hexdigest()[:16]


async def _write_flag(conn, thesis_id: int, code: str, detail: dict[str, Any], message: str) -> bool:  # type: ignore[no-untyped-def]
    """Append one integrity_flag revision unless the newest flag for
    (thesis, code) already carries the same fingerprint. Returns True if
    written."""
    fp = _fingerprint(detail)
    latest = await conn.fetchrow(
        """
        SELECT diff FROM thesis_revisions
        WHERE thesis_id = $1
          AND revision_type = 'integrity_flag'
          AND diff->'flag'->>'code' = $2
        ORDER BY revised_at DESC, revision_id DESC
        LIMIT 1
        """,
        thesis_id,
        code,
    )
    if latest is not None:
        prev = latest["diff"]
        if isinstance(prev, str):
            prev = json.loads(prev)
        if prev.get("flag", {}).get("fingerprint") == fp:
            return False
    await conn.execute(
        """
        INSERT INTO thesis_revisions
            (thesis_id, revised_at, revision_type, diff, reasoning)
        VALUES ($1, NOW(), 'integrity_flag', $2::jsonb, $3)
        """,
        thesis_id,
        # default=str: Decimals/dates land as strings — the same Decimal-
        # string diff contract every thesis_revisions writer follows.
        json.dumps(
            {"flag": {"code": code, "detail": detail, "fingerprint": fp}},
            default=str,
        ),
        message,
    )
    return True


async def _fetch_latest_close(conn, symbol: str, as_of: date) -> tuple[Decimal, date] | None:  # type: ignore[no-untyped-def]
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


async def _sma(conn, symbol: str, n_days: int, as_of: date) -> Decimal | None:  # type: ignore[no-untyped-def]
    """N-day simple moving average of closes as of ``as_of``, Decimal-only.
    None when fewer than n_days closes exist (insufficient tape, not an
    error)."""
    rows = await conn.fetch(
        """
        SELECT close FROM prices
        WHERE  symbol = $1 AND dt <= $2
        ORDER  BY dt DESC LIMIT $3
        """,
        symbol,
        as_of,
        n_days,
    )
    if len(rows) < n_days:
        return None
    total = sum((Decimal(str(r["close"])) for r in rows), Decimal("0"))
    return total / Decimal(n_days)


async def _replay_condition(conn, cond: dict[str, Any], symbol: str, as_of: date) -> tuple[int, list[dict[str, Any]]]:  # type: ignore[no-untyped-def]
    """Tape-replay one triggered/re_armed machine-checkable condition since
    its last event. Returns (events_written, missed-transition dicts).

    Repairs are written source='sweep' with ON CONFLICT DO NOTHING (idempotent
    re-runs), plus a final guarded status UPDATE when the replayed end-state
    differs from the stored one. Anchor rule: replay starts AFTER the last
    recorded event's price_date; a triggered/re_armed condition with NO events
    at all has no trustworthy anchor — that is flagged by the caller, never
    guessed at (conservative reading of design §7.4).
    """
    last = await conn.fetchrow(
        """
        SELECT price_date FROM thesis_condition_events
        WHERE condition_id = $1
        ORDER BY price_date DESC, event_id DESC
        LIMIT 1
        """,
        cond["condition_id"],
    )
    if last is None:
        return 0, []

    closes = await conn.fetch(
        """
        SELECT dt, close FROM prices
        WHERE symbol = $1 AND dt > $2 AND dt <= $3
        ORDER BY dt
        """,
        symbol,
        last["price_date"],
        as_of,
    )
    threshold = Decimal(str(cond["enforcement_threshold"]))
    state = cond["status"]
    missed: list[dict[str, Any]] = []
    for row in closes:
        close = Decimal(str(row["close"]))
        breached = evaluate(cond["enforcement_kind"], threshold, close)
        if state == "triggered" and not breached:
            missed.append({"event_type": "re_armed", "price_date": row["dt"], "close": close})
            state = "re_armed"
        elif state == "re_armed" and breached:
            missed.append({"event_type": "triggered", "price_date": row["dt"], "close": close})
            state = "triggered"

    if not missed:
        return 0, []

    written = 0
    async with conn.transaction():
        for m in missed:
            ins = await conn.execute(
                """
                INSERT INTO thesis_condition_events
                    (condition_id, thesis_id, event_type, price_date,
                     observed_close, threshold, source, note)
                VALUES ($1, $2, $3, $4, $5, $6, 'sweep',
                        'sweep tape-replay repair (STALE_TRIGGER_STATE): transition '
                        'missed by the daily job, reconstructed from prices')
                ON CONFLICT (condition_id, price_date, event_type) DO NOTHING
                """,
                cond["condition_id"],
                cond["thesis_id"],
                m["event_type"],
                m["price_date"],
                m["close"],
                threshold,
            )
            if not ins.endswith(" 0"):
                written += 1
        if state != cond["status"]:
            upd = await conn.execute(
                """
                UPDATE thesis_conditions
                SET status = $1, updated_at = NOW()
                WHERE condition_id = $2 AND status = $3
                """,
                state,
                cond["condition_id"],
                cond["status"],
            )
            if upd != "UPDATE 1":
                raise RuntimeError(
                    f"sweep replay lost-update guard: condition "
                    f"{cond['condition_id']} status moved during replay "
                    f"(expected {cond['status']!r})"
                )
    return written, missed


async def _sweep_thesis(conn, thesis: dict[str, Any], as_of: date) -> tuple[int, list[str]]:  # type: ignore[no-untyped-def]
    """All R8 checks for one live thesis. Returns (rows_written, notes)."""
    rows_written = 0
    notes: list[str] = []
    thesis_id = thesis["thesis_id"]
    symbol = thesis["symbol"]

    # ── 1. Re-lint (placeholders included — flagged, never blocked) ────────
    for f in lint.lint_ladder(
        stop_price=thesis["stop_price"],
        entry_band_lower=thesis["entry_band_lower"],
        entry_band_upper=thesis["entry_band_upper"],
        target_price=thesis["target_price"],
    ):
        detail = {
            "stop_price": thesis["stop_price"],
            "entry_band_lower": thesis["entry_band_lower"],
            "entry_band_upper": thesis["entry_band_upper"],
            "target_price": thesis["target_price"],
            "attestation": thesis["attestation"],
        }
        if await _write_flag(conn, thesis_id, f.code, detail, f"{symbol}: {f.message}"):
            rows_written += 1

    uc = lint.lint_unattested_with_capital(
        attestation=thesis["attestation"], status=thesis["status"]
    )
    if uc is not None:
        detail = {"status": thesis["status"], "attestation": thesis["attestation"]}
        if await _write_flag(conn, thesis_id, uc.code, detail, f"{symbol}: {uc.message}"):
            rows_written += 1

    got = await _fetch_latest_close(conn, symbol, as_of)
    tape_fresh = got is not None and got[1] >= as_of - timedelta(days=_STALE_CLOSE_DAYS)
    if got is None:
        notes.append(f"{symbol}: NO price rows — close-dependent checks skipped")
    elif not tape_fresh:
        notes.append(
            f"{symbol}: stale tape (latest close {got[1]}) — close-dependent "
            "checks skipped, no transition on stale tape"
        )

    if thesis["attestation"] == "underwritten" and tape_fresh and got is not None:
        bb = lint.lint_born_breached(stop_price=thesis["stop_price"], latest_close=got[0])
        if bb is not None:
            detail = {
                "stop_price": thesis["stop_price"],
                "latest_close": got[0],
                "price_date": got[1],
            }
            if await _write_flag(conn, thesis_id, bb.code, detail, f"{symbol}: {bb.message}"):
                rows_written += 1

    # ── 2/3/4. Conditions: parse drift, frozen values, tape replay ─────────
    conds = await conn.fetch(
        """
        SELECT condition_id, thesis_id, ordinal, condition_text, status,
               enforcement_kind, enforcement_threshold, parser_version
        FROM thesis_conditions
        WHERE thesis_id = $1 AND status <> 'resolved'
        ORDER BY ordinal
        """,
        thesis_id,
    )
    for c in conds:
        cond = dict(c)
        reparsed = parse_condition(cond["condition_text"])

        same_baseline = (
            reparsed.kind == cond["enforcement_kind"]
            and reparsed.threshold == cond["enforcement_threshold"]
        )
        if same_baseline:
            if cond["parser_version"] != PARSER_VERSION:
                # Identical baseline under the current parser — silent refresh.
                await conn.execute(
                    """
                    UPDATE thesis_conditions
                    SET parser_version = $1, updated_at = NOW()
                    WHERE condition_id = $2
                    """,
                    PARSER_VERSION,
                    cond["condition_id"],
                )
        else:
            detail = {
                "condition_id": cond["condition_id"],
                "ordinal": cond["ordinal"],
                "stored_kind": cond["enforcement_kind"],
                "stored_threshold": cond["enforcement_threshold"],
                "stored_parser_version": cond["parser_version"],
                "current_kind": reparsed.kind,
                "current_threshold": reparsed.threshold,
                "current_parser_version": PARSER_VERSION,
            }
            msg = (
                f"{symbol} condition {cond['ordinal']}: baseline drift — stored "
                f"{cond['enforcement_kind']}/{cond['enforcement_threshold']} "
                f"({cond['parser_version']}) vs current {reparsed.kind}/"
                f"{reparsed.threshold} ({PARSER_VERSION}). Baseline NOT changed "
                "— re-author to change the enforced promise."
            )
            if await _write_flag(conn, thesis_id, PARSE_DRIFT, detail, msg):
                rows_written += 1

        for fig in reparsed.embedded_figures:
            if not fig.label.endswith("d MA"):
                continue
            n_days = int(fig.label.removesuffix("d MA"))
            current = await _sma(conn, symbol, n_days, as_of)
            if current is None or fig.value == 0:
                notes.append(
                    f"{symbol} condition {cond['ordinal']}: cannot re-derive "
                    f"'{fig.label}' (insufficient tape)"
                )
                continue
            drift = abs(current - fig.value) / fig.value
            if drift > _FROZEN_VALUE_TOLERANCE:
                quantised = current.quantize(Decimal("0.01"))
                detail = {
                    "condition_id": cond["condition_id"],
                    "ordinal": cond["ordinal"],
                    "label": fig.label,
                    "authored_value": fig.value,
                    "current_value": quantised,
                }
                msg = (
                    f"{symbol} condition {cond['ordinal']}: frozen embedded value "
                    f"'{fig.label}' authored as {fig.value} but currently "
                    f"{quantised} (>1% drift) — the text asserts a stale number"
                )
                if await _write_flag(conn, thesis_id, FROZEN_VALUE_DRIFT, detail, msg):
                    rows_written += 1

        if (
            cond["enforcement_kind"] != "not_machine_checkable"
            and cond["status"] in ("triggered", "re_armed")
            and tape_fresh
        ):
            written, missed = await _replay_condition(conn, cond, symbol, as_of)
            rows_written += written
            if missed:
                detail = {
                    "condition_id": cond["condition_id"],
                    "ordinal": cond["ordinal"],
                    "from_status": cond["status"],
                    "missed": [
                        {"event_type": m["event_type"], "price_date": m["price_date"]}
                        for m in missed
                    ],
                }
                msg = (
                    f"{symbol} condition {cond['ordinal']}: {len(missed)} missed "
                    "transition(s) repaired from tape (source='sweep') — the "
                    "stored state had gone dark (register #6)"
                )
                if await _write_flag(conn, thesis_id, STALE_TRIGGER_STATE, detail, msg):
                    rows_written += 1
            has_events = await conn.fetchval(
                "SELECT EXISTS (SELECT 1 FROM thesis_condition_events WHERE condition_id = $1)",
                cond["condition_id"],
            )
            if not has_events:
                detail = {
                    "condition_id": cond["condition_id"],
                    "ordinal": cond["ordinal"],
                    "status": cond["status"],
                    "anchor": "none",
                }
                msg = (
                    f"{symbol} condition {cond['ordinal']}: status "
                    f"{cond['status']!r} with NO events — no trustworthy replay "
                    "anchor; repair by hand, not by guess"
                )
                if await _write_flag(conn, thesis_id, STALE_TRIGGER_STATE, detail, msg):
                    rows_written += 1

    return rows_written, notes


async def _profile_drift_note(conn) -> str | None:  # type: ignore[no-untyped-def]
    """R8 item 5 — doc-vs-profile drift. Thesis-less → JobMonitor.note only.
    Cap-constant reconciliation against a canonical limits table is STUBBED
    pending D3 (see module docstring)."""
    prof = await conn.fetchrow(
        "SELECT capital_aud FROM profiles WHERE is_active = TRUE"
    )
    snap = await conn.fetchrow(
        "SELECT as_of, capital_aud FROM portfolio_daily_snapshots ORDER BY as_of DESC LIMIT 1"
    )
    if prof is None or snap is None or snap["capital_aud"] is None:
        return None
    prof_cap = Decimal(str(prof["capital_aud"]))
    snap_cap = Decimal(str(snap["capital_aud"]))
    if snap_cap == 0:
        return None
    drift = abs(prof_cap - snap_cap) / snap_cap
    if drift > _PROFILE_DRIFT_TOLERANCE:
        return (
            f"profile capital_aud {prof_cap} vs latest snapshot "
            f"{snap_cap} ({snap['as_of']}) — {drift:.1%} drift (>1%)"
        )
    return None


async def _run(as_of: date) -> None:
    require_personal_use_job()
    healthcheck_url = os.environ.get("HEALTHCHECK_URL_SWEEP_RULE_INTEGRITY", "")
    await init_pool()
    try:
        async with JobMonitor(JOB_NAME, as_of, healthcheck_url) as monitor:
            rows_written = 0
            notes: list[str] = []
            async with acquire() as conn:
                theses = await conn.fetch(
                    """
                    SELECT thesis_id, symbol, status, attestation,
                           stop_price, entry_band_lower, entry_band_upper,
                           target_price
                    FROM theses
                    WHERE status NOT IN ('exited', 'expired')
                    ORDER BY thesis_id
                    """
                )
                for t in theses:
                    n, t_notes = await _sweep_thesis(conn, dict(t), as_of)
                    rows_written += n
                    notes.extend(t_notes)

                drift = await _profile_drift_note(conn)
                if drift:
                    notes.append(drift)

            monitor.rows_written = rows_written
            if notes:
                monitor.note = "; ".join(notes)
    finally:
        await close_pool()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Weekly rule-integrity sweep (R8)")
    parser.add_argument("--as-of", metavar="YYYY-MM-DD", help="Date override (default: today)")
    args = parser.parse_args()

    as_of = date.fromisoformat(args.as_of) if args.as_of else date.today()
    asyncio.run(_run(as_of))
