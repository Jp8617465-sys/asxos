"""jobs/apply_github_decisions.py — owner comments on the decisions issue become governance writes."""
from __future__ import annotations

import io
import json
import urllib.error
import urllib.request
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, ClassVar
from unittest.mock import AsyncMock, patch

import pytest
import yaml

import jobs.apply_github_decisions as job_mod
from asxos.config import settings
from asxos.domain.governance import github_commands as gc

ROOT = Path(__file__).resolve().parents[1]
OWNER = "Jp8617465-sys"
NOW = datetime(2026, 9, 17, 20, 31, tzinfo=UTC)


class FakeGitHub:
    """The four calls, in memory; `unavailable` makes every call a GitHubUnavailable."""

    def __init__(self, comments: list[gc.IssueComment], *, pinned: bool = False, unavailable: str | None = None, post_fails: bool = False) -> None:
        self.issue_number = 289
        self._comments = list(comments)
        self.pinned = pinned
        self.unavailable = unavailable
        self.post_fails = post_fails
        self.posted: list[str] = []

    def _check(self) -> None:
        if self.unavailable:
            raise job_mod.GitHubUnavailable(self.unavailable)

    def owner_login(self) -> str:
        self._check()
        return OWNER

    def ensure_pinned(self) -> bool:
        self._check()
        was = self.pinned
        self.pinned = True
        return not was

    def comments(self) -> list[gc.IssueComment]:
        self._check()
        return list(self._comments)

    def post_comment(self, body: str) -> int:
        if self.post_fails:
            raise job_mod.GitHubUnavailable("POST -> HTTP 403")
        self.posted.append(body)
        return 1000 + len(self.posted)


class FakeConn:
    def transaction(self) -> Any:
        @asynccontextmanager
        async def _tx() -> Any:
            yield

        return _tx()


class FakeMonitor:
    def __init__(self) -> None:
        self.rows_written = 0
        self.note: str | None = None


def _c(comment_id: int, body: str, author: str = OWNER) -> gc.IssueComment:
    return gc.IssueComment(comment_id=comment_id, author_login=author, body=body)


def _thesis(thesis_id: int, status: str) -> Any:
    return SimpleNamespace(thesis_id=thesis_id, symbol="CBA.AU", governance_status=status)


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")


async def _run(github: FakeGitHub, **overrides: Any) -> tuple[dict[str, Any], FakeMonitor, dict[str, Any]]:
    @asynccontextmanager
    async def _acquire() -> Any:
        yield FakeConn()

    mocks = {
        "approve_object": AsyncMock(side_effect=lambda conn, tid, *, reasoning: _thesis(tid, "approved")),
        "reject_object": AsyncMock(side_effect=lambda conn, tid, *, reasoning: _thesis(tid, "rejected")),
        "persist_disposition": AsyncMock(),
    }
    mocks.update(overrides)
    case = SimpleNamespace(decision=SimpleNamespace(decision_packet_id="dpk-cba-1-2026-09-17", content_hash="a" * 64, recommendation_state="watch"))
    monitor = FakeMonitor()
    with (
        patch.object(job_mod, "acquire", side_effect=_acquire),
        patch.object(job_mod, "approve_object", mocks["approve_object"]),
        patch.object(job_mod, "reject_object", mocks["reject_object"]),
        patch.object(job_mod, "persist_disposition", mocks["persist_disposition"]),
        patch.object(job_mod.repository, "load_case", AsyncMock(return_value=case)),
        patch.object(job_mod, "disposition_for", lambda case, *, verdict, note, recorded_at: SimpleNamespace(disposition_id=f"disp-{case.decision.decision_packet_id}-{verdict}", note=note)),
        patch.object(job_mod, "paper_intent_for", lambda case, disp, *, created_at: None),
    ):
        summary = await job_mod.run(monitor=monitor, github=github, recorded_at=NOW)  # type: ignore[arg-type]
    return summary, monitor, mocks


