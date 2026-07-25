# Investment engine sprint — `/investment-engine-sprint`

`$ARGUMENTS` = one sprint ID (`S01`–`S12`), optionally followed by `8h` or
`12h`. Example: `S02 8h`.

Execute exactly one accepted outcome from the investment-engine dossier. This
command is attended and reversible: it may prepare implementation and draft
pull requests, but it never merges, deploys, applies a production migration,
changes capital policy, or connects to a broker.

## 1 — Load one bounded context

Read, in order:

1. `CLAUDE.md`;
2. `docs/programs/investment-engine/README.md`;
3. `decisions.md`, `current-state.md`, and `architecture.md` in that directory;
4. `docs/product/roadmap.yaml`;
5. exactly the requested file under `docs/programs/investment-engine/sprints/`;
6. only the contracts, schemas, fixtures, acceptance rows, and operations
   sections linked by that sprint.

Do not load all sprint files into the build prompt. If the requested sprint is
not the next dependency-ready outcome, return `NOT READY` with the unresolved
dependency; do not jump ahead.

## 2 — Verify before planning

- Refresh `origin/main`, open PRs, the latest handoff, live migration ledger,
  `REQUIRED_MIGRATIONS`, and affected runtime/deploy state using read-only
  probes.
- Compare that truth with the dossier baseline. A material mismatch is
  `DOSSIER_DRIFT`.
- Bootstrap and verify the project CPython 3.12 environment, then run the
  dossier validator and its negative self-tests:

  ```bash
  PYTHON_312="${PYTHON_312:-$(command -v python3.12 || true)}"
  test -x "$PYTHON_312"
  "$PYTHON_312" -c 'import sys; assert sys.version_info[:2] == (3, 12)'
  test -x .venv/bin/python || make install PY="$PYTHON_312"
  .venv/bin/python -c 'import sys; assert sys.version_info[:2] == (3, 12)'
  .venv/bin/python scripts/validate_investment_program.py
  .venv/bin/python -m pytest tests/test_investment_program_dossier.py -q
  ```

  Never substitute an unversioned shell-global `python` or `pytest`.
- Confirm James is the sole user and external order placer.
- Confirm the active runtime constitution still permits the proposed output.
  A target decision in the dossier does not silently override current rules.

No production write, migration apply, deploy, or authority-file change is
implied by this command.

## 3 — Freeze the mission

Treat `docs/programs/investment-engine/mission-template.yaml` as immutable.
Copy it to
`docs/programs/investment-engine/missions/SXX/MXX/mission.yaml` and fill that
instance from the selected sprint. Record closure separately at
`docs/programs/investment-engine/missions/SXX/MXX/close.md`. Choose the next
unused mission ID within the sprint; never overwrite an earlier mission. For
S01's first mission the exact paths are
`docs/programs/investment-engine/missions/S01/M01/mission.yaml` and
`docs/programs/investment-engine/missions/S01/M01/close.md`.

Use the sprint's declared window unless James explicitly chose the other recipe
and the work still fits:

- `8h`: normally one PR, hard maximum two, one implementation lane, scope
  cutoff at hour four, freeze at hour six-and-a-half.
- `12h`: maximum two product PRs plus one evidence/operations PR, maximum two
  disjoint implementation lanes, scope cutoff at hour six, freeze at hour ten.

Return a `START VERDICT` containing the outcome, exact in/out scope, owners,
contract versions, negative states, migration posture, PR graph, acceptance
tests, rollback trigger, roadmap maximum evidence tier, and unresolved James
decisions. Every implementation sprint, S01–S12, is exactly `PAPER_ONLY`.
Only a later immutable operational-gate decision over the frozen final lineage
may permit `UNCALIBRATED`.

Opus/Ultra freezes architecture, financial/tax/accounting semantics,
migrations, capital boundaries, and adversarial review. Fable-low works only
after those choices, fixtures, acceptance tests, and file ownership are frozen.
After two failed Fable repair cycles on the same failure, stop and escalate the
fixture, logs, and both attempted diffs.

## 4 — Execute the frozen slice

- Reuse the exact existing components named by the sprint.
- AI may research and review; deterministic code owns quant, tax, accounting,
  evaluation, risk, sizing, and order arithmetic.
- Missing, stale, contradictory, or future-dated input fails closed.
- Capital arithmetic is `Decimal`; persisted monetary/statistical values are
  `NUMERIC(18,6)`.
- Model A and legacy signal/allocator output are absent from every capital
  dependency and wire contract.
- Output stops at an expiring, non-executable artifact for James. Introduce no
  broker client, credential, endpoint, route, submission, modification,
  cancellation, or execution capability.
- Do not add auth, RLS, multi-user fields, web/mobile UI, or feature flags.

For S01, load `model-a-decommission.md`. M02 is the bounded, read-only M-A1
mission only: prepare the exact deployed inventory, checksummed read-only archive,
attended restore/reproduction evidence, rollback plan, and James
approval record. It does not disable a writer or product surface. Treat the
recorded **James approval** as a required input, never an inference. If approved,
open separately bounded M-A2/M-A3 missions for authority alignment, shutdown,
surface retirement, and a natural scheduled-window no-write observation; do not
compress their work or elapsed observation clock into M02. Use exactly these M02
records:

- `docs/programs/investment-engine/missions/S01/M02/mission.yaml`
- `docs/programs/investment-engine/missions/S01/M02/model-a-inventory.json`
- `docs/programs/investment-engine/missions/S01/M02/model-a-archive-manifest.json`
- `docs/programs/investment-engine/missions/S01/M02/model-a-restore-evidence.json`
- `docs/programs/investment-engine/missions/S01/M02/model-a-approval.md`
- `docs/programs/investment-engine/missions/S01/M02/close.md`

Only an approved M-A3 makes `/pm-review` plus its Model-A-coupled agents fail closed
with the stable `MODEL_A_DECOMMISSIONED` tombstone. S04/S05 build the
independent replacement; they never import or alias the passive signal-driven
review lane.

S01 may produce an authority-ratification inventory but may not enable tailored
output. Before any direct tailored, recommendation-ready, `ADVICE_READY`, or
`ORDER_STAGED` runtime output, James must separately ratify one reviewed change
covering all seven current authority documents:

1. `CLAUDE.md`;
2. `docs/product/north-star.md`;
3. `docs/product/portfolio-manager-charter.md`;
4. `docs/product/portfolio-policy.md`;
5. `docs/product/recommendation-schema.md`;
6. `docs/product/arbi-permission-model.md`; and
7. `.claude/rules/portfolio-conventions.md`.

If any authority remains unresolved, stop with `NOT READY`; the stricter current
repository wording wins.

Author and test an additive migration when the sprint requires one, but stop
for James before any live apply. Keep unfinished work on the branch.

## 5 — Freeze, review, and close

At the recipe freeze:

1. stop feature implementation;
2. test all planned PRs together;
3. run targeted tests,
   `.venv/bin/python scripts/validate_investment_program.py`,
   `VENV=.venv make check`/CI, replay, stale, UTC date-time, Model A, broker,
   auth/RLS/tenancy, and multi-user boundary tests;
4. run fresh-context security, architecture/financial, and documentation
   reviews;
5. attach acceptance, migration, observability, recovery, repair-cycle, and
   clean-worktree evidence;
6. open only draft PRs; never merge or enable auto-merge.

Return one `CLOSE VERDICT`: `READY FOR JAMES`, `NOT READY`, or `BLOCKED`, with
the exact evidence tier, evidence, authority/quarantine status where applicable,
and next decision. Elapsed time never closes an unmet acceptance criterion or
release gate.
