#!/usr/bin/env python
"""Apply arbi's readiness verdicts under the brakes — Layer 3, no model in the loop.

    AUTO_READY=on AUTO_READY_DAILY_CAP=3 AUTO_READY_WIP_LIMIT=2 \\
      GH_TOKEN=… GITHUB_REPOSITORY=owner/repo python scripts/issue_ready_apply.py

Reads ``.readiness-verdicts.json`` (the agent step's output) and ``.eligible-issues.json``
(the eligibility step's), refuses any verdict for an issue outside that run's eligible
set, and applies the rest: halt → AUTO_READY → daily cap → WIP limit. Prints the report.
Exit 0 on success, 1 when GitHub refuses, 2 when the verdicts file is malformed.
A shim: the logic is ``asxos/autoready.py``.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from asxos import autoready
from asxos.clock import today
from asxos.github_api import GitHubClient, GitHubUnavailable, repo_ref_from_env


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="issue_ready_apply", description=__doc__)
    ap.add_argument("--verdicts", type=Path, default=Path(autoready.VERDICTS_FILE))
    ap.add_argument("--eligible", type=Path, default=Path(autoready.ELIGIBLE_FILE))
    ns = ap.parse_args(argv)

    token = os.environ.get("GH_TOKEN") or os.environ.get("ARBI_GITHUB_TOKEN") or ""
    if not token:
        raise SystemExit("GH_TOKEN or ARBI_GITHUB_TOKEN is not set")
    try:
        verdicts = autoready.load_verdicts(ns.verdicts)
        eligible = autoready.eligible_from_file(ns.eligible)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"issue_ready_apply: {exc}", file=sys.stderr)
        return 2

    client = GitHubClient(token=token, ref=repo_ref_from_env())
    try:
        report = autoready.apply_readiness(
            client,
            verdicts=verdicts,
            eligible=eligible,
            brakes=autoready.brakes_from_env(),
            run_id=os.environ.get("GITHUB_RUN_ID", "local"),
            date=today().isoformat(),
        )
    except GitHubUnavailable as exc:
        print(f"issue_ready_apply: GitHub unavailable: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report.as_dict(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
