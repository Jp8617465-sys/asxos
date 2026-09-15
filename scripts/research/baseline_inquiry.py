"""Print (or run) one report of the baseline inquiry SQL.

The SQL file holds one PRELUDE (the recursive residual-income sweep) and several REPORT
sections, each a final SELECT over the ``sweep`` CTE. Postgres cannot share a CTE across
statements, so this helper concatenates PRELUDE + the chosen report into one statement:

    .venv/bin/python scripts/research/baseline_inquiry.py C          # print REPORT C
    .venv/bin/python scripts/research/baseline_inquiry.py C --run    # run it (needs DATABASE_URL
                                                                     # to reach the pooler)

Paste the printed statement into the read-only ``supabase-ro`` connector when the sandbox
cannot reach the database (the 2026-09-16 case). Read-only by construction: the SQL is
SELECT-only and the ``--run`` path opens no transaction that writes.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import re
import sys
from pathlib import Path

SQL_PATH = Path(__file__).with_name("baseline_inquiry.sql")


def _split(text: str) -> tuple[str, dict[str, str]]:
    prelude_match = re.search(r"^-- =+ PRELUDE\n(.*?)^-- =+ END PRELUDE", text, flags=re.S | re.M)
    if prelude_match is None:
        raise SystemExit("PRELUDE markers not found in baseline_inquiry.sql")
    prelude = prelude_match.group(1).strip()
    reports: dict[str, str] = {}
    for m in re.finditer(
        r"^-- REPORT ([A-Z]) — [^\n]*\n(.*?)(?=^-- REPORT |\Z)", text, flags=re.S | re.M
    ):
        body = m.group(2).strip()
        if body.startswith("--"):  # REPORT G is documented, not executable here
            continue
        reports[m.group(1)] = body.rstrip(";").strip()
    return prelude, reports


def statement(report: str) -> str:
    prelude, reports = _split(SQL_PATH.read_text())
    if report not in reports:
        raise SystemExit(f"unknown report {report!r}; have {sorted(reports)}")
    return f"{prelude}\n{reports[report]}"


async def _run(sql: str) -> None:
    import asyncpg  # local import: printing must work without the driver

    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    try:
        rows = await conn.fetch(sql)
    finally:
        await conn.close()
    if not rows:
        print("(no rows)")
        return
    cols = list(rows[0].keys())
    print("\t".join(cols))
    for r in rows:
        print("\t".join("" if r[c] is None else str(r[c]) for c in cols))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("report", help="report letter, e.g. A, B, C, D, E, F")
    ap.add_argument(
        "--run", action="store_true", help="execute against DATABASE_URL instead of printing"
    )
    args = ap.parse_args(argv)
    sql = statement(args.report.upper())
    if args.run:
        asyncio.run(_run(sql))
    else:
        sys.stdout.write(sql + ";\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
