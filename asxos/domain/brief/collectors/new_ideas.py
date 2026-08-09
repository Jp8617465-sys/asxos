"""
Section 6: New ideas — M-Brief-V2-Sections.

Research-stage theses (status='research'). Suppressed when the market regime
is risk_off_orderly or risk_off_disorderly — capital preservation takes priority
over new idea evaluation during market stress (V2 spec §4.4).

Two 2026-08-09 fixes from the finance red-team register (PR #78, D6 conformance
half — governor-approved):

- **Fail CLOSED on an unknown regime** (register #17). Previously a missing
  `market_context_current` row made `effective_regime` None, which is not in
  `_RISK_OFF_REGIMES`, so the section rendered normally — a broken regime
  ingest silently UN-suppressed ideas, inverting the capital-preservation
  intent and the fail-loud doctrine (CLAUDE.md #10). Unknown regime now
  suppresses, with the cause named.
- **Counted suppression line** (register #27, spec :359). The suppressed
  branch previously returned before ever counting, so the spec's required
  "N idea(s) identified but suppressed…" line was unproducible. The count is
  now taken (same governance filter as the render path — approved research
  theses only, so unapproved drafts never leak into the count) and carried in
  the section's error/message field. Deliberately NOT rendered as items:
  status stays `suppressed`, items stay empty, so section-health visibility
  and the snapshot's red/yellow/green exclusion semantics are unchanged and
  no symbol or thesis text reaches a risk-off brief.

SeverityItem levels:
  - green: research thesis (informational)
Section status:
  - suppressed: risk-off regime active, or regime unavailable (fail-closed)
  - no_data:    no research theses
"""
from __future__ import annotations

import time
from datetime import date, timedelta

from asxos.db import acquire
from asxos.domain.brief.types import SectionResult, SectionStatus, SeverityItem, SeverityLevel

_SECTION = "new_ideas"
_RISK_OFF_REGIMES = {"risk_off_orderly", "risk_off_disorderly"}

# Calendar-day window for the fallback regime lookup: the brief's calendar as_of
# is usually ahead of the newest market_context row (anchored to the latest
# complete trading day), so an exact `as_of = $1` match fails on most mornings.
# 4 calendar days covers a weekend plus one holiday — a deliberate calendar
# approximation of the spec's 2-trading-day freshness gate (spec :370). Older
# than this window counts as "regime unavailable" and fails closed.
_REGIME_LOOKBACK_DAYS = 4

_COUNT_SQL = """
    SELECT count(*) AS n
    FROM theses
    WHERE status = 'research'
      AND governance_status = 'approved'
"""


def _suppression_message(count: int, reason: str) -> str:
    """The spec-:359 counted line, prefixed with the machine-readable reason."""
    noun = "idea" if count == 1 else "ideas"
    return (
        f"{reason} — {count} {noun} identified but suppressed by current market "
        "regime. Re-evaluate when the regime classifier returns to neutral or risk-on."
    )


async def collect_new_ideas(as_of: date, regime_label: str | None = None) -> SectionResult:
    """Collect research theses. Suppressed under risk-off or UNKNOWN regimes.

    regime_label is passed from the market_context collector result to avoid
    a second DB round-trip. If None, the latest regime within
    _REGIME_LOOKBACK_DAYS is fetched; none found ⇒ fail closed (suppressed).
    """
    start_ms = int(time.monotonic() * 1000)

    effective_regime = regime_label

    if effective_regime is None:
        async with acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT regime_label FROM market_context_current
                WHERE as_of <= $1 AND as_of >= $2
                ORDER BY as_of DESC
                LIMIT 1
                """,
                as_of,
                as_of - timedelta(days=_REGIME_LOOKBACK_DAYS),
            )
            effective_regime = row["regime_label"] if row else None

    if effective_regime is None or effective_regime in _RISK_OFF_REGIMES:
        # Suppressed either way; the reason distinguishes a deliberate risk-off
        # posture from a broken/absent regime feed (fail-closed).
        async with acquire() as conn:
            count_row = await conn.fetchrow(_COUNT_SQL)
        count = int(count_row["n"]) if count_row else 0
        if effective_regime is None:
            reason = (
                f"regime unavailable (no market_context row within "
                f"{_REGIME_LOOKBACK_DAYS}d of {as_of.isoformat()}) — failing closed"
            )
        else:
            reason = f"regime={effective_regime}"
        elapsed_ms = int(time.monotonic() * 1000) - start_ms
        return SectionResult(
            name=_SECTION, status=SectionStatus.suppressed,
            items=(), elapsed_ms=elapsed_ms,
            error=_suppression_message(count, reason),
        )

    async with acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT symbol, opened_at, thesis_text
            FROM theses
            WHERE status = 'research'
              AND governance_status = 'approved'
            ORDER BY opened_at DESC
            """
        )

    elapsed_ms = int(time.monotonic() * 1000) - start_ms

    if not rows:
        return SectionResult(
            name=_SECTION, status=SectionStatus.no_data,
            items=(), elapsed_ms=elapsed_ms,
            error="no research theses",
        )

    items: list[SeverityItem] = []
    for row in rows:
        days_in_research = (as_of - row["opened_at"].date()).days
        thesis_snippet = ""
        if row["thesis_text"]:
            thesis_snippet = f"\n{row['thesis_text'][:100]}{'…' if len(row['thesis_text']) > 100 else ''}"
        msg = (
            f"{row['symbol']} | Research | {days_in_research}d"
            f"{thesis_snippet}"
        )
        items.append(SeverityItem(
            level=SeverityLevel.green, message=msg, section=_SECTION
        ))

    return SectionResult(
        name=_SECTION, status=SectionStatus.ok,
        items=tuple(items), elapsed_ms=elapsed_ms,
    )
