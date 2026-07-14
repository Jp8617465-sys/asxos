# Session handoff — 2026-07-13

**Status:** current
**Scope:** whole repo / session handoff
**Last verified:** 2026-07-13
**Read priority:** read first
**Superseded by:** N/A

Read this before doing anything else in this repo. The line-by-line backlog in
`docs/next-session-backlog.md` and the reconciled state in
`docs/product/roadmap-state.md` remain accurate; this document says what actually
matters right now and what is waiting on James.

---

## STOP — read first: rule #11 (Model A quarantine) is STANDING policy, not an open question

The Model A signal-reliability dispute is **RESOLVED (2026-07-11, against Model A)** — on 19,032
matured signals, `corr(ml_prob, 21d) = −0.03` and STRONG_BUY returned −0.09% at 21d vs HOLD's
+5.07% (conviction inverted at the top). James **shelved the ML engine**; the product is the
model-independent moat (discipline, tax, themes, ETFs). Rule #11 is now **standing policy**, a
boundary to hold — **not** a P0 to resolve. Do **not** re-run the decay check (recency overfit),
do **not** act on Model A output for capital, and do **not** remove rule #11 from `CLAUDE.md` on
the basis of v1_5. `asxos-retrain-model-a` is (correctly) suspended; the quarantine is
mechanically enforced (`approved_for_allocation=FALSE` → allocator hard-fails).

Everything below is model-independent and unaffected by the quarantine.

---

## What shipped this session

**Merged to `main`:**
- **PR #26** — restored the monitoring lane: `track_signal_outcomes` init-pool ordering fix (it
  had silently crashed since 2026-04-15), `check_model_staleness` made shelf-aware,
  `validate_price_data` nano-cap floor, `sync_financial_statements` OOM fix.
- **PR #27** — universe→segment coverage rollup (`asx theme coverage`), Tier 2a mechanical
  screening evaluator (`asx screen`), theme approve/reject CLI, news-brief flip (`ASXOS_NEWS_BRIEF_ENABLED=1`),
  ETF/LIC screening-criteria scoping + sector-screener spec (design docs), recovered research.
- **PR #28** — the portfolio-team-visibility **proposal** + the ChatGPT autonomy note (backlog) +
  candidate lessons L-cand-2/L-cand-3.

**Built this session, open as draft PR #29 (CI pending at close):**
- **PR1 of the portfolio-visibility lane** — `asxos/domain/theses/discipline.py`, a pure,
  deterministic, model-independent thesis-discipline evaluator (revisit cadence, trajectory,
  stop/target, data-sanity, conviction, concentration, benchmark lag). 19 tests, mypy --strict
  clean, full review loop applied. Ships wired to **nothing** — a later PR2 surfaces it. Rule #11
  + R10 + s766B held by construction; fail-loud per-check.

**The core diagnosis this session** (behind James's "the team knew, but I didn't see it"): the
portfolio discipline layer is a **surfacing gap, not a compute gap** — the daily `active_theses`
collector computes CBA's "revisit 14d overdue" *every day* and then the emailed V1 brief drops it
(the discipline section is behind the unset `ASXOS_V2_BRIEF_ENABLED`), and the `/pm-review` LLM
findings die in markdown. PR1→PR4 fix this in reversible steps. Full: `docs/proposals/portfolio-team-visibility-2026-07-12.md`.

**Also:** `market_context_current` feed fixed + live (RBA cash rate 4.31%, VIX 15.03 now
populated; only iron ore still 404s). HUBS reframed in `james-inbox.md` as an ESPP single-employer
**concentration-policy** call, not a 1–5 conviction rating (James's clarification).

## Pending, requiring James (nothing below is arbi's to self-serve)

1. **PR #29** — confirm CI green (expected; the sandbox's 35 joblib collection-errors don't apply
   in CI), then review/merge. Draft; not merged.
2. **PR2 surface choice — A-brief (recommended) vs A-cron** (`portfolio-team-visibility-2026-07-12.md` §5).
   This is the only decision gating the next build; PR1 needed none. A-brief = a discipline section
   in the brief you already read (no gate flip); A-cron = a 5th daily email.
3. **HUBS concentration policy** — a max-% ceiling for employer/ESPP stock (or a conviction number
   if you still want one). ~100% of capital; blocks the size-vs-conviction check portfolio-wide (R11).
4. **CBA thesis #1 — fix or retire.** Ladder 42/45/38/60 vs live ~168 (CBA traded $142–$191 over
   18mo) — a data-entry error; revisit 14d overdue. Not held, no capital at risk either way.
5. **VGS.AU / VAS.AU holding-lot data** (quantity · cost base · acquisition date · FX) — unblocks
   ETF Slice 2 running on real passive positions.
6. **Autonomy gates (parallel, your config):** R-A2 branch protection on `main` (GitHub settings —
   the mechanical poisoning-firewall gap, still unconfigured); R-A1 reversible-work allowlist
   (arbi drafts, you sign — it's a `settings.json` self-modification tier). See
   `arbi-operating-backlog.md:R-A1..R-A5`.
7. **Agent DB read-only role migration** (`docs/proposals/agent-db-readonly-role-design-2026-07-11.md`)
   — apply + re-point the MCP; autonomy precondition (2) + Phase 2c prereq. Note the **draft-0038
   collision** (screening-evaluator-wiring vs agent-readonly-role) — whichever applies first, the
   other renumbers to 0039.

## Files committed this session (on branch `claude/wake-up-arbi-jeww8p`, in PR #29)

`asxos/domain/theses/discipline.py`, `tests/test_thesis_discipline.py`,
`docs/proposals/portfolio-team-visibility-2026-07-12.md` (PR1 landed marker),
`docs/product/roadmap-state.md` (wake refresh + queue re-rank), `docs/product/decision-log.md`
(this session's rows), `docs/product/james-inbox.md` (HUBS reframe),
`docs/product/arbi-operating-backlog.md` (autonomy note), `docs/product/memory/working/`
(L-cand-2/L-cand-3), and this handoff.

These reach `main` when PR #29 merges (James's call). A handoff that lives only on a feature
branch is a process defect (`docs/README.md`) — so the merge is what makes the next wake read from
truth.
