"""
Morning-brief composer.

Pulls sections from Postgres and renders them through a Jinja template.
Keep the prose under 200 words — this brief is consumed daily, so density matters.

Sections (in order):
  1. Job failures banner (if any in the last 24h)
  2. Market regime
  3. Portfolio discipline (portfolio-team-visibility lane, PR2a/PR2b —
     `docs/proposals/portfolio-team-visibility-2026-07-12.md` §8): revisit-
     overdue, stop/target trajectory, conviction-unset, concentration,
     benchmark lag. Model-independent by construction (rule #11) — the loader
     never reads `signals`/`shap_factors` and never calls
     `resolve_production_model()`. Gated on ASXOS_PERSONAL_USE=1 only (not
     ASXOS_PORTFOLIO_BRIEF_ENABLED, which is orthogonal — §4). Quiet when
     every check is clean; a check that errors renders a loud "could not run"
     line rather than vanishing (CLAUDE.md #10).
  4. Signal label changes on current holdings (today vs yesterday)
  5. Tax actions: lots crossing the 12-month CGT boundary in next 30 days
  6. Regulatory hits on holdings in the last 24h
  7. Market news on holdings (M14a) — gated by ALL of:
       ASXOS_PERSONAL_USE=1 (Part 0 Q1 regulatory firewall)
       ASXOS_NEWS_BRIEF_ENABLED=1 (paper-trade dark gate, plan M14a)
       ingest_news job_runs success within 24h (freshness gate)
     Section absent entirely when any gate fails.
  8. Portfolio adjustments (M13.7) — gated by BOTH:
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

from asxos.domain.benchmark.returns import period_return
from asxos.domain.brief.shap import format_top_factors
from asxos.domain.models.production_gate import resolve_production_model
from asxos.domain.prices.coverage import latest_complete_trading_day
from asxos.domain.prices.fx import is_foreign_symbol
from asxos.domain.tax.cgt import days_to_eligibility
from asxos.domain.theses.discipline import (
    DisciplineFinding,
    DisciplineLevel,
    HoldingWeight,
    PortfolioDisciplineInput,
    ThesisDisciplineInput,
    evaluate_discipline,
)

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
    # PR2a: collected, not yet rendered (PR2b adds the brief.html.j2 block).
    discipline_findings: list[DisciplineFinding] = field(default_factory=list)
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
        # Governance gate (Section 4.4 Step B): resolve the single
        # active+approved_for_allocation production model. The *allocator*
        # (build.py) calls the gate with required=True and fails loudly — that
        # is rule #11's mechanical enforcement point. The brief is display-only,
        # so it passes required=False and DEGRADES gracefully (returns None →
        # skips the Model A signal reads below) rather than hard-failing when a
        # Model A quarantine revokes approval (see risk-register R9). Gate
        # condition + error messages live in production_gate.py so build.py
        # (the other model_versions consumer) can't drift apart on the invariant.
        model_rows = await conn.fetch(
            "SELECT model FROM model_versions "
            "WHERE is_active = TRUE AND approved_for_allocation = TRUE"
        )
        production_model = resolve_production_model(model_rows, required=False)

        # Anchor signal/regime queries on the latest *complete* trading day
        # (the anchor generate_signals uses), not the calendar as_of — EOD data
        # lands ~1 day late, so "today" usually has no signal row yet. The
        # calendar as_of is still the brief's title/delivery date.
        data_as_of = await latest_complete_trading_day(conn)
        signals_as_of = data_as_of or as_of

        # regime, latest_signal_date and signal_changes are Model-A-derived and
        # display-only. Under a deliberate Model A quarantine (rule #11 →
        # approved_for_allocation revoked → 0 approved models) resolve returns
        # None; skip the signal reads so the model-INDEPENDENT brief (tax,
        # regulatory, job failures, portfolio) still renders instead of
        # hard-failing. The allocator keeps its own hard-fail (build.py) — that
        # is rule #11's real enforcement point; this is only the cosmetic signal
        # surface. See risk-register R9.
        regime: str | None = None
        latest_signal_date: date | None = None
        signal_changes: list[SignalChange] = []
        if production_model is not None:
            # regime is market-wide for an as_of but rows are keyed by
            # (model, model_version, symbol); a bare LIMIT 1 returns an
            # arbitrary, non-reproducible row. Pin a deterministic order.
            regime_row = await conn.fetchrow(
                """
                SELECT regime FROM signals
                WHERE model = $1 AND as_of = $2
                ORDER BY model_version DESC, model, symbol
                LIMIT 1
                """,
                production_model,
                signals_as_of,
            )
            regime = regime_row["regime"] if regime_row else None
            latest_signal_date = await conn.fetchval(
                "SELECT MAX(as_of) FROM signals WHERE model = $1", production_model
            )
            signal_changes = await _signal_changes(
                conn, signals_as_of, production_model
            )

        holdings_count = await conn.fetchval(
            "SELECT COUNT(*) FROM current_holdings"
        ) or 0

        latest_price_date: date | None = await conn.fetchval(
            """
            SELECT MAX(p.dt)
            FROM prices p
            JOIN universe u ON u.symbol = p.symbol
            WHERE u.is_active = TRUE
            """
        )

        tax_actions = await _tax_actions(conn, as_of)
        regulatory_hits = await _regulatory_hits(conn, as_of)
        job_failures = await _job_failures(conn, as_of)
        news_items = await _news_section(conn, as_of)
        portfolio_section = await _portfolio_section(conn, as_of)

        # Fail-loud isolation (CLAUDE.md #10): a broken discipline query must
        # never take down the rest of the brief. Surface it as a single loud
        # error finding instead — the same "never silently vanish" contract
        # evaluate_discipline() already enforces for its own per-check errors.
        try:
            discipline_findings = await _discipline_findings(conn, as_of)
        except Exception as exc:
            discipline_findings = [
                DisciplineFinding(
                    check="discipline_section",
                    level=DisciplineLevel.error,
                    message=f"⚠ discipline section could not run: {exc}",
                )
            ]

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
        discipline_findings=discipline_findings,
        latest_signal_date=latest_signal_date,
        latest_price_date=latest_price_date,
        data_as_of=data_as_of,
    )


async def _signal_changes(
    conn: asyncpg.Connection, as_of: date, production_model: str
) -> list[SignalChange]:
    rows = await conn.fetch(
        """
        WITH today AS (
            SELECT DISTINCT ON (s.symbol)
                s.symbol, s.signal_label, s.shap_factors
            FROM signals s
            JOIN current_holdings h ON h.symbol = s.symbol
            WHERE s.model = $2 AND s.as_of = $1
            ORDER BY s.symbol, s.as_of DESC
        ),
        yesterday AS (
            SELECT DISTINCT ON (s.symbol)
                s.symbol, s.signal_label
            FROM signals s
            JOIN current_holdings h ON h.symbol = s.symbol
            WHERE s.model = $2
              AND s.as_of < $1
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
        production_model,
    )
    out: list[SignalChange] = []
    for r in rows:
        # Single strongest driver — same ranking the V2 thesis cards use.
        top = format_top_factors(r["shap_factors"], n=1)
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


