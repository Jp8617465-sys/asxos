# Session handoff — 2026-09-18 (the weekly screen reaches James)

**Status:** current
**Read priority:** read first. `docs/session-handoff-2026-09-18-routine.md` (the `daily-product`
fire that landed #328) is the companion; read it second. Routine handoffs carry `-routine`;
interactive ones keep the bare date.
**Session:** interactive, remote, auto mode, 2026-09-17 → 2026-09-18. James, in order: *"Create a
plan use our product to scan for investment opportunities … Don't build any new features"* →
*"Ensuring you are using arbi to lead this"* → *"Why doesn't it automate and detect selection —
that's the entire point"* → *"Deliver and auto open. Option 2 … Model A didn't work but we can build
something better that does work. @arbi take the lead and deliver this"* → *"We started in Jan, I still
haven't seen a single stock produced"* → *"How much of the universe was explored"* → *"What is the ROE
rule that is dominating? … how strong is our maths for valuing"* → *"Scope"* → *"Ready"*.
**`main` at close:** `611eb9d` (#332) · **4725 passed / 13 skipped** · ruff + mypy clean on 237
files · ledger head `20260917114415` (0060), 112 rows; 0045 absent, 0042 reserved.

---

## STOP — read first

**Rule #11 stands.** Nothing this session read `signals`, `signal_outcomes` or `model_versions`.
The residual-income model is not Model A, and the candidates card asserts the absence of Model A
vocabulary in every state it can render (`tests/test_brief_candidates.py`).

**Incident #327 is open and `pipeline-health` is red** — run `35289220374`, 23:59 UTC 09-17. Read
its log before acting on it: both notes are the known shape. The 09-16 "12 of 13" note is still
inside the 36-hour window (eleven of those are the #315 rows, since retired; the twelfth is HUBS),
and the 09-17 note is "1 of 2" — `HUBS.NYSE` alone. Cause 1 (`run_valuation` writing its same-day
re-run into `monitor.note`) is fixed in #332. Cause 2's code is fixed in #328; its data lands only
when `weekly-research` runs, **Saturday 2026-09-19 16:00 UTC, reserved to James and never
dispatched from a session**. A fire before then must not re-take the incident — the routine
handoff says the same. It closes when Sunday's `build_decision_packets` reports 0 of 2.

**#332 merged with that incident open, on purpose and recorded.** `AGENTS.md` §7 puts incidents
before features. #332 carries half the fix — cause 1, and the `has_price_plan` partition that
removes the "12 of 13" shape for good — and the other half is a schedule that is James's.
Decision-log row 2026-09-18.

---

## What the session found

James's opening ask was a runbook. The `/arbi` wake he then asked for found the runbook wrong
(L59: it told him to run by hand what `daily-brief.yml` already runs nightly), and his third
message — *why doesn't it automate* — was the real question. Probed rather than answered:
**detection had been automated since #287 and its output reached nothing.** `run_valuation`
values 1,879 names weekly; `discover_opportunities` records 537 through the liquidity screen and
16 through all four gates; `brief_section_gold` carried nine sections and none was discovery; the
V2 `new_ideas` collector was unshipped and filtered `governance_status='approved'`, which a machine
proposal can never open as. Eight months in, the sixteen existed for whoever ran SQL by hand.

## What shipped

| PR | Class | What |
|---|---|---|
| **#332** `611eb9d` | Amber | **The candidates card** — `asxos/brief/compose.py`, `section.py`, `brief.html.j2`: `theses` at `pending_review`, symbol order, sector / last close / model value / proposed / the approve command per row; EMPTY is not MISSING; the valuation LATERAL pinned on `method` and `terminal_convention` with a full `ORDER BY`. **Proposals restored** — `jobs/discover_opportunities.py` + `asxos/domain/discovery/proposals.py`: each fresh survivor opens as a `system_screen` thesis at `pending_review` with two `thesis_evidence` rows; 90-day cooling-off on `governance_events`; queue-depth 25 and runaway 30 breakers that refuse the whole run rather than truncate; `validate_symbol` before any row exists. **Planless partition** — `asxos/domain/theses/plan.py::has_price_plan`, shared by `decision_engine/builder.py` and `jobs/build_decision_packets.py`: an approved thesis with no plan is `awaiting_plan`, never `failed`, never in `monitor.note`. **`run_valuation`** logs its same-day re-run instead of noting it (AST guard). **Runbook** `docs/product/runbooks/opportunity-scan.md`, red-teamed twice. Nine decision rows, L59, five facts, `CLAUDE.md` schema block to 0060 / 112. |
| **#331** | — | The relative-valuation lens, scoped in two phases. An issue; ships no code. |

**What #332 does not do, by design.** No target, no stop, no entry band, no rank, no truncation —
`RESPONSE_RULE` (#306) is intact. Decision #0b was **reversed on James's instruction for the
proposal half only**; the reversal row states how each of #0b's two hazards is met mechanically
(nothing truncated, so no rank; `pending_review` rows never enter the builder, so no nightly red).
No level gate on approval either: it would make the phone-comment `approve thesis <id>` surface
unsatisfiable, and `enter_thesis` already refuses capital without a plan.

## Questions James asked, answered on the record

- **Coverage.** The funnel is **1,879 → 537 → 332 → 270 → 138 → 16**: `au_equity` → liquid (ADV
  ≥ A$250k, cap ≥ A$100m) → valued → currency-verified → average ROE > Ke → value ≥ price under
  both conventions. The 517 outside 1,879 are 487 ETF / 18 hybrid / 12 LIC. In
  `project-facts.md`.
- **"One lens terminating so many."** The average-ROE > Ke gate removes 132 of 270. It is a
  quality gate on a 3-period average against Ke ≈ 8.9%, and a residual-income model with the
  registered terminal convention finds discount-to-assets and cyclical-peak names and never
  growth compounders (baseline inquiry 2026-09-16). Industry practice is several lenses with a
  reconciliation; ours is one pre-registered single-stage model, sealed and **null on its own
  test** (#304), which is exactly why it may state a number and may not set a price.
- **"Scope."** #331: phase (a) the record, prereg and sealed test for a peer-relative lens,
  buildable after #327, peer leg only; phase (b) the gate, card and proposals, conditional on
  (a)'s verdict **and a James ruling** on `RESPONSE_RULE` (three branches in the issue). Red-team
  found seven errors in the draft; each verified and corrected before filing.

## Review loop (Tier A, CLAUDE.md §Review consult)

`security-engineer`, read-only over the whole diff: four findings, each verified against source
before acting (L55). **M1** and **N1** taken with tests — the LATERAL's `terminal_convention` pin
(**L60**) and `validate_symbol` ahead of the proposal transaction. **N2** (`builder.py` copies
`thesis_text` as `verified` evidence whatever tier the evidence rows carry), **N3**
(`weekly-research.yml:89-95` says "Opens NO theses", now false; `.claude/rules/job-conventions.md`'s
`ASXOS_PERSONAL_USE` list has rotted) and **N4** (the discovery step runs before
`sync_fundamentals`) are recorded as follow-ups in the decision log and the roadmap.
`refactoring-expert`: `_status_for` extracted in `section.py`. `technical-writer`: the runbook's
§0 / §4.1 / §5 / §7 / §11 / §13 for the restored proposal half; two of its counts were wrong against
the live set and were corrected before commit. Two `arbi-red-team` CHALLENGE verdicts earlier in
the session, every finding verified.

## What is NOT done, and must not be read as done

- **AC1–AC5 are unmet until the first live fire** — Saturday 2026-09-19 16:00 UTC,
  `weekly-research`, James's. The evidence is `discover_opportunities` `job_runs.rows_written = N`
  with `error_message` NULL, and N `pending_review` `system_screen` theses each carrying two
  `thesis_evidence` rows and three `evidence_citations`. Not the green run. One-shot check-in
  `trig_01TMyoZHedGbatdz3yY742dr` fires 18:30 UTC Saturday into this session to read it, and arms
  one more for Sunday's brief.
- **Tonight's `daily-brief` (20:30 UTC) is the first to render the card, EMPTY.** "None … ordinary
  weekly state" is the correct reading until Saturday. A banner is not.
- **Seven of the current sixteen are LICs / A-REITs misclassified as `au_equity`** (six funds plus
  `BWP`). They will be proposed. Reject on sight — the runbook §5 prints the command — and the
  90-day cooling-off keeps them out. The fix is `universe.security_kind`, one row each
  (`m14_candidate_security_kind_enum`).
- **N3 + N4** are one Amber `.github/workflows/` PR, taken when `weekly-research.yml` is next
  touched. **N2** is its own PR: every packet's narrative tier moves.
- **If EODHD does not answer its fundamentals endpoint for a US ticker**, #327 does not close on
  Saturday either — the routine handoff's honest unknown, still unknown.

## Yours (AGENTS.md §2 or a ruling)

1. **#331** — the `RESPONSE_RULE` ruling, three branches in the issue. Not urgent; nothing builds
   before R-01 and #327's rows.
2. **#319, #334** (`.claude/**`) — drafted, yours to merge. (**#335**, `fx_rates` revised in
   place, asks for a triage call; it is not §2 and arbi can take it — listed here only so it is
   not lost.)
3. **From Sunday: the Candidates card.** Approve or reject each row. A row left more than 14 days
   trips the evidence-staleness check on approval; the queue is meant to be worked.

## Next wake

Take the ranked queue. Do not re-take #327 before Saturday's data. If Saturday's check-in reads
`rows_written = 0` with a non-empty passing set, read `proposals.selectable`'s breaker path in the
job log first, not the gates — both breakers refuse the whole run by design.
