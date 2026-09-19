"""The brief's macro section — loader, ordering, four-state mapping, render, firewall.

Three approved macro theses have been scored nightly by `jobs/score_macro_theses.py`
since 2026-07-21 (29 successful runs by 2026-09-18) and reached no surface James
reads: `SECTION_ORDER` had no macro entry. The regime the book sits in existed,
was governed, was evaluated every night, and was invisible.

Four properties are load-bearing and each has a test below:

* **A tripped falsifier sorts first.** It is the only row that asks for anything;
  everything else is context. The ordering is asserted, not assumed.
* **EMPTY is not MISSING.** "No approved macro thesis" and "the macro read failed"
  are different facts and only one of them is ordinary.
* **An unscored thesis still renders.** A newly approved thesis that the scorer has
  not reached yet must appear with its measurements absent, never vanish
  (CLAUDE.md #10) — and must not borrow 'open' from a thesis that was scored.
* **s766B.** The card is impersonal market commentary: no security, no direction,
  no advice vocabulary in its fixed prose.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from asxos.brief.compose import BriefData, MacroRow, _macro, render_html
from asxos.brief.section import SectionStatus, assemble_sections
from tests.test_results_review_reviewer_challenger import _ADVICE_PATTERNS

AS_OF = date(2026, 5, 22)
FIXED = datetime(2026, 5, 22, 20, 30, tzinfo=UTC)

_START = "<!-- macro:start -->"
_END = "<!-- macro:end -->"


def _fragment(html: str) -> str:
    """The macro section alone. Markers are emitted unconditionally, so this
    never depends on the section's own state."""
    assert _START in html and _END in html, "macro section markers missing"
    return html.split(_START, 1)[1].split(_END, 1)[0]


def _brief(**overrides: Any) -> BriefData:
    defaults: dict[str, Any] = {
        "as_of": AS_OF,
        "holdings_count": 1,
        "latest_price_date": AS_OF,
    }
    defaults.update(overrides)
    return BriefData(**defaults)


def _row(macro_thesis_id: int = 6, **over: Any) -> MacroRow:
    defaults: dict[str, Any] = {
        "macro_thesis_id": macro_thesis_id,
        "title": "Breadth-led catch-down resolves into orderly risk-off",
        "regime_quadrant": "falling_growth_falling_inflation",
        "horizon_months": 6,
        "status": "open",
        "catalyst_progress": None,
        "falsifier_triggered": False,
        "days_elapsed": 59,
        "days_to_horizon": 125,
        "authored_at": date(2026, 7, 21),
        "scored_as_of": date(2026, 9, 18),
    }
    defaults.update(over)
    return MacroRow(**defaults)


@dataclass
class _FakeConn:
    rows: list[dict[str, Any]]
    queries: list[str]

    async def fetch(self, query: str, *args: Any) -> list[dict[str, Any]]:
        self.queries.append(query)
        return self.rows


def _db_row(**over: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "macro_thesis_id": 6,
        "title": "A regime claim",
        "regime_quadrant": "falling_growth_falling_inflation",
        "horizon_months": 6,
        "created_at": datetime(2026, 7, 21, 10, 55, tzinfo=UTC),
        "as_of": date(2026, 9, 18),
        "status": "open",
        "catalyst_progress": None,
        "falsifier_triggered": False,
        "days_elapsed": 59,
        "days_to_horizon": 125,
    }
    base.update(over)
    return base


# ---------------------------------------------------------------------------
# 1. Loader
# ---------------------------------------------------------------------------


async def test_loader_maps_a_scored_row() -> None:
    conn = _FakeConn(rows=[_db_row()], queries=[])
    rows = await _macro(conn)
    assert len(rows) == 1
    r = rows[0]
    assert (r.macro_thesis_id, r.status, r.falsifier_triggered) == (6, "open", False)
    assert r.authored_at == date(2026, 7, 21)
    assert r.scored_as_of == date(2026, 9, 18)


async def test_loader_selects_only_approved_and_unretired() -> None:
    """The governance gate belongs in SQL: a draft or retired regime view is not
    a view this book is being held against."""
    conn = _FakeConn(rows=[], queries=[])
    await _macro(conn)
    q = conn.queries[0]
    assert "governance_status = 'approved'" in q
    assert "retired_at IS NULL" in q


async def test_loader_orders_falsified_first() -> None:
    """The one editorial decision in this section, pinned.

    Sorting is done in SQL, so this asserts the ORDER BY rather than re-sorting
    in Python — a test that sorted the rows itself would pass against any query.
    """
    conn = _FakeConn(rows=[], queries=[])
    await _macro(conn)
    q = conn.queries[0]
    assert "ORDER BY COALESCE(o.falsifier_triggered, FALSE) DESC, m.macro_thesis_id" in q


async def test_unscored_thesis_renders_with_absent_measurements() -> None:
    """A thesis the scorer has not reached must not vanish, and must not be
    reported as 'open' — that would assert a measurement nobody took."""
    conn = _FakeConn(
        rows=[
            _db_row(
                as_of=None,
                status=None,
                falsifier_triggered=None,
                days_elapsed=None,
                days_to_horizon=None,
            )
        ],
        queries=[],
    )
    rows = await _macro(conn)
    assert len(rows) == 1
    assert rows[0].status == "unscored"
    assert rows[0].falsifier_triggered is False
    assert rows[0].scored_as_of is None


