# Session handoff — 2026-09-14, third session (`/arbi` wake + product sprint)

**Status:** current
**Read priority:** read first. Then `docs/session-handoff-2026-09-14-2.md` (the merge-train
session) — this session executed its carry-forward list, so that file is now mostly discharged
and is useful as the record of why each item existed.

**Filename note:** third session of the same calendar day. `-2` was the merge train; the
unsuffixed file was the grants settlement.

## What James asked for

A `/arbi` wake, then "keep going as one continuous mission (`/loop`, self-paced) until the stop
condition holds" — an eleven-item mission: clear the substrate in Hour 1 and then stop touching
it, then product work on the model-independent moat, one concern per PR, landing each before the
next.

## Outcome — every figure measured this session

**6 PRs opened, 5 merged, 1 handed over.** `main` moved `b564220` → `45727f8` + #266.
Test count **4294 → 4322** (+28), `ruff` and `mypy` clean throughout. No migration applied,
no capital action, no Model A output used.

| PR | Item | Class | State |
|---|---|---|---|
| #261 | 1 — `.claude/` grant removed from the lanes' settings | Green | merged `ced2092` |
| #262 | 2 — `DENIED_FILES` re-derived from `AGENTS.md` | Green | merged `5a5f712` |
| #263 | 4 — `--permission-prompts none`, pin → v1.0.223 | Amber | merged `f7c858c` |
| #264 | 5 — `reversible-work-window` rewrite | Green | **OPEN — YOURS** |
| #265 | 3 + 6 — lane-arming trigger, AUTONOMY blocker | Green | merged `9d4b002` |
| #267 | 8 — dark-launch verdicts | Green | merged `45727f8` |
| #266 | 7 — #228, cash reported unmeasured | Amber | merged |

## The three findings worth reading even if nothing else

### 1. The lanes' real permission surface is not under `.claude/`

`#261` removed the `.claude/` grant from `.github/runner/claude-user-settings.json`. But the
deeper issue only surfaced doing `#262`: **that file is not itself protected by anything.** It
is not under `.claude/`, yet its `autoMode.allow` array *is* what the classifier reads for every
headless lane. So the backlog picker could hand a fire a task scoped to the file that grants the
fire its permissions. It is now in `DENIED_FILES` for exactly that reason. #261 closed the hole
from the grant side; #262 closed it from the task side.

### 2. `DENIED_FILES` was 17/30 dead, and that is why the lane had nothing to do

The 09-14-2 handoff said three deleted `arbi-*` docs. Measured: **17 of 30 entries** named files
that no longer exist, and the prefixes excluded `.github/**`, `migrations/**` and four
`asxos/domain/` packages — most of what `AGENTS.md` §14 says is arbi's. Every prior pin of the
seed test asserted `picked == []`, and that was read as a property of the backlog. It was a
property of this list. After the trim the picker yields **E-11** and a **42-row click-list**.

### 3. The toolwatch report's premise was already stale when it was read

`#259`'s ADOPT #1 measured the pin at `a874e9e` (CC 2.1.251) and asked for a 19-release jump.
**#214 landed `56cf60f` (v1.0.222, CC 2.1.269) hours later in the same session**, so both
capabilities it wanted were already in the bundle. What was missing was never the version — it
was *using* the flag. Worth generalising: an agent lane's findings age against the same session
that produced them.

## Dark-launch: the queue is empty for the first time

All four surfaces carry a live verdict. #1 and #4 were **14 days past expiry**; #3 was ruled
**16 days early** because inspecting it falsified its premise.

- **#1 portfolio brief → DELETE.** The finding that decides it: *the flag was never what kept
  this dark.* `_portfolio_section` needs three gates; `build_portfolio` last succeeded
  **2026-08-01** against a 2-day freshness gate, and `approved_for_allocation = 0` so the
  allocator hard-fails by design. Flipping the flag today changes nothing. And `compose.py:1163`
  says in as many words that the discipline digest is "deliberately not" behind this flag — the
  model-independent cards this KEEP-DARK claimed to protect already ship.
- **#3 V2 brief tree → DELETE the dark rendering path.** Two claims in the standing verdict were
  wrong: the gate *is* plumbed (`composer.py:94`), and its collectors are *already in
  production* (all ten imported at `composer.py:28-36`, run on every brief). Only a renderer and
  an already-archived template are dark.
