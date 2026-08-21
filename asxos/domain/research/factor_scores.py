"""Sector-neutral factor scores — research store ``rs_factor_scores`` (M14, Layer-1).

The Layer-1 alpha input. For a cross-section date ``as_of`` it computes, per symbol,
five **sector-neutral z-scored** factor categories (value / quality / momentum /
low-vol / yield) and a value×quality ``composite`` — the candidate sleeve the audit
named, which is TESTED (never crowned) by ``alpha_eval`` once enough history exists.

Leak-safety (the whole point of the research store)
---------------------------------------------------
Every input is taken **as it was knowable at ``as_of``**, never by ``as_of`` of the
underlying fact:

* Fundamentals: the LATEST ``rs_fundamentals_pit`` row per symbol with
  ``knowledge_date <= as_of`` (``knowledge_date`` is the guarded disclosure date
  from ``derive_knowledge_date`` — future/scheduled statements were already dropped
  upstream). We re-filter on it here so a re-run at a historical ``as_of`` is exact.
* Prices: only rows with ``dt <= as_of`` (EOD bars; no intraday look-ahead).

Sector neutrality
-----------------
Each raw sub-factor is z-scored **within its GICS/Morningstar sector** (sourced from
``rs_security_master.gics_sector``, populated by the financial-statements enrichment
pass). A sub-factor with a degenerate group (size < 2 or zero dispersion) contributes
a z of 0 — it cannot discriminate, so it is neither a tailwind nor a headwind. z's are
winsorized to ``[-WINSOR, WINSOR]`` before blending. A category score is the mean of
its present sub-factor z's; ``n_factors_present`` counts the categories that had any.

Reads the research store (+ production ``prices`` for market data, the same source
``alpha_loader`` already uses) and writes only ``rs_factor_scores``. Never touches
``universe``. Research module — plain ``float`` stats are appropriate here (these are
dimensionless ranking scores, not money), unlike the Decimal-only portfolio domain.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from itertools import pairwise
from math import log
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import asyncpg

FACTOR_SET_VERSION = "fs_v1"

# Winsorization clamp on z-scores (in std units) before blending — caps a single
# extreme name from dominating a thin sector.
WINSOR = 3.0

# Australian company tax rate for franking gross-up (yield factor). franking credit
# = cash_dividend * franking_pct * rate/(1-rate). 30% is the full rate; the system is
# franking-credit aware (CLAUDE.md #7 / spec §7) but this is a research ranking input,
# not a tax computation.
_CORP_TAX_RATE = Decimal("0.30")
_GROSS_UP = _CORP_TAX_RATE / (Decimal("1") - _CORP_TAX_RATE)  # 0.428571...

# Momentum: 12-1 month residual-free total return (skip the most recent month to avoid
# 1-month reversal). In trading days: ~252 back to ~21 back.
_MOM_LONG_TD = 252
_MOM_SKIP_TD = 21
# Low-vol: realised daily-return stdev over this many recent trading days.
_VOL_WINDOW_TD = 120
# Price window to fetch (calendar days) — must cover _MOM_LONG_TD trading days.
_PRICE_WINDOW_DAYS = 420

# The five categories and the raw sub-factors that compose each. Sub-factor values are
# "higher is better" AFTER the sign normalisation applied when they are computed
# (cheaper value, lower vol → larger score).
_CATEGORIES: dict[str, list[str]] = {
    "value": ["earnings_yield", "book_yield"],
    "quality": ["roe", "roa", "gross_margin", "operating_margin"],
    "momentum": ["mom_12_1"],
    "low_vol": ["neg_vol"],
    "yield": ["gross_yield"],
}
# composite = the value×quality candidate (audit §3 row 10): the thing under test.
_COMPOSITE_CATEGORIES = ("value", "quality")


# ---------------------------------------------------------------------------
# Pure raw-factor computation (per symbol)
# ---------------------------------------------------------------------------


def _f(x: Any) -> float | None:
    """Coerce a Decimal/str/number to float; None/blank → None."""
    if x is None or x == "":
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _ratio(a: float | None, b: float | None) -> float | None:
    """a/b with a None/zero-denominator guard."""
    if a is None or b is None or b == 0:
        return None
    return a / b


def momentum_12_1(adj_closes: list[float]) -> float | None:
    """12-1 month total return from an ascending adj_close series.

    Needs at least ``_MOM_LONG_TD + 1`` points. Uses the price ~21 trading days back
    over the price ~252 trading days back, so the most recent month is excluded.
    Returns ``None`` when the series is too short or a referenced price is non-positive.
    """
    n = len(adj_closes)
    if n < _MOM_LONG_TD + 1:
        return None
    recent = adj_closes[-1 - _MOM_SKIP_TD]
    old = adj_closes[-1 - _MOM_LONG_TD]
    if old <= 0 or recent <= 0:
        return None
    return recent / old - 1.0


def neg_realised_vol(adj_closes: list[float]) -> float | None:
    """Negative realised daily log-return stdev over the last ``_VOL_WINDOW_TD`` days.

    Sign-flipped so that *lower* volatility scores *higher* (the low-vol factor).
    Returns ``None`` with fewer than ~20 usable returns.
    """
    window = adj_closes[-(_VOL_WINDOW_TD + 1):]
    rets: list[float] = []
    for prev, cur in pairwise(window):
        if prev > 0 and cur > 0:
            rets.append(log(cur / prev))
    if len(rets) < 20:
        return None
    return -statistics.pstdev(rets)


def gross_franked_yield(
    dividend_ttm: float | None, franking_avg_pct: float | None, price: float | None
) -> float | None:
    """Grossed-up franked dividend yield (cash yield + franking credit), per price.

    ``franking_avg_pct`` is a 0–100 percentage (NULL≠0 — a missing franking is not an
    unfranked dividend; treated as 0 credit only when the dividend itself is present).
    """
    if dividend_ttm is None or price is None or price <= 0:
        return None
    frank = (franking_avg_pct or 0.0) / 100.0
    credit = dividend_ttm * frank * float(_GROSS_UP)
    return (dividend_ttm + credit) / price


def raw_factors(
    *,
    eps_ttm: Any,
    book_value_ps: Any,
    roe: Any,
    roa: Any,
    gross_margin: Any,
    operating_margin: Any,
    dividend_ttm: Any,
    franking_avg_pct: Any,
    close: float | None,
    adj_closes: list[float],
) -> dict[str, float | None]:
    """All raw sub-factor values for one symbol (``None`` where inputs are missing).

    Value sub-factors are *yields* (inverse of price multiples) so higher = cheaper =
    better, matching the "higher is better" convention every sub-factor shares.
    """
    return {
        "earnings_yield": _ratio(_f(eps_ttm), close),
        "book_yield": _ratio(_f(book_value_ps), close),
        "roe": _f(roe),
        "roa": _f(roa),
        "gross_margin": _f(gross_margin),
        "operating_margin": _f(operating_margin),
        "mom_12_1": momentum_12_1(adj_closes),
        "neg_vol": neg_realised_vol(adj_closes),
        "gross_yield": gross_franked_yield(_f(dividend_ttm), _f(franking_avg_pct), close),
    }


# ---------------------------------------------------------------------------
# Pure sector-neutral scoring (cross-section)
# ---------------------------------------------------------------------------


@dataclass
class SymbolScore:
    symbol: str
    sector: str | None
    market_cap_aud: float | None
    value_score: float | None = None
    quality_score: float | None = None
    momentum_score: float | None = None
    low_vol_score: float | None = None
    yield_score: float | None = None
    composite_score: float | None = None
    n_factors_present: int = 0
    raw: dict[str, float | None] = field(default_factory=dict)


_CATEGORY_FIELD = {
    "value": "value_score",
    "quality": "quality_score",
    "momentum": "momentum_score",
    "low_vol": "low_vol_score",
    "yield": "yield_score",
}


def _winsor(z: float) -> float:
    return max(-WINSOR, min(WINSOR, z))


def _zscores(values: dict[str, float | None]) -> dict[str, float]:
    """z-score a {key: value} map over its NON-None members.

    Degenerate group (n < 2 or zero stdev) → all present members get z = 0 (the factor
    cannot discriminate within the group). Keys with a None value are omitted.
    """
    present = {k: v for k, v in values.items() if v is not None}
    if len(present) < 2:
        return {k: 0.0 for k in present}
    mean = statistics.fmean(present.values())
    sd = statistics.pstdev(present.values())
    if sd == 0:
        return {k: 0.0 for k in present}
    return {k: _winsor((v - mean) / sd) for k, v in present.items()}


def sector_neutral_scores(rows: list[SymbolScore]) -> list[SymbolScore]:
    """Populate category + composite scores on ``rows`` in place, sector by sector.

    Each sub-factor is z-scored within its sector group; a category score is the mean
    of its present sub-factor z's; the composite is the mean of the value & quality
    category scores (the value×quality candidate). Symbols with a NULL/blank sector are
    grouped under a single ``"__none__"`` bucket so they are still scored relative to
    each other rather than dropped — flagged by the absent sector in the output row.
    """
    by_sector: dict[str, list[SymbolScore]] = {}
    for r in rows:
        by_sector.setdefault(r.sector or "__none__", []).append(r)

    all_subfactors = [sf for subs in _CATEGORIES.values() for sf in subs]
    for group in by_sector.values():
        # z-score every sub-factor across this sector group.
        z_by_sub: dict[str, dict[str, float]] = {}
        for sf in all_subfactors:
            z_by_sub[sf] = _zscores({r.symbol: r.raw.get(sf) for r in group})
        for r in group:
            present_categories = 0
            for cat, subs in _CATEGORIES.items():
                zs = [z_by_sub[sf][r.symbol] for sf in subs if r.symbol in z_by_sub[sf]]
                score = statistics.fmean(zs) if zs else None
                setattr(r, _CATEGORY_FIELD[cat], score)
                if score is not None:
                    present_categories += 1
            r.n_factors_present = present_categories
            comp = [
                getattr(r, _CATEGORY_FIELD[c])
                for c in _COMPOSITE_CATEGORIES
                if getattr(r, _CATEGORY_FIELD[c]) is not None
            ]
            r.composite_score = statistics.fmean(comp) if comp else None
    return rows


# ---------------------------------------------------------------------------
# DB orchestration (leak-safe loads → compute → idempotent UPSERT)
# ---------------------------------------------------------------------------

# Hybrid/capital-note security_type values excluded below (matches
# asxos/ingestion/universe.py's _TYPE_TO_KIND "hybrid" mapping and
# jobs/sync_financial_statements.py's _HYBRID_SECURITY_TYPES). A bank hybrid
# note carries its parent's whole income statement under its own symbol
# (e.g. CBAPI.AU reports CBA group net income) -- unfiltered, this materially
# inflated a naive Financials-segment aggregate (2026-08-18 segment-valuation
# architecture doc, D2). Hardcoded literals rather than a bind parameter:
# fixed, small, non-user-supplied set, and it avoids renumbering the
# existing conditional $2/$3 symbol-filter parameters below.
_PIT_SQL = """
SELECT DISTINCT ON (p.symbol)
       p.symbol, p.eps_ttm, p.book_value_ps, p.roe, p.roa, p.gross_margin,
       p.operating_margin, p.dividend_ttm, p.franking_avg_pct, p.shares_outstanding,
       p.knowledge_date, s.gics_sector AS sector
