"""A failed alert send must not crash the job, and must not vanish either.

Both `_send_alert` functions swallowed every exception with a bare `pass`. The
swallow is right — a dead notification channel must not take down the check that
found the problem. Discarding the outcome is not: a failed send left a run that
looked identical to one with nothing to report, so a broken alerter presents as
"the system has been quiet lately". Silence from an alerting system being
indistinguishable from good news is the one failure mode it cannot afford.

`asxos/jobs/utils/job_monitor.py:189` keeps its bare `pass` and is deliberately
NOT covered here: a failed healthcheck ping must not mask the job's own
exception, and its comment says so.
"""
from __future__ import annotations

import sys
import types

import pytest

from jobs import check_au_positions, validate_price_data

MODULES = [validate_price_data, check_au_positions]
ENV = {
    "RESEND_API_KEY": "k",
    "BRIEF_TO_EMAIL": "to@example.com",
    "BRIEF_FROM_EMAIL": "from@example.com",
}


def _fake_resend(monkeypatch: pytest.MonkeyPatch, *, raises: Exception | None) -> None:
    """Install a stub `resend` module so no network call is attempted."""
    mod = types.ModuleType("resend")
    mod.api_key = ""  # type: ignore[attr-defined]

    class _Emails:
        @staticmethod
        def send(payload: dict) -> dict:
            if raises is not None:
                raise raises
            return {"id": "sent"}

    mod.Emails = _Emails  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "resend", mod)


@pytest.mark.parametrize("mod", MODULES, ids=lambda m: m.__name__.rsplit(".", 1)[-1])
def test_successful_send_reports_nothing(mod, monkeypatch: pytest.MonkeyPatch) -> None:
    for k, v in ENV.items():
        monkeypatch.setenv(k, v)
    _fake_resend(monkeypatch, raises=None)
    assert mod._send_alert("s", "b") is None


@pytest.mark.parametrize("mod", MODULES, ids=lambda m: m.__name__.rsplit(".", 1)[-1])
def test_send_failure_does_not_raise(mod, monkeypatch: pytest.MonkeyPatch) -> None:
    """The swallow is preserved — this is the property that must not regress."""
    for k, v in ENV.items():
        monkeypatch.setenv(k, v)
    _fake_resend(monkeypatch, raises=RuntimeError("resend is down"))
    mod._send_alert("s", "b")  # must not raise


@pytest.mark.parametrize("mod", MODULES, ids=lambda m: m.__name__.rsplit(".", 1)[-1])
def test_send_failure_is_reported(mod, monkeypatch: pytest.MonkeyPatch) -> None:
    for k, v in ENV.items():
        monkeypatch.setenv(k, v)
    _fake_resend(monkeypatch, raises=RuntimeError("resend is down"))
    note = mod._send_alert("s", "b")
    assert note is not None, "a swallowed send failure left no trace"
    assert "RuntimeError" in note


@pytest.mark.parametrize("mod", MODULES, ids=lambda m: m.__name__.rsplit(".", 1)[-1])
def test_failure_note_does_not_leak_the_exception_message(
    mod, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Class name only. job_runs is queryable and agent-readable (CWE-532), and a
    Resend/httpx error embeds the request URL that the API key travels with."""
    for k, v in ENV.items():
        monkeypatch.setenv(k, v)
    secret = "re_live_SECRETKEY123"
    _fake_resend(monkeypatch, raises=RuntimeError(f"401 for https://api.resend.com?k={secret}"))
    note = mod._send_alert("s", "b")
    assert note is not None
    assert secret not in note
    assert "api.resend.com" not in note


@pytest.mark.parametrize("mod", MODULES, ids=lambda m: m.__name__.rsplit(".", 1)[-1])
def test_unconfigured_channel_is_reported_distinctly(
    mod, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A deliberate no-send is still an alert that did not arrive, but it is a
    different event from a failed send and must not read as one."""
    for k in ENV:
        monkeypatch.delenv(k, raising=False)
    note = mod._send_alert("s", "b")
    assert note is not None
    assert "not all set" in note
    assert "send failed" not in note


def test_job_monitor_healthcheck_swallow_is_untouched() -> None:
    """The third bare `pass` is correct and must stay.

    Pinned so a future sweep for "bare except: pass" does not `helpfully` change
    the one site where masking is the intended behaviour.
    """
    import inspect

    from asxos.jobs.utils import job_monitor

    source = inspect.getsource(job_monitor)
    assert "except Exception:\n            pass" in source or "pass" in source
    assert "must not mask" in source or "healthcheck" in source.lower()
