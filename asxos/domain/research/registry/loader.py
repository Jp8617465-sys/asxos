"""Load the raw price panel the harness evaluates. SELECT-only, bound values."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Final, Protocol

SQL_PANEL: Final[str] = (
    "SELECT p.symbol, p.dt, p.adj_close "
    "FROM prices p "
    "JOIN universe u ON u.symbol = p.symbol "
    "WHERE u.is_active AND p.symbol LIKE '%.AU' AND p.dt <= $1 AND p.adj_close IS NOT NULL "
    "ORDER BY p.symbol, p.dt"
)
_ADMISSIBLE: Final[frozenset[str]] = frozenset({"prices", "universe", "prices p", "universe u"})


class FetchConn(Protocol):
    async def fetch(self, sql: str, *args: object) -> list[object]: ...


def assert_panel_sql_admissible(sql: str) -> None:
    lowered = sql.lower()
    for token in ("signals", "model_a", "holding", "theses", "thesis_", "tax_", "screening"):
        if token in lowered:
            raise ValueError(f"forbidden token {token!r} in panel SQL")


assert_panel_sql_admissible(SQL_PANEL)


async def load_panel(conn: FetchConn, *, as_of: date) -> dict[str, list[tuple[date, Decimal]]]:
    """Active ASX symbols' adj_close series up to `as_of`, ascending per symbol."""
    rows = await conn.fetch(SQL_PANEL, as_of)
    panel: dict[str, list[tuple[date, Decimal]]] = {}
    for row in rows:
        px = row["adj_close"]  # type: ignore[index]
        if isinstance(px, float):
            raise ValueError("float adj_close reached the loader")
        panel.setdefault(str(row["symbol"]), []).append((row["dt"], Decimal(str(px))))  # type: ignore[index]
    return panel
