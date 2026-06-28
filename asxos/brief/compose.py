"""
Morning-brief composer.

Pulls sections from Postgres and renders them through a Jinja template.
Keep the prose under 200 words — this brief is consumed daily, so density matters.

Sections (in order):
  1. Job failures banner (if any in the last 24h)
  2. Market regime
  3. Signal label changes on current holdings (today vs yesterday)
  4. Tax actions: lots crossing the 12-month CGT boundary in next 30 days
  5. Regulatory hits on holdings in the last 24h
  6. Market news on holdings (M14a) — gated by ALL of:
       ASXOS_PERSONAL_USE=1 (Part 0 Q1 regulatory firewall)
       ASXOS_NEWS_BRIEF_ENABLED=1 (paper-trade dark gate, plan M14a)
       ingest_news job_runs success within 24h (freshness gate)
     Section absent entirely when any gate fails.
  7. Portfolio adjustments (M13.7) — gated by BOTH:
       ASXOS_PERSONAL_USE=1 (Part 0 Q1 regulatory firewall)
       ASXOS_PORTFOLIO_BRIEF_ENABLED=1 (paper-trade validation gate, plan I.6)
     Omitted entirely when either flag is unset, or when no successful
     build_portfolio run exists with as_of >= today - 2 (plan I.7 freshness gate).
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Any

import jinja2
from dateutil.relativedelta import relativedelta

from asxos.domain.prices.coverage import latest_complete_trading_day
from asxos.domain.tax.cgt import days_to_eligibility

if TYPE_CHECKING:
    import asyncpg

# Deferred to avoid pulling pydantic_settings into test collection.
# Tests patch asxos.brief.compose.acquire directly; production collect()
# falls through to the lazy import below.
acquire: Any = None


@dataclass(frozen=True)
class SignalChange:
    symbol: str
    old_label: str
    new_label: str
    top_factor: str  # e.g. "mom_12_1+0.953"


@dataclass(frozen=True)
class TaxAction:
    symbol: str
    lot_id: int
    eligible_at: date
    days: int


@dataclass(frozen=True)
class RegulatoryHit:
    symbol: str
    source: str
    title: str
    published_at: date
    kind: str


@dataclass(frozen=True)
class NewsItem:
    """One news article relevant to a current holding (M14a).

    ``symbols`` is the subset of the article's tagged symbols that match
    current holdings (normalised to BHP.AU format).
    ``sentiment`` is "positive" | "negative" | "neutral" | "".
    """

    symbols: list[str]
    title: str
    url: str
    published_at: date
    sentiment: str


@dataclass(frozen=True)
class JobFailure:
    job_name: str
    as_of: date
    error_message: str


@dataclass(frozen=True)
class PortfolioTradeSummary:
    """Minimal trade row for the brief's portfolio section."""

    symbol: str
    side: str  # 'buy' or 'sell'
    delta_aud: Decimal


@dataclass(frozen=True)
class PortfolioSection:
    """Section 6 of the brief — portfolio adjustments (M13.7).

    Populated only when both ASXOS_PERSONAL_USE=1 and
    ASXOS_PORTFOLIO_BRIEF_ENABLED=1, and a fresh build_portfolio run
    exists (as_of >= brief_date - 2, plan I.7).
    """

    run_id: int
    run_as_of: date
    top_buys: list[PortfolioTradeSummary]
    top_sells: list[PortfolioTradeSummary]
    total_buy_aud: Decimal
    total_sell_aud: Decimal
    turnover_aud: Decimal


@dataclass(frozen=True)
class BriefData:
    as_of: date
    regime: str | None          # None when no signal row exists for as_of
    holdings_count: int
    signal_changes: list[SignalChange] = field(default_factory=list)
    tax_actions: list[TaxAction] = field(default_factory=list)
    regulatory_hits: list[RegulatoryHit] = field(default_factory=list)
    job_failures: list[JobFailure] = field(default_factory=list)
    news_items: list[NewsItem] = field(default_factory=list)
    portfolio_section: PortfolioSection | None = None
    latest_signal_date: date | None = None
    latest_price_date: date | None = None
    # Latest *complete* trading day the regime/signal queries were anchored to
    # (not the calendar as_of). None only when no complete day exists at all.
    data_as_of: date | None = None

    @property
    def has_failures(self) -> bool:
        return bool(self.job_failures)

    @property
    def signals_stale(self) -> bool:
        """True only when signals genuinely lag the latest complete trading day.

        The brief is titled with the calendar ``as_of`` but anchors its regime
        and signal queries on ``data_as_of`` = latest_complete_trading_day (the
        same anchor generate_signals uses), because EOD data lands ~1 day late.
        Stale when there are no signals at all, or the freshest signal is
        *behind* that anchor (e.g. generate_signals was blocked) — not merely
        because no row exists for today's calendar date. This preserves the
        anti-fabrication intent (genuinely-missing signals still warn) without
        the daily false alarm.
        """
        if self.latest_signal_date is None:
            return True
        anchor = self.data_as_of or self.as_of
        return self.latest_signal_date < anchor

    @property
    def prices_stale(self) -> bool:
        if self.latest_price_date is None:
            return True
        return (self.as_of - self.latest_price_date).days > 5


