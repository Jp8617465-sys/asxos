# Session handoff — 2026-09-06 (attended window AW-01, Recipe R2)

**Window:** 12:15 → 20:15 UTC, James: "I authorise you to execute this". Envelope:
`docs/proposals/arbi-window-aw01-2026-09-06.md`. Ledger row `close-2026-09-06` (3.9 provisional).
**Session shape:** out-of-fence (launched outside the repo root; hooks never loaded — R17-class) at
James's explicit choice; every write path pre-checked through `authority-guard.sh` by synthetic
payload; `arbi` / `arbi-red-team` emulated by subagents carrying the agent files verbatim;
`guilfoyle` not run (account session limit hit at 12:42 UTC). Every figure below is **measured**
unless marked *inferred*.

## STOP — read this first: Model A's quarantine (rule #11) stands, untouched

Nothing this window read `signals` as evidence. #212 touches `asxos/domain/prices/` and `jobs/`
only; #213 is documentation. Rule #11 is standing policy, not up for reinterpretation.

## What this session was

A wake, one live-ops fix, and a close. The plan (approved 2026-09-06) named three substantive PRs:
the queue-to-truth reconciliation, D-9a (tax §5.5 + the `lots.py` partial-draw defect), and C-13a
(the P5-01 risk-calibration draft). The wake's live probes surfaced a **self-inflicted red** —
`check_cron_health` failing 09-03/04/05 on a `sync_prices` NO_EQUITY_DATA that was a false positive
after #171 made `clock.today()` Sydney — and both emulated agents re-ranked it to THE ONE THING
under "unblock before you build". It was built and drafted (#212). The agents' reports then sat
undelivered in the mailbox from 12:36 to 19:15 UTC; with an hour left, PR-B and PR-C were **parked
with their specs** (below) rather than truncated mid-node.

## Where the code is

| PR | Branch | What | State |
|---|---|---|---|
| **#212** | `claude/aw01-sync-prices-completeness` | `select_sync_target` — the completeness verdict targets the freshest *closed* session; 5 tests; 4,387 passed / 1 skipped | draft, CI pending at close |
| **#213** | `claude/arbi-wake-close-2026-09-06` | wake + close record: `roadmap-state.md`, `backlog.yaml` re-seed, scorecard (E-16), `latest-snapshot.json`, `james-inbox.md`, `dark-launch-exit-plan.md`, `decision-log.md`, `arbi-run-ledger.md`, `CLAUDE.md:40-56`, the envelope, the issue-snapshot patch, this file | draft, CI pending at close |

**Recommended merge order:** #212 first (it stops a daily red), then #213. Both independent of
each other; neither stacks. If you want `CLAUDE.md` merged separately from the run record, say so
and it splits out of #213.

## What the wake found (all on `main` truth as of 12:21 UTC, re-probed 19:15 UTC)

- `main` @ `e058be3` (#209) — the whole Amendment H stack merged 09-05 (#185–#201, plus #178,
  #203, #206–#209). `roadmap-state.md` and `backlog.yaml` were both still describing the pre-merge
  queue; the picker was hiding your real clicks behind stale dependencies. Fixed in #213.
- `backup.yml` **green** 09-05, and **again 09-06 twice**: run 34045223384 (16:22 UTC, dump) and run
  34048829799 (17:30 UTC, dump + **`restore_drill` success** — the first drill since #186). C-1 now
  needs only **B-3** (the deadman secret) and the pasted run ids.
- `issue-snapshot` **red** since 09-06 11:27 UTC (run 34030294978): it pushes to `main` and the
  ruleset rejects it (`GH013`). Worse: `docs/ops/github-issues-snapshot.json` on `main` is `[]` —
  the lane has never archived an issue. `.github/**` is yours: patch + four options in
  `docs/proposals/claude-config-patches-2026-09-06/issue-snapshot.md`; backlog **A-24**.
- `pipeline-health` scheduled runs were **red 09-02/03/04 UTC** — the cron-health false positive.
  A latest-run-only view (the one the wake snapshot used) showed the lane green; the red-team's own
  `gh run list` caught it. Snapshot corrected; lesson below.
- `knowledge_tier` populated 54,459 / 54,466 (C-2 observed); weekly-research green three Saturdays
  (C-11 observed); 0049–0052 applied, 104 ledger rows; **0045 still deliberately unapplied**.
- Dark surfaces #1/#4 six days past expiry, still unruled (re-raised in `dark-launch-exit-plan.md`);
  #3 has 24 days.

## What did NOT happen, and why

- **PR-B (D-9a) — parked.** Spec §5.5 lot selection + numeric TC + the `lots.py` fix as a proposed
  diff, merge contingent on D-9, `tax-spec-conformance` on record (red-team condition iii). The
  defect is verified live at `asxos/domain/tax/lots.py:93-101, 110-125`: `combinations` preserves
  input order and `_draw` puts the partial on the last lot of each combo, so which lot bears the
  partial is never explored and post-discount gain is not minimised when per-unit gains differ. The
  natural fixture is the 6,250-vs-5,000 case in `docs/session-handoff-2026-09-03.md:110-113`.
  Branch was created and removed untouched. **Next window's #2** (after C-13a per arbi's re-rank,
  or #1 per the red-team's "defensibility wins ties" — James picks).
- **PR-C (C-13a) — parked.** `docs/proposals/p5-01-risk-calibration-2026-09.md`: the F4 calibration
  as a ruling-ready proposal — numeric loss / drawdown / position limits as options with one
  recommended default each, every number traced to an existing constraint (`portfolio-policy.md`,
  ADR D1 cash floor 7.5%, D2 0% leverage, F4's universal gates), a worked application to
  `dpk-cba-1-2026-09-01` showing which gates bind and that the negative-control packet still closes
  abstain on `price_detached`, an explicit `model_independence` statement, and a "changes nothing
  until James merges an edit to `portfolio-policy.md`" clause. P5 is draft-only
  (`arbi-permission-model.md:171`). Consults: `portfolio-invariant-guard`, `arbi-red-team`.
  "Closes at abstain" is a **policy** gate (`portfolio-policy.md:35-37`), not a code path.
- **guilfoyle** never planned the graph — the account's session limit was consumed by the two
  emulated agents. The main loop executed the plan's own graph.
- **S1 doc-expiry sweep / S2 issue-snapshot fix** — not built by James's ruling (R2 ceiling;
  patch-for-James); recorded as E-17 (attended) and A-24.
- **Tonight's daily-brief (20:30 UTC, D-14)** fires after stand-down — read it Monday. Note it will
  also emit the false DEGRADED once more unless #212 has merged.

## What is waiting on James — the morning report

**Decisions needed (time-boxed first)**
1. **D-1 / D-2** dark surfaces #1/#4 — six days expired; drafts merged in #190; one word each.
2. **B-3** add `HEALTHCHECK_URL_BACKUP_IRREPLACEABLE`, then **C-1** paste run ids 34048829799 (drill)
   and the next dump — closes live defect #1's gate. **B-2**'s workflow patch is still owed (the
   drill asserts 14 tables; 0048–0052 tables are outside it).
3. **A-24** choose the issue-snapshot archive route (recommend B) and apply the patch.
4. **C-5** a second `big-4-banks` member — the Stage 4 positive control.
5. **D-3** retire CBA thesis #1; **D-8** thresholds; **D-10** retention; **C-15** Stage 1 wording;
   **B-15** D10 — now also decides the issue-snapshot shape.
6. **H-32 / C-13** and **H-29b / D-9** — the two rulings the parked drafts exist to enable.

**Completed PRs:** #212 (fix), #213 (record) — both draft.
**Skipped / deferred:** PR-B, PR-C (specs above); S1, S2 (by ruling); C-14 (needs the G12 feed).
**Risks found:** the monitoring lane cries wolf every weekday until #212 merges; the issue-snapshot
lane has archived nothing since it was built; a latest-run-only probe masks scheduled reds.
`scripts/check_ledger_coverage.sh` is red on six **pre-existing** close rows (2026-08-20/21/22 and the
three 08-22 sub-rows — no or multiple Amendment E fields); untouched here (append-only ledger); the
new `close-2026-09-06` row passes.
**Recommended merge order:** #212 → #213.

## Files to commit (Step 4 — reminder, not a push)

All on `claude/arbi-wake-close-2026-09-06` (PR #213) — nothing here merges, pushes to `main`,
deploys, or migrates:

- `docs/product/roadmap-state.md` — header, live ranked block, In-flight note, Last wake snapshot
- `docs/product/backlog.yaml` — the re-seed (A-0…A-18, B-13a/B-14a, C-2, C-11; A-24/A-25/A-26/E-17/E-18)
- `docs/product/product-health-scorecard.md`, `docs/product/state/latest-snapshot.json`
- `docs/product/james-inbox.md`, `docs/product/dark-launch-exit-plan.md`
- `docs/product/decision-log.md`, `docs/product/arbi-run-ledger.md`
- `CLAUDE.md` (migration paragraph), `tests/test_backlog_next.py` (seed pin)
- `docs/proposals/arbi-window-aw01-2026-09-06.md`,
  `docs/proposals/claude-config-patches-2026-09-06/issue-snapshot.md`, this file

## Standing lessons from this window (working-memory candidates; `/arbi-dream` decides)

1. **A latest-run-only workflow view masks scheduled reds.** The wake snapshot listed one conclusion
   per workflow and showed `pipeline-health` green while three consecutive scheduled runs were red.
   Probe scheduled lanes with `--limit ≥ 5` (or record "last failure"), and let the snapshot schema
   carry more than the newest row.
2. **A "through today" window plus a timezone fix is a false-positive generator.** #171 was right to
   make `today` Sydney; the completeness check anchored on `max(day_counts)` was written against the
   old UTC contract. Any check that grades "today" must exclude the not-yet-closed session
   (`select_sync_target`). Grep for other `today`-anchored windows before the next clock change.
3. **Emulated agents share the account budget and speak only through the mailbox.** Two agents
   consumed the session limit and their reports waited six hours. When agents are emulated, check
   `ListAgents` once after spawning, cap their reading, and never let the window's build depend on
   a report arriving.
4. **Reversible work can still be lost to time, not to gates.** The right response was to park with
   specs, not to rush PR-B/PR-C into a truncated draft — the recipe's "never truncate a PR mid-node"
   held.

Nothing here merges, pushes to `main`, deploys, or migrates. That is `/ship`'s job, done deliberately.
