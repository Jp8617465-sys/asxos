# arbi permission model — the blast-radius ladder

**Status:** current
**Scope:** the authoritative permission model for arbi (the `arbi-harness.md` tier table
points here)
**Last verified:** 2026-07-10
**Owner:** James (governor); changing a grant is a boundary change (constitution §reserved)
**Superseded by:** N/A

The organising principle is **reversible vs irreversible**, not "autonomous vs not." arbi
is granted broad standing autonomy for reversible work and is review-gated for everything
irreversible. This file is the source of truth for what arbi may do at each tier; the
`arbi-scorecard.md` circuit breakers are the hard floor beneath it.

---

## The tier ladder

| Tier | Capability | Reversible? | Standing autonomy | Runtime enforcement (target) |
|---|---|---|---|---|
| 0 | Read repo / docs / live-state snapshot | yes | **Yes** | `always_allow` (read-only tools) |
| 1 | Summarise / prioritise / detect drift / draft NEXT PROMPT + PR summaries | yes | **Yes** | `always_allow` |
| 2 | Write docs (roadmap-state, handoffs, ledgers, README links) | yes (git-revertible) | **command-invoked only today** | `always_allow` on a docs-scoped write tool |
| 3 | Open a **docs-only draft** PR (branch + commit docs + classify) | yes | not granted yet | `always_ask` → `always_allow` when promoted |
| 4 | Dispatch NEXT PROMPT to a specialist (who produces a **draft** code PR) | yes (draft) | not granted yet | multi-agent delegation, `always_ask` |
| 5 | Migrations / DB writes / Render / secrets | **no** | **never standing** | `always_ask` (or disabled) — James approves each |
| 6 | Merge / deploy / push to `main` / CI changes | **no** | **never standing** | `always_ask` — James approves each |
| 7 | Capital action / trading / portfolio change | **no** | **Never** | **disabled** — not a tool arbi holds |

The **Reversible?** column is the real gate. Tiers 0–4 are reversible (docs are
git-revertible; PRs are draft; dispatched code is draft) → eligible for standing autonomy
once earned. Tiers 5–7 are irreversible or capital-impacting → always human-approved, never
standing, regardless of track record.

## Where arbi stands today

- **Standing autonomy:** Tiers 0–1 (read + think + draft).
- **Tier 2 (docs write):** performed **only inside an explicitly invoked command** (`/arbi`
  refreshing state, `/arbi-close` writing a handoff) — human-in-the-loop, James ran it — not
  unattended standing autonomy. The subagent itself is `Read, Glob, Grep` only.
- **Tiers 3–7:** not granted.

Promotion to *standing* Tier 2/3 (and later Tier 4 dispatch) requires the preconditions
below and an explicit James decision. **Tiers 5–7 are never promoted to standing** — they
are permanently `always_ask`/disabled by design.

## Promotion preconditions (Tier ≤4 only)

Before arbi earns standing autonomy at a higher reversible tier, all must hold:

1. **Model A dispute resolved** — CLAUDE.md rule #11 lifted (you cannot autonomously operate
   a project whose core engine is under dispute).
2. **Agent DB role scoping landed** (`m14_candidate_agent_db_role_scoping`) — a read-only
   Postgres role so an unattended agent physically cannot write.
3. **Track record** — the `arbi-scorecard.md` trend + `arbi-run-ledger.md` + eval suite show
   arbi's calls hold up (no Safety fails, no state-accuracy regression) over a sustained
   window.

## Circuit breakers (hard floor, always on)

Independent of tier, any of these **voids the run** (`arbi-scorecard.md` Layer 1) and pauses
arbi: unapproved DB write / migration / Render change / merge / deploy; secret exposure;
branch-only state treated as `main` truth; capital-impacting action; a Model A-derived
capital recommendation while quarantined; self-editing the constitution or a boundary
without review; presenting an unsourced claim as current truth. These are not metrics — they
are the floor beneath the ladder.

## Runtime enforcement honesty

Today every grant here is **prompt + doc enforced** — arbi is instructed to obey it; nothing
mechanically stops a mis-scoped tool call (the same limitation the security-engineer flagged
for agent DB access). On the Managed Agents platform these map to real **permission policies**
(`always_allow` / `always_ask`) and disabled toolsets, and Tier 7 tools simply are not
mounted. Until that lands, the harness + this doc are the enforcement, and Tiers 5–7 must be
treated as if disabled.