async def collect(as_of: date) -> BriefData:
    """Single async DB session, five sections + optional portfolio section."""
    # Use module-level `acquire` if set (e.g. by tests); otherwise lazy-import
    # from asxos.db to avoid pulling pydantic_settings in at collection time.
    _acquire: Any = globals().get("acquire")
    if _acquire is None:
        from asxos.db import acquire as _acquire
    async with _acquire() as conn:
        # Anchor signal/regime queries on the latest *complete* trading day
        # (the anchor generate_signals uses), not the calendar as_of — EOD data
        # lands ~1 day late, so "today" usually has no signal row yet. The
        # calendar as_of is still the brief's title/delivery date.
        data_as_of = await latest_complete_trading_day(conn)
        signals_as_of = data_as_of or as_of

        # regime is market-wide for an as_of but rows are keyed by
        # (model, model_version, symbol); a bare LIMIT 1 returns an arbitrary,
        # non-reproducible row. Pin a deterministic order so the brief is stable.
        regime_row = await conn.fetchrow(
            """
            SELECT regime FROM signals
            WHERE as_of = $1
            ORDER BY model_version DESC, model, symbol
            LIMIT 1
            """,
            signals_as_of,
        )
        regime: str | None = regime_row["regime"] if regime_row else None

        holdings_count = await conn.fetchval(
            "SELECT COUNT(*) FROM current_holdings"
        ) or 0

        latest_signal_date: date | None = await conn.fetchval(
            "SELECT MAX(as_of) FROM signals"
        )
        latest_price_date: date | None = await conn.fetchval(
            """
            SELECT MAX(p.dt)
            FROM prices p
            JOIN universe u ON u.symbol = p.symbol
            WHERE u.is_active = TRUE
            """
        )

        signal_changes = await _signal_changes(conn, signals_as_of)
        tax_actions = await _tax_actions(conn, as_of)
        regulatory_hits = await _regulatory_hits(conn, as_of)
        job_failures = await _job_failures(conn, as_of)
        news_items = await _news_section(conn, as_of)
        portfolio_section = await _portfolio_section(conn, as_of)

    return BriefData(
        as_of=as_of,
        regime=regime,
        holdings_count=int(holdings_count),
        signal_changes=signal_changes,
        tax_actions=tax_actions,
        regulatory_hits=regulatory_hits,
        job_failures=job_failures,
        news_items=news_items,
        portfolio_section=portfolio_section,
        latest_signal_date=latest_signal_date,
        latest_price_date=latest_price_date,
        data_as_of=data_as_of,
    )


async def _signal_changes(conn: asyncpg.Connection, as_of: date) -> list[SignalChange]:
    rows = await conn.fetch(
        """
        WITH today AS (
            SELECT DISTINCT ON (s.symbol)
                s.symbol, s.signal_label, s.shap_factors
            FROM signals s
            JOIN current_holdings h ON h.symbol = s.symbol
            WHERE s.as_of = $1
            ORDER BY s.symbol, s.as_of DESC
        ),
        yesterday AS (
            SELECT DISTINCT ON (s.symbol)
                s.symbol, s.signal_label
            FROM signals s
            JOIN current_holdings h ON h.symbol = s.symbol
            WHERE s.as_of < $1
              AND s.as_of >= $1::date - 7
            ORDER BY s.symbol, s.as_of DESC
        )
        SELECT
            t.symbol,
            COALESCE(y.signal_label, '(new)') AS old_label,
            t.signal_label AS new_label,
            t.shap_factors
        FROM today t
        LEFT JOIN yesterday y ON y.symbol = t.symbol
        WHERE COALESCE(y.signal_label, '') <> t.signal_label
        ORDER BY t.symbol
        """,
        as_of,
    )
    out: list[SignalChange] = []
    for r in rows:
        shap = r["shap_factors"] or {}
        if isinstance(shap, str):
            import json
            shap = json.loads(shap)
        top = ""
        if shap:
            ordered = sorted(
                ((k, v) for k, v in shap.items() if k != "bias" and v is not None),
                key=lambda kv: abs(float(kv[1])),
                reverse=True,
            )
            if ordered:
                k, v = ordered[0]
                top = f"{k}{float(v):+.3f}"
        out.append(
            SignalChange(
                symbol=r["symbol"],
                old_label=r["old_label"],
                new_label=r["new_label"],
                top_factor=top,
            )
        )
    return out


