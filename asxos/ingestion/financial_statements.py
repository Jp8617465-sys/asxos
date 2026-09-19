"""Financial-statements ingestion — research store `rs_financial_statements`.

Raw historical balance-sheet / income / cash-flow statements for every security in
`rs_security_master`, the source from which point-in-time factors are later derived.
SEPARATE from production tables — never touches `universe` or `prices`.

This is the leak-critical job. The protection is NOT in this table (which stores the
raw `filing_date` and `report_date`) but in `derive_knowledge_date()` below — the
guarded rule the `rs_fundamentals_pit` derivation (next step) MUST apply. It is
implemented and tested here because the disclosure-date semantics live here.

Structure (probe 2026-06-24, verified on a real payload):
  Financials.{Income_Statement,Balance_Sheet,Cash_Flow}.{yearly,quarterly}[period] each
  carry `date` (period end), `filing_date`, `currency_symbol`, and the line items.
  `Earnings.History[].reportDate` is joined onto statements by period end.

Why the guard, not a single field (probe 2026-06-24):
  `reportDate` is a real disclosure date for most names but defaults to `period_end`
  for some (BHP); `filing_date` is likewise inconsistent. Each can also be a
  future/scheduled date. Neither is safe alone.

Decimal for promoted numerics; the full raw statement is kept in `line_items` JSONB.

Sector enrichment: the same `/fundamentals` payload carries `General.Sector` /
`General.Industry`, so this job ALSO back-fills `rs_security_master.gics_sector` /
`gics_industry` — the "later enrichment pass" that `security_master.py` deliberately
left unwritten so it would not clobber. (EODHD exposes the Morningstar-style `Sector`;
`GicSector` is NULL on the current plan — same source as production `universe.sector`.)
This is what makes the downstream sector-neutral `rs_factor_scores` possible.
"""
from __future__ import annotations

import asyncio
import json
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING, Any, Literal

import asyncpg

from asxos.ingestion.symbols import eodhd_symbol

if TYPE_CHECKING:
    # Deliberately NOT a module-top runtime import (P2-04 Step 0): importing
    # `asxos.ingestion.eodhd` executes `asxos.config` (`config.py:108`
    # instantiates `CoreSettings()`, which reads the secrets env file), and
    # this module's pure `derive_knowledge_date()` is imported by
    # `asxos/domain/results_review/contracts.py:49` — a path that must be
    # importable in secrets-free environments (tests, contract consumers).
    # `EODHDClient` is used only as a type annotation here (PEP 563 keeps it
    # unevaluated at runtime); the job entry point
    # (`jobs/sync_financial_statements.py`) imports the real client itself.
    from asxos.ingestion.eodhd import EODHDClient

# EODHD Financials block name -> our statement_type token.
_STMT_MAP = {
    "Income_Statement": "income",
    "Balance_Sheet": "balance_sheet",
    "Cash_Flow": "cash_flow",
}

# Conservative fallback lag when neither disclosure date is usable. Observed real
# lags: annual ~57-68d, quarterly ~33-55d (probe 2026-06-24). Annual default; the
# derivation step may pass a tighter value per period_type.
_DEFAULT_LAG_DAYS = 75


#: Tier of evidence behind a `knowledge_date`. `filed` = a real disclosure date the
#: vendor reported and the guard accepted. `estimated` = no usable disclosure date
#: existed, so the date is `period_end + lag_days` — a convention, not an event.
KnowledgeTier = Literal["filed", "estimated"]


