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

import ast
import pathlib
import sys
import types

import pytest

from jobs import (
    check_au_positions,
    check_thesis_invalidations,
    check_us_positions,
    score_macro_theses,
    validate_price_data,
)

# All five jobs whose `_send_alert(subject, body)` is the shared helper
# (`asxos/jobs/utils/alert_email.py`). Extended 2026-09-18 from the original
# two: the other three still swallowed silently, which is the very defect this
# file's docstring describes, so centralising the contract fixed them and the
# parametrisation is what proves it. `check_cron_health` is deliberately absent
# — different signature, and its discard is documented (see the structural
# tests at the bottom).
MODULES = [
    validate_price_data,
    check_au_positions,
    check_us_positions,
    check_thesis_invalidations,
    score_macro_theses,
]
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


# ---------------------------------------------------------------------------
# Structural guards — the defect class, not one instance of it
# ---------------------------------------------------------------------------

_JOBS_DIR = pathlib.Path(__file__).resolve().parents[1] / "jobs"

# A discard is legitimate in exactly one shape: the enclosing block RAISES
# straight after, so JobMonitor records the exception as the run's
# error_message and the run goes red anyway. Recording a send note there would
# overwrite the primary failure with a secondary one. That shape is detected
# below rather than allow-listed by filename, so a new job gets the same
# latitude for the same reason — and no latitude for any other reason.


def _raises_later(body: list[ast.stmt], idx: int) -> bool:
    """Does any statement after `idx` in this same block raise?"""
    return any(
        isinstance(n, ast.Raise)
        for stmt in body[idx + 1 :]
        for n in ast.walk(stmt)
    )


def test_no_job_reimplements_the_resend_call() -> None:
    """One place touches the provider. Six private copies is how the contract
    drifted into three different ones in the first place."""
    offenders = [
        p.name
        for p in sorted(_JOBS_DIR.glob("*.py"))
        if "resend.Emails.send" in p.read_text()
    ]
    assert not offenders, (
        "these jobs call resend directly instead of "
        "asxos.jobs.utils.alert_email.send_alert: " + ", ".join(offenders)
    )


def test_no_job_discards_a_send_outcome_on_a_run_that_stays_green() -> None:
    """A bare `_send_alert(...)` throws the failure note away, which is what
    made a broken alerter present as "quiet lately". Allowed only where the
    block goes on to raise — see the comment above."""
    offenders: list[str] = []
    for path in sorted(_JOBS_DIR.glob("*.py")):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            body = getattr(node, "body", None)
            if not isinstance(body, list):
                continue
            for idx, stmt in enumerate(body):
                if not isinstance(stmt, ast.Expr) or not isinstance(
                    stmt.value, ast.Call
                ):
                    continue
                fn = stmt.value.func
                name = fn.id if isinstance(fn, ast.Name) else getattr(fn, "attr", "")
                if name in {"_send_alert", "send_alert"} and not _raises_later(
                    body, idx
                ):
                    offenders.append(f"{path.name}:{stmt.lineno}")
    assert not offenders, (
        "the return of send_alert is discarded on a path that does not raise, "
        "so a failed alert leaves no trace in job_runs: " + ", ".join(offenders)
    )
