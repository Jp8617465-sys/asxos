"""W1-1 asxos_pit_db path — hashed-fixture regression stays in existing files."""
from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from asxos.domain.results_review.adapter import ResultsReviewAdapterError, adapt_hashed_fixture
from asxos.domain.results_review.contracts import AcquisitionPath, hash_document_payload
from asxos.domain.results_review.fixtures import (
    historical_document_payload,
    historical_results_case,
)
from asxos.domain.results_review.pit_db import (
    G2_MISSING,
    SQL_INCOME,
    SQL_PIT,
    SQL_SECURITY,
    SQL_SESSIONS,
    adapt_pit_snapshot,
    assert_sql_admissible,
    build_pit_case,
    fetch_pit_snapshot,
    validate_symbol,
)
from asxos.domain.results_review.presentation import present_adapted


def _cutoff() -> datetime:
    return datetime(2025, 8, 21, 23, 59, 59, tzinfo=UTC)


def _sessions(start: date, n: int = 21) -> list[str]:
    days: list[str] = []
    cursor = start
    while len(days) < n:
        cursor += timedelta(days=1)
        if cursor.weekday() < 5:
            days.append(cursor.isoformat())
    return days


def _snapshot(*, symbol: str = "BHP.AU") -> dict[str, object]:
    return {
        "acquisition": "asxos_pit_db",
        "security_id": symbol,
        "period_end": "2024-06-30",
        "period_type": "yearly",
        "cutoff": "2025-08-21",
        "income_current": {
            "symbol": symbol,
            "period_end": "2024-06-30",
            "period_type": "yearly",
            "statement_type": "income",
            "filing_date": "2024-08-20",
            "report_date": "2024-08-15",
            "currency": "AUD",
            "total_revenue": "55000000000",
            "net_income": "7900000000",
        },
        "income_prior": {
            "symbol": symbol,
            "period_end": "2023-06-30",
            "period_type": "yearly",
            "statement_type": "income",
            "filing_date": "2023-08-18",
            "report_date": "2023-08-14",
            "currency": "AUD",
            "total_revenue": "50000000000",
            "net_income": "7000000000",
        },
        "pit_current": {
            "symbol": symbol,
            "as_of": "2024-06-30",
            "knowledge_date": "2024-08-20",
            "revenue_ttm": "55000000000",
            "net_income_ttm": "7900000000",
            "currency": "AUD",
        },
        "sessions": _sessions(date(2025, 8, 21)),
    }


def test_acquisition_path_admits_pit_and_fixture() -> None:
    assert set(AcquisitionPath.__args__) == {"hashed_fixture", "asxos_pit_db"}


def test_fixture_path_still_never_real() -> None:
    adapted = adapt_hashed_fixture(
        historical_document_payload(), historical_results_case()
    )
    assert adapted.case.document.acquisition == "hashed_fixture"
    assert adapted.case.document.data_mode == "synthetic"


def test_pit_case_abstains_with_named_g2_g3_g5() -> None:
    payload, case = build_pit_case(_snapshot(), cutoff=_cutoff())
    assert case.document.acquisition == "asxos_pit_db"
    assert case.document.data_mode == "real"
    assert case.review.outcome == "abstain"
    assert G2_MISSING in case.review.missing_evidence
    assert any("G3" in item for item in case.review.missing_evidence)
    assert any("G5" in item for item in case.review.missing_evidence)
    assert case.review.tax_assessment_reference.readiness == "unknown"
    assert case.review.model_independence is True
    assert hash_document_payload(payload) == case.document.document_sha256
    for delta in case.review.metric_deltas:
        assert delta.source_class == "asxos_pit_record"
        assert delta.basis == "statutory"


def test_relabelled_fixture_payload_is_refused() -> None:
    fixture = dict(historical_document_payload())
    fixture["acquisition"] = "asxos_pit_db"
    with pytest.raises(ResultsReviewAdapterError):
        build_pit_case(fixture, cutoff=_cutoff())


def test_hashed_fixture_cannot_be_real() -> None:
    case = historical_results_case()
    dumped = case.document.model_dump()
    dumped["data_mode"] = "real"
    dumped.pop("content_hash", None)
    with pytest.raises(Exception, match="hashed fixture"):
        type(case.document).model_validate(dumped)


def test_adapt_and_present_pit_is_deterministic() -> None:
    snap = _snapshot()
    first = adapt_pit_snapshot(snap, cutoff=_cutoff())
    second = adapt_pit_snapshot(snap, cutoff=_cutoff())
    assert first.artifact_sha256 == second.artifact_sha256
    presented = present_adapted(first, evaluated_at=_cutoff())
    assert presented.acquisition == "asxos_pit_db"
    assert presented.data_mode == "real"
    assert presented.outcome == "abstain"
    assert "STRONG BUY" not in presented.presentation_markdown


