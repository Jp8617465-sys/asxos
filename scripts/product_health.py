#!/usr/bin/env python
"""product_health.py — the ASXOS Product Health Scorecard engine (READ-ONLY).

Answers "is ASXOS actually working today?" — not "did tests pass?". Queries live
Supabase (read-only) for data freshness, cron reality, product surfaces, and
investment readiness, grades each metric PASS / WARN / FAIL against the thresholds
in `docs/product/data-contracts.md`, and prints a markdown scorecard.

Usage:
    python scripts/product_health.py               # print scorecard to stdout
    python scripts/product_health.py --write        # also overwrite docs/product/product-health-scorecard.md

Read-only by contract: SELECTs only, no INSERT/UPDATE/DDL. Safe to run any time,
attended or unattended (it makes no capital-impacting output — it reports state).
Intended to become a daily cron (health cadence) and the data source behind /arbi.
"""
from __future__ import annotations

import argparse
import asyncio
import os
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

from asxos.db import acquire, close_pool, init_pool

TODAY = date.today()
SCORECARD_PATH = Path(__file__).resolve().parents[1] / "docs/product/product-health-scorecard.md"


@dataclass
class Check:
    section: str
    metric: str
    value: str
    grade: str  # PASS | WARN | FAIL | INFO
    note: str = ""


def _grade_age(latest: date | None, warn_days: int, fail_days: int) -> tuple[str, str]:
    if latest is None:
        return "FAIL", "no rows / no date"
    age = (TODAY - latest).days
    if age <= warn_days:
        return "PASS", f"{age}d old"
    if age <= fail_days:
        return "WARN", f"{age}d old"
    return "FAIL", f"{age}d old"


# (table, date_col-or-None, warn_days, fail_days, min_rows) — mirrors data-contracts.md.
FRESHNESS = [
    ("prices", "dt", 4, 8, 100_000),
    ("signals", "as_of", 4, 8, 1_000),
    ("market_context", "as_of", 4, 8, 1),
    ("portfolio_daily_snapshots", "as_of", 4, 9, 1),
    ("fundamentals", "as_of", 8, 20, 1_000),
]


async def _freshness(conn) -> list[Check]:  # type: ignore[no-untyped-def]
    out: list[Check] = []
    for table, col, warn, fail, min_rows in FRESHNESS:
        row = await conn.fetchrow(f"SELECT max({col}) AS latest, count(*) AS n FROM {table}")
        latest, n = row["latest"], row["n"]
        latest_d = latest if isinstance(latest, date) else (latest.date() if latest else None)
        grade, agenote = _grade_age(latest_d, warn, fail)
        if n < min_rows:
            grade = "FAIL"
        out.append(Check("Data freshness", table, f"{latest_d} ({n:,} rows)", grade, agenote))
    # signal_outcomes: no date col; presence is the signal (empty blocks decay automation).
    n = await conn.fetchval("SELECT count(*) FROM signal_outcomes")
    out.append(Check(
        "Data freshness", "signal_outcomes", f"{n:,} rows",
        "PASS" if n > 0 else "FAIL",
        "populated — decay automation is runnable" if n > 0 else "EMPTY — blocks Model A decay automation",
    ))
    return out


async def _cron_reality(conn) -> list[Check]:  # type: ignore[no-untyped-def]
    rows = await conn.fetch(
        """
        SELECT job_name,
               max(as_of) AS last_as_of,
               (array_agg(status ORDER BY as_of DESC))[1] AS last_status,
               count(*) FILTER (WHERE status='success') AS ok,
               count(*) AS total
        FROM job_runs GROUP BY job_name ORDER BY job_name
        """
    )
    out: list[Check] = []
    for r in rows:
        last, ok, total = r["last_status"], r["ok"], r["total"]
        if last == "success":
            grade = "PASS"
        elif ok == 0:
            grade = "FAIL"  # never succeeded
        else:
            grade = "WARN"
        if last == "running":  # stuck / hung
            grade = "WARN"
        note = f"{ok}/{total} ok · last {r['last_status']} @ {r['last_as_of']}"
        out.append(Check("Cron reality", r["job_name"], f"{ok}/{total}", grade, note))
    return out


