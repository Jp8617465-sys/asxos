"""
Tests for asxos/jobs/utils/fallback_email.py and the compose_brief.main
integration that uses it.

Covers:
  - send_fallback_email calls Resend with correct args
  - HTML escaping of body text (no <script> injection through error messages)
  - Resend failure → synthetic job_runs row written
  - Resend + DB both fail → stderr, NO raise (last-resort path)
  - compose_brief.main fires fallback when collect() raises
  - compose_brief.main avoids duplicate fallback after confirmed primary delivery
  - compose_brief.main catches asyncio.CancelledError
  - compose_brief.main includes traceback in fallback body
  - compose_brief.main does NOT fire fallback when --no-send
  - compose_brief.main does NOT fire fallback on happy path
  - Original exception always propagates through the fallback
"""
from __future__ import annotations

import asyncio
import io
import os
import sys
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from asxos.jobs.utils.fallback_email import send_fallback_email


@pytest.fixture(autouse=True)
def _personal_use_on(monkeypatch: pytest.MonkeyPatch) -> None:
    """compose_brief.main() gained a top-level require_personal_use_job()
    gate (07-18 audit P1 #2, added 2026-07-21) — same autouse pattern #59
    established when the R14 gates landed. The gate's own negative test
    lives in test_jobs_personal_use_gate.py, not here."""
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")


# ---------------------------------------------------------------------------
# send_fallback_email — happy path
# ---------------------------------------------------------------------------


def _stub_settings() -> MagicMock:
    s = MagicMock()
    s.resend_api_key = "test_key"
    s.brief_from_email = "from@example.com"
    s.brief_to_email = "to@example.com"
    return s


def test_send_fallback_email_calls_resend_with_correct_args() -> None:
    fake_send = MagicMock(return_value="msg_123")
    with (
        patch("asxos.brief.email._send_via_resend", new=fake_send),
        patch("asxos.brief.email._EmailSettings", return_value=_stub_settings()),
    ):
        send_fallback_email(subject="[asxos] FAIL", body_text="something broke")

    fake_send.assert_called_once()
    kwargs = fake_send.call_args.kwargs
    assert kwargs["api_key"] == "test_key"
    assert kwargs["from_address"] == "from@example.com"
    assert kwargs["to_address"] == "to@example.com"
    assert kwargs["subject"] == "[asxos] FAIL"
    assert "something broke" in kwargs["html"]
    # Wrapped in <pre> for monospace
    assert "<pre" in kwargs["html"]


def test_send_fallback_email_escapes_html_injection() -> None:
    """Error messages may contain user-controlled strings; ensure escaping."""
    fake_send = MagicMock(return_value="msg_1")
    with (
        patch("asxos.brief.email._send_via_resend", new=fake_send),
        patch("asxos.brief.email._EmailSettings", return_value=_stub_settings()),
    ):
        send_fallback_email(
            subject="[asxos] FAIL",
            body_text="<script>alert(1)</script>",
        )
    html_out = fake_send.call_args.kwargs["html"]
    # The escaped form must appear; raw <script> must not
    assert "&lt;script&gt;" in html_out
    assert "<script>alert(1)</script>" not in html_out


# ---------------------------------------------------------------------------
# send_fallback_email — Resend failure path
# ---------------------------------------------------------------------------


def test_send_fallback_email_swallows_resend_failure_and_writes_job_runs() -> None:
    """Resend down → fallback attempts synthetic job_runs row; never raises."""
    fake_send = MagicMock(side_effect=RuntimeError("Resend 503"))
    fake_record = AsyncMock()
    with (
        patch("asxos.brief.email._send_via_resend", new=fake_send),
        patch("asxos.brief.email._EmailSettings", return_value=_stub_settings()),
        patch(
            "asxos.jobs.utils.fallback_email._record_fallback_failure",
            new=fake_record,
        ),
    ):
        # MUST NOT raise
        send_fallback_email(subject="[asxos] FAIL", body_text="body")

    fake_record.assert_awaited_once()
    kwargs = fake_record.await_args.kwargs
    assert kwargs["subject"] == "[asxos] FAIL"
    assert "Resend 503" in kwargs["error"]


def test_send_fallback_email_swallows_settings_validation_error() -> None:
    """Missing env vars → _EmailSettings() raises → swallowed; never raises out."""
    fake_record = AsyncMock()
    with (
        patch(
            "asxos.config.BriefSettings",
            side_effect=RuntimeError("BRIEF_TO_EMAIL missing"),
        ),
        patch(
            "asxos.jobs.utils.fallback_email._record_fallback_failure",
            new=fake_record,
        ),
    ):
        send_fallback_email(subject="x", body_text="y")
    fake_record.assert_awaited_once()


