# Building a Roadmap, Backlog, and Ticketing System for a Solo AI-Agent-Driven Python Data/ML Product (asxos)

## TL;DR
- **Keep the whole system in the repo as Markdown, driven by Backlog.md (MIT-licensed, ~6.5k stars) plus GitHub Issues used sparingly as an "inbox," with PROJECT_STATUS.md staying as your canonical Now/Next/Later roadmap.** This is the only combination that is diffable, offline, agent-readable via both a CLI and an official MCP server, and free — matching your CLI-first, Claude-Code-driven, single-user reality without importing team ceremony.
- **Separate your three work types into three explicitly different ticket shapes**: product-engineering tickets (full acceptance criteria + files-to-touch + approval tier), data-infrastructure tickets (migration-first ordering + schema guards), and research/experiment tickets (pre-registered falsification conditions + timebox, judged on decision quality, never on shipped code). Do NOT estimate research with story points; timebox it.
- **Adopt almost none of the standard agile apparatus** (no sprints-as-ceremony, no story points, no RICE spreadsheets, no backlog grooming meetings, no velocity). For a single-user product where "customer value" is your own judgement, use a lightweight value/effort call plus Shape Up's "appetite" and "circuit breaker," and treat the backlog as a deliberately short "to-don't list," not an archive.

## Key Findings

