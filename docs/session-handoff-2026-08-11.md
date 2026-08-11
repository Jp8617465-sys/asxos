# Session handoff — 2026-08-11

**Status:** current
**Scope:** whole repo / session handoff
**Last verified:** 2026-08-11
**Read priority:** read first
**Superseded by:** N/A

Read this before doing anything else in this repo.

This handoff is **retrospective**. The 2026-08-11 build session ran five parallel missions,
merged all five, and stood down without a close. Everything below was reconstructed a session
later from commits, PR bodies, observed CI runs and live database probes — not from first-hand
observation of that session. Where a claim could not be verified that way, it is marked.

---

## STOP — read this first

### 1. Model A quarantine (CLAUDE.md rule #11) — STANDING

Resolved 2026-07-11 **against** Model A: on 19,032 matured `signal_outcomes`,
`corr(ml_prob, 21d return) = −0.03`, and STRONG_BUY returned −0.09% at 21d vs HOLD's +5.07% —
conviction is inverted at the top. Do not use Model A output as a basis for real capital
decisions. The rule is standing policy, not a temporary hold, and is lifted only by a **new**
model version passing a pre-registered decay bar. See `docs/model-a-decay-analysis-2026-07-11.md`.

This session **strengthened** the quarantine rather than touching it: PR #87 makes
`model_independence` a mandatory assertion on the decision contract, with adversarial identifier
rejection so a Model A-derived input cannot be smuggled in under a renamed field.

### 2. `prices` history is still being destroyed, today

Defect #3 — every dividend or split silently rewrites `adj_close` — is **contained in code but
not in production**. `migrations/0043_price_revisions.sql` is on disk and unapplied; the database
reports 95 applied migrations, latest `20260724110030` (0041). Until 0043 is applied, each
corporate action continues to overwrite history irreversibly, and 0043 is **prospective only** —
it will not recover anything already lost.

This is the only open defect where delay causes permanent, unrecoverable loss. It is the
recommended next action.

---

## What shipped

Five PRs, all squash-merged to `main`, all CI-green. `main` is at `7aa8507`.

| PR | Commit | What |
|---|---|---|
| #83 | `8975e41` | `backup.yml`: removes the deb822 Microsoft runner sources that were 403-ing `apt-get update`, installs `postgresql-client-17` from PGDG, asserts client/server major-version compatibility before `pg_dump`, verifies backup-source identity — **and adds a restore drill** |
| #84 | `d0dbee0` | `migrations/0043_price_revisions.sql`: append-only price-revision ledger, DELETE tombstones, no revision noise on no-op updates, UPDATE/DELETE/TRUNCATE blocked on the ledger, TRUNCATE blocked on `prices`, SECURITY DEFINER trigger with fixed `search_path`. Migration 0042 left reserved for the parked rules-integrity branch |
| #85 | `36b07fb` | `derive_fundamentals_pit`: keyset-paginated symbol discovery (50/page, range 1–200) and bounded PIT write chunks (250 rows, range 1–1,000), each chunk committed independently and idempotent after partial failure, with `JobMonitor` cumulative rows updated per chunk so a later failure reports real progress — all **without** raising the 30-second command timeout |
| #86 | `e130240` | Brief persistence: a failed `brief_runs` audit write is no longer silently swallowed. Primary delivery is attempted first, then a typed failure is raised inside `JobMonitor`; the run records failed, the failure healthcheck pings, cron exits non-zero, and a confirmed primary delivery suppresses duplicate fallback mail. Closes the `except Exception: pass` violation of CLAUDE.md #10 |
| #87 | `7aa8507` | Decision engine adopted from the preserved #81 prototype onto a fresh branch from `main`, closing all ten `target-architecture.md` Appendix I.2 blockers and all five F8 amendments. Stays read-only and synthetic |

**The backup fix is the one to note.** It was not declared done on a green YAML parse. Run
`31465179375` records `backup: success` **and** `restore_drill: success` — a real dump restored
into a clean schema built from the repository's own migrations, with every table count verified.
That is the first end-to-end proof the irreplaceable-data backup works since the Render exit.

Full suite at close: **2033 passed, 0 failed, 2 xfailed** (39s), run against the full dependency
set at `/Users/jpcino/Desktop/asxos-wt-pr71/.venv/bin/python`. The CLAUDE.md joblib/lightgbm
sandbox caveat does not apply to that runner — it has real dependencies and the suite is clean.

---

## The honest frame: merged is not shipped

Four of the seven live defects are fixed **in code**. **Zero are closed in production.**

- Defect #3 stops at an unapplied migration. `prices` is still being overwritten.
- Defect #2 stops at an unrun job. `rs_fundamentals_pit` is unchanged at **63 rows / 11 symbols**
  of a 2,391-symbol active universe — exactly where it was before the fix merged.
