"""
Brief composition tests.

`render_html` is pure over BriefData — we synthesize the dataclass
directly. `collect` is exercised under a MagicMock conn that returns
canned rows for each of the five queries.

M14a additions: NewsItem dataclass, news section HTML, _news_section() gating.
"""
from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from asxos.brief.compose import (
    BriefData,
    DisciplineLevel,
    JobFailure,
    NewsItem,
    RegulatoryHit,
    SignalChange,
    TaxAction,
    _discipline_findings,
    collect,
    render_html,
)

# ---------------------------------------------------------------------------
# render_html — pure path
# ---------------------------------------------------------------------------

def _brief(**overrides) -> BriefData:
    defaults = {
        "as_of": date(2026, 5, 22),
        "regime": "bear",
        "latest_signal_date": date(2026, 5, 22),
        "latest_price_date": date(2026, 5, 22),
        "holdings_count": 3,
        "signal_changes": [],
        "tax_actions": [],
        "regulatory_hits": [],
        "job_failures": [],
    }
    defaults.update(overrides)
    return BriefData(**defaults)


def test_render_html_contains_title_and_regime() -> None:
    html = render_html(_brief())
    assert "asxos brief — 2026-05-22" in html
    assert "Regime: <strong>bear</strong>" in html


def test_render_html_shows_stale_regime_warning() -> None:
    """When regime is None, shows unavailable + latest signal date instead of regime label."""
    html = render_html(_brief(regime=None, latest_signal_date=date(2026, 5, 20)))
    assert "unavailable" in html
    assert "2026-05-20" in html
    assert "Regime: <strong>bear</strong>" not in html


def test_signals_not_stale_when_anchored_to_complete_day() -> None:
    """The reported scenario: brief dated 2026-06-18, but signals are anchored to
    the latest complete trading day 2026-06-17 (the ~1-day EOD lag) → NOT stale,
    regime is shown, no freshness banner."""
    html = render_html(_brief(
        as_of=date(2026, 6, 18),
        regime="neutral",
        latest_signal_date=date(2026, 6, 17),
        latest_price_date=date(2026, 6, 17),
        data_as_of=date(2026, 6, 17),
    ))
    assert "Regime: <strong>neutral</strong>" in html
    assert "Data freshness warning" not in html
    assert "unavailable" not in html


def test_signals_stale_when_behind_complete_day() -> None:
    """Genuinely stale: the freshest signal is *behind* the latest complete
    trading day (e.g. generate_signals was blocked) → unavailable + banner."""
    b = _brief(
        as_of=date(2026, 6, 18),
        regime=None,
        latest_signal_date=date(2026, 6, 17),
        latest_price_date=date(2026, 6, 18),
        data_as_of=date(2026, 6, 18),
    )
    assert b.signals_stale is True
    html = render_html(b)
    assert "unavailable" in html
    assert "Signals stale — latest signal run: 2026-06-17" in html


def test_signals_stale_when_no_signals_at_all() -> None:
    b = _brief(regime=None, latest_signal_date=None, data_as_of=None)
    assert b.signals_stale is True


def test_render_html_shows_freshness_banner_when_prices_stale() -> None:
    """Freshness banner appears when latest_price_date is >5 days before as_of."""
    html = render_html(_brief(latest_price_date=date(2026, 5, 10)))
    assert "Prices stale" in html
    assert "2026-05-10" in html


def test_render_html_freshness_banner_absent_when_fresh() -> None:
    """No freshness banner when prices and signals are current."""
    html = render_html(_brief())
    assert "Data freshness warning" not in html


def test_render_html_shows_signal_changes() -> None:
    html = render_html(
        _brief(
            signal_changes=[
                SignalChange("BHP.AU", "BUY", "STRONG_SELL", "mom_12_1-0.420"),
                SignalChange("CSL.AU", "HOLD", "STRONG_BUY", "mom_12_1+1.002"),
            ]
        )
    )
    assert "BHP.AU" in html
    assert "STRONG_SELL" in html
    assert "mom_12_1-0.420" in html
    assert "CSL.AU" in html


