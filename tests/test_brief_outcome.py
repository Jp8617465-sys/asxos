"""Section 8 of the V1 brief — outcome vs benchmark: loader, render, firewall.

Three families:

* **The snapshot-differencing defect class, closed structurally.** `capital_aud`
  must appear in no query this path issues — why:
  `asxos/domain/brief/collectors/wealth_state.py:101-108`. Anchoring on
  `holding_lots` closes it; the assertions below keep it closed.
* **Today's real shape must render honestly.** One open lot, HUBS.NYSE, 24 shares.
  Global sleeve populated, ASX sleeve stating it is empty — not a misleading zero.
* **s766B.** The rendered section carries no rating, price target, position size,
  order or action vocabulary, asserted with the frozen grep list the P2 lane
  already applies.

The loader is exercised through a routing mock connection (the pattern
`tests/test_brief_compose.py` established), so the SQL text itself is available
for assertion — which is the only way to prove a *negative* about which columns
were read.
"""
from __future__ import annotations

import asyncio
import os
import re
from contextlib import asynccontextmanager
from datetime import date, timedelta
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from asxos.brief.compose import (
    BriefData,
    DisciplineFinding,
    DisciplineLevel,
    _lot_outcomes,
    _resolve_anchor,
    collect,
    render_html,
)
from asxos.domain.benchmark.outcome import (
    MAX_ANCHOR_LAG_DAYS,
    BenchmarkAnchor,
    BenchmarkState,
    Observation,
    OutcomeSection,
    ReturnState,
    Sleeve,
)
from asxos.domain.review.status import ReviewStatus

# The frozen advice vocabulary the P2 results-review lane applies, imported
# rather than copied. `tests` is a package (`tests/__init__.py`), so this is a
# real import and not a fragile path hack. Importing keeps ONE list: a term
# added there — as `allocat`, `reduc`, `increas` and the plural forms were,
# after an independent review found the gap — tightens this surface too, with
# no second copy to rot.
from tests.test_results_review_reviewer_challenger import _ADVICE_PATTERNS

AS_OF = date(2026, 8, 17)


def _obs(value: str, day: date = AS_OF) -> Observation:
    """A dated market observation, defaulting to the measurement date itself."""
    return Observation(as_of=day, value=Decimal(value))


# Today's actual state (2026-08-17): ONE open lot.
HUBS_LOT = {
    "id": 1,
    "symbol": "HUBS.NYSE",
    "quantity": Decimal("24"),
    "acquired_at": date(2025, 6, 2),
    "cost_base_normal": Decimal("6978.23"),
}
CBA_LOT = {
    "id": 7,
    "symbol": "CBA.AU",
    "quantity": Decimal("100"),
    "acquired_at": date(2025, 8, 15),
    "cost_base_normal": Decimal("9000.00"),
}


# ---------------------------------------------------------------------------
# Routing mock
# ---------------------------------------------------------------------------


#: Distinguishes "not supplied, use the default" from "supplied as None", which
#: is a real case here: `fx_row=None` means the AUDUSD lookup found nothing.
_DEFAULT = object()


