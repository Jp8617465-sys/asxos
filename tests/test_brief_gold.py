"""Stage 2 gold artefacts: fake conn, no live Postgres."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from asxos.brief.compose import NEWS_UNVERIFIED, BriefData, render_html
from asxos.brief.gold import decode_brief, encode_brief, hydrate, persist
from asxos.brief.section import SECTION_ORDER, SectionResult, SectionStatus, assemble_sections

AS_OF = date(2026, 5, 22)
FIXED = datetime(2026, 5, 22, 8, 0, tzinfo=UTC)


class UndefinedTableError(Exception):
    """asyncpg-shaped 42P01."""

    sqlstate = "42P01"

    def __str__(self) -> str:
        return 'relation "brief_section_gold" does not exist'


class FakeConn:
    """In-memory gold table. Keyed by (as_of, section_name)."""

    def __init__(self, *, missing_table: bool = False) -> None:
        self.store: dict[tuple[date, str], dict[str, Any]] = {}
        self.missing_table = missing_table
        self.now = datetime(2026, 5, 22, 7, 0, tzinfo=UTC)

    async def execute(self, query: str, *args: object) -> str:
        if self.missing_table:
            raise UndefinedTableError()
        as_of, name, status, computed_at, source, error, payload = args
        payload_obj: object
        if payload is None:
            payload_obj = None
        elif isinstance(payload, bytes | str):
            payload_obj = json.loads(payload)
        else:
            payload_obj = payload
        key = (as_of, name)  # type: ignore[arg-type]
        existing = self.store.get(key)
        created = existing["created_at"] if existing is not None else self.now
        self.store[key] = {
            "as_of": as_of,
            "section_name": name,
            "status": status,
            "computed_at": computed_at,
            "source": source,
            "error": error,
            "payload": payload_obj,
            "created_at": created,
        }
        return "INSERT"

    async def fetch(self, query: str, *args: object) -> list[dict[str, Any]]:
        if self.missing_table:
            raise UndefinedTableError()
        as_of = args[0]
        return [row for (row_as_of, _name), row in self.store.items() if row_as_of == as_of]


def _brief(**overrides: object) -> BriefData:
    defaults: dict[str, object] = {
        "as_of": AS_OF,
        "latest_price_date": AS_OF,
        "data_as_of": AS_OF,
        "holdings_count": 3,
        "regulatory_hits": [],
        "job_failures": [],
        "news_status": NEWS_UNVERIFIED,
    }
    defaults.update(overrides)
    if "sections" not in defaults:
        defaults["sections"] = assemble_sections(
            latest_price_date=defaults["latest_price_date"],  # type: ignore[arg-type]
            prices_stale=False,
            job_failures=defaults.get("job_failures", []),  # type: ignore[arg-type]
            discipline_findings=defaults.get("discipline_findings", []),  # type: ignore[arg-type]
            outcome_section=defaults.get("outcome_section"),
            outcome_error=defaults.get("outcome_error"),  # type: ignore[arg-type]
            regulatory_hits=defaults.get("regulatory_hits", []),  # type: ignore[arg-type]
            news_items=defaults.get("news_items", []),  # type: ignore[arg-type]
            news_status=str(defaults.get("news_status", NEWS_UNVERIFIED)),
            news_error=None,
            portfolio_section=defaults.get("portfolio_section"),
            computed_at=FIXED,
            data_as_of=defaults.get("data_as_of"),
        )
    return BriefData(**defaults)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_upsert_conflict_updates_payload_same_key() -> None:
    conn = FakeConn()
    first = _brief(holdings_count=3)
    await persist(conn, first)
    key = (AS_OF, "header")
    created = conn.store[key]["created_at"]
    payload1 = conn.store[key]["payload"]
    second = _brief(holdings_count=9)
    await persist(conn, second)
    assert {k[1] for k in conn.store} == {*SECTION_ORDER, "header", "deltas"}
    assert conn.store[key]["created_at"] is created
    assert conn.store[key]["payload"]["holdings_count"] == 9
    assert payload1["holdings_count"] == 3


@pytest.mark.asyncio
async def test_hydrate_undefined_table_all_missing_collect_not_called() -> None:
    conn = FakeConn(missing_table=True)
    with patch("asxos.brief.compose.collect", new=AsyncMock()) as collect:
        data = await hydrate(conn, AS_OF)
    collect.assert_not_awaited()
    assert isinstance(data, BriefData)
    assert data.news_status is NEWS_UNVERIFIED
    assert data.holdings_count == 0
    for name in SECTION_ORDER:
        section = data.sections[name]
        assert section.status is SectionStatus.MISSING
        assert section.error
        assert "brief_section_gold" in section.error
    html = render_html(data)
    assert "Integrity" in html
    assert "MISSING" in html


@pytest.mark.asyncio
async def test_absent_news_row_is_missing_not_empty() -> None:
    conn = FakeConn()
    await persist(conn, _brief())
    del conn.store[(AS_OF, "news")]
    data = await hydrate(conn, AS_OF)
    news = data.sections["news"]
    assert news.status is SectionStatus.MISSING
    assert news.status is not SectionStatus.EMPTY
    assert news.error == f"gold row absent: news as_of={AS_OF}"
    assert data.news_status is NEWS_UNVERIFIED


@pytest.mark.asyncio
async def test_stored_empty_stays_empty() -> None:
    conn = FakeConn()
    brief = _brief()
    sections = dict(brief.sections)
    sections["news"] = SectionResult(
        name="news",
        status=SectionStatus.EMPTY,
        data=[],
        computed_at=FIXED,
        source="gold.test",
        error=None,
    )
    await persist(conn, BriefData(**{**brief.__dict__, "sections": sections}))
    data = await hydrate(conn, AS_OF)
    assert data.sections["news"].status is SectionStatus.EMPTY
    assert data.sections["news"].status is not SectionStatus.MISSING


@pytest.mark.asyncio
async def test_stale_prices_core_untrusted() -> None:
    conn = FakeConn()
    brief = _brief()
    sections = dict(brief.sections)
    sections["prices"] = SectionResult(
        name="prices",
        status=SectionStatus.STALE,
        data={"latest_price_date": date(2026, 5, 10), "data_as_of": date(2026, 5, 10)},
        computed_at=FIXED,
        source="gold.test",
        error=None,
    )
    await persist(conn, BriefData(**{**brief.__dict__, "sections": sections}))
    data = await hydrate(conn, AS_OF)
    assert data.sections["prices"].status is SectionStatus.STALE
    assert data.core_untrusted is True


def test_encode_decode_roundtrip_render_includes_integrity_and_bluf() -> None:
    brief = _brief()
    rows = encode_brief(brief)
    mapped = [
        {
            "as_of": as_of,
            "section_name": name,
            "status": status,
            "computed_at": computed_at,
            "source": source,
            "error": error,
            "payload": payload,
        }
        for as_of, name, status, computed_at, source, error, payload in rows
    ]
    restored = decode_brief(AS_OF, mapped)
    html = render_html(restored)
    assert "Integrity" in html
    assert 'id="bluf"' in html
    assert restored.as_of == brief.as_of
    assert restored.holdings_count == brief.holdings_count
    assert restored.sections["prices"].status is SectionStatus.FRESH


def test_gold_and_materialiser_have_no_signals_or_gather() -> None:
    gold = Path("asxos/brief/gold.py").read_text(encoding="utf-8")
    job = Path("jobs/materialise_brief_sections.py").read_text(encoding="utf-8")
    for text, label in ((gold, "gold.py"), (job, "materialise_brief_sections.py")):
        assert "signals" not in text, label
        assert "asyncio.gather" not in text, label
