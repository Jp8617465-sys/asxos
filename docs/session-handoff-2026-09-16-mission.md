# Session handoff — 2026-09-16, F-E2E r2 loop mission

**Status:** current. **Read priority:** this is the mission record for the sprint plan at
`docs/proposals/production-sprint-r2-2026-09-16.md`; read that file for the full slice
definitions and windows. James's admission: "One loop mission. Given arbi has enhanced
permissions now it shouldn't need me" (2026-09-16). No human input arrived mid-mission beyond
one "Continue".

**STOP — read first.** Rule #11 stands throughout: no `signals` / `model_versions` read at any
point. No real order was placed; `asxos/capital/` stays empty. `.claude/**`, `north-star.md` and
`portfolio-policy.md` P5 were not touched.

## What shipped

Twelve PRs merged, in window order, each one concern per branch, each with `make check` green
before opening and full-check/targeted-ml-tests green before merge:

| # | Slice | Backlog | What |
|---|---|---|---|
| #283 | S1 | A-36 | `jobs/run_valuation.py` — weekly residual-income valuation sweep, `valuation_runs` (0054), sealed pre-registration |
| #284 | S2 | A-37 | Valuation as decision evidence; 16th challenge rule `rule_valuation_gap` (never blocking) |
| #285 | M1 | A-40 | Migrations 0055 (paired NULL cash/capital), 0056 (`cash_balance_assertions`), 0057 (`system_screen` source) — one §8 sitting |
| #286 | S3 | C-23 | `jobs/snapshot_paper_book.py` — daily arbi-declared paper book, A$25,000 (James's C1/D15 ruling) |
| #287 | S4 | C-24 | `jobs/discover_opportunities.py` — liquidity screen + deterministic ranker, system-screen theses at `pending_review` |
| #288 | S5 | C-25 | `jobs/build_decision_packets.py` — a challenged packet for every approved thesis, daily, on the paper book |
| #290 | S8 | A-39 | `jobs/apply_github_decisions.py` — issue **#289 "asxos — decisions"**, owner-only `APPROVE`/`REJECT`/`DISPOSE` comments |
| #291 | S7 | C-26 | `jobs/observe_decision_outcomes.py` — t0 + 21/63/126-session horizon observations, daily |
| #292 | S9 | C-14 | `asxos/domain/tax/feed.py` — the G12 dividend feed; rules James's three A-31 decisions; spec amended to v1.7 |
| #293 | — | C-24 close | Docs-only: closes C-24 on the live discovery evidence below |
| #294 | S11 | A-41 | `docs/proposals/global-universe-spike-2026-09-16.md` — research only, no build, no spend |
| #295 | S10 | D-16 | `derive_state()` replaces the hard-coded state ternary; byte-identical live output |

