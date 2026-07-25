# Sprint-start prompt

Use this at the start of every investment-engine sprint.

---

You are starting **ASXOS Investment Engine SXX**.

Read, in order:

1. `CLAUDE.md`;
2. `docs/README.md` and the current handoff/roadmap authority it names;
3. `docs/programs/investment-engine/acceptance-matrix.md`;
4. `docs/programs/investment-engine/operations-and-rollout.md`;
5. the SXX sprint contract;
6. the previous sprint close record.

Verify the actual `main` SHA, live migration ledger, deployed job inventory, open PRs,
and worktree before accepting any state claim. The dossier baseline is
`9d442de287e123ae090b95838155dc41d76ee5f3`; it is a historical implementation
anchor, not permission to ignore newer `main`.

Copy `mission-template.yaml` to
`docs/programs/investment-engine/missions/SXX/MXX/mission.yaml`, using the next
unused mission ID in the sprint; never edit the template or overwrite a prior
mission. The close record belongs at
`docs/programs/investment-engine/missions/SXX/MXX/close.md`. Do not implement
until the mission instance contains:

- one outcome and named acceptance IDs;
- exact in-scope and out-of-scope paths;
- current-code reuse;
- input/output/freshness/negative-state contracts;
- migration and forward-recovery decision;
- owned, non-overlapping lanes;
- PR plan within the selected window ceiling;
- test, observability, and rollback evidence.

Hold these boundaries:

- James-only, single-user decision support;
- advise and stage only; never connect to or execute through a broker;
- Model A v1_5, `signals`, the signal-driven allocator, and signal-ranked
  opportunity cost are prohibited in the capital path;
- AI may research and review theses; risk, tax, costs, evaluation, and sizing are
  deterministic;
- missing/stale/contradictory inputs fail closed;
- monetary/statistical arithmetic is Decimal and persisted as `NUMERIC(18,6)`;
- the mission uses the roadmap's exact maximum evidence tier: every
  implementation sprint, S01–S12, is `PAPER_ONLY`; only a later immutable
  operational-gate decision over the frozen final lineage may permit
  `UNCALIBRATED`.

For S01, load `model-a-decommission.md`. Resolve the deployed Model A inventory,
create and restore-check the read-only archive manifest, and prepare the exact
scheduler/writer/surface shutdown with rollback and no-write observation.
M02 performs no production change and cannot manufacture elapsed no-write
evidence. Production changes require James's recorded approval plus separately
bounded M-A2/M-A3 missions. Only their successful close may make the legacy
`/pm-review` and Model-A-coupled agents fail closed; S04/S05 build an independent
replacement regardless of that retirement lane.

S01 may prepare but may not activate tailored-output semantics. Before any such
runtime output, James must separately ratify one reviewed change covering
`CLAUDE.md`, `docs/product/north-star.md`,
`docs/product/portfolio-manager-charter.md`,
`docs/product/portfolio-policy.md`,
`docs/product/recommendation-schema.md`,
`docs/product/arbi-permission-model.md`, and
`.claude/rules/portfolio-conventions.md`. If any one is unresolved, return
`NOT READY`.

Use the project CPython 3.12 environment from a fresh shell:

```bash
PYTHON_312="${PYTHON_312:-$(command -v python3.12 || true)}"
test -x "$PYTHON_312"
"$PYTHON_312" -c 'import sys; assert sys.version_info[:2] == (3, 12)'
test -x .venv/bin/python || make install PY="$PYTHON_312"
.venv/bin/python -c 'import sys; assert sys.version_info[:2] == (3, 12)'
.venv/bin/python scripts/validate_investment_program.py
.venv/bin/python -m pytest tests/test_investment_program_dossier.py -q
```

Never substitute unversioned shell-global `python` or `pytest`.

Route work explicitly:

- Opus/Ultra: architecture, financial/tax/accounting semantics, migrations, capital
  boundaries, and red-team review;
- Fable-low: implementation of a frozen contract, tests, adapters, and rendering;
- after two failed Fable repair cycles on the same acceptance failure, stop and
  escalate the failing fixture, logs, and both attempted diffs to Opus/Ultra.

Window controls:

- 8h: normally one PR, hard maximum two, one implementation lane, no scope after
  hour 4, freeze at hour 6.5;
- 12h: maximum two product PRs plus one evidence/ops PR, maximum two implementation
  lanes, no scope after hour 6, freeze at hour 10.

Before implementation, return a **START VERDICT**:

```text
READY | NOT READY
baseline:
authority:
outcome:
acceptance:
scope/owners:
model routing:
PR/window:
migration:
tests:
rollback:
blockers:
```

`NOT READY` is the correct verdict when a capital-boundary input, source authority,
ownership boundary, migration number, or James decision is unresolved. Do not fill
those gaps by assumption.
