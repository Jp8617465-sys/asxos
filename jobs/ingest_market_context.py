"""
Daily market context ingest — M-Market-Context.

Runs at 20:45 UTC (Sun-Thu) — before generate_signals (20:50).

Pipeline:
  1. Compute breadth indicators from local prices table
  2. Fetch ASX200 close + AVIX + AUD/USD + VIX from EODHD
  3. Fetch US HY OAS + 10y-2y spread + AUS rate via FREDClient
  4. Classify regime
  5. INSERT row into market_context (append-only)

Hard-fail: asx200_close, avix, us_hy_oas missing → job exits non-zero.
Soft-degrade: other indicators missing → ingestion_warnings JSONB populated.
"""
from __future__ import annotations

import asyncio
import json
import os
from datetime import date
from decimal import Decimal, InvalidOperation

from asxos.clients.fred import get_client as get_fred_client
from asxos.db import acquire, close_pool, init_pool
from asxos.domain.regime.classifier import CLASSIFIER_VERSION, classify
from asxos.ingestion.eodhd import get_client as get_eodhd_client
from asxos.jobs.utils.job_monitor import JobMonitor


def _to_dec(v: object) -> Decimal | None:
    if v is None:
        return None
    try:
        return Decimal(str(v))
    except InvalidOperation:
        return None


async def _compute_breadth(conn, as_of: date) -> dict[str, Decimal | None]:
    """Compute breadth from the local prices table for the given date."""
    row = await conn.fetchrow(
        """
        WITH latest AS (
            -- Most recent close for each active symbol on or before as_of
            SELECT DISTINCT ON (p.symbol)
                   p.symbol,
                   p.close,
                   p.dt
            FROM   prices p
            JOIN   universe u ON u.symbol = p.symbol AND u.is_active
            WHERE  p.dt <= $1
            ORDER  BY p.symbol, p.dt DESC
        ),
        ma50 AS (
            SELECT p.symbol, AVG(p.close) AS avg_close
            FROM   prices p
            JOIN   universe u ON u.symbol = p.symbol AND u.is_active
            WHERE  p.dt BETWEEN ($1 - INTERVAL '70 days')::date AND $1
            GROUP  BY p.symbol
            HAVING COUNT(*) >= 40
        ),
        ma200 AS (
            SELECT p.symbol, AVG(p.close) AS avg_close
            FROM   prices p
            JOIN   universe u ON u.symbol = p.symbol AND u.is_active
            WHERE  p.dt BETWEEN ($1 - INTERVAL '290 days')::date AND $1
            GROUP  BY p.symbol
            HAVING COUNT(*) >= 180
        ),
        highs10 AS (
            SELECT p.symbol,
                   MAX(p.high) = p.close AS new_high,
                   MIN(p.low)  = p.close AS new_low
            FROM   prices p
            JOIN   universe u ON u.symbol = p.symbol AND u.is_active
            WHERE  p.dt BETWEEN ($1 - INTERVAL '10 days')::date AND $1
            GROUP  BY p.symbol, p.close
        )
        SELECT
            COUNT(l.symbol)                                              AS total,
            COALESCE(SUM(CASE WHEN l.close > m50.avg_close THEN 1 END), 0) AS above_50,
            COALESCE(SUM(CASE WHEN l.close > m200.avg_close THEN 1 END), 0) AS above_200,
            COALESCE(SUM(CASE WHEN h.new_high THEN 1 END), 0)           AS new_highs,
            COALESCE(SUM(CASE WHEN h.new_low THEN 1 END), 0)            AS new_lows
        FROM latest l
        LEFT JOIN ma50  ON ma50.symbol  = l.symbol
        LEFT JOIN ma200 ON ma200.symbol = l.symbol
        LEFT JOIN highs10 h ON h.symbol = l.symbol
        """,
        as_of,
    )
    if row is None or row["total"] == 0:
        return {
            "pct_above_50d_ma": None,
            "pct_above_200d_ma": None,
            "net_new_highs_lows_10d": None,
        }
    total = Decimal(str(row["total"]))
    return {
        "pct_above_50d_ma": (Decimal(str(row["above_50"])) / total).quantize(Decimal("0.000001")),
        "pct_above_200d_ma": (Decimal(str(row["above_200"])) / total).quantize(Decimal("0.000001")),
        "net_new_highs_lows_10d": (
            (Decimal(str(row["new_highs"])) - Decimal(str(row["new_lows"]))) / total
        ).quantize(Decimal("0.000001")),
    }


