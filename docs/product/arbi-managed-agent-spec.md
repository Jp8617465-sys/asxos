# arbi — Managed Agents deployment spec

**Status:** current (design spec — NOT yet provisioned)
**Scope:** how to stand arbi up as an Anthropic **Managed Agent** so the governance docs
become live config, not prose
**Last verified:** 2026-07-10 (against the Managed Agents beta, `managed-agents-2026-04-01`)
**Owner:** James provisions on the Claude Developer Platform; arbi may draft changes only
**Superseded by:** N/A

This is the blueprint for PR 7b→8 (standing/unattended arbi). **It cannot be provisioned
from the asxos repo** — Managed Agents is a separate hosted platform (Claude Developer
Platform / API, beta header `managed-agents-2026-04-01`, needs an API key). This doc is the
config you (or arbi-with-platform-access) apply there. Every boundary below is the *same*
one already written in the governance set — this just maps it onto the platform's real
enforcement primitives (`always_allow`/`always_ask`/disabled, read-only memory stores,
scheduled deployments), which is the upgrade from today's prompt-only enforcement (risk R5).

Do **not** flip standing autonomy on until the three preconditions clear (Model A resolved ·
agent DB read-only role landed · scorecard/eval track record — `arbi-permission-model.md`).

---

## 1. Agent (the model + prompt + tools)

- **Model:** the current top Claude model (Opus-tier) for planning/synthesis; specialists may
  use a cheaper tier per `/arbi-run`'s roster.
- **System prompt:** `.claude/agents/arbi.md` verbatim + a pointer to read the governance set
  (`arbi-constitution.md`, `arbi-authority.md`, `arbi-permission-model.md`, `arbi-scorecard.md`)
  on session start.
- **Tools** (start minimal, widen only by tier):
  | Tool | Grant |
  |---|---|
  | File read (Read/Glob/Grep) | `always_allow` |
  | Web search / fetch | `always_allow` |
  | File write/edit | `always_ask` → `always_allow` only for `docs/**` after I2 promotion |
  | Bash | `always_ask` (read-only git/pytest ok; anything mutating asks) |
  | GitHub MCP (PR/branch) | `always_ask`; **merge/deploy disabled** |
  | Supabase MCP | **read-only role only** (see §5 precondition); `always_ask` |
- **Skills:** `/arbi`, `/arbi-close`, `/arbi-run` port as-is.

## 2. Environment (where it runs)

- **Anthropic-managed cloud sandbox** (default) — the asxos GitHub repo attached as a
  resource (cloned into the sandbox, PRs pushed back), same model as Claude Code on the web.
  Self-hosted sandbox is the alternative if data-residency ever requires it.
- Repo is the evidence source (authority ladder levels 3–4); the sandbox is disposable.

## 3. Sessions & events

- On-demand (a user event) or scheduled (§6). Stateful: filesystem + event history persist
  server-side and resume cleanly. `/arbi` and `/arbi-run` are the entry events.

## 4. Multi-agent topology (PR 8)

arbi is the **coordinator**; specialists run as context-isolated sub-agents (each its own
model/prompt/tools), matching the `/arbi-run` roster:

```
arbi (coordinator)
├── backend-architect        schema / API / write-path / DB design
├── security-engineer        secrets / permissions / tool blast radius
├── refactoring-expert       behaviour-preserving code cleanup (mutates code)
├── technical-writer         docs / handoffs (mutates docs)
├── system-architect         module boundaries / structural change
├── tax-spec-conformance     tax spec↔test↔code
├── portfolio-invariant-guard  portfolio invariants
└── (5) investment-analysis  live-portfolio evidence
```

arbi decides *what/who/success/must-not-touch*; the platform's multi-agent session executes
the fan-out. Irreversible results still climb the tier gate (§5) for James.

## 5. Permission policies (the real enforcement)

Map `arbi-permission-model.md`'s **Infrastructure ladder (I0–I6)** and **Portfolio ladder
(P0–P6)** onto platform toolset policies:

| Tier | Capability | Policy |
|---|---|---|
| I0–I1 | read / think / draft | `always_allow` |
| I2 | write `docs/**` | `always_allow` **after** standing-I2 promotion; else `always_ask` |
| I3 | docs-only draft PR | `always_ask` → `always_allow` when promoted |
| I4 | dispatch specialist / draft code PR | `always_ask` |
| I5 | migration / DB write / Render / secrets | `always_ask` (or tool **disabled**) |
| I6 | merge / deploy / push `main` / CI | `always_ask` |
| P0–P1 | read portfolio state / analyse (`/pm-review` fan-out) | `always_allow` |
| P2 | single-position action memo | `always_allow` **after** standing-P2 promotion; else `always_ask` |
| P3–P4 | allocation proposal / log + track memo | `always_ask` → `always_allow` when promoted |
| P5 | propose a capital-policy change | `always_ask` (**draft only**, never standing) |
| P6 | execute / place order / move capital | **tool not mounted** |

The **9 circuit breakers** (`arbi-scorecard.md`) remain the hard floor. The **Supabase MCP
grant must be a read-only Postgres role** (`m14_candidate_agent_db_role_scoping`) before any
standing DB access — this is the mechanical fix for R2/R5, and a hard precondition.

## 6. Scheduled deployments (cron)

| Schedule (UTC) | Session | Tier |
|---|---|---|
| daily 20:30 (06:30 AEST) | `/arbi` morning brief | **7a read-only** today; 7b writes after preconditions |
| daily 02:00 | PR / CI / blocker check | 7a read-only |
| weekly | roadmap-state reconciliation | 7b (gated) |
| weekly (Sun) | **dream** over the week's sessions → candidate memory | dream (research preview — request access) |
| monthly | promote/reject dream memory vs holdout evals | promotion gate (`arbi-promotion-gate.md`) |

Today the daily brief already runs as a Claude Code **Routine** (PR 7a, `trig_01PiLVYg…`) —
no API bill. Move it to a Managed Agents scheduled deployment only when you want the memory +
dream + multi-agent features that Routines don't provide.

## 7. Memory stores

Provision the 5 stores from `arbi-memory-policy.md` with the read-only/read-write split —
**never one shared read-write blob** (poisoning defence, R7):

`asxos-authority-memory` (RO) · `asxos-project-memory` (RO) · `asxos-arbi-working-memory` (RW)
· `asxos-dream-candidate-memory` (RO after gen) · `asxos-approved-learning-memory` (RO in runs).

## 8. Outcomes (the grader loop)

Register the `docs/product/rubrics/*` as **outcomes**: each defines "done" + a rubric graded
in a **separate context**, feeding results back so arbi iterates. Fixtures in
`docs/product/evals/` are the holdout set the promotion gate runs against.

## 9. Cost (plan for it)

Usage-billed to your **API account**, not a chat subscription. Two dimensions: **standard
token rates** + **$0.08 per session-hour** (only while running); no flat/per-agent fee.
Driver is tokens × cadence × fan-out — the daily brief is pennies; a heavy multi-agent
orchestration (like the 2026-07-10 scan, ~705k tokens) is low-single-digit-plus dollars.
Prompt caching materially reduces it. See `platform.claude.com` pricing for current rates.

## 10. Governance-doc → platform-feature map

| Governance doc | Configures |
|---|---|
| `arbi-constitution.md` / `.claude/agents/arbi.md` | the Agent (system prompt, authority) |
| `arbi-authority.md` | conflict-resolution prompt; repo/live as evidence source |
| `arbi-permission-model.md` | permission policies (§5) |
| `arbi-scorecard.md` + `rubrics/` + `evals/` | outcomes graders (§8) |
| `arbi-promotion-gate.md` | the promote step (monthly, §6) |
| `arbi-memory-policy.md` | memory stores (§7) |
| `arbi-dream-policy.md` | dream deployment (§6, research preview) |
| `arbi-run-ledger.md` / `decision-log.md` | run records (event history + the ledgers) |
| this spec | the Agent + Environment + scheduled deployments |

## 11. Provisioning checklist (when preconditions clear)

1. [ ] API key + `managed-agents-2026-04-01` beta header; request Dreams access.
2. [ ] Land the **read-only Postgres role** for the Supabase MCP grant (§5 precondition).
3. [ ] Resolve the **Model A** dispute (decay check) — precondition #1.
4. [ ] Create the Agent (§1) + cloud Environment (§2) + attach the repo.
5. [ ] Provision the 5 memory stores (§7).
6. [ ] Register rubrics as outcomes (§8).
7. [ ] Start with the **read-only 7a** scheduled brief; verify against the Routine's output.
8. [ ] Only after a scorecard/eval track record: promote standing I2/I3, then wire 7b + PR 8.