def derive_knowledge_date_tiered(
    period_end: date,
    report_date: date | None,
    filing_date: date | None,
    as_of: date,
    *,
    lag_days: int = _DEFAULT_LAG_DAYS,
) -> tuple[date, KnowledgeTier]:
    """THE point-in-time leak guard, plus how much the answer is worth.

    Rule (probe-validated 2026-06-24), unchanged:
      knowledge_date = max(d for d in (report_date, filing_date)
                           if d is not None and period_end < d <= as_of)   -> `filed`
                       else period_end + lag_days                          -> `estimated`

    - `d <= as_of` drops scheduled/future disclosure dates -> no look-ahead. This is
      what removes the e.g. period 2026-06-30 / reportDate 2026-08-11 forecast row.
    - `period_end < d` drops a field that defaulted to period_end (no real lag).
    - the fallback covers the both-defaulted / both-missing case.

    `as_of` is the point-in-time cutoff (today at ingest, or a research test_date when
    re-deriving). NEVER pass a future as_of expecting future dates to survive — they
    are dropped by design.

    **Why the tier exists (2026-09-02).** Stage 1's exit gate is "replay a historical
    decision date using only facts with `known_at <= cutoff`". That predicate is only
    meaningful if `knowledge_date` records something we actually knew. The fallback
    branch does not: `period_end + 75d` is an assumption about how long filing usually
    takes, and it can even land in the FUTURE when `as_of` is close to `period_end`.
    Measured live 2026-09-02: 326 rows of `rs_fundamentals_pit` carry
    `knowledge_date = 2026-09-13`, every one of them `period_end 2026-06-30 + 75d`,
    with `report_date` NULL and `filing_date` equal to `period_end` (so the guard
    correctly rejected it) — i.e. **every future row comes from this fallback, not
    from a scheduled `report_date`.**

    Those rows are harmless to today's readers, which all filter
    `knowledge_date <= as_of` and therefore just cannot see them. They are not
    harmless to a replay: a replay that accepts estimated rows can declare itself
    clean while resting on a date nobody ever observed. So the fix is to record the
    difference, not to clamp the date — clamping would assert we knew something
    earlier than we did, which is the look-ahead leak this guard exists to prevent.

    Callers that only need the date can keep using `derive_knowledge_date()`.
    """
    candidates = [
        d for d in (report_date, filing_date)
        if d is not None and period_end < d <= as_of
    ]
    if candidates:
        return max(candidates), "filed"
    return period_end + timedelta(days=lag_days), "estimated"


def derive_knowledge_date(
    period_end: date,
    report_date: date | None,
    filing_date: date | None,
    as_of: date,
    *,
    lag_days: int = _DEFAULT_LAG_DAYS,
) -> date:
    """Date-only view of `derive_knowledge_date_tiered()`. Behaviour unchanged."""
    knowledge_date, _tier = derive_knowledge_date_tiered(
        period_end, report_date, filing_date, as_of, lag_days=lag_days
    )
    return knowledge_date


def _dec(x: Any) -> Decimal | None:
    if x is None or x == "":
        return None
    try:
        return Decimal(str(x))
    except InvalidOperation:
        return None


def _d(s: Any) -> date | None:
    try:
        return date.fromisoformat(str(s)[:10]) if s else None
    except (TypeError, ValueError):
        return None


def _report_dates(fund: dict[str, Any]) -> dict[date, date | None]:
    """period_end -> reportDate from Earnings.History (raw; may be future/None)."""
    out: dict[date, date | None] = {}
    history = ((fund.get("Earnings") or {}).get("History")) or {}
    for v in history.values():
        if isinstance(v, dict):
            pe = _d(v.get("date"))
            if pe is not None:
                out[pe] = _d(v.get("reportDate"))
    return out


def _promote(st: dict[str, Any], stmt_type: str) -> dict[str, Decimal | None]:
    """Promote the scalar line items relevant to this statement type. The full raw
    statement is preserved in line_items JSONB regardless."""
    p: dict[str, Decimal | None] = dict.fromkeys(
        ("total_revenue", "net_income", "total_assets", "total_equity", "total_debt", "shares_diluted")
    )
    if stmt_type == "income":
        p["total_revenue"] = _dec(st.get("totalRevenue"))
        p["net_income"] = _dec(st.get("netIncome"))
    elif stmt_type == "balance_sheet":
        p["total_assets"] = _dec(st.get("totalAssets"))
        p["total_equity"] = _dec(st.get("totalStockholderEquity"))
        p["total_debt"] = _dec(st.get("shortLongTermDebtTotal"))
        # period-end shares outstanding (proxy for diluted; derivation may refine)
        p["shares_diluted"] = _dec(st.get("commonStockSharesOutstanding"))
    return p