**Not built this mission:** S6 (brief "opportunities" card, A-38) — blocked on the nightly
`daily-product` routine landing **A-34**/**A-35** (the dark-launch DELETE verdicts on
`asxos/brief/compose.py`) first; the plan explicitly serialises S6 after them and reserves them
to the routine, not this mission. Both were still `open` on `main` at close.

## Rulings and decisions this mission made (arbi's, under the 2026-09-16 delegation)

Full text in `docs/product/decision-log.md` under `sprint-r2-*` rows. The load-bearing ones:

- **S1 close:** the DoD (i) bar of ≥1,000 `valued` rows is withdrawn as mis-set, not lowered —
  1,222 names (1,082 loss-makers + 140 negative-book) have no residual-income basis, so the
  method's reach is ~658 of 1,880. `defect:` recorded, not a lowered target.
- **S2:** `valuation_gap` never blocks (D14); 25% materiality is an arbi draft constant.
- **S3:** paper capital is **25,000 AUD** (James's C1 ruling), not the baseline memo's
  illustrative 100,000.
- **S4:** four gates on the ranker (liquidity, never propose `currency_unverified`, average-ROE
  quality, value ≥ price under both conventions); `candidate_snapshots` not written (no theme
  version for a value screen).
- **S8:** who may command is the repository owner login fetched from the repo itself, never a
  comment; a command's marker reply is the only idempotency key.
- **S9 / A-31 (the three G12 design-spike decisions, delegated by James 2026-09-16):**
  1. a tax `pass` is a **security-level characterisation only**, never a position;
  2. undeclared (NULL) franking is **never 0** — `tax-alpha.md` amended to **v1.7** (§3, §10,
     TC-26/26(b)/26(c));
  3. `tax_settings` stays unread (a security-level gross-up needs no marginal rate).
- **S10:** action states stay **structurally** unreachable this sprint — `derive_state` raises
  rather than guessing a direction when a non-`None` calibration is passed, because C-13 supplies
  neither the calibration value nor a position/stage-aware direction rule yet.
- **Superseded by James's 2026-09-16 admission** (recorded in the sprint plan): the r1
  reservations of C-3…C-8 (first live `--persist` runs), D-9 (tax §5.5 ratification) and A-31
  (G12's three decisions) all moved to arbi; none is an `AGENTS.md` §2 item.

## DoD — honest status at close (sprint plan §1 acceptance table)

| Clause | Status |
|---|---|
| (i) weekly universe valuation | **Closed with `defect:`** — bar mis-set (above); live: 1,879 rows, 573 valued, full blocked-reason histogram in the S1-close decision-log row |
| (ii) discovery | **Met** — `screening_runs` 1 row; 10 system-screen theses at `pending_review`, each with 2 `thesis_evidence` rows |
| (iii) brief opportunities card | **Not met — honest miss.** S6 was not built (blocked on the routine's A-34/A-35, out of this mission's control) |
| (iv) packets + t0 for every approved thesis | **Delivered, pending first live run.** S5/S7 are merged; their first scheduled firing is `daily-brief` at 2026-09-16 20:30 UTC — after this mission's session window. 13 approved theses exist to be packeted |
| (v) disposition | **Delivered, undisposed** — the plan's own anticipated wording. Issue #289 is live and pinned; no owner comment has been posted yet |

Two of five clauses hold live, one closes with a stated defect (not a lowered bar), and two are
honestly reported as not yet observed rather than assumed from a green workflow — per the
mission's own standing instruction that a green run is not evidence, `job_runs.rows_written` is.

## What's next (for whoever wakes next — a routine fire or a fresh mission session)

1. **Verify DoD (iv) and (v) after 2026-09-16 20:30 UTC.** Query `job_runs` for
   `snapshot_paper_book`, `build_decision_packets`, `observe_decision_outcomes`,
   `apply_github_decisions` (all should show one `success` row for `as_of=2026-09-16`); confirm
   `decision_packets` has ≥13 rows and `thesis_outcomes` has a t0 row for every one of them
   (including the two pre-existing 2026-09 packets). Close C-23/C-25/C-26 in `backlog.yaml` with
   the counts, the same pattern as the C-24-close PR (#293) in this mission.
2. **S6** (A-38, brief opportunities card) once A-34/A-35 land.
3. **r3 candidates**, per the sprint plan: first 21-session outcome (needs 21 trading sessions
   past the first packet); action states once C-13 (capital-risk calibration) exists; the global
   universe path S11 recommended (ASX-quoted global ETFs first, zero new cost or tax-module
   surface).
4. James's decisions issue (**#289**) is live. Nothing to prompt him with; the first
   `APPROVE`/`REJECT`/`DISPOSE` comment he posts will be answered by the next `daily-brief` run.

## Verification

Every merged PR's branch: `make check` equivalent (ruff + mypy + full pytest) green before
opening; full-check + targeted-ml-tests green on the merged head before squash. Final state on
`main` after #295: 4548 passed, 12 skipped, ruff and mypy clean.

No migration this mission beyond M1's three (§8 sequence followed: `migration-integration` green
on branch, `backup.yml` dispatched and its conclusion read `success`, applied via
`mcp__Supabase__apply_migration`, `schema_drift` clean, merged with the ledger versions and
backup run id in the PR body). No capital action. No Model A read.
