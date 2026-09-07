"""Versioned ASX Trade cash-market exception calendar.

The table is transcribed from ASX's official cash-market trading calendar,
verified 2026-09-08. Normal weekdays are inferred only inside covered years;
unknown years return ``UNKNOWN`` so callers emit a diagnostic instead of
misclassifying missing market data as actionable code work.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from enum import StrEnum
from typing import Final, Literal

ASX_CALENDAR_SOURCE: Final = (
    "https://www.asx.com.au/markets/market-resources/trading-hours-calendar/"
    "cash-market-trading-hours/trading-calendar"
)
ASX_CALENDAR_VERIFIED_AT: Final = dt.date(2026, 9, 8)
ASX_CALENDAR_YEARS: Final = frozenset({2026, 2027})


class MarketSession(StrEnum):
    OPEN = "open"
    CLOSED = "closed"
    PARTIAL = "partial"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class CalendarRecord:
    date: dt.date
    market: Literal["ASX"]
    session: Literal[MarketSession.CLOSED, MarketSession.PARTIAL]
    source_url: str
    source_year: int
    verified_at: dt.date
    name: str
    source_note: str | None = None


@dataclass(frozen=True, slots=True)
class SessionAssessment:
    date: dt.date
    market: Literal["ASX"]
    session: MarketSession
    reason: Literal["calendar_exception", "weekend", "normal_weekday", "out_of_horizon"]
    record: CalendarRecord | None = None

    @property
    def is_trading_day(self) -> bool | None:
        if self.session is MarketSession.UNKNOWN:
            return None
        return self.session in {MarketSession.OPEN, MarketSession.PARTIAL}


def _record(
    iso_date: str,
    session: Literal[MarketSession.CLOSED, MarketSession.PARTIAL],
    name: str,
    *,
    source_note: str | None = None,
) -> CalendarRecord:
    day = dt.date.fromisoformat(iso_date)
    return CalendarRecord(
        date=day,
        market="ASX",
        session=session,
        source_url=ASX_CALENDAR_SOURCE,
        source_year=day.year,
        verified_at=ASX_CALENDAR_VERIFIED_AT,
        name=name,
        source_note=source_note,
    )


ASX_CALENDAR: Final[tuple[CalendarRecord, ...]] = (
    _record("2026-01-01", MarketSession.CLOSED, "New Year's Day"),
    _record("2026-01-26", MarketSession.CLOSED, "Australia Day"),
    _record("2026-04-03", MarketSession.CLOSED, "Good Friday"),
    _record("2026-04-06", MarketSession.CLOSED, "Easter Monday"),
    _record("2026-04-25", MarketSession.CLOSED, "ANZAC Day"),
    _record("2026-06-08", MarketSession.CLOSED, "King's Birthday"),
    _record("2026-12-24", MarketSession.PARTIAL, "Last business day before Christmas Day"),
    _record("2026-12-25", MarketSession.CLOSED, "Christmas Day"),
    _record("2026-12-28", MarketSession.CLOSED, "Boxing Day substitute"),
    _record("2026-12-31", MarketSession.PARTIAL, "Last business day of the year"),
    _record("2027-01-01", MarketSession.CLOSED, "New Year's Day"),
    _record("2027-01-26", MarketSession.CLOSED, "Australia Day"),
    _record("2027-03-26", MarketSession.CLOSED, "Good Friday"),
    _record("2027-03-29", MarketSession.CLOSED, "Easter Monday"),
    _record("2027-04-26", MarketSession.CLOSED, "ANZAC Day substitute"),
    _record("2027-06-14", MarketSession.CLOSED, "King's Birthday"),
    _record("2027-12-24", MarketSession.PARTIAL, "Last business day before Christmas Day"),
    _record(
        "2027-12-27",
        MarketSession.CLOSED,
        "Christmas Day substitute",
        source_note=(
            "ASX calendar footnote [5] states 'Substitute for Saturday 25 December'; "
            "the substitute weekday is Monday 27 December."
        ),
    ),
    _record("2027-12-28", MarketSession.CLOSED, "Boxing Day substitute"),
    _record("2027-12-31", MarketSession.PARTIAL, "Last business day of the year"),
)


def _validated_index() -> dict[dt.date, CalendarRecord]:
    index: dict[dt.date, CalendarRecord] = {}
    for record in ASX_CALENDAR:
        if record.date in index:
            raise RuntimeError(f"duplicate ASX calendar date: {record.date}")
        if record.market != "ASX":
            raise RuntimeError(f"unexpected market in ASX calendar: {record.market}")
        if record.source_year != record.date.year:
            raise RuntimeError(f"source_year mismatch for {record.date}")
        if record.source_year not in ASX_CALENDAR_YEARS:
            raise RuntimeError(f"calendar entry outside declared horizon: {record.date}")
        if record.source_url != ASX_CALENDAR_SOURCE:
            raise RuntimeError(f"non-official source for {record.date}")
        if record.verified_at != ASX_CALENDAR_VERIFIED_AT:
            raise RuntimeError(f"verification date mismatch for {record.date}")
        index[record.date] = record
    if {record.source_year for record in ASX_CALENDAR} != ASX_CALENDAR_YEARS:
        raise RuntimeError("each declared ASX calendar year must contain an exception record")
    return index


_ASX_CALENDAR_BY_DATE: Final = _validated_index()


def asx_session(day: dt.date) -> SessionAssessment:
    """Classify a date without guessing beyond the checked-in horizon."""

    if day.year not in ASX_CALENDAR_YEARS:
        return SessionAssessment(
            date=day,
            market="ASX",
            session=MarketSession.UNKNOWN,
            reason="out_of_horizon",
        )
    record = _ASX_CALENDAR_BY_DATE.get(day)
    if record is not None:
        return SessionAssessment(
            date=day,
            market="ASX",
            session=MarketSession(record.session),
            reason="calendar_exception",
            record=record,
        )
    if day.weekday() >= 5:
        return SessionAssessment(
            date=day,
            market="ASX",
            session=MarketSession.CLOSED,
            reason="weekend",
        )
    return SessionAssessment(
        date=day,
        market="ASX",
        session=MarketSession.OPEN,
        reason="normal_weekday",
    )
