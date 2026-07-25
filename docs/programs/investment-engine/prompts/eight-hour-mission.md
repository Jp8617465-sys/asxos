# Eight-hour mission prompt

**Contract version:** 1.0

Execute one bounded ASXOS investment-engine mission in an **eight-hour window**.

## Hard envelope

- Normally one PR; hard maximum two.
- Exactly one implementation lane.
- No new scope after **T+04:00**.
- Implementation/content freeze at **T+06:30**.
- End with all PRs tested together and a clean combined worktree.

Use `mission-template.yaml` and the sprint contract. James-only/no-broker execution,
zero Model A in the capital path, deterministic risk/tax/cost/evaluation/sizing,
Decimal arithmetic, provenance, fail-closed freshness, and the selected sprint's
roadmap evidence ceiling are hard gates. Every implementation sprint, S01–S12,
is exactly `PAPER_ONLY`. Only a later immutable operational-gate decision over
the frozen final lineage may permit `UNCALIBRATED`; elapsed sprint completion
cannot.

Copy the template to
`docs/programs/investment-engine/missions/SXX/MXX/mission.yaml`, using the next
unused mission ID in the sprint; never overwrite the template or a prior
mission. Close at
`docs/programs/investment-engine/missions/SXX/MXX/close.md`.

## Fresh-shell gate

Use the project CPython 3.12 environment for every Python command:

```bash
PYTHON_312="${PYTHON_312:-$(command -v python3.12 || true)}"
test -x "$PYTHON_312"
"$PYTHON_312" -c 'import sys; assert sys.version_info[:2] == (3, 12)'
test -x .venv/bin/python || make install PY="$PYTHON_312"
.venv/bin/python -c 'import sys; assert sys.version_info[:2] == (3, 12)'
.venv/bin/python scripts/validate_investment_program.py
```

Do not substitute an unversioned `python` or `pytest` from the shell.

## Routing

- Opus/Ultra owns architecture, financial/tax/accounting semantics, migrations,
  capital boundaries, and red-team review.
- Fable-low may implement only a frozen contract and own tests, adapters, and
  rendering.
- Count repair cycles per acceptance failure. After two failed Fable cycles, freeze
  that lane and escalate the fixture, logs, and both diffs to Opus/Ultra.

## Clock

| Time | Required state |
|---|---|
| T+00:00–00:30 | Verify authority, baseline, live schema/deploy state, outcome, scope, owner, and acceptance. Return START VERDICT. |
| T+00:30–01:30 | Opus/Ultra freezes any high-consequence contract; establish golden and negative fixtures. |
| T+01:30–04:00 | One implementation lane builds the smallest coherent slice. Keep PR1 reviewable. |
| T+04:00 | Scope cutoff. Reject additions; cut optional work. |
| T+04:00–06:30 | Finish the frozen slice, tests, adapters, and evidence. Use PR2 only when separation is necessary, never to exceed scope. |
| T+06:30 | Freeze. No implementation except a rollback or a review-blocking defect. |
| T+06:30–07:30 | Opus/Ultra red-team where required; run targeted and full/CI gates; test combined PR state. |
| T+07:30–08:00 | Attach acceptance/observability/rollback evidence, clean worktree proof, and CLOSE VERDICT. |

If the mission cannot fit one lane and at most two PRs, stop at start and reduce the
mission. Do not silently turn an eight-hour mission into a twelve-hour one.
