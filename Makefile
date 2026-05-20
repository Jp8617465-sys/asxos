.PHONY: help install dev test lint type format check migrate shell logs deploy check-drift clean

PY ?= python3.12
VENV ?= .venv
ACTIVATE = source $(VENV)/bin/activate

help:  ## Show this help
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

$(VENV)/bin/activate:
	$(PY) -m venv $(VENV)
	$(VENV)/bin/pip install --upgrade pip
	$(VENV)/bin/pip install -e ".[dev]"

install: $(VENV)/bin/activate  ## Create venv and install deps

dev:  ## Run the API at 127.0.0.1:8788 with reload
	$(VENV)/bin/python -m uvicorn asxos.api.main:app --host 127.0.0.1 --port 8788 --reload

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

shell:  ## Start a Python REPL with asxos importable
	$(VENV)/bin/python

logs:  ## Tail the Render service logs via MCP (asks Claude Code)
	@echo "Ask Claude Code: 'tail the last 100 lines of logs from asxos-api via Render MCP'."

deploy:  ## Push to main; Render auto-deploys
	@echo "Pushing to main. Render will auto-deploy on push."
	git push origin main
	@echo ""
	@echo "Then ask Claude Code: 'run check-drift against the asxos-api Render service'."

check-drift:  ## Compare render.yaml to deployed Render state via MCP
	@echo "Ask Claude Code: 'use the Render MCP to compare actual deployed services and crons against render.yaml. Report any drift.'"

clean:  ## Remove caches
	rm -rf .pytest_cache .ruff_cache .mypy_cache __pycache__
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
