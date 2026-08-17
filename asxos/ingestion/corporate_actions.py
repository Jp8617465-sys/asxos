"""Corporate-actions ingestion — research store `rs_corporate_actions`.

Dividends (`/div`) + splits (`/splits`) for every security in `rs_security_master`
(survivorship-free). SEPARATE from production tables — this module never touches
`universe` or `prices`.

Field semantics verified by the read-only probes (docs/research/probes/
2026-06-24-eodhd-gate-closure.md and the 2026-06-24 corporate-actions probe):

  * `/div` object: `date` (ex-date), `value` (split-adjusted), `unadjustedValue`
    (as-paid cash/share — the PIT-correct figure -> `dividend_amount`), `paymentDate`,
    `recordDate`, `period`, `currency`, and (AU only) `franking` as a "<float>%"
    string. US names carry no `franking` key. No-dividend names return [].
  * `franking` parses to NUMERIC: "100%"->100, "0%"->0, "25.03%"->25.03. **NULL means
    undeclared/unknown — NOT 0** (0% = explicitly unfranked; the tax distinction is
    material). Out-of-range values parse to NULL.
  * `/splits` object: `date` (ex-date), `split` = "new/old" string
    ("4.000000/1.000000" = 4:1) -> `split_ratio` = new/old.

Decimal throughout (NUMERIC columns; never float for money).
"""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from datetime import date
from decimal import Decimal, DecimalException, InvalidOperation
from typing import Any

import asyncpg

from asxos.ingestion.eodhd import EODHDClient

log = logging.getLogger(__name__)

# (symbol, ex_date, action_type, split_ratio, dividend_amount, franking_pct,
#  pay_date, record_date) — `source` is the literal below. franking_pct is COALESCEd
# so a later run returning NULL never wipes a known franking value.
_UPSERT = """
INSERT INTO rs_corporate_actions
    (symbol, ex_date, action_type, split_ratio, dividend_amount, franking_pct,
     pay_date, record_date, source)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'eodhd')
ON CONFLICT (symbol, ex_date, action_type) DO UPDATE SET
    split_ratio     = EXCLUDED.split_ratio,
    dividend_amount = EXCLUDED.dividend_amount,
    franking_pct    = COALESCE(EXCLUDED.franking_pct, rs_corporate_actions.franking_pct),
    pay_date        = EXCLUDED.pay_date,
    record_date     = EXCLUDED.record_date,
    source          = 'eodhd'
"""

_HUNDRED = Decimal(100)

# Whole-run wall-clock deadline (CLAUDE.md #10: fail loud). Like the sibling guard in
# financial_statements.py it is a HANG detector, not a throughput budget — a systemic
# EODHD stall makes every fetch burn ~185s (httpx 60s x 3 tenacity attempts), which
# would hang the run for hours and orphan a 'running' job_runs row that only self-heals
# on the NEXT weekly run.
#
# Sizing (2026-08-17) — deliberately NOT 5400 like financial_statements.py:
# `.github/workflows/weekly-research.yml` sets `timeout-minutes: 90` for the ENTIRE
# six-step job, so a 90-minute per-step guard is provably dead: GitHub's timeout always
# fires first. That is exactly what happened on run 31895667938 (2026-08-15) — this step
# ran 88.1 min, GitHub cancelled the job, and `Derive fundamentals PIT` never ran.
# A per-step guard must therefore be sized as a SHARE of the 90-minute budget:
#   * healthy post-batching estimate for this step is ~10-12 min — fetching already
#     finishes in ~5 min (~4,784 requests; the 174 HTTP 429s on 08-15 all fell inside one
#     4-minute window, so rate limiting was never the bottleneck), and the writes
#     collapse from 30,099 sequential round-trips to ~1,721 per-symbol batches (that is
#     one batch per symbol that HAD actions, ~17.5 rows each; ~2,392 symbols are
#     processed in total, the rest carrying no actions at all);
#   * 1500s = 25 min is ~2x that estimate, so a healthy run has generous headroom;
#   * it leaves ~64 min of the 90 for the three downstream steps, whose only observed
#     scheduled cost is financial statements 11.4 min (run 31267448443) + PIT ~2.5 min.
# The point of firing INSIDE the GitHub timeout is attribution: JobMonitor gets to write
# a real 'failure' row with an error message, instead of the step being killed mid-run
# with no record of why. Re-tighten once a scheduled run publishes a real duration_ms.
_RUN_DEADLINE_S = 1500

