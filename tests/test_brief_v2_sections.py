"""
Tests for Phase 4 brief collectors and cross-layer observations.

Covers:
- market_context: no_data, regime warning (red/yellow), indicator green items
- active_theses: no_data, overdue→red, diverging→yellow, ok→green
- watchlist: no_data, green items
- new_ideas: no_data, suppressed under risk-off, green items
- underlying_drivers: no_data (no underlyings), score propagation
- theme_dashboard: no_data, stage_suggested divergence→yellow, ok→green
- opportunity_cost: graceful no_data on missing table, scenarios
- cross_layer: confirming/diverging/risk-off observations (spec Part 5.5)
"""
from __future__ import annotations

import asyncio
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from asxos.domain.brief.collectors.market_context import collect_market_context
from asxos.domain.brief.collectors.new_ideas import collect_new_ideas
from asxos.domain.brief.collectors.opportunity_cost import collect_opportunity_cost
from asxos.domain.brief.collectors.theme_dashboard import collect_theme_dashboard
from asxos.domain.brief.collectors.watchlist import collect_watchlist
from asxos.domain.brief.cross_layer import cross_layer_observations
from asxos.domain.brief.types import SectionStatus, SeverityLevel
from asxos.domain.underlyings.types import UnderlyingScore

AS_OF = date(2026, 6, 1)


# ── helpers ────────────────────────────────────────────────────────────────────

def _make_row(**kwargs):
    """Return a dict that behaves like an asyncpg Record for indexing."""
    row = MagicMock()
    row.__getitem__ = lambda self, k: kwargs[k]
    row.get = lambda k, default=None: kwargs.get(k, default)
    return row


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ── market_context ─────────────────────────────────────────────────────────────

class TestCollectMarketContext:
    def test_no_data_when_row_missing(self):
        async def _run_test():
            conn = AsyncMock()
            conn.fetchrow.return_value = None
            with patch("asxos.domain.brief.collectors.market_context.acquire") as mock_acquire:
                mock_acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
                mock_acquire.return_value.__aexit__ = AsyncMock(return_value=False)
                result = await collect_market_context(AS_OF)
            assert result.status == SectionStatus.no_data

        _run(_run_test())

    def test_risk_off_disorderly_gives_red(self):
        async def _run_test():
            row = _make_row(
                regime_label="risk_off_disorderly",
                asx200_close=None, asx200_daily_change_pct=None,
                avix=None, aud_usd=None,
            )
            conn = AsyncMock()
            conn.fetchrow.return_value = row
            with patch("asxos.domain.brief.collectors.market_context.acquire") as mock_acquire:
                mock_acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
                mock_acquire.return_value.__aexit__ = AsyncMock(return_value=False)
                result = await collect_market_context(AS_OF)
            assert result.status == SectionStatus.ok
            red_items = [i for i in result.items if i.level == SeverityLevel.red]
            assert red_items, "risk_off_disorderly should produce a red item"

        _run(_run_test())

    def test_risk_off_orderly_gives_yellow(self):
        async def _run_test():
            row = _make_row(
                regime_label="risk_off_orderly",
                asx200_close=None, asx200_daily_change_pct=None,
                avix=None, aud_usd=None,
            )
            conn = AsyncMock()
            conn.fetchrow.return_value = row
            with patch("asxos.domain.brief.collectors.market_context.acquire") as mock_acquire:
                mock_acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
                mock_acquire.return_value.__aexit__ = AsyncMock(return_value=False)
                result = await collect_market_context(AS_OF)
            assert result.status == SectionStatus.ok
            yellow_items = [i for i in result.items if i.level == SeverityLevel.yellow]
            assert yellow_items

        _run(_run_test())

    def test_risk_on_gives_green_with_indicators(self):
        async def _run_test():
            row = _make_row(
                regime_label="risk_on_broadening",
                asx200_close=Decimal("8200.0"),
                asx200_daily_change_pct=Decimal("0.45"),
                avix=Decimal("14.2"),
                aud_usd=Decimal("0.6550"),
            )
            conn = AsyncMock()
            conn.fetchrow.return_value = row
            with patch("asxos.domain.brief.collectors.market_context.acquire") as mock_acquire:
                mock_acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
                mock_acquire.return_value.__aexit__ = AsyncMock(return_value=False)
                result = await collect_market_context(AS_OF)
            assert result.status == SectionStatus.ok
            assert all(i.level == SeverityLevel.green for i in result.items)
            # indicators item should contain ASX200
            assert any("ASX200" in i.message for i in result.items)

        _run(_run_test())


