# Governor drafts — 2026-09-02

**Status:** draft for James's ruling — nothing here is in force
**Scope:** four decisions the 2026-09-02 `/arbi` wake surfaced as overdue or undecided, each
drafted to the point where the ruling is a word, not a research task
**Owner:** arbi drafts (Amendment H §3); James rules
**Campaign node:** H1-G (Wave 1)
**Superseded by:** N/A — supersede this file when each ruling is recorded

Every figure below was probed live on 2026-09-02 against production (read-only) or cited to a
file. Nothing rests on training knowledge or on a doc's own claim about itself.

---

## 1. Dark surfaces #1 and #4 — EXPIRED 2026-08-31, verdict overdue (click H-16)

### The finding that changes this decision

**Surface #1's ship condition is currently unreachable, and not because of a date.**

Its gate is "4 weeks of paper-trade sign-off (M13.8)". That sign-off is computed by
`has_enough_paper_weeks()` (`asxos/domain/portfolio/paper_trade.py:295`), which is two
independent conditions:

| Condition | What it checks | Live state 2026-09-02 | Result |
|---|---|---|---|
| **Maturation** | ≥1 `rebalance_runs` row old enough to have 4 weeks of subsequent price history | 5 runs exist, latest `as_of` **2026-07-11** — 53 days old | **PASSES** |
| **Continuity** | the weekly `build_portfolio` cron actually ran across the window: no blackout > 14 days, and the cron is *currently alive* (`_cron_was_continuous`, `:270`) | `build_portfolio` last succeeded **2026-07-11**, 6 successes lifetime, and it appears in **no** `.github/workflows/*.yml` | **FAILS, permanently** |

Continuity fails because `build_portfolio` is not scheduled anywhere — and it is not *supposed*
to be: **Amendment F (James, 2026-08-19) ruled `build_portfolio` DELETED**, replaced by the
segment-valuation → selection → exposure architecture (`roadmap-state.md`, Amendment F). The
job file still sits in `jobs/`, but nothing runs it and nothing should.

So surface #1's gate depends on a mechanism its owner retired. No amount of waiting satisfies it.
Per this file-set's own rule — *"A SHIPPED surface whose ship condition is later falsified reverts
to un-shipped … restate the condition"* (`dark-launch-exit-plan.md`) — the honest move is to
**restate the condition**, not to re-date it.

### The second reason KEEP-DARK is right on the merits

The surface fronts the M13 allocator. The allocator hard-fails unless a model is both
`is_active` and `approved_for_allocation` (`asxos/domain/models/production_gate.py`, the rule #11
enforcement point). Live: **0 models are approved for allocation.** So shipping the section would
front a path that is deliberately not allowed to run — and rule #11 is standing policy, not a
temporary block. The model-independent cards it would surface (tax, discipline, thesis,
regulatory) already reach you through the main brief, so there is no user-facing loss in keeping
it dark.

And the portfolio it would describe is one open lot: **HUBS.NYSE**, sole holding. An allocator
brief over a one-name book is not a product, it is a formatting exercise.

### Recommended verdicts

**Surface #1 — portfolio brief: KEEP-DARK, new expiry 2026-11-30, with the ship condition
restated.** Replace "4 weeks of paper-trade sign-off (M13.8)" with:

> Ship when a Stage 4 governed paper case has been delivered end-to-end and disposed by James,
> and the section renders that case's `DecisionPacket` rather than an allocator run. Until the
> decision engine can produce a non-abstain packet, this surface has nothing true to show.

That ties the surface to a milestone the campaign is actually building (Wave 6), rather than to
a cron that no longer exists. If Stage 4 slips past 2026-11-30, the surface re-raises and you get
asked again — which is the point.

**Surface #4 — paper-trade evaluator: KEEP-DARK, new expiry 2026-11-30, ruled together with #1.**
"Ship" here means *start the 4-week run*. Starting it today would evaluate `rebalance_runs`
produced by a deleted job against an allocator no approved model may drive: the run would be
methodologically empty. Keep the code — it is the only instrument that can produce sign-off
evidence once there is something to sign off — and re-raise it with #1.

**Do not DELETE either.** Deleting #4 removes the only mechanism that can ever retire #1;
deleting #1 discards a re-scopable surface whose model-independent half is already proven.

**Surface #3 — V2 brief tree: no ruling needed yet.** Expiry 2026-09-30, 28 days out, unexpired.
Flagged here only so it is not a surprise in four weeks. Its descope-to-model-independent work is
unstarted.

**What arbi does on your word:** records the verdicts and the restated condition in
`dark-launch-exit-plan.md`, closes the two `james-inbox.md` rows, and — since neither verdict
flips a flag — touches no environment variable and no workflow.

