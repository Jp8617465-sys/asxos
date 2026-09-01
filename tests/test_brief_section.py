"""Stage 0 SectionResult seam — pure mapper + constructor contract."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from asxos.brief.section import (
    SECTION_ORDER,
    SectionResult,
    SectionStatus,
    assemble_sections,
    news_to_status,
)

FIXED = datetime(2026, 5, 22, 8, 0, tzinfo=UTC)


def test_missing_requires_error() -> None:
    with pytest.raises(ValueError, match="MISSING"):
        SectionResult(name="news", status=SectionStatus.MISSING)


def test_news_to_status_four_states() -> None:
    assert news_to_status("ok") is SectionStatus.FRESH
    assert news_to_status("unverified") is SectionStatus.STALE
    assert news_to_status("quiet") is SectionStatus.EMPTY
    assert news_to_status("disabled") is SectionStatus.EMPTY
    assert news_to_status("ok", error="boom") is SectionStatus.MISSING
    assert news_to_status("mystery") is SectionStatus.MISSING


def _assemble(**overrides):  # type: ignore[no-untyped-def]
    defaults = {
        "latest_price_date": date(2026, 5, 22),
        "prices_stale": False,
        "job_failures": [],
        "discipline_findings": [],
        "outcome_section": None,
        "outcome_error": None,
        "regulatory_hits": [],
        "news_items": [],
        "news_status": "disabled",
        "news_error": None,
        "portfolio_section": None,
        "computed_at": FIXED,
        "data_as_of": date(2026, 5, 22),
    }
    defaults.update(overrides)
    return assemble_sections(**defaults)


def test_assemble_quiet_day_empty_not_missing() -> None:
    sections = _assemble()
    assert list(sections) == list(SECTION_ORDER)
    assert sections["prices"].status is SectionStatus.FRESH
    assert sections["jobs"].status is SectionStatus.EMPTY
    assert sections["discipline"].status is SectionStatus.EMPTY
    assert sections["outcome"].status is SectionStatus.EMPTY
    assert sections["regulatory"].status is SectionStatus.EMPTY
    assert sections["news"].status is SectionStatus.EMPTY
    assert sections["portfolio"].status is SectionStatus.EMPTY
    assert sections["news"].error is None


def test_assemble_stale_prices() -> None:
    sections = _assemble(prices_stale=True)
    assert sections["prices"].status is SectionStatus.STALE
    assert sections["prices"].data is not None


def test_assemble_missing_prices() -> None:
    sections = _assemble(latest_price_date=None, prices_stale=True)
    assert sections["prices"].status is SectionStatus.MISSING
    assert sections["prices"].error
    assert sections["prices"].data is None


def test_assemble_news_collector_failure_is_missing() -> None:
    sections = _assemble(news_status="unverified", news_error="news section could not run: boom")
    assert sections["news"].status is SectionStatus.MISSING
    assert "boom" in (sections["news"].error or "")
    assert sections["news"].data is None


def test_assemble_news_unverified_without_error_is_stale() -> None:
    sections = _assemble(news_status="unverified")
    assert sections["news"].status is SectionStatus.STALE
    assert sections["news"].error is None