- **#4 paper-trade evaluator → KEEP-DARK, re-scoped, 2026-11-30.** Kept because its code has
  live callers, not because it earns #1's sign-off — that job is void now #1 is DELETE.

**Both #1 and #4 were mis-assigned to James** and are closed in `james-inbox.md` with the
reason: `AGENTS.md` §2 reserves the personal-use invariant, capital, and spend over cap. These
gates sit *behind* `ASXOS_PERSONAL_USE`. Part of why an expiry got carried five times is that it
sat in a queue nobody was obliged to empty.

## #228 — what landed, and what is deliberately still open

**#228 stays OPEN.** #266 closes the live harm; the authoritative source is the remaining work.

Landed: the decision engine stops consuming `portfolio_daily_snapshots.cash_aud`, which is
`profile.cash_floor_pct * profile.capital_aud`. `PortfolioState.cash_pct` is `Decimal | None`,
required with no default. `rule_cash_floor` reports `evaluated=False`; the sizer returns zero;
the builder declares the gap. Reproduced live before changing anything (2026-09-11 snapshot:
`cash_aud` 0.000000 = the policy-derived 0.000000).

**Deviation from the issue's red test, and the reason.** The issue asks `_snapshot_one_day` to
raise. That job is **step 3 of 12** in `daily-brief.yml`, and `job-conventions.md` says step
order is the dependency graph — so it would kill the brief daily until a human records a cash
balance, manufacturing a §7 incident out of paperwork. The assertion moves to where its blast
radius is one command.

**Before-image for the follow-up migration, measured not assumed:** `portfolio_daily_snapshots`
holds **72 rows, 26 with non-zero `cash_aud`, max 25000.000000**, 2026-05-27 → 2026-09-11. That
falsifies "they're all zero anyway" — run it before any backfill.

**`backend-architect`'s three-PR split is the plan.** PR 1 landed. PR 2 (migration 0055: NULL
`cash_aud` *and* `capital_aud` together under a paired CHECK, so "capital with an implied zero
cash" is unrepresentable). PR 3 (migration 0056: `cash_balance_assertions` — dated, sourced,
append-only balance assertions, staleness derived at read time, not stored).

**Residual stated in the PR, repeated here because it bites the next reader:** `capital_aud` is
still `holdings_mv_aud + cash_aud`, so the placeholder remains in every weight's denominator.
With the live floor at `0.0000` that term is 0 and the weights are exact. It stops being exact
the moment the floor is set non-zero.

**Security review (Tier A, `security-engineer`): PASS** on all five safety questions, two Medium
findings fixed before merge — the bear case was asserting a clean register sweep with D1
unchecked (`cash_floor` is the first register rule that can be skipped), and neither builder hunk
had a test. **Writing those tests, the first draft of both passed while covering nothing** — the
evidence-item dedupe guard silently skipped one branch, and the default CBA fixture is
price-detached so the headline never reached the branch under test. Both commented in place.

**Carried forward, not fixed:** `staging.stage_order` has two independent gates and no
`PortfolioState` parameter, so its D1 protection is entirely inherited. Before #266 an
unmeasured-cash book was refused by gate 1 whatever size was passed; now only gate 2 stands. Not
exploitable — `stage_order` has no production caller. Whoever wires its first real caller must
see this.

## Yours

1. **PR #264** — `.claude/skills/reversible-work-window`. arbi drafts, James merges (`AGENTS.md`
   §8). It still instructed *"Draft PR is the durable stopping point. Never mark
   ready-for-review or merge inside a window"*, which §8.3 contradicts in as many words.
   Everything its floor rested on (`arbi-permission-model.md`, `harness-profiles.md`, four guard
   hooks, `ARBI_UNATTENDED`, Render) is deleted. The runbook rides with it.
2. **The `AUTONOMY` repo variable is still unverified.** Second session, second distinct cause:
   the merge train had no tool; this session's agent proxy **403s** `/actions/variables` and
   `/actions/secrets` (`{"message":"Access to this GitHub Actions path is not permitted through
   this proxy."}`), and there is no `gh` CLI. Not absent, not present — unverified.
   `gh variable list --repo Jp8617465-sys/asxos`, delete if present. Nothing is blocked behind it.
