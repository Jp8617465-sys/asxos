"""Live daily-brief section contract (Stage 0).

Four-state degradation for the *send path* in ``asxos.brief.compose``. This is
intentionally a separate type from the dark V2 ``SectionResult`` in
``asxos.domain.brief.types`` (``ok`` / ``degraded`` / ``suppressed`` / ``failed``).
Do not mix the vocabularies. See ``docs/product/daily-brief-v2.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any


class SectionStatus(StrEnum):
    """Closed four-state vocab. EMPTY ≠ MISSING."""

    FRESH = "FRESH"
    STALE = "STALE"
    MISSING = "MISSING"
    EMPTY = "EMPTY"


# Stable render order for the integrity line.
SECTION_ORDER: tuple[str, ...] = (
    "prices",
    "jobs",
    "discipline",
    "outcome",
    "regulatory",
    "news",
    "portfolio",
    "candidates",
)


@dataclass(frozen=True)
class SectionResult:
    """One brief section's payload plus lineage.

    ``error`` is required when ``status is MISSING`` (constructor-enforced).
    ``data`` is None on MISSING; otherwise the section payload.
    """

    name: str
    status: SectionStatus
    data: object | None = None
    computed_at: datetime | None = None
    source: str = ""
    error: str | None = None

    def __post_init__(self) -> None:
        if self.status is SectionStatus.MISSING and not self.error:
            raise ValueError(f"SectionResult {self.name!r} is MISSING without error")


def news_to_status(news_status: str, *, error: str | None = None) -> SectionStatus:
    """Map the existing four NewsStatus values (+ collector failure) onto SectionStatus."""
    if error:
        return SectionStatus.MISSING
    raw = str(news_status)
    if raw == "ok":
        return SectionStatus.FRESH
    if raw == "unverified":
        return SectionStatus.STALE
    if raw in {"quiet", "disabled"}:
        return SectionStatus.EMPTY
    return SectionStatus.MISSING


def assemble_sections(
    *,
    latest_price_date: Any,
    prices_stale: bool,
    job_failures: list[Any],
    discipline_findings: list[Any],
    outcome_section: Any,
    outcome_error: str | None,
    regulatory_hits: list[Any],
    news_items: list[Any],
    news_status: str,
    news_error: str | None,
    portfolio_section: Any,
    computed_at: datetime,
    data_as_of: Any = None,
    candidates: list[Any] | None = None,
    candidates_error: str | None = None,
) -> dict[str, SectionResult]:
    """Pure mapper: live collect() payloads → SectionResult dict.

    Sequential collect() calls this once at the end. Tests call it directly.
    """
    if latest_price_date is None:
        prices_status = SectionStatus.MISSING
        prices_error: str | None = "no complete price day"
    elif prices_stale:
        prices_status = SectionStatus.STALE
        prices_error = None
    else:
        prices_status = SectionStatus.FRESH
        prices_error = None

    section_failed = any(
        getattr(f, "check", None) in {"discipline_section", "cgt_discount_boundary"}
        and str(getattr(f, "level", "")) == "error"
        for f in discipline_findings
    )
    if section_failed:
        disc_status = SectionStatus.MISSING
        disc_error: str | None = next(
            (
                getattr(f, "message", None)
                for f in discipline_findings
                if getattr(f, "check", None) in {"discipline_section", "cgt_discount_boundary"}
            ),
            "discipline section could not run",
        )
    elif not discipline_findings:
        disc_status = SectionStatus.EMPTY
        disc_error = None
    else:
        disc_status = SectionStatus.FRESH
        disc_error = None

    if outcome_error:
        out_status = SectionStatus.MISSING
        out_error: str | None = outcome_error
    elif outcome_section is None:
        out_status = SectionStatus.EMPTY
        out_error = None
    else:
        out_status = SectionStatus.FRESH
        out_error = None

    news_status_enum = news_to_status(news_status, error=news_error)
    news_err = news_error
    if news_status_enum is SectionStatus.MISSING and not news_err:
        news_err = "news section could not run"

    # EMPTY is the ordinary weekly state: "nothing new cleared the gates". It is
    # a different claim from MISSING ("the queue could not be read"), and the
    # two must never collapse — see `_candidates` in compose.py.
    if candidates_error:
        cand_status = SectionStatus.MISSING
        cand_error: str | None = candidates_error
    elif not candidates:
        cand_status = SectionStatus.EMPTY
        cand_error = None
    else:
        cand_status = SectionStatus.FRESH
        cand_error = None

    jobs_status = SectionStatus.EMPTY if not job_failures else SectionStatus.FRESH
    reg_status = SectionStatus.EMPTY if not regulatory_hits else SectionStatus.FRESH
    port_status = SectionStatus.EMPTY if portfolio_section is None else SectionStatus.FRESH

    results = (
        SectionResult(
            name="prices",
            status=prices_status,
            data=(
                None
                if prices_status is SectionStatus.MISSING
                else {"latest_price_date": latest_price_date, "data_as_of": data_as_of}
            ),
            computed_at=computed_at,
            source="sql:prices.max(dt)+fn:latest_complete_trading_day",
            error=prices_error,
        ),
        SectionResult(
            name="jobs",
            status=jobs_status,
            data=list(job_failures),
            computed_at=computed_at,
            source="sql:job_runs",
        ),
        SectionResult(
            name="discipline",
            status=disc_status,
            data=None if disc_status is SectionStatus.MISSING else list(discipline_findings),
            computed_at=computed_at,
            source="fn:evaluate_discipline+fn:days_to_eligibility",
            error=disc_error,
        ),
        SectionResult(
            name="outcome",
            status=out_status,
            data=None if out_status is SectionStatus.MISSING else outcome_section,
            computed_at=computed_at,
            source="fn:build_outcome_section",
            error=out_error,
        ),
        SectionResult(
            name="regulatory",
            status=reg_status,
            data=list(regulatory_hits),
            computed_at=computed_at,
            source="sql:regulatory_events",
        ),
        SectionResult(
            name="news",
            status=news_status_enum,
            data=None if news_status_enum is SectionStatus.MISSING else list(news_items),
            computed_at=computed_at,
            source="sql:holding_news" if news_error is None else "fn:_news_section",
            error=news_err,
        ),
        SectionResult(
            name="portfolio",
            status=port_status,
            data=portfolio_section,
            computed_at=computed_at,
            source="sql:portfolio_runs+gate:ASXOS_PORTFOLIO_BRIEF_ENABLED",
        ),
        SectionResult(
            name="candidates",
            status=cand_status,
            data=None if cand_status is SectionStatus.MISSING else list(candidates or []),
            computed_at=computed_at,
            source="sql:theses[pending_review]+valuation_runs",
            error=cand_error,
        ),
    )
    return {s.name: s for s in results}
