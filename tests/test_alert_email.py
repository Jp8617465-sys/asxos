"""The shared job alert path — `asxos/jobs/utils/alert_email.py`.

Six jobs had grown three different `_send_alert` contracts. This covers the one
they now share. `tests/test_alert_send_observability.py` covers the same
contract through each job module (and pins that no job re-implements it); this
file covers the helper directly, plus the two properties only it has: body
escaping, and a not-configured signal distinct from a failure.
"""
from __future__ import annotations

import sys
import types

import pytest

from asxos.jobs.utils.alert_email import NOT_CONFIGURED, send_alert

ENV = {
    "RESEND_API_KEY": "k",
    "BRIEF_TO_EMAIL": "to@example.com",
    "BRIEF_FROM_EMAIL": "from@example.com",
}


def _fake_resend(
    monkeypatch: pytest.MonkeyPatch, *, raises: Exception | None = None
) -> list[dict]:
    """Stub `resend` so no network call is attempted. Returns captured payloads."""
    sent: list[dict] = []
    mod = types.ModuleType("resend")
    mod.api_key = ""  # type: ignore[attr-defined]

    class _Emails:
        @staticmethod
        def send(payload: dict) -> dict:
            if raises is not None:
                raise raises
            sent.append(payload)
            return {"id": "sent"}

    mod.Emails = _Emails  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "resend", mod)
    return sent


@pytest.fixture
def configured(monkeypatch: pytest.MonkeyPatch) -> None:
    for k, v in ENV.items():
        monkeypatch.setenv(k, v)


def test_success_returns_none(configured, monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_resend(monkeypatch)
    assert send_alert("subject", "body") is None


def test_body_is_escaped_into_a_pre_block(
    configured, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`job_runs.error_message` reaches check_cron_health's alert, so external
    text must not be able to break out of the `<pre>`."""
    sent = _fake_resend(monkeypatch)
    send_alert("s", "DEGRADED: <script>alert(1)</script> & more")
    assert sent[0]["html"] == (
        "<pre>DEGRADED: &lt;script&gt;alert(1)&lt;/script&gt; &amp; more</pre>"
    )
    assert "<script>" not in sent[0]["html"]


def test_subject_and_addresses_are_passed_through(
    configured, monkeypatch: pytest.MonkeyPatch
) -> None:
    sent = _fake_resend(monkeypatch)
    send_alert("asxos pipeline alert — 2026-09-18", "body")
    assert sent[0]["subject"] == "asxos pipeline alert — 2026-09-18"
    assert sent[0]["to"] == ENV["BRIEF_TO_EMAIL"]
    assert sent[0]["from"] == ENV["BRIEF_FROM_EMAIL"]


def test_failure_does_not_raise(configured, monkeypatch: pytest.MonkeyPatch) -> None:
    """A dead notification channel must not take down the check that found the
    problem. This is the property that must not regress."""
    _fake_resend(monkeypatch, raises=RuntimeError("resend is down"))
    send_alert("s", "b")  # must not raise


def test_failure_is_reported_not_swallowed(
    configured, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_resend(monkeypatch, raises=RuntimeError("resend is down"))
    note = send_alert("s", "b")
    assert note is not None, "a swallowed send failure left no trace"
    assert "RuntimeError" in note


def test_failure_note_carries_the_class_name_only(
    configured, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CWE-532: a Resend/httpx error embeds the request URL and the API key
    travels with it, and `job_runs` is queryable and agent-readable."""
    secret = "re_live_SECRETKEY123"
    _fake_resend(
        monkeypatch,
        raises=RuntimeError(f"401 for https://api.resend.com?k={secret}"),
    )
    note = send_alert("s", "b")
    assert note is not None
    assert secret not in note
    assert "api.resend.com" not in note
    assert "401" not in note


@pytest.mark.parametrize("missing", sorted(ENV))
def test_any_missing_env_var_reports_not_configured(
    missing: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A deliberate no-send is still an alert that did not arrive, but it is a
    different event from a failed send and must not read as one."""
    for k, v in ENV.items():
        monkeypatch.setenv(k, v)
    monkeypatch.delenv(missing, raising=False)
    assert send_alert("s", "b") == NOT_CONFIGURED


def test_unconfigured_never_touches_the_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for k in ENV:
        monkeypatch.delenv(k, raising=False)
    sent = _fake_resend(monkeypatch, raises=AssertionError("must not be called"))
    assert send_alert("s", "b") == NOT_CONFIGURED
    assert sent == []