async def test_owner_commands_are_applied_once_each_and_answered_with_a_marker() -> None:
    github = FakeGitHub([
        _c(1, "APPROVE thesis 42 evidence fresh, plan sane"),
        _c(2, "APPROVE thesis 43 looks fine", author="stranger"),
        _c(3, "DISPOSE dpk-cba-1-2026-09-17 defer"),
        _c(4, "nice work"),
    ])
    summary, monitor, mocks = await _run(github)
    assert summary["applied"] == ["1:APPROVE thesis 42", "3:DISPOSE dpk-cba-1-2026-09-17 defer"]
    assert summary["refused"] == {} and monitor.rows_written == 2 and monitor.note is None
    assert summary["pinned_now"] is True and github.pinned
    mocks["approve_object"].assert_awaited_once()
    assert mocks["approve_object"].await_args.kwargs == {"reasoning": "evidence fresh, plan sane"}
    mocks["persist_disposition"].assert_awaited_once()
    disp = mocks["persist_disposition"].await_args.args[1]
    assert disp.note == "disposed via GitHub comment 3"
    assert [gc.parse_marker(b) for b in github.posted] == [gc.MarkerReply("applied", 1), gc.MarkerReply("applied", 3)]
    assert "✅ Applied `APPROVE thesis 42`" in github.posted[0] and "governance_status=approved" in github.posted[0]
    assert "paper only" not in github.posted[1] and "no paper intent" in github.posted[1]


async def test_a_second_run_is_a_no_op_because_the_markers_exist() -> None:
    github = FakeGitHub([
        _c(1, "APPROVE thesis 42 fine"),
        _c(2, f"{gc.marker_for('applied', 1)}\n✅ Applied"),
    ], pinned=True)
    summary, _monitor, mocks = await _run(github)
    assert summary["applied"] == [] and summary["pending"] == 0 and github.posted == []
    assert summary["pinned_now"] is False
    mocks["approve_object"].assert_not_awaited()


async def test_a_refused_command_is_answered_once_with_the_reason_and_noted() -> None:
    refuse = AsyncMock(side_effect=ValueError("Cannot approve thesis 42 — governance_status is 'approved', expected 'pending_review'."))
    github = FakeGitHub([_c(1, "APPROVE thesis 42 again"), _c(2, "REJECT thesis 9"), _c(3, "REJECT thesis 10 stale")])
    summary, monitor, _mocks = await _run(github, approve_object=refuse)
    assert summary["applied"] == ["3:REJECT thesis 10"] and monitor.rows_written == 1
    assert set(summary["refused"]) == {"1:APPROVE thesis 42", "2:REJECT thesis 9"}
    assert "expected 'pending_review'" in summary["refused"]["1:APPROVE thesis 42"]
    assert summary["refused"]["2:REJECT thesis 9"].startswith("syntax:")
    assert monitor.note is not None and "2 command(s) refused" in monitor.note
    assert [gc.parse_marker(b) for b in github.posted] == [
        gc.MarkerReply("refused", 1), gc.MarkerReply("refused", 2), gc.MarkerReply("applied", 3),
    ]
    assert "❌ Not applied `APPROVE thesis 42`" in github.posted[0]


async def test_github_unavailable_is_a_note_not_a_failure() -> None:
    github = FakeGitHub([_c(1, "APPROVE thesis 42 fine")], unavailable="GET … -> HTTP 401")
    summary, monitor, mocks = await _run(github)
    assert summary["github"] == "unavailable" and summary["applied"] == []
    assert monitor.note is not None and "GitHub unavailable" in monitor.note and "401" in monitor.note
    mocks["approve_object"].assert_not_awaited()


async def test_an_applied_decision_whose_marker_cannot_post_fails_loudly() -> None:
    github = FakeGitHub([_c(1, "APPROVE thesis 42 fine")], post_fails=True)
    with pytest.raises(RuntimeError, match="could not post its marker reply"):
        await _run(github)


