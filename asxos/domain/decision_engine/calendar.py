"""Forward trading-session calendar — Slice 1's honest-abstain real packet.

`asxos/domain/results_review/pit_db.py`'s `TradingSessionCalendar` is built
from `prices.dt` rows *observed after* a historical cutoff (G6,
`docs/product/results-review-contracts-2026-08-16.md` §8) — it can only see
sessions the market has already traded, so it cannot serve a live/current
`knowledge_cutoff` (there is no future `prices` data to select). That gap is
named and deferred in the same doc as
`p2_deferred_forward_trading_calendar_source`; this module is NOT that
resolution — it is a narrow, explicitly-scoped stand-in for Slice 1's single
real packet, which is forced into `abstain` before any calendar-derived
expiry could matter to an action.

**Not an ASX exchange calendar.** Sessions are naive Mon-Fri weekdays with
no public-holiday awareness — a weekday the market is actually closed for a
public holiday (e.g. Australia Day, Anzac Day) will be counted here as if
it traded.
`calendar_id` says so explicitly (`asx-forward-weekdays-not-exchange-
verified`) so nothing downstream can mistake this for a verified exchange
feed. **Do not reuse this calendar for any packet whose
`recommendation_state` is in `ACTION_STATES`** without first resolving
`p2_deferred_forward_trading_calendar_source` — an F3 expiry computed off a
miscounted holiday would silently shift an action packet's real deadline.

Each session closes at 16:00 `Australia/Sydney`, converted to UTC via
`zoneinfo` (AEST/AEDT-aware) — the same convention
`results-review-contracts-2026-08-16.md` §8 fixes for the historical
calendar. This module writes its own anchor helper rather than importing
`pit_db.py`'s private `_session_close_utc` — the two calendars are
independent sources (observed-past vs. synthesized-future) and should not
share a private implementation detail across module boundaries.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime, timedelta
from typing import Final
from zoneinfo import ZoneInfo

from asxos.domain.decision_engine.types import TradingSessionCalendar

#: Deliberately distinct from pit_db.py's `TRADING_CALENDAR_ID_PREFIX`
#: ("asx-observed-prices") — this source is unverified forward weekday
#: arithmetic, not an observed trading fact.
CALENDAR_ID: Final[str] = "asx-forward-weekdays-not-exchange-verified"

_SYDNEY: Final = ZoneInfo("Australia/Sydney")

#: F3's longest default horizon (NON_ACTION_STATES, types.py:107-108) is 21
#: trading sessions — build exactly that many, no more.
DEFAULT_SESSION_COUNT: Final[int] = 21


def _session_close_utc(day: date) -> datetime:
    """This module's own anchor helper — see module docstring for why it is
    not shared with `results_review/pit_db.py`'s private equivalent."""
    return datetime(day.year, day.month, day.day, 16, 0, tzinfo=_SYDNEY).astimezone(UTC)


def build_forward_weekday_calendar(
    knowledge_cutoff: datetime, *, session_count: int = DEFAULT_SESSION_COUNT
) -> TradingSessionCalendar:
    """Build `session_count` forward Mon-Fri sessions strictly after `knowledge_cutoff`.

    `calendar_version` follows the same convention `pit_db.py` uses for its
    historical calendar: the ISO date of the latest included session plus
    the first 12 hex characters of the SHA-256 digest over the canonical
    ISO-8601 session list (`",".join(session.isoformat() for session in
    sessions)`).

    The first candidate session is always `knowledge_cutoff`'s UTC date plus
    at least one calendar day, so every session this function returns is
    guaranteed later than `knowledge_cutoff` regardless of what time of day
    `knowledge_cutoff` falls on — required for
    `TradingSessionCalendar.resolve_expiry`'s "sessions after cutoff"
    contract (types.py:186-195).
    """
    if session_count <= 0:
        raise ValueError("session_count must be positive")
    cursor = knowledge_cutoff.astimezone(UTC).date()
    sessions: list[datetime] = []
    while len(sessions) < session_count:
        cursor += timedelta(days=1)
        if cursor.weekday() < 5:
            sessions.append(_session_close_utc(cursor))
    session_canon = ",".join(session.isoformat() for session in sessions)
    digest = hashlib.sha256(session_canon.encode("ascii")).hexdigest()[:12]
    return TradingSessionCalendar(
        calendar_id=CALENDAR_ID,
        calendar_version=f"{sessions[-1].date().isoformat()}+{digest}",
        sessions=tuple(sessions),
    )
