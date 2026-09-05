# Toolwatch findings log — the research lane's cross-run memory

**Status:** current (append-only; a row is written by a workflow step on every fire)
**Scope:** every Claude Code / harness capability the weekly toolwatch lane surfaces, its
disposition, and the repo surface it affects
**Owner:** the lane appends; James reviews; rows are immutable once written
**Rules:** `security-perf-mission-loop.md` (shared safety envelope),
`harness-profiles.md` §Standing dispatch (Amendment H)

This is the dedup source — a capability already logged `adopted`, `watching` or `ignored` is not
re-proposed. It is also the liveness proof: **the row is written by a workflow step with
`if: always()`, not by the agent.** A fire that finds nothing still commits a `heartbeat` row.

The two prior scheduled loops in this repo (7a brief, secperf) both died as unobserved silence
and were only noticed weeks later. `roadmap-state.md:1254` names the lesson: their *"quality and
liveness problems are the same problem."* If two consecutive fires leave no commit here, treat
the lane as dead regardless of what its run status reports.

## Disposition legend

- `adopted` — a draft PR implements it (link in the row)
- `watching` — real, not yet worth adopting; **the trigger that would promote it is required**
- `ignored` — investigated, not applicable to this repo (reason required)
- `heartbeat` — a fire that proposed nothing; proves the lane ran (silence ≠ calm)

## The relevance bar

Every `adopted` or `watching` row **must name a concrete repo surface** — a file path, a hook, a
workflow, a `CLAUDE.md` rule, an agent definition. An item that cannot name one is `ignored`,
not carried as background.

This is the whole design constraint. James paused the last two loops because *"the briefs
weren't worth reading"* — a generic changelog digest is precisely that failure. A release note
about a feature this repo will never use is not a finding.

## Log (append below; newest at bottom)

| Date (UTC) | Fire | Capability | Repo surface affected | Disposition | PR / reason |
|---|---|---|---|---|---|
| 2026-09-02 | seed | — | — | heartbeat | Log initialized with the lane (Amendment H). No fire has run yet. |
