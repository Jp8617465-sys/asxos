# asxos — project handoff, 2026-08-18

`origin/main` = `fbede4d`. Every figure below was verified against the live database,
the GitHub API, or a command run during the session. Where something is inferred it
says so.

---

## What this project is

A single-user investment intelligence system for ASX equities. Python 3.12, FastAPI,
asyncpg, Supabase Postgres. **CLI and a daily email brief — no frontend.** Jobs run as
scheduled **GitHub Actions workflows** (Render was deleted 2026-08-12; ignore any doc
that says otherwise).

The output is not the brief. It is *better investment decisions* — benchmark-relative
and risk-controlled. `docs/product/north-star.md` and `docs/product/target-architecture.md`
are the canonical statements; the second is a ratified stage plan whose **Stage 1 has
never been authorised.**

---

## Read these first, in this order

1. `CLAUDE.md` — non-negotiables. Rule #11 and the s766B firewall are load-bearing.
2. `docs/product/north-star.md` — what "done" means.
3. `docs/product/target-architecture.md` — the ratified target and its stage gates.
4. `docs/product/memory/approved-lessons.md` — **L1–L26**, hard-won. L17 and L21 in
   particular will save you a day.
5. `docs/product/finance-capability-matrix-2026-08-13.md` §6 — gaps G1–G12.

---

## Two constraints that will get work rejected

**Rule #11 — the Model A quarantine.** No code may read `signals`, `model_versions`,
`shap_factors`, `prob_up` or `expected_return` as a basis for any capital-facing output.
This is resolved policy backed by 19,032 matured signals showing inverted conviction, not
an open question. Note `signals` has had **no writer since its producer was deleted** — it
is a dead table regardless.

**s766B — the personal-advice firewall.** The system **measures and remembers; it never
takes a view.** No rating, ordinal ranking, system-generated price target, recommended
position size, or "should". A reverse-DCF is permitted *because* the assumptions are the
user's own input — a system default assumption is advice smuggled in. The canonical
vocabulary guard is `asxos/domain/review/status.py::directive_terms`; import it, never
hand-roll a second list.

---

## Traps that will bite in the first hour

**Local `main` is ~34 commits stale and checked out in a different worktree**
(`/Users/jpcino/Documents/PR Agent/asxos-arbi-plan`). Always `git fetch` and reference
`origin/main`. This staleness has already made two agents disagree about whether a file
exists, and it broke a merge today.

**The test baseline is interpreter-dependent.** The `asxos-wt-pr71/.venv` interpreter has
joblib/lightgbm/sklearn and reports **2393 passed, 0 failed, 0 errors**. Other environments
report 2390 with 1 failure and 1 error. Both are correct. **Re-derive the baseline yourself
on `origin/main` in the same interpreter — never trust a remembered number.** Note the
lightgbm failure does *not* appear under `grep '^ERROR'`, so that grep alone under-reports.

**File:line citations rot.** Five false in-code citations were found in one day. Prefer
names (workflow step names, function names) over line numbers. Verify any citation before
repeating it.

**A hook blocks `git commit` when Python is staged** until a review loop has run
(`.claude/hooks/review-gate.sh`). It also denies compound `git add … && git commit`. Stage
Python separately, run the loop, `touch` the marker it prints, then commit.

**An authority guard blocks Bash commands whose *text* references governance paths**
(`CLAUDE.md`, `.claude/settings.json`, `.claude/rules/`, `.github/`) alongside a
write-capable utility — including in commit messages. This is a known false-positive class.
Do not work around it; reword or route the change to James.

---

## What changed today

