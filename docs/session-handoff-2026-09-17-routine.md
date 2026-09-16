# Session handoff — 2026-09-17, `daily-product` routine (catch-up fire)

**Status:** current
**Read priority:** read after `docs/session-handoff-2026-09-16-loop.md` (the session that produced
the null verdict this fire applies). Interactive-session handoffs keep the bare date; routine
handoffs carry `-routine`.

**STOP — read first.** Rule #11 (Model A) stands, untouched; nothing in this fire read `signals`.
Separately, the **residual-income model is now DEMOTED in code** (#306 → #309): it emits no
target price, entry band, stop or ranked list. That is a demotion under a sealed response rule,
not a rule-#11 quarantine — the primary endpoint was positive and conviction was not inverted.

## What fired

`trig_019hfSFbVCdKQA5PPxJM9MMH` → bound session `session_01HyKLpP6LMTm9wio1oL9e5m`, fire
2026-09-16T19:50:54Z (05:50 AEST 09-17), `doc_sha=66bcb93`, START/END on #270. Budget 120 min.
This is the **catch-up** for the 17:38 UTC fire that was delivered but never ran (#308 records
the rebind); the scheduler recorded that one as `SUCCEEDED`, which for a bound routine means
*delivered*, not *ran* — the ledger detector worked.

**Gate (§1), all four held:** (a) `nightly-check` 35137435106 on `main` `success` (scheduled,
head `7bb9d96`); (b) no open `incident` issue; (c) ledger #270 has no dangling START (the
steward's 19:45 START has its 19:48 END); (d) 0 open PRs → picker exit 0, eligible 3, pick
**A-34** — but the roadmap's live block (dated 2026-09-16, within 7 days) ranked **#306** at #0,
and Amendment K says the roadmap wins.

## The one thing — #306, and the call inside it

`arbi-red-team` was dispatched first (§3: a large call) and returned **NO CHALLENGE** with four
conditions: record the #0b design call as a decision; keep `require_personal_use_job()`, the
workflow env and step, the four gates and `MIN_ADV_AUD`; file the backlog row and fix C-24/A-38;
state the proof as pending Saturday's run. All four carried.

| What | Where | Result |
|---|---|---|
| Sealed rule | `asxos/domain/research/registry/vp.py::RESPONSE_RULE` | "stops emitting target prices, entry bands and ranked 'opportunities'" — now pinned to the code by a test |
| `plan_for`, the three constants, `TIMELINE_DAYS`, `liquidity_factor`, `rank`, thesis prose, `ThesisPlan`, `Opportunity.plan/.score/.liquidity_factor` | `discovery/ranker.py`, `discovery/types.py` | deleted |
| The four gates | `ranker.passing()` | kept; output is symbol-ordered, a set not a rank |
| `jobs/discover_opportunities.py` | | records the `screening_runs` row, logs the passing set, opens **no** thesis, `rows_written=0` with a note naming #306 |
| `weekly-research.yml` | step + env | unchanged; comment corrected |
| Ten `system_screen` theses ids 14–23 | `theses`, `pending_review`, opened 2026-09-16 | **untouched** (stored records; no Supabase write in a routine) |

**DECISION (#0b):** "still state a falsifiable number per thesis" is the model value as the
challenge already reads it — `valuation_fact` evidence and the `valuation_gap` rule in
`decision_engine/builder.py` — for theses a human has written and approved. Nothing is derived
from the model value by constant multiplication, and the screen proposes no theses (a top-K by
score is a ranking; every passing name with NULL levels recreates the 11-auto-seeded defect and
floods #289). **TAKING:** stop proposing and stop ranking. **REVERSAL:** one revert.

Class **Amber** (investment output; one workflow comment). Amendment E field: **`captures:`
pending** — Saturday 2026-09-19 16:00 UTC `weekly-research` should show `job_runs.rows_written=0`
for `discover_opportunities` with the note, and `theses` gaining no `system_screen` row. The
routine's `nightly-check` proof does not exercise the weekly job, so it is not claimed here.

## Also done this fire

- **Row A-42 filed** (Amendment K: the loop close ranked #306 at #0 without a row, so the picker
  and the roadmap disagreed again). **C-24** annotated as demoted; **A-38** (S6 brief card)
  re-scoped — no ranked list, no targets — and now depends on A-42.
- Roadmap live block re-ranked (#0 done, #0b decided, #1-#5 carried unchanged: A-34 → A-35 →
  #228 PR 2 → E-20 → carried); snapshot fence refreshed.

## Findings about the routine itself (for `docs/ops/routines/` — draft-only from here)

1. **System Python in the sandbox is 3.11; the project pins 3.12.** `pip install -e ".[dev]"`
   fails on `numpy==2.5.3`. `uv` is present: `uv venv --python 3.12 .venv && uv pip install
   --python .venv/bin/python -e ".[dev]"` works (about two minutes). Gate (d).2 should say so —
   yesterday's finding 1 named `pip install` and that no longer suffices.
2. **The bound session again carries the write-capable `Supabase` connector** beside
   `supabase-ro` (both present; the write one unused). `README.md` already records this.
3. **`HC_ROUTINE_PRODUCT_URL` is unset** → `deadman=unset` in END.
4. **The gate's item order can disagree with Amendment K.** §1(d) returns the picker's pick
   (item 2) before the roadmap block (item 3); when the roadmap ranks something the yaml lacks,
   the picker's answer is the wrong one. Filing the row in the close fixes it for the next fire,
   which is what A-42 does; the doc could say "check Amendment K before accepting (d).2".

## Verification

- Baseline `make check` on unmodified `main` (`66bcb93`) in the routine sandbox: **4603 passed /
  12 skipped**, ruff clean, mypy clean on 231 files.
- On the branch before push: see the ledger END comment on #270 for the figures (recorded after
  this file was written).
- Migrations unchanged: ledger head `20260916185525` (0058); 0045 unapplied; 0042 reserved.
- No migration, no capital action, no Model A output, no Supabase write.

## Yours

Nothing under `AGENTS.md` §2. Two carried from the loop close, neither blocking: the
`.claude/rules/job-conventions.md` dispatch-scope reconciliation (`.claude/**`, James's to
merge); `HC_ROUTINE_PRODUCT_URL` / detaching the write-capable `Supabase` connector.

## Next fire

(d).1 none → (d).2 exit 0, pick **A-34 — DELETE verdict #1 (portfolio brief)**, scope in
`dark-launch-exit-plan.md` §1; the roadmap agrees. Then A-35, then E-20. **Attended, not
routine:** reject the ten `system_screen` theses ids 14–23 (`asx thesis reject` ×10 — A-39's
#289 parser is still open, so a comment executes nothing); #228 PR 2 (migration).
