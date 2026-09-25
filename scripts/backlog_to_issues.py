#!/usr/bin/env python
"""File the archived queue's currently-eligible arbi rows as GitHub issues.

    GH_TOKEN=… GITHUB_REPOSITORY=owner/repo python scripts/backlog_to_issues.py [--apply] [--limit 10]

``docs/product/backlog.yaml`` is the archive; GitHub Issues are the queue (AGENTS.md §11).
This is the bridge, run from an attended session a few rows at a time: every row
``asxos.backlog.eligible`` would have picked becomes one issue in the product form's
layout, carrying the arbi marker and ``Provenance: backlog:<id>`` so Layer 1 can resolve
it. A row already filed (an issue whose body cites ``backlog:<id>``) is skipped. The
default is a dry run that prints what it would file; ``--apply`` files it, ``needs-triage``
and ``type:product`` labelled, so the next eligibility pass judges it like any other.

The acceptance criteria are honest but thin — the YAML never carried Given/When/Then —
and arbi's readiness judgement (Layer 2) is expected to decline most of them until a
real criterion is written on the issue. That is the point: the queue moves to a place
where the criterion can be written and read on a phone.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

from asxos.backlog import DEFAULT_BACKLOG, Item, eligible, load
from asxos.domain.governance.issue_eligibility import ISSUE_AUTHOR_MARKER
from asxos.github_api import GitHubClient, GitHubUnavailable, repo_ref_from_env

LABELS = ["type:product", "needs-triage"]
_AREA_BY_PREFIX = (
    ("asxos/cli/", "cli"),
    ("jobs/", "cron"),
    ("asxos/brief/", "email"),
    ("migrations/", "db"),
    ("asxos/domain/screening/", "screens"),
)


def area_for(paths: tuple[str, ...]) -> str:
    for path in paths:
        for prefix, area in _AREA_BY_PREFIX:
            if path.startswith(prefix):
                return area
    return "pipeline"


def render_body(item: Item) -> str:
    files = "\n".join(f"`{p}`" for p in item.paths)
    depends = ", ".join(item.depends_on) or "none"
    sections = [
        ("Approval tier", "L2"),
        ("Area", area_for(item.paths)),
        (
            "Problem / outcome",
            f"{item.title} — so that backlog row `{item.id}` closes on evidence rather than being carried.",
        ),
        ("Files to touch (expected)", files),
        (
            "Acceptance criteria (Given/When/Then)",
            f"Given `main` at the picked commit\nWhen `{item.id}` is built as its source describes ({item.source})\nThen {item.title}",
        ),
        ("Out of scope", "Anything not named in Files to touch."),
        ("Depends on", depends),
        ("Provenance", f"backlog:{item.id}"),
    ]
    parts = [ISSUE_AUTHOR_MARKER, ""]
    for label, text in sections:
        parts += [f"### {label}", "", text, ""]
    return "\n".join(parts)


def already_filed(client: GitHubClient, item_id: str) -> int | None:
    hits = client.search_issues(f'repo:{client.ref.slug} is:issue "backlog:{item_id}" in:body')
    exact = re.compile(rf"backlog:{re.escape(item_id)}(?![\w-])")
    for hit in hits:
        if exact.search(str(hit.get("body") or "")):
            return int(hit["number"])
    return None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="backlog_to_issues", description=__doc__)
    ap.add_argument("--apply", action="store_true", help="file the issues (default: dry run)")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--backlog", type=Path, default=DEFAULT_BACKLOG)
    ns = ap.parse_args(argv)
    if not 1 <= ns.limit <= 10:
        print("backlog_to_issues: --limit must be between 1 and 10", file=sys.stderr)
        return 2

    token = os.environ.get("GH_TOKEN") or os.environ.get("ARBI_GITHUB_TOKEN") or ""
    if not token:
        print("backlog_to_issues: GH_TOKEN or ARBI_GITHUB_TOKEN is not set", file=sys.stderr)
        return 2
    client = GitHubClient(token=token, ref=repo_ref_from_env())

    items = load(ns.backlog)
    by_id = {item.id: item for item in items}
    rows = [item for item in items if eligible(item, by_id)][: ns.limit]
    out: list[dict[str, object]] = []
    try:
        for item in rows:
            existing = already_filed(client, item.id)
            if existing is not None:
                out.append({"id": item.id, "skipped": f"already filed as #{existing}"})
                continue
            title = f"{item.id}: {item.title}"
            body = render_body(item)
            if ns.apply:
                number = client.create_issue(title=title, body=body, labels=LABELS)
                out.append({"id": item.id, "filed": number})
            else:
                out.append({"id": item.id, "would_file": title})
    except GitHubUnavailable as exc:
        print(f"backlog_to_issues: GitHub unavailable: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"apply": ns.apply, "rows": out}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
