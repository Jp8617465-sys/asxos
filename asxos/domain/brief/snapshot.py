"""
Snapshot builder — M-Brief-Skeleton.

build_snapshot(sections) → Snapshot

Triage priority for one_thing:
  1. thesis overdue (red, section=active_theses)
  2. stop breach (red, section=active_theses, 'stop' in message)
  3. cap breach (red, section=allocation_health)
  4. regime warning (any severity, section=market_context)
  5. opportunity cost (yellow, section=opportunity_cost)
  6. new ideas (green, section=new_ideas)

Time estimate: 1 min all-green, 3 min yellow only, 8 min any red, capped 60.
"""
from __future__ import annotations

from asxos.domain.brief.types import (
    SectionResult,
    SectionStatus,
    SeverityItem,
    SeverityLevel,
    Snapshot,
)

# Triage priority weights — lower number = higher priority
_PRIORITY: dict[tuple[str, str], int] = {
    # (section, fragment in message) → priority
    ("active_theses", "overdue"): 1,
    ("active_theses", "stop"): 2,
    ("active_theses", "earnings"): 3,
    ("allocation_health", ""): 4,
    ("market_context", ""): 5,
    ("opportunity_cost", ""): 6,
    ("new_ideas", ""): 7,
}


def _triage_priority(item: SeverityItem) -> int:
    """Lower = more urgent."""
    for (section, fragment), priority in _PRIORITY.items():
        if item.section == section and (not fragment or fragment in item.message.lower()):
            return priority
    # Red items from unknown sections rank above yellows
    if item.level == SeverityLevel.red:
        return 50
    if item.level == SeverityLevel.yellow:
        return 100
    return 200


def build_snapshot(sections: list[SectionResult]) -> Snapshot:
    """Derive a triage snapshot from the list of completed section results."""
    all_items: list[SeverityItem] = []
    for section in sections:
        if section.status in (SectionStatus.ok, SectionStatus.degraded):
            all_items.extend(section.items)

    reds = [i for i in all_items if i.level == SeverityLevel.red]
    yellows = [i for i in all_items if i.level == SeverityLevel.yellow]
    greens = [i for i in all_items if i.level == SeverityLevel.green]

    # Sort: red first, then yellow, then green — within each tier by triage priority
    sorted_items = (
        sorted(reds, key=_triage_priority)
        + sorted(yellows, key=_triage_priority)
        + sorted(greens, key=_triage_priority)
    )

    # one_thing: highest-priority item, or affirmative message if none
    if sorted_items:
        one_thing = sorted_items[0].message
    else:
        one_thing = "No action required — all clear."

    # health_line
    if reds:
        health_line = f"Action required — {len(reds)} red item{'s' if len(reds) > 1 else ''}"
    elif yellows:
        health_line = f"Review recommended — {len(yellows)} yellow item{'s' if len(yellows) > 1 else ''}"
    else:
        health_line = "All systems green — no action required today."

    # time_estimate_min
    if reds:
        time_estimate_min = min(8 * len(reds), 60)
    elif yellows:
        time_estimate_min = min(3 * len(yellows), 30)
    else:
        time_estimate_min = 1

    return Snapshot(
        red_count=len(reds),
        yellow_count=len(yellows),
        green_count=len(greens),
        one_thing=one_thing,
        health_line=health_line,
        time_estimate_min=time_estimate_min,
        items=tuple(sorted_items),
    )
