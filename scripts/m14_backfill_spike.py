#!/usr/bin/env python
"""
M14b backfill spike — one-off, NOT a permanent job.

Fetches 24 months of EODHD /sentiments for active universe symbols (or
--symbols CSV), upserts into signal_sentiment, then joins with the prices
table to compute H1 validation metrics at 5/10/21 trading-day horizons.

Output: scratch/m14_backfill_report.md

H1 gate thresholds (plan Step B7):
  IC < 0.02 across all horizons AND hit rate < 53% → HALT M14c
  IC >= 0.05 at any horizon                         → proceed with M14c
  0.02 <= IC < 0.05                                 → proceed, conservative weight

Usage:
    python scripts/m14_backfill_spike.py
    python scripts/m14_backfill_spike.py --symbols BHP.AU,CBA.AU,RIO.AU
    python scripts/m14_backfill_spike.py --months 18 --dry-run

Requirements: pip install -e ".[ml]"  (brings in scipy via scikit-learn)
Env: DATABASE_URL and EODHD_API_KEY (read from ~/.env.production automatically)
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from datetime import date, timedelta
from pathlib import Path

try:
    import numpy as np
    import pandas as pd
    from scipy.stats import spearmanr
except ImportError as exc:
    sys.exit(f"Missing dependency: {exc}\nRun: pip install -e '.[ml]'")

from asxos.config import settings
from asxos.db import acquire, close_pool, init_pool
from asxos.ingestion.eodhd import get_client
from asxos.ingestion.sentiment import parse_sentiment_response, upsert_sentiment

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger(__name__)

HORIZONS = (5, 10, 21)  # trading-day forward return windows
MIN_OBS = 15             # minimum paired observations to compute IC
OUTPUT_PATH = Path("scratch/m14_backfill_report.md")


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

async def get_active_symbols(conn) -> list[str]:
    """Return all active universe symbols that have at least some price history."""
    rows = await conn.fetch(
        """
        SELECT DISTINCT p.symbol
        FROM prices p
        JOIN universe u ON u.symbol = p.symbol
        WHERE u.is_active = true
        ORDER BY p.symbol
        """
    )
    return [r["symbol"] for r in rows]


async def load_prices(conn, symbols: list[str], from_date: date) -> pd.DataFrame:
    """Load adj_close (falling back to close) for symbols from from_date onward."""
    rows = await conn.fetch(
        """
        SELECT symbol, dt,
               COALESCE(adj_close, close) AS close
        FROM prices
        WHERE symbol = ANY($1)
          AND dt >= $2
          AND COALESCE(adj_close, close) IS NOT NULL
        ORDER BY symbol, dt
        """,
        symbols,
        from_date,
    )
    if not rows:
        return pd.DataFrame(columns=["symbol", "dt", "close"])
    df = pd.DataFrame(rows, columns=["symbol", "dt", "close"])
    df["dt"] = pd.to_datetime(df["dt"])
    df["close"] = df["close"].astype(float)
    return df


async def load_sentiment(conn, symbols: list[str], from_date: date) -> pd.DataFrame:
    """Load signal_sentiment rows for symbols from from_date onward."""
    rows = await conn.fetch(
        """
        SELECT symbol, as_of, sentiment_normalised
        FROM signal_sentiment
        WHERE symbol = ANY($1)
          AND as_of >= $2
        ORDER BY symbol, as_of
        """,
        symbols,
        from_date,
    )
    if not rows:
        return pd.DataFrame(columns=["symbol", "as_of", "sentiment_normalised"])
    df = pd.DataFrame(rows, columns=["symbol", "as_of", "sentiment_normalised"])
    df["as_of"] = pd.to_datetime(df["as_of"])
    df["sentiment_normalised"] = df["sentiment_normalised"].astype(float)
    return df


# ---------------------------------------------------------------------------
# Fetch + store sentiment from EODHD
# ---------------------------------------------------------------------------

async def backfill_symbol(
    client, symbol: str, from_date: str, to_date: str, holdings: set[str], conn
) -> int:
    """Fetch /sentiments for one symbol and upsert. Returns rows stored."""
    try:
        raw = await client.sentiments_for_symbol(symbol, from_date=from_date, to_date=to_date)
        entries = parse_sentiment_response(raw, symbol=symbol, holdings=holdings)
        n = await upsert_sentiment(conn, entries)
        log.info("  %s: fetched %d days of sentiment", symbol, n)
        return n
    except Exception as exc:
        log.warning("  %s: FAILED — %s", symbol, exc)
        return 0


# ---------------------------------------------------------------------------
# IC computation
# ---------------------------------------------------------------------------

def compute_ic_for_symbol(
    symbol: str,
    sent_df: pd.DataFrame,
    price_df: pd.DataFrame,
) -> dict:
    """Compute Spearman IC and hit rate at each horizon for one symbol."""
    result: dict = {"symbol": symbol}

    s = sent_df[sent_df["symbol"] == symbol].set_index("as_of")["sentiment_normalised"]
    p = price_df[price_df["symbol"] == symbol].set_index("dt")["close"].sort_index()

    if s.empty or p.empty:
        for h in HORIZONS:
            result[f"ic_{h}d"] = None
            result[f"hit_{h}d"] = None
            result[f"n_{h}d"] = 0
        result["verdict"] = "NO_DATA"
        return result

    # Sorted price dates as a list for horizon lookup
    price_dates = p.index.tolist()
    price_date_pos = {d: i for i, d in enumerate(price_dates)}

    sentiments, fwd_returns_by_h = [], {h: [] for h in HORIZONS}

    for sent_date, sent_val in s.items():
        # Snap to nearest price date on or after sent_date
        snapped = next(
            (d for d in price_dates if d >= sent_date),
            None,
        )
        if snapped is None:
            continue
        pos = price_date_pos[snapped]
        price_now = p.iloc[pos]
        if price_now <= 0:
            continue

        valid_for_any = False
        for h in HORIZONS:
            fwd_pos = pos + h
            if fwd_pos >= len(price_dates):
                fwd_returns_by_h[h].append(np.nan)
            else:
                fwd_price = p.iloc[fwd_pos]
                if fwd_price > 0:
                    fwd_returns_by_h[h].append(np.log(float(fwd_price) / float(price_now)))
                    valid_for_any = True
                else:
                    fwd_returns_by_h[h].append(np.nan)

        if valid_for_any:
            sentiments.append(float(sent_val))
        else:
            # pop last np.nan for each horizon to keep alignment
            for h in HORIZONS:
                if fwd_returns_by_h[h]:
                    fwd_returns_by_h[h].pop()

    sentiments_arr = np.array(sentiments)
    any_pass = False

    for h in HORIZONS:
        fwd = np.array(fwd_returns_by_h[h])
        mask = ~np.isnan(fwd) & ~np.isnan(sentiments_arr)
        n = int(mask.sum())
        result[f"n_{h}d"] = n

        if n < MIN_OBS:
            result[f"ic_{h}d"] = None
            result[f"hit_{h}d"] = None
            continue

        s_clean = sentiments_arr[mask]
        r_clean = fwd[mask]

        ic, _ = spearmanr(s_clean, r_clean)
        hit = float((np.sign(s_clean) == np.sign(r_clean)).mean())
        result[f"ic_{h}d"] = round(float(ic), 4)
        result[f"hit_{h}d"] = round(hit, 4)
        if abs(ic) >= 0.02:
            any_pass = True

    # Per-symbol verdict
    ic_vals = [result[f"ic_{h}d"] for h in HORIZONS if result[f"ic_{h}d"] is not None]
    if not ic_vals:
        result["verdict"] = "INSUFFICIENT_DATA"
    elif max(abs(v) for v in ic_vals) >= 0.05:
        result["verdict"] = "H1_PASS"
        any_pass = True
    elif max(abs(v) for v in ic_vals) >= 0.02:
        result["verdict"] = "H1_MARGINAL"
    else:
        result["verdict"] = "H1_NULL"

    return result


# ---------------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------------

def write_report(results: list[dict], as_of: date, months: int) -> str:
    """Write markdown report to scratch/ and return path string."""
    OUTPUT_PATH.parent.mkdir(exist_ok=True)

    ic_all = [
        r[f"ic_{h}d"]
        for r in results
        for h in HORIZONS
        if r.get(f"ic_{h}d") is not None
    ]
    hit_all = [
        r[f"hit_{h}d"]
        for r in results
        for h in HORIZONS
        if r.get(f"hit_{h}d") is not None
    ]
    max_ic = max(abs(v) for v in ic_all) if ic_all else None
    avg_hit = sum(hit_all) / len(hit_all) if hit_all else None

    # Aggregate verdict
    if max_ic is None:
        agg_verdict = "⚠️  INSUFFICIENT DATA — run with holdings present"
    elif max_ic >= 0.05:
        agg_verdict = "✅ H1_PASS — proceed with M14c"
    elif max_ic >= 0.02:
        agg_verdict = "🟡 H1_MARGINAL — proceed with conservative weighting"
    else:
        agg_verdict = "🔴 H1_NULL — halt M14c; sentiment signal not detected"

    lines = [
        f"# M14b Backfill Spike Report",
        f"",
        f"**Generated:** {as_of.isoformat()}  ",
        f"**Lookback:** {months} months  ",
        f"**Symbols analysed:** {len(results)}  ",
        f"",
        f"## Aggregate Verdict",
        f"",
        f"{agg_verdict}",
        f"",
        f"| Metric | Value |",
        f"|---|---|",
        f"| Max abs IC (any horizon) | {f'{max_ic:.4f}' if max_ic is not None else 'n/a'} |",
        f"| Avg hit rate | {f'{avg_hit:.1%}' if avg_hit is not None else 'n/a'} |",
        f"| H1_PASS symbols | {sum(1 for r in results if r.get('verdict') == 'H1_PASS')} |",
        f"| H1_MARGINAL symbols | {sum(1 for r in results if r.get('verdict') == 'H1_MARGINAL')} |",
        f"| H1_NULL symbols | {sum(1 for r in results if r.get('verdict') == 'H1_NULL')} |",
        f"| Insufficient data | {sum(1 for r in results if 'DATA' in r.get('verdict', ''))} |",
        f"",
        f"## Per-Symbol Results",
        f"",
        f"| Symbol | IC 5d | IC 10d | IC 21d | Hit 5d | Hit 10d | Hit 21d | n | Verdict |",
        f"|---|---|---|---|---|---|---|---|---|",
    ]

    for r in sorted(results, key=lambda x: x["symbol"]):
        def fmt_ic(v):
            return f"{v:+.4f}" if v is not None else "—"
        def fmt_hit(v):
            return f"{v:.1%}" if v is not None else "—"
        n_min = min(r.get(f"n_{h}d", 0) for h in HORIZONS)
        lines.append(
            f"| {r['symbol']} "
            f"| {fmt_ic(r.get('ic_5d'))} "
            f"| {fmt_ic(r.get('ic_10d'))} "
            f"| {fmt_ic(r.get('ic_21d'))} "
            f"| {fmt_hit(r.get('hit_5d'))} "
            f"| {fmt_hit(r.get('hit_10d'))} "
            f"| {fmt_hit(r.get('hit_21d'))} "
            f"| {n_min} "
            f"| {r.get('verdict', '—')} |"
        )

    lines += [
        f"",
        f"## Gate Thresholds (plan Step B7)",
        f"",
        f"| IC | Outcome |",
        f"|---|---|",
        f"| ≥ 0.05 at any horizon | H1_PASS → proceed with M14c |",
        f"| 0.02–0.05 | H1_MARGINAL → proceed with conservative weighting |",
        f"| < 0.02 all horizons AND hit < 53% | H1_NULL → **halt M14c** |",
        f"",
        f"## Next Steps",
        f"",
    ]

    if max_ic is not None and max_ic >= 0.02:
        lines += [
            f"1. Run `asx sentiment backtest-signoff` to write `m14_backtest_signoff` to decisions.",
            f"2. Wait for `m13_paper_signoff` + `m14_news_signoff` if not yet signed off.",
            f"3. Then run `asx allocator-news signoff` to enable M14c composite score.",
        ]
    else:
        lines += [
            f"1. Sentiment signal not detected at required threshold.",
            f"2. M14a (brief ribbon) continues as display-only indefinitely.",
            f"3. Revisit after 90+ days of live data collection in `signal_sentiment`.",
        ]

    content = "\n".join(lines)
    OUTPUT_PATH.write_text(content)
    return str(OUTPUT_PATH)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def _run(symbols_arg: str | None, months: int, dry_run: bool) -> None:
    today = date.today()
    from_date = today - timedelta(days=months * 30)
    from_date_str = from_date.isoformat()
    to_date_str = today.isoformat()

    await init_pool()
    try:
        async with acquire() as conn:
            if symbols_arg:
                symbols = [s.strip() for s in symbols_arg.split(",") if s.strip()]
                log.info("Using %d symbols from --symbols arg", len(symbols))
            else:
                symbols = await get_active_symbols(conn)
                log.info("Found %d active symbols with price history", len(symbols))

        if not symbols:
            log.warning("No symbols found. Pass --symbols or ensure universe + prices are populated.")
            return

        holdings = set(symbols)

        # --- Phase 1: fetch + store sentiment ---
        if not dry_run:
            log.info("Phase 1: fetching %d months of /sentiments from EODHD...", months)
            client = get_client()

            async with acquire() as conn:
                results_phase1 = await asyncio.gather(
                    *[backfill_symbol(client, s, from_date_str, to_date_str, holdings, conn)
                      for s in symbols],
                    return_exceptions=True,
                )

            total_stored = sum(r for r in results_phase1 if isinstance(r, int))
            errors = sum(1 for r in results_phase1 if isinstance(r, BaseException))
            log.info(
                "Phase 1 done: %d rows stored, %d symbol errors",
                total_stored,
                errors,
            )
        else:
            log.info("--dry-run: skipping EODHD fetch; using existing signal_sentiment rows")

        # --- Phase 2: load from DB and compute IC ---
        log.info("Phase 2: loading sentiment + prices from DB...")
        async with acquire() as conn:
            sent_df = await load_sentiment(conn, symbols, from_date)
            price_df = await load_prices(conn, symbols, from_date)

        log.info(
            "Loaded %d sentiment rows, %d price rows",
            len(sent_df),
            len(price_df),
        )

        if sent_df.empty:
            log.warning("No sentiment data found. Run without --dry-run first.")
            return

        if price_df.empty:
            log.warning("No price data found. Ensure sync_prices has run.")
            return

    finally:
        await close_pool()

    # --- Phase 3: compute IC per symbol ---
    log.info("Phase 3: computing IC at horizons %s...", HORIZONS)
    ic_results = [
        compute_ic_for_symbol(sym, sent_df, price_df)
        for sym in symbols
    ]

    # --- Phase 4: write report ---
    output = write_report(ic_results, today, months)
    log.info("Report written to %s", output)

    # Print aggregate to stdout
    passes = sum(1 for r in ic_results if r.get("verdict") == "H1_PASS")
    marginal = sum(1 for r in ic_results if r.get("verdict") == "H1_MARGINAL")
    nulls = sum(1 for r in ic_results if r.get("verdict") == "H1_NULL")
    insufficient = sum(1 for r in ic_results if "DATA" in r.get("verdict", ""))

    print(f"\n=== M14b Backfill Spike Results ===")
    print(f"Symbols: {len(ic_results)}  |  PASS: {passes}  |  MARGINAL: {marginal}  |  NULL: {nulls}  |  NO_DATA: {insufficient}")
    ic_vals = [r[f"ic_{h}d"] for r in ic_results for h in HORIZONS if r.get(f"ic_{h}d") is not None]
    if ic_vals:
        print(f"Max abs IC: {max(abs(v) for v in ic_vals):.4f}  |  Avg IC: {sum(ic_vals)/len(ic_vals):+.4f}")
    print(f"Full report: {output}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="M14b backfill spike — fetch/analyse sentiment IC")
    parser.add_argument("--symbols", help="Comma-separated symbol list (default: all active universe)")
    parser.add_argument("--months", type=int, default=24, help="Lookback in months (default: 24)")
    parser.add_argument("--dry-run", action="store_true", help="Skip EODHD fetch; use existing DB rows")
    args = parser.parse_args()

    asyncio.run(_run(symbols_arg=args.symbols, months=args.months, dry_run=args.dry_run))


if __name__ == "__main__":
    main()
