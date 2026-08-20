.PHONY: help install dev decision-demo test lint type format check migrate shell logs deploy check-drift clean

PY ?= /usr/local/bin/python3.12
VENV ?= .venv
ACTIVATE = source $(VENV)/bin/activate

help:  ## Show this help
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

$(VENV)/bin/activate:
	$(PY) -m venv $(VENV)
	$(VENV)/bin/pip install --upgrade pip
	$(VENV)/bin/pip install -e ".[dev]"

install: $(VENV)/bin/activate  ## Create venv and install core + dev deps (no ML)

install-ml:  ## Add ML deps (lightgbm, shap, sklearn) — requires LLVM
	$(VENV)/bin/pip install -e ".[ml]"

dev:  ## Run the API at 127.0.0.1:8788 with reload
	$(VENV)/bin/python -m uvicorn asxos.api.main:app --host 127.0.0.1 --port 8788 --reload

decision-demo:  ## Run the read-only target-architecture cockpit at 127.0.0.1:8790
	$(VENV)/bin/python -m uvicorn asxos.prototype.app:app --host 127.0.0.1 --port 8790 --reload

migrate:  ## Reminder: migrations are applied via Supabase MCP, not this target
	@echo "Migrations are applied via Claude Code using mcp__supabase__apply_migration."
	@echo "Ask Claude Code: 'apply migration 00NN to the asxos Supabase project'."
	@echo "For offline docker-compose dev: psql \$$DATABASE_URL -f migrations/00NN_*.sql"

test:  ## Run pytest
	$(VENV)/bin/pytest

lint:  ## Run ruff lint
	$(VENV)/bin/ruff check .

type:  ## Run mypy type check
	$(VENV)/bin/mypy asxos

format:  ## Run ruff format
	$(VENV)/bin/ruff format .

check: lint type test  ## Run all quality gates

install-hooks:  ## Activate the tracked git pre-push gate (ruff + mypy)
	git config core.hooksPath scripts/hooks
	@echo "core.hooksPath -> scripts/hooks. Pre-push runs ruff + mypy."
	@echo "Set RUN_TESTS=1 to also run pytest on push; bypass with 'git push --no-verify'."

shell:  ## Start a Python REPL with asxos importable
	$(VENV)/bin/python

logs:  ## Show recent GitHub Actions job logs
	@echo "Jobs run as GitHub Actions (Render deleted 2026-08-12). Use: gh run list  and  gh run view <run-id> --log."

deploy:  ## No Render deploy; jobs are GitHub Actions
	@echo "There is no Render deploy step (Render deleted 2026-08-12). Job config lives in .github/workflows/ and updates on merge to main."
	@echo "Dispatch a run with: gh workflow run <name>.yml"

check-drift:  ## (deprecated) Render is gone; config lives in .github/workflows
	@echo "Deprecated: Render was deleted 2026-08-12. No drift target — .github/workflows/ is the source of truth."

clean:  ## Remove caches
	rm -rf .pytest_cache .ruff_cache .mypy_cache __pycache__
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
