# Arbi as chief of staff + feature control plane

- **Status:** proposal and Claude execution handoff; **not authority**
- **Date:** 2026-09-03 (Australia/Brisbane)
- **Baseline:** `main` at `55f2619` plus live GitHub inspection on 2026-09-03
- **Owner / governor:** James
- **Proposed operating owner:** Arbi
- **Scope:** agent routing, bounded autonomy, work control, feature version control,
  and documentation lifecycle
- **Non-scope:** implementing the design; changing capital policy; merging; deploying;
  applying migrations; changing secrets or production state

> This is the last plan that should be allowed to create a parallel work system.
> If James adopts it, Claude should implement it by making GitHub Issues + Projects
> the live work substrate, slimming the instruction surface, and then archiving or
> superseding the planning documents it replaces. This file grants no new permission.

## Executive decision

Build Arbi into a **chief-of-staff control plane**, not a CEO, not a code-writing
super-agent, and not a second project-management database.

The target division is:

- **James governs:** outcomes, bets, risk appetite, exceptions, irreversible actions,
  capital, and changes to the authority model.
- **Arbi runs the operating system:** captures and triages work, maintains the one
  portfolio view, protects WIP, routes each work object to one accountable lane,
  assembles decision packets, follows commitments through to evidence, and closes or
  escalates stale work.
- **Guilfoyle runs delivery planning:** converts an approved feature or incident into a
  dependency graph and bounded slices.
- **One builder mutates code:** `reversible-work-builder` executes a slice. Other agents
  advise, challenge, or verify.
- **A verifier independent of the planner closes the loop:** a small new
  `verification-steward` role checks contract-to-test-to-PR-to-observation evidence.
- **GitHub holds live work state:** one parent Issue per feature, sub-issues per slice,
  Projects fields for state, short-lived branches per slice, and PRs as the review and
  evidence boundary. Do not create one Markdown plan/spec/handoff per feature.

The immediate goal is not “more agent power.” It is **less founder coordination load with
better observability**. Arbi can take much more control over reversible coordination now.
Power over merge, deployment, migrations, secrets, production writes, capital, and its own
constitution should remain with James.

## 1. Why this is one problem, not two

The chief-of-staff question and the version-control question are the same systems problem.
Arbi cannot reliably coordinate a portfolio if work identity, state, dependencies,
acceptance, and decisions are scattered across long Markdown files and branch prose.
Conversely, a feature-control system will decay unless someone owns intake, routing,
follow-through, and closure. That owner should be Arbi.

The desired loop is:

```text
ideas / defects / evidence / obligations
                  |
                  v
        Arbi intake + triage
                  |
       one parent Issue (FTR/BUG/OPS/RSR)
                  |
         James bets / reserves decision
                  |
                  v
       Arbi route + WIP admission
                  |
                  v
   Guilfoyle slices + assigns lanes
                  |
       +----------+-----------+
       |          |           |
   specialists  builder   challengers
       |          |           |
       +----------+-----------+
                  |
          verification steward
                  |
     draft PR -> James gate -> observation
                  |
           Arbi closes + learns
```

Known steps should be deterministic workflow. Judgment belongs in agents. This follows the
central distinction in Anthropic's [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents):
use simple, composable workflows for predictable paths and agents where the path genuinely
requires model-directed reasoning.

## 2. Current-state diagnosis

### 2.1 What Arbi already does well

The current design has several strong primitives worth preserving:

1. **Clear constitutional boundary.** `arbi-constitution.md` and
   `arbi-permission-model.md` reserve capital and irreversible infrastructure actions to
   James and separate infrastructure from portfolio authority.
