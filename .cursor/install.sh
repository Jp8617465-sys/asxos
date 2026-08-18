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

.venv/bin/pip install --upgrade pip setuptools wheel
# Full install (ML + dev) — matches CI `full-check`: pip install -e ".[ml,dev]".
.venv/bin/pip install -e ".[ml,dev]"

# Fail loudly if the core + ML import chain is broken (CLAUDE.md #1/#10).
.venv/bin/python -c "import fastapi, lightgbm, shap, sklearn; print('asxos deps OK')"