def _make_conn(
    *,
    lot_rows: list[dict[str, Any]] | None = None,
    price_rows: list[dict[str, Any]] | None = None,
    fx_row: Any = _DEFAULT,
    benchmark_rows: list[dict[str, Any]] | None = None,
    holdings_count: int = 1,
    lots_error: Exception | None = None,
) -> MagicMock:
    """A mock asyncpg connection covering every query `collect()` can issue.

    Routing is by SQL substring, and three near-collisions are disambiguated
    deliberately rather than by luck:

    * `FROM prices` matches BOTH section 8's per-symbol close query and
      `latest_complete_trading_day`'s coverage aggregate. Section 8's is
      selected on its `DISTINCT ON (symbol) symbol, dt, close` projection; the
      coverage query falls through to `[]`.
    * `FROM portfolio_daily_snapshots` matches both section 8's
      `benchmark_tr_level` read and the discipline section's `fx_rate_audusd`
      read. Told apart by the column each selects.
    * `lots_error` fails ONLY the `holding_lots` query, so the fail-loud
      isolation test proves the *outcome* section degraded — not that a mock
      that raises on everything took the brief down for unrelated reasons.
    """
    _lots = lot_rows if lot_rows is not None else [HUBS_LOT]
    _prices = (
        price_rows
        if price_rows is not None
        else [{"symbol": "HUBS.NYSE", "dt": AS_OF, "close": Decimal("205.92")}]
    )
    _fx = (
        {"dt": AS_OF, "rate": Decimal("0.650000")} if fx_row is _DEFAULT else fx_row
    )
    _benchmarks = benchmark_rows if benchmark_rows is not None else []

    conn = MagicMock()

    async def _fetchval(query: str, *args: Any, **kwargs: Any) -> Any:
        q = " ".join(query.split())
        if "COUNT(*)" in q:
            return holdings_count
        if "MAX(p.dt)" in q:
            return AS_OF
        return None

    async def _fetchrow(query: str, *args: Any, **kwargs: Any) -> Any:
        q = " ".join(query.split())
        if "FROM fx_rates" in q:
            return _fx
        return None

    async def _fetch(query: str, *args: Any, **kwargs: Any) -> Any:
        q = " ".join(query.split())
        if "FROM holding_lots" in q:
            if lots_error is not None:
                raise lots_error
            return _lots
        if "DISTINCT ON (symbol) symbol, dt, close" in q:
            return _prices
        if "FROM portfolio_daily_snapshots" in q and "benchmark_tr_level" in q:
            return _benchmarks
        return []

    conn.fetchval = AsyncMock(side_effect=_fetchval)
    conn.fetchrow = AsyncMock(side_effect=_fetchrow)
    conn.fetch = AsyncMock(side_effect=_fetch)
    return conn


def _all_queries(conn: MagicMock) -> list[str]:
    calls = (
        list(conn.fetch.await_args_list)
        + list(conn.fetchval.await_args_list)
        + list(conn.fetchrow.await_args_list)
    )
    return [" ".join(str(c.args[0]).split()) for c in calls if c.args]


def _run_loader(conn: MagicMock) -> OutcomeSection | None:
    return asyncio.run(_lot_outcomes(conn, AS_OF))


def _sleeve(section: OutcomeSection, sleeve: Sleeve):  # type: ignore[no-untyped-def]
    return next(s for s in section.sleeves if s.sleeve is sleeve)


@pytest.fixture
def personal_use() -> Any:
    with patch.dict(os.environ, {"ASXOS_PERSONAL_USE": "1"}):
        yield


# ---------------------------------------------------------------------------
# 1. Snapshot-differencing defect class — `capital_aud` is not on this path
# ---------------------------------------------------------------------------


def test_loader_never_reads_capital_aud(personal_use: Any) -> None:
    """The structural closure, asserted on the SQL text.

    An ASX lot is present so the `portfolio_daily_snapshots` query is genuinely
    issued — otherwise this assertion would pass vacuously on a portfolio that
    happens to hold nothing Australian, which is exactly today's state.
    """
    conn = _make_conn(
        lot_rows=[HUBS_LOT, CBA_LOT],
        price_rows=[
            {"symbol": "HUBS.NYSE", "dt": AS_OF, "close": Decimal("205.92")},
            {"symbol": "CBA.AU", "dt": AS_OF, "close": Decimal("108.00")},
        ],
        benchmark_rows=[
            {
                "as_of": date(2025, 8, 15),
                "benchmark_tr_level": Decimal("80000"),
                "trailing_div_yield_pct": None,
            },
            {
                "as_of": AS_OF,
                "benchmark_tr_level": Decimal("84000"),
                "trailing_div_yield_pct": None,
            },
        ],
    )
    _run_loader(conn)

    queries = _all_queries(conn)
    snapshot_queries = [q for q in queries if "portfolio_daily_snapshots" in q]
    assert snapshot_queries, (
        "the benchmark query was not issued — this test would pass vacuously"
    )
    for q in queries:
        assert "capital_aud" not in q, f"capital_aud read on the outcome path: {q}"

    # Positive companion to the negative above. A substring tripwire cannot see
    # past a `SELECT *`, which would re-expose `capital_aud` while the
    # `not in` assertion stayed green. Pinning the projection to exactly the
    # three columns section 8 needs closes that hole.
    projection = snapshot_queries[0].split("SELECT", 1)[1].split("FROM", 1)[0]
    assert [c.strip() for c in projection.split(",")] == [
        "as_of",
        "benchmark_tr_level",
        "trailing_div_yield_pct",
    ]
    assert "*" not in projection


