#!/usr/bin/env python
"""Layer 1 over the open issues — the lane's first step, no model in the loop.

    GH_TOKEN|ARBI_GITHUB_TOKEN=… GITHUB_REPOSITORY=owner/repo python scripts/issue_eligibility.py [--apply]

Without ``--apply`` it reads and reports; with it, labels and marker comments are
written. Either way ``.eligible-issues.json`` is produced for the readiness step. Exit 0
on success, 1 when GitHub refuses. A shim: the logic is ``asxos/autoready.py``.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from asxos import autoready
from asxos.github_api import GitHubClient, GitHubUnavailable, repo_ref_from_env


def _token() -> str:
    token = os.environ.get("GH_TOKEN") or os.environ.get("ARBI_GITHUB_TOKEN") or ""
    if not token:
        raise SystemExit("GH_TOKEN or ARBI_GITHUB_TOKEN is not set")
    return token


class _ReadOnly:
    """Wraps the client so a dry run reports what it would do and writes nothing."""

    def __init__(self, client: GitHubClient) -> None:
        self._client = client
        self.would: list[str] = []

    def __getattr__(self, name: str):  # pass-through proxy; writes are recorded, not sent
        if name in {"post_comment", "add_labels", "remove_label", "create_label"}:

            def _record(*args: object, **kwargs: object) -> int:
                self.would.append(f"{name}{args}")
                return 0

            return _record
        return getattr(self._client, name)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="issue_eligibility", description=__doc__)
    ap.add_argument("--apply", action="store_true", help="write labels and marker comments")
    ap.add_argument("--root", type=Path, default=Path.cwd())
    ap.add_argument("--out", type=Path, default=Path(autoready.ELIGIBLE_FILE))
    ns = ap.parse_args(argv)

    real = GitHubClient(token=_token(), ref=repo_ref_from_env())
    client = real if ns.apply else _ReadOnly(real)
    run_id = os.environ.get("GITHUB_RUN_ID", "local")
    try:
        report = autoready.eligibility_pass(
            client, run_id=run_id, repo_root=ns.root, write_to=ns.out
        )  # type: ignore[arg-type]
    except GitHubUnavailable as exc:
        print(f"issue_eligibility: GitHub unavailable: {exc}", file=sys.stderr)
        return 1
    summary = report.as_dict()
    if not ns.apply:
        summary["would"] = client.would  # type: ignore[attr-defined]
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