**Eight PRs merged this session** (#125, #126, #132, #133, #135, #136, #137, #138);
#129–#131 landed immediately before it.

- **The brief can now report its own failures.** `_job_failures` filtered
  `WHERE as_of = $1`, which could never match — every failure-writing job runs *after*
  `compose_brief`. Live proof: `check_cron_health` failed on 08-15, 08-16 and 08-17 naming
  a stuck job, and none reached the email. Now windowed on the previous successful
  `compose_brief`, floored at 7 days, with stuck `running` rows surfaced as a distinct kind.
  **Verified by rendering the actual brief**, not by tests.
- **`check_cron_health` can escalate.** It used `timedelta.seconds` — the sub-day
  remainder — so a 56.5h hang reported ">8h" forever.
- **The weekly research chain is alive.** `sync_corporate_actions` went 88 min → **4m35s**;
  the six-step chain completed end-to-end for the first time (23m22s against a 90-min cap),
  writing 435,442 financial-statement rows and 53,687 PIT rows.
- **Memory advanced L16 → L26** — first promotion in 34 days.
- **36 stale docs archived**, five corrected, `scripts/check_doc_expiry.sh` added.
- **Eight agent definitions fixed** — every DB-reading agent declared a tool name that does
  not resolve, so all eight ran blind.

---

## Open work, ordered

### 1. Memory-gap line in the daily brief *(small, high value)*
A row reading `Memory: N candidates un-enacted · approved-lessons unchanged for D days`.
The promotion loop has a working producer and consumer and **no trigger** — that is why a
34-day gap went unnoticed. Reuses an existing surface; needs no new schedule.

### 2. Re-run `sector-screener` against Consumer Cyclical
It has never successfully queried. Its tool name is now fixed on `main`, but **agent
definitions are parsed at session start**, so it needs a fresh session. It twice refused to
emit a plausible zero rather than assert something it had not measured — that behaviour is
correct and should be preserved.

### 3. T1 segment metrics — review loop, then draft PR
Branch `claude/t1-segment-metrics` (worktree `/Users/jpcino/Desktop/asxos-wt-t1`),
2 commits, +1,933 lines. Renders 13 GICS sectors over 1,852 live symbols. **Its review loop
has never run.** Caution: its reported split multiples did not reproduce — it claimed
`ID8.AU` "exactly 100×"; measured **266.7×** (an actual 1-for-200 consolidation). Verify its
numbers.

### 4. Agent-drafted theses — one branch away
`ThesisProposal` **exists** at `asxos/domain/theses/schemas.py:344`, fully specified with
provenance-carrying `ReportFigure` prices and mandatory evidence citations.
`create_thesis_from_agent_run()` is wired end-to-end and ends in a `raise ValueError`
saying *"no ThesisProposal schema exists yet"* — **which is now false**. Its own docstring
says landing the schema makes this *"a schema-plus-one-branch change."*
Add while you are there: the validator checks `entry_lower <= entry_upper` but nothing
checks `stop < entry < target`.

### 5. `discipline.py:389` — print the bound that fired
The trajectory message interpolates `target` for every state, so a `STOP_VIOLATED` finding
never shows the stop. Live example: `HUBS.NYSE` renders
`STOP VIOLATED (current 215.17, target 318.00)` — the 230.00 stop that triggered it is
invisible, and the position is *up* 14.7%.

---

## Blocked, and why — do not "fix" these

- **Tax module.** Franking, Medicare, Div 296, TC-20 and TC-21 are implemented and
  spec-tested and have **never run on real data**. `asxos/cli/tax.py:93,99` hardcodes
  `dividends=[]` and `realised_gains=[]`. Root cause is deeper than the hardcode:
  `holding_lots` has **zero disposed rows** and **nothing in the repo writes `disposed_at`**
  (~20 readers, zero writers). Secondary: `cli/tax.py:53` reads `current_holdings`, a view
  that filters disposals out. `cash_dividend` has **no source in the schema at all** — no
  dividends/income/transactions table exists.
- **Benchmark/alpha.** Render `unavailable` **by ruling, not defect**. `AXJOA.INDX` does not
  exist; governor ruling F1 forbids a proxy; F2 gives the global sleeve no benchmark, and
  the sole open lot is in that sleeve.
- **Exposure/concentration at n=1.** One open lot; most decompositions are degenerate. A
  known per-lot-vs-per-symbol bug exists but renders identically today.

---

## The rule that governs what gets built

**Amendment D** (ratified, `docs/product/roadmap-state.md:192`): a unit is not complete
while its output on **live data** is `unavailable`, empty, or driven only by demo rows.
Correct-and-empty is not done.

**Amendment E** is drafted in the same file and **NOT ratified** — James's call. It extends
the test to all lanes and requires a close row to carry exactly one true field:
`renders:` / `captures:` / `defect:`.

**Practical consequence: run the code path against production before writing it.** Six units
shipped correct, tested, reviewed and inert. Two more were stopped today by a single SQL
query at design time.

---

## The pattern worth internalising

Seven times in one day, a mechanism existed and the thing that makes it fire did not:

| Built | Missing |
|---|---|
| `price_revisions` trigger (live) | past dates are never re-fetched, so nothing to capture |
| `scripts/check_ledger_coverage.sh` | invoked by nothing |
| `ThesisProposal` schema | a `raise` saying it doesn't exist |
| `disposed_at` — 20 readers | zero writers |
| `.github/CODEOWNERS` | enforcement (documented its own gap in its header) |
| `asxos/domain/results_review/` | a producer |
| three fixes applied on disk | never committed |

**The tell: anything that documents its own precondition has not been installed.** If a file
explains what else must be true for it to work, that "what else" is the deliverable.

---

## Governance state

- **CODEOWNERS is advisory, not enforced.** `required_approving_review_count: 0`. Tested:
  PR #137 touched `CLAUDE.md` (an owned path) and merged with no review and no `--admin`.
  Cause is structural — the sole code owner authors every PR and GitHub cannot request a
  review from an author on their own PR. With one identity the only reachable states are
  gate-everything or gate-nothing.
- **The real fix is a separate GitHub identity for agent-authored PRs** (tracked as R2/R5).
  Today upgraded it from fine print to a demonstrated prerequisite.
- **`.github/CODEOWNERS` is not in its own list** — the file defining ownership can be
  edited without triggering a review. One line fixes it.
- Migration **`0042` must never be applied.** `REQUIRED_MIGRATIONS = 96`, matching live.

---

## Known unowned defects

- **`adj_close` is frozen at first ingest.** `adj_close = close` on 2,318 of 2,319 rows at
  the latest date; 35 symbols carry a >5× one-day step. Past dates are never re-fetched, so
  corporate actions never propagate.
- **60 `rs_fundamentals_pit` rows carry FUTURE `knowledge_date` values** (to 2026-09-13),
  because the vendor `report_date` can be scheduled. Harmless today (PIT filters
  `knowledge_date <= as_of`) but it undermines Stage 1's replay gate.
- **The one real position carries a demo thesis.** `HUBS.NYSE` is a real lot (24u,
  A$6,978.23, acquired 2026-05-31); its `theses` row is demo data. So the discipline layer
  evaluates a fabricated ladder against real capital — concentration and unrealised return
  are trustworthy; `STOP VIOLATED`, review-overdue and conviction-unset are not.
- **12 git worktrees**, one holding `main`, one with 25 uncommitted files on a branch 78
  commits behind. Clean by explicit path enumeration only — never a pattern, never
  `--force --force`; that combination destroyed a live builder's worktree on 2026-08-17.