_BOOK_DELTA_SNAPSHOT_COLS = [
    "as_of",
    "capital_aud",
    "holdings_mv_aud",
    "cash_aud",
    "holdings_count",
]


def _is_book_delta_snapshot_query(q: str) -> bool:
    """True only for Stage 1's two snapshot-level SELECTs, never a return."""
    if "FROM portfolio_daily_snapshots" not in q:
        return False
    if "benchmark_tr_level" in q:
        return False
    if "/" in q:
        return False
    projection = q.split("SELECT", 1)[1].split("FROM", 1)[0]
    if "*" in projection:
        return False
    cols = [c.strip() for c in projection.split(",")]
    return cols == _BOOK_DELTA_SNAPSHOT_COLS


def test_collect_capital_aud_only_on_book_delta_path_and_never_touches_a_model(
    personal_use: Any,
) -> None:
    """Whole-brief firewall; capital_aud is a book-delta *level*, never a return.

    Outcome loader still must not see capital_aud (`test_loader_never_reads_capital_aud`).
    Collect still never touches model_versions or signals.
    """
    conn = _make_conn(
        lot_rows=[HUBS_LOT, CBA_LOT],
        price_rows=[
            {"symbol": "HUBS.NYSE", "dt": AS_OF, "close": Decimal("205.92")},
            {"symbol": "CBA.AU", "dt": AS_OF, "close": Decimal("108.00")},
        ],
        benchmark_rows=[
            {
                "as_of": AS_OF,
                "benchmark_tr_level": Decimal("84000"),
                "trailing_div_yield_pct": None,
            },
        ],
    )

    @asynccontextmanager
    async def fake_acquire() -> Any:
        yield conn

    with patch("asxos.brief.compose.acquire", fake_acquire):
        data = asyncio.run(collect(AS_OF))

    assert data.outcome_error is None
    assert data.outcome_section is not None

    queries = _all_queries(conn)
    assert queries
    delta_qs = [q for q in queries if _is_book_delta_snapshot_query(q)]
    assert len(delta_qs) == 2
    assert any("as_of <= $1" in q for q in delta_qs)
    assert any("as_of < $1" in q for q in delta_qs)
    for q in queries:
        if q in delta_qs:
            continue
        assert "capital_aud" not in q, f"capital_aud read: {q}"
        assert "model_versions" not in q, f"model gate query: {q}"
        assert "FROM signals" not in q, f"signals read: {q}"
    for q in delta_qs:
        assert "model_versions" not in q, f"model gate query: {q}"
        assert "FROM signals" not in q, f"signals read: {q}"


def test_the_open_lot_filter_is_visible_at_the_query(personal_use: Any) -> None:
    """The lot query states `disposed_at IS NULL` itself.

    CORRECTION (2026-08-17): this test was named
    ``..._from_holding_lots_not_the_view`` and asserted that `current_holdings`
    "does not expose `cost_base_normal`". **That is false** — the view selects
    it (`migrations/0001_initial.sql`), and no later migration redefines it. The
    claim was inherited from a wrong comment at `jobs/snapshot_portfolio.py:200-201`
    and propagated into a test *name*, where a reviewer nearly cited it onward.

    Either source would return correct rows. The real reason to read the table is
    that the open-lot predicate is then legible at the call site, rather than
    implied by a view definition in a migration forty files away — a reader
    auditing "does this section include disposed lots?" can answer it here.
    """
    conn = _make_conn()
    _run_loader(conn)
    lot_query = next(q for q in _all_queries(conn) if "cost_base_normal" in q)
    assert "FROM holding_lots" in lot_query
    assert "disposed_at IS NULL" in lot_query


# ---------------------------------------------------------------------------
# 2. The gate — ASXOS_PERSONAL_USE only, no new flag
# ---------------------------------------------------------------------------


def test_section_absent_without_personal_use() -> None:
    with patch.dict(os.environ, {"ASXOS_PERSONAL_USE": "0"}):
        conn = _make_conn()
        assert _run_loader(conn) is None
    assert _all_queries(conn) == [], "gated-out loader still hit the database"