def _thesis_discipline_inputs(
    thesis_rows: list[asyncpg.Record], prices: dict[str, Decimal]
) -> tuple[ThesisDisciplineInput, ...]:
    """Build per-thesis inputs, native-currency-against-native throughout.

    Currency safety (R10, `.claude/rules/portfolio-conventions.md`): entry/
    target/stop come straight from `theses` (authored in the holding's own
    native currency) and current comes from `prices.close` (also native) —
    all four legs are native-against-native, no FX step needed here.
    """
    return tuple(
        ThesisDisciplineInput(
            symbol=r["symbol"],
            currency="USD" if is_foreign_symbol(r["symbol"]) else "AUD",
            revisit_due_at=r["revisit_due_at"].date(),
            opened_at=r["opened_at"].date(),
            timeline_days=r["timeline_days"],
            entry_price_native=r["actual_entry_price"],
            current_price_native=prices.get(r["symbol"]),
            target_price_native=r["target_price"],
            stop_price_native=r["stop_price"],
            conviction_level=r["conviction_level"],
        )
        for r in thesis_rows
    )


def _holding_weights(
    holding_rows: list[asyncpg.Record],
    prices: dict[str, Decimal],
    fx_rate: Decimal | None,
) -> tuple[HoldingWeight, ...]:
    """Market value per holding, converted to AUD for the concentration check.

    Foreign (USD) holdings need AUDUSD to convert their native market value
    to AUD (R10) — never divide an AUD figure by quantity to get back to
    native, always convert forward from native. A foreign holding with no
    FX rate available is omitted rather than mis-converted.
    """
    holdings: list[HoldingWeight] = []
    for r in holding_rows:
        close = prices.get(r["symbol"])
        if close is None:
            continue
        mv_native = Decimal(str(r["quantity"])) * close
        if is_foreign_symbol(r["symbol"]):
            if fx_rate is None:
                continue
            mv_aud = mv_native / fx_rate
        else:
            mv_aud = mv_native
        holdings.append(HoldingWeight(symbol=r["symbol"], market_value_aud=mv_aud))
    return tuple(holdings)


