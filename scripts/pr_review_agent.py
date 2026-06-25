#!/usr/bin/env python3
"""Comment-only PR and main-branch commit reviewer for GitHub Actions."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


GITHUB_API = os.environ.get("GITHUB_API_URL", "https://api.github.com")
OPENAI_API = os.environ.get("OPENAI_API_URL", "https://api.openai.com/v1/responses")
MARKER_PREFIX = "<!-- pr-review-agent:v1"


def log(message: str) -> None:
    print(message, flush=True)


def env(name: str, required: bool = True) -> str:
    value = os.environ.get(name, "")
    if required and not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def request_json(
    method: str,
    url: str,
    *,
    token: str | None = None,
    payload: dict[str, Any] | None = None,
    accept: str = "application/vnd.github+json",
) -> Any:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {
        "Accept": accept,
        "Content-Type": "application/json",
        "User-Agent": "pr-review-agent",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            body = response.read().decode("utf-8")
            if not body:
                return None
            if "json" in response.headers.get("content-type", ""):
                return json.loads(body)
            return body
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {url} failed with {exc.code}: {body}") from exc


def request_text(method: str, url: str, *, token: str, accept: str) -> str:
    headers = {
        "Accept": accept,
        "User-Agent": "pr-review-agent",
        "Authorization": f"Bearer {token}",
    }
    req = urllib.request.Request(url, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            return response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {url} failed with {exc.code}: {body}") from exc


def paged_github(path: str, token: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    page = 1
    while True:
        sep = "&" if "?" in path else "?"
        url = f"{GITHUB_API}{path}{sep}per_page=100&page={page}"
        batch = request_json("GET", url, token=token)
        if not batch:
            return items
        items.extend(batch)
        if len(batch) < 100:
            return items
        page += 1


def extract_response_text(response: dict[str, Any]) -> str:
    if isinstance(response.get("output_text"), str):
        return response["output_text"].strip()

    chunks: list[str] = []
    for item in response.get("output", []):
        for part in item.get("content", []):
            if part.get("type") == "output_text" and isinstance(part.get("text"), str):
                chunks.append(part["text"])
    return "\n".join(chunks).strip()


def truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 200] + "\n\n[Diff truncated for review size. Inspect the full diff in GitHub before merging.]"


def github_path(repo: str, path: str) -> str:
    owner_repo = urllib.parse.quote(repo, safe="/")
    return f"/repos/{owner_repo}{path}"


def has_existing_marker(comments: list[dict[str, Any]], marker: str) -> bool:
    return any(marker in (comment.get("body") or "") for comment in comments)


def openai_review(prompt: str) -> str:
    api_key = env("OPENAI_API_KEY")
    model = os.environ.get("OPENAI_MODEL") or "gpt-5.2"
    payload = {
        "model": model,
        "instructions": (
            "You are a senior code reviewer for production repositories. "
            "Write concise, high-signal GitHub commentary. Only comment; do not approve, "
            "request changes, or claim checks have passed. Prioritize correctness, security, "
            "auth and permissions, data exposure, API/schema compatibility, migrations, "
            "missing tests, and rollout risk. Avoid style-only findings and avoid repeating "
            "generic linter advice. If there are no meaningful findings, say so briefly."
        ),
        "input": prompt,
        "max_output_tokens": 1600,
        "store": False,
    }
    response = request_json("POST", OPENAI_API, token=api_key, payload=payload, accept="application/json")
    text = extract_response_text(response)
    if not text:
        raise RuntimeError("OpenAI response did not include review text.")
    return text


def build_pr_prompt(repo: str, event: dict[str, Any], diff: str) -> str:
    pr = event["pull_request"]
    max_chars = int(os.environ.get("REVIEW_MAX_DIFF_CHARS", "60000"))
    return f"""Review this pull request and produce one top-level GitHub comment.

Repository: {repo}
PR: #{pr["number"]} {pr.get("title", "")}
Author: {pr.get("user", {}).get("login", "unknown")}
Base branch: {pr.get("base", {}).get("ref", "unknown")}
Head branch: {pr.get("head", {}).get("ref", "unknown")}
Head SHA: {pr.get("head", {}).get("sha", "unknown")}
Body:
{pr.get("body") or "(no description)"}

Required format:
## Automated Review

**Verdict:** Needs attention | Looks good with notes | No blocking issues found

**Highest-risk areas**
- ...

**Findings**
1. [Severity] File/path:line - Issue and why it matters.
   Suggested fix: ...

