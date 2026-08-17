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
import dataclasses
import os
import re
from contextlib import asynccontextmanager
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import jinja2
import pytest

from asxos.brief import compose
from asxos.brief.compose import (
    NEWS_DISABLED,
    NEWS_OK,
    NEWS_QUIET,
    NEWS_UNVERIFIED,
    BriefData,
    DisciplineFinding,
    DisciplineLevel,
    JobFailure,
    NewsItem,
    RegulatoryHit,
    _cgt_boundary_findings,
    _discipline_findings,
    collect,
    render_html,
)
from asxos.domain.review.status import ReviewStatus, directive_terms

# ---------------------------------------------------------------------------
# render_html — pure path
# ---------------------------------------------------------------------------

def _brief(**overrides) -> BriefData:
    defaults = {
        "as_of": date(2026, 5, 22),
        "latest_price_date": date(2026, 5, 22),
        "holdings_count": 3,
        "regulatory_hits": [],
        "job_failures": [],
    }
    defaults.update(overrides)
    # A fixture that supplies news items is modelling a day that HAS news, so it
    # gets NEWS_OK unless it states otherwise. The production default stays
    # NEWS_DISABLED (see BriefData.news_status) — that default renders the
    # section away, which would silently vacuum up any assertion about its
    # contents and pass. Tests that exercise the empty states pass news_status
    # explicitly.
    if overrides.get("news_items") and "news_status" not in overrides:
        defaults["news_status"] = NEWS_OK
    return BriefData(**defaults)


def test_render_html_contains_title() -> None:
    html = render_html(_brief())
    assert "asxos brief — 2026-05-22" in html


# ---------------------------------------------------------------------------
# Review status — the model-independent headline (packet P1 item 4)
# ---------------------------------------------------------------------------


def test_review_clear_when_nothing_flagged_and_nothing_unknown() -> None:
    b = _brief(holdings_count=0)
    assert b.review.status is ReviewStatus.clear
    assert "CLEAR" in render_html(b)


def test_review_evidence_thin_when_holdings_have_no_discipline_evidence() -> None:
    """3 holdings, every check silent: that is 'we did not look', not 'all well'.

    The failure this closes is the calm-looking brief. Before the four-state
    vocabulary the header printed a regime label and moved on; a discipline
    section that produced nothing was indistinguishable from one that ran clean.
    """
    b = _brief(holdings_count=3, discipline_findings=[])
    assert b.review.status is ReviewStatus.evidence_thin
    assert b.review.unknowns  # the reason is named, not implied
    assert "EVIDENCE_THIN" in render_html(b)


def test_an_info_finding_does_not_count_as_discipline_evidence() -> None:
    """A CGT-boundary fact is evidence about tax, not about the thesis.

    `_cgt_boundary_findings` appends `info` rows into the same
    `discipline_findings` list the discipline checks use. Keying the "no
    evidence" unknown on that list being *empty* would let one CGT line make a
    wholly unchecked portfolio read CLEAR — the quiet neutral again, arriving
    through a side door.
    """
    cgt_only = DisciplineFinding(
        check="cgt_discount_boundary",
        level=DisciplineLevel.info,
        message="CBA.AU lot #7: 12-month CGT discount in 12d",
        symbol="CBA.AU",
    )
    b = _brief(holdings_count=3, discipline_findings=[cgt_only])
    assert b.review.status is ReviewStatus.evidence_thin
    assert any("no discipline evidence" in u for u in b.review.unknowns)

    # A real discipline check having run does clear the unknown.
    checked = _brief(
        holdings_count=3, discipline_findings=[cgt_only, _REVISIT_OVERDUE_FINDING]
    )
    assert not any("no discipline evidence" in u for u in checked.review.unknowns)


def test_review_attention_when_a_finding_needs_the_governor() -> None:
    b = _brief(discipline_findings=[_REVISIT_OVERDUE_FINDING])
    assert b.review.status is ReviewStatus.attention
    assert "ATTENTION" in render_html(b)