def test_gate_is_not_the_v2_flag(personal_use: Any) -> None:
    """Parity with `_discipline_findings`: one gate, and it is already set.

    `ASXOS_V2_BRIEF_ENABLED` gates the dark V2 tree (deferred to Stage 6). This
    section depends on it in neither direction, which is what makes it
    shippable on V1 today. It used to be asserted against
    `ASXOS_PORTFOLIO_BRIEF_ENABLED` too; that gate was deleted under A-34, and
    an assertion naming a variable nothing reads proves nothing.
    """
    env = {"ASXOS_V2_BRIEF_ENABLED": "0"}
    with patch.dict(os.environ, env):
        section = _run_loader(_make_conn())
    assert section is not None
    assert len(_sleeve(section, Sleeve.global_).lots) == 1


# ---------------------------------------------------------------------------
# 3. Today's actual state — one HUBS lot, empty ASX sleeve
# ---------------------------------------------------------------------------


def test_todays_shape_one_hubs_lot(personal_use: Any) -> None:
    section = _run_loader(_make_conn())
    assert section is not None

    glob = _sleeve(section, Sleeve.global_)
    assert [lot.symbol for lot in glob.lots] == ["HUBS.NYSE"]
    hubs = glob.lots[0]
    assert hubs.return_state is ReturnState.measured
    assert hubs.market_value_aud == Decimal("7603.200000")
    assert hubs.lot_return == Decimal("0.089560")  # +8.96% AUD, not −29%
    assert hubs.benchmark_state is BenchmarkState.not_applicable_sleeve
    assert hubs.alpha is None

    asx = _sleeve(section, Sleeve.asx)
    assert asx.lots == ()
    assert "No open ASX lots" in asx.empty_note


def test_todays_shape_renders_without_crashing_and_without_a_zero(
    personal_use: Any,
) -> None:
    """An empty ASX sleeve must say so, not render a misleading 0.0%."""
    section = _run_loader(_make_conn())
    html = render_html(
        BriefData(
            as_of=AS_OF,
            holdings_count=1,
            latest_price_date=AS_OF,
            outcome_section=section,
        )
    )
    fragment = _outcome_fragment(html)
    assert "No open ASX lots" in fragment
    assert "+8.96%" in fragment
    # The ASX sleeve prints its empty note and no numeric row at all.
    asx_block = fragment.split("ASX sleeve")[1].split("Global sleeve")[0]
    assert "0.00%" not in asx_block
    assert "<table" not in asx_block


def test_no_fx_rate_reports_unavailable_rather_than_a_number(
    personal_use: Any,
) -> None:
    section = _run_loader(_make_conn(fx_row=None))
    assert section is not None
    hubs = _sleeve(section, Sleeve.global_).lots[0]
    assert hubs.return_state is ReturnState.unavailable_no_fx
    assert hubs.lot_return is None


def test_the_loader_selects_the_dates_the_staleness_checks_need(
    personal_use: Any,
) -> None:
    """`dt` on both market queries — without it staleness is unknowable.

    The close query originally selected only `symbol, close`, so the pure layer
    could not tell yesterday's price from one three months old. The date is the
    whole mechanism; asserting the projection keeps a future tidy-up from
    dropping it and silently disabling the guard.
    """
    conn = _make_conn()
    _run_loader(conn)
    queries = _all_queries(conn)
    close_query = next(q for q in queries if "DISTINCT ON (symbol)" in q)
    assert "symbol, dt, close" in close_query
    fx_query = next(q for q in queries if "FROM fx_rates" in q)
    assert "SELECT dt, rate" in fx_query


def test_a_stale_close_degrades_to_unavailable_through_the_loader(
    personal_use: Any,
) -> None:
    """End to end: an old close reaches the render as a named unavailable."""
    stale = AS_OF - timedelta(days=MAX_ANCHOR_LAG_DAYS + 30)
    section = _run_loader(
        _make_conn(
            price_rows=[
                {"symbol": "HUBS.NYSE", "dt": stale, "close": Decimal("205.92")}
            ]
        )
    )
    assert section is not None
    hubs = _sleeve(section, Sleeve.global_).lots[0]
    assert hubs.return_state is ReturnState.unavailable_stale_price
    assert hubs.lot_return is None

    fragment = _outcome_fragment(
        render_html(_brief(outcome_section=section, holdings_count=1))
    )
    assert "+8.96%" not in fragment
    assert "unavailable" in fragment
    assert str(stale) in fragment


def test_the_valuation_date_is_rendered(personal_use: Any) -> None:
    """"Value A$ 7,603.20" with no date invites the reader to assume today."""
    section = _run_loader(_make_conn())
    fragment = _outcome_fragment(
        render_html(_brief(outcome_section=section, holdings_count=1))
    )
    assert f"Valued to {AS_OF}" in fragment