# How many per-symbol write failures get a full traceback before the log switches to
# counting only. See the write-failure branch in refresh_corporate_actions().
_WRITE_TRACEBACK_LIMIT = 5


def parse_franking(raw: Any) -> Decimal | None:
    """AU franking "<float>%" -> Decimal(0..100); NULL when undeclared/unknown.

    NULL is NOT 0 — 0% is explicitly unfranked, NULL is "no franking info". Values
    outside [0, 100], and the non-finite specials (NaN/sNaN/Infinity), parse to NULL.
    """
    if raw is None:
        return None
    s = str(raw).strip().rstrip("%").strip()
    if not s:
        return None
    try:
        v = Decimal(s)
    except InvalidOperation:
        return None
    # `Decimal("NaN")` parses fine, but ANY comparison against it signals
    # InvalidOperation — so the range check below must not be reached with a
    # non-finite value. Without this the docstring's "outside [0,100] -> NULL"
    # promise was false for "NaN%": it raised out of the parser and killed the run.
    if not v.is_finite():
        return None
    return v if Decimal(0) <= v <= _HUNDRED else None


def parse_split_ratio(raw: Any) -> Decimal | None:
    """EODHD "new/old" split string -> Decimal(new/old). NULL on malformed/zero-div,
    and NULL on any non-finite result (NaN/Infinity) — see `_finite_or_none`."""
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    try:
        if "/" in s:
            new, old = s.split("/", 1)
            n, o = Decimal(new.strip()), Decimal(old.strip())
            return _finite_or_none(n / o) if o != 0 else None
        return _finite_or_none(Decimal(s))
    except (DecimalException, ValueError):
        # DecimalException, NOT just InvalidOperation: this is the only parser here
        # that does ARITHMETIC (the n / o division), so it can raise `decimal.Overflow`
        # — which is trapped by default context and is a subclass of ArithmeticError,
        # NOT of InvalidOperation. `"1e1000000/1"` raises it. That escaped to
        # `to_split_rows`, which runs OUTSIDE the per-symbol `executemany` try/except,
        # so a single malformed vendor split string aborted the entire run — the exact
        # permanent-wedge mode the write isolation was added to prevent, arriving one
        # step earlier on the parse path. InvalidOperation is itself a DecimalException,
        # so the previous behaviour is fully retained.
        return None


def _finite_or_none(v: Decimal) -> Decimal | None:
    """Drop the Decimal specials before they can reach the DB.

    Postgres does NOT apply a NUMERIC typmod to the special values, so an
    `Infinity` split_ratio is plausibly persistable into NUMERIC(18,6) and would
    then silently poison every downstream split-adjustment multiplication. "NaN/1"
    and a bare "Infinity" both reach here from real EODHD-shaped strings.
    """
    return v if v.is_finite() else None


def _dec(x: Any) -> Decimal | None:
    if x is None:
        return None
    try:
        return _finite_or_none(Decimal(str(x)))
    except InvalidOperation:
        return None


def _d(s: Any) -> date | None:
    try:
        return date.fromisoformat(str(s)[:10]) if s else None
    except (TypeError, ValueError):
        return None


# Row tuple order matches _UPSERT params $1..$8.
_Row = tuple[str, date, str, Decimal | None, Decimal | None, Decimal | None, date | None, date | None]


def to_dividend_rows(raw: Any, symbol: str) -> list[_Row]:
    """EODHD /div payload -> rs_corporate_actions dividend rows. Rows without an
    ex-date (the PK component) are skipped. dividend_amount = unadjustedValue
    (as-paid), falling back to value."""
    rows: list[_Row] = []
    if not isinstance(raw, list):
        return rows
    for r in raw:
        if not isinstance(r, dict):
            continue
        ex = _d(r.get("date"))
        if ex is None:
            continue
        amount = r.get("unadjustedValue")
        if amount is None:
            amount = r.get("value")
        rows.append((
            symbol, ex, "dividend",
            None,                                   # split_ratio
            _dec(amount),                           # dividend_amount
            parse_franking(r.get("franking")),
            _d(r.get("paymentDate")),
            _d(r.get("recordDate")),
        ))
    return rows


def to_split_rows(raw: Any, symbol: str) -> list[_Row]:
    """EODHD /splits payload -> rs_corporate_actions split rows."""
    rows: list[_Row] = []
    if not isinstance(raw, list):
        return rows
    for r in raw:
        if not isinstance(r, dict):
            continue
        ex = _d(r.get("date"))
        if ex is None:
            continue
        rows.append((
            symbol, ex, "split",
            parse_split_ratio(r.get("split")),
            None, None, None, None,                 # dividend_amount, franking, pay, record
        ))
    return rows