# ---------------------------------------------------------------------------
# Signal caveat (Brief QA Step 1) — labels experimental, not trade instructions
# ---------------------------------------------------------------------------

_CAVEAT_MARKER = "Signal caveat:"


def test_render_html_contains_signal_caveat() -> None:
    html = render_html(_brief())
    assert _CAVEAT_MARKER in html
    assert "experimental model-derived rankings" in html
    assert "decision-support context only" in html
    assert "not trade instructions" in html


def test_render_html_caveat_present_when_signals_stale() -> None:
    """Caveat still appears when regime is unavailable (signals stale) — and the
    existing stale behaviour is preserved."""
    html = render_html(_brief(regime=None, latest_signal_date=date(2026, 5, 20)))
    assert _CAVEAT_MARKER in html
    assert "unavailable" in html  # existing stale-regime behaviour intact


def test_render_html_caveat_near_signal_section_not_buried() -> None:
    """Caveat sits in the regime/signal area: after the regime line and before
    the 'Signal changes on holdings' section — not buried at the bottom."""
    html = render_html(_brief())
    caveat_pos = html.index(_CAVEAT_MARKER)
    regime_pos = html.index("Regime:")
    signal_section_pos = html.index("Signal changes on holdings")
    assert regime_pos < caveat_pos < signal_section_pos


def test_render_html_renders_empty_states() -> None:
    html = render_html(_brief())
    assert "No label changes overnight" in html
    assert "No lots crossing" in html
    assert "No regulatory hits" in html


def test_render_html_renders_failures_banner() -> None:
    html = render_html(
        _brief(
            job_failures=[
                JobFailure(job_name="sync_prices", as_of=date(2026, 5, 22), error_message="HTTP 503"),
            ]
        )
    )
    assert "Job failures in the last 24h" in html
    assert "sync_prices" in html


def test_render_html_escapes_user_content() -> None:
    # Autoescape: a malicious title shouldn't render as HTML
    html = render_html(
        _brief(
            regulatory_hits=[
                RegulatoryHit(
                    symbol="BHP.AU",
                    source="ATO",
                    title="<script>alert(1)</script>",
                    published_at=date(2026, 5, 22),
                    kind="tax",
                )
            ]
        )
    )
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_render_html_shows_tax_actions() -> None:
    html = render_html(
        _brief(
            tax_actions=[
                TaxAction(symbol="CBA.AU", lot_id=42, eligible_at=date(2026, 6, 1), days=10),
            ]
        )
    )
    assert "CBA.AU" in html
    assert "10" in html
    assert "2026-06-01" in html


# ---------------------------------------------------------------------------
# collect — under a mocked DB
# ---------------------------------------------------------------------------

def _make_conn(
    *,
    regime_row,
    holdings_count,
    signal_rows,
    tax_rows,
    reg_rows,
    hold_syms,
    fail_rows,
    news_rows=None,
    news_job_rows=None,
    latest_signal_date=None,
    latest_price_date=None,
    model_gate_rows=None,
):
    """Build a mock asyncpg connection that routes queries to canned rows.

    news_rows:          rows for ``FROM holding_news`` queries (_holding_news)
    news_job_rows:      rows for ``FROM job_runs … job_name = 'ingest_news'`` (_news_ingest_fresh)
    latest_signal_date: return value for ``SELECT MAX(as_of) FROM signals``
    latest_price_date:  return value for ``SELECT MAX(p.dt) FROM prices ...``
    model_gate_rows:    rows for the ``FROM model_versions`` contamination-isolation
                         gate query; defaults to a single approved model_a row so
                         existing tests don't need to know about the gate.
    """
    _latest_signal_date = latest_signal_date
    _latest_price_date = latest_price_date
    _model_gate_rows = (
        model_gate_rows if model_gate_rows is not None else [{"model": "model_a"}]
    )

    conn = MagicMock()
    conn.fetchrow = AsyncMock(return_value=regime_row)

    async def _fetchval(query, *args, **kwargs):
        q = " ".join(query.split())
        if "COUNT(*)" in q:
            return holdings_count
        if "MAX(as_of)" in q:
            return _latest_signal_date
        if "MAX(p.dt)" in q:
            return _latest_price_date
        return None

    conn.fetchval = AsyncMock(side_effect=_fetchval)

    async def _fetch(query, *args, **kwargs):
        q = " ".join(query.split())
        if "FROM model_versions" in q:
            return _model_gate_rows
        if "signals s\nJOIN current_holdings" in query or ("FROM signals" in q and "old_label" in q):
            return signal_rows
        if "FROM current_holdings\nORDER BY acquired_at" in query:
            return tax_rows
        if "FROM regulatory_events" in q:
            return reg_rows
        if "FROM holding_news" in q:
            return news_rows or []
        if "FROM job_runs" in q:
            # Differentiate the freshness check from the failures query.
            if "ingest_news" in q:
                return news_job_rows or []
            return fail_rows
        if "SELECT symbol FROM current_holdings" in q:
            return hold_syms
        return []

    conn.fetch = AsyncMock(side_effect=_fetch)
    return conn