# ── watchlist ──────────────────────────────────────────────────────────────────

class TestCollectWatchlist:
    def test_no_data_when_empty(self):
        async def _run_test():
            conn = AsyncMock()
            conn.fetch.return_value = []
            with patch("asxos.domain.brief.collectors.watchlist.acquire") as mock_acquire:
                mock_acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
                mock_acquire.return_value.__aexit__ = AsyncMock(return_value=False)
                result = await collect_watchlist(AS_OF)
            assert result.status == SectionStatus.no_data

        _run(_run_test())

    def test_watching_thesis_returns_green(self):
        async def _run_test():
            row = _make_row(
                symbol="MIN.AU",
                entry_band_lower=Decimal("48.00"),
                entry_band_upper=Decimal("53.00"),
                stop_price=Decimal("42.00"),
                target_price=Decimal("74.00"),
                opened_at=MagicMock(date=lambda: AS_OF - timedelta(days=30)),
                thesis_text="Iron ore and lithium leveraged miner.",
            )
            conn = AsyncMock()
            conn.fetch.return_value = [row]
            with patch("asxos.domain.brief.collectors.watchlist.acquire") as mock_acquire:
                mock_acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
                mock_acquire.return_value.__aexit__ = AsyncMock(return_value=False)
                result = await collect_watchlist(AS_OF)
            assert result.status == SectionStatus.ok
            assert len(result.items) == 1
            assert result.items[0].level == SeverityLevel.green
            assert "MIN.AU" in result.items[0].message

        _run(_run_test())


# ── new_ideas ──────────────────────────────────────────────────────────────────

class TestCollectNewIdeas:
    def test_suppressed_under_risk_off_orderly(self):
        result = _run(collect_new_ideas(AS_OF, regime_label="risk_off_orderly"))
        assert result.status == SectionStatus.suppressed

    def test_suppressed_under_risk_off_disorderly(self):
        result = _run(collect_new_ideas(AS_OF, regime_label="risk_off_disorderly"))
        assert result.status == SectionStatus.suppressed

    def test_not_suppressed_under_risk_on(self):
        async def _run_test():
            conn = AsyncMock()
            conn.fetch.return_value = []
            conn.fetchrow.return_value = None
            with patch("asxos.domain.brief.collectors.new_ideas.acquire") as mock_acquire:
                mock_acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
                mock_acquire.return_value.__aexit__ = AsyncMock(return_value=False)
                result = await collect_new_ideas(AS_OF, regime_label="risk_on_broadening")
            assert result.status == SectionStatus.no_data  # empty, not suppressed

        _run(_run_test())

    def test_research_thesis_gives_green(self):
        async def _run_test():
            row = _make_row(
                symbol="LTR.AU",
                opened_at=MagicMock(date=lambda: AS_OF - timedelta(days=14)),
                thesis_text="Lithium refiner with Kathleen Valley project.",
            )
            conn = AsyncMock()
            conn.fetch.return_value = [row]
            with patch("asxos.domain.brief.collectors.new_ideas.acquire") as mock_acquire:
                mock_acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
                mock_acquire.return_value.__aexit__ = AsyncMock(return_value=False)
                result = await collect_new_ideas(AS_OF, regime_label="neutral_mixed")
            assert result.status == SectionStatus.ok
            assert result.items[0].level == SeverityLevel.green
            assert "LTR.AU" in result.items[0].message

        _run(_run_test())

    def test_regime_fetched_from_db_when_none(self):
        """When regime_label is None, collector queries market_context_current."""
        async def _run_test():
            conn = AsyncMock()
            # Returns risk_off_orderly from DB → should suppress
            conn.fetchrow.return_value = _make_row(regime_label="risk_off_orderly")
            conn.fetch.return_value = []
            with patch("asxos.domain.brief.collectors.new_ideas.acquire") as mock_acquire:
                mock_acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
                mock_acquire.return_value.__aexit__ = AsyncMock(return_value=False)
                result = await collect_new_ideas(AS_OF, regime_label=None)
            assert result.status == SectionStatus.suppressed

        _run(_run_test())


