"""
Tests for M-Underlyings: attribution scoring, hidden-risk detection, service cap.

Covers:
  - score_thesis_underlying: confirming / mixed / diverging / no-data / empty
  - detect_hidden_risk: bullish+diverging, exited, mixed
  - attach_underlying: exposure sum cap (ValueError before any DB write)
"""
from __future__ import annotations

import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from asxos.domain.underlyings.attribution import score_thesis_underlying
from asxos.domain.underlyings.divergence import detect_hidden_risk
from asxos.domain.underlyings.service import attach_underlying
from asxos.domain.underlyings.types import ThesisUnderlying, UnderlyingDirection, UnderlyingScore


def _tu(
    underlying_id: int,
    code: str,
    exposure: str,
    direction: str,
) -> ThesisUnderlying:
    return ThesisUnderlying(
        thesis_id=1,
        underlying_id=underlying_id,
        code=code,
        exposure=Decimal(exposure),
        direction=UnderlyingDirection(direction),
        last_validated_at=None,
    )


# ---------------------------------------------------------------------------
# score_thesis_underlying — label outcomes
# ---------------------------------------------------------------------------

def test_confirming() -> None:
    """Iron ore +6% on 0.5 positive exposure → weighted_movement = +3.0 → confirming."""
    tu = _tu(1, "iron_ore_62fe", "0.5", "positive")
    score = score_thesis_underlying([tu], {1: Decimal("6.0")})
    assert score.label == "confirming"
    assert score.weighted_movement > Decimal("2")
    assert score.component_moves[0]["contribution"] is not None


def test_mixed() -> None:
    """Iron ore +1% on 0.5 exposure → weighted_movement = +0.5 → mixed."""
    tu = _tu(1, "iron_ore_62fe", "0.5", "positive")
    score = score_thesis_underlying([tu], {1: Decimal("1.0")})
    assert score.label == "mixed"
    assert Decimal("-2") <= score.weighted_movement <= Decimal("2")


def test_diverging() -> None:
    """Iron ore -6% on 0.5 positive exposure → weighted_movement = -3.0 → diverging."""
    tu = _tu(1, "iron_ore_62fe", "0.5", "positive")
    score = score_thesis_underlying([tu], {1: Decimal("-6.0")})
    assert score.label == "diverging"
    assert score.weighted_movement < Decimal("-2")


def test_negative_direction_inverts_contribution() -> None:
    """Iron ore -6% on 0.5 NEGATIVE exposure → contribution = +3.0 → confirming."""
    tu = _tu(1, "iron_ore_62fe", "0.5", "negative")
    score = score_thesis_underlying([tu], {1: Decimal("-6.0")})
    assert score.label == "confirming"
    assert score.weighted_movement > Decimal("2")


def test_multi_underlying_mixed_signals() -> None:
    """Two underlyings with opposing contributions land in mixed band."""
    tu_pos = _tu(1, "iron_ore_62fe", "0.5", "positive")
    tu_neg = _tu(2, "aud_usd", "0.5", "negative")
    # iron_ore +4% (contribution +2), aud_usd +4% (contribution -2) → net 0
    score = score_thesis_underlying(
        [tu_pos, tu_neg],
        {1: Decimal("4.0"), 2: Decimal("4.0")},
    )
    assert score.label == "mixed"
    assert len(score.component_moves) == 2


# ---------------------------------------------------------------------------
# score_thesis_underlying — missing / empty data
# ---------------------------------------------------------------------------

def test_no_price_data_returns_mixed() -> None:
    """None move → contribution excluded → mixed (insufficient data)."""
    tu = _tu(1, "iron_ore_62fe", "0.5", "positive")
    score = score_thesis_underlying([tu], {1: None})
    assert score.label == "mixed"
    assert score.weighted_movement == Decimal("0")
    assert score.component_moves[0]["move_5d_pct"] is None
    assert score.component_moves[0]["contribution"] is None


def test_empty_thesis_underlyings() -> None:
    """No underlyings → mixed with zero movement."""
    score = score_thesis_underlying([], {})
    assert score.label == "mixed"
    assert score.weighted_movement == Decimal("0")
    assert score.component_moves == ()


def test_underlying_id_not_in_moves() -> None:
    """underlying_id absent from moves dict treated as None move."""
    tu = _tu(99, "copper", "0.4", "positive")
    score = score_thesis_underlying([tu], {})
    assert score.label == "mixed"
    assert score.weighted_movement == Decimal("0")


