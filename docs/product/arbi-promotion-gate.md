# arbi promotion gate — the only path from candidate to approved

**Status:** current
**Scope:** the gate that decides whether an arbi prompt / memory / policy version becomes
current
**Last verified:** 2026-07-10
**Owner:** James (governor); the gate is graded outside arbi
**Superseded by:** N/A

Self-improvement is dangerous precisely where it is powerful: an unchecked loop can make arbi
"better" at the metric while worse at the mission, or launder a stale/poisoned conclusion into
authority. The promotion gate is the single valve that prevents this. **Nothing becomes
current — no new prompt, no new memory, no new policy — except through this gate.**

---

## What passes through the gate

- a **dream candidate** → `asxos-approved-learning-memory`
- a new **arbi prompt version** (agent file / command wording)
- a new **policy/rubric version**
- a **working-memory lesson** proposed as durable

## The rule

> A candidate is promoted **only if** it **improves** the scorecard **without worsening** any
> of: hard gates, state accuracy, or risk controls.

Concretely, promote only if it improves at least one of — state accuracy · repeated-mistake
reduction · rubric pass rate · blocker prioritisation · handoff quality · scope control — **and
regresses none of** — safety boundaries · the source hierarchy · Model A quarantine handling ·
the permission model · the financial-decision boundary.

## How it's graded (not by arbi)

1. **Hard-gate tests** — the `arbi-scorecard.md` Layer-1 circuit breakers must all pass.
2. **Holdout evals** — run the candidate against `docs/product/evals/` fixtures it has *not*
   been tuned on. Compare rubric pass rates (`docs/product/rubrics/`).
3. **Scorecard trend** — the candidate's `episode_score` trend vs the incumbent, over a window,
   not a single lucky run.
4. **No safety/state regression** — an explicit check that none of the "regresses none of" list
   moved backward.
5. **Second reviewer for high impact** — a specialist reviewer (e.g. `security-engineer` for a
   boundary-adjacent change) in a **separate context** from whatever produced the candidate.

The grader is **never the same agent/run that produced the candidate** (Goodhart defence).

## Failure handling

- A candidate that fails any gate is **archived, not used** — including partial/failed dream
  output (a dream that didn't complete cleanly is never promoted; see `arbi-dream-policy.md`).
- A promoted version that later regresses the scorecard is **rolled back** to the prior
  version (git makes this trivial for docs/prompts) and the regression logged to
  `arbi-run-ledger.md`.

## Constitution/boundary changes are NOT ordinary promotions

Promoting a routine lesson is arbi-initiable (drafted, then gated). **Changing a safety
boundary — the constitution, permission grants, rule #11, the s766B firewall — is reserved to
James** (`arbi-constitution.md` §reserved). arbi may draft such a change and run it through
this gate to *demonstrate* no regression, but James's explicit approval (ladder level 0) is
required to merge it. The gate can clear a boundary change; only James can enact one.

## Today vs the platform

**Update (2026-07-10): promotion is now git-native** — a CODEOWNER-reviewed PR merge to
`main` (arbi cannot self-approve — `.github/CODEOWNERS` makes James the required reviewer),
CI-gated by `full-check`. See `/arbi-promote`. Managed Agents automation is an optional
backend. The paragraph below is the platform mapping.


Today "promotion" = a reviewed git commit that changes an arbi doc/prompt, with the review
loop (`security-engineer`/`technical-writer`) and this gate's criteria applied by hand. On
Managed Agents it becomes automated: outcomes-graded candidates, holdout eval runs, and a
memory-store promotion step — same criteria, mechanised.
