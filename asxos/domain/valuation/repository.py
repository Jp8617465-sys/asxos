"""Persistence for the valuation store — migration 0054, applied 2026-09-14.

Same rules as `decision_engine/repository.py`: `payload JSONB` is the sole
authoritative column (reconstruction is `Model.model_validate(payload)`); every
other column is a NON-AUTHORITATIVE shadow for indexing; both tables are
append-only by trigger, so the only idempotent write is
`INSERT ... ON CONFLICT DO NOTHING`. A same-day re-run therefore keeps the
first run's rows and reports zero written — recorded, not hidden.
"""
from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from datetime import date
from typing import Any, Final, Protocol

from asxos.domain.valuation.contracts import ScenarioPreregistration, ValuationRun
from asxos.domain.valuation.inputs import assert_valuation_sql_admissible
from asxos.domain.valuation.universe import SQL_RESIDUAL_INCOME_ELIGIBLE

DEFAULT_WRITE_BATCH_SIZE: Final[int] = 200


class RepositoryConn(Protocol):
    async def execute(self, query: str, *args: object) -> str: ...

    async def fetch(self, query: str, *args: object) -> list[Any]: ...

    async def fetchrow(self, query: str, *args: object) -> Mapping[str, object] | None: ...

    def transaction(self) -> Any: ...


class PreregistrationDriftError(RuntimeError):
    """The stored registration for this id was sealed with a different hash."""


SQL_PREREG_BY_ID: Final[str] = (
    "SELECT content_hash FROM valuation_scenario_preregistrations WHERE preregistration_id = $1"
)
SQL_INSERT_PREREG: Final[str] = """
INSERT INTO valuation_scenario_preregistrations
    (preregistration_id, content_hash, registered_by, registered_at, applies_to, payload)
VALUES ($1, $2, $3, $4, $5, $6::jsonb)
ON CONFLICT (preregistration_id) DO NOTHING
"""
SQL_INSERT_RUN: Final[str] = """
INSERT INTO valuation_runs
    (run_id, content_hash, symbol, as_of, knowledge_cutoff, created_at, method,
     terminal_convention, franking_convention, outcome, value_per_share, data_mode,
     preregistration_id, payload)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14::jsonb)
ON CONFLICT (run_id) DO NOTHING
"""
SQL_COUNT_RUNS_FOR_AS_OF: Final[str] = (
    "SELECT count(*) AS n, count(*) FILTER (WHERE outcome = 'valued') AS valued "
    "FROM valuation_runs WHERE as_of = $1"
)
SQL_LATEST_RUNS: Final[str] = f"""
SELECT DISTINCT ON (v.symbol) v.payload
FROM valuation_runs v
JOIN universe u ON u.symbol = v.symbol
WHERE v.as_of <= $1 AND v.terminal_convention = $2
  AND v.method = 'residual_income'
  AND {SQL_RESIDUAL_INCOME_ELIGIBLE}
ORDER BY v.symbol, v.as_of DESC, v.created_at DESC
"""
for _sql in (SQL_PREREG_BY_ID, SQL_INSERT_PREREG, SQL_INSERT_RUN, SQL_COUNT_RUNS_FOR_AS_OF, SQL_LATEST_RUNS):
    assert_valuation_sql_admissible(_sql)


def _dump(model: ScenarioPreregistration | ValuationRun) -> str:
    return json.dumps(model.model_dump(mode="json"))


def _payload(row: Mapping[str, object]) -> dict[str, object]:
    raw = row["payload"]
    if isinstance(raw, str):
        return dict(json.loads(raw))
    if isinstance(raw, Mapping):
        return dict(raw)
    raise TypeError(f"unexpected payload column type: {type(raw)!r}")


def _inserted(status: str) -> int:
    """`INSERT 0 1` → 1; `INSERT 0 0` (conflict, kept the stored row) → 0."""
    try:
        return int(status.split()[-1])
    except (ValueError, IndexError) as exc:
        raise RuntimeError(f"unexpected INSERT status tag: {status!r}") from exc