- Defects #4 (9 orphaned Render jobs), #5 (`us-positions` cron at US market *open*, not close),
  and #7 (V2 brief dark, `ASXOS_V2_BRIEF_ENABLED` set nowhere) were not touched at all.

Only defect #1 moved in reality, and it did so precisely because it carried its own observed
proof rather than a promise of a later run.

**Live consequence, observed at close:** `check_cron_health` has failed every run for at least a
week. Its error is verbatim `CONSECUTIVE FAILURES: derive_fundamentals_pit last 3 runs all
failed`. The monitor is a **true positive, not a broken monitor**. One successful PIT run clears
both reds at once.

**Standing lesson (now in `decision-log.md`):** a defect row goes green on an observed
production artifact, not on a merge SHA.

---

## Recommended next action

**Rehearse migration 0043 against a disposable PostgreSQL instance and hand James the observed
evidence.** PR #84 names this as its own gate: observe update, delete, no-op and immutability
behaviour end to end before production application. It is reversible, needs no governor decision
to *perform*, and it is the only remaining item where every further day destroys data.

Then, in order: run `derive_fundamentals_pit` once under authority and reconcile coverage
(this also clears `check_cron_health`), then take defect #5 (a one-line cron correction plus its
wrong header comment) as the cheapest remaining win.

---

## Pending — requires James

| # | Item | Why it's yours |
|---|---|---|
| 1 | **Apply migration 0043** and bump `REQUIRED_MIGRATIONS` 95→96 (`asxos/api/main.py:15`) | Migration approval. Do this *after* the disposable-Postgres rehearsal above |
| 2 | **Authorise one full `derive_fundamentals_pit` run**, then `compute_factor_scores` on the resulting cross-section | PR #85's stated production gate |
| ~~3~~ | ~~**PR #81**~~ — **RESOLVED 2026-08-11: closed as superseded**, with a comment pointing to #87. Branch `claude/decision-engine-prototype` @ `c6ff3c3` retained; do not delete it | Was merge/close authority; James ruled at the close |
| 4 | **PR #80** (rules-integrity, PARKED at `3f6fd51`) — 4,869 lines, 2,035 tests passing, review loop never completed. `migrations/0042_rules_integrity.sql` **must not be applied** | Resume, or formally retire? Preservation is not adoption |
| 5 | **Does #87 supersede Appendix B** as the canonical contract, or does Appendix B remain the logical authority with #87 as its implementation? | Governor call on the source-of-truth ladder |
| 6 | Carried from before: HUBS 10/20 employer-concentration enforcement (deferred to the `security_kind` build); CBA thesis #1 retire confirmation | `james-inbox.md` — unchanged, still open |
| 7 | **Apply the one-line `docs/README.md` amendment below** — that file is authority-guarded, so this close could only draft it | Authority file. arbi may draft, never apply |

### Draft amendment — `docs/README.md` line 20

`docs/README.md:20` still names the 08-08 handoff as newest. Replace that line with:

> `2. session-handoff-2026-08-11.md` — the newest dated handoff and current priority state; it
> records the five-PR remediation session, and separates code-complete work from what is actually
> live in production (four defects fixed in code, zero closed in production)

`session-handoff-2026-08-08.md` has already been marked SUPERSEDED in its own header (that file is
not authority-guarded).

---

## Process finding

`arbi-run-ledger.md` and `decision-log.md` both ran dry after **2026-07-24**. The entire August
arc — 08-05, 08-08, 08-09, 08-10, 08-11 — went unrecorded until this close. The compounding loop
(wake → work → stand down → wake) was broken for five sessions before anyone noticed, which also
means autonomy precondition (3), the scorecard track record, stopped accruing for that whole span.

This close restarts the ledger with an episode score of **3.8** for the 08-11 build session
(excellent engineering, broken bookkeeping, nothing shipped to production). It does **not**
back-fill scores for sessions no one observed. If a session ends without `/arbi-close`, the next
one starts from a document that is confidently wrong — which is what happened here.

---

## Also on the working tree

Two untracked proposals, both superseded to reference-only by the 2026-08-10 reframe, neither
committed: `docs/proposals/arbi-outcome-programme-convergence-sprint-2026-08-08.md` and
`docs/proposals/asxos-research-to-decision-live-slice-brief-2026-08-10.md`. Commit or delete —
they should not sit untracked indefinitely.

Other open drafts, untouched: #78 (finance red-team evidence), #73 (M0 news empty-state),
#70 (investment-engine dossier). **#81 was closed as superseded at this session's close** — the
remaining four are all still open and none were assessed here.