async def _tax_actions(
    conn: asyncpg.Connection, as_of: date, window_days: int = 30
) -> list[TaxAction]:
    rows = await conn.fetch(
        """
        SELECT id, symbol, acquired_at
        FROM current_holdings
        ORDER BY acquired_at
        """
    )
    out: list[TaxAction] = []
    for r in rows:
        days = days_to_eligibility(r["acquired_at"], as_of)
        if 0 < days <= window_days:
            out.append(
                TaxAction(
                    symbol=r["symbol"],
                    lot_id=r["id"],
                    eligible_at=r["acquired_at"] + relativedelta(years=1) + timedelta(days=1),
                    days=days,
                )
            )
    return out


async def _regulatory_hits(
    conn: asyncpg.Connection, as_of: date, lookback_hours: int = 24
) -> list[RegulatoryHit]:
    rows = await conn.fetch(
        """
        SELECT r.source, r.title, r.published_at, r.relevance_tags
        FROM regulatory_events r
        WHERE r.published_at >= $1::date - INTERVAL '2 day'
          AND r.ingested_at >= $1::date - make_interval(hours => $2)
        ORDER BY r.published_at DESC
        """,
        as_of,
        lookback_hours,
    )
    holdings_rows = await conn.fetch("SELECT symbol FROM current_holdings")
    holdings = {r["symbol"] for r in holdings_rows}

    out: list[RegulatoryHit] = []
    for r in rows:
        tags = r["relevance_tags"] or {}
        if isinstance(tags, str):
            import json
            tags = json.loads(tags)
        symbols = tags.get("symbols") if isinstance(tags, dict) else []
        kind = tags.get("kind", "other") if isinstance(tags, dict) else "other"
        # Match on any holding symbol
        for s in symbols or []:
            if s in holdings:
                out.append(
                    RegulatoryHit(
                        symbol=s,
                        source=r["source"],
                        title=r["title"],
                        published_at=r["published_at"],
                        kind=kind,
                    )
                )
                break
    return out


async def _job_failures(
    conn: asyncpg.Connection, as_of: date
) -> list[JobFailure]:
    rows = await conn.fetch(
        """
        SELECT job_name, as_of, error_message
        FROM job_runs
        WHERE as_of = $1 AND status = 'failure'
        ORDER BY job_name
        """,
        as_of,
    )
    return [
        JobFailure(
            job_name=r["job_name"],
            as_of=r["as_of"],
            error_message=(r["error_message"] or "")[:200],
        )
        for r in rows
    ]


async def _news_section(
    conn: asyncpg.Connection, as_of: date
) -> list[NewsItem]:
    """Return news items for section 6, or [] if gated out (M14a).

    Three-layer gating (mirrors M13.7 Amendment C):
      1. ASXOS_PERSONAL_USE=1  (regulatory firewall)
      2. ASXOS_NEWS_BRIEF_ENABLED=1  (paper-trade dark gate; default 0)
      3. ingest_news had a successful job_run within 24h  (freshness gate)

    Section absent entirely when any gate fails.
    """
    if os.environ.get("ASXOS_PERSONAL_USE") != "1":
        return []
    if os.environ.get("ASXOS_NEWS_BRIEF_ENABLED") != "1":
        return []
    if not await _news_ingest_fresh(conn, as_of):
        return []
    return await _holding_news(conn, as_of)


async def _news_ingest_fresh(conn: asyncpg.Connection, as_of: date) -> bool:
    """True when ingest_news has a successful job_run within the last 24 hours."""
    cutoff = as_of - timedelta(days=1)
    rows = await conn.fetch(
        """
        SELECT 1 FROM job_runs
        WHERE job_name = 'ingest_news' AND as_of >= $1 AND status = 'success'
        LIMIT 1
        """,
        cutoff,
    )
    return bool(rows)