async def _investment_readiness(conn) -> list[Check]:  # type: ignore[no-untyped-def]
    active = await conn.fetchval("SELECT count(*) FROM theses WHERE status='active'")
    watching = await conn.fetchval("SELECT count(*) FROM theses WHERE status='watching'")
    holdings = await conn.fetchval("SELECT count(*) FROM current_holdings")
    no_stop = await conn.fetchval(
        "SELECT count(*) FROM theses WHERE status IN ('active','watching') AND (stop_price IS NULL OR target_price IS NULL)"
    )
    overdue = await conn.fetchval(
        "SELECT count(*) FROM theses WHERE status IN ('active','watching') AND revisit_due_at::date < $1",
        TODAY,
    )
    null_conv = await conn.fetchval(
        "SELECT count(*) FROM theses WHERE status IN ('active','watching') AND conviction_level IS NULL"
    )
    # holdings whose symbol has no active thesis
    orphan = await conn.fetchval(
        """
        SELECT count(*) FROM (SELECT DISTINCT symbol FROM current_holdings) h
        WHERE NOT EXISTS (SELECT 1 FROM theses t WHERE t.symbol=h.symbol AND t.status='active')
        """
    )
    return [
        Check("Investment readiness", "active theses", str(active), "PASS" if active > 0 else "WARN"),
        Check("Investment readiness", "watching theses", str(watching), "INFO"),
        Check("Investment readiness", "open holdings", str(holdings), "INFO"),
        Check("Investment readiness", "holdings without active thesis", str(orphan), "PASS" if orphan == 0 else "WARN"),
        Check("Investment readiness", "theses missing stop/target", str(no_stop), "PASS" if no_stop == 0 else "WARN"),
        Check("Investment readiness", "revisit overdue", str(overdue), "PASS" if overdue == 0 else "WARN"),
        Check("Investment readiness", "conviction_level NULL", str(null_conv), "PASS" if null_conv == 0 else "WARN"),
    ]


def _render(checks: list[Check]) -> str:
    stamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    fails = [c for c in checks if c.grade == "FAIL"]
    warns = [c for c in checks if c.grade == "WARN"]
    lines = [
        "# ASXOS Product Health Scorecard",
        "",
        f"**Generated:** {stamp} · by `scripts/product_health.py` (read-only)",
        f"**Top line:** {len(fails)} FAIL · {len(warns)} WARN · "
        f"{len([c for c in checks if c.grade=='PASS'])} PASS",
        "",
        "> Answers *is ASXOS actually working?* — not *did tests pass?*. Thresholds: "
        "`docs/product/data-contracts.md`. This is a generated snapshot; re-run the script to refresh.",
        "",
    ]
    if fails:
        lines += ["## 🔴 FAIL — needs attention", ""]
        lines += [f"- **{c.metric}** ({c.section}): {c.value} — {c.note}" for c in fails] + [""]
    if warns:
        lines += ["## 🟡 WARN", ""]
        lines += [f"- **{c.metric}** ({c.section}): {c.value} — {c.note}" for c in warns] + [""]
    section = None
    icon = {"PASS": "🟢", "WARN": "🟡", "FAIL": "🔴", "INFO": "⚪"}
    for c in checks:
        if c.section != section:
            section = c.section
            lines += ["", f"## {section}", "", "| metric | value | grade | note |", "|---|---|---|---|"]
        lines.append(f"| {c.metric} | {c.value} | {icon[c.grade]} {c.grade} | {c.note} |")
    lines.append("")
    return "\n".join(lines)


async def _run(write: bool) -> None:
    await init_pool()
    try:
        async with acquire() as conn:
            checks = (
                await _freshness(conn)
                + await _cron_reality(conn)
                + await _investment_readiness(conn)
            )
    finally:
        await close_pool()
    md = _render(checks)
    print(md)
    if write:
        SCORECARD_PATH.write_text(md)
        print(f"\n[wrote {SCORECARD_PATH}]", flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="ASXOS product health scorecard (read-only)")
    p.add_argument("--write", action="store_true", help="overwrite docs/product/product-health-scorecard.md")
    args = p.parse_args()
    if not os.environ.get("DATABASE_URL"):
        raise SystemExit("DATABASE_URL not set — this script reads live Supabase.")
    asyncio.run(_run(args.write))
