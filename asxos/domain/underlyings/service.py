"""
Underlyings domain service — M-Underlyings.

Functions:
  seed_defaults(conn)                       — upsert standard underlying catalog
  get_underlying(conn, code)                — fetch by code
  list_underlyings(conn)                    — all active underlyings
  upsert_price(conn, code, as_of, spot)     — idempotent daily price write
  attach_underlying(conn, thesis_id, ...)   — add/update thesis_underlyings row
  list_thesis_underlyings(conn, thesis_id)  — fetch all rows for a thesis
  get_5d_moves(conn, underlying_ids, as_of) — compute 5d % change per underlying
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from asxos.domain.underlyings.types import (
    ThesisUnderlying,
    Underlying,
    UnderlyingCategory,
    UnderlyingDirection,
)

# ---------------------------------------------------------------------------
# Default underlying catalog — seeded once on first deploy
# ---------------------------------------------------------------------------

_DEFAULTS: list[dict[str, Any]] = [
    {"code": "iron_ore_62fe", "name": "Iron Ore 62% Fe CFR China", "category": "commodity_resources", "unit": "USD/t", "data_source": "eodhd:IRON.COMM"},
    {"code": "copper", "name": "Copper Grade A LME", "category": "commodity_resources", "unit": "USD/t", "data_source": "eodhd:COPPER.COMM"},
    {"code": "lithium_carbonate", "name": "Lithium Carbonate 99.5% China", "category": "commodity_resources", "unit": "CNY/t", "data_source": "manual"},
    {"code": "brent_crude", "name": "Brent Crude Oil", "category": "commodity_energy", "unit": "USD/bbl", "data_source": "eodhd:BRENT.COMM"},
    {"code": "nat_gas", "name": "Natural Gas Henry Hub", "category": "commodity_energy", "unit": "USD/MMBtu", "data_source": "eodhd:NG.COMM"},
    {"code": "aud_usd", "name": "AUD/USD Exchange Rate", "category": "currency", "unit": "AUD/USD", "data_source": "eodhd:AUDUSD.FOREX"},
    {"code": "aud_cny", "name": "AUD/CNY Exchange Rate", "category": "currency", "unit": "AUD/CNY", "data_source": "eodhd:AUDCNY.FOREX"},
    {"code": "rba_cash_rate", "name": "RBA Cash Rate Target", "category": "rate", "unit": "%", "data_source": "fred:AUCBCNTO"},
    {"code": "aus_10y_yield", "name": "Australia 10Y Government Bond Yield", "category": "rate", "unit": "%", "data_source": "fred:IRLTLT01AUM156N"},
    {"code": "us_hy_oas", "name": "US High-Yield OAS (FRED BAMLH0A0HYM2)", "category": "rate", "unit": "%", "data_source": "fred:BAMLH0A0HYM2"},  # FRED publishes this in percent; "bps" was the label that made the v1.0 classifier defect look intended
    {"code": "xjo", "name": "ASX 200 Index", "category": "index", "unit": "points", "data_source": "eodhd:AXJO.INDX"},
]


async def seed_defaults(conn: Any) -> int:
    """Upsert the standard underlying catalog. Returns count of rows upserted."""
    rows_written = 0
    for d in _DEFAULTS:
        await conn.execute(
            """
            INSERT INTO underlyings (code, name, category, unit, data_source)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (code) DO UPDATE SET
                name        = EXCLUDED.name,
                category    = EXCLUDED.category,
                unit        = EXCLUDED.unit,
                data_source = EXCLUDED.data_source
            """,
            d["code"], d["name"], d["category"], d["unit"], d["data_source"],
        )
        rows_written += 1
    return rows_written


def _row_to_underlying(row: Any) -> Underlying:
    return Underlying(
        underlying_id=row["underlying_id"],
        code=row["code"],
        name=row["name"],
        category=UnderlyingCategory(row["category"]),
        unit=row["unit"],
        data_source=row["data_source"],
        is_active=row["is_active"],
        created_at=row["created_at"],
    )


async def get_underlying(conn: Any, code: str) -> Underlying | None:
    row = await conn.fetchrow(
        "SELECT * FROM underlyings WHERE code = $1", code
    )
    return _row_to_underlying(row) if row else None


async def list_underlyings(conn: Any, *, include_inactive: bool = False) -> list[Underlying]:
    if include_inactive:
        rows = await conn.fetch("SELECT * FROM underlyings ORDER BY category, code")
    else:
        rows = await conn.fetch("SELECT * FROM underlyings WHERE is_active ORDER BY category, code")
    return [_row_to_underlying(r) for r in rows]


async def upsert_price(
    conn: Any,
    code: str,
    as_of: date,
    spot: Decimal,
) -> None:
    """Idempotent daily price write. Raises RuntimeError if code not found."""
    underlying_id = await conn.fetchval(
        "SELECT underlying_id FROM underlyings WHERE code = $1", code
    )
    if underlying_id is None:
        raise RuntimeError(f"upsert_price: underlying '{code}' not found in catalog")
    await conn.execute(
        """
        INSERT INTO underlying_prices (underlying_id, as_of, spot)
        VALUES ($1, $2, $3)
        ON CONFLICT (underlying_id, as_of) DO UPDATE SET spot = EXCLUDED.spot
        """,
        underlying_id, as_of, spot,
    )


async def attach_underlying(
    conn: Any,
    thesis_id: int,
    underlying_code: str,
    exposure: Decimal,
    direction: str,
) -> None:
    """Attach or update an underlying on a thesis.

    Hard-fails with ValueError if:
      - underlying_code not found
      - exposure outside [0, 1]
      - adding this row would push total exposure sum > 1.0

    The DB enforces the per-row [0,1] CHECK; the sum check is application-level.
    """
    if not (Decimal("0") <= exposure <= Decimal("1")):
        raise ValueError(
            f"attach_underlying: exposure must be in [0, 1], got {exposure}"
        )
    if direction not in ("positive", "negative"):
        raise ValueError(
            f"attach_underlying: direction must be 'positive' or 'negative', got {direction!r}"
        )

    underlying_id = await conn.fetchval(
        "SELECT underlying_id FROM underlyings WHERE code = $1 AND is_active",
        underlying_code,
    )
    if underlying_id is None:
        raise RuntimeError(
            f"attach_underlying: underlying '{underlying_code}' not found or inactive"
        )

    # Check that the new total exposure won't exceed 1.0
    existing_sum = await conn.fetchval(
        """
        SELECT COALESCE(SUM(exposure), 0)
        FROM thesis_underlyings
        WHERE thesis_id = $1 AND underlying_id != $2
        """,
        thesis_id, underlying_id,
    )
    new_total = Decimal(str(existing_sum)) + exposure
    if new_total > Decimal("1"):
        raise ValueError(
            f"attach_underlying: total exposure would be {new_total} (max 1.0). "
            f"Reduce exposure or remove another underlying first."
        )

    await conn.execute(
        """
        INSERT INTO thesis_underlyings (thesis_id, underlying_id, exposure, direction)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (thesis_id, underlying_id) DO UPDATE SET
            exposure  = EXCLUDED.exposure,
            direction = EXCLUDED.direction,
            last_validated_at = CURRENT_DATE
        """,
        thesis_id, underlying_id, exposure, direction,
    )


async def list_thesis_underlyings(conn: Any, thesis_id: int) -> list[ThesisUnderlying]:
    rows = await conn.fetch(
        """
        SELECT tu.thesis_id, tu.underlying_id, u.code, tu.exposure,
               tu.direction, tu.last_validated_at
        FROM thesis_underlyings tu
        JOIN underlyings u ON u.underlying_id = tu.underlying_id
        WHERE tu.thesis_id = $1
        ORDER BY u.code
        """,
        thesis_id,
    )
    return [
        ThesisUnderlying(
            thesis_id=r["thesis_id"],
            underlying_id=r["underlying_id"],
            code=r["code"],
            exposure=Decimal(str(r["exposure"])),
            direction=UnderlyingDirection(r["direction"]),
            last_validated_at=r["last_validated_at"],
        )
        for r in rows
    ]


async def bulk_list_thesis_underlyings(
    conn: Any,
    thesis_ids: list[int],
) -> dict[int, list[ThesisUnderlying]]:
    """Batch-load thesis_underlyings for multiple theses in one query.

    Returns {thesis_id: [ThesisUnderlying, ...]}. Theses with no underlyings
    are absent from the dict (not an empty list entry).
    """
    if not thesis_ids:
        return {}
    rows = await conn.fetch(
        """
        SELECT tu.thesis_id, tu.underlying_id, u.code, tu.exposure,
               tu.direction, tu.last_validated_at
        FROM thesis_underlyings tu
        JOIN underlyings u ON u.underlying_id = tu.underlying_id
        WHERE tu.thesis_id = ANY($1)
        ORDER BY tu.thesis_id, u.code
        """,
        thesis_ids,
    )
    result: dict[int, list[ThesisUnderlying]] = {}
    for r in rows:
        thesis_id = r["thesis_id"]
        if thesis_id not in result:
            result[thesis_id] = []
        result[thesis_id].append(ThesisUnderlying(
            thesis_id=r["thesis_id"],
            underlying_id=r["underlying_id"],
            code=r["code"],
            exposure=Decimal(str(r["exposure"])),
            direction=UnderlyingDirection(r["direction"]),
            last_validated_at=r["last_validated_at"],
        ))
    return result


async def get_5d_moves(
    conn: Any,
    underlying_ids: list[int],
    as_of: date,
) -> dict[int, Decimal | None]:
    """Compute 5-trading-day percentage change for each underlying_id.

    Returns {underlying_id: pct_change | None}.
    None means insufficient price history.
    """
    if not underlying_ids:
        return {}

    rows = await conn.fetch(
        """
        WITH recent AS (
            SELECT underlying_id,
                   spot,
                   ROW_NUMBER() OVER (PARTITION BY underlying_id ORDER BY as_of DESC) AS rn
            FROM underlying_prices
            WHERE underlying_id = ANY($1)
              AND as_of <= $2
        )
        SELECT underlying_id,
               MAX(CASE WHEN rn = 1 THEN spot END) AS latest,
               MAX(CASE WHEN rn = 6 THEN spot END) AS prior_5d
        FROM recent
        WHERE rn <= 6
        GROUP BY underlying_id
        HAVING COUNT(*) >= 2
        """,
        underlying_ids, as_of,
    )
    result: dict[int, Decimal | None] = dict.fromkeys(underlying_ids)
    for r in rows:
        latest = Decimal(str(r["latest"])) if r["latest"] is not None else None
        prior = Decimal(str(r["prior_5d"])) if r["prior_5d"] is not None else None
        if latest is not None and prior is not None and prior != Decimal("0"):
            result[r["underlying_id"]] = ((latest - prior) / prior * 100).quantize(Decimal("0.01"))
    return result
