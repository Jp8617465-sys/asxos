#!/usr/bin/env python
"""
M14b backfill spike — one-off, NOT a permanent job.

DISCOVERY: EODHD /sentiments returns empty for all ASX symbols on the
current plan tier (Fundamentals Data Feed). However, /news returns
article-level sentiment with a numeric ``polarity`` field on every item.

This spike uses news polarity instead:
  1. Fetch /news (limit=1000) for each symbol → articles with polarity ∈ [-1, +1]
  2. Aggregate to daily mean polarity (volume-weighted by article count)
  3. Join with prices table to compute forward returns
  4. Compute Spearman IC at 5/10/21 trading-day horizons
  5. Write scratch/m14_backfill_report.md

Architectural implication: signal_sentiment should be populated from
news polarity aggregation, not from /sentiments. The ingest_sentiment
job design needs to pivot (plan amendment M14b-REV-K).

H1 gate thresholds (plan Step B7):
  IC < 0.02 across all horizons AND hit rate < 53% → HALT M14c
  IC >= 0.05 at any horizon                         → proceed with M14c
  0.02 <= IC < 0.05                                 → proceed, conservative weight

Usage:
    python3.12 scripts/m14_backfill_spike.py --symbols BHP.AU,CBA.AU,CSL.AU,...
    python3.12 scripts/m14_backfill_spike.py --symbols BHP.AU --months 24 --dry-run

Requirements: numpy, pandas, scipy, asyncpg, httpx, tenacity, pydantic-settings
Env: DATABASE_URL and EODHD_API_KEY (read from ~/Projects/asxos-secrets/.env.production)
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

try:
    import numpy as np
    import pandas as pd
    from scipy.stats import spearmanr
except ImportError as exc:
    sys.exit(f"Missing dependency: {exc}\nRun: pip3.12 install numpy pandas scipy")

from asxos import clock
from asxos.db import acquire, close_pool, init_pool
from asxos.ingestion.eodhd import get_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger(__name__)

HORIZONS = (5, 10, 21)   # trading-day forward return windows
MIN_OBS = 10              # minimum paired observations to compute IC
OUTPUT_PATH = Path("scratch/m14_backfill_report.md")

# Default ASX50 large-caps most likely to have news coverage
DEFAULT_SYMBOLS = (
    "BHP.AU,CBA.AU,CSL.AU,WBC.AU,ANZ.AU,NAB.AU,WES.AU,TLS.AU,RIO.AU,MQG.AU,"
    "TCL.AU,WDS.AU,ALL.AU,GMG.AU,S32.AU,FMG.AU,NCM.AU,WPL.AU,AMP.AU,ASX.AU,"
    "COL.AU,QBE.AU,MPL.AU,IAG.AU,SHL.AU,MIN.AU,TWE.AU,JHX.AU,REA.AU,APX.AU"
)


# ---------------------------------------------------------------------------
# News fetch + polarity extraction
# ---------------------------------------------------------------------------

def _extract_polarity(sentiment) -> float | None:
    """Extract numeric polarity from EODHD sentiment field.

    EODHD returns: {'polarity': -0.953, 'neg': 0.05, 'neu': 0.942, 'pos': 0.008}
    Falls back to string parsing for older response shapes.
    """
    if isinstance(sentiment, dict):
        v = sentiment.get("polarity")
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                pass
    if isinstance(sentiment, str):
        mapping = {"positive": 0.5, "negative": -0.5, "neutral": 0.0}
        return mapping.get(sentiment.lower())
    return None


async def fetch_news_polarity(
    client,
    symbol: str,
    from_date: str,
) -> pd.DataFrame:
    """Fetch news for a symbol, extract polarity, aggregate to daily mean.

    Returns DataFrame with columns: [date, polarity, article_count].
    Empty DataFrame if no news with polarity found — a genuinely quiet symbol.

    Raises ``ValueError`` if the vendor payload is not a list of objects.
    ``news_for_symbol`` no longer coerces a non-list HTTP-200 body to ``[]``
    (that coercion was why a real error envelope could never be classified), so
    this caller must now classify the shape itself. Two failures were otherwise
    reachable here: a dict payload iterates its KEYS, so ``item.get`` raised
    ``AttributeError`` on a str; a scalar raised ``TypeError`` at the ``for``.

    Raising rather than returning an empty frame is the point. An empty frame is
    indistinguishable from a quiet symbol, which is the same
    invalid-looks-like-no-data equivalence the contract change exists to remove.

    The diagnostic carries type names and counts ONLY, never payload contents —
    a vendor error envelope can embed the request URL and its credentials.
    """
    try:
        raw = await client.news_for_symbol(symbol, limit=1000, from_date=from_date)
    except Exception as exc:
        log.warning("  %s: news fetch failed — %s", symbol, type(exc).__name__)
        return pd.DataFrame(columns=["date", "polarity", "article_count"])

    if not isinstance(raw, list):
        raise ValueError(
            f"news_for_symbol({symbol}) returned {type(raw).__name__}, expected list"
        )

    daily: dict[str, list[float]] = defaultdict(list)
    malformed = 0
    for item in raw:
        if not isinstance(item, dict):
            malformed += 1
            continue
        pol = _extract_polarity(item.get("sentiment"))
        if pol is None:
            continue
        dt_str = str(item.get("date") or "")[:10]
        if not dt_str or dt_str < from_date:
            continue
        daily[dt_str].append(pol)

    if malformed:
        # Fail closed on a mixed batch: a schema change landing on SOME articles
        # must not be averaged into a polarity series and presented as signal.
        raise ValueError(
            f"news_for_symbol({symbol}) returned {malformed}/{len(raw)} "
            "non-object items; refusing to derive polarity from a partial batch"
        )

    if not daily:
        return pd.DataFrame(columns=["date", "polarity", "article_count"])

    rows = [
        {"date": dt, "polarity": sum(vals) / len(vals), "article_count": len(vals)}
        for dt, vals in sorted(daily.items())
    ]
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    df["polarity"] = df["polarity"].astype(float)
    return df


# ---------------------------------------------------------------------------
# Price loading
# ---------------------------------------------------------------------------

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

    p = price_df[price_df["symbol"] == symbol].set_index("dt")["close"].sort_index()
    if sent_df.empty or p.empty:
        for h in HORIZONS:
            result[f"ic_{h}d"] = None
            result[f"hit_{h}d"] = None
            result[f"n_{h}d"] = 0
        result["verdict"] = "NO_DATA"
        return result

    # Indexed by date
    s = sent_df.set_index("date")["polarity"]
    price_dates = p.index.tolist()
    price_date_pos = {d: i for i, d in enumerate(price_dates)}

    sentiments: list[float] = []
    fwd_returns_by_h: dict[int, list[float]] = {h: [] for h in HORIZONS}

    for sent_date, sent_val in s.items():
        # Snap to nearest price date on or after sent_date
        snapped = next((d for d in price_dates if d >= sent_date), None)
        if snapped is None:
            continue
        pos = price_date_pos[snapped]
        price_now = p.iloc[pos]
        if price_now <= 0:
            continue

        sentiments.append(float(sent_val))
        for h in HORIZONS:
            fwd_pos = pos + h
            if fwd_pos < len(price_dates):
                fwd_price = p.iloc[fwd_pos]
                fwd_returns_by_h[h].append(
                    np.log(float(fwd_price) / float(price_now)) if fwd_price > 0 else np.nan
                )
            else:
                fwd_returns_by_h[h].append(np.nan)

    sentiments_arr = np.array(sentiments)

    for h in HORIZONS:
        fwd = np.array(fwd_returns_by_h[h])
        mask = ~np.isnan(fwd)
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

    # Per-symbol verdict
    ic_vals = [result[f"ic_{h}d"] for h in HORIZONS if result[f"ic_{h}d"] is not None]
    if not ic_vals:
        result["verdict"] = "INSUFFICIENT_DATA"
    elif max(abs(v) for v in ic_vals) >= 0.05:
        result["verdict"] = "H1_PASS"
    elif max(abs(v) for v in ic_vals) >= 0.02:
        result["verdict"] = "H1_MARGINAL"
    else:
        result["verdict"] = "H1_NULL"

    return result


# ---------------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------------

def write_report(results: list[dict], as_of: date, months: int) -> str:
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

    if max_ic is None:
        agg_verdict = "⚠️  INSUFFICIENT DATA — no paired sentiment+price observations"
    elif max_ic >= 0.05:
        agg_verdict = "✅ H1_PASS — proceed with M14c (full composite score integration)"
    elif max_ic >= 0.02:
        agg_verdict = "🟡 H1_MARGINAL — proceed with conservative weighting"
    else:
        agg_verdict = "🔴 H1_NULL — no sentiment signal detected; halt M14c"

    lines = [
        "# M14b Backfill Spike Report",
        "",
        f"**Generated:** {as_of.isoformat()}  ",
        f"**Lookback:** {months} months  ",
        "**Signal source:** EODHD /news polarity (not /sentiments — no ASX coverage on plan tier)  ",
        f"**Symbols analysed:** {len(results)}  ",
        "",
        "## ⚠️  Architecture Finding",
        "",
        "EODHD `/sentiments` endpoint returns **empty for all ASX symbols** on the current",
        "Fundamentals Data Feed plan. `/news` items include a numeric `polarity` score",
        "(`{'polarity': float, 'neg': float, 'neu': float, 'pos': float}`) on every article.",
        "",
        "**Recommendation (plan amendment M14b-REV-K):**",
        "- Add `sentiment_polarity NUMERIC(8,6)` column to `holding_news`",
        "- Store the raw numeric polarity at ingest time (already available in news items)",
        "- Nightly aggregation query: `INSERT INTO signal_sentiment` from daily mean polarity",
        "  grouped from `holding_news` (replaces the `/sentiments` API call in `ingest_sentiment.py`)",
        "- `ingest_sentiment.py` can be repurposed or replaced with a post-ingest aggregation step",
        "",
        "## Aggregate Verdict",
        "",
        agg_verdict,
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Max abs IC (any horizon) | {f'{max_ic:.4f}' if max_ic is not None else 'n/a'} |",
        f"| Avg hit rate | {f'{avg_hit:.1%}' if avg_hit is not None else 'n/a'} |",
        f"| H1_PASS symbols | {sum(1 for r in results if r.get('verdict') == 'H1_PASS')} |",
        f"| H1_MARGINAL symbols | {sum(1 for r in results if r.get('verdict') == 'H1_MARGINAL')} |",
        f"| H1_NULL symbols | {sum(1 for r in results if r.get('verdict') == 'H1_NULL')} |",
        f"| Insufficient data | {sum(1 for r in results if 'DATA' in r.get('verdict', ''))} |",
        "",
        "## Per-Symbol Results",
        "",
        "| Symbol | IC 5d | IC 10d | IC 21d | Hit 5d | Hit 10d | Hit 21d | n | Verdict |",
        "|---|---|---|---|---|---|---|---|---|",
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
        "",
        "## Gate Thresholds (plan Step B7)",
        "",
        "| IC | Outcome |",
        "|---|---|",
        "| ≥ 0.05 at any horizon | H1_PASS → proceed with M14c |",
        "| 0.02–0.05 | H1_MARGINAL → proceed with conservative weighting |",
        "| < 0.02 all horizons AND hit < 53% | H1_NULL → halt M14c |",
        "",
        "## Next Steps",
        "",
    ]

    if max_ic is not None and max_ic >= 0.02:
        lines += [
            "1. Implement M14b-REV-K: add `sentiment_polarity` to `holding_news` + nightly aggregation.",
            "2. Run `asx sentiment backtest-signoff` once M14b-REV-K is live and re-validated.",
            "3. Wait for `m13_paper_signoff` + `m14_news_signoff` before running `asx allocator-news signoff`.",
        ]
    else:
        lines += [
            "1. No sentiment signal detected at H1 threshold.",
            "2. M14a (brief ribbon) continues display-only indefinitely.",
            "3. Revisit after holdings are populated and 90+ days of news polarity data collected.",
        ]

    content = "\n".join(lines)
    OUTPUT_PATH.write_text(content)
    return str(OUTPUT_PATH)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def _run(symbols_arg: str | None, months: int, dry_run: bool) -> None:
    today = clock.today()
    from_date = today - timedelta(days=months * 30)
    from_date_str = from_date.isoformat()

    await init_pool()
    try:
        async with acquire() as conn:
            if symbols_arg:
                symbols = [s.strip() for s in symbols_arg.split(",") if s.strip()]
                log.info("Using %d symbols from --symbols arg", len(symbols))
            else:
                symbols = [s.strip() for s in DEFAULT_SYMBOLS.split(",") if s.strip()]
                log.info("Using default ASX large-cap list: %d symbols", len(symbols))

        if not symbols:
            log.warning("No symbols to analyse.")
            return

        # --- Phase 1: fetch news polarity from EODHD ---
        sentiment_by_symbol: dict[str, pd.DataFrame] = {}

        if not dry_run:
            log.info("Phase 1: fetching news polarity for %d symbols...", len(symbols))
            client = get_client()

            async def _fetch(symbol: str) -> tuple[str, pd.DataFrame]:
                df = await fetch_news_polarity(client, symbol, from_date_str)
                log.info(
                    "  %s: %d daily polarity observations (%d articles)",
                    symbol,
                    len(df),
                    int(df["article_count"].sum()) if not df.empty else 0,
                )
                return symbol, df

            results_phase1 = await asyncio.gather(
                *[_fetch(s) for s in symbols],
                return_exceptions=True,
            )
            for result in results_phase1:
                if isinstance(result, BaseException):
                    log.warning("Unexpected error: %s", result)
                else:
                    sym, df = result
                    sentiment_by_symbol[sym] = df
        else:
            log.info("--dry-run: skipping EODHD fetch")
            for s in symbols:
                sentiment_by_symbol[s] = pd.DataFrame(columns=["date", "polarity", "article_count"])

        # --- Phase 2: load prices from DB ---
        log.info("Phase 2: loading prices from DB...")
        async with acquire() as conn:
            price_df = await load_prices(conn, symbols, from_date)
        log.info("Loaded %d price rows", len(price_df))

    finally:
        await close_pool()

    if price_df.empty:
        log.warning("No price data found. Ensure sync_prices has run.")
        return

    # --- Phase 3: compute IC per symbol ---
    log.info("Phase 3: computing IC at horizons %s...", HORIZONS)
    ic_results = [
        compute_ic_for_symbol(sym, sentiment_by_symbol.get(sym, pd.DataFrame()), price_df)
        for sym in symbols
    ]

    # --- Phase 4: write report ---
    output = write_report(ic_results, today, months)
    log.info("Report written to %s", output)

    passes = sum(1 for r in ic_results if r.get("verdict") == "H1_PASS")
    marginal = sum(1 for r in ic_results if r.get("verdict") == "H1_MARGINAL")
    nulls = sum(1 for r in ic_results if r.get("verdict") == "H1_NULL")
    insufficient = sum(1 for r in ic_results if "DATA" in r.get("verdict", ""))

    print("\n=== M14b Backfill Spike Results ===")
    print(f"Symbols: {len(ic_results)}  |  PASS: {passes}  |  MARGINAL: {marginal}  |  NULL: {nulls}  |  NO_DATA: {insufficient}")
    ic_vals = [r[f"ic_{h}d"] for r in ic_results for h in HORIZONS if r.get(f"ic_{h}d") is not None]
    if ic_vals:
        print(f"Max abs IC: {max(abs(v) for v in ic_vals):.4f}  |  Avg IC: {sum(ic_vals)/len(ic_vals):+.4f}")
    print(f"Full report: {output}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="M14b backfill spike — news polarity IC validation")
    parser.add_argument(
        "--symbols",
        help="Comma-separated symbols (default: ASX30 large-caps)",
    )
    parser.add_argument("--months", type=int, default=24, help="Lookback in months (default: 24)")
    parser.add_argument("--dry-run", action="store_true", help="Skip EODHD fetch")
    args = parser.parse_args()
    asyncio.run(_run(symbols_arg=args.symbols, months=args.months, dry_run=args.dry_run))


if __name__ == "__main__":
    main()