def test_collect_assembles_brief_data() -> None:
    today = date(2026, 5, 22)
    signal_rows = [
        {
            "symbol": "BHP.AU",
            "old_label": "BUY",
            "new_label": "STRONG_SELL",
            "shap_factors": {"mom_12_1": -0.420, "market_cap": -0.310, "bias": 0.05},
        }
    ]
    tax_rows = [
        {"id": 7, "symbol": "CBA.AU", "acquired_at": today.replace(day=21).replace(year=today.year - 1)},
    ]
    reg_rows = [
        {
            "source": "ATO",
            "title": "Tax determination",
            "published_at": today,
            "relevance_tags": {"symbols": ["BHP.AU"], "kind": "tax"},
        }
    ]
    hold_syms = [{"symbol": "BHP.AU"}, {"symbol": "CBA.AU"}]
    fail_rows = [
        {"job_name": "sync_fundamentals", "as_of": today, "error_message": "timeout"},
    ]
    conn = _make_conn(
        regime_row={"regime": "bear"},
        holdings_count=2,
        signal_rows=signal_rows,
        tax_rows=tax_rows,
        reg_rows=reg_rows,
        hold_syms=hold_syms,
        fail_rows=fail_rows,
    )

    @asynccontextmanager
    async def fake_acquire():
        yield conn

    with patch("asxos.brief.compose.acquire", fake_acquire):
        data = asyncio.run(collect(today))

    assert data.regime == "bear"
    assert data.holdings_count == 2
    assert len(data.signal_changes) == 1
    assert data.signal_changes[0].top_factor.startswith("mom_12_1")
    # Tax action: acquired_at ~yesterday-of-last-year → far from boundary, skip
    # (the days_to_eligibility check filters within 30 days).
    assert isinstance(data.tax_actions, list)
    assert len(data.regulatory_hits) == 1
    assert data.regulatory_hits[0].symbol == "BHP.AU"
    assert data.has_failures
    assert data.job_failures[0].job_name == "sync_fundamentals"


def test_collect_handles_empty_db() -> None:
    today = date(2026, 5, 22)
    conn = _make_conn(
        regime_row=None,
        holdings_count=0,
        signal_rows=[],
        tax_rows=[],
        reg_rows=[],
        hold_syms=[],
        fail_rows=[],
    )

    @asynccontextmanager
    async def fake_acquire():
        yield conn

    with patch("asxos.brief.compose.acquire", fake_acquire):
        data = asyncio.run(collect(today))

    assert data.regime is None
    assert data.signals_stale is True
    assert data.holdings_count == 0
    assert data.signal_changes == []
    assert not data.has_failures