**Tests to add or verify**
- ...

**Release notes / rollout**
- ...

Changed diff:
```diff
{truncate(diff, max_chars)}
```
"""


def build_push_prompt(repo: str, event: dict[str, Any], diff: str) -> str:
    max_chars = int(os.environ.get("REVIEW_MAX_DIFF_CHARS", "60000"))
    commits = event.get("commits", [])
    commit_lines = "\n".join(
        f"- {commit.get('id', '')[:12]} {commit.get('message', '').splitlines()[0]}"
        for commit in commits
    )
    return f"""Review these direct commits to the main branch and produce one GitHub commit comment.

Repository: {repo}
Branch: {event.get("ref", "")}
Before: {event.get("before", "")}
After: {event.get("after", "")}
Pusher: {event.get("pusher", {}).get("name", "unknown")}
Commits:
{commit_lines or "(no commit metadata)"}

Required format:
## Automated Main-Branch Commit Review

**Verdict:** Needs attention | Looks good with notes | No blocking issues found

**Highest-risk areas**
- ...

**Findings**
1. [Severity] File/path:line - Issue and why it matters.
   Suggested fix: ...

**Tests to add or verify**
- ...

Changed diff:
```diff
{truncate(diff, max_chars)}
```
"""


def comment_on_pr(repo: str, pr_number: int, body: str, token: str) -> None:
    path = github_path(repo, f"/issues/{pr_number}/comments")
    request_json("POST", f"{GITHUB_API}{path}", token=token, payload={"body": body})


def comment_on_commit(repo: str, sha: str, body: str, token: str) -> None:
    path = github_path(repo, f"/commits/{sha}/comments")
    request_json("POST", f"{GITHUB_API}{path}", token=token, payload={"body": body})


def review_pull_request(repo: str, event: dict[str, Any], github_token: str) -> None:
    pr = event["pull_request"]
    number = int(pr["number"])
    head_sha = pr.get("head", {}).get("sha", "")
    marker = f"{MARKER_PREFIX} repo={repo} pr={number} head={head_sha} -->"

    comments = paged_github(github_path(repo, f"/issues/{number}/comments"), github_token)
    if has_existing_marker(comments, marker):
        log(f"Review comment already exists for PR #{number} at {head_sha}; skipping.")
        return

    diff_url = f"{GITHUB_API}{github_path(repo, f'/pulls/{number}')}"
    diff = request_text("GET", diff_url, token=github_token, accept="application/vnd.github.v3.diff")
    review = openai_review(build_pr_prompt(repo, event, diff))
    body = f"{marker}\n{review}\n\n_Comment-only automated review._"
    comment_on_pr(repo, number, body[:65000], github_token)
    log(f"Posted review comment on PR #{number}.")


def review_push(repo: str, event: dict[str, Any], github_token: str) -> None:
    before = event.get("before")
    after = event.get("after")
    if not before or not after or set(after) == {"0"}:
        log("Push event has no comparable commit range; skipping.")
        return

    marker = f"{MARKER_PREFIX} repo={repo} commit={after} -->"
    comments = paged_github(github_path(repo, f"/commits/{after}/comments"), github_token)
    if has_existing_marker(comments, marker):
        log(f"Review comment already exists for commit {after}; skipping.")
        return

    compare_path = github_path(repo, f"/compare/{before}...{after}")
    diff = request_text(
        "GET",
        f"{GITHUB_API}{compare_path}",
        token=github_token,
        accept="application/vnd.github.v3.diff",
    )
    review = openai_review(build_push_prompt(repo, event, diff))
    body = f"{marker}\n{review}\n\n_Comment-only automated review for a direct push to main._"
    comment_on_commit(repo, after, body[:65000], github_token)
    log(f"Posted review comment on commit {after}.")


def main() -> int:
    if not os.environ.get("OPENAI_API_KEY"):
        log("OPENAI_API_KEY secret is not configured; skipping automated review.")
        return 0

    event_name = env("GITHUB_EVENT_NAME")
    event_path = env("GITHUB_EVENT_PATH")
    repo = env("GITHUB_REPOSITORY")
    github_token = env("GITHUB_TOKEN")

    with open(event_path, "r", encoding="utf-8") as handle:
        event = json.load(handle)

    if event_name == "pull_request":
        review_pull_request(repo, event, github_token)
    elif event_name == "push":
        review_push(repo, event, github_token)
    else:
        log(f"Unsupported event {event_name}; skipping.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"::error::{exc}", file=sys.stderr)
        raise
