#!/usr/bin/env python
"""Create the build loop's labels that do not exist yet. Idempotent; never edits.

GH_TOKEN=… GITHUB_REPOSITORY=owner/repo python scripts/ensure_labels.py
"""

from __future__ import annotations

import json
import os
import sys

from asxos import autoready
from asxos.github_api import GitHubClient, GitHubUnavailable, repo_ref_from_env


def main() -> int:
    token = os.environ.get("GH_TOKEN") or os.environ.get("ARBI_GITHUB_TOKEN") or ""
    if not token:
        raise SystemExit("GH_TOKEN or ARBI_GITHUB_TOKEN is not set")
    client = GitHubClient(token=token, ref=repo_ref_from_env())
    try:
        created = autoready.ensure_labels(client)
    except GitHubUnavailable as exc:
        print(f"ensure_labels: GitHub unavailable: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"created": created, "known": sorted(autoready.LABELS)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