def test_collect_no_approved_model_renders_without_model_sections() -> None:
    """R9: 0 active+approved_for_allocation models is the EXPECTED state under a
    Model A quarantine (rule #11), not a misconfig for this display path. collect()
    must render the model-INDEPENDENT brief (regime None, no signal changes) instead
    of hard-failing and hiding it. The allocator still hard-fails on 0 approved —
    see tests/test_portfolio_build.py."""
    today = date(2026, 5, 22)
    conn = _make_conn(
        regime_row={"regime": "bear"},  # present, but must be skipped (model gated off)
        holdings_count=2,
        signal_rows=[],
        tax_rows=[],
        reg_rows=[],
        hold_syms=[],
        fail_rows=[],
        model_gate_rows=[],
    )

    @asynccontextmanager
    async def fake_acquire():
        yield conn

    with patch("asxos.brief.compose.acquire", fake_acquire):
        data = asyncio.run(collect(today))

    assert data.regime is None          # model-derived → skipped under quarantine
    assert data.signal_changes == []    # model-derived → skipped
    assert data.latest_signal_date is None
    assert data.signals_stale is True
    assert data.holdings_count == 2     # model-INDEPENDENT data survives


def test_collect_multiple_approved_models_renders_without_model_sections() -> None:
    """R9: >1 approved is ambiguous (no single model to display) → skip the Model A
    sections rather than hard-fail the whole brief. The allocator still hard-fails on
    >1 approved — see tests/test_portfolio_build.py."""
    today = date(2026, 5, 22)
    conn = _make_conn(
        regime_row={"regime": "bull"},
        holdings_count=1,
        signal_rows=[],
        tax_rows=[],
        reg_rows=[],
        hold_syms=[],
        fail_rows=[],
        model_gate_rows=[{"model": "model_a"}, {"model": "factor_sleeve"}],
    )

    @asynccontextmanager
    async def fake_acquire():
        yield conn

    with patch("asxos.brief.compose.acquire", fake_acquire):
        data = asyncio.run(collect(today))

    assert data.regime is None
    assert data.signal_changes == []
    assert data.holdings_count == 1


def test_collect_anchors_on_complete_trading_day() -> None:
    """collect() queries regime/signals on the latest *complete* trading day,
    not the calendar as_of, and records it as data_as_of → not stale."""
    calendar_today = date(2026, 6, 18)
    complete_day = date(2026, 6, 17)
    conn = _make_conn(
        regime_row={"regime": "neutral"},
        holdings_count=1,
        signal_rows=[],
        tax_rows=[],
        reg_rows=[],
        hold_syms=[],
        fail_rows=[],
        latest_signal_date=complete_day,
    )

    @asynccontextmanager
    async def fake_acquire():
        yield conn

    with (
        patch("asxos.brief.compose.acquire", fake_acquire),
        patch(
            "asxos.brief.compose.latest_complete_trading_day",
            AsyncMock(return_value=complete_day),
        ),
    ):
        data = asyncio.run(collect(calendar_today))

    assert data.data_as_of == complete_day
    assert data.regime == "neutral"
    assert data.signals_stale is False
    # The regime query is pinned to the production model and used the
    # complete-day anchor, not the calendar date.
    assert conn.fetchrow.await_args.args[1] == "model_a"
    assert conn.fetchrow.await_args.args[2] == complete_day


# ---------------------------------------------------------------------------
# M14a — news section render_html tests
# ---------------------------------------------------------------------------


def test_render_html_shows_news_section() -> None:
    """When news_items are populated the section appears in the HTML."""
    html = render_html(
        _brief(
            news_items=[
                NewsItem(
                    symbols=["BHP.AU"],
                    title="BHP quarterly results",
                    url="https://example.com/bhp",
                    published_at=date(2026, 5, 23),
                    sentiment="positive",
                )
            ]
        )
    )
    assert "BHP.AU" in html
    assert "BHP quarterly results" in html
    assert "https://example.com/bhp" in html
    assert "sentiment-positive" in html
    assert "Market news on holdings" in html


def test_render_html_news_section_absent_when_no_items() -> None:
    """When news_items=[] the news section header is not rendered (no empty-state placeholder)."""
    html = render_html(_brief(news_items=[]))
    assert "Market news on holdings" not in html


def test_render_html_news_section_escapes_title() -> None:
    """Malicious title in news item is HTML-escaped (autoescape active)."""
    html = render_html(
        _brief(
            news_items=[
                NewsItem(
                    symbols=["BHP.AU"],
                    title="<script>alert(1)</script>",
                    url="https://example.com/x",
                    published_at=date(2026, 5, 23),
                    sentiment="",
                )
            ]
        )
    )
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


