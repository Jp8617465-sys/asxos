"""asxos/github_api.py — the one GitHub client, and the trust rule it carries."""

from __future__ import annotations

import io
import json
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from typing import Any, ClassVar
from unittest.mock import patch

import pytest

from asxos import github_api
from asxos.domain.governance.github_commands import IssueComment

OWNER = "Jp8617465-sys"
REF = github_api.RepoRef("Jp8617465-sys", "asxos")


class _Resp(io.BytesIO):
    headers: ClassVar[dict[str, str]] = {"content-type": "application/json"}

    def __enter__(self) -> Any:
        return self

    def __exit__(self, *a: Any) -> None:
        return None


def _http(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError("u", code, "m", {}, io.BytesIO(b""))  # type: ignore[arg-type]


class Routes:
    """A fake `urlopen`: routes by (method, path-with-query) to a JSON body or an error."""

    def __init__(self) -> None:
        self.table: dict[tuple[str, str], Any] = {}
        self.calls: list[urllib.request.Request] = []

    def add(self, method: str, url: str, body: Any) -> None:
        self.table[(method, url)] = body

    def __call__(self, req: urllib.request.Request, timeout: int) -> Any:
        self.calls.append(req)
        key = (req.get_method(), req.full_url)
        if key not in self.table:
            raise AssertionError(f"unexpected request {key}")
        body = self.table[key]
        if isinstance(body, Exception):
            raise body
        return _Resp(json.dumps(body).encode() if body is not None else b"")


def _client(routes: Routes, token: str = "t") -> tuple[github_api.GitHubClient, Callable[[], Any]]:
    return github_api.GitHubClient(token=token, ref=REF), lambda: patch.object(
        urllib.request, "urlopen", routes
    )


REPO = f"{github_api.GITHUB_API}/repos/Jp8617465-sys/asxos"


def test_owner_login_comes_from_the_repo_not_a_comment() -> None:
    routes = Routes()
    routes.add("GET", REPO, {"owner": {"login": OWNER}, "name": "asxos"})
    client, patched = _client(routes)
    with patched():
        assert client.owner_login() == OWNER
    assert [c.full_url for c in routes.calls] == [REPO]


def test_4xx_is_github_unavailable_5xx_raises_and_network_is_unavailable() -> None:
    client = github_api.GitHubClient(token="t", ref=REF)
    with (
        patch.object(urllib.request, "urlopen", side_effect=_http(403)),
        pytest.raises(github_api.GitHubUnavailable, match="403"),
    ):
        client.owner_login()
    with (
        patch.object(urllib.request, "urlopen", side_effect=_http(502)),
        pytest.raises(urllib.error.HTTPError),
    ):
        client.owner_login()
    with (
        patch.object(urllib.request, "urlopen", side_effect=urllib.error.URLError("dns")),
        pytest.raises(github_api.GitHubUnavailable, match="dns"),
    ):
        client.owner_login()


def test_token_is_a_bearer_header_and_never_appears_in_exception_text() -> None:
    routes = Routes()
    routes.add("GET", REPO, _http(404))
    client, patched = _client(routes, token="secret-token-value")
    with patched(), pytest.raises(github_api.GitHubUnavailable) as excinfo:
        client.owner_login()
    assert "secret-token-value" not in str(excinfo.value)
    assert routes.calls[0].get_header("Authorization") == "Bearer secret-token-value"
    assert routes.calls[0].get_header("User-agent") == "asxos-github-api"


def test_pagination_stops_on_a_short_page_and_drops_pull_requests() -> None:
    routes = Routes()
    page1 = [{"number": n, "title": f"i{n}"} for n in range(1, 101)]
    page1[3]["pull_request"] = {"url": "…"}
    page2 = [{"number": 101}, {"number": 102}, {"number": 103}]
    base = f"{REPO}/issues?state=open&labels=ready%2Ctype%3Aproduct"
    routes.add("GET", f"{base}&per_page=100&page=1", page1)
    routes.add("GET", f"{base}&per_page=100&page=2", page2)
    client, patched = _client(routes)
    with patched():
        rows = client.list_issues(labels=("ready", "type:product"))
    assert len(rows) == 102 and all("pull_request" not in r for r in rows)
    assert len(routes.calls) == 2


def test_comments_map_to_issue_comment_and_an_empty_page_ends_the_walk() -> None:
    routes = Routes()
    routes.add(
        "GET",
        f"{REPO}/issues/289/comments?per_page=100&page=1",
        [
            {"id": 7, "user": {"login": OWNER}, "body": "APPROVE thesis 1 ok"},
            {"id": 8, "user": None},
        ],
    )
    client, patched = _client(routes)
    with patched():
        assert client.comments(289) == [
            IssueComment(comment_id=7, author_login=OWNER, body="APPROVE thesis 1 ok"),
            IssueComment(comment_id=8, author_login="", body=""),
        ]


def test_search_issues_quotes_the_query_and_unwraps_items() -> None:
    routes = Routes()
    q = "repo:Jp8617465-sys/asxos is:pr is:merged merged:>=2026-09-24"
    url = f"{github_api.GITHUB_API}/search/issues?q={urllib.parse.quote(q)}&per_page=100&page=1"
    routes.add("GET", url, {"total_count": 1, "items": [{"number": 373}]})
    client, patched = _client(routes)
    with patched():
        assert client.search_issues(q) == [{"number": 373}]


def test_labels_are_added_as_a_batch_and_removal_tolerates_an_absent_label() -> None:
    routes = Routes()
    routes.add("POST", f"{REPO}/issues/5/labels", [{"name": "ready"}])
    routes.add("DELETE", f"{REPO}/issues/5/labels/needs-info", _http(404))
    routes.add("DELETE", f"{REPO}/issues/5/labels/type%3Aproduct", _http(403))
    client, patched = _client(routes)
    with patched():
        client.add_labels(5, ["ready"])
        client.add_labels(5, [])  # nothing to send, nothing sent
        client.remove_label(5, "needs-info")  # 404 → already absent
        with pytest.raises(github_api.GitHubUnavailable, match="403"):
            client.remove_label(5, "type:product")
    posted = [c for c in routes.calls if c.get_method() == "POST"]
    assert len(posted) == 1 and json.loads(posted[0].data) == {"labels": ["ready"]}


def test_update_comment_patches_and_workflow_runs_filter_by_created_and_event() -> None:
    routes = Routes()
    routes.add("PATCH", f"{REPO}/issues/comments/99", {"id": 99})
    runs_url = (
        f"{REPO}/actions/workflows/backlog-roll.yml/runs"
        f"?created=%3E%3D2026-09-24&event=schedule&per_page=100&page=1"
    )
    routes.add(
        "GET", runs_url, {"total_count": 1, "workflow_runs": [{"id": 1, "conclusion": "success"}]}
    )
    client, patched = _client(routes)
    with patched():
        client.update_comment(99, "new body")
        runs = client.workflow_runs(
            "backlog-roll.yml", created_since="2026-09-24", event="schedule"
        )
    assert runs == [{"id": 1, "conclusion": "success"}]
    patched_call = routes.calls[0]
    assert patched_call.get_method() == "PATCH" and json.loads(patched_call.data) == {
        "body": "new body"
    }


def test_ensure_pinned_is_a_no_op_when_already_pinned_and_pins_otherwise() -> None:
    routes = Routes()
    routes.add("GET", f"{REPO}/issues/271", {"pinned": True, "node_id": "X"})
    client, patched = _client(routes)
    with patched():
        assert client.ensure_pinned(271) is False

    routes = Routes()
    routes.add("GET", f"{REPO}/issues/271", {"pinned": False, "node_id": "X"})
    routes.add("POST", github_api.GITHUB_GRAPHQL, {"data": {"pinIssue": {"issue": {"id": "X"}}}})
    client, patched = _client(routes)
    with patched():
        assert client.ensure_pinned(271) is True


def test_create_issue_posts_title_body_labels_and_returns_the_number() -> None:
    routes = Routes()
    routes.add("POST", f"{REPO}/issues", {"number": 401, "title": "E-11: x"})
    client, patched = _client(routes)
    with patched():
        assert (
            client.create_issue(title="E-11: x", body="b", labels=("type:product", "needs-triage"))
            == 401
        )
        assert client.create_issue(title="no labels", body="b") == 401
    first, second = (json.loads(c.data) for c in routes.calls)
    assert first == {"title": "E-11: x", "body": "b", "labels": ["type:product", "needs-triage"]}
    assert second == {"title": "no labels", "body": "b"}


def test_env_helpers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(github_api.REPO_ENV, "Jp8617465-sys/asxos")
    assert github_api.repo_ref_from_env() == REF and REF.slug == "Jp8617465-sys/asxos"
    monkeypatch.setenv(github_api.REPO_ENV, "asxos")
    with pytest.raises(RuntimeError, match="owner/repo"):
        github_api.repo_ref_from_env()
    monkeypatch.delenv(github_api.TOKEN_ENV, raising=False)
    with pytest.raises(RuntimeError, match=github_api.TOKEN_ENV):
        github_api.token_from_env()
    monkeypatch.setenv(github_api.TOKEN_ENV, "x")
    assert github_api.token_from_env() == "x"