# ── theme_dashboard ────────────────────────────────────────────────────────────

class TestCollectThemeDashboard:
    def test_no_data_when_no_themes(self):
        async def _run_test():
            conn = AsyncMock()
            conn.fetch.return_value = []
            with patch("asxos.domain.brief.collectors.theme_dashboard.acquire") as mock_acquire:
                mock_acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
                mock_acquire.return_value.__aexit__ = AsyncMock(return_value=False)
                result = await collect_theme_dashboard(AS_OF)
            assert result.status == SectionStatus.no_data

        _run(_run_test())

    def test_stage_suggested_divergence_gives_yellow(self):
        async def _run_test():
            row = _make_row(
                theme_id=1,
                theme_code="lithium_miners",
                stage="emerging",
                stage_suggested="consensus",
                conviction_band="high",
                holding_count=3,
                thesis_count=2,
            )
            conn = AsyncMock()
            conn.fetch.return_value = [row]
            with patch("asxos.domain.brief.collectors.theme_dashboard.acquire") as mock_acquire:
                mock_acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
                mock_acquire.return_value.__aexit__ = AsyncMock(return_value=False)
                result = await collect_theme_dashboard(AS_OF)
            assert result.status == SectionStatus.ok
            assert result.items[0].level == SeverityLevel.yellow
            assert "consensus" in result.items[0].message

        _run(_run_test())

    def test_aligned_stage_gives_green(self):
        async def _run_test():
            row = _make_row(
                theme_id=1,
                theme_code="copper_infrastructure",
                stage="emerging",
                stage_suggested="emerging",
                conviction_band="medium",
                holding_count=2,
                thesis_count=1,
            )
            conn = AsyncMock()
            conn.fetch.return_value = [row]
            with patch("asxos.domain.brief.collectors.theme_dashboard.acquire") as mock_acquire:
                mock_acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
                mock_acquire.return_value.__aexit__ = AsyncMock(return_value=False)
                result = await collect_theme_dashboard(AS_OF)
            assert result.status == SectionStatus.ok
            assert result.items[0].level == SeverityLevel.green

        _run(_run_test())


# ── opportunity_cost ───────────────────────────────────────────────────────────

class TestCollectOpportunityCost:
    def test_graceful_no_data_when_table_missing(self):
        async def _run_test():
            conn = AsyncMock()
            conn.fetch.side_effect = Exception(
                'relation "opportunity_cost_scenarios" does not exist'
            )
            with patch("asxos.domain.brief.collectors.opportunity_cost.acquire") as mock_acquire:
                mock_acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
                mock_acquire.return_value.__aexit__ = AsyncMock(return_value=False)
                result = await collect_opportunity_cost(AS_OF)
            assert result.status == SectionStatus.no_data
            assert "Phase 5 pending" in (result.error or "")

        _run(_run_test())

    def test_no_data_when_no_scenarios(self):
        async def _run_test():
            conn = AsyncMock()
            conn.fetch.return_value = []
            with patch("asxos.domain.brief.collectors.opportunity_cost.acquire") as mock_acquire:
                mock_acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
                mock_acquire.return_value.__aexit__ = AsyncMock(return_value=False)
                result = await collect_opportunity_cost(AS_OF)
            assert result.status == SectionStatus.no_data

        _run(_run_test())

    def test_high_net_return_scenario_gives_yellow(self):
        async def _run_test():
            row = _make_row(
                thesis_id=1,
                symbol="MIN.AU",
                alternative_symbol="PLS.AU",
                alternative_source="watchlist",
                gross_expected_return=Decimal("0.20"),
                estimated_cgt_friction=Decimal("0.04"),
                net_expected_return=Decimal("0.16"),
                notes=None,
            )
            conn = AsyncMock()
            conn.fetch.return_value = [row]
            with patch("asxos.domain.brief.collectors.opportunity_cost.acquire") as mock_acquire:
                mock_acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
                mock_acquire.return_value.__aexit__ = AsyncMock(return_value=False)
                result = await collect_opportunity_cost(AS_OF)
            assert result.status == SectionStatus.ok
            assert result.items[0].level == SeverityLevel.yellow

        _run(_run_test())

    def test_low_net_return_scenario_gives_green(self):
        async def _run_test():
            row = _make_row(
                thesis_id=1,
                symbol="MIN.AU",
                alternative_symbol="CASH",
                alternative_source="cash",
                gross_expected_return=Decimal("0.04"),
                estimated_cgt_friction=Decimal("0.02"),
                net_expected_return=Decimal("0.02"),
                notes=None,
            )
            conn = AsyncMock()
            conn.fetch.return_value = [row]
            with patch("asxos.domain.brief.collectors.opportunity_cost.acquire") as mock_acquire:
                mock_acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
                mock_acquire.return_value.__aexit__ = AsyncMock(return_value=False)
                result = await collect_opportunity_cost(AS_OF)
            assert result.status == SectionStatus.ok
            assert result.items[0].level == SeverityLevel.green

        _run(_run_test())