def test_review_blocked_when_a_check_could_not_run() -> None:
    """An `error` finding means the check did not compute — no view is available."""
    b = _brief(discipline_findings=[_TRAJECTORY_ERROR_FINDING])
    assert b.review.status is ReviewStatus.blocked
    assert "BLOCKED" in render_html(b)


def test_review_blocked_outranks_attention() -> None:
    b = _brief(discipline_findings=[_REVISIT_OVERDUE_FINDING, _TRAJECTORY_ERROR_FINDING])
    assert b.review.status is ReviewStatus.blocked


def test_review_attention_not_masked_by_an_unrelated_unknown() -> None:
    """A real finding must not be downgraded to EVIDENCE_THIN because prices are
    stale. The unknown is still carried on the outcome and still printed."""
    b = _brief(
        discipline_findings=[_REVISIT_OVERDUE_FINDING],
        latest_price_date=date(2026, 5, 1),
    )
    assert b.review.status is ReviewStatus.attention
    assert any("Prices stale" in u for u in b.review.unknowns)
    assert "Prices stale" in render_html(b)


def test_review_blocked_on_job_failure() -> None:
    b = _brief(
        job_failures=[
            JobFailure(job_name="sync_prices", as_of=date(2026, 5, 22), error_message="HTTP 503")
        ]
    )
    assert b.review.status is ReviewStatus.blocked


def test_render_html_shows_freshness_banner_when_prices_stale() -> None:
    """Freshness banner appears when latest_price_date is >5 days before as_of.

    This is the model-INDEPENDENT warning that must never be suppressed. It
    previously shared a banner with a Model A "Signals stale" line whose
    suppression was wired to the shelf flag; the price warning survives that
    removal unchanged.
    """
    html = render_html(_brief(latest_price_date=date(2026, 5, 10)))
    assert "Data freshness warning" in html
    assert "Prices stale" in html
    assert "2026-05-10" in html


def test_render_html_freshness_banner_absent_when_fresh() -> None:
    html = render_html(_brief(holdings_count=0))
    assert "Data freshness warning" not in html


def test_render_html_unknowns_are_printed_never_defaulted() -> None:
    """No price data at all → the banner says so instead of rendering a blank."""
    html = render_html(_brief(latest_price_date=None))
    assert "no data" in html
    assert "Prices stale" in html


# ---------------------------------------------------------------------------
# Adversarial: the brief is model-independent, and cannot quietly stop being so
#
# These replace the pre-retirement model-gate tests (manifest T9). Those asserted
# that a *quarantined* model's sections were skipped — a property that only
# exists while there is a model to quarantine. The assertions below are strictly
# stronger: there is no state of `model_versions`, and no BriefData, that puts
# model-derived content into this brief, because no code path reads one.
# ---------------------------------------------------------------------------

_MODEL_VOCABULARY = (
    "Model A",
    "model_a",
    "shelved",
    "Regime:",
    "Signal caveat",
    "Signal changes",
    "Signals stale",
    "top driver",
    "STRONG_BUY",
    "STRONG_SELL",
    "shap",
)


def test_rendered_brief_contains_no_model_vocabulary() -> None:
    """Every Model A surface is gone from the rendered page, in every state."""
    briefs = [
        _brief(),
        _brief(holdings_count=0),
        _brief(latest_price_date=None, data_as_of=None),
        _brief(discipline_findings=[_REVISIT_OVERDUE_FINDING, _TRAJECTORY_ERROR_FINDING]),
    ]
    for b in briefs:
        html = render_html(b)
        for token in _MODEL_VOCABULARY:
            assert token not in html, f"{token!r} leaked into the brief"