def test_no_open_lots_reports_two_empty_sleeves(personal_use: Any) -> None:
    section = _run_loader(_make_conn(lot_rows=[]))
    assert section is not None
    assert all(s.lots == () and s.empty_note for s in section.sleeves)


def test_no_fx_query_when_nothing_foreign_is_open(personal_use: Any) -> None:
    conn = _make_conn(
        lot_rows=[CBA_LOT],
        price_rows=[{"symbol": "CBA.AU", "dt": AS_OF, "close": Decimal("108.00")}],
    )
    _run_loader(conn)
    assert not any("FROM fx_rates" in q for q in _all_queries(conn))


# ---------------------------------------------------------------------------
# 4. Governor rulings F1 / F2 through the loader
# ---------------------------------------------------------------------------


def test_benchmark_levels_are_not_fetched_for_a_global_only_portfolio(
    personal_use: Any,
) -> None:
    """F2 at the loader: a global lot cannot reach an ASX comparison.

    The outcome layer refuses the blend on its own (`test_benchmark_outcome.py`);
    this asserts the loader does not even fetch the levels, so there is nothing
    to blend in the first place.
    """
    conn = _make_conn()  # HUBS only
    section = _run_loader(conn)
    assert section is not None
    assert not any("benchmark_tr_level" in q for q in _all_queries(conn))
    assert _sleeve(section, Sleeve.global_).lots[0].benchmark_return is None


def test_proxy_level_is_detected_from_trailing_div_yield_pct(
    personal_use: Any,
) -> None:
    """F1: a non-NULL `trailing_div_yield_pct` marks the synthetic overlay.

    `jobs/snapshot_portfolio.py:274-290` writes the assumed yield only on the
    approximation path and leaves it NULL when `benchmark_tr_level` is the real
    accumulation index. That column is the sole record of which path ran.
    """
    conn = _make_conn(
        lot_rows=[CBA_LOT],
        price_rows=[{"symbol": "CBA.AU", "dt": AS_OF, "close": Decimal("108.00")}],
        benchmark_rows=[
            {
                "as_of": date(2025, 8, 15),
                "benchmark_tr_level": Decimal("80000"),
                "trailing_div_yield_pct": Decimal("4.0"),
            },
            {
                "as_of": AS_OF,
                "benchmark_tr_level": Decimal("84000"),
                "trailing_div_yield_pct": Decimal("4.0"),
            },
        ],
    )
    section = _run_loader(conn)
    assert section is not None
    lot = _sleeve(section, Sleeve.asx).lots[0]
    assert lot.benchmark_state is BenchmarkState.unavailable_proxy
    assert lot.benchmark_return is None
    assert lot.alpha is None
    assert lot.lot_return == Decimal("0.200000")  # its own return still reported


def test_real_index_levels_measure_the_benchmark(personal_use: Any) -> None:
    conn = _make_conn(
        lot_rows=[CBA_LOT],
        price_rows=[{"symbol": "CBA.AU", "dt": AS_OF, "close": Decimal("108.00")}],
        benchmark_rows=[
            {
                "as_of": date(2025, 8, 15),
                "benchmark_tr_level": Decimal("80000"),
                "trailing_div_yield_pct": None,
            },
            {
                "as_of": AS_OF,
                "benchmark_tr_level": Decimal("84000"),
                "trailing_div_yield_pct": None,
            },
        ],
    )
    section = _run_loader(conn)
    assert section is not None
    lot = _sleeve(section, Sleeve.asx).lots[0]
    assert lot.benchmark_state is BenchmarkState.measured
    assert lot.benchmark_return == Decimal("0.050000")
    assert lot.alpha == Decimal("0.150000")


# ---------------------------------------------------------------------------
# 5. `_resolve_anchor`
# ---------------------------------------------------------------------------


def _snap(day: date, level: str, yield_pct: str | None = None) -> dict[str, Any]:
    return {
        "as_of": day,
        "benchmark_tr_level": Decimal(level),
        "trailing_div_yield_pct": None if yield_pct is None else Decimal(yield_pct),
    }


def test_resolve_anchor_takes_the_latest_row_on_or_before_the_target() -> None:
    rows = [
        _snap(date(2026, 8, 10), "80000"),
        _snap(date(2026, 8, 14), "81000"),
        _snap(date(2026, 8, 17), "82000"),
    ]
    anchor = _resolve_anchor(rows, date(2026, 8, 15))  # type: ignore[arg-type]
    assert anchor == BenchmarkAnchor(
        as_of=date(2026, 8, 14), level=Decimal("81000"), is_proxy=False
    )


