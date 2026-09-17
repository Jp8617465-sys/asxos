"""The brief's candidates section — loader, four-state mapping, render, firewall.

This section is the delivery half of automated discovery: `discover_opportunities`
writes machine proposals to `theses` at `pending_review`, and this is where they
reach James. Before it existed the screen ran weekly and its output reached
nothing — `brief_section_gold` carried nine sections and none of them was
discovery.

Three properties are load-bearing and each has a test below:

* **No rank, no target, no stop, no entry band.** The sealed value-to-price test
  returned null (#304) and the pre-committed `RESPONSE_RULE` demotes the model so
  it "stops emitting target prices, entry bands and ranked 'opportunities'". A
  symbol-ordered set is not a rank; sorting it by the model's own number would
  be, which is why the order is asserted rather than assumed.
* **EMPTY is not MISSING.** A quiet week and an unreadable queue are the one pair
  a reader cannot distinguish, and only one of them is good news.
* **s766B.** The section carries no rating, price target, position size or trade
  direction, in every shape it can render.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import pytest

from asxos.brief.compose import BriefData, CandidateRow, _candidates, render_html
from asxos.brief.section import SectionStatus, assemble_sections
from tests.test_results_review_reviewer_challenger import _ADVICE_PATTERNS

AS_OF = date(2026, 5, 22)
FIXED = datetime(2026, 5, 22, 20, 30, tzinfo=UTC)

_START = "<!-- candidates:start -->"
_END = "<!-- candidates:end -->"


def _fragment(html: str) -> str:
    """The candidates section alone, isolated for the firewall sweep.

    Same reason the outcome section does this: the rest of the page
    legitimately prints "Portfolio discipline", "holdings" and the
    CLEAR/ATTENTION/BLOCKED tokens, so a whole-page assertion would have to run
    a weakened vocabulary. Markers are emitted unconditionally, so extraction
    never depends on the section's own state.
    """
    assert _START in html and _END in html, "candidates section markers missing"
    return html.split(_START, 1)[1].split(_END, 1)[0]


def _brief(**overrides: Any) -> BriefData:
    defaults: dict[str, Any] = {
        "as_of": AS_OF,
        "holdings_count": 1,
        "latest_price_date": AS_OF,
    }
    defaults.update(overrides)
    return BriefData(**defaults)


def _row(symbol: str, thesis_id: int = 1, **over: Any) -> CandidateRow:
    defaults: dict[str, Any] = {
        "symbol": symbol,
        "thesis_id": thesis_id,
        "sector": "Industrials",
        "last_close": Decimal("1.100"),
        "model_value": Decimal("1.515"),
        "proposed_at": date(2026, 5, 20),
    }
    defaults.update(over)
    return CandidateRow(**defaults)


# ---------------------------------------------------------------------------
# 1. Loader — the firewall gate and the row mapping
# ---------------------------------------------------------------------------


@dataclass
class _FakeConn:
    rows: list[dict[str, Any]]
    queries: list[str]

    async def fetch(self, query: str, *args: Any) -> list[dict[str, Any]]:
        self.queries.append(query)
        return self.rows


async def test_loader_is_behind_the_personal_use_firewall(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Parity with _discipline_findings / _news_section / _portfolio_section.

    Candidate securities for this user's own portfolio are personal investment
    content whether or not they carry a price plan.
    """
    monkeypatch.delenv("ASXOS_PERSONAL_USE", raising=False)
    conn = _FakeConn(rows=[{"x": 1}], queries=[])
    assert await _candidates(conn, AS_OF) == []
    assert conn.queries == [], "the query must not run at all when ungated"


