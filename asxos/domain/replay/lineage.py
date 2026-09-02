"""Resolve every canonical row a replay used back to its raw source rows.

Stage 1 exit clause (2): "raw-to-canonical lineage resolves exactly". For the
two canonical facts a replay snapshot carries:

* `rs_fundamentals_pit(symbol, knowledge_date)` was derived by
  `asxos.ingestion.fundamentals_pit` from the yearly `rs_financial_statements`
  rows for `(symbol, period_end = as_of)` — `income` is required, `balance_sheet`
  is optional but expected. Lineage is resolved when the income row exists; a
  missing balance sheet is reported as a partial resolution, never hidden.

* `prices(symbol, dt)` is its own raw row today (the provider payload archive
  is Stage 1 work order F6, not yet built), so it resolves to itself plus every
  `price_revisions` ledger row that touched it. That is an honest "resolves to
  the projection" rather than a claim of provider-level provenance; the report
  says so in `provenance_ceiling`.

Nothing is inferred. A row either has a source row with a matching key or it
is listed under `unresolved`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Final

from asxos.domain.replay.cutoff import (
    FetchConn,
    ReplayError,
    ReplaySnapshot,
    assert_replay_sql_admissible,
)

SQL_STATEMENT_KEYS: Final[str] = (
    "SELECT symbol, period_end, period_type, statement_type, filing_date, report_date "
    "FROM rs_financial_statements "
    "WHERE symbol = $1 AND period_end = $2 AND period_type = 'yearly' "
    "ORDER BY statement_type"
)
SQL_PRICE_KEY: Final[str] = "SELECT symbol, dt FROM prices WHERE symbol = $1 AND dt = $2"
SQL_REVISION_IDS: Final[str] = (
    "SELECT revision_id FROM price_revisions "
    "WHERE prior_symbol = $1 AND prior_dt = $2 ORDER BY revision_id"
)

_LINEAGE_TABLES: Final[frozenset[str]] = frozenset(
    {"rs_financial_statements", "prices", "price_revisions"}
)


def _assert_lineage_sql(sql: str) -> None:
    # Same forbidden-token discipline as the replay; a wider admissible set
    # because lineage reads the raw statements table the replay never does.
    lowered = sql.lower()
    tables = {
        word.strip(",;")
        for prev, word in zip(lowered.split(), lowered.split()[1:], strict=False)
        if prev in {"from", "join"}
    }
    if not tables <= _LINEAGE_TABLES:
        raise ReplayError(f"lineage SQL touches non-admissible table(s): {sorted(tables)}")
    assert_replay_sql_admissible(sql.replace("rs_financial_statements", "prices"))


for _sql in (SQL_STATEMENT_KEYS, SQL_PRICE_KEY, SQL_REVISION_IDS):
    _assert_lineage_sql(_sql)


@dataclass(frozen=True)
class LineageReport:
    resolved: list[dict[str, object]] = field(default_factory=list)
    unresolved: list[dict[str, object]] = field(default_factory=list)
    provenance_ceiling: str = (
        "prices resolves to the serving projection plus its revision ledger; "
        "provider payload lineage awaits Stage 1 work order F6 (raw object store)"
    )

    @property
    def complete(self) -> bool:
        return not self.unresolved

    def as_payload(self) -> dict[str, object]:
        return {
            "complete": self.complete,
            "resolved": self.resolved,
            "unresolved": self.unresolved,
            "provenance_ceiling": self.provenance_ceiling,
        }


async def resolve_lineage(conn: FetchConn, snapshot: ReplaySnapshot) -> LineageReport:
    payload = snapshot.payload
    symbol = str(payload["symbol"])
    resolved: list[dict[str, object]] = []
    unresolved: list[dict[str, object]] = []

    # --- fundamentals → statements ----------------------------------------
    fundamentals = payload["fundamentals"]
    row = fundamentals["row"]  # type: ignore[index]
    if row is not None:
        as_of = date.fromisoformat(str(row["as_of"]))
        statements = await conn.fetch(SQL_STATEMENT_KEYS, symbol, as_of)
        kinds = {str(s["statement_type"]) for s in statements}  # type: ignore[index]
        entry: dict[str, object] = {
            "canonical": f"rs_fundamentals_pit({symbol}, {row['knowledge_date']})",
            "derived_by": "asxos.ingestion.fundamentals_pit.compute_pit_factors",
            "source_rows": [
                f"rs_financial_statements({symbol}, {as_of.isoformat()}, yearly, {kind})"
                for kind in sorted(kinds)
            ],
        }
        if "income" in kinds:
            if "balance_sheet" not in kinds:
                entry["note"] = "balance_sheet absent — ratios needing equity/assets were NULL"
            resolved.append(entry)
        else:
            entry["reason"] = "no yearly income statement for the row's as_of"
            unresolved.append(entry)

    # --- price → its own row + ledger --------------------------------------
    price = payload["price"]
    prow = price["row"]  # type: ignore[index]
    if prow is not None:
        dt = date.fromisoformat(str(prow["dt"]))
        key = await conn.fetchrow(SQL_PRICE_KEY, symbol, dt)
        revision_ids = [
            int(r["revision_id"]) for r in await conn.fetch(SQL_REVISION_IDS, symbol, dt)  # type: ignore[index]
        ]
        entry = {
            "canonical": f"prices({symbol}, {dt.isoformat()})",
            "source_rows": [f"prices({symbol}, {dt.isoformat()})"]
            + [f"price_revisions.revision_id={rid}" for rid in revision_ids],
        }
        if key is None:
            entry["reason"] = "price row vanished between snapshot and lineage"
            unresolved.append(entry)
        else:
            resolved.append(entry)

    return LineageReport(resolved=resolved, unresolved=unresolved)
