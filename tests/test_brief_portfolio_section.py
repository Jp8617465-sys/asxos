"""
Tests for the portfolio section (section 6) of the morning brief (M13.7).

Coverage (plan I.10 / plan M13.7 prompt):
  - Section omitted when ASXOS_PORTFOLIO_BRIEF_ENABLED=0
  - Section omitted when ASXOS_PERSONAL_USE=0
  - Section omitted when both flags are 0
  - Section omitted when no fresh build_portfolio run exists (freshness gate)
  - Section populated when both flags are 1 and a fresh run exists
  - Top-buys / top-sells limited to 3 each
  - Turnover equals total_buy + total_sell
  - HTML rendering omits section 6 when portfolio_section is None
  - HTML rendering includes section 6 when portfolio_section is populated
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from asxos.brief.compose import (
    BriefData,
    PortfolioSection,
    PortfolioTradeSummary,
    _portfolio_section,
    render_html,
)

_TODAY = date(2026, 5, 23)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_conn_no_run() -> AsyncMock:
    """Connection that returns no matching rebalance_runs row."""
    conn = AsyncMock()
    conn.fetchrow.return_value = None
    return conn


def _make_conn_with_run(
    run_id: int = 1,
    run_as_of: date = date(2026, 5, 22),
    trades: list[dict] | None = None,
) -> AsyncMock:
    """Connection that returns a matching run and trade rows."""
    if trades is None:
        trades = [
            {"symbol": "BHP", "side": "buy",  "delta_aud": 5000},
            {"symbol": "CBA", "side": "buy",  "delta_aud": 3000},
            {"symbol": "RIO", "side": "buy",  "delta_aud": 1000},
            {"symbol": "WBC", "side": "sell", "delta_aud": -4000},
            {"symbol": "ANZ", "side": "sell", "delta_aud": -2000},
        ]

    conn = AsyncMock()

    # fetchrow for the freshness gate query
    run_record = MagicMock()
    run_record.__getitem__ = lambda self, k: {"run_id": run_id, "as_of": run_as_of}[k]
    conn.fetchrow.return_value = run_record

    # fetch for the trades query
    trade_records = []
    for t in trades:
        r = MagicMock()
        r.__getitem__ = lambda self, k, t=t: t[k]
        r.__iter__ = lambda self, t=t: iter(t)
        trade_records.append(r)
    conn.fetch.return_value = trade_records

    return conn


def _minimal_brief_data(portfolio_section: PortfolioSection | None = None) -> BriefData:
    return BriefData(
        as_of=_TODAY,
        regime="neutral",
        holdings_count=5,
        portfolio_section=portfolio_section,
    )


# ---------------------------------------------------------------------------
# Env-flag gate tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_portfolio_section_both_flags_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    """Both flags unset → None (section omitted)."""
    monkeypatch.delenv("ASXOS_PERSONAL_USE", raising=False)
    monkeypatch.delenv("ASXOS_PORTFOLIO_BRIEF_ENABLED", raising=False)
    conn = AsyncMock()
    result = await _portfolio_section(conn, _TODAY)
    assert result is None
    conn.fetchrow.assert_not_called()


@pytest.mark.asyncio
async def test_portfolio_section_personal_use_only(monkeypatch: pytest.MonkeyPatch) -> None:
    """ASXOS_PERSONAL_USE=1 but ASXOS_PORTFOLIO_BRIEF_ENABLED unset → None."""
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    monkeypatch.delenv("ASXOS_PORTFOLIO_BRIEF_ENABLED", raising=False)
    conn = AsyncMock()
    result = await _portfolio_section(conn, _TODAY)
    assert result is None
    conn.fetchrow.assert_not_called()


@pytest.mark.asyncio
async def test_portfolio_section_brief_enabled_only(monkeypatch: pytest.MonkeyPatch) -> None:
    """ASXOS_PORTFOLIO_BRIEF_ENABLED=1 but ASXOS_PERSONAL_USE unset → None."""
    monkeypatch.delenv("ASXOS_PERSONAL_USE", raising=False)
    monkeypatch.setenv("ASXOS_PORTFOLIO_BRIEF_ENABLED", "1")
    conn = AsyncMock()
    result = await _portfolio_section(conn, _TODAY)
    assert result is None
    conn.fetchrow.assert_not_called()


@pytest.mark.asyncio
async def test_portfolio_section_flags_set_to_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    """Both flags explicitly "0" → None."""
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "0")
    monkeypatch.setenv("ASXOS_PORTFOLIO_BRIEF_ENABLED", "0")
    conn = AsyncMock()
    result = await _portfolio_section(conn, _TODAY)
    assert result is None


# ---------------------------------------------------------------------------
# Freshness gate tests (both env flags set)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_portfolio_section_no_fresh_run(monkeypatch: pytest.MonkeyPatch) -> None:
    """Both flags set but no fresh successful build_portfolio run → None."""
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    monkeypatch.setenv("ASXOS_PORTFOLIO_BRIEF_ENABLED", "1")
    conn = _make_conn_no_run()
    result = await _portfolio_section(conn, _TODAY)
    assert result is None
    conn.fetchrow.assert_awaited_once()


@pytest.mark.asyncio
async def test_portfolio_section_returns_data(monkeypatch: pytest.MonkeyPatch) -> None:
    """Both flags set + fresh run → PortfolioSection with correct data."""
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    monkeypatch.setenv("ASXOS_PORTFOLIO_BRIEF_ENABLED", "1")
    conn = _make_conn_with_run()
    result = await _portfolio_section(conn, _TODAY)
    assert result is not None
    assert isinstance(result, PortfolioSection)
    assert result.run_id == 1
    assert result.run_as_of == date(2026, 5, 22)


@pytest.mark.asyncio
async def test_portfolio_section_top_buys_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    """Top buys capped at 3 even with more buy trades."""
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    monkeypatch.setenv("ASXOS_PORTFOLIO_BRIEF_ENABLED", "1")
    trades = [
        {"symbol": f"B{i:02d}", "side": "buy", "delta_aud": 5000 - i * 100}
        for i in range(5)
    ]
    conn = _make_conn_with_run(trades=trades)
    result = await _portfolio_section(conn, _TODAY)
    assert result is not None
    assert len(result.top_buys) == 3


@pytest.mark.asyncio
async def test_portfolio_section_top_sells_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    """Top sells capped at 3."""
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    monkeypatch.setenv("ASXOS_PORTFOLIO_BRIEF_ENABLED", "1")
    trades = [
        {"symbol": f"S{i:02d}", "side": "sell", "delta_aud": -(5000 - i * 100)}
        for i in range(5)
    ]
    conn = _make_conn_with_run(trades=trades)
    result = await _portfolio_section(conn, _TODAY)
    assert result is not None
    assert len(result.top_sells) == 3


@pytest.mark.asyncio
async def test_portfolio_section_turnover_equals_buy_plus_sell(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """turnover_aud == total_buy_aud + total_sell_aud."""
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    monkeypatch.setenv("ASXOS_PORTFOLIO_BRIEF_ENABLED", "1")
    trades = [
        {"symbol": "BHP", "side": "buy",  "delta_aud": 5000},
        {"symbol": "WBC", "side": "sell", "delta_aud": -3000},
    ]
    conn = _make_conn_with_run(trades=trades)
    result = await _portfolio_section(conn, _TODAY)
    assert result is not None
    assert result.total_buy_aud == Decimal("5000")
    assert result.total_sell_aud == Decimal("3000")
    assert result.turnover_aud == Decimal("8000")


@pytest.mark.asyncio
async def test_portfolio_section_buy_side_classification(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """top_buys contains only buy-side trades."""
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    monkeypatch.setenv("ASXOS_PORTFOLIO_BRIEF_ENABLED", "1")
    trades = [
        {"symbol": "BHP", "side": "buy",  "delta_aud": 5000},
        {"symbol": "WBC", "side": "sell", "delta_aud": -3000},
    ]
    conn = _make_conn_with_run(trades=trades)
    result = await _portfolio_section(conn, _TODAY)
    assert result is not None
    assert all(t.side == "buy" for t in result.top_buys)
    assert all(t.side == "sell" for t in result.top_sells)


# ---------------------------------------------------------------------------
# HTML rendering gate tests
# ---------------------------------------------------------------------------


def test_html_omits_portfolio_section_when_none() -> None:
    """Section 6 header absent from HTML when portfolio_section is None."""
    data = _minimal_brief_data(portfolio_section=None)
    html = render_html(data)
    assert "Portfolio adjustments" not in html
    assert "Top buys" not in html
    assert "Top sells" not in html


def test_html_includes_portfolio_section_when_present() -> None:
    """Section 6 appears in HTML when portfolio_section is set."""
    section = PortfolioSection(
        run_id=42,
        run_as_of=date(2026, 5, 22),
        top_buys=[
            PortfolioTradeSummary(symbol="BHP", side="buy", delta_aud=Decimal("5000")),
        ],
        top_sells=[
            PortfolioTradeSummary(symbol="WBC", side="sell", delta_aud=Decimal("-3000")),
        ],
        total_buy_aud=Decimal("5000"),
        total_sell_aud=Decimal("3000"),
        turnover_aud=Decimal("8000"),
    )
    data = _minimal_brief_data(portfolio_section=section)
    html = render_html(data)
    assert "Portfolio adjustments" in html
    assert "run #42" in html
    assert "BHP" in html
    assert "WBC" in html
    assert "Top buys" in html
    assert "Top sells" in html


def test_html_shows_run_id() -> None:
    """Run ID appears in the section header."""
    section = PortfolioSection(
        run_id=99,
        run_as_of=date(2026, 5, 22),
        top_buys=[],
        top_sells=[],
        total_buy_aud=Decimal("0"),
        total_sell_aud=Decimal("0"),
        turnover_aud=Decimal("0"),
    )
    html = render_html(_minimal_brief_data(portfolio_section=section))
    assert "run #99" in html


def test_html_section_6_has_personal_use_note() -> None:
    """Section 6 includes the s766B personal-use note."""
    section = PortfolioSection(
        run_id=1,
        run_as_of=_TODAY,
        top_buys=[],
        top_sells=[],
        total_buy_aud=Decimal("0"),
        total_sell_aud=Decimal("0"),
        turnover_aud=Decimal("0"),
    )
    html = render_html(_minimal_brief_data(portfolio_section=section))
    assert "s766B" in html
    assert "personal use" in html.lower()