async def test_loader_maps_rows_and_orders_by_symbol(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    conn = _FakeConn(
        rows=[
            {
                "thesis_id": 31,
                "symbol": "CCP.AU",
                "opened_at": datetime(2026, 5, 20, 1, 0, tzinfo=UTC),
                "sector": "Financial Services",
                "value_per_share": Decimal("16.739"),
                "last_close": Decimal("13.610"),
            }
        ],
        queries=[],
    )
    got = await _candidates(conn, AS_OF)
    assert got == [
        CandidateRow(
            symbol="CCP.AU",
            thesis_id=31,
            sector="Financial Services",
            last_close=Decimal("13.610"),
            model_value=Decimal("16.739"),
            proposed_at=date(2026, 5, 20),
        )
    ]
    query = conn.queries[0]
    assert "pending_review" in query
    assert "ORDER BY t.symbol" in query
    # The rank RESPONSE_RULE deleted must not reappear as an ORDER BY.
    assert "value_per_share DESC" not in query
    assert "value_to_price" not in query
    # The figures column is pinned to one method. Without this, a second
    # valuation method writing to the same table on the same as_of makes the
    # LATERAL pick non-deterministic and the card mis-attributes it.
    assert "method = 'residual_income'" in query


async def test_loader_keeps_a_row_whose_valuation_is_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A superseded or missing valuation row blanks the figures, never the name.

    Dropping the row would make a proposal silently disappear from the queue
    (CLAUDE.md #10).
    """
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    conn = _FakeConn(
        rows=[
            {
                "thesis_id": 4,
                "symbol": "EHL.AU",
                "opened_at": datetime(2026, 5, 20, 1, 0, tzinfo=UTC),
                "sector": None,
                "value_per_share": None,
                "last_close": None,
            }
        ],
        queries=[],
    )
    (got,) = await _candidates(conn, AS_OF)
    assert got.symbol == "EHL.AU"
    assert got.model_value is None and got.last_close is None


# ---------------------------------------------------------------------------
# 2. Four-state mapping — EMPTY is not MISSING
# ---------------------------------------------------------------------------


def _assemble(**over: Any) -> Any:
    base: dict[str, Any] = {
        "latest_price_date": AS_OF,
        "prices_stale": False,
        "job_failures": [],
        "discipline_findings": [],
        "outcome_section": None,
        "outcome_error": None,
        "regulatory_hits": [],
        "news_items": [],
        "news_status": "quiet",
        "news_error": None,
        "portfolio_section": None,
        "computed_at": FIXED,
    }
    base.update(over)
    return assemble_sections(**base)["candidates"]


def test_quiet_week_is_empty_not_missing() -> None:
    section = _assemble(candidates=[])
    assert section.status is SectionStatus.EMPTY
    assert section.error is None


def test_unreadable_queue_is_missing_not_empty() -> None:
    """The distinction the whole four-state vocabulary exists for.

    If these collapsed, a broken query would render as "no new candidates" —
    indistinguishable from a genuinely quiet week, and reassuring in exactly the
    case where it should alarm.
    """
    section = _assemble(candidates=[], candidates_error="boom")
    assert section.status is SectionStatus.MISSING
    assert section.error == "boom"
    assert section.data is None


def test_populated_queue_is_fresh() -> None:
    section = _assemble(candidates=[_row("EHL.AU")])
    assert section.status is SectionStatus.FRESH
    assert len(section.data) == 1


def test_candidates_appears_in_the_integrity_line_order() -> None:
    from asxos.brief.section import SECTION_ORDER

    assert "candidates" in SECTION_ORDER, (
        "a section absent from SECTION_ORDER never states its status on the "
        "integrity line, which is where a MISSING section is meant to show"
    )


# ---------------------------------------------------------------------------
# 3. Render
# ---------------------------------------------------------------------------


def test_render_without_candidates_says_none_explicitly() -> None:
    fragment = _fragment(render_html(_brief()))
    assert "None." in fragment
    assert "ordinary weekly state" in fragment


def test_render_error_is_a_loud_banner_that_refuses_to_read_as_quiet() -> None:
    fragment = _fragment(
        render_html(_brief(candidates_error="candidates section could not run: boom"))
    )
    assert "could not run" in fragment
    assert "boom" in fragment
    assert "not the same as a quiet week" in fragment


def test_render_lists_every_candidate_in_the_order_given() -> None:
    fragment = _fragment(
        render_html(
            _brief(
                candidates=[
                    _row("CCP.AU", 31),
                    _row("EHL.AU", 32),
                    _row("YAL.AU", 33),
                ]
            )
        )
    )
    positions = [fragment.index(s) for s in ("CCP.AU", "EHL.AU", "YAL.AU")]
    assert positions == sorted(positions), "the rendered order must be the query's"
    assert "asx thesis approve 31" in fragment


def test_render_never_emits_a_target_stop_or_rank_column() -> None:
    """The structural half of the RESPONSE_RULE, asserted against the render.

    Prose can be reviewed; a column header is what turns a set into a ranked
    recommendation without anyone deciding to.
    """
    fragment = _fragment(render_html(_brief(candidates=[_row("EHL.AU")])))
    for banned in ("<th>Rank", "<th>Target", "<th>Stop", "<th>Entry", "<th>Score"):
        assert banned.lower() not in fragment.lower(), f"{banned} reintroduces the rank"


# ---------------------------------------------------------------------------
# 4. s766B personal-advice firewall
# ---------------------------------------------------------------------------


def _every_rendered_state() -> list[tuple[str, str]]:
    return [
        ("empty", _fragment(render_html(_brief()))),
        ("error", _fragment(render_html(_brief(candidates_error="could not run: x")))),
        (
            "populated",
            _fragment(
                render_html(
                    _brief(
                        candidates=[
                            _row("CCP.AU", 31),
                            _row("EHL.AU", 32, sector=None, last_close=None, model_value=None),
                        ]
                    )
                )
            ),
        ),
    ]


def test_no_advice_vocabulary_in_any_rendered_state() -> None:
    """The full frozen list, over every shape this section can take.

    The empty-state prose and the error banner are prose too, and prose is where
    advice creeps in.
    """
    for name, fragment in _every_rendered_state():
        for pattern in _ADVICE_PATTERNS:
            match = pattern.search(fragment)
            assert match is None, (
                f"advice vocabulary {pattern.pattern!r} surfaced in the {name} "
                f"rendering: {match.group(0)!r}"
            )


def test_the_section_states_that_a_row_is_not_a_decision() -> None:
    """The disclaimer must survive the frozen vocabulary, which is why it does
    not use the obvious words: `position`, `holding` and `portfolio` are all in
    `_ADVICE_PATTERNS`, so the honest sentence has to be written around them.
    The first draft said "not a position and not a plan" and the firewall test
    above rejected it — kept as a note because the next person to reword this
    will reach for the same word."""
    fragment = " ".join(
        _fragment(render_html(_brief(candidates=[_row("EHL.AU")]))).split()
    )
    assert "Nothing has been decided and nothing has been acted on." in fragment
    assert "remains yours" in fragment
    assert "s766B" in fragment


def test_no_model_a_vocabulary_reaches_the_section() -> None:
    """Rule #11. The residual-income model is not Model A, but the section sits
    where a signal ladder used to, so the absence is asserted rather than
    assumed."""
    for _name, fragment in _every_rendered_state():
        for banned in ("prob_up", "shap", "STRONG_BUY", "model_a", "signal"):
            assert not re.search(banned, fragment, re.IGNORECASE), banned
