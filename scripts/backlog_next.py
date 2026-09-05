#!/usr/bin/env python3
"""CLI shim over ``asxos.backlog`` — the pre-gate for the ``backlog-roll`` lane.

Same shape as ``check_migration_drift.py``: the logic lives in ``asxos/backlog.py`` so it
is importable and mypy-checked; this file only parses argv and exits.

Exit codes: 0 picked at least one item · 2 schema error · 3 nothing eligible
(the click-list is still printed — that is the lane's primary product).
"""

from __future__ import annotations

import sys

from asxos.backlog import main

if __name__ == "__main__":
    sys.exit(main())
