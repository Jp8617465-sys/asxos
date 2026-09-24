"""The memo carries every derived figure verbatim and no directive vocabulary."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from html import escape

from asxos.domain.mandate import Goals, derive
from asxos.domain.mandate.memo import render_memo
from asxos.domain.review.status import directive_terms


def _goals() -> Goals:
    return Goals(
        as_of=date(2026, 9, 19), investable_assets_aud=Decimal("25000"), income_aud_pa=Decimal("120000"),
        savings_aud_pa=Decimal("30000"), target_wealth_aud=Decimal("1000000"), horizon_years=10,
        drawdown_tolerance_pct=Decimal("25"), emergency_months=0, account_type="individual",
        marginal_rate_pct=Decimal("37"), brokerage_aud_per_side=Decimal("5"),
    )


def test_memo_states_every_figure_and_its_trace() -> None:
    g = _goals()
    m = derive(g)
    html = render_memo(g, m)
    o = m.outputs
    for name, value in o:
        if hasattr(value, "traced_to"):
            assert f"data-field='{name}'" in html, name
            assert escape(value.traced_to)[:40] in html, name
    for a in o.sleeve_allocations:
        assert f"data-sleeve='{a.sleeve_id}'" in html
    assert "4.625" in html and "17.5" in html and "etf_core_plus_sleeves" not in html  # prose, not the enum
    assert g.content_hash[:12] in html and m.content_hash[:12] in html


def test_memo_uses_no_directive_terms() -> None:
    g = _goals()
    html = render_memo(g, derive(g))
    assert directive_terms(html) == ()


def test_memo_renders_the_etf_only_case_without_sleeves() -> None:
    g = _goals().model_copy(update={"investable_assets_aud": Decimal("7749.54"), "content_hash": ""})
    g = Goals.model_validate(g.model_dump(exclude={"content_hash"}))
    html = render_memo(g, derive(g))
    assert "ETF-only" in html and "data-sleeve='slv-mom-12-1-v1'" not in html
