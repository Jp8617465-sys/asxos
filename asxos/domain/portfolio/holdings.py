"""Which symbols we actually HOLD — independent of universe membership.

Extracted 2026-09-18 from `jobs/sync_prices.py::get_us_holding_symbols` when a
second job needed it. The move is the point, not a tidy-up: incident #327 was a
held US position silently excluded from a data job because that job had no way to
ask this question, and `asxos/domain/prices/fx.py`'s own header warns about exactly
this class of bug — "the stale-copy bug where one site matched only `.US` and
silently mishandled `.NYSE`/`.NASDAQ`/`.AMEX`".

**The distinction this module exists to keep straight.** `universe.is_active=FALSE`
means "not an ASX-equity-universe member". It does **not** mean "we don't hold it"
(`.claude/rules/portfolio-conventions.md`, the `security_kind` note). A held US name
is `is_active=FALSE` on purpose, so every `WHERE is_active` ASX-equity reader excludes
it for free and no US row leaks into ASX-model candidates. The cost of that overload
is that a job wanting "everything we hold" cannot use `is_active` at all, and must
ask `holding_lots` directly — which is what this module does.

Sourcing from open lots also means coverage **auto-stops when a lot closes**, with no
list to maintain anywhere.

The clean end-state is a `security_kind` enum collapsing the three suffix/flag
conventions into one column (`m14_candidate_security_kind_enum`); until that lands,
this is the single place to ask the question.
"""
from __future__ import annotations

import asyncpg

from asxos.domain.prices.fx import foreign_symbol_sql


async def held_foreign_symbols(conn: asyncpg.Connection) -> list[str]:
    """Distinct US-exchange symbols with at least one OPEN holding lot, sorted.

    Deliberately reads `holding_lots` rather than `universe`: a held US name is
    `is_active=FALSE` by convention, so any `WHERE is_active` filter returns nothing
    for it. The `prices`→`universe` foreign key still holds, because the holding's
    `universe` row already exists — it is simply flagged out of the ASX equity set.

    Returns `[]` when nothing foreign is held, which every caller must treat as a
    valid answer rather than an error.
    """
    rows = await conn.fetch(
        "SELECT DISTINCT symbol FROM holding_lots"
        f" WHERE disposed_at IS NULL AND {foreign_symbol_sql('symbol')}"
        " ORDER BY symbol"
    )
    return [r["symbol"] for r in rows]
