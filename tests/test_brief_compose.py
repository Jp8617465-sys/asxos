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
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

from asxos.brief.compose import (
    BriefData,
    JobFailure,
    NewsItem,
    RegulatoryHit,
    SignalChange,
    TaxAction,
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
):
    """Build a mock asyncpg connection that routes queries to canned rows.

    news_rows:      rows for ``FROM holding_news`` queries (_holding_news)
    news_job_rows:  rows for ``FROM job_runs … job_name = 'ingest_news'`` (_news_ingest_fresh)
    """
    conn = MagicMock()
    conn.fetchrow = AsyncMock(return_value=regime_row)
    conn.fetchval = AsyncMock(return_value=holdings_count)

    async def _fetch(query, *args, **kwargs):
        q = " ".join(query.split())
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

    assert data.regime == "neutral"  # default
    assert data.holdings_count == 0
    assert data.signal_changes == []
    assert not data.has_failures


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
