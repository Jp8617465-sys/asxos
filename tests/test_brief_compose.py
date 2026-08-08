"""
Brief composition tests.

`render_html` is pure over BriefData — we synthesize the dataclass
directly. `collect` is exercised under a MagicMock conn (`_make_conn`) that
routes each query it issues to canned rows.

M14a additions: NewsItem dataclass, news section HTML, _news_section() gating.
A mocked conn returns its canned rows whatever the WHERE clause says, so the
freshness gate's own SQL is asserted directly instead — see the
`_news_ingest_fresh` block at the end of this file.
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
    DisciplineFinding,
    DisciplineLevel,
    JobFailure,
    NewsItem,
    RegulatoryHit,
    SignalChange,
    _cgt_boundary_findings,
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
# Model A shelved — calm state (rule #11) replaces the dead-signal banners
# ---------------------------------------------------------------------------


def test_render_html_calm_model_shelved_state() -> None:
    """0 approved models (the deliberate rule #11 shelf) → one calm 'Model A
    shelved' line, not the red 'unavailable'/'Signals stale'/caveat noise, and no
    Model-A 'Signal changes' section."""
    html = render_html(_brief(model_shelved=True, regime=None, latest_signal_date=None))
    assert "Model A" in html and "shelved" in html
    assert "unavailable" not in html
    assert "Signals stale" not in html
    assert "Signal caveat:" not in html
    assert "Signal changes on holdings" not in html


def test_render_html_shelved_still_warns_on_genuine_price_staleness() -> None:
    """Shelving Model A must NOT suppress a genuine, model-independent
    price-staleness warning (James's guardrail: hide only shelf noise)."""
    html = render_html(_brief(model_shelved=True, latest_price_date=date(2026, 5, 1)))
    assert "Data freshness warning" in html
    assert "Prices stale" in html
    assert "Signals stale" not in html


def test_render_html_not_shelved_keeps_signal_surface() -> None:
    """The single-approved-model path is unchanged: caveat + signal-changes render."""
    html = render_html(_brief())  # model_shelved defaults False
    assert "Signal caveat:" in html
    assert "Signal changes on holdings" in html


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
    # "No lots crossing" retired with the standalone tax-actions table —
    # CGT boundary facts now render as gated discipline findings.
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


# ---------------------------------------------------------------------------
# PR2b — discipline section render (brief.html.j2)
# ---------------------------------------------------------------------------

_REVISIT_OVERDUE_FINDING = DisciplineFinding(
    check="revisit_overdue",
    level=DisciplineLevel.red,
    message="CBA.AU: review overdue by 16d (due 2026-06-27)",
    symbol="CBA.AU",
)
_TRAJECTORY_ERROR_FINDING = DisciplineFinding(
    check="trajectory",
    level=DisciplineLevel.error,
    message="⚠ trajectory could not run for BHP.AU: bad data",
    symbol="BHP.AU",
)


def test_render_html_discipline_section_absent_when_empty() -> None:
    """Quiet by default (proposal §6): no findings -> no section header at all."""
    html = render_html(_brief(discipline_findings=[]))
    assert "Portfolio discipline" not in html


def test_render_html_discipline_section_shows_findings() -> None:
    html = render_html(
        _brief(
            discipline_findings=[
                _REVISIT_OVERDUE_FINDING,
                DisciplineFinding(
                    check="conviction_unset",
                    level=DisciplineLevel.yellow,
                    message="conviction unset on 13/13 theses — size-vs-conviction check disabled (R11)",
                ),
            ]
        )
    )
    assert "Portfolio discipline" in html
    assert "CBA.AU: review overdue by 16d" in html
    assert 'class="disc-red"' in html
    assert "conviction unset on 13/13 theses" in html
    assert 'class="disc-yellow"' in html


def test_render_html_discipline_error_finding_shows_banner() -> None:
    """A check that could not run (CLAUDE.md #10) renders loudly in its own
    banner, distinct from the plain findings list."""
    html = render_html(_brief(discipline_findings=[_TRAJECTORY_ERROR_FINDING]))
    assert "Discipline checks that could not run" in html
    assert "⚠ trajectory could not run for BHP.AU" in html


def test_render_html_discipline_errors_and_items_both_present() -> None:
    """A findings list mixing an error with clean findings shows both: the
    error in its own banner, the rest in the plain list — neither hides the
    other (CLAUDE.md #10, a check failure must not obscure other findings)."""
    html = render_html(
        _brief(discipline_findings=[_REVISIT_OVERDUE_FINDING, _TRAJECTORY_ERROR_FINDING])
    )
    assert "Discipline checks that could not run" in html
    assert "⚠ trajectory could not run for BHP.AU" in html
    assert "CBA.AU: review overdue by 16d" in html
    assert 'class="disc-red"' in html


def test_render_html_discipline_section_escapes_user_content() -> None:
    html = render_html(
        _brief(
            discipline_findings=[
                DisciplineFinding(
                    check="data_sanity",
                    level=DisciplineLevel.red,
                    message="<script>alert(1)</script>",
                ),
            ]
        )
    )
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


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


def test_render_html_shows_cgt_boundary_finding() -> None:
    """The CGT-boundary fact now renders as an info discipline line, folded from
    the retired standalone 'Tax actions' table."""
    html = render_html(
        _brief(
            discipline_findings=[
                DisciplineFinding(
                    check="cgt_discount_boundary",
                    level=DisciplineLevel.info,
                    symbol="CBA.AU",
                    message=(
                        "CBA.AU: lot 42 (acquired 2025-06-01) reaches the 12-month "
                        "CGT-discount threshold on 2026-06-02 — 10 day(s) away "
                        "(s 115-25(1) ITAA 1997)."
                    ),
                )
            ]
        )
    )
    assert "CBA.AU" in html
    assert "12-month CGT-discount threshold" in html
    assert 'class="disc-info"' in html
    # The standalone "Tax actions" table is retired — the fact lives in the digest.
    assert "Tax actions" not in html


def test_cgt_boundary_gate_off_returns_empty() -> None:
    conn = MagicMock()
    conn.fetch = AsyncMock(return_value=[])
    with patch.dict(os.environ, {"ASXOS_PERSONAL_USE": "0"}):
        out = asyncio.run(_cgt_boundary_findings(conn, date(2026, 7, 16)))
    assert out == []
    conn.fetch.assert_not_awaited()  # short-circuits before any DB read


def test_cgt_boundary_flags_only_in_window_lots() -> None:
    conn = MagicMock()
    conn.fetch = AsyncMock(
        return_value=[
            {"id": 42, "symbol": "CBA.AU", "acquired_at": date(2025, 8, 1)},  # eligible 2026-08-02 → 17d (in window)
            {"id": 7, "symbol": "BHP.AU", "acquired_at": date(2025, 7, 1)},   # eligible 2026-07-02 → already (0, skip)
            {"id": 9, "symbol": "WES.AU", "acquired_at": date(2026, 1, 1)},   # eligible 2027-01-02 → ~170d (skip)
        ]
    )
    with patch.dict(os.environ, {"ASXOS_PERSONAL_USE": "1"}):
        out = asyncio.run(_cgt_boundary_findings(conn, date(2026, 7, 16)))
    assert len(out) == 1
    f = out[0]
    assert f.check == "cgt_discount_boundary"
    assert f.level == DisciplineLevel.info
    assert f.symbol == "CBA.AU"
    assert "12-month CGT-discount threshold" in f.message
    assert "17 day(s)" in f.message
    # s766B: evidence-only — no trade direction. Word-boundary match so that
    # "threshold" does not falsely trip on "hold".
    import re

    assert not re.search(
        r"\b(sell|trim|exit|hold|defer|recommend|should)\b", f.message.lower()
    )


def test_cgt_boundary_malformed_acquired_at_is_loud_error() -> None:
    conn = MagicMock()
    conn.fetch = AsyncMock(
        return_value=[{"id": 1, "symbol": "XYZ.AU", "acquired_at": None}]
    )
    with patch.dict(os.environ, {"ASXOS_PERSONAL_USE": "1"}):
        out = asyncio.run(_cgt_boundary_findings(conn, date(2026, 7, 16)))
    assert len(out) == 1
    assert out[0].level == DisciplineLevel.error
    assert out[0].symbol == "XYZ.AU"
    assert "could not run" in out[0].message


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
    assert data.model_shelved is True   # 0 approved == the calm shelf state


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
    assert data.model_shelved is False  # >1 approved is a misconfig, NOT the shelf


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
        news_job_rows=[{"as_of": today, "status": "success", "error_message": None}],
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
        news_job_rows=[{"as_of": today, "status": "success", "error_message": None}],
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
    """news_items=[] when no recent ingest_news run passes the freshness gate.

    "Passes" means the LATEST run was clean (success, NULL error_message) —
    not a row count. The mock returns no rows for
    the gate query either way, so this covers both halves at the collect() level;
    the SQL itself is pinned by test_news_ingest_fresh_reads_the_latest_run_*.
    """
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
):
    thesis_rows = thesis_rows or []
    holding_rows = holding_rows or []
    price_rows = price_rows or []
    fx_rows = fx_rows or []

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
        return []

    conn = MagicMock()
    conn.fetch = AsyncMock(side_effect=_fetch)
    return conn


_PERSONAL_USE_ON = {"ASXOS_PERSONAL_USE": "1"}


def test_discipline_findings_gated_off_by_default() -> None:
    """Proposal §6: gated on ASXOS_PERSONAL_USE=1 — off (the test-suite default
    unset state) means quiet, even with findings that would otherwise fire."""
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

    with patch.dict(os.environ, {"ASXOS_PERSONAL_USE": "0"}):
        findings = asyncio.run(_discipline_findings(conn, date(2026, 7, 13)))

    assert findings == []
    conn.fetch.assert_not_called()  # gate short-circuits before any query


def test_discipline_findings_quiet_when_no_theses_or_holdings() -> None:
    conn = _disc_conn()
    with patch.dict(os.environ, _PERSONAL_USE_ON):
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

    with patch.dict(os.environ, _PERSONAL_USE_ON):
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

    with patch.dict(os.environ, _PERSONAL_USE_ON):
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

    with patch.dict(os.environ, _PERSONAL_USE_ON):
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

    with patch.dict(os.environ, _PERSONAL_USE_ON):
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

    with patch.dict(os.environ, _PERSONAL_USE_ON):
        findings = asyncio.run(_discipline_findings(conn, date(2026, 7, 13)))

    assert not any(f.check == "concentration" for f in findings)


def test_discipline_findings_appends_broker_matching_unrealised_return() -> None:
    """The loader appends a per-holding native unrealised-return line — the honest,
    broker-matching replacement for the removed false −75.7% portfolio line.
    HUBS 187.54 → 224.57 = +19.7% (the broker's FX-neutral headline)."""
    thesis_rows = [
        {
            "symbol": "HUBS.NYSE",
            "revisit_due_at": datetime(2026, 8, 1),
            "opened_at": datetime(2026, 1, 1),
            "timeline_days": 365,
            "actual_entry_price": Decimal("187.54"),
            "target_price": Decimal("318"),
            "stop_price": Decimal("150"),
            "conviction_level": 4,
        }
    ]
    price_rows = [{"symbol": "HUBS.NYSE", "close": Decimal("224.57")}]
    conn = _disc_conn(thesis_rows=thesis_rows, price_rows=price_rows)

    with patch.dict(os.environ, _PERSONAL_USE_ON):
        findings = asyncio.run(_discipline_findings(conn, date(2026, 7, 16)))

    pnl = next(f for f in findings if f.check == "unrealised_return")
    assert pnl.level == DisciplineLevel.info
    assert "+19.7% unrealised since entry" in pnl.message
    assert "USD 187.54 → 224.57" in pnl.message
    # The false portfolio "total return vs benchmark / lagging" line is gone.
    joined = " ".join(f.message for f in findings)
    assert "lagging" not in joined
    assert "benchmark" not in joined.lower()


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


# ---------------------------------------------------------------------------
# _news_ingest_fresh — the false-green regression
# (docs/market-trends-report-2026-08-05.md §1)
#
# The freshness gate previously keyed off `status='success'` alone — the same
# field as the surface's ship condition in dark-launch-exit-plan.md surface #2.
# One defect therefore cleared both: 22 consecutive ingest_news runs recorded
# status='success' with rows_written=0 while holding_news stayed empty, and this
# gate passed every one of them.
# ---------------------------------------------------------------------------


def _run_row(day: int, *, status: str = "success", error: str | None = None) -> dict:
    """One ingest_news job_runs row, dated 2026-05-<day>."""
    return {"as_of": date(2026, 5, day), "status": status, "error_message": error}


def _job_runs_conn(*runs: dict):
    """A conn that models job_runs well enough to fail a wrong freshness query.

    Applies both window bounds, the ORDER BY and the LIMIT itself, and honours
    any status/error_message/rows_written predicate that appears in the WHERE
    clause even though the correct query now has none — a mock returning canned
    rows regardless of the WHERE clause scores the defect and the fix
    identically, which is how the last two wrong gates survived review.
    """
    conn = MagicMock()

    async def _fetch(query, *args, **kwargs):
        sql = " ".join(query.split())
        lo = args[0] if len(args) > 0 else None
        hi = args[1] if len(args) > 1 and "as_of <= $2" in sql else None
        rows = [
            r for r in runs
            if (lo is None or r["as_of"] >= lo) and (hi is None or r["as_of"] <= hi)
        ]
        if "status = 'success'" in sql:
            rows = [r for r in rows if r["status"] == "success"]
        if "error_message IS NULL" in sql:
            rows = [r for r in rows if r["error_message"] is None]
        if "rows_written > 0" in sql:
            rows = []  # column not modelled; a query relying on it gets nothing
        rows = sorted(rows, key=lambda r: r["as_of"],
                      reverse="ORDER BY as_of DESC" in sql)
        return rows[:1] if "LIMIT 1" in sql else rows

    conn.fetch = AsyncMock(side_effect=_fetch)
    return conn


_GATE_TODAY = date(2026, 5, 22)
_DEGRADED_NOTE = "ingest_news degraded: malformed=2"


def test_news_ingest_fresh_reads_the_latest_run_and_judges_it_in_python() -> None:
    """INVERTED from test_news_ingest_fresh_requires_rows_written_not_just_status.

    That test pinned the overcorrection — it asserted `rows_written > 0` in the
    SQL. A row count on the WRITER is not a health signal for the READER:
    holding_news keeps 7 days, the brief reads 24h, so a quiet ingest this
    morning would hide an article ingested yesterday that is still current.

    The health predicates must also NOT be WHERE filters: next to LIMIT 1 they
    ask "did ANY clean run happen?", so an older clean run conceals the latest
    degraded one. The gate selects the latest run in a both-sided window and
    judges status/error_message in Python.
    """
    from asxos.brief.compose import _news_ingest_fresh

    captured: list[str] = []
    conn = MagicMock()

    async def _fetch(query, *args, **kwargs):
        captured.append(" ".join(query.split()))
        return []

    conn.fetch = AsyncMock(side_effect=_fetch)
    assert asyncio.run(_news_ingest_fresh(conn, _GATE_TODAY)) is False

    sql = captured[0]
    assert "ORDER BY as_of DESC" in sql, f"must select the LATEST run: {sql}"
    assert "as_of <= $2" in sql, f"window must be bounded above too: {sql}"
    assert "rows_written" not in sql, f"row count is not a health signal: {sql}"
    assert "status = 'success'" not in sql, f"health must not be a WHERE filter: {sql}"
    assert "error_message" not in sql.split("WHERE")[1], (
        f"health must not be a WHERE filter: {sql}"
    )


def test_news_ingest_fresh_true_when_a_qualifying_run_exists() -> None:
    """The latest run succeeded with no degraded note — gate opens."""
    from asxos.brief.compose import _news_ingest_fresh

    conn = _job_runs_conn(_run_row(22))
    assert asyncio.run(_news_ingest_fresh(conn, _GATE_TODAY)) is True


def test_latest_degraded_run_is_not_concealed_by_an_older_clean_one() -> None:
    """The concealment itself: yesterday clean, today degraded → NOT fresh."""
    from asxos.brief.compose import _news_ingest_fresh

    conn = _job_runs_conn(_run_row(21), _run_row(22, error=_DEGRADED_NOTE))
    assert asyncio.run(_news_ingest_fresh(conn, _GATE_TODAY)) is False


def test_older_degraded_run_does_not_veto_a_clean_latest_one() -> None:
    """Negative control: without it, 'False whenever any run is degraded' would
    pass the concealment test and wedge the section shut after every recovered
    blip."""
    from asxos.brief.compose import _news_ingest_fresh

    conn = _job_runs_conn(_run_row(21, error=_DEGRADED_NOTE), _run_row(22))
    assert asyncio.run(_news_ingest_fresh(conn, _GATE_TODAY)) is True


def test_latest_failed_run_is_not_fresh_and_no_run_is_not_fresh() -> None:
    from asxos.brief.compose import _news_ingest_fresh

    conn = _job_runs_conn(_run_row(21), _run_row(22, status="failure"))
    assert asyncio.run(_news_ingest_fresh(conn, _GATE_TODAY)) is False
    assert asyncio.run(_news_ingest_fresh(_job_runs_conn(), _GATE_TODAY)) is False


def test_a_future_run_cannot_make_a_historical_brief_fresh() -> None:
    """collect() takes an explicit as_of, so briefs are re-run for past days.

    Without the upper bound, "latest run in window" means "latest run EVER from
    that date onward" — tomorrow's clean run would retroactively open the gate
    on a day whose own ingest failed. And symmetrically, a future degraded run
    must not close a gate that was legitimately open on the day.
    """
    from asxos.brief.compose import _news_ingest_fresh

    conn = _job_runs_conn(_run_row(22, status="failure"), _run_row(23))
    assert asyncio.run(_news_ingest_fresh(conn, _GATE_TODAY)) is False

    conn = _job_runs_conn(_run_row(22), _run_row(23, error=_DEGRADED_NOTE))
    assert asyncio.run(_news_ingest_fresh(conn, _GATE_TODAY)) is True


# ---------------------------------------------------------------------------
# M0: source/publisher must be visible
#
# The rendered item previously carried instrument, citation and publication
# time but no publisher. `holding_news` has no source column and the vendor
# does not reliably supply one, so `source` is derived from the citation host —
# the strongest publisher claim the data actually supports, always available
# because `url` is NOT NULL.
# ---------------------------------------------------------------------------


def _news(url: str) -> NewsItem:
    return NewsItem(symbols=["HUBS.NYSE"], title="HubSpot beats Q2",
                    url=url, published_at=date(2026, 8, 8), sentiment="")


def test_source_strips_scheme_and_www() -> None:
    assert _news("https://www.reuters.com/tech/x").source == "reuters.com"
    assert _news("https://reuters.com/tech/x").source == "reuters.com"
    assert _news("http://SUB.AFR.COM.AU/story").source == "sub.afr.com.au"


def test_source_is_empty_when_host_unparseable() -> None:
    """Must not invent an attribution. Empty lets the template omit it."""
    assert _news("not-a-url").source == ""
    assert _news("").source == ""


def test_render_shows_all_four_required_fields() -> None:
    """M0: instrument, source, publication time and citation all visible."""
    html = render_html(_brief(news_items=[_news("https://www.reuters.com/tech/hubspot")]))
    assert "HUBS.NYSE" in html, "instrument"
    assert "reuters.com" in html, "source/publisher"
    assert "2026-08-08" in html, "publication time"
    assert 'href="https://www.reuters.com/tech/hubspot"' in html, "citation"


def test_render_omits_source_rather_than_printing_empty() -> None:
    """An unattributable item shows no publisher, not a blank one."""
    html = render_html(_brief(news_items=[_news("not-a-url")]))
    assert 'class="source"' not in html
    assert "HubSpot beats Q2" in html, "the item itself still renders"


def test_source_strips_bidi_override_that_survives_autoescape() -> None:
    """A hostile host must not display as a different publisher than it links to.

    Autoescape neutralises `< > & " '` only. Bidi controls are category Cf and
    pass through it verbatim, so an unterminated U+202E renders the host
    reversed — displaying "reuters.com" while the href goes elsewhere — and
    bleeds past </span> to reverse the rest of the item.
    """
    item = _news("https://‮moc.sretuer/article")
    assert "‮" not in item.source, "bidi override must not reach the brief"
    assert item.source == "moc.sretuer", "host survives, minus the control char"

    # The href still carries the raw URL, and that is correct: it is the genuine
    # citation, and rewriting it would misrepresent where the article actually
    # lives. Attribute values are not rendered as text, so the display risk is
    # confined to the visible span — which must be clean.
    import re

    html = render_html(_brief(news_items=[item]))
    span = re.search(r'<span class="source">(.*?)</span>', html, re.S)
    assert span is not None, "source span should render"
    assert "‮" not in span.group(1), "no bidi control in displayed text"


def test_source_is_length_bounded() -> None:
    """Untrusted strings are capped everywhere else in this codebase."""
    assert len(_news("https://" + "a" * 400 + ".com/x").source) <= 64