---

## 2. CBA thesis #1 — the automation, and the row (click H-17)

Ruled 2026-07-16 ("unsure why cba thesis is still a thing — it should be automated"); execution
was pending. Live state today:

| Field | Recorded | Live |
|---|---|---|
| `status` | `watching` | — |
| entry band | 42.00 – 45.00 | close **159.15** (2026-09-01) |
| `stop_price` | 38.00 | 76% below live |
| `target_price` | 60.00 | **62% below live** — the "target" is a price the stock passed long ago |
| `revisit_due_at` | 2026-06-27 | **67 days overdue** |
| `thesis_revisions` | 1 (the opening row) | never revised |

The entry band is **3.5× detached** from the live price. *(Corrected 2026-09-27, E-21: that
figure is `close / midpoint`, not the detachment ratio the `price_detached` rule uses. The
canonical quantity — distance from the nearest band **edge** over the midpoint, defined at
`asxos/domain/decision_engine/challenge/rules.py::detachment_ratio` — is **2.449195** on the
2026-09-16 close. The point below is unaffected: both figures are far past the 1.0 blocking
threshold.)* This is the worked example in the
north star's own framing — a thesis that was correct when written and stopped being correct,
which the discipline loop exists to catch — sitting undetected for 67 days because nothing
computes detachment.

**Recommendation, unchanged from your 2026-07-16 ruling, now scheduled:** build the deterministic
`price_detached` check as a Layer-1 rule in the Slice 2.5 challenge layer (campaign node H5-A),
not as a one-off script. It belongs beside the other 13 ratified deterministic rules, where a
thesis breaching it cannot produce `outcome="pass"`. Same lane as `discipline.py`,
model-independent, evidence-only.

**The row itself:** retire is the implied direction — not held, `watching`, no capital at risk.
That is a one-word confirm from you (**H-17**), and arbi will write the `thesis_revisions` row
recording *why* rather than silently flipping a status.

**Related finding, not part of this ruling.** HUBS thesis #2 records `stop_price` 230 with a live
close of **251.11** — currently *above* its stop, not violated. The backlog's standing note
("stop $230 violated, EXIT-CANDIDATE, no revision logged") describes a state the price has since
left, and no revision was ever logged either way. Same class of defect as CBA #1, opposite
direction: the thesis record and reality have drifted apart, and only a human can say which is
right. Not scheduled here; flagged so it is not lost.

---

## 3. The 0048 decision-spine tables — arbi's decision, recorded (no click)

**Are the five migration-0048 tables irreplaceable, and do they belong in the daily backup?
Yes.** Decided by arbi under Amendment H §2 ("what evidence counts as current truth"), recorded
here rather than left implicit:

`evidence_packets`, `thesis_versions`, `challenge_results`, `portfolio_assessments`,
`decision_packets` are append-only (enforced by `_decision_engine_forbid_mutation()` triggers)
and content-addressed. They record **what was known, what was claimed, and what was decided** at
a point in time. Unlike `prices` or `fundamentals`, nothing can re-derive them: re-running the
builder against today's data produces a *different* packet, which is the entire point of an
immutable decision record.

Already implemented in campaign node H0-B (conditional on `to_regclass`, so the script stays
green against a pre-0048 schema). The restore drill's table list is in a deny-listed workflow
file and is click **H-06**.

---

## 4. ADR §3.5 — rewritten, not superseded (no click)

You asked whether §3.5 should be rewritten or superseded. **Rewritten**, done in campaign node
H1-F: every line of the 2026-08-23 text had gone stale in the same direction — it described the
world Slice 0 was about to change and was never revisited after Slice 0 merged. Superseding it
would have left a false section in place with a pointer; rewriting it and recording what it said
in corrections row 6 keeps the audit trail without keeping the falsehood.

A second corrections row (7) was added for a sharper problem: **ADR §6 and §4 instruct adding
`signals` and `signal_outcomes` to the daily backup list**, which contradicts the backup script's
deliberate design. Anyone executing the ADR literally would reintroduce exactly what that design
avoids. Flagged rather than silently ignored, because the ADR is a ratified record and someone
will eventually follow it.

---

## What is NOT in this pack

- **P5-01 risk/capital calibration** (F4) — the largest open governor input, gating Stage 4's
  action-state packet. Not draftable by arbi: it is your risk appetite, not a derivable number.
- **D10 vs `roadmap-state.md`** — whether GitHub Issues becomes the live queue. Ratified but not
  in force; the campaign runs on `roadmap-state.md` either way, so it is not blocking.
- **The agent DB-role repoint and `REVOKE SELECT ON signals`** — infra sequencing, not a
  judgement call; it needs the Supavisor step first or the revoke is a no-op.