# ---------------------------------------------------------------------------
# detect_hidden_risk
# ---------------------------------------------------------------------------

def test_hidden_risk_active_diverging() -> None:
    """Active thesis with diverging underlyings → warning string emitted."""
    score = UnderlyingScore(
        label="diverging", weighted_movement=Decimal("-3.0"), component_moves=()
    )
    result = detect_hidden_risk("active", score)
    assert result is not None
    assert "diverging" in result
    assert "active" in result


def test_hidden_risk_watching_diverging() -> None:
    """Watching thesis with diverging underlyings → warning string emitted."""
    score = UnderlyingScore(
        label="diverging", weighted_movement=Decimal("-3.5"), component_moves=()
    )
    result = detect_hidden_risk("watching", score)
    assert result is not None


def test_hidden_risk_exited_diverging() -> None:
    """Exited thesis ignores divergence — no warning."""
    score = UnderlyingScore(
        label="diverging", weighted_movement=Decimal("-3.0"), component_moves=()
    )
    assert detect_hidden_risk("exited", score) is None


def test_hidden_risk_active_mixed() -> None:
    """Active thesis with mixed underlyings → no warning."""
    score = UnderlyingScore(
        label="mixed", weighted_movement=Decimal("0.5"), component_moves=()
    )
    assert detect_hidden_risk("active", score) is None


def test_hidden_risk_active_confirming() -> None:
    """Active thesis with confirming underlyings → no warning."""
    score = UnderlyingScore(
        label="confirming", weighted_movement=Decimal("3.0"), component_moves=()
    )
    assert detect_hidden_risk("active", score) is None


# ---------------------------------------------------------------------------
# attach_underlying — exposure cap (application-layer guard)
# ---------------------------------------------------------------------------

def test_attach_underlying_sum_cap() -> None:
    """attach_underlying raises ValueError before any DB write when sum exceeds 1.0."""
    async def _run() -> None:
        conn = AsyncMock()
        # First fetchval: underlying_id lookup → 42
        # Second fetchval: existing_sum for other underlyings → 0.80
        conn.fetchval = AsyncMock(side_effect=[42, Decimal("0.80")])
        with pytest.raises(ValueError, match="total exposure"):
            await attach_underlying(
                conn, thesis_id=1, underlying_code="iron_ore_62fe",
                exposure=Decimal("0.30"), direction="positive",
            )
        conn.execute.assert_not_called()

    asyncio.run(_run())


def test_attach_underlying_exact_one_allowed() -> None:
    """Total exposure of exactly 1.0 is accepted."""
    async def _run() -> None:
        conn = AsyncMock()
        conn.fetchval = AsyncMock(side_effect=[42, Decimal("0.70")])
        conn.execute = AsyncMock()
        await attach_underlying(
            conn, thesis_id=1, underlying_code="iron_ore_62fe",
            exposure=Decimal("0.30"), direction="positive",
        )
        conn.execute.assert_called_once()

    asyncio.run(_run())


def test_attach_underlying_invalid_direction() -> None:
    """Invalid direction raises ValueError before any DB call."""
    async def _run() -> None:
        conn = AsyncMock()
        with pytest.raises(ValueError, match="direction"):
            await attach_underlying(
                conn, thesis_id=1, underlying_code="iron_ore_62fe",
                exposure=Decimal("0.50"), direction="long",
            )
        conn.fetchval.assert_not_called()

    asyncio.run(_run())


def test_attach_underlying_not_found() -> None:
    """RuntimeError raised when underlying not found or inactive."""
    async def _run() -> None:
        conn = AsyncMock()
        conn.fetchval = AsyncMock(return_value=None)
        with pytest.raises(RuntimeError, match="not found or inactive"):
            await attach_underlying(
                conn, thesis_id=1, underlying_code="nonexistent_code",
                exposure=Decimal("0.30"), direction="positive",
            )
        conn.execute.assert_not_called()

    asyncio.run(_run())


def test_attach_underlying_exposure_out_of_range() -> None:
    """Exposure > 1 raises ValueError before any DB call."""
    async def _run() -> None:
        conn = AsyncMock()
        with pytest.raises(ValueError, match="exposure must be in"):
            await attach_underlying(
                conn, thesis_id=1, underlying_code="iron_ore_62fe",
                exposure=Decimal("1.5"), direction="positive",
            )
        conn.fetchval.assert_not_called()

    asyncio.run(_run())