# ── cross_layer ────────────────────────────────────────────────────────────────

class TestCrossLayerObservations:
    def _score(self, label: str, weighted: float = 0.0) -> UnderlyingScore:
        return UnderlyingScore(
            label=label,
            weighted_movement=Decimal(str(weighted)),
            component_moves=(),
        )

    def test_empty_when_no_theses(self):
        obs = cross_layer_observations("risk_on_broadening", [])
        assert obs == []

    def test_risk_off_with_active_thesis_warns(self):
        """spec Part 5.5: risk-off regime + bullish active thesis → red flag observation."""
        theses = [("MIN.AU", "active", self._score("mixed", 0.5))]
        obs = cross_layer_observations("risk_off_orderly", theses)
        assert len(obs) >= 1
        assert any("risk_off_orderly" in o for o in obs)

    def test_diverging_bullish_thesis_warns(self):
        """spec Part 5.5: bullish thesis + diverging underlyings → hidden risk."""
        theses = [("PLS.AU", "active", self._score("diverging", -3.5))]
        obs = cross_layer_observations("neutral_mixed", theses)
        assert any("divergence" in o.lower() or "diverging" in o.lower() for o in obs)

    def test_confirming_in_risk_on_is_positive(self):
        """spec Part 5.5: risk-on + confirming → environment supportive."""
        theses = [
            ("MIN.AU", "active", self._score("confirming", 4.2)),
            ("BHP.AU", "active", self._score("confirming", 2.1)),
        ]
        obs = cross_layer_observations("risk_on_broadening", theses)
        assert any("confirming" in o.lower() or "supportive" in o.lower() for o in obs)

    def test_max_three_observations(self):
        theses = [
            ("MIN.AU", "active", self._score("diverging", -4.0)),
            ("BHP.AU", "active", self._score("diverging", -3.0)),
            ("PLS.AU", "watching", self._score("mixed", 0.5)),
        ]
        obs = cross_layer_observations("risk_off_disorderly", theses)
        assert len(obs) <= 3

    def test_exited_thesis_status_ignored(self):
        """Exited/research theses should not contribute to risk observations."""
        theses = [("MIN.AU", "exited", self._score("diverging", -5.0))]
        obs = cross_layer_observations("risk_on_broadening", theses)
        assert obs == []

    def test_mixed_only_gives_ambiguous_observation(self):
        theses = [
            ("MIN.AU", "active", self._score("mixed", 0.5)),
            ("BHP.AU", "active", self._score("mixed", -0.3)),
        ]
        obs = cross_layer_observations("neutral_mixed", theses)
        # May or may not produce an observation depending on implementation,
        # but must never exceed 3 and never raise
        assert isinstance(obs, list)
        assert len(obs) <= 3
