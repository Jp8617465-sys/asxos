# Quality Check

Run the asxos quality gates in sequence. Stop on the first failure and
report which gate failed.

## Gates

1. `ruff check asxos tests jobs` — lint
2. `ruff format --check asxos tests jobs` — formatting
3. `mypy asxos` — types
4. `pytest tests/ -v` — full suite

Equivalent shortcut: `make check` (runs ruff + mypy + pytest in that order).

## Rules

- Run each command, capture output, report PASS or FAIL with the error summary
- Stop immediately on first failure
- If all 4 pass: **All quality gates passed. Ready for `/ship` or push to main.**
- If any fail: **Gate N failed.** + first 20 lines of error, then stop

## Auto-fix option

If `$ARGUMENTS` contains `--fix`:
- Run `ruff check --fix asxos tests jobs`
- Run `ruff format asxos tests jobs`
- Then re-run all gates from gate 1

## Known stale lints (not blocking)

The following are pre-existing from M5 — track but don't fail on:
- `asxos/domain/signals/feature_engine.py:48` — `Union[...]` UP007 nit
- `asxos/domain/signals/feature_engine.py:60` — RUF002 ambiguous `×`
- `asxos/domain/signals/feature_engine.py:68/74` — RUF012 ClassVar

If $ARGUMENTS contains `--strict`, fail on these too.
