#!/usr/bin/env python
"""Post or update today's digest comment on the digest issue — model-free (AGENTS.md §12).

    GH_TOKEN=… GITHUB_REPOSITORY=owner/repo [ASXOS_DIGEST_ISSUE=271] \\
      python scripts/post_daily_digest.py [--dry-run]

Under ``scripts/`` rather than ``jobs/`` on purpose: it touches no database, so it has no
``JobMonitor`` row — its own comment on the issue is the heartbeat, and the workflow's
conclusion is the alarm. A shim: the logic is ``asxos/digest.py``.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from asxos import digest as dg
from asxos.clock import today
from asxos.github_api import GitHubClient, GitHubUnavailable, repo_ref_from_env


def _main_sha(root: Path) -> str:
    sha = os.environ.get("GITHUB_SHA", "")
    if not sha:
        proc = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        sha = proc.stdout.strip()
    return sha[:12] if sha else "unknown"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="post_daily_digest", description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="print the digest; post nothing")
    ap.add_argument("--root", type=Path, default=Path.cwd())
    ns = ap.parse_args(argv)

    token = os.environ.get("GH_TOKEN") or os.environ.get("ARBI_GITHUB_TOKEN") or ""
    if not token:
        print("post_daily_digest: GH_TOKEN or ARBI_GITHUB_TOKEN is not set", file=sys.stderr)
        return 2
    raw_issue = os.environ.get("ASXOS_DIGEST_ISSUE", str(dg.DIGEST_ISSUE_DEFAULT))
    if not raw_issue.isdigit():
        print(
            f"post_daily_digest: ASXOS_DIGEST_ISSUE must be a number (got {raw_issue!r})",
            file=sys.stderr,
        )
        return 2
    issue_number = int(raw_issue)
    ref = repo_ref_from_env()
    client = GitHubClient(token=token, ref=ref)
    run_id = os.environ.get("GITHUB_RUN_ID", "local")
    main_sha = _main_sha(ns.root)

    try:
        existing = dg.latest_digest(client.comments(issue_number))
        built = dg.build(
            client,
            slug=ref.slug,
            today=today(),
            previous=existing[1] if existing else None,
            repo_root=ns.root,
        )
        rendered = built.render(run_id=run_id, main=main_sha)
        uncited = dg.uncited_lines(rendered)
        if uncited:
            print(
                "post_daily_digest: refusing to post lines that cite nothing:",
                *uncited,
                sep="\n  ",
                file=sys.stderr,
            )
            return 1
        if ns.dry_run:
            print(rendered)
            return 0
        outcome = dg.publish(
            client,
            issue_number=issue_number,
            digest=built,
            run_id=run_id,
            main=main_sha,
            existing=existing,
        )
    except GitHubUnavailable as exc:
        print(f"post_daily_digest: GitHub unavailable: {exc}", file=sys.stderr)
        return 1
    print(f"{outcome} digest for {built.date} on #{issue_number} (window since {built.since})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
