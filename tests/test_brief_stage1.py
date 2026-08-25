"""Stage 1: BLUF reorder, exception filter, deltas empty copy, detail page."""

from __future__ import annotations

from datetime import UTC, date, datetime

from asxos.brief.compose import (
    NEWS_DISABLED,
    BriefData,
    render_detail_html,
    render_html,
)
from asxos.brief.section import assemble_sections
from asxos.domain.review.status import directive_terms
from asxos.domain.theses.discipline import DisciplineFinding, DisciplineLevel

FIXED = datetime(2026, 5, 22, 8, 0, tzinfo=UTC)
AS_OF = date(2026, 5, 22)

_INFO = DisciplineFinding(
    check="cgt_discount_boundary",
    level=DisciplineLevel.info,
    symbol="CBA.AU",
    message="CBA.AU lot 42 reaches the 12-month CGT-discount threshold in 10d",
)
_RED = DisciplineFinding(
    check="revisit_overdue",
    level=DisciplineLevel.red,
    symbol="CBA.AU",
    message="CBA.AU: review overdue by 16d (due 2026-06-27)",
)


def _brief(**overrides) -> BriefData:
    defaults = {
        "as_of": AS_OF,
        "latest_price_date": AS_OF,
        "data_as_of": AS_OF,
        "holdings_count": 1,
        "regulatory_hits": [],
        "job_failures": [],
        "news_status": NEWS_DISABLED,
        "discipline_findings": [_INFO, _RED],
    }
    defaults.update(overrides)
    if "sections" not in defaults:
        prices_stale = (
            defaults["latest_price_date"] is None
            or (defaults["as_of"] - defaults["latest_price_date"]).days > 5
        )
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


def test_render_html_integrity_before_review() -> None:
    html = render_html(_brief())
    assert html.index("Integrity") < html.index("Review:")
    assert html.index("Integrity") < html.index("Evidence only.")


def test_render_html_includes_bluf() -> None:
    data = _brief()
    html = render_html(data)
    assert 'id="bluf"' in html
    assert data.bluf in html
    assert directive_terms(data.bluf) == ()


def test_info_omitted_from_exceptions() -> None:
    data = _brief()
    assert _INFO not in data.exception_findings
    assert _RED in data.exception_findings
    html = render_html(data)
    assert "review overdue" in html
    assert "CGT-discount threshold" not in html
    assert 'class="disc-info"' not in html


def test_deltas_empty_copy() -> None:
    html = render_html(_brief())
    assert "<h2>Deltas</h2>" in html
    assert "No prior snapshot to compare." in html


def test_detail_renderer_includes_info_finding() -> None:
    html = render_detail_html(_brief())
    assert "CGT-discount threshold" in html
    assert 'class="disc-info"' in html
    assert "review overdue" in html