# ---------------------------------------------------------------------------
# M14a — collect() with news items (gating tests)
# ---------------------------------------------------------------------------


def test_collect_news_section_absent_when_flag_off() -> None:
    """news_items=[] when ASXOS_NEWS_BRIEF_ENABLED is not '1'."""
    today = date(2026, 5, 22)
    conn = _make_conn(
        regime_row={"regime": "neutral"},
        holdings_count=1,
        signal_rows=[],
        tax_rows=[],
        reg_rows=[],
        hold_syms=[{"symbol": "BHP.AU"}],
        fail_rows=[],
        news_rows=[{
            "url": "https://example.com/bhp",
            "title": "BHP news",
            "published_at": today,
            "symbols": ["BHP.AU"],
            "sentiment": "positive",
        }],
        news_job_rows=[{"job_name": "ingest_news"}],  # fresh job run exists
    )

    @asynccontextmanager
    async def fake_acquire():
        yield conn

    # Flag is OFF → news_items should be []
    with (
        patch("asxos.brief.compose.acquire", fake_acquire),
        patch.dict(os.environ, {"ASXOS_PERSONAL_USE": "1", "ASXOS_NEWS_BRIEF_ENABLED": "0"}),
    ):
        data = asyncio.run(collect(today))

    assert data.news_items == []


def test_collect_assembles_news_items() -> None:
    """When all three gates pass, collect() populates news_items."""
    today = date(2026, 5, 22)
    conn = _make_conn(
        regime_row={"regime": "neutral"},
        holdings_count=1,
        signal_rows=[],
        tax_rows=[],
        reg_rows=[],
        hold_syms=[{"symbol": "BHP.AU"}],
        fail_rows=[],
        news_rows=[{
            "url": "https://example.com/bhp",
            "title": "BHP quarterly",
            "published_at": today,
            "symbols": ["BHP.AU"],
            "sentiment": "positive",
        }],
        news_job_rows=[{"job_name": "ingest_news"}],  # non-empty → fresh
    )

    @asynccontextmanager
    async def fake_acquire():
        yield conn

    with (
        patch("asxos.brief.compose.acquire", fake_acquire),
        patch.dict(os.environ, {
            "ASXOS_PERSONAL_USE": "1",
            "ASXOS_NEWS_BRIEF_ENABLED": "1",
        }),
    ):
        data = asyncio.run(collect(today))

    assert len(data.news_items) == 1
    assert data.news_items[0].symbols == ["BHP.AU"]
    assert data.news_items[0].title == "BHP quarterly"
    assert data.news_items[0].sentiment == "positive"


def test_collect_news_absent_when_ingest_stale() -> None:
    """news_items=[] when ingest_news has no recent successful job_run."""
    today = date(2026, 5, 22)
    conn = _make_conn(
        regime_row={"regime": "neutral"},
        holdings_count=1,
        signal_rows=[],
        tax_rows=[],
        reg_rows=[],
        hold_syms=[{"symbol": "BHP.AU"}],
        fail_rows=[],
        news_rows=[{
            "url": "https://example.com/bhp",
            "title": "BHP news",
            "published_at": today,
            "symbols": ["BHP.AU"],
            "sentiment": "",
        }],
        news_job_rows=[],   # no recent ingest_news success → stale
    )

    @asynccontextmanager
    async def fake_acquire():
        yield conn

    with (
        patch("asxos.brief.compose.acquire", fake_acquire),
        patch.dict(os.environ, {
            "ASXOS_PERSONAL_USE": "1",
            "ASXOS_NEWS_BRIEF_ENABLED": "1",
        }),
    ):
        data = asyncio.run(collect(today))

    assert data.news_items == []


# ---------------------------------------------------------------------------
# PR2a — _discipline_findings loader (collected, not yet rendered)
# ---------------------------------------------------------------------------


