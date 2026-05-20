# Quality Check

Run all quality gates in sequence. Stop on the first failure and report which gate failed.

## Frontend gates (run first)

1. `cd frontend && npm run type-check`
2. `cd frontend && npm run lint`
3. `cd frontend && npm run format:check`
4. `cd frontend && npm run test:ci`

## Backend gates

5. `black --check app/ jobs/`
6. `isort --check app/ jobs/`
7. `pytest tests/ -v`

## Rules

- Run each command, capture output, report PASS or FAIL with any error summary
- Stop immediately on first failure — do not continue to the next gate
- If all 7 pass, output: **All quality gates passed. Ready for /harden.**
- If any fail, output: **Gate N failed.** + the error, then stop

## Auto-fix option

If $ARGUMENTS contains `--fix`:
- Run `cd frontend && npm run lint -- --fix` and `cd frontend && npm run format` before the gate checks
- Run `black app/ jobs/` and `isort app/ jobs/` before the gate checks
- Then re-run all gates
