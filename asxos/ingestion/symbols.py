"""Vendor symbol-format mapping — the single source of truth.

Project symbols carry the *listing* exchange (``HUBS.NYSE``, ``CRM.NASDAQ``,
``BHP.AU``). EODHD addresses US listings through one combined exchange
(``HUBS.US``). Every per-symbol EODHD call must translate on the way out and
store under the original project symbol on the way back, so foreign keys to
``universe(symbol)`` hold. Suffixes absent from the map pass through unchanged,
so routing an already-canonical symbol (``BHP.AU``, ``AXJO.INDX``) through
``eodhd_symbol()`` is a no-op, not a corruption.

Why this module exists at all
-----------------------------
``eodhd_symbol()`` used to live in ``asxos/domain/position_monitor/fetcher.py``
and was imported *upward* by ``asxos/ingestion/prices.py`` — ingestion depending
on a domain leaf, backwards from the layering this package exists to enforce.
Worse, importing it dragged ``httpx``/``tenacity``/``fred`` in with it, which
``asxos/ingestion/news.py`` cannot afford: ``jobs/ingest_news.py`` imports that
module eagerly precisely because it is stdlib + asyncpg only.

Keeping the map in one place is the point. ``asxos/domain/prices/fx.py`` already
records what happens otherwise — "prevents the stale-copy bug where one site
matched only ``.US`` and silently mishandled ``.NYSE``". A second copy of a
suffix table is how that bug comes back.

Stdlib only. Import freely from anywhere.
"""
from __future__ import annotations

# Project exchange suffix -> EODHD exchange suffix.
#
# Keep in sync with FOREIGN_SUFFIXES in asxos/domain/prices/fx.py: any suffix
# treated as foreign for FX purposes needs a vendor mapping here, or its
# per-symbol fetches silently address the wrong namespace.
_SUFFIX_REMAP: dict[str, str] = {
    ".NYSE": ".US",
    ".NASDAQ": ".US",
    ".AMEX": ".US",
}


def eodhd_symbol(symbol: str) -> str:
    """Convert a project symbol to EODHD exchange format.

    ``HUBS.NYSE`` -> ``HUBS.US``; ``CRM.NASDAQ`` -> ``CRM.US``;
    ``BHP.AU`` -> ``BHP.AU`` (ASX passes through unchanged).

    Always returns UPPERCASE, including on the pass-through branch, so callers
    can compare the result against another symbol without re-casing it.
    """
    upper = symbol.upper()
    for suffix, replacement in _SUFFIX_REMAP.items():
        if upper.endswith(suffix):
            return upper[: -len(suffix)] + replacement
    return upper


def symbol_root(symbol: str) -> str:
    """The bare ticker, with any exchange suffix stripped.

    ``HUBS.NYSE`` -> ``HUBS``; ``BHP.AU`` -> ``BHP``; ``HUBS`` -> ``HUBS``.

    Use this ONLY to resolve a vendor tag against a symbol you already know the
    request was for. A bare root is not globally unique — ASX three-letter codes
    collide with US tickers routinely — so matching bare roots across a whole
    holdings set silently misattributes news between securities.
    """
    upper = symbol.upper()
    head, _, _tail = upper.partition(".")
    # Deliberately NOT `head or upper`: that fallback fires only for a
    # dot-leading symbol and then returns the string *including* the dot, which
    # is not a root by any reading. An empty root is the honest answer, and
    # callers already skip empty keys.
    return head