def test_review_status_surfaces_issue_no_trade_direction() -> None:
    """The brief's OWN copy — headline, caveat, unknowns banner — is directive-free.

    Read the scope narrowly, because a broader reading would be false comfort on
    an s766B property:

    * It covers the copy this module and template author: the review headline,
      the evidence-only caveat, and the unknowns banner.
    * It does NOT cover text this brief merely relays. Collector-authored finding
      messages, news headlines (`{{ n.title }}`) and RBA titles (`{{ r.title }}`)
      render verbatim, and routinely contain directive words for legitimate
      reasons — `asxos/domain/brief/severity.py:67` emits "CGT boundary in 3d —
      do not sell", which is a prohibition, not an instruction, and correctly
      stays.
    * It does NOT cover the gated "Portfolio adjustments" section, which is a
      trade *proposal* surface by design (and cannot be populated at all while
      the allocator's candidate source is retired).

    So: findings and portfolio section deliberately empty, to isolate the copy.
    """
    b = _brief()
    assert b.discipline_findings == []
    assert b.portfolio_section is None
    assert b.news_items == []
    assert b.regulatory_hits == []
    assert directive_terms(render_html(b)) == ()

    # And in the states where the brief writes the most of its own copy.
    thin = _brief(holdings_count=3, latest_price_date=None)
    assert thin.review.status is ReviewStatus.evidence_thin
    assert directive_terms(render_html(thin)) == ()


def test_brief_data_has_no_model_fields() -> None:
    """The fields that carried model state are gone, not merely unused.

    `regime`, `signal_changes`, `latest_signal_date` and the `model_shelved`
    suppression flag were the brief's entire model surface.
    """
    names = {f.name for f in dataclasses.fields(BriefData)}
    for gone in ("regime", "signal_changes", "latest_signal_date", "model_shelved"):
        assert gone not in names
    assert not hasattr(BriefData, "signals_stale")


def test_compose_module_imports_are_model_independent() -> None:
    """Mechanical import contract, in the style of test_thesis_discipline.py.

    A docstring promise that this module never reads a model is worth nothing on
    its own — this is what makes re-adding the dependency fail a test.
    """
    source = Path(compose.__file__).read_text()
    # `line.strip()`, not `line` — an indented import is still an import, and
    # this module already uses one (`collect()` lazy-imports `asxos.db.acquire`
    # inside the function body). Matching only column-0 imports would let a
    # function-local `from asxos.domain.models.production_gate import ...` walk
    # straight past the test whose entire job is to catch it.
    import_lines = [
        line for line in source.splitlines()
        if line.strip().startswith(("import ", "from "))
    ]
    banned = ("production_gate", "domain.models", "domain.signals", "brief.shap")
    for line in import_lines:
        for token in banned:
            assert token not in line, f"model-dependent import reintroduced: {line}"


def test_brief_template_source_has_no_model_references() -> None:
    """The template is checked directly, not only through a render.

    Three of the five `model_shelved` references were `{% if %}` conditions, so a
    render-only assertion can pass while the dead branches sit in the file.
    """
    template = (
        Path(compose.__file__).parent / "templates" / "brief.html.j2"
    ).read_text()
    for token in ("model_shelved", "signal_changes", "signals_stale",
                  "latest_signal_date", "d.regime", "label-"):
        assert token not in template, f"{token!r} still in brief.html.j2"


# ---------------------------------------------------------------------------
# Adversarial: the silent-failure class this retirement could have shipped
# ---------------------------------------------------------------------------


def test_template_environment_is_strict_about_undefined_names() -> None:
    """`StrictUndefined`, asserted on the real environment render_html uses.

    Jinja's default `Undefined` is falsy and renders empty. Under it, deleting
    `BriefData.model_shelved` while the template still said
    `{% if not d.model_shelved %}` would have silently *un*-suppressed the whole
    dead signal section — no exception, no failing job, no alert. This test is
    the tripwire for that entire class of failure, not for one field.
    """
    env = compose.brief_env()
    assert env.undefined is jinja2.StrictUndefined
    with pytest.raises(jinja2.UndefinedError):
        env.from_string("{% if d.model_shelved %}x{% endif %}").render(d=_brief())


def test_render_html_raises_on_a_missing_field_rather_than_rendering_empty() -> None:
    """End-to-end proof through the real template loader, not a string template."""
    env = compose.brief_env()
    with pytest.raises(jinja2.UndefinedError):
        env.from_string("{{ d.regime }}").render(d=_brief())


# ---------------------------------------------------------------------------
# Evidence-only caveat (replaces the retired signal caveat)
# ---------------------------------------------------------------------------


