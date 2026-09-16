"""Every read the universe sweep makes — bound parameters, screened at import.

Mirrors the `base` CTE of `scripts/research/baseline_inquiry.sql` (the S1
acceptance test) so the persisted runs reproduce REPORT B: the latest usable
point-in-time row per symbol, the mean ROE of its latest three periods, the
last close inside a bounded window, and the two market inputs (risk-free,
AUDUSD). Rule #11: the statements below name no Model A surface, and
`assert_valuation_sql_admissible` proves it at import.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Final, Protocol

from asxos.domain.valuation.inputs import assert_valuation_sql_admissible
from asxos.domain.valuation.numeric import dec

#: The last close must fall inside this many calendar days before the cutoff
#: date. Bounds the `prices` scan (the unbounded DISTINCT ON of the baseline SQL
#: walks the whole table) and refuses to value a suspended name at a stale
#: print — pre-registered as `input_rules.price_window_days`.
PRICE_WINDOW_DAYS: Final[int] = 40

#: Statement timeout for the bulk universe read: the pool's default 30 s
#: `command_timeout` is sized for row lookups, not a 1,880-name sweep.
UNIVERSE_QUERY_TIMEOUT_S: Final[float] = 300.0

SQL_UNIVERSE_INPUTS: Final[str] = """
WITH pit AS (
    SELECT DISTINCT ON (symbol)
           symbol, as_of, knowledge_date, book_value_ps, roe, eps_ttm, dividend_ttm,
           franking_avg_pct, currency
    FROM rs_fundamentals_pit
    WHERE knowledge_date <= $1
    ORDER BY symbol, as_of DESC, knowledge_date DESC
),
pit_avg AS (
    SELECT symbol, avg(roe) AS roe_average, count(*) AS roe_periods
    FROM (
        SELECT symbol, roe,
               row_number() OVER (PARTITION BY symbol ORDER BY as_of DESC, knowledge_date DESC) AS rn
        FROM rs_fundamentals_pit
        WHERE knowledge_date <= $1 AND roe IS NOT NULL
    ) ranked
    WHERE rn <= $3
    GROUP BY symbol
),
px AS (
    SELECT DISTINCT ON (symbol) symbol, dt, close
    FROM prices
    WHERE dt <= $1 AND dt >= $2
    ORDER BY symbol, dt DESC
)
SELECT u.symbol,
       pit.as_of            AS pit_as_of,
       pit.knowledge_date   AS pit_knowledge_date,
       pit.book_value_ps,
       pit.roe,
       pit.eps_ttm,
       pit.dividend_ttm,
       pit.franking_avg_pct,
       pit.currency,
       pit_avg.roe_average,
       pit_avg.roe_periods,
       px.dt                AS last_close_dt,
       px.close             AS last_close
FROM universe u
LEFT JOIN pit     ON pit.symbol = u.symbol
LEFT JOIN pit_avg ON pit_avg.symbol = u.symbol
LEFT JOIN px      ON px.symbol = u.symbol
WHERE u.security_kind = 'au_equity' AND u.is_active
ORDER BY u.symbol
"""

SQL_RISK_FREE_LATEST: Final[str] = (
    "SELECT as_of, aus_10y_yield FROM market_context_current "
    "WHERE aus_10y_yield IS NOT NULL AND as_of <= $1 ORDER BY as_of DESC LIMIT 1"
)
SQL_AUDUSD_LATEST: Final[str] = (
    "SELECT dt, rate FROM fx_rates WHERE pair = 'AUDUSD' AND dt <= $1 ORDER BY dt DESC LIMIT 1"
)

for _sql in (SQL_UNIVERSE_INPUTS, SQL_RISK_FREE_LATEST, SQL_AUDUSD_LATEST):
    assert_valuation_sql_admissible(_sql)


class Conn(Protocol):
    """The asyncpg surface the sweep reads through (`fetch` takes a per-call timeout)."""

    async def fetch(self, query: str, *args: object, timeout: float | None = None) -> list[Any]: ...

    async def fetchrow(self, query: str, *args: object) -> Any: ...


@dataclass(frozen=True)
class UniverseRow:
    """One active ASX equity as the sweep read it. Absent inputs stay None."""

    symbol: str
    pit_as_of: date | None
    pit_knowledge_date: date | None
    book_value_ps: Decimal | None
    roe: Decimal | None
    eps_ttm: Decimal | None
    dividend_ttm: Decimal | None
    franking_avg_pct: Decimal | None
    currency: str | None
    roe_average: Decimal | None
    roe_periods: int
    last_close_dt: date | None
    last_close: Decimal | None


@dataclass(frozen=True)
class MarketInputs:
    """The two universe-wide inputs. Either absent hard-fails the run (CLAUDE.md #10)."""

    risk_free: Decimal
    risk_free_as_of: date
    audusd: Decimal
    audusd_as_of: date


def _opt_dec(value: object) -> Decimal | None:
    return None if value is None else dec(value)


def row_from_record(record: Any) -> UniverseRow:
    return UniverseRow(
        symbol=str(record["symbol"]),
        pit_as_of=record["pit_as_of"],
        pit_knowledge_date=record["pit_knowledge_date"],
        book_value_ps=_opt_dec(record["book_value_ps"]),
        roe=_opt_dec(record["roe"]),
        eps_ttm=_opt_dec(record["eps_ttm"]),
        dividend_ttm=_opt_dec(record["dividend_ttm"]),
        franking_avg_pct=_opt_dec(record["franking_avg_pct"]),
        currency=record["currency"],
        roe_average=_opt_dec(record["roe_average"]),
        roe_periods=int(record["roe_periods"] or 0),
        last_close_dt=record["last_close_dt"],
        last_close=_opt_dec(record["last_close"]),
    )


async def load_universe_rows(
    conn: Conn, *, cutoff_date: date, roe_average_periods: int
) -> list[UniverseRow]:
    """Every active ASX equity with whatever inputs exist at the cutoff date."""
    window_start = cutoff_date - timedelta(days=PRICE_WINDOW_DAYS)
    records = await conn.fetch(
        SQL_UNIVERSE_INPUTS,
        cutoff_date,
        window_start,
        roe_average_periods,
        timeout=UNIVERSE_QUERY_TIMEOUT_S,
    )
    rows = [row_from_record(r) for r in records]
    if not rows:
        raise RuntimeError(
            "universe sweep read zero active au_equity rows — the universe table is "
            "empty or security_kind is unset; refusing to record a blank run"
        )
    return rows


async def load_market_inputs(conn: Conn, *, cutoff_date: date) -> MarketInputs:
    rf = await conn.fetchrow(SQL_RISK_FREE_LATEST, cutoff_date)
    if rf is None:
        raise RuntimeError(
            "no risk-free rate: market_context_current.aus_10y_yield is empty at or before "
            f"{cutoff_date} — run ingest_market_context before the valuation sweep"
        )
    fx = await conn.fetchrow(SQL_AUDUSD_LATEST, cutoff_date)
    if fx is None:
        raise RuntimeError(
            f"no AUDUSD rate in fx_rates at or before {cutoff_date} — USD reporters cannot be "
            "converted; run sync_prices (FX phase) before the valuation sweep"
        )
    return MarketInputs(
        risk_free=dec(rf["aus_10y_yield"]) / Decimal("100"),
        risk_free_as_of=rf["as_of"],
        audusd=dec(fx["rate"]),
        audusd_as_of=fx["dt"],
    )