3. **A-20 (`HC_BACKLOG_URL`)** is still open and still gates arming `backlog-roll` specifically.

## Item 9 — blocked, and the blocker is more useful than the clock

Three measured blockers: **#228 is not closed** (its own stated precondition); **nothing writes
`paper_book_snapshots` on a cadence** (1 row, `as_of` 2026-09-07, written by #229's landing, no
workflow mentions the paper book); and **the gate points at the wrong instrument** —
`has_enough_paper_weeks` counts `rebalance_runs` (5 rows, newest 2026-07-11) plus
`build_portfolio` continuity (last success 2026-08-01), so it returns `False` correctly and can
now never return `True`, because Amendment F ratified that cron deleted.

Starting a dated clock tonight would have produced a date nothing could satisfy, feeding a flag
now ruled for deletion. **Unblocking sequence:** close #228 → give the paper book a cadenced
writer → re-point `has_enough_paper_weeks` at `paper_book_snapshots` → then start the clock.

## Item 10 — the item does not exist

"The thesis-in-the-same-sitting pairing item named in the 09-10 handoff" is **not in the 09-10
handoff.** That file's residue list is four items: `DENIED_FILES`, `reversible-work-window`, the
359-occurrence citation residue, and retired-doc citations in `proposals/`/`archive/`.

The phrase occurs in exactly two places repo-wide, neither defining it:
`session-handoff-2026-09-14-2.md:141` (which attributes it to 09-10) and
`roadmap-state.md:754`, whose only attached sentence is *"The thesis numbers are still James's."*

So it is a name that was carried forward without a spec. Rather than invent a plausible reading
and build it, it is recorded here as under-specified. Its nearest defined relative is
`m14_candidate_agentic_thesis_drafter` (`roadmap-state.md:1772`), which has a real four-part gap
list — and whose item (1), the agent-authorship boundary, is an open James ruling (click
**D-12 / C17**). **If the pairing item means something, say what; otherwise D-12 is the real
next move in that area.**

## Item 11 — scheduled, not skipped

The first scheduled `daily-brief` after the `resend` 2.39→2.43 bump had not fired by session
end. **The cron says `30 20 * * 0-4` but the four most recent scheduled runs were created at
22:31, 22:42, 22:40 and 22:51 UTC** — a consistent ~2h delay, so the real window is 22:30–22:55.
A self check-in is armed for **23:00 UTC** (`trig_01EaYV49f4dx2G8zUVNi5NCt`) to read the run and
treat red as a §7 incident. The last run, `34787074094` (2026-09-13, success), predates the bump.

## Lane arming — trigger set, not met

Lanes stay `workflow_dispatch`-only. Arm when **both**: (a) ≥10 open click-list rows —
**MET, 42** (though ~8 name PRs the merge train closed, so the live count is nearer 34); and
(b) a week of product PRs to triage — **NOT met**, today is day one. Earliest re-check
**2026-09-21**. REVERSAL: one workflow PR.

## Verification

- `.venv/bin/pytest tests -q` on the final branch: **4322 passed, 1 skipped**. `ruff check`
  clean; `mypy asxos` clean over 218 source files.
- Migrations unchanged: **106 rows**, head `20260914123930` (0054). 0045 still deliberately
  unapplied, 0042 still reserved. No migration authored or applied this session.
- All 21 jobs with a run in the last 4 days are `success`. `prices.dt` and
  `portfolio_daily_snapshots.as_of` both 2026-09-11 (Friday — correct for a Monday).
- `backup.yml` ran on schedule, run `34882922972`, `success`.
- Open PRs at close: **#264** (James's). Open issues: **#228** (deliberately).

## Next wake

1. **#228 PR 2** — migration 0055, the snapshot stops writing a number it did not measure. Run
   the before-image query first; it is in this file and in #266's body.
2. **Execute the two DELETE verdicts** (#1 portfolio brief, #3 V2 rendering path) — each names
   its scope, each is its own revertible PR.
3. **#228 PR 3** — migration 0056, `cash_balance_assertions`.
4. The 359-occurrence citation residue from the 09-10 handoff, triaged by whether a doc is *read
   as current* rather than by reference count.
