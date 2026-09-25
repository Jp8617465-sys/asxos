#!/usr/bin/env python
"""Layer 4 — pick the next `ready` issues this fire may build. Shim over asxos/backlog_issues.py.

    GH_TOKEN=… GITHUB_REPOSITORY=owner/repo python scripts/issue_next.py --max 1 > backlog-pick.json

Exit 0 picked at least one · 2 error · 3 nothing to build.
"""

from __future__ import annotations

import sys

from asxos.backlog_issues import main

if __name__ == "__main__":
    sys.exit(main())