async def _since_inception_returns(
    conn: asyncpg.Connection, as_of: date
) -> tuple[Decimal | None, Decimal | None]:
    """Since-inception portfolio vs. benchmark total return (both as +/-%).

    Same framing as `wealth_state.py`'s alpha line: `period_return` over
    `capital_aud` vs `benchmark_tr_level`, anchored on the earliest snapshot
    carrying a benchmark level. Returns (None, None) until Stage 1 backfills
    `benchmark_tr_level`.
    """
    snap_rows = await conn.fetch(
        """
        SELECT capital_aud, benchmark_tr_level
        FROM portfolio_daily_snapshots
        WHERE as_of <= $1
        ORDER BY as_of DESC
        LIMIT 1
        """,
        as_of,
    )
    inception_rows = await conn.fetch(
        """
        SELECT capital_aud, benchmark_tr_level
        FROM portfolio_daily_snapshots
        WHERE benchmark_tr_level IS NOT NULL AND as_of <= $1
        ORDER BY as_of ASC
        LIMIT 1
        """,
        as_of,
    )
    if not snap_rows or not inception_rows or snap_rows[0]["benchmark_tr_level"] is None:
        return None, None

    inc_cap = Decimal(str(inception_rows[0]["capital_aud"]))
    inc_tr = Decimal(str(inception_rows[0]["benchmark_tr_level"]))
    cur_cap = Decimal(str(snap_rows[0]["capital_aud"]))
    cur_tr = Decimal(str(snap_rows[0]["benchmark_tr_level"]))
    if inc_cap <= 0 or inc_tr <= 0:
        return None, None
    return period_return(inc_cap, cur_cap) * 100, period_return(inc_tr, cur_tr) * 100


async def _discipline_findings(
    conn: asyncpg.Connection, as_of: date
) -> list[DisciplineFinding]:
    """Loader for `asxos.domain.theses.discipline.evaluate_discipline()` (PR2a).

    Fetches thesis/holding/price rows, then delegates the native-currency
    thesis-input build to `_thesis_discipline_inputs`, the AUD holding-weight
    build to `_holding_weights`, and the since-inception benchmark comparison
    to `_since_inception_returns` (R10 currency-safety notes live on those
    helpers, next to the arithmetic they govern).

    Gated on ``ASXOS_PERSONAL_USE=1`` only (proposal §6 acceptance criteria) —
    deliberately not ``ASXOS_PORTFOLIO_BRIEF_ENABLED``, which gates the
    allocator's trade suggestions and is orthogonal to this model-independent
    digest (§4). Matches the same gate `_news_section`/`_portfolio_section`
    already apply to their own display-only data.
    """
    if os.environ.get("ASXOS_PERSONAL_USE") != "1":
        return []

    thesis_rows = await conn.fetch(
        """
        SELECT symbol, revisit_due_at, opened_at, timeline_days,
               actual_entry_price, target_price, stop_price, conviction_level
        FROM theses
        WHERE status = 'active'
        ORDER BY opened_at
        """
    )
    holding_rows = await conn.fetch("SELECT symbol, quantity FROM current_holdings")

    symbols = sorted({r["symbol"] for r in thesis_rows} | {r["symbol"] for r in holding_rows})
    prices: dict[str, Decimal] = {}
    if symbols:
        price_rows = await conn.fetch(
            """
            SELECT DISTINCT ON (symbol) symbol, close
            FROM prices
            WHERE symbol = ANY($1) AND dt <= $2
            ORDER BY symbol, dt DESC
            """,
            symbols,
            as_of,
        )
        prices = {r["symbol"]: Decimal(str(r["close"])) for r in price_rows}

    # Deliberately a separate query from `_since_inception_returns`'s latest-
    # snapshot lookup below: this one filters to the latest snapshot that
    # actually carries an FX rate, which need not be the same row as the
    # latest snapshot overall.
    fx_rows = await conn.fetch(
        """
        SELECT fx_rate_audusd
        FROM portfolio_daily_snapshots
        WHERE as_of <= $1 AND fx_rate_audusd IS NOT NULL
        ORDER BY as_of DESC
        LIMIT 1
        """,
        as_of,
    )
    fx_rate = Decimal(str(fx_rows[0]["fx_rate_audusd"])) if fx_rows else None

    thesis_inputs = _thesis_discipline_inputs(thesis_rows, prices)
    holdings = _holding_weights(holding_rows, prices, fx_rate)
    portfolio_tr_aud, benchmark_tr_aud = await _since_inception_returns(conn, as_of)

    port_input = PortfolioDisciplineInput(
        holdings=holdings,
        portfolio_tr_aud=portfolio_tr_aud,
        benchmark_tr_aud=benchmark_tr_aud,
    )
    return evaluate_discipline(thesis_inputs, port_input, as_of)


def render_html(data: BriefData) -> str:
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(Path(__file__).parent / "templates"),
        autoescape=True,
    )
    return env.get_template("brief.html.j2").render(d=data)