def test_render_html_contains_evidence_only_caveat() -> None:
    html = render_html(_brief())
    assert "Evidence only." in html
    assert "model-independent" in html
    assert "CLEAR / ATTENTION / BLOCKED / EVIDENCE_THIN" in html
    assert "no instruction to act on any holding" in html


def test_render_html_caveat_sits_under_the_headline_not_buried() -> None:
    html = render_html(_brief())
    assert html.index("Review:") < html.index("Evidence only.")
    assert html.index("Evidence only.") < html.index("Regulatory hits on holdings")


def test_render_html_renders_empty_states() -> None:
    html = render_html(_brief())
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
    holdings_count,
    tax_rows,
    reg_rows,
    hold_syms,
    fail_rows,
    news_rows=None,
    news_job_rows=None,
    latest_price_date=None,
    model_gate_rows=None,
):
    """Build a mock asyncpg connection that routes queries to canned rows.

    news_rows:          rows for ``FROM holding_news`` queries (_holding_news)
    news_job_rows:      rows for ``FROM job_runs … job_name = 'ingest_news'`` (_news_ingest_fresh)
    latest_price_date:  return value for ``SELECT MAX(p.dt) FROM prices ...``
    model_gate_rows:    rows this mock would return for a ``FROM model_versions``
                        query. Kept deliberately, with no consumer: it is the
                        instrument for
                        ``test_collect_never_queries_model_versions_or_signals``,
                        which proves collect() issues no such query in any
                        model_versions state.
    """
    _latest_price_date = latest_price_date
    _model_gate_rows = (
        model_gate_rows if model_gate_rows is not None else [{"model": "model_a"}]
    )

    conn = MagicMock()
    conn.fetchrow = AsyncMock(return_value=None)

    async def _fetchval(query, *args, **kwargs):
        q = " ".join(query.split())
        if "COUNT(*)" in q:
            return holdings_count
        if "MAX(p.dt)" in q:
            return _latest_price_date
        return None

    conn.fetchval = AsyncMock(side_effect=_fetchval)

    async def _fetch(query, *args, **kwargs):
        q = " ".join(query.split())
        if "FROM model_versions" in q:
            return _model_gate_rows
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


def _all_queries(conn) -> list[str]:
    """Every SQL string collect() passed to this mock, across all three verbs."""
    calls = (
        list(conn.fetch.await_args_list)
        + list(conn.fetchval.await_args_list)
        + list(conn.fetchrow.await_args_list)
    )
    return [" ".join(str(c.args[0]).split()) for c in calls if c.args]


def test_collect_assembles_brief_data() -> None:
    today = date(2026, 5, 22)
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
        holdings_count=2,
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

    assert data.holdings_count == 2
    assert len(data.regulatory_hits) == 1
    assert data.regulatory_hits[0].symbol == "BHP.AU"
    assert data.has_failures
    assert data.job_failures[0].job_name == "sync_fundamentals"