def _disc_conn(
    *,
    thesis_rows=None,
    holding_rows=None,
    price_rows=None,
    fx_rows=None,
    snap_rows=None,
    inception_rows=None,
):
    thesis_rows = thesis_rows or []
    holding_rows = holding_rows or []
    price_rows = price_rows or []
    fx_rows = fx_rows or []
    snap_rows = snap_rows or []
    inception_rows = inception_rows or []

    async def _fetch(query, *args, **kwargs):
        q = " ".join(query.split())
        if "FROM theses" in q:
            return thesis_rows
        if "SELECT symbol, quantity FROM current_holdings" in q:
            return holding_rows
        if "FROM prices" in q:
            return price_rows
        if "fx_rate_audusd IS NOT NULL" in q:
            return fx_rows
        if "benchmark_tr_level IS NOT NULL" in q:
            return inception_rows
        if "FROM portfolio_daily_snapshots" in q:
            return snap_rows
        return []

    conn = MagicMock()
    conn.fetch = AsyncMock(side_effect=_fetch)
    return conn


def test_discipline_findings_quiet_when_no_theses_or_holdings() -> None:
    conn = _disc_conn()
    findings = asyncio.run(_discipline_findings(conn, date(2026, 7, 13)))
    assert findings == []


def test_discipline_findings_cba_revisit_and_data_sanity() -> None:
    """Acceptance criterion (proposal §6): CBA's stale ladder (target 60 vs
    live 168) emits both a REVISIT OVERDUE and a DATA-SANITY line."""
    thesis_rows = [
        {
            "symbol": "CBA.AU",
            "revisit_due_at": datetime(2026, 6, 27),
            "opened_at": datetime(2026, 1, 10),
            "timeline_days": None,
            "actual_entry_price": Decimal("50"),
            "target_price": Decimal("60"),
            "stop_price": Decimal("42"),
            "conviction_level": 3,
        }
    ]
    price_rows = [{"symbol": "CBA.AU", "close": Decimal("168")}]
    conn = _disc_conn(thesis_rows=thesis_rows, price_rows=price_rows)

    findings = asyncio.run(_discipline_findings(conn, date(2026, 7, 13)))

    checks = {f.check for f in findings}
    assert "revisit_overdue" in checks
    assert "data_sanity" in checks
    sanity = next(f for f in findings if f.check == "data_sanity")
    assert sanity.level == DisciplineLevel.red
    assert "CBA.AU" in sanity.message


def test_discipline_findings_conviction_unset_summary() -> None:
    """Acceptance criterion (proposal §6, R11): N/N conviction-unset theses
    yield one portfolio-level summary line, not per-thesis noise."""
    row = {
        "revisit_due_at": datetime(2026, 8, 1),
        "opened_at": datetime(2026, 6, 1),
        "timeline_days": 180,
        "actual_entry_price": Decimal("10"),
        "target_price": Decimal("15"),
        "stop_price": Decimal("9"),
        "conviction_level": None,
    }
    thesis_rows = [{"symbol": "A.AU", **row}, {"symbol": "B.AU", **row}]
    price_rows = [
        {"symbol": "A.AU", "close": Decimal("11")},
        {"symbol": "B.AU", "close": Decimal("11")},
    ]
    conn = _disc_conn(thesis_rows=thesis_rows, price_rows=price_rows)

    findings = asyncio.run(_discipline_findings(conn, date(2026, 7, 1)))

    conv = next(f for f in findings if f.check == "conviction_unset")
    assert "2/2" in conv.message
    assert conv.symbol is None


def test_discipline_findings_foreign_thesis_uses_native_prices_not_aud() -> None:
    """R10 regression: a foreign thesis's entry/target/current all stay in the
    holding's native currency (USD) — no AUD/native mixing, so a HUBS-style
    false −29% from dividing an AUD cost base cannot recur here."""
    thesis_rows = [
        {
            "symbol": "HUBS.NYSE",
            "revisit_due_at": datetime(2026, 8, 1),
            "opened_at": datetime(2026, 1, 1),
            "timeline_days": 365,
            "actual_entry_price": Decimal("187.54"),
            "target_price": Decimal("260"),
            "stop_price": Decimal("150"),
            "conviction_level": 4,
        }
    ]
    price_rows = [{"symbol": "HUBS.NYSE", "close": Decimal("205.79")}]  # native USD, ~+9.8%
    conn = _disc_conn(thesis_rows=thesis_rows, price_rows=price_rows)

    findings = asyncio.run(_discipline_findings(conn, date(2026, 7, 13)))

    assert not any(f.check == "data_sanity" for f in findings)


