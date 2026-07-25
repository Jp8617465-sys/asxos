# Twelve-hour mission prompt

**Contract version:** 1.0

Execute one approved ASXOS investment-engine mission in a **twelve-hour window**.
Use this only where the sprint contract names two truly independent implementation
lanes or separates a product change from required evidence/operations work.

## Hard envelope

- Maximum **two product PRs plus one evidence/operations PR**.
- Maximum **two implementation lanes**, with disjoint file ownership.
- No new scope after **T+06:00**.
- Implementation/content freeze at **T+10:00**.
- Test the integrated head and finish with a clean combined worktree.

The three-PR limit is a ceiling, not a target. One coherent PR is preferred.

## Routing and boundaries

- Opus/Ultra owns architecture, financial/tax/accounting semantics, migrations,
  capital boundaries, integration arbitration, and red-team review.
- Fable-low implements a frozen contract and may own tests, adapters, and rendering.
- After two failed Fable repair cycles on the same acceptance failure, freeze and
  escalate with evidence.
- James-only/no broker execution and zero Model A in the capital path are circuit
  breakers.
- AI research/review is qualitative; risk, tax, cost, evaluation, and sizing are
  deterministic.
- Missing/stale evidence fails closed. Use the roadmap's exact evidence ceiling:
  every implementation sprint, S01–S12, is `PAPER_ONLY`. Only a later immutable
  operational-gate decision over the frozen final lineage may permit
  `UNCALIBRATED`.

Copy `mission-template.yaml` to
`docs/programs/investment-engine/missions/SXX/MXX/mission.yaml`, using the next
unused mission ID in the sprint; never edit the template or overwrite a prior
mission. Close at
`docs/programs/investment-engine/missions/SXX/MXX/close.md`.

## Fresh-shell gate

```bash
PYTHON_312="${PYTHON_312:-$(command -v python3.12 || true)}"
test -x "$PYTHON_312"
"$PYTHON_312" -c 'import sys; assert sys.version_info[:2] == (3, 12)'
test -x .venv/bin/python || make install PY="$PYTHON_312"
.venv/bin/python -c 'import sys; assert sys.version_info[:2] == (3, 12)'
.venv/bin/python scripts/validate_investment_program.py
```

Run tests as `.venv/bin/python -m pytest ...`; do not use shell-global
`python` or `pytest`.

## Clock

| Time | Required state |
|---|---|
| T+00:00–00:45 | Verify authority, baseline, schema/deploy state, dependencies, exact ownership, PR graph, and acceptance. Return START VERDICT. |
| T+00:45–02:00 | Opus/Ultra freezes shared contracts, migration/forward recovery, and integration fixtures. |
| T+02:00–06:00 | Up to two disjoint lanes implement. Integrate continuously against frozen contracts. |
| T+06:00 | Scope cutoff. Reject additions and remove optional work that threatens the freeze. |
| T+06:00–08:30 | Complete product PRs and targeted tests. Evidence/ops PR may document or instrument only the approved outcome. |
| T+08:30–10:00 | Integrate all PRs; run migrations in a safe target; exercise stale/failure/rollback paths. |
| T+10:00 | Freeze. No feature implementation after this point. |
| T+10:00–11:15 | Opus/Ultra red-team; run combined `make check`/CI, replay, security/boundary, and drift checks. |
| T+11:15–12:00 | Attach evidence, verify PR ceiling and clean worktree, record residual risks and CLOSE VERDICT. |

If lane ownership overlaps, pause the second lane and resolve the plan; do not merge
through the conflict. If the integrated head is not clean and passing at T+10:00,
reduce to the last coherent reversible slice or return `NOT READY`.
