#!/usr/bin/env bash
# Idempotent dependency refresh for the asxos Cloud Agent environment.
# Runs after checkout with the repo root as CWD. Safe to re-run against a
# cached venv (creates it only when missing; pip install -e is a no-op refresh
# when nothing changed).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON_BIN="${ASXOS_PYTHON:-python3.12}"

if [ ! -x .venv/bin/python ]; then
  "$PYTHON_BIN" -m venv .venv
fi

# Build-time tooling only, deliberately unpinned: pyproject's build-system requires
# setuptools>=68 + wheel, and these never enter the resolved runtime set — every runtime
# dependency is pinned with `==` in pyproject.toml, which is what determines what installs.
.venv/bin/pip install --upgrade pip setuptools wheel
# Full install (ML + dev) — matches CI `full-check`: pip install -e ".[ml,dev]".
# uv.lock exists in the repo but pip does not read it; CI uses pip, so this does too.
.venv/bin/pip install -e ".[ml,dev]"

# Fail loudly if the core + ML import chain is broken (CLAUDE.md #1/#10).
.venv/bin/python -c "import fastapi, lightgbm, shap, sklearn; print('asxos deps OK')"

# Fail loudly if the container clock is not UTC. 25 files under jobs/ key their `as_of`
# rows off a naive date.today(); a non-UTC zone silently shifts that partition key
# relative to CI and the crons (see .cursor/Dockerfile).
.venv/bin/python - <<'PY'
import time
assert time.strftime("%Z") == "UTC", (
    f"container TZ is {time.strftime('%Z')!r}, expected 'UTC' — naive date.today() in "
    "jobs/ would write a shifted as_of key. Fix TZ in .cursor/Dockerfile."
)
print("asxos clock OK (UTC)")
PY
