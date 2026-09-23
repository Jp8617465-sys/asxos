"""Has the data layer EVER held a financial statement for a symbol?

One question, two consumers, and they must not drift apart:

* ``jobs/build_decision_packets.py`` asks it per symbol, to set a thesis aside
  into ``no_data_coverage`` *before* calling the builder (issue #327). A symbol
  the vendor does not serve would otherwise raise every night into
  ``monitor.note`` and page through ``check_cron_health`` forever.
* ``asxos/brief/compose.py`` asks it for the whole thesis set, so a thesis the
  builder sets aside still appears somewhere James reads (E-30). Once a name
  stops paging it also stops being visible; that is the half #327 kept open.

**"Ever", not "at this cutoff" — this is the safety property, stated once here
rather than twice in prose that can diverge.** Zero rows ever means the vendor
does not cover the name and no run will ever build it. A symbol *with* history
whose cutoff yields nothing admissible is a regression: it must still fail
loudly in the job, and it is NOT what either query below detects.

Measured 2026-09-19 on the first ``weekly-research`` run after #328's held-US-name
union shipped: the run concluded ``success`` and ``sync_financial_statements``
wrote 437,031 rows, yet ``HUBS.NYSE`` has ZERO — as do ALL non-``.AU`` symbols,
0 of 3,379 distinct. That is a vendor-coverage fact, not a fault in any job.

The two statements are kept in one module so that widening one (a different
table, an added predicate) is a change to the other by construction.
"""

from __future__ import annotations

from typing import Any, Final

#: Per-symbol form. ``$1`` is the symbol; a row means "covered", ``None`` means
#: never covered. Used by the packet builder's partition.
SQL_SYMBOL_HAS_STATEMENTS: Final[str] = (
    "SELECT 1 FROM rs_financial_statements WHERE symbol = $1 LIMIT 1"
)

#: Set form. ``$1`` is a symbol array; returns the subset that IS covered.
#: Deliberately returns the covered set rather than the uncovered one: the
#: caller knows which symbols it asked about, and a query that returned
#: "missing" rows would have to invent them.
SQL_SYMBOLS_WITH_STATEMENTS: Final[str] = (
    "SELECT DISTINCT symbol FROM rs_financial_statements WHERE symbol = ANY($1)"
)


async def covered_symbols(conn: Any, symbols: list[str]) -> set[str]:
    """The subset of ``symbols`` the data layer has ever held a statement for.

    An empty input short-circuits: ``ANY('{}')`` is a valid but pointless round
    trip, and the brief runs this on every compose.
    """
    if not symbols:
        return set()
    rows = await conn.fetch(SQL_SYMBOLS_WITH_STATEMENTS, symbols)
    return {str(r["symbol"]) for r in rows}