async def _holding_news(
    conn: asyncpg.Connection, as_of: date, lookback_hours: int = 24
) -> list[NewsItem]:
    """Fetch holding_news rows from the last ``lookback_hours`` hours.

    Filters the result to symbols that appear in current_holdings.
    Returns at most 20 items, ordered most-recent first.
    """
    rows = await conn.fetch(
        """
        SELECT url, title, published_at, symbols, sentiment
        FROM holding_news
        WHERE published_at >= $1::date - make_interval(hours => $2)
        ORDER BY published_at DESC
        LIMIT 20
        """,
        as_of,
        lookback_hours,
    )
    holdings_rows = await conn.fetch("SELECT symbol FROM current_holdings")
    holdings = {r["symbol"] for r in holdings_rows}

    out: list[NewsItem] = []
    for r in rows:
        syms = r["symbols"] or []
        if isinstance(syms, str):
            import json
            syms = json.loads(syms)
        matched = [s for s in syms if s in holdings]
        if not matched:
            continue
        out.append(
            NewsItem(
                symbols=matched,
                title=r["title"],
                url=r["url"],
                published_at=r["published_at"],
                sentiment=r["sentiment"] or "",
            )
        )
    return out


async def _portfolio_section(
    conn: asyncpg.Connection, as_of: date
) -> PortfolioSection | None:
    """Return portfolio adjustments for section 6, or None if gated out.

    Gating (plan I.7 + plan I.6 + Part 0 Q1):
    - ASXOS_PERSONAL_USE must be "1" (regulatory firewall).
    - ASXOS_PORTFOLIO_BRIEF_ENABLED must be "1" (paper-trade gate; stays 0
      until 4 weeks of sign-off per M13.8).
    - A successful ``build_portfolio`` job run must exist with
      ``as_of >= as_of - 2`` (freshness gate; plan I.7 standardises on
      24h lookback with a 2-day tolerance for the weekly cron cadence).

    The section is omitted entirely when any gate fails — never partial or
    stale (plan I.7: "If the cron failed: section 6 is omitted entirely").
    """
    if os.environ.get("ASXOS_PERSONAL_USE") != "1":
        return None
    if os.environ.get("ASXOS_PORTFOLIO_BRIEF_ENABLED") != "1":
        return None

    # Freshness gate: most recent successful build_portfolio run within 2 days.
    # Uses as_of date arithmetic (plan H.2 QUICK-WIN-1: filter on as_of, not created_at).
    cutoff = as_of - timedelta(days=2)
    run_row = await conn.fetchrow(
        """
        SELECT r.run_id, r.as_of
        FROM rebalance_runs r
        JOIN job_runs j
          ON j.job_name = 'build_portfolio'
         AND j.as_of = r.as_of
         AND j.status = 'success'
        WHERE r.as_of >= $1
        ORDER BY r.as_of DESC
        LIMIT 1
        """,
        cutoff,
    )
    if run_row is None:
        return None

    run_id = run_row["run_id"]
    run_as_of = run_row["as_of"]

    # Top 3 buys and top 3 sells (by |delta_aud|).
    trade_rows = await conn.fetch(
        """
        SELECT symbol, side, delta_aud
        FROM proposed_trades
        WHERE run_id = $1 AND side IN ('buy', 'sell')
        ORDER BY ABS(delta_aud) DESC
        """,
        run_id,
    )

    top_buys = [
        PortfolioTradeSummary(
            symbol=r["symbol"],
            side="buy",
            delta_aud=Decimal(str(r["delta_aud"])),
        )
        for r in trade_rows
        if r["side"] == "buy"
    ][:3]

    top_sells = [
        PortfolioTradeSummary(
            symbol=r["symbol"],
            side="sell",
            delta_aud=Decimal(str(r["delta_aud"])),
        )
        for r in trade_rows
        if r["side"] == "sell"
    ][:3]

    # Aggregate AUD totals.
    total_buy_aud = sum(
        (Decimal(str(r["delta_aud"])) for r in trade_rows if r["side"] == "buy"),
        Decimal("0"),
    )
    total_sell_aud = sum(
        (abs(Decimal(str(r["delta_aud"]))) for r in trade_rows if r["side"] == "sell"),
        Decimal("0"),
    )

    return PortfolioSection(
        run_id=run_id,
        run_as_of=run_as_of,
        top_buys=top_buys,
        top_sells=top_sells,
        total_buy_aud=total_buy_aud,
        total_sell_aud=total_sell_aud,
        turnover_aud=total_buy_aud + total_sell_aud,
    )


def render_html(data: BriefData) -> str:
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(Path(__file__).parent / "templates"),
        autoescape=True,
    )
    return env.get_template("brief.html.j2").render(d=data)