FROM rs_fundamentals_pit p
JOIN rs_security_master s ON s.symbol = p.symbol
WHERE p.knowledge_date <= $1
  AND (s.security_type IS NULL OR s.security_type NOT IN ('Preferred Stock', 'Notes', 'BOND')){filt}
ORDER BY p.symbol, p.knowledge_date DESC
"""

_PRICE_SQL = """
SELECT symbol, dt, close, adj_close
FROM prices
WHERE adj_close IS NOT NULL AND close IS NOT NULL
  AND dt <= $1 AND dt > $2{filt}
ORDER BY symbol, dt
"""

_UPSERT = """
INSERT INTO rs_factor_scores
    (symbol, as_of, factor_set_version, sector, market_cap_aud, value_score,
     quality_score, momentum_score, low_vol_score, yield_score, composite_score,
     n_factors_present, computed_at)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, now())
ON CONFLICT (symbol, as_of, factor_set_version) DO UPDATE SET
    sector            = EXCLUDED.sector,
    market_cap_aud    = EXCLUDED.market_cap_aud,
    value_score       = EXCLUDED.value_score,
    quality_score     = EXCLUDED.quality_score,
    momentum_score    = EXCLUDED.momentum_score,
    low_vol_score     = EXCLUDED.low_vol_score,
    yield_score       = EXCLUDED.yield_score,
    composite_score   = EXCLUDED.composite_score,
    n_factors_present = EXCLUDED.n_factors_present,
    computed_at       = now()