# Row tuple matches _UPSERT params $1..$14 (line_items is a JSON string -> ::jsonb).
def to_statement_rows(fund: Any, symbol: str, *, as_of: date) -> list[tuple[Any, ...]]:
    """EODHD /fundamentals payload -> rs_financial_statements rows (3 statements x
    yearly+quarterly). `report_date` is joined from Earnings.History by period end.
    Statements with no `date`, or a period_end after `as_of` (unreported future
    period — EODHD should never return one, this is a safety net), are skipped."""
    rows: list[tuple[Any, ...]] = []
    if not isinstance(fund, dict):
        return rows
    fin = fund.get("Financials") or {}
    rdmap = _report_dates(fund)
    for eod_name, stmt_type in _STMT_MAP.items():
        block = fin.get(eod_name) or {}
        for period_type in ("yearly", "quarterly"):
            periods = block.get(period_type) or {}
            for st in periods.values():
                if not isinstance(st, dict):
                    continue
                pe = _d(st.get("date"))
                if pe is None or pe > as_of:
                    continue
                prom = _promote(st, stmt_type)
                rows.append((
                    symbol, pe, period_type, stmt_type,
                    _d(st.get("filing_date")),
                    rdmap.get(pe),
                    # `or None` for the same reason _sector_industry does it below: a bare
                    # `a or b` chain returns the LAST falsy operand, so two blank sources
                    # yield '' rather than NULL. This line is the ORIGIN of the blank
                    # currencies that then propagate into rs_fundamentals_pit. Blank is
                    # missing data, not a currency. (Counts and query scope live in
                    # docs/proposals/segval-live-validation-2026-08-20.md F1, not here --
                    # a census baked into a comment rots, and this function writes both
                    # yearly AND quarterly rows, so F1's yearly-scoped figures would
                    # understate this line's reach anyway.)
                    #
                    # Two honest limits, so the next reader does not over-trust it:
                    #   1. Fixes rows written FROM NOW ON. Legacy blank rows are NOT
                    #      backfilled, so on THIS table the correct predicate stays
                    #      `WHERE (currency IS NULL OR currency = '')`. rs_fundamentals_pit
                    #      has no such problem -- refresh_fundamentals_pit() re-derives the
                    #      whole symbol space through _currency() every run, so it heals.
                    #   2. `or None` catches '' but NOT whitespace-only ('   '), which would
                    #      still land here as-is. _currency() strips at the PIT layer, so
                    #      the derived table is safe either way; this one is not.
                    (st.get("currency_symbol") or block.get("currency_symbol") or None),
                    prom["total_revenue"], prom["net_income"], prom["total_assets"],
                    prom["total_equity"], prom["total_debt"], prom["shares_diluted"],
                    json.dumps(st, default=str),
                ))
    return rows


def _sector_industry(fund: Any) -> tuple[str | None, str | None]:
    """(sector, industry) from the EODHD General block. Prefer GicSector when present
    (NULL on the current plan), else the Morningstar-style Sector. Blank → None."""
    if not isinstance(fund, dict):
        return None, None
    general = fund.get("General") or {}
    sector = general.get("GicSector") or general.get("Sector") or None
    industry = general.get("GicIndustry") or general.get("Industry") or None
    return (sector or None), (industry or None)


# Enrichment-only UPDATE: touches gics_sector/gics_industry on an EXISTING row (the
# security master always runs first). COALESCE preserves a previously-learned value
# when a later sparse payload omits the field; never inserts (no row → no-op).
_SECTOR_UPDATE = """
UPDATE rs_security_master SET
    gics_sector   = COALESCE($2, gics_sector),
    gics_industry = COALESCE($3, gics_industry),
    updated_at    = now()
WHERE symbol = $1
"""