def test_discipline_findings_concentration_uses_fx_converted_market_value() -> None:
    """A foreign holding's market value is converted forward (native / FX ->
    AUD) before the concentration check, never AUD / quantity backward (R10)."""
    holding_rows = [
        {"symbol": "BHP.AU", "quantity": Decimal("50")},
        {"symbol": "HUBS.NYSE", "quantity": Decimal("24")},
    ]
    price_rows = [
        {"symbol": "BHP.AU", "close": Decimal("10")},
        {"symbol": "HUBS.NYSE", "close": Decimal("205")},
    ]
    fx_rows = [{"fx_rate_audusd": Decimal("0.6450")}]
    conn = _disc_conn(holding_rows=holding_rows, price_rows=price_rows, fx_rows=fx_rows)

    findings = asyncio.run(_discipline_findings(conn, date(2026, 7, 13)))

    # BHP: 50 * $10 = $500 AUD (~6% of the converted total) -> no finding.
    # HUBS: 24 * $205 / 0.6450 ~= $7,627.91 AUD (~94% of total) -> red.
    hubs_conc = next(
        f for f in findings if f.check == "concentration" and f.symbol == "HUBS.NYSE"
    )
    assert hubs_conc.level == DisciplineLevel.red
    assert not any(
        f.check == "concentration" and f.symbol == "BHP.AU" for f in findings
    )


def test_discipline_findings_no_fx_rate_skips_foreign_holding() -> None:
    """No AUDUSD rate available -> the foreign holding is omitted from the
    concentration weighting rather than mis-converted (silent omission is
    preferable to a wrong-currency figure here, mirroring wealth_state.py)."""
    holding_rows = [{"symbol": "HUBS.NYSE", "quantity": Decimal("24")}]
    price_rows = [{"symbol": "HUBS.NYSE", "close": Decimal("205")}]
    conn = _disc_conn(holding_rows=holding_rows, price_rows=price_rows)

    findings = asyncio.run(_discipline_findings(conn, date(2026, 7, 13)))

    assert not any(f.check == "concentration" for f in findings)


# ---------------------------------------------------------------------------
# collect() wiring for discipline_findings (PR2a)
# ---------------------------------------------------------------------------


def test_collect_discipline_findings_quiet_by_default() -> None:
    today = date(2026, 5, 22)
    conn = _make_conn(
        regime_row={"regime": "bear"},
        holdings_count=0,
        signal_rows=[],
        tax_rows=[],
        reg_rows=[],
        hold_syms=[],
        fail_rows=[],
    )

    @asynccontextmanager
    async def fake_acquire():
        yield conn

    with patch("asxos.brief.compose.acquire", fake_acquire):
        data = asyncio.run(collect(today))

    assert data.discipline_findings == []


def test_collect_discipline_section_failure_isolated() -> None:
    """A broken discipline query must not take the rest of the brief down with
    it (CLAUDE.md #10) — it surfaces as one loud error finding instead."""
    today = date(2026, 5, 22)
    conn = _make_conn(
        regime_row={"regime": "bear"},
        holdings_count=1,
        signal_rows=[],
        tax_rows=[],
        reg_rows=[],
        hold_syms=[],
        fail_rows=[],
    )

    @asynccontextmanager
    async def fake_acquire():
        yield conn

    with (
        patch("asxos.brief.compose.acquire", fake_acquire),
        patch(
            "asxos.brief.compose._discipline_findings",
            AsyncMock(side_effect=RuntimeError("boom")),
        ),
    ):
        data = asyncio.run(collect(today))

    assert data.holdings_count == 1  # sibling sections unaffected
    assert len(data.discipline_findings) == 1
    assert data.discipline_findings[0].level == DisciplineLevel.error
    assert "boom" in data.discipline_findings[0].message