def test_resolve_anchor_never_reaches_forward() -> None:
    """Reaching forward would measure a window the lot never had."""
    rows = [_snap(date(2026, 8, 14), "81000")]
    assert _resolve_anchor(rows, date(2026, 8, 1)) is None  # type: ignore[arg-type]
    assert _resolve_anchor([], date(2026, 8, 1)) is None


def test_resolve_anchor_marks_the_proxy() -> None:
    rows = [_snap(date(2026, 8, 14), "81000", "4.0")]
    anchor = _resolve_anchor(rows, date(2026, 8, 17))  # type: ignore[arg-type]
    assert anchor is not None and anchor.is_proxy is True


# ---------------------------------------------------------------------------
# 6. Render — StrictUndefined, error banner, absence
# ---------------------------------------------------------------------------

_START = "<!-- outcome:start -->"
_END = "<!-- outcome:end -->"


def _outcome_fragment(html: str) -> str:
    """Section 8's rendered text, isolated from the rest of the page.

    The rest of the brief legitimately prints "Portfolio discipline", "holdings"
    and the CLEAR/ATTENTION/BLOCKED review tokens — all of which are in the
    frozen advice vocabulary. Extracting this section is what lets the firewall
    assertion below run the FULL list instead of a weakened one.
    """
    assert _START in html and _END in html, "outcome section markers missing"
    return html.split(_START, 1)[1].split(_END, 1)[0]


def _brief(**overrides: Any) -> BriefData:
    defaults: dict[str, Any] = {
        "as_of": AS_OF,
        "holdings_count": 1,
        "latest_price_date": AS_OF,
    }
    defaults.update(overrides)
    return BriefData(**defaults)


def test_strict_undefined_still_passes_without_the_section() -> None:
    """`render_html` uses `jinja2.StrictUndefined`; a missing name must raise.

    A brief with no outcome section still renders, and still emits the markers,
    so the extraction never depends on the section's own state.
    """
    html = render_html(_brief())
    assert _outcome_fragment(html).strip() == ""


def test_outcome_error_renders_a_loud_banner_not_silence() -> None:
    html = render_html(_brief(outcome_error="outcome section could not run: boom"))
    fragment = _outcome_fragment(html)
    assert "could not run" in fragment
    assert "boom" in fragment
    assert 'class="banner"' in fragment


def test_outcome_error_wins_over_a_partial_section(personal_use: Any) -> None:
    """A brief cannot both fail and report — the failure is the honest state."""
    section = _run_loader(_make_conn())
    html = render_html(_brief(outcome_section=section, outcome_error="boom"))
    fragment = _outcome_fragment(html)
    assert "could not run" in fragment
    assert "+8.96%" not in fragment


def test_a_failed_outcome_section_cannot_coexist_with_a_clear_headline() -> None:
    """The exact co-reachable pair review found: CLEAR above a red banner.

    Zero holdings + fresh prices + no findings is otherwise the one genuinely
    ``CLEAR`` brief. Add a crashed section 8 and the header must stop saying
    "nothing to review" — that is `asxos/domain/review/status.py`'s stated
    purpose ("an absence of evidence presented as evidence of absence")
    reappearing through a section added after the module was written.
    """
    clear = _brief(holdings_count=0)
    assert clear.review.status is ReviewStatus.clear  # the control

    failed = _brief(holdings_count=0, outcome_error="outcome section could not run: x")
    assert failed.review.status is ReviewStatus.evidence_thin
    assert any("Outcome vs benchmark not measured" in u for u in failed.review.unknowns)

    html = render_html(failed)
    assert "EVIDENCE_THIN" in html
    assert "could not run" in _outcome_fragment(html)


def test_a_measured_outcome_section_does_not_disturb_the_headline(
    personal_use: Any,
) -> None:
    """Unknown only on failure — a section that ran must not itself raise state."""
    section = _run_loader(_make_conn())
    data = _brief(holdings_count=0, outcome_section=section)
    assert data.review.status is ReviewStatus.clear
    assert not any("Outcome vs benchmark" in u for u in data.review.unknowns)


