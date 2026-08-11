# asxos — Session handoff — 2026-08-08

**Status:** SUPERSEDED 2026-08-11 by `session-handoff-2026-08-11.md` — read that one first. This
document remains accurate as the record of the 2026-08-08 session; it is no longer current state.

**Read priority:** historical (was: read first; superseded `session-handoff-2026-07-24.md` on priority)

**Owner:** arbi (`/arbi-close`)

**Cutoff:** 2026-08-08, Australia/Brisbane

**Reconciled remote baseline:** `main@cda6b1b963236c477805654100cbce324b54fc25`
(PR #77 merge; includes PR #76)

**Closeout PR:** [#75](https://github.com/Jp8617465-sys/asxos/pull/75), branch
`agent/arbi-session-close-2026-08-08-api`

**Preserved local source branch:** `agent/arbi-session-close-2026-08-08@b0980f4`

This is the durable closeout for the PR #70/#71/#72 recovery work, the PR #74/#76/#77
release sequence, the Arbi future-state review, the autonomy/control review, and the proposed
outcome-driven investment-engine build loop. It records what is real, what is branch-only, and
what remains a recommendation. It does not grant deployment, migration, trading, or
increased-autonomy authority.

---

## STOP — read first

1. **Model A remains shelved and quarantined.** Do not use it as evidence for a capital
   decision. "Decommission" currently means dormant/passive and excluded from the decision
   path, not deleting its code, data, or audit history. Reuse requires a new version to pass a
   pre-registered evidence gate.
2. **No Arbi authority increase has been approved.** The intended future role is broader, but
   current controls and James-reserved decisions remain in force. Arbi must not merge, deploy,
   migrate, move capital, place orders, rotate credentials, or alter its own constitution unless
   the governing policy explicitly authorises that exact action.
3. **Do not wholesale merge the investment-engine dossier or the future-state proposal.** They
   are reviewed source material, not canonical product state. Extract only an accepted vertical
   onto current `main`, with exact-diff verification.
4. **Do not treat a 12-hour ceiling as a quota.** A long loop must execute a ranked chain of
   bounded outcome increments and stop on a real gate; it must not manufacture architecture,
   agents, docs, or reviews merely to stay busy.
5. **Do not infer live state from this handoff.** Re-probe GitHub, Render, Supabase, scheduled
   jobs, and the current brief before acting. The active Claude terminal was not observable from
   this Codex thread at close.
6. **No secrets are recorded here.** James reports the transcript-exposed credentials were
   rotated; that report was not independently verified in this closeout.
7. **The single-user/personal-use boundary is not, by itself, a complete legal conclusion.**
   Before commercial, multi-user, or personalised-advice expansion, obtain qualified Australian
   financial-services advice. Reserving execution to James does not automatically resolve every
   advice/influence question under the current
   [Corporations Act 2001 s 766B](https://www.legislation.gov.au/C2004A00818/latest/text).

---

## Executive outcome

The project now has a clearer destination but has not yet delivered the complete product loop.
The north star is **better investment understanding, decisions, and wealth-building outcomes for
James**. Software, agents, architecture, and governance exist to produce and improve those
outcomes; asxos is not a software-development organisation whose output is more software.

James's intended future operating model is:

- **Arbi is the outcome brain and chief of staff** — it frames the objective, selects the next
  highest-value mission, coordinates finance/product/engineering specialists, judges evidence,
  and learns from James's disposition and later outcomes.
- **The investment engine must be built and mastered before broad expansion.** The immediate
  proof is one genuinely useful, evolving investment thesis from evidence through review,
  delivery, use, monitoring, and evaluation.
- **James retains constitutional authority** over objectives, risk appetite, capital, trades,
  irreversible operations, and the governed authority boundary.

That direction is durable. The implementation sequence below remains a reviewed recommendation,
not permission to bypass existing gates.

---

## What is real at close

| Artifact | Exact state | Meaning |
|---|---|---|
| Current `main` | `cda6b1b96323` | PRs #72, #74, #76, and #77 are merged. Code and exact-head CI are green; post-merge production outcomes remain unverified in this handoff. |
| News degradation + scheduler | PR #74, merge `a4fb797dc8d3`, head `ddbd64c93144` | News now has an end-to-end degradation contract and explicit render states; GitHub Actions daily-brief and watchdog workflows were added. The PR explicitly performed no deployment. |
| Scheduler-in-git + macro-thesis loop | PR #76, merge `9f3b81405496`, head `5bd9a844a942` | Added/extended the ordered daily brief, weekly research, US-position, and backup workflows; updated pipeline-health expectations; placed `score_macro_theses` after brief delivery; and repaired backup, redaction, fallback-email, and price-validation defects. The PR explicitly performed no deployment. |
| Portable authority guard | PR #77, merge `cda6b1b96323`, reconciled head `2d7ce8af0dbb` | The macOS/Linux path-canonicalisation hotfix was rerun against post-PR76 `main`; all three exact-head GitHub checks passed before merge. It does not increase Arbi's authority. |
| Gate0 control hardening | local `agent/arbi-authority-gate0@eeed24019edf` | Recorded `CODE_READY / MCP_CANARY_PENDING / NO AUTHORITY INCREASE` against the PR #72 base. Local-only at close; it now requires narrow extraction and reverification against post-PR77 main. |
| Arbi future-state proposal | local `agent/arbi-future-state-operating-model@33eb00e3cd34` | Reviewed `CHALLENGE / CONDITIONAL ADOPT`; local-only, branch-only, and non-authoritative. |
| Investment-engine dossier | local `agent/investment-engine-dossier@6cfaf15518d8` | Large source-material branch; its matching remote branch is four commits behind. Not a release or replacement roadmap. |
| This closeout | PR #75 on `agent/arbi-session-close-2026-08-08-api`; preserved source branch `agent/arbi-session-close-2026-08-08@b0980f4` | Must merge to `main` before a normal `/arbi` wake can rely on it. Do not force-push the preserved source branch. |

The three pre-existing worktrees were clean when inspected. A separate latest-main worktree was
created for this closeout so no Claude or Arbi implementation branch was edited.

The first closeout publication used an API transport branch during a DNS-restricted session. That
remote branch has now been reconciled through current `main`; the original local source branch is
intentionally preserved rather than force-pushed. The exact Gate0, future-state, and dossier heads
above remain local/branch-only evidence. Publish or extract them deliberately later—do not
reconstruct them from this summary or treat their SHAs as merged state.

PR #76 superseded the narrower PR #74 activation target. Its merged workflows require the existing
daily-pipeline secrets plus `BACKUP_GITHUB_TOKEN` and `BACKUP_REPO`; secret *presence*, workflow
runs, delivered output, and the backup artifact were not independently verified in this handoff.
James reports the transcript-exposed credentials were rotated, but that is not a production
canary. PR #76's own decommission gates are: first scheduled green daily run, green Saturday
research chain, and green backup with a verified artifact before deleting Render services. Those
gates are necessary, not sufficient: independent closeout review found that `us-positions.yml`
calls 13:30 UTC "after NYSE close," although it is 09:30 EDT (market open) in August and 08:30 EST
(pre-open) in standard time. Correct or explicitly re-decide that schedule, then prove exact-SHA
green `us-positions` and `pipeline-health` runs too. Until those receipts exist, live news,
delivery, position monitoring, thesis scoring, scheduler ownership, backup recovery, and absence
of duplicate production runs remain **UNVERIFIED** here. Render decommission remains blocked.

### Gate0 evidence and caveat

The Gate0 commit changes 20 files (`843` additions, `186` deletions). Its focused hook suite
passed `287` tests; the recorded full check passed Ruff, mypy over 153 files, and pytest with
`1918 passed, 2 xfailed`. Independent exact-diff reviews passed.

Keep the worktree-binding, explicit MCP matching, redacted logging, deny-only guard, and truthful
review-ack fixes. **Hold the review-policy cutover.** The commit also changes the old fixed
multi-review doctrine into prose risk tiers before the proposal's H3 shadow evidence and H4
explicit cutover exist. There is no deterministic diff-risk classifier yet. Treat that portion as
provisional or extract around it; do not call Gate0 an autonomy promotion.

### Future-state proposal evidence

Canonical reviewed source in its worktree:
`docs/proposals/arbi-outcome-operating-system-and-interface-future-state-2026-08-06.md` at
SHA-256 `66ebd8cfa6fa792108308596738ca39f8226b7a908ff491aaf538c6973a41a3e`, 1,592 lines.

Adopt from it:

- Arbi as a bounded outcome executive rather than a build policeman;
- one frozen decision truth with multiple renderers;
- outcome → capability → mission → release → use → learning traceability;
- code-proven is not outcome-proven;
- deterministic CI plus the minimum targeted independent review justified by risk.

Do not adopt yet:

- the whole dossier as canonical state;
- a production cockpit or Ask Arbi interface before the underlying decision loop works;
- persistent/unattended autonomy before receipts, replay, stop controls, and outcome evidence;
- a new control-plane/receipt-broker architecture without proving the smallest in-repo contract
  cannot meet the need.

### Dossier evidence

Measured against the PR #72 baseline `ec3f059`, the dossier branch changes 324 files with 102,955
insertions and 3,223 deletions. `docs/programs/investment-engine/` alone is 185 files / 55,343
insertions, including a large contract/schema/fixture set. Recompute those counts against current
main before extraction. It contains valuable designs and acceptance material, but its
self-labelled acceptance is not product proof and it is absent from main. Mine it selectively.

---

## What remains architecture rather than delivered outcome

The review found a split runtime rather than one mastered investment product:

- the CLI calls the V1 brief path directly;
- the scheduled job calls the V2 composer, which defaults back to V1 rendering;
- V1 can show news, while V2 has no complete news collector/decision-view contract;
- `brief_runs` stores rendered output but lacks a canonical decision-view hash, complete lineage,
  citations, and reliable delivery receipt; persistence failures can be swallowed;
- the `ThesisProposal` schema exists, but the materializer still rejects proposals using a stale
  "no schema" assumption;
- the FastAPI surface is currently a health endpoint that warms Model A; it is not a safe or
  useful cockpit host.

The root README also still describes active Model A/ML signals and "no frontend" as if that were
the current product definition. Treat it as a stale overview until a small, evidence-backed
README correction lands; do not let it override the north star, Model A shelf decision, or this
handoff.

---

## Recommended build sequence — outcome first

### Next wake's ONE THING

**Prove the post-PR76 operating cutover without losing the brief/news or running duplicate
schedulers.** The code is on `main`; merge is not outcome proof. First inventory GitHub Actions
secret presence (names only), current/recent workflow runs, and the still-live Render cron fleet.
Confirm neither substrate has an active conflicting run before any dispatch. Correct or explicitly
re-decide the erroneous 13:30 UTC `us-positions` schedule in a narrow reviewed change. Then, with
James's authority for each external change, run `daily-brief` at the exact current main SHA and
prove the naturally occurring live-news state plus delivery. Prove the other states through
isolated fixtures or a shadow path with no production writes and no email:

1. recent relevant news is visible when present;
2. a valid empty result renders an explicit calm empty state rather than disappearing;
3. provider/data failure is distinct from "no relevant news" and is observable.

Also verify ordered upstream blocking, `job_runs` freshness/degradation evidence, the delivered
email, post-brief `score_macro_theses`, AU-position checks, thesis-invalidations, the corrected
US-position monitor, pipeline health, and the weekly research chain. James's receipt should record
whether the brief arrived, was read, and was useful, missing something material, or materially
wrong. Verify backup integrity with an isolated scratch restore; never restore into production or
the shared Supabase project without separate James approval. Record the exact SHA and
run/delivery/artifact receipts. Do not decommission Render or accept dual scheduling implicitly;
make the cutover a separate, evidence-backed James decision only after every operating gate above
is green.

This is a narrow activation gate, not the final investment engine. It closes the in-flight loop
before new architecture accumulates.

### Then build one real vertical

Use one governed thesis and produce:

```text
governed thesis
  → sourced investment case and falsifiers
  → independent challenge
  → monitor/change events
  → immutable investment-decision-view-v1
      → email / CLI / later cockpit renderer
  → exact James disposition
  → paper outcome + decision-utility evaluation
  → Arbi learning record
```

Keep these semantic/audit contracts separate; this is not a mandate for separate services or
tables, and the first implementation should reuse the existing thesis and brief structures where
they can express the contract faithfully:

1. `DecisionView` — immutable, evidence-linked truth shown to James;
2. `SurfaceRender` — email/CLI/web representation of that truth;
3. `DeliveryReceipt` — what was delivered, when, through which surface;
4. `Disposition` — James's actual response and rationale;

`StagedOrderSet` is outside the first vertical. Add it only after the decision-utility loop is
proven and a concrete paper-only need exists; it remains separate from any execution authority.

Only after that vertical is used should the team generalise the view, add a read-only static
cockpit experiment, evaluate a persistent cockpit, then consider Ask Arbi. Persistent autonomy is
last, not first.

### Sustainable long-loop rule

A semi-attended 8–12 hour run should receive a ranked outcome queue, authority envelope,
deterministic acceptance checks, checkpoint cadence, and explicit stop conditions. Arbi chooses
the next eligible outcome increment; specialists do bounded work; exact-commit evidence closes
each increment. The loop continues to the next eligible item without asking merely because one
small task completed, but stops for capital, merge/deploy/migration authority, secrets, ambiguous
product choices, repeated failures, or exhausted useful work. A time ceiling is a circuit breaker,
not a promise of continuous token use.

---

## Next wake sequence

1. Confirm this file exists on `main`; if it is still branch-only, surface the docs-only closeout
   PR as the first process blocker.
2. Run `git fetch --all --prune`; record current main, open PRs, worktrees, dirty indexes, and the
   exact head of every branch named above. Never reuse a verdict across a changed digest.
3. Inspect the post-PR76 Actions workflows, secret presence, active/recent runs, and the Render cron
   fleet before changing either scheduler. Correct or explicitly re-decide the erroneous
   `us-positions` schedule; do not assume merge or a mistimed green run equals outcome proof.
4. Complete the post-PR76 operating-proof ONE THING above and record exact-SHA run, delivery,
   James-usage, and scratch-restore receipts, including `us-positions` and `pipeline-health`. Keep
   Render until James approves a proven cutover.
5. Reconcile Gate0 by retaining safe deny-only controls and holding the premature risk-tier policy
   cutover. Extract against post-PR77 main and run its MCP command-shape canary before proposing any
   authority change.
6. Reconcile `docs/product/roadmap-state.md` and the backlog against this handoff; do not create a
   ninth roadmap. Mark extracted dossier items with provenance rather than copying the dossier.
7. Present the one-thesis vertical as the next bounded mission, with acceptance tied to James's
   actual use and disposition—not files, agents, or PR count.

---

## Decisions and authority at close

**James explicitly directed:** end the session; preserve the work locally and remotely; ensure
the next Arbi/future-state wake receives the discussion; prioritise investment and wealth outcomes
over software output; make Arbi the future outcome brain/chief of staff; master the existing
investment engine before expansion; recognise PR #76 as merged; merge PR #77 if green; then move
to PR #75 and merge it if open and green. PR #77 has now satisfied that exact-head condition and
merged.

**Not newly approved by this close:** deployment, migration, workflow dispatch/live canary,
frontend, Render decommissioning, trade, capital action, persistent autonomy, authority escalation,
dossier-wide adoption, or commercial/multi-user expansion.

**Closeout completion condition:** PR #75's refreshed exact head must pass the required checks and
merge to `main`. Until then this handoff is branch-only and cannot govern a normal `/arbi` wake.
The original local source branch remains divergent archival evidence; do not force-push it. After
merge, treat the resulting `main` commit—not this branch name or an earlier check run—as the
authoritative closeout identity.
