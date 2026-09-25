"""One GitHub REST client for every job and script that talks to this repository.

Extracted from ``jobs/apply_github_decisions.py`` once a second consumer (the issue
loop: eligibility, readiness, the picker, the digest) needed the same trust
primitive. The trust rule lives here and nowhere else: **the owner's login comes
from the repository record** (``GET /repos/{owner}/{repo}``), never from a comment,
a label event or an issue body. Every caller that decides "may this actor direct
me?" compares against :meth:`GitHubClient.owner_login`.

Design constraints carried over unchanged:

* ``urllib`` only — no ``requests`` dependency for ~150 lines.
* A 4xx or an unreachable API is :class:`GitHubUnavailable`, which callers treat as
  "GitHub is not this pipeline's dependency" (note it, exit 0). A 5xx propagates:
  that is GitHub failing, not us being refused.
* The token is sent as a Bearer header and never logged or embedded in an
  exception message.
* Pagination is ``per_page=100``; a short page ends the walk.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any, Final

from asxos.domain.governance.github_commands import IssueComment

GITHUB_API: Final[str] = os.environ.get("GITHUB_API_URL", "https://api.github.com")
GITHUB_GRAPHQL: Final[str] = os.environ.get("GITHUB_GRAPHQL_URL", "https://api.github.com/graphql")
REPO_ENV: Final[str] = "GITHUB_REPOSITORY"
TOKEN_ENV: Final[str] = "ARBI_GITHUB_TOKEN"
PER_PAGE: Final[int] = 100
_TIMEOUT_S: Final[int] = 30


class GitHubUnavailable(RuntimeError):
    """GitHub refused (4xx) or could not be reached — noted by callers, never fatal."""


@dataclass(frozen=True)
class RepoRef:
    owner: str
    repo: str

    @property
    def slug(self) -> str:
        return f"{self.owner}/{self.repo}"


class GitHubClient:
    """The REST calls the repo's jobs need, over urllib. Never logs the token."""

    def __init__(self, *, token: str, ref: RepoRef, user_agent: str = "asxos-github-api") -> None:
        self._token = token
        self.ref = ref
        self._user_agent = user_agent

    # --- transport ------------------------------------------------------------------

    def _request(
        self,
        method: str,
        url: str,
        payload: dict[str, Any] | None = None,
        *,
        tolerate: frozenset[int] = frozenset(),
    ) -> Any:
        data = json.dumps(payload).encode() if payload is not None else None
        req = urllib.request.Request(
            url,
            data=data,
            method=method,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json",
                "User-Agent": self._user_agent,
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=_TIMEOUT_S) as resp:
                body = resp.read().decode()
                return json.loads(body) if body else None
        except urllib.error.HTTPError as exc:
            if exc.code in tolerate:
                return None
            if 400 <= exc.code < 500:
                raise GitHubUnavailable(f"{method} {url} -> HTTP {exc.code}") from exc
            raise
        except urllib.error.URLError as exc:
            raise GitHubUnavailable(f"{method} {url} -> {exc.reason}") from exc

    def _paged(self, url: str, *, key: str | None = None) -> list[Any]:
        """Walk ``per_page=100`` pages until a short or empty page. ``key`` unwraps
        envelope responses (``{"items": [...]}``, ``{"workflow_runs": [...]}``)."""
        joiner = "&" if "?" in url else "?"
        out: list[Any] = []
        page = 1
        while True:
            batch = self._request("GET", f"{url}{joiner}per_page={PER_PAGE}&page={page}")
            rows = (batch or {}).get(key) if key else batch
            rows = rows or []
            out.extend(rows)
            if len(rows) < PER_PAGE:
                return out
            page += 1

    def _repo_url(self, tail: str) -> str:
        return f"{GITHUB_API}/repos/{self.ref.owner}/{self.ref.repo}{tail}"

    # --- repository ----------------------------------------------------------------------

    def owner_login(self) -> str:
        """The one login allowed to direct the loop — read from the repository, never a comment."""
        data = self._request("GET", self._repo_url(""))
        return str(data["owner"]["login"])

    # --- issues ---------------------------------------------------------------------------

    def issue(self, number: int) -> dict[str, Any]:
        return dict(self._request("GET", self._repo_url(f"/issues/{number}")))

    def create_issue(self, *, title: str, body: str, labels: Sequence[str] = ()) -> int:
        payload: dict[str, Any] = {"title": title, "body": body}
        if labels:
            payload["labels"] = [str(label) for label in labels]
        data = self._request("POST", self._repo_url("/issues"), payload)
        return int(data["number"])

    def list_issues(
        self, *, labels: Sequence[str] = (), state: str = "open"
    ) -> list[dict[str, Any]]:
        """Issues only — the REST endpoint also returns pull requests, which are dropped."""
        query = f"state={urllib.parse.quote(state)}"
        if labels:
            query += "&labels=" + urllib.parse.quote(",".join(labels))
        rows = self._paged(self._repo_url(f"/issues?{query}"))
        return [dict(r) for r in rows if "pull_request" not in r]

    def search_issues(self, query: str) -> list[dict[str, Any]]:
        """``GET /search/issues`` — the query is quoted; ``repo:`` scoping is the caller's."""
        url = f"{GITHUB_API}/search/issues?q={urllib.parse.quote(query)}"
        return [dict(r) for r in self._paged(url, key="items")]

    def comments(self, number: int) -> list[IssueComment]:
        rows = self._paged(self._repo_url(f"/issues/{number}/comments"))
        return [
            IssueComment(
                comment_id=int(c["id"]),
                author_login=str((c.get("user") or {}).get("login") or ""),
                body=str(c.get("body") or ""),
            )
            for c in rows
        ]

    def post_comment(self, number: int, body: str) -> int:
        data = self._request("POST", self._repo_url(f"/issues/{number}/comments"), {"body": body})
        return int(data["id"])

    def update_comment(self, comment_id: int, body: str) -> None:
        self._request("PATCH", self._repo_url(f"/issues/comments/{comment_id}"), {"body": body})

    def add_labels(self, number: int, labels: Iterable[str]) -> None:
        names = [str(label) for label in labels]
        if names:
            self._request("POST", self._repo_url(f"/issues/{number}/labels"), {"labels": names})

    def remove_label(self, number: int, label: str) -> None:
        """Idempotent: a label that is already absent (404) is not an error."""
        self._request(
            "DELETE",
            self._repo_url(f"/issues/{number}/labels/{urllib.parse.quote(label, safe='')}"),
            tolerate=frozenset({404}),
        )

    def labels(self) -> list[dict[str, Any]]:
        return [dict(r) for r in self._paged(self._repo_url("/labels"))]

    def create_label(self, name: str, color: str, description: str) -> None:
        self._request(
            "POST",
            self._repo_url("/labels"),
            {"name": name, "color": color, "description": description},
        )

    def timeline(self, number: int) -> list[dict[str, Any]]:
        """Label events carry the ``actor`` that applied them — Layer 4's evidence."""
        return [dict(r) for r in self._paged(self._repo_url(f"/issues/{number}/timeline"))]

    def ensure_pinned(self, number: int) -> bool:
        """Pin the issue (GraphQL is the only API for it). True if this call pinned it."""
        node = self._request("GET", self._repo_url(f"/issues/{number}"))
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

    # --- pull requests and runs -------------------------------------------------------

    def list_pulls(self, *, state: str = "open") -> list[dict[str, Any]]:
        return [
            dict(r)
            for r in self._paged(self._repo_url(f"/pulls?state={urllib.parse.quote(state)}"))
        ]

    def pull_files(self, number: int) -> list[dict[str, Any]]:
        return [dict(r) for r in self._paged(self._repo_url(f"/pulls/{number}/files"))]

    def workflow_runs(
        self,
        workflow_file: str,
        *,
        created_since: str | None = None,
        event: str | None = None,
    ) -> list[dict[str, Any]]:
        """Runs of one workflow file, newest first. ``created_since`` is ``YYYY-MM-DD``."""
        params: list[str] = []
        if created_since:
            params.append("created=" + urllib.parse.quote(f">={created_since}", safe=""))
        if event:
            params.append("event=" + urllib.parse.quote(event))
        tail = f"/actions/workflows/{urllib.parse.quote(workflow_file)}/runs"
        if params:
            tail += "?" + "&".join(params)
        return [dict(r) for r in self._paged(self._repo_url(tail), key="workflow_runs")]


def repo_ref_from_env() -> RepoRef:
    raw = os.environ.get(REPO_ENV, "")
    owner, sep, repo = raw.partition("/")
    if not sep or not owner or not repo:
        raise RuntimeError(f"{REPO_ENV} must be owner/repo (got {raw!r})")
    return RepoRef(owner=owner, repo=repo)


def token_from_env(name: str = TOKEN_ENV) -> str:
    token = os.environ.get(name, "")
    if not token:
        raise RuntimeError(f"{name} is not set")
    return token