def test_outcome_error_is_an_unknown_not_a_blocker() -> None:
    """EVIDENCE_THIN, not BLOCKED — section 8 measures, it does not check.

    The adjacent discipline loaders map their failures to blocking. This one
    deliberately does not, so the distinction is pinned rather than incidental:
    a real `error` finding still outranks it.
    """
    only_outcome = _brief(outcome_error="boom")
    assert only_outcome.review.status is ReviewStatus.evidence_thin
    assert any("Outcome vs benchmark" in u for u in only_outcome.review.unknowns)

    with_discipline_error = _brief(
        outcome_error="boom",
        discipline_findings=[
            DisciplineFinding(
                check="discipline_section",
                level=DisciplineLevel.error,
                message="⚠ discipline section could not run: x",
            )
        ],
    )
    assert with_discipline_error.review.status is ReviewStatus.blocked


def test_a_loader_failure_does_not_take_down_the_brief(personal_use: Any) -> None:
    conn = _make_conn(lots_error=RuntimeError("db exploded"))

    @asynccontextmanager
    async def fake_acquire() -> Any:
        yield conn

    with patch("asxos.brief.compose.acquire", fake_acquire):
        data = asyncio.run(collect(AS_OF))

    assert data.outcome_section is None
    assert data.outcome_error is not None
    assert "db exploded" in data.outcome_error
    assert "could not run" in render_html(data)


# ---------------------------------------------------------------------------
# 7. s766B personal-advice firewall
# ---------------------------------------------------------------------------


def _every_rendered_state() -> list[tuple[str, str]]:
    """(name, fragment) for each shape section 8 can take, for the grep sweep."""
    from asxos.domain.benchmark.outcome import LotInput, build_outcome_section

    def anchor(day: date, level: str, proxy: bool = False) -> BenchmarkAnchor:
        return BenchmarkAnchor(as_of=day, level=Decimal(level), is_proxy=proxy)

    measured = LotInput(
        lot_id=7,
        symbol="CBA.AU",
        quantity=Decimal("100"),
        acquired_at=date(2025, 8, 15),
        cost_base_aud=Decimal("9000"),
        close=_obs("108"),
        fx_audusd=None,
        benchmark_start=anchor(date(2025, 8, 15), "80000"),
        benchmark_end=anchor(AS_OF, "84000"),
    )
    proxied = LotInput(
        lot_id=8,
        symbol="BHP.AU",
        quantity=Decimal("50"),
        acquired_at=date(2025, 8, 15),
        cost_base_aud=Decimal("2000"),
        close=_obs("30"),  # a loss, so the negative branch renders too
        fx_audusd=None,
        benchmark_start=anchor(date(2025, 8, 15), "80000", True),
        benchmark_end=anchor(AS_OF, "84000", True),
    )
    no_series = LotInput(
        lot_id=9,
        symbol="ANZ.AU",
        quantity=Decimal("5"),
        acquired_at=date(2025, 8, 15),
        cost_base_aud=Decimal("1000"),
        close=None,
        fx_audusd=None,
        benchmark_start=None,
        benchmark_end=None,
    )
    stale_window = LotInput(
        lot_id=10,
        symbol="WES.AU",
        quantity=Decimal("5"),
        acquired_at=date(2025, 8, 15),
        cost_base_aud=Decimal("1000"),
        close=_obs("200"),
        fx_audusd=None,
        benchmark_start=anchor(date(2025, 1, 1), "70000"),
        benchmark_end=anchor(AS_OF, "84000"),
    )
    bad_cost_base = LotInput(
        lot_id=11,
        symbol="TLS.AU",
        quantity=Decimal("5"),
        acquired_at=date(2025, 8, 15),
        cost_base_aud=Decimal("0"),
        close=_obs("4"),
        fx_audusd=None,
        benchmark_start=None,
        benchmark_end=None,
    )
    hubs = LotInput(
        lot_id=1,
        symbol="HUBS.NYSE",
        quantity=Decimal("24"),
        acquired_at=date(2025, 6, 2),
        cost_base_aud=Decimal("6978.23"),
        close=_obs("205.92"),
        fx_audusd=_obs("0.65"),
        benchmark_start=None,
        benchmark_end=None,
    )
    no_fx = LotInput(
        lot_id=12,
        symbol="AAPL.US",
        quantity=Decimal("5"),
        acquired_at=date(2025, 8, 15),
        cost_base_aud=Decimal("1000"),
        close=_obs("200"),
        fx_audusd=None,
        benchmark_start=None,
        benchmark_end=None,
    )
    every_lot = build_outcome_section(
        [measured, proxied, no_series, stale_window, bad_cost_base, hubs, no_fx], AS_OF
    )
    return [
        ("absent", _outcome_fragment(render_html(_brief()))),
        (
            "error",
            _outcome_fragment(render_html(_brief(outcome_error="could not run: x"))),
        ),
        (
            "empty",
            _outcome_fragment(
                render_html(_brief(outcome_section=build_outcome_section([], AS_OF)))
            ),
        ),
        (
            "hubs_only",
            _outcome_fragment(
                render_html(
                    _brief(outcome_section=build_outcome_section([hubs], AS_OF))
                )
            ),
        ),
        (
            "every_state",
            _outcome_fragment(render_html(_brief(outcome_section=every_lot))),
        ),
    ]


