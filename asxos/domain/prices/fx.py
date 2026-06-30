"""Foreign (USD) symbol detection for FX conversion.

Single source of truth for "is this a USD-denominated US-exchange holding that
needs AUDUSD conversion?". The asxos universe is ASX-AUD by default; US holdings
(e.g. a wife's ESPP) carry an exchange suffix and price in USD. Several call
sites (the daily snapshot MV, the wealth-state brief line, the US position
monitor, the holdings importer, the price-sync US phase) all need the same
membership test — keeping it here prevents the stale-copy bug where one site
matched only `.US` and silently mishandled `.NYSE`/`.NASDAQ`/`.AMEX`.

`fx_rates` carries only AUDUSD, so "foreign" == "USD" in v1; suffix-matching is
the codebase's canonical FX signal (not `universe.currency`).
"""
from __future__ import annotations

import re

# USD-denominated US-exchange suffixes. EODHD normalises these for its API, but
# we store and reason about them verbatim. Order is irrelevant.
FOREIGN_SUFFIXES: tuple[str, ...] = (".US", ".NYSE", ".NASDAQ", ".AMEX")

# A plain column reference or table-qualified alias (e.g. "symbol", "hl.symbol").
_COLUMN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_.]*")


def is_foreign_symbol(symbol: str) -> bool:
    """True for a USD-denominated US-exchange symbol (needs AUDUSD conversion).

    `str.endswith` accepts a tuple, so this matches any of FOREIGN_SUFFIXES.
    ASX symbols (`.AU`) and bare codes return False.
    """
    return symbol.endswith(FOREIGN_SUFFIXES)


def foreign_symbol_sql(column: str = "symbol") -> str:
    """A parenthesised SQL predicate matching FOREIGN_SUFFIXES for ``column``.

    e.g. ``foreign_symbol_sql("hl.symbol")`` →
    ``(hl.symbol LIKE '%.US' OR hl.symbol LIKE '%.NYSE' OR …)``.

    Single-sources the WHERE-clause form from FOREIGN_SUFFIXES so SQL filters
    can't drift from the Python test. The suffixes are **hardcoded module
    constants — never user input** — so interpolating them into SQL carries no
    injection risk. ``column`` must be a developer-supplied identifier/alias,
    never external input; the guard below rejects anything that isn't a plain
    column reference so a future caller cannot route untrusted data here.
    """
    if not _COLUMN_RE.fullmatch(column):
        raise ValueError(
            f"foreign_symbol_sql column must be a plain identifier/alias, got {column!r}"
        )
    return "(" + " OR ".join(f"{column} LIKE '%{sfx}'" for sfx in FOREIGN_SUFFIXES) + ")"