async def _fetch_avix_history(eodhd, as_of: date, days: int = 35) -> list[Decimal]:
    """Return recent AVIX closes (newest-first) for band-position computation."""
    from_date = (as_of.toordinal() - days)
    from_str = date.fromordinal(from_date).isoformat()
    rows = await eodhd.daily_prices("AVIX.INDX.AU", from_date=from_str)
    closes = []
    for r in sorted(rows, key=lambda x: x.get("date", ""), reverse=True):
        raw = r.get("adjusted_close") or r.get("close")
        v = _to_dec(raw)
        if v is not None:
            closes.append(v)
    return closes


async def _fetch_eodhd_indicators(
    as_of: date,
) -> tuple[dict[str, Decimal | None], list[dict]]:
    """Fetch ASX200, AVIX, AUD/USD, VIX, iron ore from EODHD."""
    eodhd = get_eodhd_client()
    warnings: list[dict] = []
    result: dict[str, Decimal | None] = {
        "asx200_close": None,
        "asx200_daily_change_pct": None,
        "avix": None,
        "avix_5d_change_pct": None,
        "avix_30d_band_pos": None,
        "aud_usd": None,
        "vix": None,
        "iron_ore_62fe": None,
    }

    from_str = as_of.isoformat()

    async def _latest(symbol: str) -> list[dict]:
        try:
            rows = await eodhd.daily_prices(symbol, from_date=from_str)
            return sorted(rows, key=lambda x: x.get("date", ""), reverse=True)
        except Exception as exc:
            warnings.append({"source": symbol, "status": "fetch_failed", "detail": str(exc)})
            return []

    asx200_rows, avix_rows, audusd_rows, vix_rows, iron_rows = await asyncio.gather(
        _latest("AXJO.INDX"),
        _latest("AVIX.INDX.AU"),
        _latest("AUDUSD.FOREX"),
        _latest("VIX.US"),
        _latest("IRON.COMM"),
        return_exceptions=False,
    )

    # ASX200
    if asx200_rows:
        latest = asx200_rows[0]
        result["asx200_close"] = _to_dec(latest.get("adjusted_close") or latest.get("close"))
        prev_close = _to_dec(asx200_rows[1].get("adjusted_close") or asx200_rows[1].get("close")) if len(asx200_rows) > 1 else None
        if result["asx200_close"] and prev_close:
            result["asx200_daily_change_pct"] = (
                (result["asx200_close"] - prev_close) / prev_close * 100
            ).quantize(Decimal("0.000001"))
    else:
        warnings.append({"source": "AXJO.INDX", "status": "no_data", "detail": "no rows returned"})

    # AVIX
    if avix_rows:
        avix_vals = [_to_dec(r.get("adjusted_close") or r.get("close")) for r in avix_rows]
        avix_vals = [v for v in avix_vals if v is not None]
        if avix_vals:
            result["avix"] = avix_vals[0]
            if len(avix_vals) >= 5:
                result["avix_5d_change_pct"] = (
                    (avix_vals[0] - avix_vals[4]) / avix_vals[4] * 100
                ).quantize(Decimal("0.000001"))
            if len(avix_vals) >= 30:
                lo = min(avix_vals[:30])
                hi = max(avix_vals[:30])
                if hi != lo:
                    result["avix_30d_band_pos"] = (
                        (avix_vals[0] - lo) / (hi - lo)
                    ).quantize(Decimal("0.000001"))
    else:
        warnings.append({"source": "AVIX.INDX.AU", "status": "no_data", "detail": "no rows returned"})

    # AUD/USD
    if audusd_rows:
        r = audusd_rows[0]
        result["aud_usd"] = _to_dec(r.get("adjusted_close") or r.get("close"))

    # VIX
    if vix_rows:
        r = vix_rows[0]
        result["vix"] = _to_dec(r.get("adjusted_close") or r.get("close"))

    # Iron ore
    if iron_rows:
        r = iron_rows[0]
        result["iron_ore_62fe"] = _to_dec(r.get("adjusted_close") or r.get("close"))

    return result, warnings


