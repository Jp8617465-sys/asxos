"""Tests for ``asxos.clock`` — the reporting-timezone wall clock.

The substantive test here is ``test_pipeline_window_is_already_tomorrow_in_sydney``:
it pins the actual defect the sweep fixed, rather than just asserting the helper
calls the stdlib correctly.
"""
from __future__ import annotations

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import pytest

from asxos import clock
from asxos.config import CoreSettings

SYDNEY = ZoneInfo("Australia/Sydney")


def test_reporting_tz_is_the_configured_zone() -> None:
    """One copy of the zone name, and it is clock's own.

    Before this module existed, asxos_tz was a CoreSettings field read by exactly zero
    code paths — a dead-config finding this module retired. It then moved out of
    CoreSettings altogether when daily-digest, a lane with no DATABASE_URL, died importing
    this module through CoreSettings() (incident #389). Two copies would be the old
    finding back; the second assertion keeps it at one.
    """
    assert clock.settings.asxos_tz == "Australia/Sydney"
    assert "asxos_tz" not in CoreSettings.model_fields
    assert clock.reporting_tz() == SYDNEY


def test_today_matches_sydney_wall_clock() -> None:
    assert clock.today() == datetime.now(SYDNEY).date()


def test_today_returns_a_plain_date() -> None:
    assert type(clock.today()) is date


@pytest.mark.parametrize(
    ("utc_instant", "offset_label", "expected_sydney_day"),
    [
        # daily-brief fires at 20:30 UTC. In JULY the offset is AEST (+10):
        # 20:30 UTC + 10h = 06:30 the NEXT day in Sydney.
        (datetime(2026, 7, 15, 20, 30, tzinfo=UTC), "AEST +10", date(2026, 7, 16)),
        # In JANUARY the offset is AEDT (+11): 20:30 UTC + 11h = 07:30 next day.
        (datetime(2026, 1, 15, 20, 30, tzinfo=UTC), "AEDT +11", date(2026, 1, 16)),
        # pipeline-health at 22:00 UTC — same conclusion, further into the day.
        (datetime(2026, 7, 15, 22, 0, tzinfo=UTC), "AEST +10", date(2026, 7, 16)),
        # nightly-check at 15:17 UTC: chosen precisely so the two dates differ.
        (datetime(2026, 7, 15, 15, 17, tzinfo=UTC), "AEST +10", date(2026, 7, 16)),
    ],
)
def test_pipeline_window_is_already_tomorrow_in_sydney(
    utc_instant: datetime, offset_label: str, expected_sydney_day: date
) -> None:
    """The bug, pinned.

    Every scheduled workflow in this repo runs in a window where the UTC
    calendar day and the Sydney calendar day DIFFER. A bare date.today() on the
    runner returns the UTC day — i.e. yesterday by Sydney reckoning — on every
    single run, under both AEST and AEDT. This is not a DST edge case.
    """
    utc_day = utc_instant.date()
    sydney_day = utc_instant.astimezone(SYDNEY).date()

    assert sydney_day == expected_sydney_day
    assert sydney_day != utc_day, (
        f"{offset_label}: expected the Sydney day to differ from the UTC day "
        "in the pipeline window"
    )
    assert (sydney_day - utc_day).days == 1


def test_dst_transition_does_not_shift_the_date_answer() -> None:
    """Across the AEDT->AEST changeover, the +1-day conclusion still holds.

    2026-04-05 is the first Sunday in April — the AEDT->AEST transition. The
    offset changes; the fact that 20:30 UTC is already the next Sydney day does
    not.
    """
    for day in (date(2026, 4, 4), date(2026, 4, 5), date(2026, 4, 6)):
        instant = datetime(day.year, day.month, day.day, 20, 30, tzinfo=UTC)
        assert (instant.astimezone(SYDNEY).date() - day).days == 1
