#!/usr/bin/env python
"""
Apply James's GitHub-comment decisions (F-E2E r2, S8) — disposition from a phone.

First step of daily-brief.yml. Reads the comments on the pinned "asxos —
decisions" issue (ASXOS_DECISIONS_ISSUE), keeps only those written by the
repository OWNER (the login fetched from the repository itself, never from a
comment) that have no marker reply yet, parses each first line with
asxos/domain/governance/github_commands.py, and applies:

    APPROVE thesis <id> <reason>        -> theses/service.approve_object
    REJECT thesis <id> <reason>         -> theses/service.reject_object
    DISPOSE <packet_id> <verdict> [note] -> disposition_for + paper_intent_for
                                           + persist_disposition

Every command gets exactly one reply carrying a marker (applied or refused,
with the error). A comment with a marker is never re-read, so a re-run is a
no-op and a refused command is answered once, not nightly. Every other
comment on the issue is data and is left alone.

GitHub is not this pipeline's dependency: a 4xx (bad token, wrong issue
number, no permission) or an unreachable API records a job_runs note and
exits 0 so the brief below still runs. A database failure still fails loudly.
The issue is pinned on first contact (GraphQL pinIssue; already pinned is
fine), so nothing about the issue has to be done by hand.

Env: ARBI_GITHUB_TOKEN (Issues RW), GITHUB_REPOSITORY (owner/repo, set by
Actions), ASXOS_DECISIONS_ISSUE (issue number), ASXOS_PERSONAL_USE=1 (the
decisions are personal investment content).

Usage:
    ASXOS_PERSONAL_USE=1 ARBI_GITHUB_TOKEN=… GITHUB_REPOSITORY=owner/repo \\
        ASXOS_DECISIONS_ISSUE=<n> python jobs/apply_github_decisions.py
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Final, Literal

from asxos.config import settings
from asxos.db import acquire, close_pool, init_pool
from asxos.domain.decision_engine import repository
from asxos.domain.decision_engine.delivery import (
    disposition_for,
    paper_intent_for,
    persist_disposition,
)
from asxos.domain.governance.github_commands import (
    DisposeCommand,
    IssueComment,
    PendingCommand,
    ThesisGovernanceCommand,
    marker_for,
    select_commands,
)
from asxos.domain.theses.service import approve_object, reject_object
from asxos.jobs._helpers import require_personal_use_job
from asxos.jobs.utils.job_monitor import JobMonitor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

JOB_NAME: Final[str] = "apply_github_decisions"
GITHUB_API: Final[str] = os.environ.get("GITHUB_API_URL", "https://api.github.com")
GITHUB_GRAPHQL: Final[str] = os.environ.get("GITHUB_GRAPHQL_URL", "https://api.github.com/graphql")
TOKEN_ENV: Final[str] = "ARBI_GITHUB_TOKEN"
ISSUE_ENV: Final[str] = "ASXOS_DECISIONS_ISSUE"
REPO_ENV: Final[str] = "GITHUB_REPOSITORY"
SIGNATURE: Final[str] = "— arbi (`jobs/apply_github_decisions.py`)"


class GitHubUnavailable(RuntimeError):
    """GitHub refused (4xx) or could not be reached — noted, never fatal to the brief."""


@dataclass(frozen=True)
class RepoRef:
    owner: str
    repo: str


class GitHubIssue:
    """The four calls the job needs, over urllib. Never logs the token."""

    def __init__(self, *, token: str, ref: RepoRef, issue_number: int) -> None:
        self._token = token
        self.ref = ref
        self.issue_number = issue_number

    def _request(self, method: str, url: str, payload: dict[str, Any] | None = None) -> Any:
        data = json.dumps(payload).encode() if payload is not None else None
        req = urllib.request.Request(
            url,
            data=data,
            method=method,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json",
                "User-Agent": "asxos-apply-github-decisions",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read().decode()
                return json.loads(body) if body else None
        except urllib.error.HTTPError as exc:
            if 400 <= exc.code < 500:
                raise GitHubUnavailable(f"{method} {url} -> HTTP {exc.code}") from exc
            raise
        except urllib.error.URLError as exc:
            raise GitHubUnavailable(f"{method} {url} -> {exc.reason}") from exc

    def owner_login(self) -> str:
        data = self._request("GET", f"{GITHUB_API}/repos/{self.ref.owner}/{self.ref.repo}")
        return str(data["owner"]["login"])

    def comments(self) -> list[IssueComment]:
        out: list[IssueComment] = []
        page = 1
        while True:
            batch = self._request(
                "GET",
                f"{GITHUB_API}/repos/{self.ref.owner}/{self.ref.repo}/issues/"
                f"{self.issue_number}/comments?per_page=100&page={page}",
            )
            if not batch:
                return out
            out.extend(
                IssueComment(
                    comment_id=int(c["id"]),
                    author_login=str((c.get("user") or {}).get("login") or ""),
                    body=str(c.get("body") or ""),
                )
                for c in batch
            )
            if len(batch) < 100:
                return out
            page += 1

    def post_comment(self, body: str) -> int:
        data = self._request(
            "POST",
            f"{GITHUB_API}/repos/{self.ref.owner}/{self.ref.repo}/issues/{self.issue_number}/comments",
            {"body": body},
        )
        return int(data["id"])

    def ensure_pinned(self) -> bool:
        """Pin the issue (GraphQL is the only API for it). True if this call pinned it."""
        node = self._request(
            "GET", f"{GITHUB_API}/repos/{self.ref.owner}/{self.ref.repo}/issues/{self.issue_number}"
        )
        if bool(node.get("pinned")):
            return False
        result = self._request(
            "POST",
            GITHUB_GRAPHQL,
            {
                "query": "mutation($id: ID!) { pinIssue(input: {issueId: $id}) { issue { id } } }",
                "variables": {"id": str(node["node_id"])},
            },
        )
        errors = (result or {}).get("errors") or []
        if errors and not any("already" in str(e.get("message", "")).lower() for e in errors):
            raise GitHubUnavailable(f"pinIssue refused: {errors[0].get('message', errors[0])}")
        return not errors


def repo_ref_from_env() -> RepoRef:
    raw = os.environ.get(REPO_ENV, "")
    owner, sep, repo = raw.partition("/")
    if not sep or not owner or not repo:
        raise RuntimeError(f"{REPO_ENV} must be owner/repo (got {raw!r})")
    return RepoRef(owner=owner, repo=repo)


def issue_number_from_env() -> int:
    raw = os.environ.get(ISSUE_ENV, "")
    if not raw.isdigit():
        raise RuntimeError(f"{ISSUE_ENV} must be the decisions issue number (got {raw!r})")
    return int(raw)


async def apply_one(conn: Any, pending: PendingCommand, *, recorded_at: datetime) -> str:
    """Apply a parsed command inside one transaction; returns the human line for the reply."""
    command = pending.command
    assert command is not None
    async with conn.transaction():
        if isinstance(command, ThesisGovernanceCommand):
            if command.action == "approve":
                thesis = await approve_object(conn, command.thesis_id, reasoning=command.reason)
            else:
                thesis = await reject_object(conn, command.thesis_id, reasoning=command.reason)
            return (
                f"thesis {thesis.thesis_id} ({thesis.symbol}) is now "
                f"`governance_status={thesis.governance_status}`"
            )
        assert isinstance(command, DisposeCommand)
        case = await repository.load_case(command.packet_id, conn=conn)
        note = command.note or f"disposed via GitHub comment {pending.comment.comment_id}"
        disposition = disposition_for(
            case, verdict=command.verdict, note=note, recorded_at=recorded_at
        )
        intent = paper_intent_for(case, disposition, created_at=recorded_at)
        await persist_disposition(conn, disposition)
        intent_line = (
            "no paper intent (non-action state or not accepted)"
            if intent is None
            else f"paper intent `{intent.intent_id}` (paper only — never an order)"
        )
        return f"disposition `{disposition.disposition_id}` recorded; {intent_line}"


def reply_body(pending: PendingCommand, *, applied: bool, detail: str) -> str:
    outcome: Literal["applied", "refused"] = "applied" if applied else "refused"
    head = "✅ Applied" if applied else "❌ Not applied"
    return (
        f"{marker_for(outcome, pending.comment.comment_id)}\n"
        f"{head} `{pending.summary}` — {detail}\n\n{SIGNATURE}"
    )


async def run(*, monitor: JobMonitor, github: GitHubIssue, recorded_at: datetime) -> dict[str, Any]:
    try:
        owner = github.owner_login()
        pinned_now = github.ensure_pinned()
        comments = github.comments()
    except GitHubUnavailable as exc:
        monitor.note = f"GitHub unavailable — no decisions read: {exc}"
        log.warning(monitor.note)
        return {"github": "unavailable", "error": str(exc), "applied": [], "refused": []}
    pending = select_commands(comments, owner_login=owner)
    applied: list[str] = []
    refused: dict[str, str] = {}
    async with acquire() as conn:
        for item in pending:
            key = f"{item.comment.comment_id}:{item.summary}"
            if item.error is not None:
                detail = f"syntax: {item.error}"
                refused[key] = detail
            else:
                try:
                    detail = await apply_one(conn, item, recorded_at=recorded_at)
                    applied.append(key)
                    monitor.rows_written = len(applied)
                except (ValueError, RuntimeError) as exc:
                    detail = f"{type(exc).__name__}: {exc}"
                    refused[key] = detail
            try:
                github.post_comment(reply_body(item, applied=item.error is None and key in applied, detail=detail))
            except GitHubUnavailable as exc:
                # The decision is in the database; the marker is not. The next run
                # would re-apply an approve (refused: not pending_review) or write a
                # second disposition, so say so loudly rather than continue.
                raise RuntimeError(
                    f"applied {item.summary} from comment {item.comment.comment_id} but could not "
                    f"post its marker reply ({exc}); post `{marker_for('applied', item.comment.comment_id)}` "
                    "on the issue by hand before the next run"
                ) from exc
    summary = {
        "issue": github.issue_number,
        "owner": owner,
        "pinned_now": pinned_now,
        "comments": len(comments),
        "pending": len(pending),
        "applied": applied,
        "refused": refused,
    }
    if refused:
        monitor.note = f"{len(refused)} command(s) refused: {json.dumps(refused)}"
    log.info("apply_github_decisions done — %s", json.dumps(summary))
    return summary


async def main() -> None:
    require_personal_use_job()
    token = os.environ.get(TOKEN_ENV, "")
    if not token:
        raise RuntimeError(f"{TOKEN_ENV} is not set")
    github = GitHubIssue(token=token, ref=repo_ref_from_env(), issue_number=issue_number_from_env())
    recorded_at = datetime.now(UTC)
    await init_pool()
    async with JobMonitor(
        job_name=JOB_NAME,
        as_of=recorded_at.date(),
        healthcheck_url=settings.healthcheck_url_apply_github_decisions,
    ) as monitor:
        await run(monitor=monitor, github=github, recorded_at=recorded_at)
    await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
