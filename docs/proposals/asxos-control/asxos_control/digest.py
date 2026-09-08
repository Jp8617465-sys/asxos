"""Daily digest contract. 07:00 AEST is 21:00 UTC year-round in Brisbane."""

from __future__ import annotations

from datetime import date

# Australia/Brisbane is UTC+10 with no daylight saving.
DIGEST_CRON_UTC = "0 21 * * *"
DIGEST_LOCAL = "07:00 AEST"


def digest_template(day: date, autonomy: str) -> str:
    state = autonomy if autonomy in {"STANDING", "ATTENDED"} else "ATTENDED"
    return (
        f"## {day.isoformat()}   AUTONOMY: {state}\n"
        "Merged\n"
        "Awaiting you\n"
        "AC freezing\n"
        "Assumptions\n"
        "Risks\n"
        "Breakers\n"
    )
