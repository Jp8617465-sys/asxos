"""Read-only PIT acquisition path for results-review — W1-1 (2026-08-22).

Widens ``AcquisitionPath`` with ``asxos_pit_db``: a hashed snapshot of SELECT
rows from the research store. This is **not** an ASX announcement feed (G2
stays closed). Honest first outcome is ``abstain`` with named
``missing_evidence``.

Import-isolation: this module must not import ``asxos.db`` or ``asxos.config``.
The caller injects a connection. No persistence. Decimal-only. No tax import.
"""
from __future__ import annotations

import hashlib
import hmac
import re
from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Final, Protocol
from zoneinfo import ZoneInfo

from asxos.domain.decision_engine.types import (
    EvidenceItem,
    EvidencePacket,
    TradingSessionCalendar,
    default_packet_expiry,
)
from asxos.domain.results_review.adapter import (
    AdaptedResultsReview,
    ResultsReviewAdapterError,
    adapt_hashed_fixture,
    normalize_scale,
)
from asxos.domain.results_review.contracts import (
    RESULTS_REVIEW_SCHEMA_VERSION,
    SECURITY_ID_BINDING,
    TRADING_CALENDAR_ID_PREFIX,
    CitedStatement,
    FrozenInputTuple,
    MetricDelta,
    ResultsReviewArtifact,
    ResultsReviewCase,
    SourceDocumentRecord,
    derive_statement_known_at,
    frozen_delta_pct,
    hash_document_payload,
    unresolved_tax_assessment_reference,
)

_SYMBOL_RE: Final = re.compile(r"^[A-Z0-9]{1,10}\.[A-Z]{1,10}$")
_FORBIDDEN: Final[tuple[str, ...]] = (
    "signals",
    "signal_outcomes",
    "model_versions",
    "shap_factors",
    "prob_up",
    "signal_label",
    "model_a",
    "holding_lots",
    "theses",
    "thesis_",
    "screening_rules",
    "screening_runs",
    "line_items",
    "job_runs",
    "tax_",
)
_ADMISSIBLE_TABLES: Final[frozenset[str]] = frozenset(
    {
        "rs_security_master",
        "rs_financial_statements",
        "rs_fundamentals_pit",
        "prices",
    }
)
_SYDNEY: Final = ZoneInfo("Australia/Sydney")
_REQUIRED_SESSIONS: Final[int] = 21

SQL_SECURITY: Final[str] = (
    "SELECT symbol FROM rs_security_master WHERE symbol = $1"
)
SQL_INCOME: Final[str] = (
    "SELECT symbol, period_end, period_type, statement_type, filing_date, "
    "report_date, currency, total_revenue, net_income "
    "FROM rs_financial_statements "
    "WHERE symbol = $1 AND period_end = $2 AND period_type = $3 "
    "AND statement_type = 'income'"
)
SQL_PIT: Final[str] = (
    "SELECT symbol, as_of, knowledge_date, revenue_ttm, net_income_ttm, "
    "currency "
    "FROM rs_fundamentals_pit "
    "WHERE symbol = $1 AND as_of = $2 AND knowledge_date <= $3 "
    "ORDER BY knowledge_date DESC LIMIT 1"
)
SQL_SESSIONS: Final[str] = (
    "SELECT DISTINCT dt FROM prices "
    "WHERE symbol = $1 AND dt > $2 "
    "ORDER BY dt ASC LIMIT 40"
)

G2_MISSING: Final[str] = (
    "ASX results announcement (asx_announcement) — no acquisition path exists "
    "(G2: asx_announcements dropped in migration 0030)"
)
G3_MISSING: Final[str] = (
    "statutory/underlying bridge (G3) — rs_financial_statements carries a "
    "single normalised set, not a statutory/underlying pair"
)
G5_MISSING: Final[str] = (
    "guidance change (G5) — no guidance store exists in this repo"
)


class FetchConn(Protocol):
    async def fetch(
        self, query: str, *args: object
    ) -> Sequence[Mapping[str, object]]: ...

    async def fetchrow(
        self, query: str, *args: object
    ) -> Mapping[str, object] | None: ...