def test_http_4xx_and_network_errors_map_to_unavailable_but_5xx_raises() -> None:
    gh = job_mod.GitHubIssue(token="t", ref=job_mod.RepoRef("o", "r"), issue_number=1)

    def _http(code: int) -> Any:
        return urllib.error.HTTPError("u", code, "m", {}, io.BytesIO(b""))  # type: ignore[arg-type]

    with patch.object(urllib.request, "urlopen", side_effect=_http(404)), pytest.raises(job_mod.GitHubUnavailable, match="404"):
        gh.owner_login()
    with patch.object(urllib.request, "urlopen", side_effect=urllib.error.URLError("dns")), pytest.raises(job_mod.GitHubUnavailable, match="dns"):
        gh.owner_login()
    with patch.object(urllib.request, "urlopen", side_effect=_http(502)), pytest.raises(urllib.error.HTTPError):
        gh.owner_login()


def test_requests_carry_the_token_as_a_bearer_and_never_log_it(caplog: pytest.LogCaptureFixture) -> None:
    gh = job_mod.GitHubIssue(token="secret-token-value", ref=job_mod.RepoRef("o", "r"), issue_number=1)
    seen: list[Any] = []

    class _Resp(io.BytesIO):
        headers: ClassVar[dict[str, str]] = {"content-type": "application/json"}

        def __enter__(self) -> Any:
            return self

        def __exit__(self, *a: Any) -> None:
            return None

    def _open(req: Any, timeout: int) -> Any:
        seen.append(req)
        return _Resp(json.dumps({"owner": {"login": OWNER}}).encode())

    with patch.object(urllib.request, "urlopen", _open):
        assert gh.owner_login() == OWNER
    assert seen[0].get_header("Authorization") == "Bearer secret-token-value"
    assert "secret-token-value" not in caplog.text


def test_env_parsing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(job_mod.REPO_ENV, "Jp8617465-sys/asxos")
    monkeypatch.setenv(job_mod.ISSUE_ENV, "289")
    assert job_mod.repo_ref_from_env() == job_mod.RepoRef("Jp8617465-sys", "asxos")
    assert job_mod.issue_number_from_env() == 289
    monkeypatch.setenv(job_mod.ISSUE_ENV, "issue-289")
    with pytest.raises(RuntimeError, match=job_mod.ISSUE_ENV):
        job_mod.issue_number_from_env()
    monkeypatch.setenv(job_mod.REPO_ENV, "asxos")
    with pytest.raises(RuntimeError, match="owner/repo"):
        job_mod.repo_ref_from_env()


async def test_main_is_behind_the_personal_use_firewall_then_needs_the_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ASXOS_PERSONAL_USE")
    with pytest.raises(RuntimeError, match="ASXOS_PERSONAL_USE"):
        await job_mod.main()
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    monkeypatch.delenv(job_mod.TOKEN_ENV, raising=False)
    with pytest.raises(RuntimeError, match=job_mod.TOKEN_ENV):
        await job_mod.main()


def test_daily_brief_applies_decisions_first_with_the_token_scoped_to_that_step() -> None:
    wf = yaml.safe_load((ROOT / ".github/workflows/daily-brief.yml").read_text())
    job = next(iter(wf["jobs"].values()))
    steps = [s for s in job["steps"] if s.get("name")]
    first = steps[0]
    assert first["name"] == "Install" and steps[1]["name"] == "Apply GitHub decisions"
    step = steps[1]
    assert step["env"]["ARBI_GITHUB_TOKEN"] == "${{ secrets.ARBI_GITHUB_TOKEN }}"
    assert step["env"]["ASXOS_DECISIONS_ISSUE"] == "289"
    assert "ARBI_GITHUB_TOKEN" not in job["env"]
    assert sum("ARBI_GITHUB_TOKEN" in json.dumps(s.get("env", {})) for s in job["steps"]) == 1
    assert settings.healthcheck_url_apply_github_decisions == ""
