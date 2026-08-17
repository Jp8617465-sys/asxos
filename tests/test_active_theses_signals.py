"""Adversarial tests for the model-independence of the active_theses collector.

Historically this file guarded the collector's Model A driver line
(``Model A: <label> | Top drivers: …``) and the contamination-isolation model
gate above it — manifest T10. Mission P1-04 removed both (manifest A5), so the
conditional property those tests asserted ("under a quarantine, skip the driver
line") no longer has a subject. What replaces them is the unconditional property:
**this collector issues no ``model_versions`` and no ``signals`` query in any
state**, and each card now carries a four-state review status instead of a model
label.

The filename is kept deliberately: it is cited as T10 in
``docs/product/model-a-reference-manifest.md``, and a renamed file would leave
that reference dangling.

Helper functions (underlyings, severity) are patched so the tests isolate the
collector's own behaviour.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from asxos.domain.brief.types import SectionStatus, SeverityItem, SeverityLevel
from asxos.domain.review.status import ReviewStatus, directive_terms

_MODULE = "asxos.domain.brief.collectors.active_theses"


def _thesis_row(symbol: str = "BHP.AU") -> dict:
    return {
        "thesis_id": 1,
        "symbol": symbol,
        "status": "active",
        "opened_at": datetime(2026, 1, 1),
        "stop_price": Decimal("38.00"),
        "target_price": Decimal("55.00"),
        "timeline_days": 360,
        "entry_band_lower": Decimal("40.00"),
        "entry_band_upper": Decimal("44.00"),
        "revisit_due_at": datetime(2026, 12, 1),  # far future → green
        "analyst_buy_count": 0,
        "analyst_neutral_count": 0,
        "analyst_sell_count": 0,
        "analyst_consensus_target": None,
        "next_earnings_date": None,
        "earnings_notes": None,
    }


def _underlying(underlying_id: int = 11):
    tu = MagicMock()
    tu.underlying_id = underlying_id
    return tu


async def _run_collector(
    theses_rows,
    as_of=date(2026, 6, 1),
    *,
    underlyings=None,
    moves=None,
    score_label="confirming",
    extra_fetch_rows=None,
):
    """Drive the collector over one canned theses query.

    ``conn.fetch`` is routed by a side_effect LIST of exactly the queries the
    collector is expected to issue — one. If it issues a second (a resurrected
    model gate or signals read), the mock raises StopIteration, so the count is
    itself an assertion. ``extra_fetch_rows`` exists only for the negative test
    that proves this.
    """
    conn = MagicMock()
    conn.fetch = AsyncMock(side_effect=[theses_rows, *(extra_fetch_rows or [])])

    score = MagicMock()
    score.label = score_label
    score.weighted_movement = Decimal("3.5")

    tu_by_thesis = {1: underlyings} if underlyings else {}

    with (
        patch(f"{_MODULE}.acquire") as mock_acquire,
        patch(
            f"{_MODULE}.bulk_list_thesis_underlyings",
            AsyncMock(return_value=tu_by_thesis),
        ),
        patch(f"{_MODULE}.get_5d_moves", AsyncMock(return_value=moves or {})),
        patch(f"{_MODULE}.score_thesis_underlying", return_value=score),
        patch(f"{_MODULE}.thesis_revisit_overdue", return_value=None),
        patch(f"{_MODULE}.thesis_timeline_expired", return_value=None),
        patch(f"{_MODULE}.earnings_risk", return_value=None),
        patch(f"{_MODULE}.detect_hidden_risk", return_value=None),
    ):
        mock_acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
        mock_acquire.return_value.__aexit__ = AsyncMock(return_value=False)
        from asxos.domain.brief.collectors.active_theses import collect_active_theses
        return await collect_active_theses(as_of), conn


# ---------------------------------------------------------------------------
# Adversarial: no model surface remains, in any state
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_collector_issues_only_the_theses_query():
    """One fetch, and it is the theses read.

    The two removed queries — the `model_versions` approval gate and the
    `DISTINCT ON (symbol) … FROM signals` batch — were the collector's entire
    model dependency. Asserting the query *count* catches a reintroduction that
    an output-only assertion would miss (e.g. a signals read whose result is
    fetched but not yet rendered).
    """
    result, conn = await _run_collector([_thesis_row()])
    assert result.status == SectionStatus.ok
    assert conn.fetch.await_count == 1
    query = " ".join(str(conn.fetch.await_args_list[0].args[0]).split())
    assert "FROM theses" in query
    assert "model_versions" not in query
    assert "signals" not in query
    assert "shap_factors" not in query


@pytest.mark.asyncio
async def test_no_model_vocabulary_on_any_card():
    result, _ = await _run_collector(
        [_thesis_row()], underlyings=[_underlying()], moves={11: Decimal("4.0")}
    )
    msg = result.items[0].message
    for token in ("Model A", "model_a", "Top drivers", "shap", "STRONG_BUY", "HOLD"):
        assert token not in msg, f"{token!r} leaked onto a thesis card"


@pytest.mark.asyncio
async def test_card_carries_no_trade_direction():
    """A card reports upkeep evidence, never a direction (s766B firewall)."""
    result, _ = await _run_collector(
        [_thesis_row()], underlyings=[_underlying()], moves={11: Decimal("4.0")}
    )
    assert directive_terms(result.items[0].message) == ()


# ---------------------------------------------------------------------------
# The four-state review vocabulary (packet P1 item 4)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_card_shows_a_review_status_from_the_four_state_vocabulary():
    result, _ = await _run_collector(
        [_thesis_row()], underlyings=[_underlying()], moves={11: Decimal("4.0")}
    )
    msg = result.items[0].message
    assert "Review: " in msg
    status = msg.rsplit("Review: ", 1)[1].strip()
    assert status in {s.value for s in ReviewStatus}


@pytest.mark.asyncio
async def test_review_status_reaches_the_red_cards_too():
    """The overdue/expired branches render the severity helper's own message and
    never touch the card body — so the state has to be attached to the emitted
    item, not written into the body. Without that, the four states would be
    absent from exactly the cards that most need one.
    """
    overdue = SeverityItem(
        level=SeverityLevel.red,
        message="BHP.AU: review overdue by 16d (due 2026-05-16)",
        section="active_theses",
    )

    conn = MagicMock()
    conn.fetch = AsyncMock(side_effect=[[_thesis_row()]])
    score = MagicMock()
    score.label = "confirming"
    score.weighted_movement = Decimal("3.5")

    with (
        patch(f"{_MODULE}.acquire") as mock_acquire,
        patch(f"{_MODULE}.bulk_list_thesis_underlyings", AsyncMock(return_value={})),
        patch(f"{_MODULE}.get_5d_moves", AsyncMock(return_value={})),
        patch(f"{_MODULE}.score_thesis_underlying", return_value=score),
        patch(f"{_MODULE}.thesis_revisit_overdue", return_value=overdue),
        patch(f"{_MODULE}.thesis_timeline_expired", return_value=None),
        patch(f"{_MODULE}.earnings_risk", return_value=None),
        patch(f"{_MODULE}.detect_hidden_risk", return_value=None),
    ):
        mock_acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
        mock_acquire.return_value.__aexit__ = AsyncMock(return_value=False)
        from asxos.domain.brief.collectors.active_theses import collect_active_theses
        result = await collect_active_theses(date(2026, 6, 1))

    item = result.items[0]
    assert item.level == SeverityLevel.red
    assert "review overdue by 16d" in item.message  # helper's message preserved
    assert f"Review: {ReviewStatus.attention}" in item.message


@pytest.mark.asyncio
async def test_measured_underlyings_give_a_clear_card():
    result, _ = await _run_collector(
        [_thesis_row()], underlyings=[_underlying()], moves={11: Decimal("4.0")}
    )
    msg = result.items[0].message
    assert "Underlying: confirming (weighted +3.50%)" in msg
    assert f"Review: {ReviewStatus.clear}" in msg


@pytest.mark.asyncio
async def test_diverging_underlyings_give_an_attention_card():
    result, _ = await _run_collector(
        [_thesis_row()],
        underlyings=[_underlying()],
        moves={11: Decimal("-9.0")},
        score_label="diverging",
    )
    assert f"Review: {ReviewStatus.attention}" in result.items[0].message


# ---------------------------------------------------------------------------
# Explicit unknowns instead of a fabricated neutral (packet P1 item 5)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_linked_underlyings_reads_unavailable_not_a_zero():
    """`score_thesis_underlying([], {})` returns "mixed" at weighted 0.00%.

    Printed as-is that is a fabricated neutral: it looks like a measurement, and
    a reader cannot tell it from underlyings that genuinely cancelled out.
    """
    result, _ = await _run_collector([_thesis_row()], underlyings=None, moves={})
    msg = result.items[0].message
    assert "Underlying: unavailable" in msg
    assert "weighted" not in msg
    assert "+0.00%" not in msg
    assert f"Review: {ReviewStatus.evidence_thin}" in msg


@pytest.mark.asyncio
async def test_all_moves_stale_reads_unavailable_not_a_zero():
    """Same fabricated neutral by a different route: underlyings exist, but every
    5d move is missing, so the weighted sum stays 0 with nothing measured."""
    result, _ = await _run_collector(
        [_thesis_row()], underlyings=[_underlying(11), _underlying(12)], moves={}
    )
    msg = result.items[0].message
    assert "Underlying: unavailable" in msg
    assert "weighted" not in msg
    assert f"Review: {ReviewStatus.evidence_thin}" in msg


@pytest.mark.asyncio
async def test_evidence_thin_does_not_downgrade_a_real_finding():
    """An unknown must not mask an ATTENTION (review-status precedence)."""
    result, _ = await _run_collector(
        [_thesis_row() | {"revisit_due_at": datetime(2026, 6, 3)}],  # due in 2d
        underlyings=None,
        moves={},
    )
    msg = result.items[0].message
    assert "Underlying: unavailable" in msg
    assert f"Review: {ReviewStatus.attention}" in msg


# ---------------------------------------------------------------------------
# Regression kept from the pre-retirement suite
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_date_typed_earnings_value_does_not_call_date_method():
    row = _thesis_row()
    row["next_earnings_date"] = date(2026, 6, 15)

    result, _ = await _run_collector([row])

    assert result.status == SectionStatus.ok
