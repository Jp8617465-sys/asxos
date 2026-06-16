# 07 — Safe Parallel Workstream Plan (Opus + UltraCode)

*Category-5. Principle: many read-only streams can run concurrently; only ONE implementation branch at a time, after approval.*

## Can run in parallel (read-only — no conflict risk)
- P0 correctness final verification (one residual: confirm persisted `v1_5` regressor used `×10_000`).
- Baseline / rank-IC / decile-spread research design (`08` Prompt D).
- `price_coverage` metadata design + Thu/Fri gap root-cause diagnostic (`08` Prompt B/diag).
- Brief QA review (does the email overstate confidence? `08` Prompt I).
- Quant-guide synthesis / roadmap refinement.
- Red-team review of any plan.

These touch **no production files** and **no shared writable state** → safe to fan out as subagents.

## Must run sequentially (mutating; conflict or blast-radius risk)
- Any production code change touching the same files (`generate_signals.py`, `thresholds.py`, `loader.py`, `compose.py`).
- `sync_prices` changes (e.g. `price_coverage` writer).
- Schema migrations.
- Render config / schedule changes.
- Model retraining / activation.
- Threshold changes (the P0 units fix).

**Hard rule:** at most **one implementation branch in flight**, merged via review before the next starts. The P0 units fix and the adj_close retrain must NOT be implemented concurrently (both touch the signal pipeline and both change labels).

## Recommended next two sessions
- **Session 1 (read-only, fan-out):** finalize P0 verification + draft the units-fix decision brief + brief-caveat copy + `price_coverage` design + gap diagnostic — all parallel read-only subagents, synthesized into one approval-ready plan. *No code.*
- **Session 2 (single implementation branch, after approval):** implement the P0 units fix + brief caveat on one branch; full tests; PR; review; merge. Only then schedule the adj_close+retrain branch.

## Using Opus + UltraCode without conflicts
- Use parallel subagents **only for read-only research/review**; keep them structurally read-only (no Edit/Write).
- The orchestrator is the **single writer** (docs or, in an implementation session, one feature branch).
- Never run two file-mutating workflows at once; never let a subagent edit production code.
- Gate every mutation behind explicit human approval, especially threshold/label/retrain changes.