async def ensure_preregistered(conn: RepositoryConn, prereg: ScenarioPreregistration) -> bool:
    """Register once; refuse loudly if the stored row was sealed differently.

    Returns True when this call inserted the row, False when it already existed
    with the same hash.
    """
    existing = await conn.fetchrow(SQL_PREREG_BY_ID, prereg.preregistration_id)
    if existing is not None:
        stored = str(existing["content_hash"])
        if stored != prereg.content_hash:
            raise PreregistrationDriftError(
                f"preregistration {prereg.preregistration_id!r} is stored with hash "
                f"{stored[:12]}… but the bundled file hashes {prereg.content_hash[:12]}…; "
                "a changed registration is a NEW id, never an edit"
            )
        return False
    status = await conn.execute(
        SQL_INSERT_PREREG,
        prereg.preregistration_id,
        prereg.content_hash,
        prereg.registered_by,
        prereg.registered_at,
        prereg.applies_to,
        _dump(prereg),
    )
    return _inserted(status) == 1


async def save_runs(
    conn: RepositoryConn,
    runs: list[ValuationRun],
    *,
    batch_size: int = DEFAULT_WRITE_BATCH_SIZE,
    on_rows_committed: Callable[[int], None] | None = None,
) -> int:
    """Insert in bounded transactions; return the number of rows actually written."""
    if batch_size < 1:
        raise ValueError("batch_size must be >= 1")
    written = 0
    for start in range(0, len(runs), batch_size):
        batch = runs[start : start + batch_size]
        async with conn.transaction():
            for run in batch:
                status = await conn.execute(
                    SQL_INSERT_RUN,
                    run.run_id,
                    run.content_hash,
                    run.symbol,
                    run.as_of,
                    run.knowledge_cutoff,
                    run.created_at,
                    run.method,
                    run.terminal_convention,
                    run.franking_convention,
                    run.outcome,
                    run.value_per_share,
                    run.data_mode,
                    run.preregistration_id,
                    _dump(run),
                )
                written += _inserted(status)
        if on_rows_committed is not None:
            on_rows_committed(written)
    return written


async def count_runs_for(conn: RepositoryConn, as_of: date) -> tuple[int, int]:
    """(rows, valued rows) already stored for an as_of — the same-day re-run signal."""
    row = await conn.fetchrow(SQL_COUNT_RUNS_FOR_AS_OF, as_of)
    if row is None:
        return 0, 0
    return int(str(row["n"])), int(str(row["valued"]))


async def latest_runs(
    conn: RepositoryConn, *, as_of: date, terminal_convention: str = "zero_excess"
) -> list[ValuationRun]:
    """The most recent *applicable* run per symbol at or before `as_of`.

    Applicability is current sweep eligibility (`SQL_RESIDUAL_INCOME_ELIGIBLE`)
    plus `method = residual_income`. A stored row for a kind the method no
    longer applies to — the 2026-09-16 LIC valued runs after A-49 — is not
    returned. The store stays append-only; the reader stops treating an
    inapplicable run as current. Reconstructed from payload.
    """
    records = await conn.fetch(SQL_LATEST_RUNS, as_of, terminal_convention)
    return [ValuationRun.model_validate(_payload(r)) for r in records]


SQL_LATEST_RUN_FOR_SYMBOL: Final[str] = f"""
SELECT v.payload
FROM valuation_runs v
JOIN universe u ON u.symbol = v.symbol
WHERE v.symbol = $1 AND v.as_of <= $2 AND v.terminal_convention = $3
  AND v.method = 'residual_income'
  AND {SQL_RESIDUAL_INCOME_ELIGIBLE}
ORDER BY v.as_of DESC, v.created_at DESC
LIMIT 1
"""
assert_valuation_sql_admissible(SQL_LATEST_RUN_FOR_SYMBOL)


async def latest_run_for_symbol(
    conn: RepositoryConn, *, symbol: str, as_of: date, terminal_convention: str = "zero_excess"
) -> ValuationRun | None:
    """The most recent applicable run for one name — the decision builder's read (S2/S5).

    Same eligibility as `latest_runs`. An excluded symbol (LIC, ETF, inactive)
    returns None even when a residual-income row still sits in the store.
    """
    row = await conn.fetchrow(SQL_LATEST_RUN_FOR_SYMBOL, symbol, as_of, terminal_convention)
    return None if row is None else ValuationRun.model_validate(_payload(row))