def test_collect_handles_empty_db() -> None:
    today = date(2026, 5, 22)
    conn = _make_conn(
        holdings_count=0,
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

    assert data.holdings_count == 0
    assert not data.has_failures


@pytest.mark.parametrize(
    "model_gate_rows",
    [
        pytest.param([], id="zero_approved_models"),
        pytest.param([{"model": "model_a"}], id="one_approved_model"),
        pytest.param(
            [{"model": "model_a"}, {"model": "factor_sleeve"}],
            id="multiple_approved_models",
        ),
    ],
)
def test_collect_never_queries_model_versions_or_signals(model_gate_rows) -> None:
    """Adversarial, replacing manifest T9's two model-gate tests.

    Those asserted the brief *skipped* its model sections when 0 or >1 models
    were approved — a conditional property, and one that quietly depends on the
    gate call still being there to do the skipping. This asserts the
    unconditional one: whatever `model_versions` contains, collect() issues no
    `model_versions` query and no `signals` query at all, and the brief is
    identical in all three states. There is no configuration that re-enables a
    model surface, because there is no surface left to enable.
    """
    today = date(2026, 5, 22)
    conn = _make_conn(
        holdings_count=2,
        tax_rows=[],
        reg_rows=[],
        hold_syms=[],
        fail_rows=[],
        model_gate_rows=model_gate_rows,
    )

    @asynccontextmanager
    async def fake_acquire():
        yield conn

    with patch("asxos.brief.compose.acquire", fake_acquire):
        data = asyncio.run(collect(today))

    queries = _all_queries(conn)
    assert queries, "collect() issued no queries — the routing mock is misconfigured"
    for q in queries:
        assert "model_versions" not in q, f"model gate query survived: {q}"
        assert "FROM signals" not in q, f"signals read survived: {q}"
        assert "shap_factors" not in q, f"SHAP read survived: {q}"

    # Model-INDEPENDENT data is unaffected in every gate state.
    assert data.holdings_count == 2


def test_collect_anchors_on_complete_trading_day() -> None:
    """collect() records the latest *complete* trading day as data_as_of.

    The anchor outlived the signal queries it was introduced for, but its meaning
    narrowed with them: it is now a statement about PRICE completeness only,
    since every remaining collector is computed on the calendar as_of. The
    template labels it "Prices complete to" for exactly that reason — calling it
    "evidence as of" would assert a provenance no query backs, which is the same
    fabrication the four-state vocabulary exists to stop.
    """
    calendar_today = date(2026, 6, 18)
    complete_day = date(2026, 6, 17)
    conn = _make_conn(
        holdings_count=1,
        tax_rows=[],
        reg_rows=[],
        hold_syms=[],
        fail_rows=[],
        latest_price_date=complete_day,
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
    assert data.prices_stale is False
    html = render_html(data)
    assert "Prices complete to: 2026-06-17" in html
    assert "Evidence as of" not in html


# ---------------------------------------------------------------------------
# M14a — news section render_html tests
# ---------------------------------------------------------------------------


def test_render_html_shows_news_section() -> None:
    """When news_items are populated the section appears in the HTML."""
    html = render_html(
        _brief(
            news_status=NEWS_OK,
            news_items=[
                NewsItem(
                    symbols=["BHP.AU"],
                    title="BHP quarterly results",
                    url="https://example.com/bhp",
                    published_at=date(2026, 5, 23),
                    sentiment="positive",
                )
            ],
        )
    )
    assert "BHP.AU" in html
    assert "BHP quarterly results" in html
    assert "https://example.com/bhp" in html
    assert "sentiment-positive" in html
    assert "Market news on holdings" in html


# ---------------------------------------------------------------------------
# News empty-state honesty (M0)
#
# INVERTED from test_render_html_news_section_absent_when_no_items, which
# asserted `"Market news on holdings" not in html` for an empty list and
# described the silence approvingly as "no empty-state placeholder". That
# assertion pinned the defect, so it had to be inverted rather than
# supplemented: an omitted section and a reported quiet day are mutually
# exclusive renderings of the same input.
#
# Silence is the problem. An absent section reads to James as "nothing
# happened", which is indistinguishable from "ingestion has written zero rows
# for a month" — the 2026-08 false-green shape one layer up, in the surface he
# actually reads. Only NEWS_QUIET may assert that no news was found.
# ---------------------------------------------------------------------------


def test_render_html_quiet_reports_no_news_rather_than_vanishing() -> None:
    """A verified-fresh, genuinely empty ingest states that finding explicitly."""
    html = render_html(_brief(news_status=NEWS_QUIET, news_items=[]))

    assert "Market news on holdings" in html, (
        "a quiet day is a reportable finding, not an omitted section"
    )
    assert "No qualifying news found" in html
    assert "not</strong> evidence" not in html, (
        "quiet must not carry the unverified disclaimer"
    )


def test_render_html_unverified_does_not_claim_no_news() -> None:
    """An unverified ingest must NOT be rendered as a quiet day.

    This is the distinction the whole change exists for. Both states carry zero
    items; only one of them licenses the sentence "no qualifying news was
    found". Rendering `unverified` as quiet would manufacture a finding out of a
    pipeline failure.
    """
    html = render_html(_brief(news_status=NEWS_UNVERIFIED, news_items=[]))

    assert "Market news on holdings" in html
    assert "News unavailable" in html
    assert "not</strong> evidence" in html, "must disclaim absence-as-evidence"
    assert "No qualifying news found" not in html, (
        "an unverified pipeline must never assert that no news existed"
    )


def test_render_html_disabled_omits_the_section_entirely() -> None:
    """A gated-off feature is the one case where silence is correct.

    NEWS_DISABLED means the surface is not running at all — rendering a state
    line would imply a live pipeline that reported something.
    """
    html = render_html(_brief(news_status=NEWS_DISABLED, news_items=[]))
    assert "Market news on holdings" not in html


def test_render_html_unrecognised_status_fails_closed() -> None:
    """An unknown status omits the section rather than defaulting to a claim.

    `news_status` is a bare str, so a typo or a future state added to the
    collector without a template arm reaches here. The outer guard is a positive
    allowlist for that reason: the failure mode of an unrecognised value is a
    missing section, not the 'News unavailable' copy asserted about a state
    nobody established.
    """
    html = render_html(_brief(news_status="some-future-state", news_items=[]))
    assert "Market news on holdings" not in html
    assert "News unavailable" not in html


def test_brief_data_defaults_to_disabled_not_quiet() -> None:
    """The default must never silently claim a verified quiet day.

    A BriefData constructed without news (older call sites, fixtures) defaults
    to NEWS_DISABLED. Defaulting to NEWS_QUIET would let any incomplete
    construction assert a finding it never established.
    """
    assert BriefData(as_of=date(2026, 5, 22),
                     holdings_count=1).news_status == NEWS_DISABLED


def test_render_html_news_section_escapes_title() -> None:
    """Malicious title in news item is HTML-escaped (autoescape active)."""
    html = render_html(
        _brief(
            news_status=NEWS_OK,
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
        holdings_count=1,
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
        holdings_count=1,
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
        holdings_count=1,
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
    # The loader's theses query also selects `status` and the derived
    # `last_answering_revision_at`; default them here so fixtures predating the
    # escalation check stay minimal. Explicit keys in a fixture row win.
    #
    # The default mirrors production rather than the maximally-escalating case:
    # `open_thesis()` always writes an 'opened' revision, so no live thesis has
    # a NULL anchor. Behaviour-identical (the check falls back to `opened_at`),
    # but a fixture that says "never answered" should say so deliberately.
    thesis_rows = [
        {"status": "active", "last_answering_revision_at": r["opened_at"], **r}
        for r in (thesis_rows or [])
    ]
    holding_rows = holding_rows or []
    price_rows = price_rows or []
    fx_rows = fx_rows or []
    captured: list[str] = []

    async def _fetch(query, *args, **kwargs):
        q = " ".join(query.split())
        captured.append(q)
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
    # Exposed so a test can assert on the SQL itself: this fixture dispatches on
    # a substring and ignores the rest of the query, so without this the WHERE
    # clause is entirely unpinned.
    conn.captured_queries = captured
    return conn


def _theses_query(conn) -> str:
    """The theses query as actually issued (whitespace-normalised)."""
    return next(q for q in conn.captured_queries if "FROM theses" in q)


def _cba_row(**overrides):
    """The live worked example's row shape: recorded ladder 60 vs live 168.

    Mirrors `_cba_detached` in test_thesis_discipline.py — three loader tests
    need this same 10-field row and only ever differ in status / anchor date.
    """
    row = {
        "symbol": "CBA.AU",
        "status": "watching",
        # 2026-06-27 is 16 days BEFORE the tests' as_of (2026-07-13), so the
        # `revisit_overdue` arm of the watching-row negative control is LIVE.
        # A future-dated default silently made that assertion vacuous.
        "revisit_due_at": datetime(2026, 6, 27),
        "opened_at": datetime(2026, 1, 10),
        "timeline_days": None,
        "actual_entry_price": None,
        "target_price": Decimal("60"),
        "stop_price": Decimal("42"),
        "conviction_level": 3,
        "last_answering_revision_at": datetime(2026, 5, 1),  # 73d before as_of
    }
    row.update(overrides)
    return row


_CBA_PRICE_ROWS = [{"symbol": "CBA.AU", "close": Decimal("168")}]


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
    # This fixture (opened 2026-01-10, never answered, as_of 2026-07-13) is also
    # past the escalation window, so it now emits a THIRD line. Pinned
    # explicitly: the assertions above are membership checks and would have
    # absorbed the new finding silently.
    esc = next(f for f in findings if f.check == "data_sanity_escalation")
    assert esc.level == DisciplineLevel.red
    assert "no answering revision for 184d" in esc.message


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


def test_discipline_findings_escalates_unanswered_watching_thesis() -> None:
    """The 2026-07-16 CBA ruling's escalation half, end-to-end at the loader:
    a `watching` thesis (which the full active-only check battery never sees)
    carrying a detached ladder with no answering revision for more than one
    revisit cadence emits the escalated red naming both CLI verbs."""
    conn = _disc_conn(thesis_rows=[_cba_row()], price_rows=_CBA_PRICE_ROWS)

    with patch.dict(os.environ, _PERSONAL_USE_ON):
        findings = asyncio.run(_discipline_findings(conn, date(2026, 7, 13)))

    esc = next(f for f in findings if f.check == "data_sanity_escalation")
    assert esc.level == DisciplineLevel.red
    assert esc.symbol == "CBA.AU"
    assert "no answering revision for 73d" in esc.message
    assert "asx thesis revise CBA.AU --target <corrected>" in esc.message
    assert "asx thesis revise CBA.AU --status expired" in esc.message
    # Provenance: an uninvested watchlist row is not evidence about a holding.
    assert esc.watchlist_only is True
    # The watching row runs ONLY the escalation pass — no revisit/timeline/
    # data-sanity noise from the active-only battery leaks in for it.
    assert not any(
        f.check in ("revisit_overdue", "data_sanity", "timeline") for f in findings
    )


def test_watchlist_escalation_does_not_count_as_holding_evidence() -> None:
    """A `watching` escalation must NOT silence the "no discipline evidence"
    unknown: the row carries no capital, so it says nothing about whether any
    HOLDING was checked. Before `watchlist_only` this was the one side door the
    `info`-level exclusion did not cover — a portfolio where zero holdings were
    evaluated would have read as checked (packet P1 required-work item 5)."""
    conn = _disc_conn(thesis_rows=[_cba_row()], price_rows=_CBA_PRICE_ROWS)
    with patch.dict(os.environ, _PERSONAL_USE_ON):
        findings = asyncio.run(_discipline_findings(conn, date(2026, 7, 13)))

    b = _brief(holdings_count=3, discipline_findings=findings)
    assert any("no discipline evidence" in u for u in b.review.unknowns)
    # The red itself still raises ATTENTION (it is a real finding and must be
    # acted on); what matters here is that the unknown survives beside it —
    # "something is wrong with a watchlist record" and "no holding was checked"
    # are both true, and the brief says both.
    assert b.review.status is ReviewStatus.attention

    # …while the same finding from an ACTIVE thesis is holding evidence and
    # does clear the unknown.
    active_conn = _disc_conn(
        thesis_rows=[_cba_row(status="active", actual_entry_price=Decimal("50"))],
        price_rows=_CBA_PRICE_ROWS,
    )
    with patch.dict(os.environ, _PERSONAL_USE_ON):
        active_findings = asyncio.run(
            _discipline_findings(active_conn, date(2026, 7, 13))
        )
    checked = _brief(holdings_count=3, discipline_findings=active_findings)
    assert not any("no discipline evidence" in u for u in checked.review.unknowns)


def test_discipline_findings_active_thesis_gets_base_red_and_escalation() -> None:
    """An active thesis past the window carries BOTH lines: the base
    data-sanity red (evidence) and the escalation (the named verbs)."""
    conn = _disc_conn(
        thesis_rows=[_cba_row(status="active", actual_entry_price=Decimal("50"))],
        price_rows=_CBA_PRICE_ROWS,
    )

    with patch.dict(os.environ, _PERSONAL_USE_ON):
        findings = asyncio.run(_discipline_findings(conn, date(2026, 7, 13)))

    checks = {f.check for f in findings}
    assert "data_sanity" in checks
    assert "data_sanity_escalation" in checks
    esc = next(f for f in findings if f.check == "data_sanity_escalation")
    assert esc.watchlist_only is False  # capital behind it → holding evidence


def test_discipline_findings_answering_revision_suppresses_escalation() -> None:
    """An answered red on an ACTIVE thesis: the base data-sanity red still
    fires (the evidence is never suppressed) but the escalation does not.

    Deliberately active, not watching — on a watching row the whole result is
    `[]`, which would pass a "no escalation" assertion for the wrong reason.
    """
    conn = _disc_conn(
        thesis_rows=[
            _cba_row(
                status="active",
                actual_entry_price=Decimal("50"),
                last_answering_revision_at=datetime(2026, 7, 8),  # 5d before as_of
            )
        ],
        price_rows=_CBA_PRICE_ROWS,
    )

    with patch.dict(os.environ, _PERSONAL_USE_ON):
        findings = asyncio.run(_discipline_findings(conn, date(2026, 7, 13)))

    checks = {f.check for f in findings}
    assert "data_sanity" in checks  # evidence survives the answer
    assert "data_sanity_escalation" not in checks


def test_discipline_findings_watching_answered_red_is_wholly_silent() -> None:
    """The honest limitation, pinned rather than papered over: on a `watching`
    row an answering revision means TOTAL silence — the base red never runs
    there, so nothing at all surfaces. The `revision_type` scoping in the query
    is what keeps an unrelated edit (--tax-notes, --conviction) from reaching
    this state; this test exists so a future widening of that filter is felt."""
    conn = _disc_conn(
        thesis_rows=[_cba_row(last_answering_revision_at=datetime(2026, 7, 8))],
        price_rows=_CBA_PRICE_ROWS,
    )

    with patch.dict(os.environ, _PERSONAL_USE_ON):
        findings = asyncio.run(_discipline_findings(conn, date(2026, 7, 13)))

    assert findings == []


def test_discipline_query_keeps_its_governance_and_status_filters() -> None:
    """`_disc_conn` dispatches on a substring and ignores the rest of the SQL,
    so without this the WHERE clause is unpinned: dropping
    `governance_status = 'approved'` would admit agent-authored
    `pending_review` theses into the brief with every other test still green
    (adjacent to the documented `m14_candidate_agent_db_role_scoping` risk)."""
    conn = _disc_conn(thesis_rows=[_cba_row()], price_rows=_CBA_PRICE_ROWS)
    with patch.dict(os.environ, _PERSONAL_USE_ON):
        asyncio.run(_discipline_findings(conn, date(2026, 7, 13)))

    q = _theses_query(conn)
    assert "governance_status = 'approved'" in q
    assert "status IN ('watching', 'active')" in q
    # The answering-revision scoping is equally load-bearing: MAX over ALL
    # revisions would let an unrelated edit mute the escalation for 30 days.
    # Set-equality, NOT prefix-plus-denylist: a denylist passes when a NEW type
    # is added. Verified — adding 'analyst_action' (the type most likely to
    # become a job-driven feed) to the SQL list passed the entire suite while
    # silently re-opening the suppression hole this scoping exists to close.
    scoped = re.search(r"revision_type IN \(([^)]*)\)", q)
    assert scoped is not None, "the answering-revision scoping is gone"
    assert {t.strip().strip("'") for t in scoped.group(1).split(",")} == {
        "target_adjusted",
        "reviewed_no_change",
        "status_change",
        "entered",
        "expired",
        "exited",
        "exited_by_stop",
        "exited_by_target",
    }


# ---------------------------------------------------------------------------
# collect() wiring for discipline_findings (PR2a)
# ---------------------------------------------------------------------------


def test_collect_discipline_findings_quiet_by_default() -> None:
    today = date(2026, 5, 22)
    conn = _make_conn(
        holdings_count=0,
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
        holdings_count=1,
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