def validate_symbol(symbol: str) -> str:
    if not _SYMBOL_RE.fullmatch(symbol):
        raise ResultsReviewAdapterError(
            f"symbol {symbol!r} is not a vendor-namespaced security_id "
            f"({SECURITY_ID_BINDING})"
        )
    lowered = symbol.lower()
    for token in _FORBIDDEN:
        if token in lowered:
            raise ResultsReviewAdapterError(
                f"symbol {symbol!r} contains forbidden identifier {token!r}"
            )
    return symbol


def assert_sql_admissible(sql: str) -> None:
    """Hard-fail if a query names a table/column outside the allowlist story."""
    compact = sql.lower()
    for token in _FORBIDDEN:
        if token in compact:
            raise ResultsReviewAdapterError(
                f"SQL names forbidden identifier {token!r}"
            )
    named = {name for name in _ADMISSIBLE_TABLES if name in compact}
    if not named:
        raise ResultsReviewAdapterError("SQL names no admissible table")


def _dec(value: object) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, float):
        raise ResultsReviewAdapterError("float is forbidden on the PIT path")
    text = str(value)
    if text.strip() == "":
        return None
    return Decimal(text)


def _dec_str(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return format(value, "f")


def _as_date(value: object) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def _prior_period_end(period_end: date) -> date:
    """The same calendar date one year earlier.

    One helper rather than the expression inline, because BOTH
    ``fetch_pit_snapshot`` (which SELECTs the prior row) and ``build_pit_case``
    (which names it in ``missing_evidence`` and on the prior EvidenceItem)
    derive it. Two copies of a date computation that must agree is how a
    snapshot ends up fetched for one year and labelled with another.

    A Feb-29 ``period_end`` has no same-date prior year, and the bare
    ``date(...)`` call raises ``ValueError`` — an exception type nothing on this
    path catches, so it would escape as a traceback rather than as this module's
    own refusal. Clamping to Feb 28 (or Mar 1) is not obviously right and no
    caller could tell which was chosen, so it refuses instead — the same posture
    as ``build_pit_case``'s "refusing to slide to an older year". Rare against
    ASX fiscal calendars; the point is the failure mode, not the frequency.
    """
    try:
        return date(period_end.year - 1, period_end.month, period_end.day)
    except ValueError as exc:
        raise ResultsReviewAdapterError(
            f"period_end {period_end.isoformat()} has no same-date prior year "
            "(leap day); refusing to guess Feb 28 vs Mar 1"
        ) from exc


def _session_close_utc(day: date) -> datetime:
    return datetime(day.year, day.month, day.day, 16, 0, tzinfo=_SYDNEY).astimezone(UTC)


def _scale_pair(
    current: Decimal, prior: Decimal | None
) -> tuple[Decimal, Decimal | None, str]:
    peak = abs(current)
    if prior is not None:
        peak = max(peak, abs(prior))
    target = "ones"
    if peak >= Decimal("1000000000"):
        target = "billions"
    elif peak >= Decimal("1000000"):
        target = "millions"
    elif peak >= Decimal("1000"):
        target = "thousands"
    scaled_current = normalize_scale(current, "ones", target)  # type: ignore[arg-type]
    scaled_prior = (
        None if prior is None else normalize_scale(prior, "ones", target)  # type: ignore[arg-type]
    )
    return scaled_current, scaled_prior, target


async def fetch_pit_snapshot(
    conn: FetchConn,
    *,
    symbol: str,
    period_end: date,
    cutoff: date,
    period_type: str = "yearly",
) -> dict[str, object]:
    """SELECT-only snapshot. Identifiers are constants; values are bound."""
    symbol = validate_symbol(symbol)
    if period_type != "yearly":
        raise ResultsReviewAdapterError(
            "asxos_pit_db admits yearly statements only in W1-1 "
            "(map_statement_period_type hard-fails half_yearly)"
        )
    for sql in (SQL_SECURITY, SQL_INCOME, SQL_PIT, SQL_SESSIONS):
        assert_sql_admissible(sql)

    master = await conn.fetchrow(SQL_SECURITY, symbol)
    if master is None:
        raise ResultsReviewAdapterError(
            f"{symbol} is absent from rs_security_master"
        )

    current = await conn.fetchrow(SQL_INCOME, symbol, period_end, period_type)
    prior_end = _prior_period_end(period_end)
    prior = await conn.fetchrow(SQL_INCOME, symbol, prior_end, period_type)
    pit = await conn.fetchrow(SQL_PIT, symbol, period_end, cutoff)
    session_rows = await conn.fetch(SQL_SESSIONS, symbol, cutoff)

    def _row(mapping: Mapping[str, object] | None) -> dict[str, object] | None:
        if mapping is None:
            return None
        out: dict[str, object] = {}
        for key, raw in mapping.items():
            # SUBSTRING, matching assert_sql_admissible's test against the same
            # tuple -- not `key in _FORBIDDEN`, which was exact tuple membership.
            # _FORBIDDEN carries prefix entries ("tax_", "thesis_") that only
            # mean anything as substrings, so under exact matching those two
            # were dead here while live in the sibling check: `tax_rate` passed
            # this gate and would have been refused by the other. Two tests of
            # one list must not disagree about what the list means.
            #
            # `key == "line_items"` is gone with it -- "line_items" is already a
            # _FORBIDDEN entry, and that special case only existed to work
            # around this same asymmetry.
            #
            # Verified against every column the four SQL constants select
            # (symbol, period_end, period_type, statement_type, filing_date,
            # report_date, currency, total_revenue, net_income, as_of,
            # knowledge_date, revenue_ttm, net_income_ttm): none contains a
            # _FORBIDDEN token, so nothing admissible starts failing. Re-check
            # that if a SELECT list ever widens.
            lowered = key.lower()
            if any(token in lowered for token in _FORBIDDEN):
                raise ResultsReviewAdapterError(f"forbidden column {key!r}")
            if isinstance(raw, float):
                raise ResultsReviewAdapterError(f"float in column {key!r}")
            if isinstance(raw, Decimal):
                out[key] = format(raw, "f")
            elif isinstance(raw, date) and not isinstance(raw, datetime):
                out[key] = raw.isoformat()
            elif raw is None:
                out[key] = None
            else:
                out[key] = str(raw) if not isinstance(raw, str) else raw
        return out

    sessions = [_as_date(row["dt"]).isoformat() for row in session_rows]
    snapshot: dict[str, object] = {
        "acquisition": "asxos_pit_db",
        "security_id": symbol,
        "period_end": period_end.isoformat(),
        "period_type": period_type,
        "cutoff": cutoff.isoformat(),
        "income_current": _row(current),
        "income_prior": _row(prior),
        "pit_current": _row(pit),
        "sessions": sessions,
    }
    return snapshot


def _known_at_for_income(
    row: Mapping[str, object] | None, *, as_of: date, period_end: date
) -> datetime | None:
    if row is None:
        return None
    report = row.get("report_date")
    filing = row.get("filing_date")
    report_d = None if report in (None, "") else _as_date(report)
    filing_d = None if filing in (None, "") else _as_date(filing)
    return derive_statement_known_at(period_end, report_d, filing_d, as_of)


def _currency(row: Mapping[str, object] | None) -> str | None:
    if row is None:
        return None
    raw = row.get("currency")
    if raw is None:
        return None
    text = str(raw).strip()
    if text == "":
        return None
    return text.upper()


def build_pit_case(
    snapshot: Mapping[str, object],
    *,
    cutoff: datetime,
) -> tuple[dict[str, object], ResultsReviewCase]:
    """Build a validated case from a JSON-native PIT snapshot. No DB."""
    if snapshot.get("acquisition") != "asxos_pit_db":
        raise ResultsReviewAdapterError(
            "PIT builder refuses any acquisition other than asxos_pit_db"
        )
    symbol = validate_symbol(str(snapshot["security_id"]))
    period_end = _as_date(snapshot["period_end"])
    as_of = cutoff.date()
    payload = dict(snapshot)
    digest = hash_document_payload(payload)

    current = snapshot.get("income_current")
    prior = snapshot.get("income_prior")
    if current is not None and not isinstance(current, Mapping):
        raise ResultsReviewAdapterError("income_current must be a mapping or null")
    if prior is not None and not isinstance(prior, Mapping):
        raise ResultsReviewAdapterError("income_prior must be a mapping or null")

    currency = _currency(current) or _currency(prior)
    if currency is None:
        raise ResultsReviewAdapterError(
            "reporting currency is blank or missing — refuse mixed/empty currency"
        )

    missing: list[str] = [G2_MISSING, G3_MISSING, G5_MISSING]
    current_known = _known_at_for_income(
        current if isinstance(current, Mapping) else None,
        as_of=as_of,
        period_end=period_end,
    )
    if current is None or current_known is None or current_known > cutoff:
        missing.append(
            f"yearly income statement for {period_end.isoformat()} with "
            f"knowledge_date <= {as_of.isoformat()}"
        )
        current = None
        current_known = None

    prior_end = _prior_period_end(period_end)
    prior_known = _known_at_for_income(
        prior if isinstance(prior, Mapping) else None,
        as_of=as_of,
        period_end=prior_end,
    )
    if prior is not None and (prior_known is None or prior_known > cutoff):
        missing.append(
            f"yearly income statement for {prior_end.isoformat()} with "
            f"knowledge_date <= {as_of.isoformat()}"
        )
        prior = None
        prior_known = None

    if current is None:
        raise ResultsReviewAdapterError(
            f"no admissible yearly income row for {symbol} period_end="
            f"{period_end.isoformat()} at cutoff {as_of.isoformat()}; "
            "refusing to slide to an older year"
        )

    session_iso = snapshot.get("sessions")
    if not isinstance(session_iso, list) or len(session_iso) < _REQUIRED_SESSIONS:
        raise ResultsReviewAdapterError(
            f"trading calendar needs {_REQUIRED_SESSIONS} observed prices.dt "
            f"sessions after {as_of.isoformat()} (G6); got "
            f"{0 if not isinstance(session_iso, list) else len(session_iso)}"
        )
    sessions = tuple(_session_close_utc(_as_date(item)) for item in session_iso)
    session_canon = ",".join(item.isoformat() for item in sessions)
    cal_hash = hashlib.sha256(session_canon.encode("ascii")).hexdigest()[:12]
    calendar = TradingSessionCalendar(
        calendar_id=TRADING_CALENDAR_ID_PREFIX,
        calendar_version=f"{sessions[-1].date().isoformat()}+{cal_hash}",
        sessions=sessions,
    )
    expires_at = default_packet_expiry(cutoff, "abstain", calendar)

    items: list[EvidenceItem] = []
    assert current_known is not None
    items.append(
        EvidenceItem(
            evidence_id="pit-income-current",
            evidence_type="fundamental_fact",
            title=f"{symbol} yearly income {period_end.isoformat()}",
            claim=(
                f"Research-store yearly income row for {symbol} period_end "
                f"{period_end.isoformat()} (source_class asxos_pit_record; "
                "not an ASX announcement)."
            ),
            source_uri=f"asxos://rs_financial_statements/{symbol}/{period_end.isoformat()}/yearly/income",
            observed_at=period_end,
            known_at=current_known,
            evidence_tier="verified",
            data_mode="real",
        )
    )
    if prior is not None and prior_known is not None:
        items.append(
            EvidenceItem(
                evidence_id="pit-income-prior",
                evidence_type="fundamental_fact",
                title=f"{symbol} yearly income {prior_end.isoformat()}",
                claim=(
                    f"Prior-year research-store income row for {symbol} "
                    f"{prior_end.isoformat()}."
                ),
                source_uri=f"asxos://rs_financial_statements/{symbol}/{prior_end.isoformat()}/yearly/income",
                observed_at=prior_end,
                known_at=prior_known,
                evidence_tier="verified",
                data_mode="real",
            )
        )

    packet_id = f"evp-pit-{symbol}-{period_end.isoformat()}"
    evidence = EvidencePacket(
        evidence_packet_id=packet_id,
        as_of=as_of,
        knowledge_cutoff=cutoff,
        expires_at=expires_at,
        data_mode="real",
        created_at=cutoff,
        items=tuple(items),
    )

    display, exchange = [*symbol.split(".", 1), "ASX"][:2]
    release_at = current_known
    document = SourceDocumentRecord(
        document_id=f"pit-{symbol}-{period_end.isoformat()}",
        acquisition="asxos_pit_db",
        data_mode="real",
        security_id=symbol,
        symbol=display,
        exchange=exchange,
        document_kind="full_year_results",
        period_end=period_end,
        period_type="yearly",
        currency=currency,
        units_scale="ones",
        release_at=release_at,
        document_sha256=digest,
        transcription_note=(
            "Hashed PIT snapshot from rs_financial_statements / "
            "rs_fundamentals_pit / prices at the stated cutoff. Not issuer "
            "text. G2 announcement, G3 statutory/underlying bridge, and G5 "
            "guidance are absent and named in missing_evidence."
        ),
    )

    deltas: list[MetricDelta] = []
    for metric, key in (("Revenue", "total_revenue"), ("NPAT", "net_income")):
        cur_val = _dec(current.get(key) if isinstance(current, Mapping) else None)
        if cur_val is None:
            missing.append(f"{metric} on the current yearly income row")
            continue
        prior_val = (
            _dec(prior.get(key)) if isinstance(prior, Mapping) else None
        )
        scaled_cur, scaled_prior, scale = _scale_pair(cur_val, prior_val)
        evidence_ids: tuple[str, ...] = ("pit-income-current",)
        if scaled_prior is not None:
            evidence_ids = ("pit-income-current", "pit-income-prior")
        delta_pct = (
            None
            if scaled_prior is None or scaled_prior == 0
            else frozen_delta_pct(scaled_cur, scaled_prior)
        )
        deltas.append(
            MetricDelta(
                metric=metric,
                basis="statutory",
                currency=currency,
                scale=scale,  # type: ignore[arg-type]
                current_value=scaled_cur,
                prior_value=scaled_prior,
                delta_pct=delta_pct,
                evidence_ids=evidence_ids,
                source_class="asxos_pit_record",
            )
        )

    frozen = FrozenInputTuple(
        document_id=document.document_id,
        document_sha256=digest,
        security_id=symbol,
        period_end=period_end,
        period_type="yearly",
        currency=currency,
        units_scale=document.units_scale,
        knowledge_cutoff=cutoff,
        evidence_packet_id=packet_id,
    )
    review = ResultsReviewArtifact(
        review_id=f"rrv-pit-{symbol}-{period_end.isoformat()}",
        schema_version=RESULTS_REVIEW_SCHEMA_VERSION,
        frozen_input=frozen,
        as_of=as_of,
        created_at=cutoff,
        data_mode="real",
        metric_deltas=tuple(deltas),
        statutory_underlying_bridges=(),
        guidance_changes=(),
        thesis_pillar_effects=(),
        catalysts=(),
        falsifiers=(
            CitedStatement(
                statement=(
                    "No ASX announcement was acquired; numeric claims rest only "
                    "on research-store PIT/statement rows (rank 4)."
                ),
                evidence_ids=("pit-income-current",),
            ),
        ),
        conflicts=(),
        missing_evidence=tuple(missing),
        outcome="abstain",
        tax_assessment_reference=unresolved_tax_assessment_reference(
            tax_assessment_id=f"taxref-pit-{symbol}-{period_end.isoformat()}",
            as_of=as_of,
            knowledge_cutoff=cutoff,
            created_at=cutoff,
        ),
        model_independence=True,
    )
    case = ResultsReviewCase(
        case_id=f"pit-{symbol}-{period_end.isoformat()}",
        label=f"PIT snapshot review {symbol} {period_end.isoformat()} (not Stage 4)",
        document=document,
        evidence=evidence,
        review=review,
    )
    return payload, case


def adapt_pit_snapshot(
    snapshot: Mapping[str, object],
    *,
    cutoff: datetime,
) -> AdaptedResultsReview:
    """Build, hash-seal, and revalidate a PIT case through the fixture adapter."""
    payload, case = build_pit_case(snapshot, cutoff=cutoff)
    if case.document.acquisition != "asxos_pit_db":
        raise ResultsReviewAdapterError("refusing a non-PIT acquisition")
    if case.document.data_mode != "real":
        raise ResultsReviewAdapterError("asxos_pit_db must carry data_mode='real'")
    digest = hash_document_payload(payload)
    if not hmac.compare_digest(digest, case.document.document_sha256):
        raise ResultsReviewAdapterError("PIT snapshot hash does not match the document record")
    # Reuse the frozen adapt path: payload hash + full case revalidation.
    return adapt_hashed_fixture(payload, case)
