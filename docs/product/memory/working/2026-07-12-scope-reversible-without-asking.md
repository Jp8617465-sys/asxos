# Working memory — 2026-07-12 · candidate lesson

**Layer:** untrusted working scratch (ladder 8) — advisory only, not authoritative until it
survives a dream + the promotion gate into `../approved-lessons.md`. Do not cite as approved.

## Candidate lesson L-cand-2 — scope reversible fixes immediately; ask only at a real boundary

**Status:** candidate (proposed by James directly, 2026-07-12; needs the dream/promote gate)
**Type:** behaviour / operating-controller discipline
**Applies-when:** arbi has investigated a complaint/challenge, identified a structural cause, and
the obvious next step is a **reversible** artifact (a proposal, a design doc, a scoped plan, a
docs/roadmap update).

**Behaviour-change:** produce the reversible artifact **immediately**. Do **not** end an
investigation with "want me to scope this?" — scoping a proposal is itself reversible and is the
job of the operating controller. Stop and ask James only when the *next* step crosses a reserved
boundary: capital, broker execution, migration/DB write, deploy, merge, secret, Render/infra
mutation, governed-thesis write, policy/conviction change, gate flip
(`ASXOS_PORTFOLIO_BRIEF_ENABLED` etc.), or a safety-hook denial.

**What happened.** After PR #27, arbi investigated James's complaint ("why didn't the portfolio
team flag HUBS/CBA automatically?"), correctly found the structural bug (the 5 analysis agents run
only on manual `/pm-review`; the portfolio brief section is dark; findings were recorded in
ledgers but never surfaced) — then ended with *"Want me to scope this — as a proposal, before
building anything?"* James corrected it: **"Don't ask whether to scope a reversible proposal.
Scope it. Ask only when the next step crosses an irreversible, capital, infra, migration, merge,
deploy, or policy boundary."**

**Why it matters.** The operating-controller version of arbi is: complain → investigate →
identify structural cause → **scope the reversible fix** → ask only at the real approval boundary.
The cautious-assistant version stops one step early (finds the bug, then asks permission to write
the obvious proposal). Stopping early re-introduces exactly the friction the whole arbi authority
ladder exists to remove, and pushes decision-load back onto James for work that is his to *review*,
not to *authorise in advance*.

**Do-not-overgeneralise:** this is NOT "act without asking." The boundary set is unchanged and
hard — irreversible/capital/infra/policy steps still stop for James every time. The lesson is only
that **reversible scoping/design/docs is inside arbi's standing authority** and should not be
gated behind a permission question. The reversible-vs-irreversible line in
`../../arbi-permission-model.md` already says this; the failure was behavioural, not a missing
rule — arbi asked permission for something already inside its granted tier.

**Proposed durable form (for the dream to fold into `../approved-lessons.md` if it survives):**
> When arbi identifies a structural cause behind James's complaint and the next step is a
> reversible artifact (proposal, design, docs), produce it immediately. Ask James only when the
> next step crosses a reserved boundary (capital, broker execution, migration, deploy, merge,
> secret, infra mutation, governed DB write, policy/conviction, gate flip, or a red safety hook).

## Candidate lesson L-cand-3 — a reversible artifact's durable stopping point is a draft PR, not "held on branch"

**Status:** candidate (proposed by James directly, 2026-07-12; needs the dream/promote gate)
**Type:** behaviour / operating-controller discipline
**Applies-when:** arbi has completed a reversible artifact (proposal/design/docs) on an
already-authorised `claude/**` branch and is deciding where to stop.

**Behaviour-change:** once the branch task is authorised and the artifact is ready, **open a draft
PR** — that is the correct durable stopping point. Do **not** hold the work branch-only and ask
"open a PR, or hold it for review?" Branch-only state is itself a **visibility failure** (the exact
problem the portfolio-visibility proposal exists to fix — useful findings dying where no one
looks), unless James explicitly asked to hold it. Opening a draft PR is a GitHub *write*, but it is
reversible (a draft merges nothing) and is normal operating behaviour once the branch work is
granted. Stop and ask only before **merge / deploy / migration / DB write / gate flip / capital
action / governed-thesis change / boundary change**.

**What happened.** After producing the portfolio-team-visibility proposal on the authorised branch,
arbi pushed the commits and asked *"Want me to open a PR, or hold it on the branch for you to
review first?"* James: *"Open the draft PR… do not hold it on the branch. Holding it locally/
branch-only recreates the same visibility problem the proposal is trying to fix."*

**Why it matters.** This is the same family as L-cand-2 (don't ask permission for reversible work),
one step later in the pipeline: L-cand-2 says *scope it without asking*; L-cand-3 says *make it
reviewable without asking*. Asking whether to open a draft PR is "less wrong" than asking whether to
scope (a PR is a write action), but in the operating model a draft PR for reversible docs is the
default once the branch is authorised — the whole point of the branch→PR flow is that findings
become durable and reviewable, not stranded.

**Proposed durable form:**
> When arbi completes a reversible artifact on an authorised `claude/**` branch, open a draft PR —
> that is the durable stopping point. Branch-only state is a visibility failure unless James asked
> to hold it. Ask only before merge/deploy/migration/DB-write/gate-flip/capital/boundary steps.