def test_no_advice_vocabulary_in_any_rendered_state() -> None:
    """The full frozen P2 list, over every shape this section can render.

    Not "no advice words in the happy path" — the unavailable notes, the error
    banner and the empty-sleeve prose are prose too, and prose is where advice
    creeps in.
    """
    for name, fragment in _every_rendered_state():
        for pattern in _ADVICE_PATTERNS:
            match = pattern.search(fragment)
            assert match is None, (
                f"advice vocabulary {pattern.pattern!r} surfaced in the {name} "
                f"rendering: {match.group(0)!r}"
            )


#: The subset that must not appear ANYWHERE on the page. The full list cannot be
#: applied page-wide — the pre-existing header prints CLEAR/ATTENTION/BLOCKED and
#: the discipline section prints "Portfolio discipline" and "holdings", all of
#: which are legitimate descriptive nouns for the user's own data. These, by
#: contrast, are instruction verbs and rating nouns with no honest use anywhere
#: in a model-independent evidence brief.
_PAGE_WIDE_PATTERNS = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\brecommend",
        r"\brating\b",
        r"\bprice target\b",
        r"\btarget price\b",
        r"\boverweight\b",
        r"\bunderweight\b",
        r"\baccumulate\b",
        r"\bdivest",
        r"take[ -]?profit",
        r"\ballocat",
        r"\bstop[ -]loss\b",
    )
)


def test_no_instruction_vocabulary_anywhere_on_the_page(personal_use: Any) -> None:
    section = _run_loader(_make_conn())
    html = render_html(_brief(outcome_section=section))
    for pattern in _PAGE_WIDE_PATTERNS:
        match = pattern.search(html)
        assert match is None, (
            f"instruction vocabulary {pattern.pattern!r} on the page: {match.group(0)!r}"
        )


def test_the_proxy_is_never_rendered_carrying_a_total_return_label() -> None:
    """Governor ruling F1, asserted on the rendered HTML.

    The synthetic overlay is a yield approximation on a PRICE index. The brief
    may say "unavailable" and name the approximation; it may not present it as
    the accumulation benchmark, in either spelling of the label.
    """
    from asxos.domain.benchmark.outcome import LotInput, build_outcome_section

    proxied = LotInput(
        lot_id=8,
        symbol="BHP.AU",
        quantity=Decimal("50"),
        acquired_at=date(2025, 8, 15),
        cost_base_aud=Decimal("2000"),
        # Deliberately NOT a close that yields +5.00%: the benchmark levels below
        # move +5.00%, so a lot whose own return coincided would make the final
        # assertion pass for the wrong reason. 50 × 30 = 1500 → −25.00%.
        close=_obs("30"),
        fx_audusd=None,
        benchmark_start=BenchmarkAnchor(date(2025, 8, 15), Decimal("80000"), True),
        benchmark_end=BenchmarkAnchor(AS_OF, Decimal("84000"), True),
    )
    fragment = _outcome_fragment(
        render_html(_brief(outcome_section=build_outcome_section([proxied], AS_OF)))
    )
    lowered = fragment.lower()
    assert "unavailable" in lowered
    assert "approximation" in lowered
    assert "total-return" not in lowered
    assert "total return" not in lowered
    assert "-25.00%" in fragment  # the lot's own return is still reported
    # The benchmark column must carry no number for a proxied lot: +5.00% is the
    # proxy's own move, and printing it would be the silent substitution F1
    # forbids by name.
    assert "+5.00%" not in fragment
