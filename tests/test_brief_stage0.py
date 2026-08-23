"""Stage 0: integrity line, four-state markers, golden snapshots."""
from __future__ import annotations

import re
from datetime import UTC, date, datetime
from pathlib import Path

from asxos.brief.compose import (
    NEWS_DISABLED,
    NEWS_OK,
    NEWS_UNVERIFIED,
    BriefData,
    render_html,
)
from asxos.brief.section import SectionResult, SectionStatus, assemble_sections

GOLDEN_DIR = Path(__file__).parent / "golden" / "brief"
FIXED = datetime(2026, 5, 22, 8, 0, tzinfo=UTC)
AS_OF = date(2026, 5, 22)


def _integrity(html: str) -> str:
    match = re.search(
        r'<table role="presentation" class="integrity.*?</table>',
        html,
        re.S,
    )
    assert match is not None, html[:800]
    return match.group(0)


def _brief(**overrides) -> BriefData:
    defaults = dict(
        as_of=AS_OF,
        latest_price_date=AS_OF,
        data_as_of=AS_OF,
        holdings_count=0,
        regulatory_hits=[],
        job_failures=[],
        news_status=NEWS_DISABLED,
    )
    defaults.update(overrides)
    if "sections" not in defaults:
        prices_stale = defaults["latest_price_date"] is None or (
            defaults["as_of"] - defaults["latest_price_date"]
        ).days > 5
        defaults["sections"] = assemble_sections(
            latest_price_date=defaults["latest_price_date"],
            prices_stale=prices_stale,
            job_failures=defaults.get("job_failures", []),
            discipline_findings=defaults.get("discipline_findings", []),
            outcome_section=defaults.get("outcome_section"),
            outcome_error=defaults.get("outcome_error"),
            regulatory_hits=defaults.get("regulatory_hits", []),
            news_items=defaults.get("news_items", []),
            news_status=str(defaults.get("news_status", NEWS_DISABLED)),
            news_error=defaults.get("news_error"),
            portfolio_section=defaults.get("portfolio_section"),
            computed_at=FIXED,
            data_as_of=defaults.get("data_as_of"),
        )
    defaults.pop("news_error", None)
    return BriefData(**defaults)


def test_integrity_line_always_present() -> None:
    html = render_html(_brief())
    assert 'id="integrity-line"' in html
    assert "Integrity" in html
    assert "Review:" in html
    assert html.index("Review:") < html.index("Integrity")
    assert html.index("Integrity") < html.index("Evidence only.")


def test_fresh_prices_not_warning_chrome() -> None:
    html = render_html(_brief())
    frag = _integrity(html)
    assert "integrity-warn" not in frag
    assert 'class="sec-FRESH">FRESH</span>' in frag
    assert "prices as-of 2026-05-22" in frag


def test_stale_prices_warning_chrome() -> None:
    html = render_html(_brief(latest_price_date=date(2026, 5, 10)))
    frag = _integrity(html)
    assert "integrity-warn" in frag
    assert 'class="sec-STALE">STALE</span>' in frag


def test_missing_and_empty_markers_render() -> None:
    sections = assemble_sections(
        latest_price_date=None,
        prices_stale=True,
        job_failures=[],
        discipline_findings=[],
        outcome_section=None,
        outcome_error="outcome section could not run: boom",
        regulatory_hits=[],
        news_items=[],
        news_status="ok",
        news_error="news section could not run: boom",
        portfolio_section=None,
        computed_at=FIXED,
        data_as_of=None,
    )
    # Force jobs EMPTY, news MISSING, outcome MISSING, prices MISSING.
    html = render_html(
        _brief(
            latest_price_date=None,
            data_as_of=None,
            news_status=NEWS_UNVERIFIED,
            outcome_error="outcome section could not run: boom",
            sections=sections,
        )
    )
    frag = _integrity(html)
    assert "integrity-warn" in frag
    assert 'class="sec-MISSING">MISSING</span>' in frag
    assert 'class="sec-EMPTY">EMPTY</span>' in frag
    assert "news:" in frag
    assert "outcome:" in frag


def test_ok_news_is_fresh_on_integrity_line() -> None:
    html = render_html(_brief(news_status=NEWS_OK, news_items=[]))
    # assemble from news_status=ok with empty items still FRESH per mapper
    # (payload present as empty list is still "ok" — EMPTY is quiet/disabled).
    frag = _integrity(html)
    assert re.search(r"news: <span class=\"sec-FRESH\">FRESH</span>", frag)


def _assert_golden(name: str, html: str) -> None:
    path = GOLDEN_DIR / name
    got = _integrity(html) + "\n"
    assert path.is_file(), f"missing golden {path}"
    assert path.read_text() == got


def test_golden_quiet_day() -> None:
    _assert_golden("integrity_quiet.html", render_html(_brief()))


def test_golden_stale_prices() -> None:
    _assert_golden(
        "integrity_stale_prices.html",
        render_html(_brief(latest_price_date=date(2026, 5, 10))),
    )


def test_golden_four_states() -> None:
    sections = {
        "prices": SectionResult(
            name="prices",
            status=SectionStatus.STALE,
            data={"latest_price_date": date(2026, 5, 10)},
            computed_at=FIXED,
            source="test",
        ),
        "jobs": SectionResult(
            name="jobs", status=SectionStatus.EMPTY, data=[], computed_at=FIXED, source="test"
        ),
        "discipline": SectionResult(
            name="discipline",
            status=SectionStatus.FRESH,
            data=["x"],
            computed_at=FIXED,
            source="test",
        ),
        "outcome": SectionResult(
            name="outcome",
            status=SectionStatus.MISSING,
            data=None,
            computed_at=FIXED,
            source="test",
            error="boom",
        ),
        "regulatory": SectionResult(
            name="regulatory",
            status=SectionStatus.EMPTY,
            data=[],
            computed_at=FIXED,
            source="test",
        ),
        "news": SectionResult(
            name="news",
            status=SectionStatus.MISSING,
            data=None,
            computed_at=FIXED,
            source="test",
            error="boom",
        ),
        "portfolio": SectionResult(
            name="portfolio",
            status=SectionStatus.EMPTY,
            data=None,
            computed_at=FIXED,
            source="test",
        ),
    }
    html = render_html(
        _brief(latest_price_date=date(2026, 5, 10), data_as_of=date(2026, 5, 10), sections=sections)
    )
    _assert_golden("integrity_four_states.html", html)
