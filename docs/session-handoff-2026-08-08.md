# asxos — Session handoff — 2026-08-08

**Status:** current after merge to `main`; branch-only closeout candidate until then

**Read priority:** read first (newest handoff; supersedes `session-handoff-2026-07-24.md` on priority)

**Owner:** arbi (`/arbi-close`)

**Cutoff:** 2026-08-08, Australia/Brisbane

**Final remote baseline observed:** `main@a4fb797dc8d34100082b275435acf812bcb46666` (PR #74 merge)

**Local checkout base:** `origin/main@ec3f059b918aa978afb06e3a49edf82d0641dd0b` (PR #72 merge; Git transport was unavailable during the final remote advance)

**Local closeout branch:** `agent/arbi-session-close-2026-08-08`

**Remote transport branch:** `agent/arbi-session-close-2026-08-08-api`

This is the durable closeout for the PR #70/#71/#72 recovery work, the Arbi future-state
review, the autonomy/control review, and the proposed outcome-driven investment-engine build
loop. It records what is real, what is branch-only, and what remains a recommendation. It does
not grant merge, deployment, migration, trading, or increased-autonomy authority.

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
| Current `main` | `a4fb797dc8d3` | PR #72 and PR #74 are merged. PR #74 landed while this closeout was being published. Production activation remains unverified. |
| News degradation + scheduler | PR #74, merge `a4fb797dc8d3`, head `ddbd64c93144` | News now has an end-to-end degradation contract and explicit render states; GitHub Actions daily-brief and watchdog workflows were added. The PR explicitly performed no deployment. |
| Gate0 control hardening | local `agent/arbi-authority-gate0@eeed24019edf` | Recorded `CODE_READY / MCP_CANARY_PENDING / NO AUTHORITY INCREASE` against the PR #72 base. Local-only at close; it now requires exact rebase/extraction and reverification against post-PR74 main. |
| Arbi future-state proposal | local `agent/arbi-future-state-operating-model@33eb00e3cd34` | Reviewed `CHALLENGE / CONDITIONAL ADOPT`; local-only, branch-only, and non-authoritative. |
| Investment-engine dossier | local `agent/investment-engine-dossier@6cfaf15518d8` | Large source-material branch; its matching remote branch is four commits behind. Not a release or replacement roadmap. |
| This closeout | local `agent/arbi-session-close-2026-08-08`; remote transport `agent/arbi-session-close-2026-08-08-api` | Must merge to `main` before a normal `/arbi` wake can rely on it. |

The three pre-existing worktrees were clean when inspected. A separate latest-main worktree was
created for this closeout so no Claude or Arbi implementation branch was edited.

Direct Git transport was DNS-blocked in this environment. The closeout itself was published
through GitHub's API, but the exact Gate0, future-state, and dossier heads above remain local; the
remote handoff records their identities but GitHub cannot resolve those three SHAs yet. Preserve
the clean worktrees and publish them deliberately later—do not reconstruct them from this summary.

PR #74 merged after that local inspection. Its activation packet requires the Actions secrets
`DATABASE_URL`, `EODHD_API_KEY`, `FRED_API_KEY`, `RESEND_API_KEY`, `BRIEF_FROM_EMAIL`, and
`BRIEF_TO_EMAIL`, followed by a manual `daily-brief` run. The PR says Render decommissioning is a
separate James-gated step. Therefore code is merged, but live news, delivery, scheduler ownership,
and absence of duplicate production runs are all still **UNVERIFIED** here.

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

**Activate and prove PR #74 without accidentally creating two production schedulers.** The code is
now on main; the remaining outcome is an exact-SHA live canary and an explicit scheduler-ownership
decision. First inventory GitHub Actions secret presence and runs plus the still-live Render cron
fleet. Then, with James's authority for any external change, configure missing Actions secrets and
manually dispatch `daily-brief` at current main. Prove all three news states are honest:

1. recent relevant news is visible when present;
2. a valid empty result renders an explicit calm empty state rather than disappearing;
3. provider/data failure is distinct from "no relevant news" and is observable.

Also verify ordered upstream blocking, `job_runs` freshness/degradation evidence, the delivered
email, and whether both Actions and Render could run the same chain. Do not decommission Render or
accept dual scheduling implicitly; make the cutover a separate, evidence-backed James decision.

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

Keep these contracts separate:

1. `DecisionView` — immutable, evidence-linked truth shown to James;
2. `SurfaceRender` — email/CLI/web representation of that truth;
3. `DeliveryReceipt` — what was delivered, when, through which surface;
4. `Disposition` — James's actual response and rationale;
5. `StagedOrderSet` — separate and paper-only until explicitly promoted.

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
3. Re-probe PR #72 and PR #74 live state. Inspect Actions runs/secret presence and the Render cron
   fleet before changing either scheduler; do not assume merge equals outcome proof.
4. Complete the PR #74 activation ONE THING above and record exact-SHA receipts.
5. Reconcile Gate0 by retaining safe deny-only controls and holding the premature risk-tier policy
   cutover. Run its MCP command-shape canary before proposing any authority change.
6. Reconcile `docs/product/roadmap-state.md` and the backlog against this handoff; do not create a
   ninth roadmap. Mark extracted dossier items with provenance rather than copying the dossier.
7. Present the one-thesis vertical as the next bounded mission, with acceptance tied to James's
   actual use and disposition—not files, agents, or PR count.

---

## Decisions and authority at close

**James explicitly directed:** end the session; preserve the work locally and remotely; ensure
the next Arbi/future-state wake receives the discussion; prioritise investment and wealth outcomes
over software output; make Arbi the future outcome brain/chief of staff; master the existing
investment engine before expansion.

**Not newly approved by this close:** any merge, deployment, migration, live canary, frontend,
trade, capital action, persistent autonomy, authority escalation, dossier-wide adoption, or
commercial/multi-user expansion.

**Closeout completion condition:** local commit plus remote branch/draft PR. Direct Git transport
was unavailable from the Codex sandbox, so the remote branch is a GitHub API transport commit
rebased onto the final observed main; the four scoped file blobs are identical to the local
closeout, while the commit/tree include newer PR #74 main state. Do not force-push either branch;
merge the docs PR or reconcile the four scoped paths after networked Git is available. The handoff
becomes normal wake-up authority only when deliberately merged to `main` by James.