async def test_loader_is_not_gated_on_personal_use(monkeypatch: Any) -> None:
    """Deliberately ungated, unlike candidates/news/discipline.

    Investment-output band is `impersonal` (AGENTS.md §7): every field is a
    market-wide regime claim. The s766B firewall exists for personal advice, and
    the `regulatory` section — also externally-sourced market content — is
    ungated for the same reason.
    """
    monkeypatch.delenv("ASXOS_PERSONAL_USE", raising=False)
    conn = _FakeConn(rows=[_db_row()], queries=[])
    assert len(await _macro(conn)) == 1


# ---------------------------------------------------------------------------
# 2. Four-state mapping
# ---------------------------------------------------------------------------


def _sections(**over: Any) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "latest_price_date": AS_OF,
        "prices_stale": False,
        "job_failures": [],
        "discipline_findings": [],
        "outcome_section": None,
        "outcome_error": None,
        "regulatory_hits": [],
        "news_items": [],
        "news_status": "disabled",
        "news_error": None,
        "computed_at": FIXED,
        "data_as_of": AS_OF,
    }
    kwargs.update(over)
    return assemble_sections(**kwargs)


def test_section_is_empty_when_no_approved_thesis() -> None:
    assert _sections(macro=[])["macro"].status is SectionStatus.EMPTY


def test_section_is_fresh_when_rows_present() -> None:
    assert _sections(macro=[_row()])["macro"].status is SectionStatus.FRESH


def test_section_is_missing_when_the_read_failed() -> None:
    s = _sections(macro=[], macro_error="boom")["macro"]
    assert s.status is SectionStatus.MISSING
    assert s.data is None
    assert s.error == "boom"


def test_macro_renders_between_news_and_candidates() -> None:
    """Order is not cosmetic: the regime is the backdrop a candidate is read
    against, so it precedes the candidate queue."""
    from asxos.brief.section import SECTION_ORDER

    assert SECTION_ORDER.index("news") < SECTION_ORDER.index("macro")
    assert SECTION_ORDER.index("macro") < SECTION_ORDER.index("candidates")


# ---------------------------------------------------------------------------
# 3. Render
# ---------------------------------------------------------------------------


def test_render_empty_states_none_without_implying_a_quiet_week() -> None:
    frag = _fragment(render_html(_brief(macro=[])))
    assert "No approved macro thesis" in frag


def test_render_error_is_distinguishable_from_empty() -> None:
    frag = _fragment(render_html(_brief(macro=[], macro_error="connection reset")))
    assert "could not be loaded" in frag
    assert "connection reset" in frag
    assert "No approved macro thesis" not in frag


def test_render_shows_falsifier_state_and_authored_date() -> None:
    frag = _fragment(render_html(_brief(macro=[_row()])))
    assert "not tripped" in frag
    assert "2026-07-21" in frag          # authored — the staleness signal
    assert "59d of 184d" in frag         # elapsed against its own horizon
    assert "asx macro-thesis show 6" in frag


def test_render_flags_a_tripped_falsifier_loudly() -> None:
    frag = _fragment(render_html(_brief(macro=[_row(falsifier_triggered=True)])))
    assert "FALSIFIED" in frag
    assert "TRIPPED" in frag


def test_render_absent_measurements_are_dashes_not_zeroes() -> None:
    """catalyst_progress NULL means no machine-checkable predicate was encoded —
    an absent measurement, not zero progress."""
    frag = _fragment(
        render_html(
            _brief(
                macro=[
                    _row(
                        status="unscored",
                        scored_as_of=None,
                        days_elapsed=None,
                        days_to_horizon=None,
                        horizon_months=None,
                        regime_quadrant=None,
                    )
                ]
            )
        )
    )
    assert "never scored" in frag
    assert "0d" not in frag
    assert "0 mo" not in frag


def test_render_carries_no_advice_vocabulary_in_its_fixed_prose() -> None:
    """The only tripwire for advice creep edited into the template itself."""
    for state in (
        _brief(macro=[]),
        _brief(macro=[], macro_error="x"),
        _brief(macro=[_row()]),
        _brief(macro=[_row(falsifier_triggered=True)]),
    ):
        frag = _fragment(render_html(state))
        # Strip interpolated thesis titles: they are governed content James
        # approved, not template prose, and a future title could legitimately
        # contain one of these stems.
        prose = re.sub(r"Breadth-led[^<]*", "", frag)
        for pattern in _ADVICE_PATTERNS:
            assert pattern.search(prose) is None, (
                f"advice vocabulary {pattern.pattern!r} in the macro card: "
                f"{pattern.search(prose).group(0)!r}"  # type: ignore[union-attr]
            )


def test_no_model_a_vocabulary_anywhere_in_the_card() -> None:
    """Rule #11: the macro lane is model-independent and must read that way."""
    frag = _fragment(render_html(_brief(macro=[_row()])))
    for token in ("model_a", "Model A", "prob_up", "signal", "SHAP", "STRONG_BUY"):
        assert token.lower() not in frag.lower()


def test_decimal_catalyst_progress_is_accepted() -> None:
    """The column is NUMERIC(18,6) (CLAUDE.md #5), so the row must carry Decimal."""
    r = _row(catalyst_progress=Decimal("0.500000"))
    assert r.catalyst_progress == Decimal("0.500000")
