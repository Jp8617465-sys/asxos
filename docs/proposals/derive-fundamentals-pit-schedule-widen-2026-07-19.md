# Proposal: widen `derive_fundamentals_pit`'s schedule gap (render.yaml)

**Status:** proposed — arbi cannot write to `render.yaml` (authority-guarded, same
mechanism as the `compute_opportunity_cost` firewall proposal earlier this sprint).
James applies this one-line diff directly and pushes to `main`.

**Not merge-blocking, unlike the `compute_opportunity_cost` render.yaml proposal.**
The companion code change (already committed on `claude/whats-new-yemcl4`,
`jobs/derive_fundamentals_pit.py::_missing_upstreams`) is the load-bearing fix — it
makes a race produce a clean `status='blocked'` instead of a confusing `TimeoutError`,
regardless of what the schedule says. This proposal is pure harm-reduction: widening
the gap so the gate fires (and a manual re-run becomes necessary) less often in
practice. Safe to apply whenever convenient, independently of the code PR merging.

## The problem this doesn't fully solve on its own

2026-07-18 incident: `sync_corporate_actions` (scheduled 16:30 UTC Saturday) took
until 18:09 UTC to finish that particular run — 99 minutes, well past
`derive_fundamentals_pit`'s 17:10 UTC fire time (40 minutes after
`sync_corporate_actions` *started*, with zero relationship to how long it actually
*takes*). `sync_financial_statements` (16:50 UTC) is described in its own render.yaml
comment as "Heavier (one /fundamentals call per symbol)" across ~2,382 active
names — plausibly the slower of the two on a bad EODHD day, though the recorded
incident was corporate-actions' run specifically.

A fixed-offset schedule for a variable-duration upstream dependency chain is
inherently fragile — no single delay is *guaranteed* safe, only more or less likely
to be. The code-level gate (`_missing_upstreams`) is correct regardless of timing;
this schedule change just reduces how often it has to fire.

## Exact diff

Verified against the live `render.yaml` (lines 182-199) via `git apply --check`,
zero offset — built mechanically from a real `diff -u` between the before/after
cron blocks (not hand-typed; the `compute_opportunity_cost` proposal earlier this
sprint had a hand-typed hunk header that only applied via fuzzy offset-matching,
so this one was generated the verified way from the start):

```diff
--- a/render.yaml
+++ b/render.yaml
@@ -182,4 +182,10 @@
-  # Weekly research-store PIT fundamentals derivation — Sunday 03:10 AEST (Sat 17:10 UTC).
+  # Weekly research-store PIT fundamentals derivation — Sunday 04:30 AEST (Sat 18:30 UTC).
+  # Widened from 17:10 UTC (2026-07-19, docs/proposals/derive-fundamentals-pit-
+  # schedule-widen-2026-07-19.md) after a 2026-07-18 race: sync_corporate_actions
+  # (16:30 UTC) ran until 18:09 that Saturday, well past the old 17:10 slot. The
+  # in-code _missing_upstreams gate is the real fix (fails 'blocked', not a
+  # confusing TimeoutError, regardless of timing) — this wider gap just reduces
+  # how often that gate has to fire in practice.
   # Pure DB-to-DB: rs_financial_statements + rs_corporate_actions -> rs_fundamentals_pit.
   # Runs AFTER the statements + corporate-actions jobs (no EODHD).
   - type: cron
@@ -189,5 +195,5 @@
     plan: starter
     branch: main
     buildCommand: pip install -e ".[ml]"
-    schedule: "10 17 * * 6"
+    schedule: "30 18 * * 6"
     command: python jobs/derive_fundamentals_pit.py
```

New schedule gives `derive_fundamentals_pit` **2 hours** of headroom after
`sync_corporate_actions` starts (16:30 → 18:30) and **1h40** after
`sync_financial_statements` starts (16:50 → 18:30) — comfortably above the one
observed slow run (99 minutes) without materially delaying anything downstream:
nothing in the daily Sun-Thu pipeline depends on `derive_fundamentals_pit`
finishing by a specific time (it's Saturday-only, feeding the research store for
factor/PIT analysis, not the daily brief).

## Post-apply steps

1. Apply the diff above to `render.yaml` on `main`.
2. `make check-drift` to confirm Render's live schedule matches (CLAUDE.md rule #2).
3. No manual trigger needed — the next scheduled run picks it up automatically.

## Deferred

A more robust design (event-driven "run when upstream actually finishes" rather
than fixed-offset scheduling) is out of scope — Render cron is offset-based only;
an event-driven trigger would need a different mechanism entirely (e.g. a
completion webhook or a polling wrapper). Not worth the complexity for a
once-a-week job that now fails cleanly and re-runnably when it does race.
