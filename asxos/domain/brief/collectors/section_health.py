"""
Footer: Section health summary — M-Brief-Skeleton.

Summarises which sections completed ok, were degraded, timed out, or failed.
Called after all other collectors complete with their actual results.
"""
from __future__ import annotations

import time

from asxos.domain.brief.types import SectionResult, SectionStatus, SeverityItem, SeverityLevel

_SECTION = "section_health"


def collect_section_health(sections: list[SectionResult]) -> SectionResult:
    """Build the footer section from the completed section results.

    This is synchronous (pure) — the results are already in memory.
    """
    start_ms = int(time.monotonic() * 1000)
    items: list[SeverityItem] = []

    for s in sections:
        if s.status == SectionStatus.ok:
            continue  # green sections get no footer item
        elif s.status == SectionStatus.no_data:
            items.append(SeverityItem(
                level=SeverityLevel.green,
                message=f"[{s.name}: no data]",
                section=_SECTION,
            ))
        elif s.status == SectionStatus.suppressed:
            items.append(SeverityItem(
                level=SeverityLevel.green,
                message=f"[{s.name}: suppressed]",
                section=_SECTION,
            ))
        elif s.status == SectionStatus.degraded:
            detail = f" ({s.error})" if s.error else ""
            items.append(SeverityItem(
                level=SeverityLevel.yellow,
                message=f"[{s.name}: degraded{detail}]",
                section=_SECTION,
            ))
        elif s.status == SectionStatus.timeout:
            items.append(SeverityItem(
                level=SeverityLevel.yellow,
                message=f"[{s.name}: timed out after {s.elapsed_ms // 1000}s]",
                section=_SECTION,
            ))
        elif s.status == SectionStatus.failed:
            detail = f" ({s.error})" if s.error else ""
            items.append(SeverityItem(
                level=SeverityLevel.red,
                message=f"[{s.name}: failed{detail}]",
                section=_SECTION,
            ))

    elapsed_ms = int(time.monotonic() * 1000) - start_ms
    return SectionResult(
        name=_SECTION,
        status=SectionStatus.ok,
        items=tuple(items),
        elapsed_ms=elapsed_ms,
    )