"""


def _q6(x: float | None) -> Decimal | None:
    """Quantise a float score to NUMERIC(18,6). None passes through."""
    if x is None:
        return None
    return Decimal(str(x)).quantize(Decimal("0.000001"))


async def refresh_factor_scores(
    conn: asyncpg.Connection,
    *,
    as_of: date,
    symbols: list[str] | None = None,
    factor_set_version: str = FACTOR_SET_VERSION,
) -> dict[str, int]:
    """Compute and UPSERT ``rs_factor_scores`` for the cross-section at ``as_of``.

    Idempotent on ``(symbol, as_of, factor_set_version)``. Reads only the research
    store + ``prices``; writes only ``rs_factor_scores``. A symbol with neither
    fundamentals nor a usable price contributes nothing.
    """
    filt = " AND p.symbol = ANY($2)" if symbols else ""
    pit_args: list[Any] = [as_of]
    if symbols:
        pit_args.append(symbols)
    pit_rows = await conn.fetch(_PIT_SQL.format(filt=filt), *pit_args)

    pfilt = " AND symbol = ANY($3)" if symbols else ""
    price_args: list[Any] = [as_of, as_of - timedelta(days=_PRICE_WINDOW_DAYS)]
    if symbols:
        price_args.append(symbols)
    price_rows = await conn.fetch(_PRICE_SQL.format(filt=pfilt), *price_args)

    # Group price series per symbol (ascending dt → ascending lists).
    closes: dict[str, list[float]] = {}
    adj: dict[str, list[float]] = {}
    for r in price_rows:
        closes.setdefault(r["symbol"], []).append(float(r["close"]))
        adj.setdefault(r["symbol"], []).append(float(r["adj_close"]))

    scored: list[SymbolScore] = []
    for r in pit_rows:
        sym = r["symbol"]
        adj_series = adj.get(sym, [])
        close_series = closes.get(sym)
        last_close = close_series[-1] if close_series else None
        shares = _f(r["shares_outstanding"])
        market_cap = shares * last_close if (shares is not None and last_close) else None
        ss = SymbolScore(
            symbol=sym,
            sector=r["sector"],
            market_cap_aud=market_cap,
            raw=raw_factors(
                eps_ttm=r["eps_ttm"], book_value_ps=r["book_value_ps"],
                roe=r["roe"], roa=r["roa"], gross_margin=r["gross_margin"],
                operating_margin=r["operating_margin"], dividend_ttm=r["dividend_ttm"],
                franking_avg_pct=r["franking_avg_pct"], close=last_close,
                adj_closes=adj_series,
            ),
        )
        scored.append(ss)

    sector_neutral_scores(scored)

    written = 0
    for r in scored:
        # Skip a symbol that produced no usable factor at all (all categories empty
        # AND no market cap) — nothing to record.
        if r.n_factors_present == 0 and r.market_cap_aud is None:
            continue
        await conn.execute(
            _UPSERT,
            r.symbol, as_of, factor_set_version, r.sector, _q6(r.market_cap_aud),
            _q6(r.value_score), _q6(r.quality_score), _q6(r.momentum_score),
            _q6(r.low_vol_score), _q6(r.yield_score), _q6(r.composite_score),
            r.n_factors_present,
        )
        written += 1

    return {"symbols": len(scored), "rows": written}
