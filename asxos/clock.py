"""Wall-clock date resolution, anchored to the reporting timezone.

Why this module exists
----------------------
Every scheduled job in this repo runs on a UTC GitHub Actions runner. A bare
``date.today()`` there resolves to the *UTC* calendar day, which is 10 or 11
hours behind Sydney. The daily pipeline fires at 20:30 UTC — already the next
calendar day in Sydney — so a bare call inside it returns **yesterday's date by
Sydney reckoning, year-round**, under both AEST (+10) and AEDT (+11).

That is not a DST edge case that bites twice a year. It is wrong on every run.

Relationship to the UTC pin in ``asxos/db.py``
----------------------------------------------
These two are complements, not contradictions, and the distinction is easy to
get backwards:

  * **Storage and comparison are UTC.** ``asxos/db.py`` pins the session
    ``timezone`` to UTC and explicitly warns against "improving" it to
    Australia/Sydney — the brief's freshness window compares a
    ``timestamp WITHOUT time zone`` against a ``timestamptz``, and Postgres
    resolves that through the session TimeZone. Sliding it would silently move
    the window ~10 hours off the pipeline it exists to cover.
  * **Presentation and business-day reckoning are Sydney.** That is what
    ``settings.asxos_tz`` is for, as ``db.py``'s own comment says.

This module is the second of those, and until now nothing implemented it:
``asxos_tz`` was defined in ``CoreSettings`` and read by exactly zero code
paths. Reading it here is deliberate — it retires that dead-config finding
rather than hard-coding a second copy of the zone name.

What this is not
----------------
``today()`` is a *wall-clock* answer. It is not a trading-day anchor: it does
not know about weekends, ASX holidays, or whether a session has settled. Code
that needs "the latest complete trading day" must derive that from the data
(``prices``), not from a clock. Most jobs here already accept an explicit
``--as-of`` for exactly that reason, and that argument still wins where it is
passed — this only changes what the *default* resolves to.
"""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from asxos.config import settings

__all__ = ["reporting_tz", "today"]


def reporting_tz() -> ZoneInfo:
    """The configured reporting timezone (``settings.asxos_tz``)."""
    return ZoneInfo(settings.asxos_tz)


def today() -> date:
    """Today's date in the reporting timezone.

    Use this instead of the stdlib wall-clock call anywhere a "today" is meant.
    ``tests/test_no_bare_date_today.py`` enforces that.
    """
    return datetime.now(reporting_tz()).date()
