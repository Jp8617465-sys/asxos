# Session handoff — 2026-08-12

**Status:** current
**Scope:** whole repo / session handoff
**Last verified:** 2026-08-12
**Read priority:** read first
**Superseded by:** N/A

Read this before doing anything else in this repo. It supersedes
`session-handoff-2026-08-11.md`, whose pending items 1 and 2 are now closed.

This handoff was written **mid-session**, at James's request, as a checkpoint rather than a
stand-down. Anything after the "Open at checkpoint time" section may have moved on.

---

## STOP — read this first

### 1. Model A quarantine (CLAUDE.md rule #11) — STANDING

Resolved 2026-07-11 **against** Model A: on 19,032 matured `signal_outcomes`,
`corr(ml_prob, 21d return) = −0.03`, and STRONG_BUY returned −0.09% at 21d vs HOLD's +5.07%.
Do not use Model A output as a basis for real capital decisions. Standing policy, not a
temporary hold; lifted only by a **new** model version passing a pre-registered decay bar.
See `docs/model-a-decay-analysis-2026-07-11.md`. A queued mission (#11 below) proposes
retiring Model A from all active surfaces entirely — that mission *strengthens* the rule, it
does not touch it.

### 2. `prices` history is now contained — but nothing before 2026-08-12 is recoverable

Migration `0043_price_revisions.sql` **is applied** (see below). Every destructive UPDATE or
DELETE on `prices` from 2026-08-12 onward writes the prior and replacement values to an
append-only ledger in the same transaction. The migration is **prospective only**: every
`adj_close` rewrite before today is permanently lost and no backfill exists.

---

## What actually changed in production today

This is the first session where defect rows moved on **observed production artifacts**
rather than merge SHAs — the standing lesson from the 08-11 close.

| Item | Evidence |
|---|---|
| **Migration 0043 applied** | Version `20260812092925`; observed `schema_migrations` count **96** (95 at preflight); exact repo file, SHA-1 `b348b74b9b1e26daf147117a8ca5cb6de86fd155`; all three triggers enabled. Pre-apply gate: manual `backup.yml` run **31574011421** green with `restore_drill=true` on `97cdc5c`. Runbook probe: exactly one same-transaction revision captured (`0P000079J8.AU` @ 2026-08-11), rolled back, residue 0. Post-apply drill **31593927269** logged `price_revisions exists — include append-only price history` and `all 14 table counts match` |
| **PIT store made real** | `derive_fundamentals_pit` succeeded in production for the first time: **53,624 rows / 3,357 symbols in 148s**, 68 batches, zero timeouts (was 63 rows / 11 symbols). Coverage reconciled: 1,853 of 2,391 active-universe symbols; the 538 uncovered actives have **no `rs_financial_statements` source rows at all** — an upstream sync-coverage question, not a PIT defect |
| **Factor scores** | `compute_factor_scores` scored **3,308 symbols** at `as_of` 2026-08-11 (`fs_v1`; was 11) |
| **Cron health** | `check_cron_health` **success** at `2026-08-12 09:40:44+00` — first green in 12+ days. The week-long red was a true positive on the PIT failures and cleared by fixing them, not by silencing the monitor |
| **us-positions** | Cron `30 13` → `30 21` UTC. It had been firing at 08:30/09:30 ET — market **open** — so every alert read the prior session's stale prices. Fixed in `.github/workflows/us-positions.yml` (the executing scheduler); `render.yaml:654` still carries the old value and belongs to the orphaned-Render cleanup (defect #4) |
| **Automation harness** | `.github/workflows/claude-execute.yml` is live and validated: run **31595260041**, `is_error: false`, 18 turns, a genuine Claude execution that obeyed its no-changes constraint |

`main` moved `7a0b9e1` → `8037137` (PRs #88, #91, #92, #93). PR #94 (governance docs) is open
and CI-green. Full suite at checkpoint: **2,060 passed, 0 failed, 1 skipped, 2 xfailed**.

---

## Three bugs found in flight

1. **`JobMonitor` wrote timestamps 10 hours in the past.** asyncpg's binary codec encodes a
   *naive* datetime via `astimezone(utc)`, which treats it as the client machine's local
   time — so an AEST run stored `started_at` shifted −10h, and `check_cron_health` flagged
   its own freshly-inserted row as STUCK (run id 849 cited its own timestamp to the
   microsecond). Fixed in `JobMonitor` and `fallback_email` with aware `datetime.now(UTC)`;
   a regression test asserts every datetime bound into `job_runs` is timezone-aware.
2. **A re-run allow-rule would have handed the agent production re-execution.** In drafting
   the guard carve-outs I justified `Bash(gh run rerun:*)` as "read-triggering only." It is
   not: it re-executes any run up to 30 days old with all secrets re-injected. The security
   review enumerated the live targets — `daily-brief` (prod DB writes + email),
   `us-positions` (alert email), `weekly-research` (prod writes + EODHD quota). Removed from
   settings **and** hard-denied in the hook, with tests. Caught before merge.
3. **Command substitution bypassed the dispatch allowlist.** `$(...)` is not a segment
   separator, so `gh workflow run backup.yml $(gh workflow run daily-brief.yml)` fired the
   *denied* workflow, passed the hook, and prefix-matched the settings rule — no prompt at
   all. Pre-existing, widened by the carve-outs, and wrongly documented as covered. Now
   refused outright.

---

## Governance changes (PR #94, open)

- **Governor ruling on #87 vs Appendix B: option (c), the hybrid.** Appendix B remains
  authoritative for which artifacts exist, which fields are mandatory, and the ruled semantic
  tables; `asxos/domain/decision_engine/types.py` is authoritative for validator strictness,
  hashing, temporal enforcement and internal structure. **Adding or removing a field or a
  ruled table row is a governor amendment; tightening a validator is not.** Recorded as
  Appendix **B.4**; **B.5** records the pre-approved `DecisionBrief` real-data amendment.
  Six requirements #87 added beyond Appendix B are folded into B.1 as ratified — including a
  **mandatory real `trading_calendar`**, which makes an ASX session calendar a hard
  prerequisite for any real packet.
- **Branch protection: the repo had been wrong about this since 2026-07-15.**
  `roadmap-state.md` asserted it was PLAN-GATED and CODEOWNERS inert. In fact rulesets
  `asxos-main` (19077432) and `main` (18221894) have been live since 2026-07-17. Classic
  protection re-asserted 2026-08-12. **Two limits, now stated wherever the fact appears:**
  `required_approving_review_count` is **0** — a 1-approval setting was tried and reverted
  the same day because on a solo repo GitHub forbids self-approval, making every merge an
  admin bypass — so **CODEOWNERS is advisory, not mechanical**; and `enforce_admins: false`,
  so an admin-scoped token bypasses it entirely.
- **Guard carve-outs (merged, #93).** The local attended session may now dispatch
  `backup.yml` and `claude-execute.yml` in addition to the three validation lanes. The
  in-CI harness keeps the narrower validation-only set — the permission model and harness doc
  now split the grant by **attendance**, not by workflow class. `backup.yml` **is**
  secret-bearing and its default path commits a dump to an external repo, so the carve-out
  is a narrowing exception to a standing rule, not an instance of it.

---

## Open at checkpoint time

| # | Item | Owner |
|---|---|---|
| 1 | **Tonight's `sync_prices` (~20:30 UTC) is the last 0043 observation** — the first ingestion against the live capture trigger. Revision growth may legitimately be zero if the provider returns byte-equivalent rows; what matters is that ingestion **succeeds**. Local runs cannot substitute: this machine's Python rejects the intercepting TLS certificate (`curl` works, `certifi` does not), so no EODHD-calling job runs from here | observe next session |
| 2 | **PR #94** (governance docs) — CI-green, draft | James: review + merge |
| 3 | **Mission #11 — retire Model A from all active surfaces** via `/arbi-team`. Needs `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` set locally. Envelope saved with operator notes | queued |
| 4 | **Mission #12 — ASX Results-to-Thesis Review slice**, dependent on #11 landing first. The (c) ruling and the `DecisionBrief` pre-approval unblock it | queued |
| 5 | **Task #13 — bounded outcome-engine executor: BLOCKED.** Its required input, `docs/proposals/asxos-outcome-engine-and-arbi-second-brain-execution-plan-2026-08-12.md`, **does not exist in the repo**. Since §2.4 of that plan is the entry gate, the envelope's own rule returns WAITING. Evidence needed to close: the plan committed, or a path to it | James |
| 6 | **A stray `sync_prices` failure row** exists in `job_runs` for 2026-08-12 from the blocked local attempt. Harmless — tonight's success supersedes it before `check_cron_health` runs at 22:00 UTC — but disclosed rather than left to be discovered | none |
| 7 | Carried from 08-11: **PR #80** (rules-integrity, PARKED at `3f6fd51`, migration 0042 must not be applied) — resume or formally retire? Plus the `james-inbox.md` items (HUBS employer concentration, CBA thesis retire confirmation) | James |
| 8 | Defects **#4** (9 orphaned Render jobs — `render.yaml` still declares them) and **#7** (V2 brief dark, `ASXOS_V2_BRIEF_ENABLED` unset) remain untouched. #7 must not be flipped as a shortcut: brief render is a Stage 6 surface concern | queued |

---

## Files to commit

`docs/session-handoff-2026-08-12.md` (this file), `docs/product/decision-log.md`,
`docs/product/arbi-run-ledger.md`, `docs/product/roadmap-state.md`. A handoff that lives only
on a feature branch is a process defect — these belong on `main`.