_UPSERT = """
INSERT INTO rs_financial_statements
    (symbol, period_end, period_type, statement_type, filing_date, report_date, currency,
     total_revenue, net_income, total_assets, total_equity, total_debt, shares_diluted,
     line_items, source)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14::jsonb, 'eodhd')
ON CONFLICT (symbol, period_end, period_type, statement_type) DO UPDATE SET
    filing_date    = EXCLUDED.filing_date,
    report_date    = COALESCE(EXCLUDED.report_date, rs_financial_statements.report_date),
    currency       = EXCLUDED.currency,
    total_revenue  = EXCLUDED.total_revenue,
    net_income     = EXCLUDED.net_income,
    total_assets   = EXCLUDED.total_assets,
    total_equity   = EXCLUDED.total_equity,
    total_debt     = EXCLUDED.total_debt,
    shares_diluted = EXCLUDED.shares_diluted,
    line_items     = EXCLUDED.line_items,
    source         = 'eodhd'
"""


# Whole-run wall-clock deadline for the bounded-worker pool (CLAUDE.md #10: fail
# loud). It is a HANG detector, not a throughput budget: a systemic EODHD outage makes
# every fetch burn ~185s (httpx 60s x 3 tenacity attempts); across ~2,382 names / 8
# workers that hangs the run for ~15h, orphaning a 'running' row that only self-heals on
# the NEXT weekly run. The deadline converts that silent hang into a loud JobMonitor
# 'failure' inside the window.
# Sizing (revised 2026-07-13): the healthy run's cost is the per-symbol batched writes
# (see executemany in the worker). Post-batching the full run is estimated ~15-30 min —
# round-trips collapse ~160x (from ~380k per-row to ~2,382 per-symbol); 90 min leaves
# generous headroom for that (still-unvalidated-in-prod) estimate while catching the
# ~15h hang by a wide margin. The prior 3600s/"tens of minutes" sizing predated the
# 2026-07-13 smoke, which measured 77 min for just 200 symbols on the per-row path — so
# 3600 would have killed even a healthy full run. Real validation = first post-merge
# weekly run (Sat); watch its duration_ms and tighten if it lands well under 30 min.
#
# !! DEAD AS SIZED (annotated 2026-08-17, comment only — deliberately NOT re-tuned) !!
# This guard can never fire on the scheduled path. 5400s is exactly 90 minutes, and
# `.github/workflows/weekly-research.yml` sets `timeout-minutes: 90` for the ENTIRE
# six-step job — of which this is step 4. GitHub's timeout therefore always wins.
# Observed: run 31895667938 (2026-08-15) cancelled this step 82s in, having spent 88.1
# min on step 3. The "real validation = first post-merge Saturday" note above has been
# silently blocked by that shared budget ever since the Render -> Actions migration:
# it is waiting on a duration_ms that the scheduled path has never produced.
# A per-step guard has to be a SHARE of the job budget, not equal to it — see
# `corporate_actions._RUN_DEADLINE_S` for a correctly-sized one and its arithmetic.
# Re-sizing this value is out of scope for the change that added this note;
# `tests/test_corporate_actions.py::test_financial_statements_deadline_is_dead_as_sized`
# pins the current state so the fix is not silently forgotten.
_RUN_DEADLINE_S = 5400


