"""Exchange-accurate calendar tests for closed-loop product probes."""

from __future__ import annotations

from dataclasses import fields
from datetime import date

import pytest

from asxos.control_plane.asx_calendar import (
    ASX_CALENDAR,
    ASX_CALENDAR_SOURCE,
    ASX_CALENDAR_VERIFIED_AT,
    ASX_CALENDAR_YEARS,
    CalendarRecord,
    MarketSession,
    asx_session,
)


def test_calendar_record_contract_has_every_required_provenance_field() -> None:
    assert {field.name for field in fields(CalendarRecord)} >= {
        "date",
        "market",
        "session",
        "source_url",
        "source_year",
        "verified_at",
    }


def test_calendar_uses_only_the_official_asx_source_and_declared_years() -> None:
    assert ASX_CALENDAR_SOURCE.startswith("https://www.asx.com.au/")
    assert ASX_CALENDAR_VERIFIED_AT == date(2026, 9, 8)
    assert {record.source_year for record in ASX_CALENDAR} == ASX_CALENDAR_YEARS
    assert all(record.source_url == ASX_CALENDAR_SOURCE for record in ASX_CALENDAR)
    assert all(record.source_year == record.date.year for record in ASX_CALENDAR)
    assert [record.date for record in ASX_CALENDAR] == sorted(
        record.date for record in ASX_CALENDAR
    )


@pytest.mark.parametrize(
    "record",
    [record for record in ASX_CALENDAR if record.session is MarketSession.CLOSED],
    ids=lambda record: record.date.isoformat(),
)
def test_each_checked_in_closed_holiday_is_closed(record: CalendarRecord) -> None:
    assessment = asx_session(record.date)

    assert assessment.session is MarketSession.CLOSED
    assert assessment.reason == "calendar_exception"
    assert assessment.record == record
    assert assessment.is_trading_day is False


@pytest.mark.parametrize(
    "record",
    [record for record in ASX_CALENDAR if record.session is MarketSession.PARTIAL],
    ids=lambda record: record.date.isoformat(),
)
def test_each_checked_in_partial_session_is_a_trading_day(record: CalendarRecord) -> None:
    assessment = asx_session(record.date)

    assert assessment.session is MarketSession.PARTIAL
    assert assessment.reason == "calendar_exception"
    assert assessment.record == record
    assert assessment.is_trading_day is True


def test_weekend_and_normal_weekday_are_classified_inside_horizon() -> None:
    weekend = asx_session(date(2026, 9, 12))
    weekday = asx_session(date(2026, 9, 9))

    assert weekend.session is MarketSession.CLOSED
    assert weekend.reason == "weekend"
    assert weekday.session is MarketSession.OPEN
    assert weekday.reason == "normal_weekday"


def test_out_of_horizon_fails_closed_even_when_date_is_a_weekend() -> None:
    assessment = asx_session(date(2028, 1, 1))

    assert assessment.session is MarketSession.UNKNOWN
    assert assessment.reason == "out_of_horizon"
    assert assessment.record is None
    assert assessment.is_trading_day is None


def test_2027_christmas_substitute_weekday_is_closed() -> None:
    assessment = asx_session(date(2027, 12, 27))

    assert assessment.session is MarketSession.CLOSED
    assert assessment.record is not None
    assert assessment.record.source_note is not None
    assert "Substitute for Saturday 25 December" in assessment.record.source_note