2. **Priority and execution are separated.** Arbi decides what matters; Guilfoyle plans
   how; the main loop dispatches; the builder mutates. This matches the manager/worker
   orchestration pattern in the [OpenAI Agents SDK](https://openai.github.io/openai-agents-python/multi_agent/).
3. **Adversarial challenge exists.** `arbi-red-team` challenges the “one thing” rather
   than producing a competing plan.
4. **The mutation ceiling is intelligible.** Reversible branch work and draft PRs are
   separate from merge, deploy, migrations, secrets, production writes, and capital.
5. **Evidence and memory are first-class.** The scorecard, run ledger, decision log,
   dream/promotion loop, and content-addressed decision work all aim at traceability.
6. **Two-speed execution is sensible.** `/build` handles tiny same-file changes;
   `/arbi-mission` handles multi-node reversible work; `/arbi-team` is reserved for work
   that is actually parallel.
7. **D6 and D10 point in the right direction.** The ratified ADR says vertical slices,
   not sprints, and GitHub Issues + Projects, not prose, should hold actionable state.

These are unusually good foundations. The problem is not lack of governance thought. It is
that the design has accumulated more descriptions of the operating system than executable
operating system.

### 2.2 Why Arbi is not yet a chief of staff

Today Arbi is primarily a **wake ritual and prioritisation adviser**:

- `/arbi` gathers state, asks Arbi for a brief and one next action, writes another state
  block, and stops.
- `/arbi-mission` begins only after James or Arbi has supplied a mission envelope.
- There is no durable, queryable intake queue with service levels and ownership.
- There is no explicit portfolio admission policy beyond “the one thing.”
- There is no machine-readable agent/lane registry or coverage check.
- Commitments, decisions required, blockers, work state, and close evidence are spread
  across `roadmap-state.md`, `james-inbox.md`, handoffs, plans, ledgers, and PRs.
- The planner (`guilfoyle`) also judges readiness; there is no general independent
  acceptance owner.
- Arbi notices stale truth during a wake, but no continuous control retires or escalates it.

A human chief of staff normally operates as a gatekeeper, counselor, implementer/proxy,
priority steward, and cross-functional follow-through owner. McKinsey describes the role in
those terms and emphasizes alignment of the leader's time, monitoring, accountability, and
escalation of true executive decisions ([McKinsey](https://www.mckinsey.com/industries/public-sector/our-insights/seven-tips-for-success-for-new-chiefs-of-staff-at-government-agencies)).
First Round's startup guidance similarly emphasizes weekly priorities, an initiative tracker,
and making the leader's operating rhythm more effective ([First Round](https://review.firstround.com/how-to-be-an-exceptional-chief-of-staff-advice-for-scaling-impact-at-startups/)).

Arbi currently supplies counsel and prioritisation, but only partially supplies gatekeeping,
operating rhythm, commitment management, and end-to-end follow-through.

### 2.3 The measured “doc spiral”

At the baseline commit:

| Signal | Observed state |
|---|---:|
| Files under `docs/` | 212 |
| Dated proposal files | 36 |
| Files with `handoff` in their path/name | 20 (10 at the `docs/` root) |
| Agent definitions excluding their README | 25 |
| Slash-command files | 33 |
| Lines in `docs/README.md`, `roadmap-state.md`, the dated truth map, and `arbi-*` governance docs | 5,565 |
| Live stale executable references matching removed migration/Model-A paths | 15 lines across 10 agent/command files |
| `docs/product/state/latest-snapshot.json` observation date | 2026-08-20 |
| `docs/ops/github-issues-snapshot.json` after the snapshot workflow landed | `[]` |

The counts are symptoms; the failure mode is duplicated responsibility:

- `CLAUDE.md`, the harness profile, agent descriptions, command files, governance docs,
  `docs/README.md`, proposals, handoffs, and the roadmap each restate routing or authority.
- The agent README says 22 agents and one discovery agent, while the directory now holds
  25 agent definitions and three discovery agents.
- Current `arbi.md` / `/arbi` instructions still mention the deleted
  `REQUIRED_MIGRATIONS` mechanism. Open PR
  [#189](https://github.com/Jp8617465-sys/asxos/pull/189) addresses part of this drift,
  demonstrating that drift is active rather than historical.
- Several command files still direct work toward removed Model A paths or “sprint” rituals
  inconsistent with the ratified vertical-slice model.
- D10 says GitHub Issues is ratified; live main still calls it “not in force” and continues
  using a 1,941-line roadmap as the queue.

Documentation is trying to act as policy, state database, event log, plan, spec, and handoff
at once. No writer can keep those copies synchronized indefinitely.

### 2.4 Live Git topology shows the feature-control gap

Live GitHub inspection on 2026-09-03 found **14 open PRs**. Two shapes matter:

- Product stack: `#192 -> #193 -> #194 -> #195 -> #196 -> #197` — six PRs deep.
- Governance/operations stack: `#185 -> #186 -> #189 -> #190` — four PRs deep,
  alongside independent `#187`, `#188`, `#191`, and Dependabot `#178`.

The work is deliberate and the PRs are clean, but the shape makes base identity, review
state, merge order, cascading rebases, and feature completion hard to see. Amendment H's
campaign plan uses waves, nodes, 39 clicks, stage cells, a ranked roadmap, handoffs, ledger
rows, and PR stacks. It is sophisticated, but the control surface is too broad for one
founder to scan.

This plan does **not** propose restacking or renaming those in-flight branches. Finish or
park that campaign under its current contract. Use the next independently shaped feature as
the control-plane pilot, then migrate only still-live work.

## 3. Research synthesis

### 3.1 Current AI chief-of-staff market scan

The current category is early and marketing-heavy, so product claims are useful for pattern
recognition, not proof of reliability. Across products aimed at founders and solo operators,
the repeated design is strikingly consistent:

| Product / example | Promised operating loop | Design signal for Arbi |
|---|---|---|
| [Dispatch](https://docs.dispatch.am/features) | Read communications, prepare meetings, track reciprocal commitments, maintain todos, and surface a daily brief | A chief of staff owns commitments and exceptions across sources, not just summarisation |
| [Aidely](https://www.tryaidely.com/) | “Things that need you” separated from work the agent can prepare; inbox, calendar, follow-up, and project loops | The founder surface should be an approval/decision desk, not the full task graph |
| [ATLAS](https://www.heyatlas.org/) | Daily brief, unanswered commitments, meeting preparation, workspace search; read-only default and approval before sending | Broad read access can coexist with narrow write authority; default-to-draft is a product feature |
| [Supervise](https://supervise.app/) | Separate chief-of-staff and solo-engineer roles, authority set per agent, inspectable receipt for each action | Coordination and engineering should be separate lanes with per-role authority and receipts |
| [Team0 for founders](https://team0.ai/for/founders) | Multi-day delegated research with periodic evaluation and escalation at approval gates | Long work needs a goal, evaluator, time/cost boundary, and explicit return-to-founder conditions |
| [Saely](https://www.saely.app/) | Overnight scan, one ranked brief, pre-drafted actions, one-click approval | Prepare everything reversible before asking; compress the founder interaction to the true decision |

Five category-level patterns are worth adopting:

1. **One attention surface:** aggregate many sources into a short exception/decision brief.
2. **Commitment memory:** track what was promised, by whom, by when, and whether it closed.
3. **Preparation before interruption:** research and draft the next action before involving the
   founder.
4. **Approval desk:** separate “needs your judgment/click” from “the system can progress.”
5. **Receipts:** every action must leave an inspectable record with source and authority.

The common gap in these vendor descriptions is rigorous engineering governance: they rarely
show how contradictory sources, test evidence, branch dependencies, or authority promotion
are handled. That is where asxos's existing constitution and harness are stronger. The target
is to combine the category's useful founder experience with asxos's evidence and boundary
discipline.

### 3.2 Patterns that transfer

| Pattern | Evidence | Consequence for asxos |
|---|---|---|
| Manager with specialists | Anthropic's orchestrator-workers pattern and OpenAI's manager-as-tools pattern keep one coordinator in control of a shared answer. | Arbi owns the portfolio and final operating brief; specialists do bounded work rather than handing the user between agents. |
| Explicit delegation contract | Anthropic's multi-agent research system found that task objective, output form, tools/sources, and boundaries must be explicit to prevent duplication and gaps. | Every dispatch uses one typed handoff envelope; no free-form “ask these agents.” |
| Context is a scarce resource | Anthropic recommends curating, compacting, externalizing memory, and progressively disclosing context. | Agents receive the feature contract and relevant evidence, not the entire 5,000-line governance corpus. |
| Deterministic paths before agent judgment | Both Anthropic and OpenAI recommend code/workflow orchestration when the sequence is known. | State transitions, validation, routing rules, and guard checks are scripts/schemas; agents handle ambiguous shaping, research, challenge, and exceptions. |
| Trace calls, handoffs, and guardrails | OpenAI's tracing and guardrail guidance treats handoffs/tool calls as observable spans and warns that final-output guardrails do not protect every nested action. | Log `work_id`, lane, actor, authority, inputs, output, verification, and escalation at every handoff; enforce side effects at the tool/hook boundary. |
| Human oversight is risk-specific | NIST AI RMF calls for clearly differentiated human/AI roles, ongoing review, lifecycle measurement, and executive responsibility for risk. | Keep a risk-based authority matrix, instrument interventions, and promote autonomy by evidence—not by broad prose grants. |
| Chief of staff protects focus and follow-through | Human CoS practice emphasizes priority rhythm, an initiative tracker, gatekeeping, and escalated decision packets. | Arbi owns intake, the decision agenda, WIP, commitments, and closure; James owns the bets and reserved calls. |
| Solo operators need briefing + triage + commitment capture | Public solo-operator case studies describe morning briefing, inbox triage, pipeline hygiene, task classification, and overnight preparation. | The useful automation is operational memory and prepared decisions, not unlimited action. Treat these as directional case studies, not controlled evidence. |
| One work source of truth | GitHub recommends sub-issues, dependency links, structured Projects fields, automation, WIP-oriented views, and one source of truth. | Enact D10. Issues hold state; PRs hold changes; docs explain or record durable decisions. |
| Isolated branches and commits | GitHub Flow recommends a separate branch for unrelated changes and isolated, complete commits. | Branch per slice, shallow dependencies, stable feature/slice IDs, and independent reversibility. |
| Version only where compatibility has meaning | Semantic Versioning requires a declared public API; Conventional Commits supplies machine-readable change intent. | Do not invent SemVer for prose specs. Use contract revisions for features and reserve SemVer for a public software interface/release. |

Key primary sources:

- [Anthropic: Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)
- [Anthropic: How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)
- [Anthropic: Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- [OpenAI Agents SDK: multi-agent orchestration](https://openai.github.io/openai-agents-python/multi_agent/)
- [OpenAI Agents SDK: handoffs](https://openai.github.io/openai-agents-python/handoffs/)
- [OpenAI Agents SDK: guardrails](https://openai.github.io/openai-agents-python/guardrails/)
- [OpenAI Agents SDK: tracing](https://openai.github.io/openai-agents-python/tracing/)
- [NIST AI RMF core](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/)
- [GitHub Issues](https://docs.github.com/en/issues/tracking-your-work-with-issues/learning-about-issues/about-issues)
- [GitHub Projects best practices](https://docs.github.com/en/issues/planning-and-tracking-with-projects/learning-about-projects/best-practices-for-projects)
- [GitHub Flow](https://docs.github.com/en/get-started/using-github/github-flow)
- [GitHub protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
- [Semantic Versioning 2.0.0](https://semver.org/)
- [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/)
- [Diátaxis documentation framework](https://www.diataxis.fr/start-here/)

Directional solo-founder examples, used only to identify common workflow shapes:

- [BetterProcess: running a solo business with an AI chief of staff](https://betterprocess.ai/blog/ai-chief-of-staff)
- [Open-source local-first chief-of-staff workflow](https://github.com/ceaksan/chief-of-staff)

### 3.3 Patterns not to copy

1. **Do not maximize agent count.** More roles increase handoff cost and ambiguity. Add a
   role only for a proven accountability gap.
2. **Do not adopt a heavy spec framework wholesale.** GitHub Spec Kit's
   [spec -> plan -> tasks -> implement](https://github.github.com/spec-kit/) sequence is a
   useful mental model, but installing a second artifact tree would worsen this repo's
   document problem.
3. **Do not use “full autonomy” as a single switch.** Authority varies by action,
   environment, evidence quality, and reversibility.
4. **Do not make Arbi both governor and unrestricted executor.** Separation between
   prioritisation, planning, mutation, verification, and human approval is a safety and
   quality control.
5. **Do not import team ceremony into a solo product.** Use WIP caps and an appetite, not
   sprint planning. Basecamp's Shape Up model is useful specifically for its bounded appetite
   and circuit breaker, not its six-week team cadence
   ([Shape Up](https://basecamp.com/shapeup/2.2-chapter-08)).

## 4. Target operating model

### 4.1 Arbi's new charter

Arbi's mission becomes:

> Preserve James's attention and move the highest-value bounded work from signal to
> observed outcome, using one truthful control plane, explicit specialist lanes, and the
> least authority needed.

Arbi owns seven functions:

1. **Intake.** Capture an idea, defect, obligation, decision request, or evidence signal
   once. Deduplicate it and assign a stable work identity.
2. **Triage.** Classify type, urgency, outcome, risk, reversibility, confidence, and lane.
   Reject or park items that lack a meaningful outcome.
3. **Portfolio.** Maintain Now / Shape / Later / Parked views, enforce WIP, surface capacity
   and dependency risk, and recommend the next bet.
4. **Decision agenda.** Turn founder-only calls into short packets with context, options,
   recommendation, downside, reversibility, deadline, and exact next action.
5. **Routing.** Choose the accountable lane, required overlays, route (`/build`, mission,
   team, research, or James), authority ceiling, and acceptance owner.
6. **Follow-through.** Track promises, blockers, review state, timeouts, and observations;
   pivot to independent work while a James gate is pending.
7. **Closure and learning.** Require evidence, close the issue, record exceptions, and
   promote only reusable lessons into durable memory.

Arbi explicitly does **not** own:

- the product's final outcome or bet selection;
- risk appetite or capital decisions;
- weakening acceptance criteria to make a PR pass;
- implementation inside specialist domains;
- self-modification of its constitution, guardrails, or promotion rules;
- merge, deploy, production changes, migrations, secret creation/read, or default-branch
  writes under the current constitution.

### 4.2 Operating cadence

| Trigger | Arbi action | James receives |
|---|---|---|
| New signal/event | Deduplicate, classify, link, set SLA, park or request missing minimum data | Nothing unless reserved/urgent |
| Start of attended session | Refresh live state and exception list; reconcile only deltas | One screen: focus, health, decisions, blockers |
| Feature admitted | Lock contract revision, route lanes, ask Guilfoyle for slices | A bet confirmation only if not already ratified |
| PR/check event | Update slice state automatically; request required overlay or verification | Only failing gate or reserved approval |
| Daily unattended check | Staleness, broken automation, expired decisions, WIP/stack breach | Exception brief; silence when healthy |
| Weekly operating review | Outcome movement, aging, interventions, autonomy failures, stale docs | 10-minute review and bet changes |
| Monthly authority review | Score eligible actions against evidence thresholds | Promote/hold/revoke packet; never self-promote |

Replace the current full historical wake rewrite with **delta + exceptions + decisions**.
The full state remains queryable in Projects, Issues, PRs, Actions, and the issue snapshot.

### 4.3 Portfolio policy for one founder

“One thing” is useful for attention but too lossy as the entire operating model. Use three
bounded slots:

1. **Focus:** one admitted product feature/campaign.
2. **Keep-safe:** at most one incident, security, data-integrity, or reliability item that
   may pre-empt focus.
3. **Shape:** at most one research/shaping item that cannot mutate production code.

Everything else is Later, Parked-with-trigger, or Rejected. Arbi may reorder work **inside an
already ratified feature**. Choosing or replacing the Focus bet remains James's call.

Recommended circuit breakers:

- maximum two active implementation PRs per feature;
- maximum stack depth two unless James explicitly accepts a deeper compile dependency;
- no slice open for more than seven days without an update or park/reshape decision;
- no feature crosses its declared appetite without a new James bet;
- two verification failures on the same acceptance gap cause reshape, not a third patch loop;
- incidents may pre-empt Focus; documentation hygiene may not unless it creates executable
  or safety drift.

## 5. Agent lanes: complete coverage with controlled overlap

### 5.1 Design rule

Every work object has:

- exactly **one accountable lane**;
- exactly **one implementation owner** for each mutable node;
- zero or more **triggered overlays** (security, performance, tax, portfolio);
- at most one **independent challenger** for a decision;
- one **verification owner** who did not author the implementation.

Overlap is intentional only when roles differ:

- producer vs challenger;
- implementer vs verifier;
- cross-system architect vs subsystem architect;
- top-down vs bottom-up independent evidence.

Two agents should not independently produce the same plan, and two mutable agents should not
edit the same node.

### 5.2 Canonical lane map

| Lane | Accountable role | Supporting agents | Deliberate overlap | Entry / exit |
|---|---|---|---|---|
| **G0 Governance + portfolio** | `arbi` | `arbi-red-team` | Arbi proposes; red-team challenges; James governs | Signal or review -> admitted/parked/rejected work with owner and authority |
| **G1 Product shaping + research** | `requirements-analyst` | `deep-research-agent`; James as single-user evidence source | Requirements shapes; deep research challenges assumptions with external evidence | Ambiguous idea -> outcome, appetite, no-gos, acceptance, confidence |
| **G2 Architecture + boundaries** | `system-architect` | `backend-architect`, `tech-stack-researcher`, dormant `frontend-architect` | System owns cross-domain shape; backend owns API/schema/write-path detail | Build-ready contract -> decision/risk/dependency map |
| **G3 Delivery planning** | `guilfoyle` | relevant G1/G2 advisers | Planner may reject executability but cannot reprioritise | Admitted contract -> slices, dependency graph, owners, checks |
| **G4 Implementation** | `reversible-work-builder` | `refactoring-expert` as advisory pattern expert; `technical-writer` for doc-only node | Exactly one mutator per node | Slice -> tested branch and draft PR |
| **G5 Verification + release evidence** | **new `verification-steward`** | `security-engineer`, `performance-engineer`, domain guards, CI | Verifier is independent; overlays activate by trigger | Draft PR -> READY / NOT READY + evidence packet |
| **G6 Investment discovery** | `macro-economist` for macro; `theme-researcher` for top-down themes; `sector-screener` for bottom-up coverage | Arbi reconciles candidates | Top-down and bottom-up evidence intentionally overlap; common candidate schema deduplicates | Question -> cited proposals only, never capital action |
| **G7 Portfolio interpretation** | `/pm-review` synthesis in main loop | `market-context-narrator`, `benchmark-performance-analyst`, `thesis-milestone-monitor`, `thesis-coherence-guard`, `portfolio-coherence-reviewer` | Multiple independent perspectives, field-owned; no agent repeats another's calculation | Review request -> evidence packet + abstain/review posture, no execution |
| **G8 Domain conformance** | owning build lane; overlays are mandatory | `tax-spec-conformance`, `portfolio-invariant-guard` | Spec/invariant check independent of implementer | Triggered diff -> conformance findings and disposition |
| **G9 Knowledge + documentation lifecycle** | Arbi owns lifecycle; `technical-writer` owns form | `learning-guide` for explanation/onboarding | Arbi decides whether an artifact should exist; writer makes it usable | New knowledge -> update existing SoT, ADR, guide, or expiry-tagged note |

### 5.3 Changes to existing roles

1. **Arbi:** broaden from brief-only prioritiser to stateful operating controller, but keep
   reasoning separate from side effects. Arbi emits typed control actions; the main loop or
   deterministic automation performs permitted writes.
2. **Guilfoyle:** plan and resource delivery only. Remove final acceptance ownership.
3. **Reversible builder:** become the only general code mutator in mission work.
4. **Refactoring expert:** advisory by default. It may be the builder for a dedicated
   behaviour-preserving `/build` task, never a concurrent second mutator.
5. **Technical writer:** write docs only after the lane owner identifies the artifact class
   and existing source to update. It must not create a new dated doc by default.
6. **Verification steward (new):** read + safe test execution, no code edits. It checks
   contract revision, acceptance coverage, risk overlays, scope, evidence, and observation
   plan. This is the only new agent justified by a clear accountability gap.
7. **Frontend architect:** remain explicitly dormant and excluded from active coverage counts
   until a UI feature is admitted.
8. **Investment agents:** publish one structured schema with field ownership. `/pm-review`
   deduplicates evidence and identifies disagreement rather than concatenating prose.

### 5.4 Machine-readable registry

Create one canonical registry, proposed path `.claude/agent-registry.yaml`, with:

```yaml
schema_version: 1
agents:
  - id: backend-architect
    lane: G2
    state: active
    role: adviser
    accountable_for: [api-design, schema-design, write-path-design]
    may_mutate: false
    triggers: [api, migration, database, auth, write-path]
    overlaps_with:
      - agent: system-architect
        reason: subsystem-detail-vs-system-boundary
    forbidden: [implementation, production-write, migration-apply]
```

Generate the human roster table from this registry or validate the Markdown against it. CI
must fail on unknown agents, duplicate accountability without an overlap reason, active lanes
with no owner, dormant agents routed by active commands, or mutation rights that disagree with
the agent file.

### 5.5 Typed handoff envelope

Every agent dispatch should receive only:

```yaml
work_id: FTR-0042/S2
contract_revision: r1
objective: "Observable outcome, not an activity"
accountable_lane: G2
agent: backend-architect
inputs:
  required: [issue-url, relevant-files, decision-ids]
  excluded: [signals, historical-backlogs]
authority:
  max_infrastructure: I2
  max_portfolio: P1
deliverable:
  format: architecture-decision
  required_fields: [recommendation, alternatives, risks, interfaces, verification]
acceptance:
  owner: verification-steward
  checks: ["no migration apply", "contract fields covered"]
escalate_when: [scope-change, reserved-decision, missing-source, confidence-below-medium]
context_budget: "contract + named files; request more explicitly"
```

This envelope is passed by the main loop. It does not need a document per dispatch; it can be
an in-memory structured output plus a trace/Issue comment.

## 6. Bounded autonomy: what to share now

### 6.1 Core principle

Delegate **coordination authority before consequential authority**. A chief of staff creates
leverage by deciding what needs attention, preparing decisions, tracking commitments, and
moving approved work—not by silently taking the founder's irreversible decisions.

### 6.2 Proposed authority matrix

| Action | Arbi now | Proposed standing state after pilot | James |
|---|---|---|---|
| Read repo/GitHub/CI/read-only production evidence | Do | Standing | Audit on demand |
| Deduplicate/classify intake | Recommend in brief | **Decide and record** | Override |
| Create/edit/comment/label/close/reopen Issues | Attended and uneven | **Standing, reversible, logged** | Override/delete |
| Maintain Projects fields and WIP | Not in force | **Standing, deterministic where possible** | Change policy |
| Route to lane and required overlays | Recommend | **Decide inside ratified policy** | Override |
| Reorder slices inside an admitted feature | Amendment-specific | **Standing** within dependency/appetite contract | Change feature priority |
| Dispatch read-only research/advice | Attended main loop | **Standing** within cost/context caps | Stop/redirect |
| Start reversible branch work on an admitted slice | Per-session/mission grant | **Attended first; candidate for standing I4 after evidence** | Stop/revoke |
| Update non-authority docs required by a shipped change | Command-scoped | **Standing through a draft PR** | Review at merge |
| Decide implementation detail with no contract/risk impact | Implicit | **Delegated to lane owner** | Exception only |
| Judge contract acceptance | Guilfoyle readiness | **Verification steward; Arbi records** | Final merge gate |
| Select/replace Focus feature or change outcome/appetite | No | No | **Decide** |
| Change acceptance criteria after build starts | No | Draft decision packet only | **Decide** |
| Merge/ready/auto-merge/default-branch push | No | No under current constitution | **Decide/act** |
| Migration apply, secrets, prod writes, workflow dispatch, deploy | No | No | **Decide/act** |
| Capital, risk appetite, Model A use, personal-advice boundary | No | Never | **Decide/act** |
| Change agent authority/constitution or self-promote | No | Never | **Ratify** |

The recommended new grant is effectively **work-control authority** between existing I2 and
I4: Arbi may maintain reversible coordination state and route approved work. Implement it as
a named permission profile rather than stretching the meanings of I2/I3.

### 6.3 Promotion protocol

No prose amendment alone should unlock standing autonomy. For each action class:

1. Define the action, tool, paths/resources, preconditions, postconditions, and rollback.
2. Run at least 20 attended samples across at least four weeks, including adversarial cases.
3. Record success, human correction, false closure, scope escape, cost, and rollback rate.
4. Require zero boundary violations and zero unlogged actions.
5. Set a maximum tolerated intervention rate; suggested starting threshold is under 10% for
   queue/routing administration and under 5% before reversible build dispatch.
6. Have an evaluator other than Arbi score the samples.
7. James explicitly promotes, holds, or rejects the action class.
8. Automatically revoke on a boundary violation, repeated stale-source use, or two bad
   closures in ten actions.

The current Amendment H is evidence for **session-bounded sequencing**, not evidence for
standing unattended implementation. Its many James clicks are useful data: classify which
were policy-required, which were mechanical/reversible, and which existed because state was
spread across artifacts.

### 6.4 Founder interrupt policy

Arbi should interrupt James immediately only for:

- suspected capital/personal-advice boundary crossing;
- irreversible data-loss or security risk;
- need for a secret, migration apply, deploy, production write, or merge;
- a choice that changes the admitted outcome, appetite, or risk posture;
- contradictory authority sources that change what is legal to do.

Everything else joins a decision batch. Each packet is:

```text
Decision ID / deadline / why now
Recommendation (one sentence)
Options (maximum three)
Evidence and uncertainty
Downside + reversibility
What Arbi will do on approval
Exact click/command, if any
```

## 7. Feature control plane

### 7.1 Source-of-truth decision

Enact ratified ADR D10:

- **GitHub parent Issue:** live feature contract, state, dependencies, decisions, and
  outcome tracking.
- **GitHub sub-issues:** independently reviewable vertical slices and non-code work.
- **Projects v2:** portfolio views and structured fields; never a second copy of narrative.
- **Branch:** isolated implementation of one slice.
- **Commit:** isolated, complete change with machine-readable identity.
- **PR:** review boundary, acceptance/evidence packet, and link back to Issue.
- **Tests/types/DDL:** executable specification, consistent with D6.
- **ADR:** durable architectural/product decision only—not status.
- **Docs:** user/developer explanation or runbook—not queue state.
- **Issue snapshot:** audit/recovery copy, not a writable competing queue.

Do not create `docs/features/FTR-*.md`. That would version prose while recreating the same
state-synchronization problem.

### 7.2 Work identities

Use monotonic repository-level IDs:

| Type | Pattern | Meaning |
|---|---|---|
| Feature/outcome | `FTR-0042` | User/product capability or outcome |
| Bug | `BUG-0042` | Incorrect observable behavior |
| Operations/reliability | `OPS-0042` | Operational control or reliability repair |
| Research/spike | `RSR-0042` | Timeboxed uncertainty reduction; no production code |
| Governance decision | `GOV-0042` | James-reserved policy/authority decision |
| Slice | `FTR-0042/S1` | One independently verifiable vertical increment |

The GitHub issue number remains the platform identifier; the work ID is the stable domain
identifier carried through branch, commits, PR, traces, and evidence.

### 7.3 Feature lifecycle

```text
Inbox -> Shaping -> Candidate -> Admitted -> Building -> Verifying
                                                     |          |
                                                     v          v
                                                  Blocked    Observing -> Done
                                                     |
                                                   Parked / Cancelled
```

State gates:

| State | Required evidence |
|---|---|
| Inbox | source + one-sentence signal |
| Shaping | problem/outcome, user, evidence, uncertainty, owner |
| Candidate | appetite, no-gos, acceptance, dependencies, risk/authority classification |
| Admitted | James bet or standing-policy citation; `contract_revision`; WIP slot |
| Building | slice owner, branch, checks, dependency links |
| Verifying | PR, CI, overlays, acceptance map, observation plan |
| Observing | merged identity, production/user evidence required, deadline |
| Done | acceptance and outcome evidence; follow-ups linked, not hidden in prose |
| Parked | explicit trigger/date; no periodic backlog grooming |
| Cancelled | reason and salvage/rollback decision |

### 7.4 Feature contract and revisioning

The parent Issue body is the editable feature contract:

```yaml
work_id: FTR-0042
contract_revision: r1
status: candidate
outcome: "James can ... so that ..."
user: James
evidence: [link-or-decision-id]
appetite: "3 implementation slices / 10 elapsed days"
no_gos: []
acceptance:
  - id: AC-1
    given: ...
    when: ...
    then: ...
observation:
  metric: ...
  window: ...
authority:
  infrastructure: I4
  portfolio: P2
dependencies: []
decision_ids: []
```

Use simple monotonic revisions, not SemVer:

- `r0` — shaping, not buildable;
- `r1` — first admitted contract;
- `r2`, `r3` — material changes after admission.

Every revision after `r1` requires an Issue comment containing the prior/new contract diff,
reason, affected slices, and decision owner. A material change to outcome, appetite, no-gos,
risk tier, or acceptance requires James. Clarification with no observable contract change may
be recorded by Arbi.

At admission, automation posts an immutable “contract lock” comment with the revision and a
digest of the normalized contract block. Each PR carries that revision and digest. This gives
the feature an auditable baseline without a second Markdown file. GitHub's issue edit history,
the lock comment, linked PR, and daily issue snapshot provide recovery layers.

Use SemVer later only if asxos declares a public API or release compatibility contract. The
feature revision describes a changed bet, not backwards compatibility.

### 7.5 Branch, commit, and PR convention

Branches:

```text
claude/ftr-0042-s1-short-slug
cursor/bug-0043-s1-short-slug
human/ops-0044-s1-short-slug
```

Rules:

1. One slice per branch and PR.
2. Base on `main` by default.
3. Stack only for a genuine compile/schema dependency; record `blocked by` on the sub-issue.
4. Stack depth is capped at two without James's exception.
5. A feature may have at most two active build PRs; research/docs do not create hidden build
   stacks.
6. Delete merged branches; preserve history in the PR.

Commit format:

```text
feat(decision-engine): persist challenge evidence

Work-Item: FTR-0042/S2
Contract-Revision: r1
Decision-Refs: GOV-0017
```

Use Conventional Commits for change intent, but treat the trailers as the control-plane
identity. Squash-merge titles should preserve the work ID, for example:

```text
feat(decision-engine): persist challenge evidence [FTR-0042/S2]
```

Required PR sections:

```text
Work item / contract revision + digest
Outcome advanced
What changed / what did not
Acceptance map: AC -> test/evidence
Risk overlays and dispositions
Migration/deploy/secret/capital clicks reserved to James
Observation plan
Rollback/revert path
Dependencies and follow-ups (linked Issues only)
```

No “follow-up” may exist only in a PR review comment or handoff. It is either a linked Issue
with disposition or explicitly rejected.

### 7.6 Projects configuration

One project, with the minimum useful fields:

| Field | Values / purpose |
|---|---|
| Status | lifecycle above |
| Work ID | stable `FTR/BUG/OPS/RSR/GOV` identifier |
| Type | feature, bug, ops, research, governance |
| WIP lane | Focus, Keep-safe, Shape, Later, Parked |
| Accountable lane | G0-G9 |
| Risk | A, B, C plus I/P ceilings |
| Contract revision | `r0`, `r1`, ... |
| Next gate | concrete state gate, not prose status |
| Blocked by | dependency relationship, not free-text duplication |
| Observation due | date |
| Last verified | automation timestamp |

Views:

- **James:** Focus + decisions required + blocked/overdue.
- **Arbi control:** all active work grouped by status, with WIP limits.
- **Delivery:** admitted/building/verifying grouped by accountable lane.
- **Observation:** merged but not outcome-verified.
- **Debt/parked:** only items with an explicit trigger; auto-archive expired noise.

GitHub supports sub-issues, dependency links, custom fields, board/roadmap/table views, column
limits, and built-in automation. Use those primitives before writing custom software.

### 7.7 Definition of ready, done, and observed

**Ready** means the contract is `r1+`, the outcome and appetite are clear, no-gos and
acceptance are testable, authority is classified, dependencies are linked, and a WIP slot is
available.

**Code done** means the PR is merged with acceptance evidence and no unowned follow-up.

**Feature done** means the observation window has produced the promised outcome evidence or
an honest miss, and Arbi has recorded the result. “PR merged” is not feature completion.

This separates delivery from learning and stops stage cells from turning green because a plan
or work order exists.

## 8. Documentation lifecycle: stop the spiral

### 8.1 Artifact classes

| Class | Purpose | State allowed? | Update rule |
|---|---|---|---|
| Authority/policy | What is allowed and why | Stable policy only | James-ratified amendment; one canonical file per concern |
| ADR/decision | Durable decision + context + consequences | Decision status only | Append/supersede; never carry task lists |
| Reference | Exact interfaces, schemas, commands | No work state | Update with code in same PR |
| How-to/runbook | Steps to achieve/respond | No portfolio state | Testable commands; owner + verification date |
| Explanation | Why system works this way | No work state | Update when model changes |
| Work state | What is being done | **GitHub only** | Issue/Project automation |
| Evidence/event | What happened | Append-only system record | PR, commit, run, trace, issue snapshot |
| Ephemeral research | Timeboxed uncertainty reduction | Temporary status + expiry | Promote conclusion to ADR/Issue or archive/delete |

Diátaxis' separation of tutorials, how-to guides, reference, and explanation is useful here
because mixed-purpose pages become difficult to use and maintain. Work state is a fifth class
for asxos, but it belongs outside narrative docs.

### 8.2 Rules

1. **Update before add.** A new doc needs an artifact class, owner, consumer, expiry or
   permanence reason, and proof no canonical file already serves the purpose.
2. **No dated session handoff by default.** Open work is in Issues; session delta is an Issue
   comment or Arbi trace. Create an incident/postmortem only when the history itself matters.
3. **No queue in Markdown.** Plans may describe a rollout but every executable node is a
   linked Issue; status appears only in Projects.
4. **No counts or “latest” pointers copied into guides.** Generate indexes/counts or query the
   canonical source.
5. **No stale banner accretion.** Living docs contain current truth plus git history, not a
   reverse-chronological stack of prior truths.
6. **No proposal remains “current” after decision.** Adopt into authority/ADR, reject, or
   archive.
7. **Docs changed with behavior.** Reference/how-to changes land in the same PR as the code.

### 8.3 Automated controls

Add a small Python check, proposed `scripts/check_control_plane.py`, to validate:

- registry schema and lane coverage;
- duplicate/unknown work IDs and contract revisions in PR metadata when available;
- prohibited live-state headings in Markdown outside approved record files;
- proposal/research expiry metadata;
- broken internal links and references to deleted paths;
- stale `REQUIRED_MIGRATIONS`, Model A, Render, and other forbidden executable references;
- agent count/roster generated from the registry;
- no active command routes to a dormant/deleted agent or path;
- no more than one declared canonical source for each governance concern.

Start in report-only mode. Make it blocking only after the existing corpus is baselined and
the false-positive rate is acceptable.

## 9. Implementation plan for Claude

### Wave 0 — ratify the decisions; do not code yet

James answers five questions:

1. Enact D10 now: GitHub Issues + one Project become live state; `roadmap-state.md` ceases to
   be a queue.
2. Approve the three-slot WIP model and stack-depth-two default.
3. Approve `verification-steward` as the one new agent.
4. Approve work-control authority as a promotable, reversible class while retaining all
   I5/I6/P5/P6 and constitutional stops.
5. Choose whether to finish the Amendment H stack before migration (recommended) or park it.

**Exit:** one `GOV-*` Issue records the rulings. This plan remains non-authoritative until then.

### Wave 1 — establish the control plane (one PR)

Files/changes:

- update the three Issue forms to add work ID, accountable lane, appetite, observation,
  authority, and contract revision fields;
- add governance/decision issue form;
- add a PR template with control-plane metadata and acceptance map;
- document the Projects fields/views/automations as a short setup checklist in the existing
  operations reference, not a new strategy doc;
- repair and observe `issue-snapshot.yml` so the audit snapshot is non-empty;
- add tests for forms/template/snapshot structure.

James-only work: create/configure the Project and any `.github/**` edits that current hooks
reserve to him; Claude may prepare exact patches if required.

**Exit:** one pilot Issue can move Inbox -> Candidate with structured fields and be recovered
from the snapshot.

### Wave 2 — canonicalize routing (one PR)

Files/changes:

- add `.claude/agent-registry.yaml`;
- reconcile all 25 active/dormant agent files with the lane map;
- add `verification-steward.md`;
- make `refactoring-expert` advisory-by-default and the builder the only general code mutator;
- generate or validate `.claude/agents/README.md` from the registry;
- update `harness-profiles.md` to reference the registry rather than duplicate the roster;
- implement the typed handoff envelope schema and tests.

**Exit:** every active agent has one lane, every lane has an accountable role, every overlap
has a reason, and CI catches a synthetic gap/duplicate.

### Wave 3 — make Arbi operate the queue (one or two PRs)

Files/changes:

- refactor `/arbi` from full-doc wake to delta/exception/decision brief;
- add deterministic intake, classification, WIP, stale-item, stack-depth, and decision-SLA
  checks;
- have Arbi emit structured actions while the main loop performs permitted side effects;
- have `/arbi-mission` accept only an admitted work ID + contract revision;
- move readiness judgment from Guilfoyle to verification steward;
- link trace/ledger events by work ID rather than writing session narrative.

**Exit:** the pilot feature can be routed end to end without creating a roadmap entry,
proposal, backlog row, or session handoff.

### Wave 4 — retire executable drift (one PR)

Inventory all 33 commands and classify each `active`, `alias`, `dormant`, or `delete`.

At minimum:

- complete or supersede open PR #189 rather than duplicating its corrections;
- remove/redirect `sprint-*` commands inconsistent with D6;
- remove or quarantine commands that reference deleted Model A writers/paths;
- update migration checks to the current name-set mechanism;
- remove obsolete Render/review-gate claims;
- add the control-plane checker in report-only mode, then fix the baseline.

**Exit:** active commands reference only live agents, paths, and policies; zero known stale
executable references.

### Wave 5 — migrate state and collapse documents (one carefully reviewed PR)

1. Convert only **currently actionable** roadmap/backlog/inbox rows to Issues, preserving
   source links and decision IDs.
2. Mark the 1,941-line `roadmap-state.md` historical or reduce it to product-stage reference
   with no task state.
3. Replace the dated truth-map approach with generated validation/index output.
4. Archive superseded proposals and old root handoffs without rewriting git history.
5. Reduce `docs/README.md` to a generated or validated reader map by artifact class.
6. Keep the decision log/ADRs only for durable decisions; link Issues for execution.

**Exit:** a normal Arbi session writes no product-state Markdown. New work appears once in
GitHub and nowhere else.

### Wave 6 — autonomy pilot and promotion

Pilot in order:

1. issue classification/labeling;
2. Projects status/WIP updates;
3. stale-item escalation and decision batching;
4. read-only specialist dispatch;
5. closure after verifier evidence;
6. reversible build dispatch on admitted slices.

Run attended first. Record at least 20 examples per action class, then submit promotion
packets. Do not bundle permissions: classification can promote even if build dispatch cannot.

**Exit:** James has a measured promote/hold/revoke decision for each action class.

### Wave 7 — first feature under the new model

Choose a modest, non-migration, non-capital feature that is not part of the in-flight
Amendment H stack. Run it from Issue intake through observation.

Success conditions:

- no new proposal or handoff doc;
- one parent Issue and no more than three slices;
- no stack deeper than two;
- every agent handoff is typed and traceable;
- James sees only the bet and reserved gates;
- feature closes on observed outcome, not merge;
- retrospective produces at most one promoted lesson.

## 10. Migration and compatibility rules

1. **Do not churn open PRs.** Existing PR numbers, bases, and Amendment H contracts remain
   valid until merged or parked.
2. **Do not dual-write after cutover.** Once D10 is in force, Issues/Projects win; do not
   update roadmap task state “for safety.”
3. **Preserve durable decisions.** ADRs, constitutional rulings, and financial boundaries are
   not converted into Issues; implementation of a ruling is.
4. **Carry source links.** Migrated Issues link the exact historical doc section/commit.
5. **Archive, do not delete, disputed history.** Git already preserves it, but an archive
   banner prevents accidental execution.
6. **Observe the snapshot before demoting the roadmap.** A non-empty successful Issue snapshot
   is the recovery gate.
7. **Keep hooks authoritative during transition.** Prompt/registry clarity never substitutes
   for tool, hook, CI, branch, and environment enforcement.

## 11. Measures

Baseline before Wave 1, then review weekly:

| Outcome | Metric | Initial target |
|---|---|---|
| Founder focus | Unplanned James interrupts per week | Down 50% after four weeks |
| Decision quality | Reserved decisions with complete packet | >=95% |
| Queue truth | Active items represented in exactly one live state system | 100% |
| Ownership | Active items with one accountable lane and next gate | 100% |
| Delivery flow | Median admitted-to-merged lead time | Baseline, then improve 20% without defect increase |
| Stack risk | PRs deeper than two | 0 without explicit exception |
| WIP | Active build PRs per feature | <=2 |
| Closure | Merged features still missing observation after due date | <10% |
| Handoff quality | Agent outputs rejected for wrong scope/format/source | <10%, trending down |
| Autonomy | Human correction/intervention by action class | Below promotion threshold |
| Safety | Boundary violations or unlogged actions | 0 |
| Doc health | New dated proposals/handoffs after cutover | 0 by default |
| Executable truth | Active commands with stale paths/policy | 0 |
| Cost | Model/tool cost per completed feature | Visible and stable/down |

Do not reward raw task count, agent count, tokens, PR count, or autonomous duration. Reward
observed outcomes, fewer founder interruptions, low rework, and intact boundaries.

## 12. Risks and trade-offs

| Risk | Mitigation |
|---|---|
| Arbi becomes a bottleneck | Deterministic routing and state transitions; Arbi handles exceptions, not every mechanical update |
| Projects becomes another stale board | One-source rule, built-in automation, daily snapshot, and no Markdown dual-write |
| Issue contracts become prose novels | Strict template, appetite/no-gos/ACs, executable specs in tests/types/DDL |
| Stable IDs add ceremony | Automation assigns them; IDs earn their cost by linking every artifact |
| New verifier slows delivery | Trigger once per PR, structured acceptance map, no implementation authority; measure lead-time impact |
| Over-specialization increases context cost | One accountable lane, trigger-based overlays, typed context-minimal handoffs |
| More autonomy hides mistakes | Per-action promotion, trace every action, independent verification, automatic revoke |
| Deep stacks recur | Default-to-main, depth-two/WIP controls, explicit exceptions, Project visibility |
| Document cleanup destroys useful history | Archive/supersede, preserve git history and source links; migrate active state only |
| Current governance conflicts block adoption | Wave 0 records explicit rulings; no authority inferred from this proposal |

## 13. Recommended James rulings

Recommended answers to Wave 0:

1. **D10:** enact GitHub Issues + Projects after one successful non-empty snapshot; freeze
   `roadmap-state.md` as task state immediately after.
2. **WIP:** approve Focus 1 / Keep-safe 1 / Shape 1 and stack depth two.
3. **Roster:** approve one new read-only `verification-steward`; add no other agents now.
4. **Autonomy:** approve a measured work-control pilot for Issues/Projects/routing/closure;
   retain merge, ready, deploy, migration, secrets, production, capital, and authority changes.
5. **Transition:** finish or explicitly park Amendment H under its current bases; pilot the
   control plane on the next independent feature.

## 14. Claude execution handoff

Paste or point Claude to this section after James records the five rulings:

```text
Implement the ratified parts of
docs/proposals/arbi-chief-of-staff-and-feature-control-plane-plan-2026-09-03.md.

Read first: CLAUDE.md, docs/product/harness-profiles.md, the newest merged session
handoff, the live GOV Issue recording James's rulings, and this plan. Inspect live
GitHub state before choosing a base; do not assume the 2026-09-03 PR stack is unchanged.

Execute Waves 1-7 in order, using one parent Issue for the programme and a sub-issue
per wave. Do not create another roadmap, session handoff, dated proposal, or feature
spec document. Update existing canonical docs only where behavior/policy changes.

Hard constraints:
- This plan itself grants no authority.
- Preserve all I5/I6/P5/P6 and constitutional stops unless James's recorded ruling
  explicitly changes them.
- No merge, ready, deploy, migration apply, production write, secret access/creation,
  capital action, or Model A resurrection.
- Do not restack or rename the in-flight Amendment H PRs merely to match the new model.
- Reuse or supersede open PR #189; do not duplicate its doc-drift work.
- One accountable lane and one mutator per node.
- Default PR base is main; stack depth <=2 without a recorded James exception.
- Tests and validation proportional to each wave; draft PR ceiling.
- Every follow-up is a linked Issue with owner/disposition, never prose-only.

Start by returning a live-state delta and the exact Wave 1 task graph. If the GOV
rulings are absent or the Issue snapshot is still empty/failing, stop at that named
gate and prepare the smallest decision/remediation packet; do not infer approval.
```

## 15. Bottom line

Arbi already has the beginnings of a strong operating constitution. The next maturity step
is not another autonomy manifesto. It is a small, executable management system:

- one live work substrate;
- one stable identity per outcome;
- one accountable lane per work object;
- one code mutator per node;
- independent verification;
- measured, action-specific autonomy;
- batched founder decisions;
- feature completion tied to observed outcomes;
- documentation that explains and records, but does not pretend to be a database.

That gives Arbi genuine chief-of-staff leverage while keeping James unmistakably in the
governor's seat.
