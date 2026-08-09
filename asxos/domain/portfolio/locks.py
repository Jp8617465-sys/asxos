"""Disposal-lock reads over holding_lots (0042, KD-3).

The ESS lock is a property of the SHARES (the lot), not of any rule: a thesis
can close and reopen while the lock persists, and future ESS/Div 83A work
(register #13, D8) hangs off the same lot columns. "Symbol locked as of D" =
any open lot with ``disposal_locked AND (lock_end IS NULL OR lock_end >= D)``;
``lock_end IS NULL`` while locked means locked INDEFINITELY (the honest
representation of "end date unknown — confirm from plan administrator").

Consumers: jobs/check_thesis_invalidations.py (alert demotion),
the brief active_theses collector (lock badge), jobs/sweep_rule_integrity.py.
Effective trigger semantics on any condition for a locked symbol are demoted
to alert_review at read time — the lock never mutates authored intent (KD-2).

Read-only module — no monetary arithmetic at all (Decimal-only invariant is
trivially satisfied), no writes, no firewall gate of its own: the
ASXOS_PERSONAL_USE gate lives in the CLI/job entry points that call it
(.claude/rules/portfolio-conventions.md, Part 0 Q1).
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

import asyncpg


@dataclass(frozen=True)
class LockState:
    """One symbol's effective disposal lock as of a date. Presence in the
    get_disposal_locks() result dict means LOCKED — absent symbols are
    unlocked."""

    symbol: str
    lock_end: date | None  # None = locked indefinitely (end date unknown)
    lock_note: str


async def get_disposal_locks(
    conn: asyncpg.Connection, symbols: Sequence[str], as_of: date
) -> dict[str, LockState]:
    """Return {symbol: LockState} for every symbol with an ACTIVE lock as of
    ``as_of``. Symbols with no active lock are simply absent from the dict.

    Multiple locked open lots per symbol collapse to the most conservative
    single state: an indefinite (NULL lock_end) lot wins outright, otherwise
    the latest lock_end wins — ORDER BY lock_end DESC NULLS FIRST + first row
    per symbol.
    """
    if not symbols:
        return {}
    rows = await conn.fetch(
        """
        SELECT symbol, lock_end, lock_note
        FROM holding_lots
        WHERE symbol = ANY($1::text[])
          AND disposed_at IS NULL
          AND disposal_locked
          AND (lock_end IS NULL OR lock_end >= $2)
        ORDER BY symbol, lock_end DESC NULLS FIRST
        """,
        list(symbols),
        as_of,
    )
    out: dict[str, LockState] = {}
    for r in rows:
        if r["symbol"] in out:
            continue  # first row per symbol is already the most conservative
        out[r["symbol"]] = LockState(
            symbol=r["symbol"],
            lock_end=r["lock_end"],
            lock_note=r["lock_note"] or "",
        )
    return out