async def _fetch_fred_indicators(as_of: date) -> tuple[dict[str, Decimal | None], list[dict]]:
    """Fetch US HY OAS, 10y-2y spread, AUS 10y yield, RBA rate from FRED."""
    fred = get_fred_client()
    warnings: list[dict] = []
    result: dict[str, Decimal | None] = {
        "us_hy_oas": None,
        "us_10y_2y_spread": None,
        "aus_10y_yield": None,
        "rba_cash_rate": None,
    }

    async def _get(series_id: str, key: str) -> None:
        try:
            val = await fred.latest_value(series_id)
            result[key] = val
            if val is None:
                warnings.append({"source": series_id, "status": "no_data", "detail": "all recent values missing"})
        except Exception as exc:
            warnings.append({"source": series_id, "status": "fetch_failed", "detail": str(exc)})

    await asyncio.gather(
        _get("BAMLH0A0HYM2", "us_hy_oas"),
        _get("T10Y2Y", "us_10y_2y_spread"),
        _get("IRLTLT01AUM156N", "aus_10y_yield"),
        _get("AUCBCNTO", "rba_cash_rate"),
    )

    return result, warnings


async def _run(as_of: date) -> None:
    healthcheck_url = os.environ.get("HEALTHCHECK_URL_INGEST_MARKET_CONTEXT", "")

    await init_pool()
    try:
        async with JobMonitor("ingest_market_context", as_of, healthcheck_url) as monitor:
            async with acquire() as conn:
                # Compute breadth from local prices
                breadth = await _compute_breadth(conn, as_of)

            # Fetch external data concurrently
            (eodhd_indicators, eodhd_warnings), (fred_indicators, fred_warnings) = await asyncio.gather(
                _fetch_eodhd_indicators(as_of),
                _fetch_fred_indicators(as_of),
            )

            all_warnings = eodhd_warnings + fred_warnings

            # Hard-fail on missing critical indicators
            asx200_close = eodhd_indicators["asx200_close"]
            avix = eodhd_indicators["avix"]
            us_hy_oas = fred_indicators["us_hy_oas"]

            if asx200_close is None:
                raise RuntimeError(
                    f"ingest_market_context: asx200_close is None for {as_of}. "
                    "Cannot proceed without ASX200 close."
                )
            if avix is None:
                raise RuntimeError(
                    f"ingest_market_context: avix is None for {as_of}. "
                    "Cannot proceed without AVIX."
                )
            if us_hy_oas is None:
                raise RuntimeError(
                    f"ingest_market_context: us_hy_oas is None for {as_of}. "
                    "Cannot proceed without US HY OAS credit indicator."
                )

            # Classify regime
            indicators = {**breadth, **eodhd_indicators, **fred_indicators}
            label, conditions = classify(indicators)
            rationale = [
                {
                    "name": c.name,
                    "fired": c.fired,
                    "value": str(c.value) if c.value is not None else None,
                    "threshold": str(c.threshold) if c.threshold is not None else None,
                    "classifier_version": CLASSIFIER_VERSION,
                }
                for c in conditions
            ]

            # INSERT (append-only)
            async with acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO market_context (
                        as_of,
                        asx200_close, asx200_daily_change_pct,
                        pct_above_50d_ma, pct_above_200d_ma, net_new_highs_lows_10d,
                        avix, avix_5d_change_pct, avix_30d_band_pos,
                        rba_cash_rate, aud_usd, aus_10y_yield, iron_ore_62fe,
                        us_hy_oas, us_10y_2y_spread, vix,
                        regime_label, regime_rationale, ingestion_warnings
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9,
                        $10, $11, $12, $13, $14, $15, $16, $17, $18, $19
                    )
                    """,
                    as_of,
                    asx200_close,
                    eodhd_indicators["asx200_daily_change_pct"],
                    breadth["pct_above_50d_ma"],
                    breadth["pct_above_200d_ma"],
                    breadth["net_new_highs_lows_10d"],
                    avix,
                    eodhd_indicators["avix_5d_change_pct"],
                    eodhd_indicators["avix_30d_band_pos"],
                    fred_indicators["rba_cash_rate"],
                    eodhd_indicators["aud_usd"],
                    fred_indicators["aus_10y_yield"],
                    eodhd_indicators["iron_ore_62fe"],
                    us_hy_oas,
                    fred_indicators["us_10y_2y_spread"],
                    eodhd_indicators["vix"],
                    label.value,
                    json.dumps(rationale),
                    json.dumps(all_warnings),
                )
                monitor.rows_written = 1
    finally:
        await close_pool()


if __name__ == "__main__":
    asyncio.run(_run(date.today()))