def test_send_fallback_email_writes_stderr_when_resend_and_db_both_fail() -> None:
    """Last-resort: both Resend and the job_runs write fail. stderr, no raise."""
    fake_send = MagicMock(side_effect=RuntimeError("Resend down"))
    fake_record = AsyncMock(side_effect=RuntimeError("DB down"))
    captured = io.StringIO()
    with (
        patch("asxos.brief.email._send_via_resend", new=fake_send),
        patch("asxos.brief.email._EmailSettings", return_value=_stub_settings()),
        patch(
            "asxos.jobs.utils.fallback_email._record_fallback_failure",
            new=fake_record,
        ),
        patch.object(sys, "stderr", captured),
    ):
        send_fallback_email(subject="x", body_text="y")  # must not raise

    out = captured.getvalue()
    assert "FATAL" in out
    assert "Resend down" in out
    assert "DB down" in out


# ---------------------------------------------------------------------------
# compose_brief.main — fallback integration
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_main_sends_fallback_when_collect_raises() -> None:
    fake_fallback = MagicMock()

    class FakeJobMonitor:
        def __init__(self, *a, **kw):
            self.rows_written = 0
        async def __aenter__(self):
            return self
        async def __aexit__(self, *a):
            return False

    with (
        patch("jobs.compose_brief.init_pool", new=AsyncMock()),
        patch("jobs.compose_brief.close_pool", new=AsyncMock()),
        patch("jobs.compose_brief.JobMonitor", new=FakeJobMonitor),
        patch(
            "jobs.compose_brief.v2_compose",
            new=AsyncMock(side_effect=RuntimeError("collect blew up")),
        ),
        patch("jobs.compose_brief.send_fallback_email", new=fake_fallback),
    ):
        # Import inside the patch context
        from jobs.compose_brief import main
        with pytest.raises(RuntimeError, match="collect blew up"):
            await main(date(2026, 5, 28), send=True)

    fake_fallback.assert_called_once()
    kwargs = fake_fallback.call_args.kwargs
    assert "FAILED" in kwargs["subject"]
    assert "2026-05-28" in kwargs["subject"]
    assert "RuntimeError" in kwargs["body_text"]
    assert "collect blew up" in kwargs["body_text"]
    # Traceback tail included
    assert "Traceback" in kwargs["body_text"]


@pytest.mark.asyncio
async def test_main_suppresses_duplicate_when_job_monitor_aexit_raises_after_send() -> None:
    """If JobMonitor's own __aexit__ fails (e.g. DB unreachable when writing
    the success row), the job still fails but the delivered brief is not sent
    again as a fallback."""
    fake_fallback = MagicMock()
    fake_send = MagicMock(return_value=MagicMock(
        to="a", subject="b", message_id="c",
    ))

    class FailingJobMonitor:
        def __init__(self, *a, **kw):
            self.rows_written = 0
        async def __aenter__(self):
            return self
        async def __aexit__(self, *a):
            raise RuntimeError("JobMonitor DB write failed")

    with (
        patch("jobs.compose_brief.init_pool", new=AsyncMock()),
        patch("jobs.compose_brief.close_pool", new=AsyncMock()),
        patch("jobs.compose_brief.JobMonitor", new=FailingJobMonitor),
        patch(
            "jobs.compose_brief.v2_compose",
            new=AsyncMock(return_value=_minimal_brief()),
        ),
        patch("jobs.compose_brief.v2_render_html", return_value="<html/>"),
        patch("jobs.compose_brief.send_brief", new=fake_send),
        patch("jobs.compose_brief.send_fallback_email", new=fake_fallback),
    ):
        from jobs.compose_brief import main
        with pytest.raises(RuntimeError, match="JobMonitor DB write failed"):
            await main(date(2026, 5, 28), send=True)

    fake_send.assert_called_once()
    fake_fallback.assert_not_called()


@pytest.mark.asyncio
async def test_main_catches_asyncio_cancelled_error() -> None:
    """CancelledError is BaseException in Py3.12; bare `except Exception` misses it.
    The fallback must still fire on asyncpg pool timeout (which propagates as
    CancelledError)."""
    fake_fallback = MagicMock()

    class FakeJobMonitor:
        def __init__(self, *a, **kw):
            self.rows_written = 0
        async def __aenter__(self):
            return self
        async def __aexit__(self, *a):
            return False

    with (
        patch("jobs.compose_brief.init_pool", new=AsyncMock()),
        patch("jobs.compose_brief.close_pool", new=AsyncMock()),
        patch("jobs.compose_brief.JobMonitor", new=FakeJobMonitor),
        patch(
            "jobs.compose_brief.v2_compose",
            new=AsyncMock(side_effect=asyncio.CancelledError()),
        ),
        patch("jobs.compose_brief.send_fallback_email", new=fake_fallback),
    ):
        from jobs.compose_brief import main
        with pytest.raises(asyncio.CancelledError):
            await main(date(2026, 5, 28), send=True)

    fake_fallback.assert_called_once()
    assert "CancelledError" in fake_fallback.call_args.kwargs["body_text"]


