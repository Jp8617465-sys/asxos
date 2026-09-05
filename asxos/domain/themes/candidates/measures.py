"""Deterministic measures from bound SQL. No LLM, no float, no signals.

Theme measures: membership, breadth of members above their 50/200-session
means at the cutoff (the same inputs `stage_classifier.ClassifierInput`
consumes), and the conditioning macro thesis if any.

Candidate measures: sector and factor z-scores from the latest
`rs_factor_scores` cross-section knowable at the cutoff, 60-session median
dollar volume, and price freshness. Every figure is a decimal string.
"""
from __future__ import annotations

import re
from datetime import date
from decimal import ROUND_HALF_EVEN, Decimal
from itertools import pairwise
from typing import Any, Final, Protocol

Q6: Final = Decimal("0.000001")
# Column-level leaks of Model A output (rule #11). Table-level access is fenced
# separately by the `_ADMISSIBLE` FROM/JOIN allowlist below, which is why
# `macro_thesis_id` (a column on `themes`) is not a forbidden token.
_FORBIDDEN: Final[tuple[str, ...]] = (
    r"\bsignals\b", r"\bshap_", r"\bprob_up\b", r"\bsignal_label\b", r"\bmodel_a\b",
    r"\bexpected_return\b", r"\bsignal_outcomes\b",
)
_ADMISSIBLE: Final[frozenset[str]] = frozenset(
    {"themes", "theme_holdings", "macro_theses", "rs_factor_scores", "rs_security_master", "prices"}
)

SQL_THEME: Final[str] = (
    "SELECT theme_id, theme_code, name, description, conviction_band, stage, "
    "macro_thesis_id, governance_status, retired_at "
    "FROM themes WHERE theme_code = $1"
)
SQL_MEMBERS: Final[str] = (
    "SELECT symbol, exposure_strength, direction, mechanism_text "
    "FROM theme_holdings WHERE theme_id = $1 ORDER BY symbol"
)
SQL_MACRO: Final[str] = (
    "SELECT macro_thesis_id, title, regime_quadrant, governance_status "
    "FROM macro_theses WHERE macro_thesis_id = $1"
)
SQL_FACTORS: Final[str] = (
    "SELECT symbol, as_of, sector, market_cap_aud, value_score, quality_score, "
    "momentum_score, low_vol_score, yield_score, composite_score, n_factors_present "
    "FROM rs_factor_scores WHERE symbol = $1 AND as_of <= $2 "
    "ORDER BY as_of DESC LIMIT 1"
)
SQL_SECTOR: Final[str] = "SELECT symbol, gics_sector FROM rs_security_master WHERE symbol = $1"
SQL_PRICES: Final[str] = (
    "SELECT dt, close, volume FROM prices "
    "WHERE symbol = $1 AND dt <= $2 ORDER BY dt DESC LIMIT $3"
)


class FetchConn(Protocol):
    async def fetchrow(self, sql: str, *args: object) -> Any: ...
    async def fetch(self, sql: str, *args: object) -> list[Any]: ...


class MeasureError(RuntimeError):
    """A measure could not be computed honestly. Reported, never guessed."""


def assert_measure_sql_admissible(sql: str) -> None:
    lowered = sql.lower()
    for token in _FORBIDDEN:
        if re.search(token, lowered):
            raise MeasureError(f"forbidden token {token!r} in measure SQL")
    words = lowered.split()
    tables = {w.strip(",;") for prev, w in pairwise(words) if prev in {"from", "join"}}
    if not tables <= _ADMISSIBLE:
        raise MeasureError(f"measure SQL touches non-admissible table(s): {sorted(tables)}")


for _sql in (SQL_THEME, SQL_MEMBERS, SQL_MACRO, SQL_FACTORS, SQL_SECTOR, SQL_PRICES):
    assert_measure_sql_admissible(_sql)


def q(value: Decimal) -> str:
    return format(value.quantize(Q6, rounding=ROUND_HALF_EVEN), "f")


def _q_opt(value: Decimal | None) -> str | None:
    return q(value) if value is not None else None


def _dec(value: object) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, float):
        raise MeasureError("float reached the measures — every figure must be Decimal")
    return Decimal(str(value))


async def price_window(conn: FetchConn, symbol: str, as_of: date, sessions: int) -> list[dict[str, Any]]:
    rows = await conn.fetch(SQL_PRICES, symbol, as_of, sessions)
    return sorted(rows, key=lambda r: r["dt"])


def breadth_flags(closes: list[Decimal]) -> tuple[bool | None, bool | None]:
    """(above 50-session mean, above 200-session mean) for an ascending close series."""
    if not closes:
        return None, None
    last = closes[-1]
    above50 = last > sum(closes[-50:], Decimal(0)) / Decimal(len(closes[-50:])) if len(closes) >= 50 else None
    above200 = last > sum(closes[-200:], Decimal(0)) / Decimal(len(closes[-200:])) if len(closes) >= 200 else None
    return above50, above200


async def theme_breadth(conn: FetchConn, members: list[str], as_of: date) -> dict[str, str | int | None]:
    """Fraction of members above their 50/200-session means. None when unknowable."""
    n50 = n200 = a50 = a200 = 0
    for sym in members:
        rows = await price_window(conn, sym, as_of, 200)
        closes = [c for c in (_dec(r["close"]) for r in rows) if c is not None]
        f50, f200 = breadth_flags(closes)
        if f50 is not None:
            n50 += 1
            a50 += int(f50)
        if f200 is not None:
            n200 += 1
            a200 += int(f200)
    return {
        "members": len(members),
        "members_with_50d_history": n50,
        "members_with_200d_history": n200,
        "pct_above_50d_ma": q(Decimal(a50) / Decimal(n50)) if n50 else None,
        "pct_above_200d_ma": q(Decimal(a200) / Decimal(n200)) if n200 else None,
    }


async def candidate_measures(conn: FetchConn, symbol: str, as_of: date) -> dict[str, str | int | None]:
    sector_row = await conn.fetchrow(SQL_SECTOR, symbol)
    factors = await conn.fetchrow(SQL_FACTORS, symbol, as_of)
    rows = await price_window(conn, symbol, as_of, 60)
    dollar = sorted(
        c * v for c, v in ((_dec(r["close"]), _dec(r["volume"])) for r in rows) if c is not None and v is not None
    )
    median = None
    if dollar:
        mid = len(dollar) // 2
        median = dollar[mid] if len(dollar) % 2 else (dollar[mid - 1] + dollar[mid]) / Decimal(2)
    last_dt = rows[-1]["dt"] if rows else None
    out: dict[str, str | int | None] = {
        "gics_sector": (sector_row["gics_sector"] if sector_row else None),
        "factor_as_of": factors["as_of"].isoformat() if factors else None,
        "factor_sector": factors["sector"] if factors else None,
        "market_cap_aud": _q_opt(_dec(factors["market_cap_aud"])) if factors else None,
        "n_factors_present": int(factors["n_factors_present"]) if factors else None,
        "price_sessions_in_window": len(rows),
        "last_price_dt": last_dt.isoformat() if last_dt else None,
        "last_close": q(_dec(rows[-1]["close"])) if rows and rows[-1]["close"] is not None else None,  # type: ignore[arg-type]
        "median_dollar_volume_60d": q(median) if median is not None else None,
    }
    for col in ("value_score", "quality_score", "momentum_score", "low_vol_score", "yield_score", "composite_score"):
        val = _dec(factors[col]) if factors else None
        out[f"factor_{col}"] = q(val) if val is not None else None
    return out