### 1. Roadmapping — what transfers to a solo operator and what doesn't
- **Now/Next/Later (NNL)** — invented by ProdPad co-founder Janna Bastow as a reaction to timeline/Gantt roadmaps — organizes by *confidence horizon*, not dates. This is the single most transferable roadmap format for you: "Now" = validated and in progress, "Next" = high confidence, "Later" = bets not yet explored. Recommended review cadence from practitioners: update Now weekly, Next monthly, Later quarterly. This maps cleanly onto your existing milestone-with-calendar-dates approach.
- **Shape Up (Basecamp)** contributes three ideas worth stealing even though the full system is built for ~50-person Basecamp: **appetite** (decide how much time something is *worth*, not how long it will take), the **circuit breaker** (if a bet isn't done in its fixed time box, it does NOT get an automatic extension — it dies by default, forcing re-shaping), and **"no backlog"** (Basecamp deliberately does not maintain a big shared backlog; important ideas resurface). Basecamp's own appendix explicitly says a tiny team should "throw out most of the structure… no cool-down period, formal pitches or a betting table… the same people can alternate back and forth," which is precisely your case.
- **Outcome-based / OKR-linked roadmaps** and **GIST/theme roadmaps** mostly solve a *communication-with-stakeholders* problem you do not have. Their value for you is only the discipline of framing items as problems/outcomes ("improve my ability to trust a screen's backtest") rather than features ("add dashboard"). Don't build OKR scaffolding for an audience of one.
- **Roadmap-as-fiction** is the dominant failure mode across every source: dated roadmaps become commitments that break, then nobody trusts them. The stated fix is universal — drop dates as promises, keep horizons, and make movement between horizons an explicit, logged decision. For you, PROJECT_STATUS.md already is this artifact; the discipline is to actually move things and record *why*.
- **Research/ML roadmapping**: the literature strongly supports separating a **discovery/experiment backlog** from a **delivery backlog** (Lean UX's "dual-track": one team, two backlogs). Uncertain work is handled with **spikes** — time-boxed research items (XP origin, Kent Beck) that are explicitly *not estimated* because they don't deliver customer value; you set a timebox as "the maximum time before we discuss again," not a deadline. **Pre-registration** — declaring hypotheses, metrics, and analysis plan *before* seeing data — has migrated from psychology/clinical science into ML as a defense against the "garden of forking paths" and post-hoc p-hacking (choosing metrics after seeing results). Your existing pre-commitment/falsification discipline is exactly this practice and is genuinely ahead of most ML teams.

### 2. Backlog construction — what granularity actually works
- **Hierarchy**: epic → story → task is standard, but for a solo dev the useful unit is a single reviewable task = one agent context window = one PR. Backlog.md explicitly encodes this: "one task = one context window = one PR." Deep epic/feature/story/task/subtask nesting is overhead you don't need; use milestone → task with optional sub-tasks.
- **Ticket writing**: **INVEST** (Independent, Negotiable, Valuable, Estimable, Small, Testable — Bill Wake) remains the best quality checklist for an individual ticket. For agent execution, **job stories** and plain problem statements beat the "As a user…" template — with one user, the "As a user" framing is noise. Keep the *value* clause ("so that…") because it stops you building things you don't need.
- **Acceptance criteria**: **Given/When/Then** maps directly onto automated test cases, which is exactly what you want when an agent implements a ticket — the criteria become the tests. Use checklists for simple tickets, Given/When/Then when behavior matters.
- **Definition of Ready / Definition of Done**: DoR (enough context to start) and DoD (tests pass, docs updated, conventional commit, merged) are worth keeping as *short reusable checklists* embedded in the ticket template — Backlog.md supports a reusable DoD. They are the cheapest quality gate you have as a solo dev with no reviewer.
- **Grooming / the backlog-as-graveyard problem**: every credible source warns the backlog becomes a wasteland. Shape Up's answer ("no backlog") and the "backlog is a to-don't list" argument both point the same way: prune aggressively, auto-close stale items, declare "backlog bankruptcy" periodically. For you: cap the backlog, and if an item has sat untouched for a quarter, close it — "important ideas come back."
- **Prioritization frameworks**: RICE (Reach×Impact×Confidence÷Effort, from Intercom's Sean McBride), ICE, WSJF (SAFe/Reinertsen, Cost of Delay ÷ Job Size), MoSCoW, Kano. The evidence is blunt: these turn subjective guesses into subjective guesses that *look* mathematical (Saeed Khan's widely-cited critique notes the inputs aren't ratio-scale numbers and carry no margin of error). **Reach is meaningless with one user.** For a single-user product, RICE/WSJF collapse. What survives: a simple **value/effort 2×2** (fastest triage) and Shape Up **appetite**. Practitioner consensus already says small/early teams should use Impact-Effort or ICE, not RICE.
- **WIP limits / flow**: the small-batch-flow evidence (short cycle time, low WIP) genuinely transfers to solo work — one main thing in progress at a time. Kanban-style Now/In-Progress/Done beats Scrum ceremony for one person. "No process at all" is a trap for agent-driven work because agents need explicit structured tickets to execute unambiguously.

### 3. Issue/ticketing tools — the comparison that matters for you
- **Git-native / in-repo trackers** are the natural fit for a CLI-first, agent-driven, single-user repo. Trade-offs are consistent across sources: **upside** = offline, diffable, version-controlled with the code, no API rate limits, no context-switching, agent-readable as plain text, travels with `git clone`, no vendor lock-in; **downside** = no notifications, weak querying, no mobile, no pretty management reports, and (the honest structural critique) no format standard / ecosystem, and they exclude non-developers. For a solo developer these downsides barely bite.
  - **Backlog.md** (github.com/MrLesk/Backlog.md, MIT, ~6.5k stars, TypeScript/Bun): tasks are plain `.md` files with frontmatter (status, assignee, priority, labels, dependencies, acceptance_criteria, definition_of_done, milestone); zero-config CLI (`backlog task create`, `backlog board`, `backlog browser` web UI); ships an **official MCP server** (`claude mcp add backlog -- backlog mcp start`) AND a CLI; explicitly built for Claude Code/Codex/Gemini; enforces a **three-checkpoint spec→plan→code review** workflow ("AI agents write the code. You review the tasks: before, during, and after"); the project dogfoods itself. This is the strongest git-native option and is designed for exactly your workflow. Known limitation: the MCP server can write to the main repo rather than the current worktree; "one PR per task" is convention, not enforced.
  - **git-bug** (git-bug/git-bug, GPLv3): stores issues as git *objects* in `refs/bugs`, not files — so no working-tree clutter — with CLI/TUI/web and bridges to GitHub/GitLab/Jira. Strong for offline archives; but issues-as-objects are *not* plain diffable markdown an agent reads naturally, and the web UI is not feature-complete. Runner-up in the git-native class, weaker for agent-readability than Backlog.md.
  - **Others** (tissue, ripissue, sit, dspinellis/git-issue, Sciit, plain todo.txt / committed Markdown task files): all viable minimalist options; the "issues live next to the code" philosophy is sound. But none has Backlog.md's Claude-Code integration, and plain hand-rolled Markdown loses the CLI/MCP query surface.
- **Hosted trackers**:
  - **GitHub Issues + Projects v2**: free, deepest possible git integration (commit/PR auto-linking, "Fixes #1" auto-close), and — critically — drivable by Claude Code **with no MCP server at all** via the `gh issue` CLI (create/list/view/edit/comment/develop/close, plus `gh api` for GraphQL) and via **@claude GitHub Actions mentions** (`anthropics/claude-code-action`, GA v1 on Aug 26 2025: mention @claude on an issue → it branches, implements, opens a PR). There is also an **official GitHub MCP server** (github/github-mcp-server, MIT, ~32k stars; remote hosted at api.githubcopilot.com/mcp) that reads/creates/updates Issues and (since Oct 14 2025, off by default) Projects v2. Widely used by solo devs as a planning tool.
  - **Linear**: free tier (250 active issues, unlimited members — enough for solo), $8+/user/mo paid; fastest UX, keyboard-first, excellent GitHub PR/branch automation, and an **official remote MCP server** (mcp.linear.app/mcp, launched May 1 2025) that creates/updates/reads issues, projects, comments — works with Claude Code (`claude mcp add linear --transport http https://mcp.linear.app/mcp`). The strongest hosted option *if* you want notifications/mobile, but it pulls state out of the repo.
  - **Jira**: enterprise-grade reporting and configurability, but heavy, and the community-standard mcp-atlassian server had two serious CVEs (CVE-2026-27825 CVSS 9.1 RCE; CVE-2026-27826 SSRF) patched in v0.17.0 (Feb 2026). Overkill and net-negative for a solo operator.
  - **Shortcut / Height / Notion / Trello / Plane / OpenProject / Taiga**: Shortcut is a lighter Linear-like ($8.50/user/mo, free ≤10 users). Height shut down September 2025 — do not adopt. Notion databases are flexible but agent-writable only with caveats (the official Notion MCP has documented prompt-injection exposure). Trello is loved by some solo founders for simplicity but has no code integration. Plane (open-source, ~46k stars, self-hostable, has a native MCP server) and OpenProject/Taiga are the self-host options — real but operational overhead you don't want to run alongside Render/Supabase.

### 4. AI-agent-native workflows — the important, still-partly-unproven part
- **Spec-driven development (SDD)** is the dominant 2025–2026 pattern for making agent work reliable. **GitHub Spec Kit** (github/spec-kit, MIT, reached 1.0.0; `specify` CLI; slash commands `/speckit.specify` → `/speckit.plan` → `/speckit.tasks` → `/speckit.implement`; artifacts `constitution.md`, `spec.md`, `plan.md`, `tasks.md` committed to the repo) and **Amazon Kiro** (requirements.md in EARS format / design.md / tasks.md) both encode the same insight: *write the spec first, as files in the repo, then let the agent execute*. This directly generalizes your "pre-registration/pre-commitment before building" discipline. Your CLAUDE.md is already your `constitution.md`.
- **AGENTS.md / CLAUDE.md convention**: persistent, repo-committed context files are now standard; Spec Kit supports 30+ agents through them. Keep CLAUDE.md as the constitution and add a per-ticket spec.
- **Claude Code specifically**: GitHub Actions integration (@claude mentions, `/install-github-app`), plan mode + TodoWrite task lists, custom slash commands, subagents, and hooks are all documented and map onto your discovery-waves/wave-gates model. The @claude-from-an-issue → PR loop is real and can be gated to require your approval (only users with write access can trigger it).
- **The harness matters more than the model**: multiple 2026 practitioner sources (HumanLayer, Anthropic/OpenAI harness-engineering docs, Martin Fowler/Böckeler) converge on "a weaker model with a good harness routinely beats a smarter model with none." Your CLAUDE.md + slash commands + tiered approval *is* the harness.
- **What is hype / unproven — surface honestly**:
  - **AI "slop"** was named Merriam-Webster's 2025 Word of the Year on Dec 15 2025, defined as "digital content of low quality that is produced usually in quantity by means of artificial intelligence" (The Economist independently chose "slop" for 2025 too).
  - **Hard evidence of degradation**: CodeRabbit's "State of AI vs Human Code Generation" report (Dec 17 2025), analyzing 470 GitHub PRs (320 AI-coauthored, 150 human), found AI PRs averaged **10.83 issues each vs 6.45 for human PRs (~1.7×)** — logic/correctness 1.75×, security 1.57×, performance 1.42×, XSS 2.74×; David Loker (Director of AI) summed it up: "AI coding tools dramatically increase output, but they also introduce predictable, measurable weaknesses that organizations must actively mitigate." GitClear's analysis of **211 million changed lines (2020–2024)** found code churn (code rewritten/deleted within two weeks) nearly doubled from 3.1% to 5.7%, refactoring activity fell from ~25% toward under 10%, and copy-pasted/duplicated code exceeded moved (refactored) code for the first time. The **SlopCodeBench** paper (2026) found no agent solved any problem end-to-end across 11 models, with structural erosion in ~80% of trajectories and agent code ~2.2× more verbose than human code and degrading each iteration.
  - **METR's July 2025 RCT** ("Measuring the Impact of Early-2025 AI on Experienced Open-Source Developer Productivity," arXiv 2507.09089) found: "developers forecast that allowing AI will reduce completion time by 24%... we find that allowing AI actually **increases completion time by 19%**" — based on 16 developers, 246 tasks, primarily Cursor Pro + Claude 3.5/3.7 Sonnet. (METR's Feb 2026 follow-up estimates ~18% *speedup* for late-2025 tools, so the picture is improving but the caution stands: measure it in your own context rather than assuming a speedup.)
  - **Agents flooding backlogs with low-quality issues/PRs** is a documented open-source crisis (maintainers auto-closing external PRs; "tragedy of the commons" framing in the Baltes/Cheong/Treude 2026 study of 1,154 posts). Amazon's Kiro caused a ~13-hour AWS outage in Dec 2025 when an agent was given broad permissions and chose to "delete and recreate the environment." Anthropic's own April 2026 postmortem admitted regressions slipped past multiple human and automated reviews.
  - **Takeaway for you**: your three-tier L1/L2/L3 model and human approval gates are exactly the right defense, and the evidence says you should keep the review gates *tighter*, not looser, as models improve. Prevent agent-generated backlog slop by requiring every agent-opened ticket to pass your Definition of Ready before it's allowed to exist.

### 5. Traceability and engineering hygiene
- **Conventional commits + automated changelog**: you already enforce conventional commits. The natural pairing is **release-please** (Google; reads conventional commits, maintains a "Release PR" with changelog + version bump that you merge when ready — a human gate you'll like) over **semantic-release** (fully automatic, fires on every merge — too hands-off for your taste) or **changesets** (best for JS monorepos; you're Python). release-please supports Python and gives you the "we decide when we ship" button.
- **ADRs**: use **Nygard's original format** (Title/Status/Context/Decision/Consequences), not MADR — the consensus is MADR is overkill except for genuinely contested trade-offs. Store ADRs in-repo (`docs/adr/NNNN-*.md`), one decision per ADR, never edit an accepted one (supersede it). The dominant failure is "Decision Documentation Theater" — teams pick a format, write five, then stop — so define *when* an ADR is required (tie it to L3 decisions: ML pipeline, migrations, auth, security) and keep them next to the code. ADRs are where your research/methodology decisions live.
- **Schema drift (your specific failure mode — 4 of 6 prod bugs in one sprint)**: the literature gives a clear, proven playbook. (1) **Migrations are the single source of truth**, committed in the same repo/commit as the code that depends on them ("migration-first commit ordering"). (2) **Never hand-edit production schema** — production changes arrive only through a reviewed, committed migration applied by your runner, never `psql`. (3) **Generate types/schema from the DB and fail CI on drift** (the `git diff --exit-code` pattern after regenerating). (4) **CI gate that replays full migration history into a clean database and asserts zero introspection diff.** (5) **expand-contract pattern** for renames (never rename in place). (6) Consider a tool like **Atlas** for drift detection, or a lightweight home-grown "DDL guard" test. For an agent specifically: add a discovery-wave audit agent whose only job is to verify every table/column a query references actually exists in the committed schema before the sprint — this directly attacks your recurring bug.
- **Technical debt as a first-class item**: track it as a labeled backlog type with an explicit "cost if we don't" note, but cap it and schedule it into Shape Up-style "cool-down" slack so it doesn't become its own wasteland.

### 6. Real-world examples to learn from
- **Formalized proposal processes**: Python **PEPs**, Rust **RFCs**, and Kubernetes **KEPs** (KEP explicitly "stolen from the Rust RFC process which itself resembles the Python PEP process") are the gold standard for *documenting significant decisions as numbered, versioned, in-repo markdown with status fields*. For you this validates numbered ADRs + a lightweight "proposal" for research directions. Note PEPs are kept updated with status transitions; Rust RFCs are criticized for going stale — a warning to keep your ADR statuses current.
- **Supabase** maintains a public roadmap via GitHub Discussions; **GitHub Issues + Projects v2** with labels/milestones/templates is how most well-run OSS projects (Django, Home Assistant, Supabase) actually operate — issue templates and a tight label taxonomy are the reusable lessons.
- **Solo-founder practice**: documented setups converge on three answers — GitHub Issues+Projects (deepest code integration, free, "issues live with the code"), Notion/Linear free tier, or "just the notes app." A recurring solo-dev manifesto pattern: daily kanban check, timeboxed focus blocks, write a failing test before fixing a bug, stop-the-line for major issues. The honest signal: solo founders who adopt team-scale tooling (ClickUp/Asana/Jira) report it *slows them down*.

## Details — the recommended system for asxos

### A. Tool choice
**Primary: Backlog.md as the in-repo tracker, + GitHub Issues as a thin "inbox," + PROJECT_STATUS.md as the roadmap. Cost: $0.**

Reasoning: it is the only option that satisfies all your hard constraints simultaneously — CLI-first, offline, diffable, version-controlled next to the code, driven by Claude Code through *both* a CLI and an official MCP server, free, no vendor lock-in, and structurally built around the spec→plan→code review checkpoints that match your pre-registration + wave-gate discipline. Tasks as plain markdown means an agent reads and writes them with zero translation layer and no API rate limits, and every change is a reviewable git diff — which is also your slop defense.

**Runner-up: GitHub Issues + Projects v2 alone**, driven by the `gh` CLI and @claude Actions. Choose this instead if you decide you want notifications, mobile, and the @claude-issue→PR loop more than you want issues living in the repo. It's free and the integration is deepest-possible, but state lives on GitHub's servers, not in your `git clone`. A pragmatic hybrid (and my actual recommendation): **Backlog.md for the working backlog/tickets in-repo; GitHub Issues only for things you want to capture from your phone or that might become public.** Avoid Linear/Jira/Plane — Linear is excellent but pulls state out of the repo for a benefit (collaboration) you don't need; Jira and self-hosted Plane/OpenProject are pure overhead for one person.

### B. Roadmap artifact
Keep **PROJECT_STATUS.md** as the canonical roadmap, restructured as **Now / Next / Later** with your milestone calendar dates attached only to "Now":
- **Now** (this milestone, dated): validated, in progress. Max ~3 items.
- **Next** (next milestone, rough): high confidence, not yet started.
- **Later** (unbounded, undated): bets and research directions. Deliberately loose; not a backlog.
- Each item framed as a problem/outcome with an appetite (how much time it's worth) and, for research, a falsification condition.
- **Review cadence**: Now weekly (5 min), Next monthly, Later quarterly (prune ruthlessly). Log every move between horizons with one line of *why* — this is what keeps it from becoming fiction.

### C. Backlog structure, workflow, labels, three work types
- **Hierarchy**: milestone → task (→ optional sub-task). One task = one agent context window = one PR.
- **States**: `backlog → ready → in-progress → in-review → done` (+ `blocked`, `archived`). "ready" means it passed Definition of Ready.
- **Label taxonomy** (keep it small):
  - **Type**: `product`, `data-infra`, `research`, `bug`, `tech-debt`, `spike`
  - **Approval tier**: `L1`, `L2`, `L3` (mirrors your incident model)
  - **Area**: `pipeline`, `ml`, `db`, `cli`, `email`, `cron`, `screens`
  - **Horizon**: `now`, `next`, `later`
- **The three work types handled differently**:
  - **Product engineering** (`product`): full ticket schema — context, files-to-touch, Given/When/Then acceptance criteria, out-of-scope, test requirements, approval tier. Estimable and shippable.
  - **Data-infrastructure** (`data-infra`): same schema **plus mandatory migration-first ordering, schema-source-of-truth note, and a CI-guard checkbox** ("regenerated types, zero introspection diff"). Default approval tier L3 (migrations are in your L3 list).
  - **Research/experimentation** (`research`/`spike`): a **different template** — a pre-registration block (hypothesis, success metric, falsification condition, timebox) instead of acceptance criteria. **Not estimated; timeboxed.** Output is a decision or an ADR, never "shipped code." Judged on decision quality. Lives in the discovery/experiment backlog, kept separate from the delivery backlog. Default approval tier L3 (ML pipeline).

### D. Copy-pasteable templates

**Product / data-infra ticket (Backlog.md task body):**
```markdown
---
title: "<verb-first, specific>"
status: ready
type: product        # or data-infra
approval_tier: L2    # L1 | L2 | L3
area: [pipeline]
horizon: now
priority: medium
dependencies: []
---
## Problem / Outcome
<one sentence: the problem, and why it matters now — the "so that">

## Context for the agent
- Relevant files: `path/a.py`, `path/b.py`
- Relevant ADRs: ADR-00xx
- Data/schema touched: <tables/columns, or "none">

## Files to touch (expected)
- `path/to/file.py` — <what changes>

## Acceptance criteria (Given/When/Then)
- Given <state>, when <action>, then <observable result>
- [ ] ...

## Out of scope (No-gos)
- <explicitly excluded>

## Test requirements
- [ ] New/updated tests in `tests/...`
- [ ] All ~500 tests pass
- [ ] (data-infra) migration committed BEFORE dependent code; types regenerated; CI drift check green

## Definition of Done
- [ ] Acceptance criteria met
- [ ] Conventional commit(s)
- [ ] PROJECT_STATUS.md updated if milestone-affecting
- [ ] Approval tier respected (see below)

## Approval tier
L2 — agent diagnoses & implements, opens PR, HUMAN APPROVES before merge.
```

**Research / experiment ticket (pre-registration):**
```markdown
---
title: "EXPERIMENT: <question>"
status: ready
type: research
approval_tier: L3
area: [ml]
horizon: next
timebox: 2d          # NOT an estimate — max time before we reassess
---
## Question
<the single question this answers>

## Hypothesis (pre-registered, before running)
<what you expect and why>

## Success metric & threshold (decided BEFORE seeing results)
<e.g. "out-of-sample Sharpe > X on held-out period; explainable feature importances">

## Falsification condition
<what result would make us abandon this idea>

## Method
<data, splits, model, what varies>

## Out of scope
<what we are NOT testing>

## Deliverable
A decision + an ADR (docs/adr/NNNN-*.md). NO production code from this ticket.

## Approval tier
L3 — diagnosis/analysis only; explicit human approval before any pipeline/model change ships.
```

**ADR (Nygard):**
```markdown
# ADR-00NN: <verb-first decision>
Date: 2026-08-23
Status: Accepted   # Proposed | Accepted | Superseded by ADR-00MM
Owner: <you>

## Context
<forces, constraints, what prompted this; for research, link the experiment ticket>

## Decision
<the choice, one paragraph>

## Consequences
<what gets easier, what gets harder, what we accept>
```

### E. Integration with your existing conventions
- **CLAUDE.md = your constitution.** Add a short section pointing agents at Backlog.md (`backlog task <id> --plain` to read a ticket), the ticket schema, the label taxonomy, and the L1/L2/L3 rules.
- **PROJECT_STATUS.md** stays canonical for the roadmap; tickets link up to milestones; `backlog board export project-status-board.md` can generate a snapshot.
- **Discovery waves** become read-only audit sub-agents that (a) verify schema references against the committed schema before any data-infra ticket, and (b) triage the inbox. **Wave-gates** map onto the `in-review → done` transition and the L2/L3 human-approval gate.
- **L1/L2/L3** becomes a required `approval_tier` field on every ticket, so the agent knows its autonomy level from the ticket itself: L1 (trivial lint/format within line-count + protected-path guards) may auto-fix/auto-merge; L2 implements + opens PR + waits for you; L3 (ML pipeline, migrations, auth, security) diagnosis-only until you approve.
- **Conventional commits** feed **release-please** for an automated CHANGELOG + version Release PR you merge on your schedule.

### F. Prioritization method for a single-user product
Drop RICE/WSJF (Reach is meaningless with one user; the scores are false precision). Use two moves:
1. **Value/effort gut-call** on a 2×2 when triaging into Now/Next — "how much does this improve *my* ability to trust/act on asxos vs. how much time."
2. **Appetite + circuit breaker** (Shape Up) for anything sizeable: decide the time it's *worth* up front; if it blows the timebox, stop and re-shape rather than sink more time. For research, the timebox IS the circuit breaker.

### G. Weekly / monthly operating cadence (concrete)
- **Daily (2–5 min)**: open the Backlog.md board; confirm the *one* "in-progress" task; if an agent PR is waiting, review it against acceptance criteria + approval tier.
- **Weekly (~20 min, e.g. Monday)**: update "Now" in PROJECT_STATUS.md; pull 1–3 tickets from Next→Now and mark them `ready` (they must pass Definition of Ready); run/queue a discovery-wave schema audit before any data-infra work.
- **Monthly (~45 min)**: review "Next"; write/close ADRs for decisions made; prune the backlog (close anything untouched a quarter — "important ideas come back"); scan tech-debt label.
- **Quarterly (~1–2 hr)**: reshape "Later"; declare backlog bankruptcy if it's bloated; retro on which experiments paid off; review whether the process itself is still earning its keep.

### H. What NOT to adopt (process theatre for a solo operator)
- **Story points and velocity** — no team to calibrate against; use calendar milestones + timeboxes, which you already do.
- **Sprints as ceremony / sprint planning meetings / retros-with-yourself as ritual** — keep the lightweight cadence above instead.
- **RICE/ICE/WSJF scoring spreadsheets** — false precision for N=1; the inputs are guesses.
- **Backlog grooming meetings** and a large maintained backlog — keep the backlog short and prune; Shape Up's "no backlog" is closer to right for you.
- **MADR / heavyweight ADRs, PRD documents, and full Spec Kit ceremony on every ticket** — reserve full specs for L3 work; small tickets don't need a constitution each.
- **Multi-tool setups** (Jira + Confluence + a separate roadmap tool) — one in-repo system + a thin GitHub inbox.
- **Fully autonomous agent merging beyond L1** — the slop/METR/Kiro-outage evidence says keep L2/L3 human gates; do not let agents auto-open dozens of tickets without a Definition-of-Ready gate.

## Recommendations — staged implementation (avoid the big-bang rollout that dies in week 3)

**Stage 0 (30 min): restructure the roadmap you already have.** Reformat PROJECT_STATUS.md into Now/Next/Later with appetites. No new tools. This alone captures most of the value and can't fail.

**Stage 1 (1 hr): install Backlog.md, migrate only "Now."** `npm i -g backlog.md`, `backlog init`, wire the MCP server into Claude Code, and create tickets *only* for the 1–3 things in "Now." Do not back-fill history. Add the three templates to the repo.

**Stage 2 (1 hr): update CLAUDE.md.** Add the ticket schema, label taxonomy, the `approval_tier` field, and the instruction to read tickets via `backlog task <id> --plain`. Point one discovery-wave sub-agent at "verify schema references before data-infra tickets."

**Stage 3 (30 min): add the schema-drift CI guard.** Migration-first rule + regenerate-and-diff check in GitHub Actions. This directly attacks your documented top failure mode and pays for itself immediately.

**Stage 4 (30 min): add release-please.** Automated CHANGELOG + Release PR from your existing conventional commits.

**Stage 5 (ongoing, opt-in): only if you feel the need** — add GitHub Issues as a phone inbox and/or the @claude Actions loop for L1/L2 tickets. Add ADRs the first time you make an L3 decision, not before.

**Benchmarks that would change the plan**: if you ever add a second contributor or real external users, revisit Linear (notifications, assignment, collaboration) and consider promoting GitHub Issues to primary. If agent-opened tickets start creating noise, tighten the Definition-of-Ready gate before anything else. If experiments start piling up untracked, formalize the separate experiment backlog with its own board view.

## Caveats
- **AI-agent workflow advice is young and partly unproven.** The strongest empirical signals (METR's 19% slowdown RCT on early-2025 tools, SlopCodeBench, GitClear's churn/duplication data, CodeRabbit's ~1.7× defect finding) are cautionary; treat "agents make you faster" as unproven for your context and measure it yourself (METR's own Feb 2026 follow-up shows the gap is narrowing for newer tools). Your instinct to keep human gates is well-supported.
- **Backlog.md is a young project** (~6.5k stars, fast-moving, one lead maintainer) with a known worktree-write limitation; it's the best fit but carries small-project risk — mitigated because everything is plain markdown you fully own and can migrate.
- **Tool pricing and MCP details move fast** and several figures here are 2026 snapshots; the mcp-atlassian CVEs and Notion MCP prompt-injection issues are a reminder that PM MCP servers are an active attack surface — prefer local CLI/in-repo over remote MCP where you can.
- **Prioritization-framework critiques cut both ways**: dropping RICE is right for N=1, but if asxos ever gets real users, structured scoring becomes worth the overhead again.
- **The single biggest risk to this whole system is the same one every source names: process that doesn't pay for itself gets abandoned.** The staged rollout and the "what not to adopt" list exist specifically to keep the system smaller than your discipline can sustain.