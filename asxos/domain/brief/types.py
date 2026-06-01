"""V2 brief domain types — M-Brief-Skeleton."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum


class SectionStatus(StrEnum):
    ok = "ok"
    degraded = "degraded"
    suppressed = "suppressed"
    failed = "failed"
    timeout = "timeout"
    no_data = "no_data"


class SeverityLevel(StrEnum):
    red = "red"
    yellow = "yellow"
    green = "green"


@dataclass(frozen=True)
class SeverityItem:
    level: SeverityLevel
    message: str
    section: str


@dataclass(frozen=True)
class SectionResult:
    name: str
    status: SectionStatus
    items: tuple[SeverityItem, ...]
    elapsed_ms: int
    error: str | None = None


@dataclass(frozen=True)
class Snapshot:
    """Triage summary derived from all section results."""
    red_count: int
    yellow_count: int
    green_count: int
    one_thing: str        # highest-priority action item for today
    health_line: str      # affirmative or warning header
    time_estimate_min: int
    items: tuple[SeverityItem, ...]  # all items, sorted red → yellow → green


@dataclass(frozen=True)
class Brief:
    """Composed brief for one as_of date."""
    as_of: date
    sections: tuple[SectionResult, ...]
    snapshot: Snapshot
    rendered_html: str | None = None


@dataclass
class BriefRun:
    """Row persisted to brief_runs after composition."""
    brief_id: int
    as_of: date
    sections_run: dict = field(default_factory=dict)
    resend_message_id: str | None = None