async def refresh_corporate_actions(
    client: EODHDClient,
    conn: asyncpg.Connection,
    symbols: list[str],
    *,
    concurrency: int = 8,
    on_rows_written: Callable[[int], None] | None = None,
) -> dict[str, int]:
    """Ingest dividends + splits for `symbols` into rs_corporate_actions.

    `on_rows_written` is called with the running total after each symbol's batch
    lands, so a caller can report partial progress even when the run later aborts on
    the deadline (house style — fundamentals_pit.py's `on_rows_committed`). Aborting
    after substantial partial progress is now an EXPECTED recurring outcome, so a
    caller that only reads the return value reports 0 rows for a run that in fact
    wrote tens of thousands.

    Fetches concurrently (bounded by `concurrency`; the client's own semaphore is the
    hard cap) and writes serially through the single connection (asyncpg connections
    are not concurrency-safe), one batched round-trip PER SYMBOL.

    Durability and restart are DIFFERENT things here, and conflating them has caused
    real planning errors — so, explicitly:

      * DURABILITY is per-symbol. Each `executemany` is its own implicit transaction
        (asyncpg >= 0.22.0), so a symbol's rows land all-or-nothing, and every symbol
        already written stays written when a later one fails.
      * RESTART IS NOT CHECKPOINTED. There is no progress cursor: `jobs/
        sync_corporate_actions.py` re-selects the full symbol list every time, and
        `/div` returns each name's FULL history on every call. A re-run therefore
        repeats every symbol from scratch — it does not resume where it stopped.
        "Idempotent" here means the UPSERT CONVERGES to the same state, NOT that a
        second run is a cheap catch-up. Budget a full run, never a partial one. That
        matters directly inside the 90-minute shared workflow budget.

    Failure accounting is deliberately lenient and slightly optimistic: `failed`
    increments when BOTH endpoints error for a symbol, or when that symbol's write
    fails. A symbol whose dividends fetch failed but whose splits fetch succeeded is
    counted as CLEAN, with its dividend history silently absent for that run.
    """
    sem = asyncio.Semaphore(concurrency)

    async def fetch(sym: str) -> tuple[str, Any, Any]:
        async with sem:
            try:
                div = await client.dividends(sym)
            except Exception:
                log.warning("dividends fetch failed for %s", sym, exc_info=True)
                div = None
            try:
                spl = await client.splits(sym)
            except Exception:
                log.warning("splits fetch failed for %s", sym, exc_info=True)
                spl = None
        return sym, div, spl

    counts = {
        "symbols": len(symbols),
        "dividends": 0,
        "splits": 0,
        "symbols_with_actions": 0,
        "failed": 0,
    }

    # KNOWN DEFERRED ITEM (named 2026-08-17 so it is not rediscovered a third time):
    # `ensure_future` over ALL symbols + `as_completed` is the same unbounded-task-
    # retention shape that financial_statements.py:262-269 documents as its 512Mi OOM
    # cause — every completed task holds its payload for the whole run, so resident
    # memory grows linearly with symbols processed. The Semaphore bounds fetching, not
    # retention. NOT fixed here, deliberately: the severity is genuinely lower on this
    # job (dividend/split payloads are small lists, not multi-MB fundamentals dicts) and
    # the 512Mi Render cap that made it fatal there is gone now this runs on GitHub
    # Actions. The fix, if it is ever wanted, is the bounded-worker queue pool that
    # financial_statements.py already uses. Do not re-diagnose this as new.
    tasks = [asyncio.ensure_future(fetch(s)) for s in symbols]

    deadline = asyncio.timeout(_RUN_DEADLINE_S)
    try:
        # Hard wall-clock deadline (see _RUN_DEADLINE_S) so a systemic upstream stall
        # fails loud, in-window and attributable, rather than silently eating the whole
        # workflow budget and starving every downstream step.
        async with deadline:
            for coro in asyncio.as_completed(tasks):
                sym, div, spl = await coro
                if div is None and spl is None:
                    counts["failed"] += 1
                    continue
                div_rows = to_dividend_rows(div or [], sym)
                spl_rows = to_split_rows(spl or [], sym)
                rows = div_rows + spl_rows
                if not rows:
                    continue
                # Batch this symbol's UPSERTs into ONE executemany round-trip (house
                # style — prices.py::upsert_prices, regulatory.py::upsert_events,
                # financial_statements.py::refresh_financial_statements). The prior
                # per-row `conn.execute` loop issued one serialized network round-trip
                # per row: run 31895667938 (2026-08-15) wrote 30,099 rows in a 5,281s
                # step = 175.5 ms/row measured across the WHOLE step (fetching overlaps
                # writing; the write-only share was ~83 of the 88 min, i.e. ~165 ms/row —
                # the whole-step figure is the one quoted everywhere else here). This is
                # the identical defect fixed in the sibling module on 2026-07-13 at 144
                # ms/row. executemany prepares _UPSERT once and pipelines the rows, so the
                # ON CONFLICT idempotency and the COALESCE never-wipe semantics on
                # franking_pct are byte-for-byte unchanged.
                #
                # PER-SYMBOL, not accumulated across symbols, and that is load-bearing:
                # asyncpg executemany is ONE implicit transaction (requires asyncpg >=
                # 0.22.0, which introduced that guarantee; this repo pins 0.29.0). One
                # batch per symbol — ~1,721 batches of ~17.5 rows for the ~1,721 symbols
                # that carry actions, out of ~2,392 processed — keeps the rollback blast
                # radius to a single symbol. One accumulated 30,099-row batch would make
                # the whole run all-or-nothing.
                try:
                    await conn.executemany(_UPSERT, rows)
                except Exception:
                    # Isolate a poison row to its own symbol. Before batching, per-row
                    # autocommit meant rows 1..k-1 of a bad symbol were already durable;
                    # now the whole symbol rolls back. If that ALSO aborted the run, the
                    # weekly re-run would re-fetch identical data, hit the identical
                    # poison row and roll back again — wedged forever — while every
                    # symbol not yet drained was skipped, nondeterministically (which
                    # ones depends on `as_completed` ordering). Real trigger: EODHD
                    # returning `1e40`, which overflows NUMERIC(18,6). Counting the
                    # symbol failed and continuing keeps one bad symbol from costing the
                    # other ~2,391. Note `except Exception` deliberately does NOT catch
                    # the deadline's CancelledError (a BaseException).
                    # Full traceback for the first few only. Under the SYSTEMIC failure
                    # class (dead connection, revoked grant) every one of ~1,721 symbols
                    # takes this branch, and 1,721 tracebacks bury the run in the Actions
                    # log. The first few identify the fault; the rest are the same one.
                    # The count is what the caller's ratio gate reads, not the log.
                    counts["failed"] += 1
                    if counts["failed"] <= _WRITE_TRACEBACK_LIMIT:
                        log.warning(
                            "corporate-actions write failed for %s", sym, exc_info=True
                        )
                    elif counts["failed"] == _WRITE_TRACEBACK_LIMIT + 1:
                        log.warning(
                            "corporate-actions: further write failures will be counted "
                            "but not traced (limit %d reached)", _WRITE_TRACEBACK_LIMIT
                        )
                    continue
                # Counted only AFTER the write lands, so a failed symbol is never
                # reported as having contributed actions.
                counts["symbols_with_actions"] += 1
                counts["dividends"] += len(div_rows)
                counts["splits"] += len(spl_rows)
                if on_rows_written is not None:
                    on_rows_written(counts["dividends"] + counts["splits"])
    except BaseException as exc:
        # The deadline firing, or cancellation from above, aborts the run. Cancel the
        # outstanding fetches and await them so no orphaned HTTP request outlives the
        # call. (Unlike financial_statements.py's worker pool, `fetch` here closes over
        # `sem`/`client`/`log` only and never touches `conn`, and the loop body runs
        # inline in the caller's own task — so connection safety is structural here, not
        # something this handler provides. Orphaned fetches are its real job.)
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        # `asxos/db.py` sets `command_timeout=30` and asyncpg raises asyncio.TimeoutError,
        # which IS builtin TimeoutError on 3.11+ — so a bare TimeoutError in
        # `job_runs.error_message` cannot distinguish "the run deadline fired" from "one
        # statement took >30s". `deadline.expired()` is the only reliable discriminator.
        # The message carries ints only: no vendor payload, no symbols, no API token.
        if isinstance(exc, TimeoutError) and deadline.expired():
            raise TimeoutError(
                f"run deadline {_RUN_DEADLINE_S}s exceeded; counts={counts}"
            ) from exc
        raise

    return counts
