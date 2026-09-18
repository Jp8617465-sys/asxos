"""
Paper-trade evaluator for the M13 portfolio construction layer (M13.8).

Evaluates one or more persisted build-portfolio runs against subsequent
market prices to produce a hypothetical P&L estimate vs the alternative
of doing nothing (holding cash).

This is NOT a backtester — it evaluates the *directional correctness* of
a single proposed rebalance against subsequent market outcomes. The
purpose was to give the operator ≥4 weeks of evidence before flipping
``ASXOS_PORTFOLIO_BRIEF_ENABLED=1`` in production (plan Part 0 Q3). That flag
and the brief section it gated were deleted under A-34 (dark-launch verdict #1,
2026-09-14); this evaluator is kept because the evidence it produces is about
the paper-trade history, not about that one display surface.

Structure
---------
Pure functions (no I/O):
  evaluate()               — takes trades + exit prices, returns PaperTradeOutcome

Async DB helpers (I/O):
  evaluate_run_from_db()   — loads run + prices from DB, calls evaluate()
  list_evaluable_runs()    — runs old enough to have N weeks of subsequent history
  has_enough_paper_weeks() — gate check for the signoff CLI command
  record_signoff()         — inserts decisions row (plan Part 0 Q3 sign-off)

Plan refs: Part 0 Q3, M13.8 prompt, plan I.6.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from itertools import pairwise
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import asyncpg

from asxos import clock
from asxos.domain.decision_engine.paper_book import (
    count_paper_snapshots_matured,
    paper_snapshot_dates,
)
from asxos.domain.portfolio.types import ProposedTrade

# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PaperTradeLine:
    """Hypothetical P&L for a single buy or sell trade.

    Accounting convention:
      buy:  pnl = (exit_price - entry_price) * delta_qty   (+ve = price rose after buy)
      sell: pnl = (entry_price - exit_price) * delta_qty   (+ve = price fell after sell)

    delta_qty is the absolute quantity traded (always >= 0).
    """

    symbol: str
    side: str           # 'buy' or 'sell'
    entry_price: Decimal
    exit_price: Decimal
    delta_qty: Decimal  # abs quantity; always >= 0
    hypothetical_pnl_aud: Decimal


@dataclass(frozen=True)
class PaperTradeOutcome:
    """Outcome of evaluating one build-portfolio run against subsequent prices.

    ``total_traded_aud`` is the denominator: sum of abs(delta_aud) for all
    buy and sell trades (regardless of exit-price availability). This keeps
    the denominator stable even when some symbols lack price history.

    ``hypothetical_return_pct = total_pnl / total_traded * 100``; 0.00 if
    no tradeable activity (all-hold run or zero total_traded_aud).

    ``symbols_missing_exit_price`` names symbols that appear in trades but
    have no price row for eval_as_of — their contribution to
    ``total_hypothetical_pnl_aud`` is zero (conservative).
    """

    run_id: int
    run_as_of: date
    eval_as_of: date
    outcome_days: int               # calendar days between run_as_of and eval_as_of
    lines: list[PaperTradeLine]     # one per buy/sell trade with exit price available
    total_hypothetical_pnl_aud: Decimal
    total_traded_aud: Decimal
    hypothetical_return_pct: Decimal
    symbols_missing_exit_price: list[str]


# ---------------------------------------------------------------------------
# Pure evaluator
# ---------------------------------------------------------------------------


def evaluate(
    *,
    run_id: int,
    run_as_of: date,
    trades: list[ProposedTrade],
    exit_prices: dict[str, Decimal],
    eval_as_of: date,
) -> PaperTradeOutcome:
    """Evaluate proposed trades against exit prices.  Pure — no I/O.

    Only buy and sell trades are processed; hold trades have delta_aud == 0
    by construction so they never contribute to the denominator.

    Symbols without an exit price appear in ``symbols_missing_exit_price``
    and are excluded from ``total_hypothetical_pnl_aud`` (their numerator
    contribution is treated as zero, conservatively).

    Decimal-only arithmetic throughout (plan portfolio-conventions.md).
    """
    active = [t for t in trades if t.side in ("buy", "sell")]

    total_traded = sum(
        (abs(t.delta_aud) for t in active),
        Decimal("0"),
    )

    lines: list[PaperTradeLine] = []
    missing: list[str] = []

    for trade in active:
        exit_px = exit_prices.get(trade.symbol)
        if exit_px is None:
            missing.append(trade.symbol)
            continue

        qty = abs(trade.delta_qty)
        entry_px = trade.reference_price

        pnl = (exit_px - entry_px) * qty if trade.side == "buy" else (entry_px - exit_px) * qty

        lines.append(
            PaperTradeLine(
                symbol=trade.symbol,
                side=trade.side,
                entry_price=entry_px,
                exit_price=exit_px,
                delta_qty=qty,
                hypothetical_pnl_aud=pnl,
            )
        )

    total_pnl = sum((ln.hypothetical_pnl_aud for ln in lines), Decimal("0"))

    if total_traded > Decimal("0"):
        return_pct = (total_pnl / total_traded * Decimal("100")).quantize(Decimal("0.01"))
    else:
        return_pct = Decimal("0.00")

    return PaperTradeOutcome(
        run_id=run_id,
        run_as_of=run_as_of,
        eval_as_of=eval_as_of,
        outcome_days=(eval_as_of - run_as_of).days,
        lines=lines,
        total_hypothetical_pnl_aud=total_pnl,
        total_traded_aud=total_traded,
        hypothetical_return_pct=return_pct,
        symbols_missing_exit_price=missing,
    )


# ---------------------------------------------------------------------------
# DB helpers (async — called by CLI commands)
# ---------------------------------------------------------------------------


async def evaluate_run_from_db(
    conn: asyncpg.Connection,
    run_id: int,
    eval_as_of: date,
) -> PaperTradeOutcome | None:
    """Load proposed trades for run_id from DB, look up exit prices, evaluate.

    Returns None if run_id is not found.  Exit prices are fetched for the
    exact ``eval_as_of`` date; if the market was closed that day (weekend /
    public holiday) the caller should try an adjacent date.
    """
    run_row = await conn.fetchrow(
        "SELECT run_id, as_of FROM rebalance_runs WHERE run_id = $1",
        run_id,
    )
    if run_row is None:
        return None

    run_as_of = run_row["as_of"]

    trade_rows = await conn.fetch(
        """
        SELECT symbol, side, delta_qty, delta_aud, reference_price
        FROM proposed_trades
        WHERE run_id = $1 AND side IN ('buy', 'sell')
        ORDER BY symbol
        """,
        run_id,
    )

    trades = [
        ProposedTrade(
            symbol=r["symbol"],
            side=r["side"],
            delta_qty=Decimal(str(r["delta_qty"])),
            delta_aud=Decimal(str(r["delta_aud"])),
            target_qty=Decimal("0"),    # not needed for evaluation
            current_qty=Decimal("0"),
            reference_price=Decimal(str(r["reference_price"])),
            rationale_tags={},
            lot_hints={},
        )
        for r in trade_rows
    ]

    symbols = list({t.symbol for t in trades})
    if symbols:
        price_rows = await conn.fetch(
            "SELECT symbol, close FROM prices WHERE dt = $1 AND symbol = ANY($2::text[])",
            eval_as_of,
            symbols,
        )
        exit_prices = {r["symbol"]: Decimal(str(r["close"])) for r in price_rows}
    else:
        exit_prices = {}

    return evaluate(
        run_id=run_id,
        run_as_of=run_as_of,
        trades=trades,
        exit_prices=exit_prices,
        eval_as_of=eval_as_of,
    )


async def list_evaluable_runs(
    conn: asyncpg.Connection,
    *,
    weeks: int = 4,
    today: date | None = None,
) -> list[dict[str, Any]]:
    """Return runs old enough to have ``weeks`` of subsequent price history.

    A run is evaluable when ``run.as_of + weeks * 7 <= today``.  The returned
    list is ordered most-recent first.
    """
    if today is None:
        today = clock.today()

    cutoff = today - timedelta(days=weeks * 7)
    rows = await conn.fetch(
        """
        SELECT run_id, as_of
        FROM rebalance_runs
        WHERE as_of <= $1
        ORDER BY as_of DESC
        """,
        cutoff,
    )
    return [{"run_id": r["run_id"], "as_of": r["as_of"]} for r in rows]


# Continuity tolerance: the weekly build_portfolio cron runs every 7 days, so a
# 14-day max gap tolerates exactly one missed slot (transient infra) but fails a
# genuine multi-week blackout.
_CONTINUITY_MAX_GAP_DAYS = 14


def _cron_was_continuous(
    successes: list[date],
    window_open: date,
    today: date,
    *,
    max_gap_days: int = _CONTINUITY_MAX_GAP_DAYS,
) -> bool:
    """True iff the weekly cron actually observed the maturation window.

    `successes` are the `build_portfolio` job_runs success dates (ascending). The
    window the paper trade must have been observed across is `[window_open, today]`.
    Continuous means: a real run opened the window (earliest success on/before
    window_open), the cron is currently alive (latest success within max_gap_days
    of today), and there is no blackout > max_gap_days between consecutive runs.
    """
    if not successes:
        return False
    ordered = sorted(successes)
    if ordered[0] > window_open:
        return False  # the window did not open on a real run — not enough history
    if ordered[-1] < today - timedelta(days=max_gap_days):
        return False  # the cron is not currently alive (stale)
    return all((b - a).days <= max_gap_days for a, b in pairwise(ordered))


async def has_enough_paper_weeks(
    conn: asyncpg.Connection,
    *,
    maturation_weeks: int = 4,
    min_matured_runs: int = 1,
    require_continuity: bool = True,
    today: date | None = None,
) -> bool:
    """M13.8 sign-off gate: are there ≥`maturation_weeks` of OBSERVED paper-book
    evidence?

    Re-pointed 2026-09-16 (F-E2E r2 S3) at `paper_book_snapshots`, the daily
    arbi-declared paper book. It previously counted `rebalance_runs` and the
    `build_portfolio` cron's `job_runs` — a cron deleted in the 2026-08-19 ruling,
    so the gate could never be True (session-handoff-2026-09-14-3.md, Item 9).
    Both reads go through `decision_engine.paper_book`, the one module that names
    the paper table.

    Two independent, decoupled conditions:

    1. **Maturation**: at least `min_matured_runs` paper snapshots are old enough
       to have `maturation_weeks` of subsequent price history
       (`as_of <= today - maturation_weeks*7`).
    2. **Continuity**: the daily writer actually ran across the window — no
       blackout > 14 days, the window opened on a real snapshot, and the writer is
       currently alive. This is what stops a same-day backfill of one old-dated
       row from gaming a pure-time gate.

    Returns `pass_1 and pass_2`. Set `require_continuity=False` to gate on
    maturation alone (e.g. for a manual override path).
    """
    if today is None:
        today = clock.today()
    window_open = today - timedelta(days=maturation_weeks * 7)

    matured = await count_paper_snapshots_matured(conn, window_open=window_open)
    if matured < min_matured_runs:
        return False

    if not require_continuity:
        return True

    successes = await paper_snapshot_dates(
        conn, since=window_open - timedelta(days=_CONTINUITY_MAX_GAP_DAYS)
    )
    return _cron_was_continuous(successes, window_open, today)


async def record_signoff(
    conn: asyncpg.Connection,
    *,
    note: str = "",
    as_of: date | None = None,
) -> int:
    """Insert a decisions row recording the paper-trade sign-off (plan Part 0 Q3).

    Uses ``action='NOTE'`` and ``rationale='[m13_paper_signoff] ...'``.
    Returns the new decisions.id.

    There is no follow-on step. The flag this sign-off once unlocked, and the
    brief section behind it, were deleted under A-34 (2026-09-14); the row
    remains as the record that the paper-trade window was signed off.
    """
    if as_of is None:
        as_of = clock.today()

    parts = [
        "[m13_paper_signoff] Operator signed off ≥4 weeks of paper trading.",
    ]
    if note:
        parts.append(note)
    rationale = " ".join(parts)

    row_id: int = await conn.fetchval(
        """
        INSERT INTO decisions (symbol, decision_date, action, rationale)
        VALUES (NULL, $1, 'NOTE', $2)
        RETURNING id
        """,
        as_of,
        rationale,
    )
    return row_id