def test_sql_constants_are_allowlisted() -> None:
    for sql in (SQL_SECURITY, SQL_INCOME, SQL_PIT, SQL_SESSIONS):
        assert_sql_admissible(sql)
        assert "$1" in sql
        assert "signals" not in sql.lower()
        assert "line_items" not in sql.lower()


def test_forbidden_sql_hard_fails() -> None:
    with pytest.raises(ResultsReviewAdapterError, match="forbidden"):
        assert_sql_admissible("SELECT prob_up FROM signals WHERE symbol = $1")


def test_symbol_validation() -> None:
    assert validate_symbol("BHP.AU") == "BHP.AU"
    with pytest.raises(ResultsReviewAdapterError):
        validate_symbol("bhp")
    with pytest.raises(ResultsReviewAdapterError):
        validate_symbol("signals.AU")


def test_blank_currency_refused() -> None:
    snap = _snapshot()
    assert isinstance(snap["income_current"], dict)
    snap["income_current"]["currency"] = ""
    snap["income_prior"] = None
    with pytest.raises(ResultsReviewAdapterError, match="currency"):
        build_pit_case(snap, cutoff=_cutoff())


def test_future_knowledge_date_does_not_slide_year() -> None:
    """Refuse the current year when conservative known_at is still after cutoff.

    ``derive_knowledge_date`` drops future disclosure dates and falls back to
    ``period_end + 75d``. For FY2025 that fallback (2025-09-13) is after the
    2025-08-21 cutoff, so the current row is inadmissible. The prior year is
    not promoted.
    """
    snap = _snapshot()
    assert isinstance(snap["income_current"], dict)
    snap["period_end"] = "2025-06-30"
    snap["income_current"]["period_end"] = "2025-06-30"
    snap["income_current"]["report_date"] = "2026-09-13"
    snap["income_current"]["filing_date"] = "2026-09-13"
    with pytest.raises(ResultsReviewAdapterError, match="no admissible yearly income"):
        build_pit_case(snap, cutoff=_cutoff())


def test_missing_current_row_does_not_promote_prior() -> None:
    snap = _snapshot()
    snap["income_current"] = None
    with pytest.raises(ResultsReviewAdapterError, match="no admissible yearly income"):
        build_pit_case(snap, cutoff=_cutoff())


def test_future_disclosure_dates_keep_current_year_via_lag_fallback() -> None:
    """Future report/filing dates are dropped; lag fallback still names FY2024."""
    snap = _snapshot()
    assert isinstance(snap["income_current"], dict)
    snap["income_current"]["report_date"] = "2026-09-13"
    snap["income_current"]["filing_date"] = "2026-09-13"
    _payload, case = build_pit_case(snap, cutoff=_cutoff())
    assert case.document.period_end.isoformat() == "2024-06-30"
    assert case.review.outcome == "abstain"


def test_present_pit_does_not_reuse_fixture_never_real_gloss() -> None:
    presented = present_adapted(
        adapt_pit_snapshot(_snapshot(), cutoff=_cutoff()), evaluated_at=_cutoff()
    )
    assert "research-store PIT snapshot" in presented.presentation_markdown
    assert "a hashed fixture can never be `real`" not in presented.presentation_markdown
    assert presented.outcome == "abstain"


class _FakeConn:
    def __init__(self, responses: list[object]) -> None:
        self.responses = list(responses)
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    async def fetch(self, query: str, *args: object) -> list[dict[str, object]]:
        self.calls.append((query, args))
        item = self.responses.pop(0)
        return item  # type: ignore[return-value]

    async def fetchrow(self, query: str, *args: object) -> dict[str, object] | None:
        self.calls.append((query, args))
        item = self.responses.pop(0)
        return item  # type: ignore[return-value]


@pytest.mark.asyncio
async def test_fetch_pit_snapshot_uses_bound_parameters() -> None:
    sessions = [{"dt": date(2025, 8, 22) + timedelta(days=i)} for i in range(30)]
    conn = _FakeConn(
        [
            {"symbol": "BHP.AU"},
            {
                "symbol": "BHP.AU",
                "period_end": date(2024, 6, 30),
                "period_type": "yearly",
                "statement_type": "income",
                "filing_date": date(2024, 8, 20),
                "report_date": date(2024, 8, 15),
                "currency": "AUD",
                "total_revenue": Decimal("55000000000"),
                "net_income": Decimal("7900000000"),
            },
            None,
            None,
            sessions,
        ]
    )
    snap = await fetch_pit_snapshot(
        conn,
        symbol="BHP.AU",
        period_end=date(2024, 6, 30),
        cutoff=date(2025, 8, 21),
    )
    assert snap["acquisition"] == "asxos_pit_db"
    assert all("$1" in call[0] for call in conn.calls)
    assert all("signals" not in call[0].lower() for call in conn.calls)
    assert conn.calls[0][1][0] == "BHP.AU"
