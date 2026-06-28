"""
CLI test for `asx news signoff` (asxos/cli/news.py).

Exercises the Typer wiring for `news_signoff`:
- personal-use firewall (ASXOS_PERSONAL_USE unset → non-zero exit)
- the no-recent-ingest Exit(1) path (fetch returns no rows)
- the --force bypass (skips the prerequisite fetch)
- the decisions INSERT ... RETURNING id path (fetchrow → decisions.id)

The db pool is fully patched (init_pool/close_pool/acquire) so no real
Postgres connection is touched. asyncio_mode=auto; CliRunner drives the app.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from asxos.cli import main as cli_main
from asxos.cli import news as news_mod

runner = CliRunner()


def _make_conn(*, fetch_rows: list[Any], insert_id: int = 4242) -> MagicMock:
    """Build a mock asyncpg connection.

    fetch() returns ``fetch_rows`` (the prerequisite check); fetchrow()
    returns a dict with the RETURNING id.
    """
    conn = MagicMock()
    conn.fetch = AsyncMock(return_value=fetch_rows)
    conn.fetchrow = AsyncMock(return_value={"id": insert_id})
    conn.fetchval = AsyncMock(return_value=None)
    conn.execute = AsyncMock(return_value=None)
    return conn


def _patched(conn: MagicMock):
    """Context patching news.py's init_pool/close_pool/acquire to use ``conn``."""

    @asynccontextmanager
    async def _acquire() -> Any:
        yield conn

    return (
        patch.object(news_mod, "init_pool", new=AsyncMock(return_value=None)),
        patch.object(news_mod, "close_pool", new=AsyncMock(return_value=None)),
        patch.object(news_mod, "acquire", new=_acquire),
    )


def test_signoff_requires_personal_use(monkeypatch) -> None:
    """Firewall: with ASXOS_PERSONAL_USE unset, the command exits non-zero."""
    monkeypatch.delenv("ASXOS_PERSONAL_USE", raising=False)
    conn = _make_conn(fetch_rows=[{"?column?": 1}])
    p1, p2, p3 = _patched(conn)
    with p1, p2, p3:
        result = runner.invoke(cli_main.app, ["news", "signoff"])
    assert result.exit_code != 0, result.output
    # The DB must never be opened when the firewall blocks the command.
    conn.fetch.assert_not_awaited()
    conn.fetchrow.assert_not_awaited()


def test_signoff_no_recent_ingest_exits_1(monkeypatch) -> None:
    """No successful ingest_news in last 7 days → Exit(code=1), no INSERT."""
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    conn = _make_conn(fetch_rows=[])  # prerequisite fetch returns nothing
    p1, p2, p3 = _patched(conn)
    with p1, p2, p3:
        result = runner.invoke(cli_main.app, ["news", "signoff"])
    assert result.exit_code == 1, result.output
    assert "No successful ingest_news" in result.output
    conn.fetch.assert_awaited_once()
    # Must NOT reach the decisions INSERT.
    conn.fetchrow.assert_not_awaited()


def test_signoff_happy_path_inserts_decision(monkeypatch) -> None:
    """Prerequisite met → decisions INSERT...RETURNING id, prints decisions.id."""
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    conn = _make_conn(fetch_rows=[{"?column?": 1}], insert_id=777)
    p1, p2, p3 = _patched(conn)
    with p1, p2, p3:
        result = runner.invoke(cli_main.app, ["news", "signoff", "--note", "ship it"])
    assert result.exit_code == 0, result.output
    assert "decisions.id=777" in result.output
    conn.fetch.assert_awaited_once()
    conn.fetchrow.assert_awaited_once()
    # The INSERT carries the rationale tag and the note text.
    args = conn.fetchrow.await_args.args
    rationale = args[-1]
    assert "[m14_news_signoff]" in rationale
    assert "Note: ship it" in rationale


def test_signoff_force_bypasses_prereq(monkeypatch) -> None:
    """--force skips the prerequisite fetch entirely and still inserts."""
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    conn = _make_conn(fetch_rows=[], insert_id=99)  # would fail prereq if checked
    p1, p2, p3 = _patched(conn)
    with p1, p2, p3:
        result = runner.invoke(cli_main.app, ["news", "signoff", "--force"])
    assert result.exit_code == 0, result.output
    assert "decisions.id=99" in result.output
    # The prerequisite check is skipped; only the INSERT runs.
    conn.fetch.assert_not_awaited()
    conn.fetchrow.assert_awaited_once()