async def refresh_financial_statements(
    client: EODHDClient,
    conn: asyncpg.Connection,
    symbols: list[str],
    *,
    as_of: date,
    concurrency: int = 8,
) -> dict[str, int]:
    """Ingest raw financial statements for `symbols` into rs_financial_statements.

    One `/fundamentals` call per symbol, fetched with bounded concurrency, written
    serially through the single connection. Idempotent UPSERT on
    (symbol, period_end, period_type, statement_type); resumable. A symbol whose
    fetch errors is counted failed and skipped, never aborting the run. The same
    payload back-fills rs_security_master.gics_sector/gics_industry (enrichment pass).
    """
    counts = {
        "symbols": len(symbols), "statements": 0, "symbols_with_statements": 0,
        "failed": 0, "sectors_enriched": 0,
    }

    # Bounded-worker pool: exactly `concurrency` workers pull from a shared queue,
    # each fetching -> parsing -> writing ONE symbol before its payload goes out of
    # scope. This caps resident memory at ~`concurrency` fundamentals payloads.
    #
    # The previous form — `asyncio.as_completed([ensure_future(fetch(s)) for s in
    # symbols])` — retained EVERY completed task's full payload (each task in the
    # list holds its result) for the whole run, so memory grew linearly with
    # symbols processed and OOM-killed the job at 512Mi (confirmed via Render event
    # 2026-07-11: oomKilled ~78s into the run). The Semaphore bounded fetching, not
    # retention. asyncpg forbids concurrent ops on one connection, so all DB writes
    # are serialised behind write_lock; only the HTTP fetches run concurrently.
    queue: asyncio.Queue[str] = asyncio.Queue()
    for s in symbols:
        queue.put_nowait(s)
    write_lock = asyncio.Lock()

    async def worker() -> None:
        while True:
            try:
                sym = queue.get_nowait()
            except asyncio.QueueEmpty:
                return
            try:
                try:
                    # Request in the vendor's namespace, store under the project
                    # symbol — the same two-step `prices.py::refresh_us_prices`
                    # takes. `HUBS.NYSE` is `HUBS.US` to EODHD; sent unchanged it
                    # 404s, lands in the `except` below as a counted-and-skipped
                    # failure, and the run stays green with the symbol absent.
                    # That is how #328's widened selection produced zero HUBS
                    # rows on its first live run (2026-09-19, incident #327).
                    fund: Any = await client.fundamentals(eodhd_symbol(sym))
                except Exception:
                    fund = None
                if fund is None:
                    counts["failed"] += 1
                    continue
                sector, industry = _sector_industry(fund)
                rows = to_statement_rows(fund, sym, as_of=as_of)
                # Drop the large raw payload before contending for write_lock —
                # sector/industry/rows are already extracted, so a worker blocked
                # on the serialised write no longer pins the multi-MB fundamentals
                # dict (belt-and-braces under the ~2.5x headroom at 512Mi).
                del fund
                async with write_lock:
                    if sector or industry:
                        await conn.execute(_SECTOR_UPDATE, sym, sector, industry)
                        counts["sectors_enriched"] += 1
                    if rows:
                        counts["symbols_with_statements"] += 1
                        # Batch the per-symbol UPSERTs into ONE executemany round-trip
                        # (house style — `prices.py::upsert_prices` and
                        # `regulatory.py::upsert_events`, the two that existed on
                        # 2026-07-13; `security_master.py::refresh_security_master` was
                        # batched later, on 2026-07-18, so it is not a precedent for
                        # this one). Cited by module::function deliberately: the
                        # original citation here was a file:line pointing at
                        # `asxos/domain/signals/writer.py:69`, a path that does not
                        # exist in this repo — which is exactly how file:line rots.
                        # The prior
                        # per-row loop issued one network round-trip per statement row:
                        # the 2026-07-13 --limit 200 smoke wrote 32,095 rows in 77 min
                        # (round-trip-bound), extrapolating to ~15h for the full ~2,382-
                        # name weekly run — well past _RUN_DEADLINE_S. executemany prepares
                        # _UPSERT once and sends all rows in one round-trip, so the
                        # ON CONFLICT idempotency and the $14::jsonb cast are unchanged.
                        # NOT strictly behavior-preserving: writes shift from per-row-
                        # persist to per-symbol-atomic (asyncpg executemany is one implicit
                        # transaction) — a mid-symbol write error rolls back that symbol's
                        # batch and aborts the run (siblings cancelled below). Safe because
                        # the UPSERT is idempotent and the run is resumable on re-fetch.
                        await conn.executemany(_UPSERT, rows)
                        counts["statements"] += len(rows)
            finally:
                queue.task_done()

    workers = [asyncio.ensure_future(worker()) for _ in range(concurrency)]
    try:
        # Hard wall-clock deadline (see _RUN_DEADLINE_S) so a systemic upstream
        # stall fails loud in-window instead of hanging until Render kills it.
        await asyncio.wait_for(asyncio.gather(*workers), timeout=_RUN_DEADLINE_S)
    except BaseException:
        # A parse/write error, a TimeoutError from the deadline, or cancellation
        # aborts the run (original contract). Cancel the siblings and await them
        # BEFORE unwinding past the caller's `async with acquire() as conn` block
        # — otherwise an orphaned worker could call conn.execute after the
        # connection is released to the pool.
        for w in workers:
            w.cancel()
        await asyncio.gather(*workers, return_exceptions=True)
        raise
    return counts
