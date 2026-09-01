"""Stage 2 wiring: GHA step order and materialiser fail-loud."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from asxos.brief.compose import NEWS_UNVERIFIED, BriefData


class UndefinedTableError(Exception):
    sqlstate = "42P01"


class FakeJobMonitor:
    def __init__(self, *a, **kw):
        self.rows_written = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


class _AcquireCM:
    def __init__(self, conn: object) -> None:
        self.conn = conn

    async def __aenter__(self) -> object:
        return self.conn

    async def __aexit__(self, *exc: object) -> bool:
        return False


def test_gha_materialise_sits_after_sentiment_before_compose() -> None:
    text = Path(".github/workflows/daily-brief.yml").read_text(encoding="utf-8")
    sentiment = text.index("- name: Ingest sentiment")
    materialise = text.index("- name: Materialise brief sections")
    compose = text.index("- name: Compose and send brief")
    assert sentiment < materialise < compose
    assert "python jobs/materialise_brief_sections.py" in text


@pytest.mark.asyncio
async def test_materialise_reraises_undefined_table() -> None:
    data = BriefData(as_of=date(2026, 5, 22), holdings_count=0, news_status=NEWS_UNVERIFIED)

    def acquire() -> _AcquireCM:
        return _AcquireCM(AsyncMock())

    with (
        patch("jobs.materialise_brief_sections.init_pool", new=AsyncMock()),
        patch("jobs.materialise_brief_sections.close_pool", new=AsyncMock()),
        patch("jobs.materialise_brief_sections.JobMonitor", new=FakeJobMonitor),
        patch("jobs.materialise_brief_sections.acquire", new=acquire),
        patch("jobs.materialise_brief_sections.collect", new=AsyncMock(return_value=data)),
        patch(
            "jobs.materialise_brief_sections.persist",
            new=AsyncMock(side_effect=UndefinedTableError("missing gold table")),
        ),
        patch.dict("os.environ", {"ASXOS_PERSONAL_USE": "1"}, clear=False),
    ):
        from jobs.materialise_brief_sections import main

        with pytest.raises(UndefinedTableError, match="missing gold table"):
            await main(date(2026, 5, 22))
