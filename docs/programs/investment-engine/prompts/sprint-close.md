# Sprint-close prompt

**Contract version:** 1.0

Use this after the code/content freeze and before calling a sprint complete.

---

Close **ASXOS Investment Engine SXX** against its written contract. Do not summarize
from memory; inspect the combined diff, test output, migrations, runtime evidence,
PRs, and worktree.

1. Re-resolve `main`, head SHA, schema ledger, and deployed state.
2. Prove every changed path belongs to the approved ownership map.
3. Map every claimed result to a sprint DoD item and acceptance-matrix ID.
4. From the documented project CPython 3.12 environment, run targeted positive,
   negative, stale, UTC date-time, Model A, broker, auth/RLS/tenancy, and
   multi-user boundary tests. Run
   `.venv/bin/python scripts/validate_investment_program.py`,
   `.venv/bin/python -m pytest ...`, and `VENV=.venv make check`/CI; separate
   known environment gaps from regressions.
5. If a migration exists, attach `pg_depend` preflight, next-number verification,
   transactional smoke test, compatibility result, apply authority, and forward
   recovery rehearsal.
6. Verify AI output never supplies deterministic risk/tax/cost/evaluation/sizing
   fields and all capital-relevant figures replay from cited evidence.
7. Verify CLI/brief output cannot be read as an order and carries James-only,
   no-execution, and the exact earned evidence tier. Every implementation
   sprint, S01–S12, must close `PAPER_ONLY`; only a later immutable
   operational-gate decision over the frozen final lineage may permit
   `UNCALIBRATED`.
8. Inspect telemetry/job runs and state whether the intended observation actually
   occurred.
9. Confirm PR ceilings and that no scope entered after the cutoff.
10. Test all mission PRs together and capture final `git status --short`.
11. Close the copied mission at
    `docs/programs/investment-engine/missions/SXX/MXX/close.md`; never write
    close evidence into `mission-template.yaml` or another mission's record.
12. For S01 M02, prove archive reproducibility, record the exact deployed Model A
    scheduler/writer/surface state and James's decommission approval status, and
    prove that M02 performed no runtime mutation, claimed no elapsed no-write
    window, and did not tombstone `/pm-review`. If separately approved M-A2/M-A3
    evidence already exists, cite its own immutable close record; never copy its
    claims into M02. Confirm that no tailored-output semantic change was
    activated. After a closed M-A3, the legacy command must fail closed with
    `MODEL_A_DECOMMISSIONED`; that is not the default M02 state. List
    the seven authority documents and James-ratification status explicitly.

Return exactly one **CLOSE VERDICT**:

```text
PASS | NOT READY | ROLLBACK
sprint:
baseline -> head:
PRs:
acceptance passed:
acceptance failed:
tests:
migration:
runtime/observability:
negative/stale behavior:
capital firewall:
model routing/repair cycles:
rollback status:
combined worktree:
residual risks:
next James decision:
```

Rules:

- A partial artifact is `NOT READY`, not “mostly done.”
- A hard-gate failure is `ROLLBACK`/forward-recovery and resets the clean-session
  counter.
- Do not merge, deploy, apply a migration, advance lifecycle state, or mark a James
  decision without the authority separately granted for that action.
- Functional release never satisfies the edge-claim gate.