@pytest.mark.asyncio
async def test_main_skips_fallback_when_no_send() -> None:
    """Local dev path: --no-send → failure visible in stdout, no email noise."""
    fake_fallback = MagicMock()

    class FakeJobMonitor:
        def __init__(self, *a, **kw):
            self.rows_written = 0
        async def __aenter__(self):
            return self
        async def __aexit__(self, *a):
            return False

    with (
        patch("jobs.compose_brief.init_pool", new=AsyncMock()),
        patch("jobs.compose_brief.close_pool", new=AsyncMock()),
        patch("jobs.compose_brief.JobMonitor", new=FakeJobMonitor),
        patch(
            "jobs.compose_brief.v2_compose",
            new=AsyncMock(side_effect=RuntimeError("boom")),
        ),
        patch("jobs.compose_brief.send_fallback_email", new=fake_fallback),
    ):
        from jobs.compose_brief import main
        with pytest.raises(RuntimeError):
            await main(date(2026, 5, 28), send=False)

    fake_fallback.assert_not_called()


@pytest.mark.asyncio
async def test_main_no_fallback_on_happy_path() -> None:
    fake_fallback = MagicMock()

    class FakeJobMonitor:
        def __init__(self, *a, **kw):
            self.rows_written = 0
        async def __aenter__(self):
            return self
        async def __aexit__(self, *a):
            return False

    with (
        patch("jobs.compose_brief.init_pool", new=AsyncMock()),
        patch("jobs.compose_brief.close_pool", new=AsyncMock()),
        patch("jobs.compose_brief.JobMonitor", new=FakeJobMonitor),
        patch(
            "jobs.compose_brief.v2_compose",
            new=AsyncMock(return_value=_minimal_brief()),
        ),
        patch("jobs.compose_brief.v2_render_html", return_value="<html/>"),
        patch("jobs.compose_brief.send_brief", return_value=MagicMock(
            to="a", subject="b", message_id="c",
        )),
        patch("jobs.compose_brief.send_fallback_email", new=fake_fallback),
    ):
        from jobs.compose_brief import main
        await main(date(2026, 5, 28), send=True)  # no raise

    fake_fallback.assert_not_called()


@pytest.mark.asyncio
async def test_persistence_failure_delivers_primary_then_fails_loudly() -> None:
    """A missing brief_runs row must not suppress the stop-breach brief.

    Delivery happens first; the typed failure then reaches JobMonitor so the
    cron exits non-zero. Because that failure was durably recorded, a duplicate
    fallback email is intentionally suppressed.
    """
    fake_fallback = MagicMock()
    fake_send = MagicMock(return_value=MagicMock(
        to="a", subject="b", message_id="c",
    ))
    monitor_exit: dict[str, object] = {}

    class RecordingJobMonitor:
        def __init__(self, *a, **kw):
            self.rows_written = 0
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            monitor_exit["exc_type"] = exc_type
            monitor_exit["rows_written"] = self.rows_written
            return False

    brief = _minimal_brief()
    brief.sections = (MagicMock(), MagicMock())
    brief.persistence_error = "RuntimeError: brief_runs unavailable"

    with (
        patch("jobs.compose_brief.init_pool", new=AsyncMock()),
        patch("jobs.compose_brief.close_pool", new=AsyncMock()),
        patch("jobs.compose_brief.JobMonitor", new=RecordingJobMonitor),
        patch("jobs.compose_brief.v2_compose", new=AsyncMock(return_value=brief)),
        patch("jobs.compose_brief.v2_render_html", return_value="<html/>"),
        patch("jobs.compose_brief.send_brief", new=fake_send),
        patch("jobs.compose_brief.send_fallback_email", new=fake_fallback),
    ):
        from jobs.compose_brief import BriefRunPersistenceError, main
        with pytest.raises(BriefRunPersistenceError, match="brief_runs unavailable"):
            await main(date(2026, 5, 28), send=True)

    fake_send.assert_called_once()
    fake_fallback.assert_not_called()
    assert monitor_exit["exc_type"] is BriefRunPersistenceError
    assert monitor_exit["rows_written"] == 2


def _minimal_brief() -> MagicMock:
    """Minimal Brief-shape stub for v2_compose return value."""
    brief = MagicMock()
    brief.sections = ()
    brief.persistence_error = None
    return brief


def test_fallback_works_with_email_only_env_no_supabase_vars() -> None:
    """The H8 pin: the notifier must construct its settings from the three
    email vars ALONE.

    The original code called BriefSettings(), which also requires SUPABASE_URL
    and SUPABASE_ANON_KEY — vars the brief runtime does not carry. So the
    last-resort notifier raised ValidationError on every real invocation and
    was swallowed: a correct alarm wired to a bell that could never ring. The
    prior tests missed it because they patched the settings class; this one
    constructs it for real. Reverting to BriefSettings fails here.
    """
    sent = {}

    def fake_send(**kwargs):
        sent.update(kwargs)

    env = {
        "RESEND_API_KEY": "dummy-key-not-real",
        "BRIEF_FROM_EMAIL": "from@example.com",
        "BRIEF_TO_EMAIL": "to@example.com",
        # Deliberately NO SUPABASE_URL / SUPABASE_ANON_KEY.
    }
    with (
        patch.dict(os.environ, env, clear=True),
        patch("asxos.brief.email._send_via_resend", new=fake_send),
    ):
        send_fallback_email(subject="[asxos] test", body_text="body")

    assert sent.get("api_key") == "dummy-key-not-real"
    assert sent.get("to_address") == "to@example.com"
