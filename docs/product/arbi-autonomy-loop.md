# arbi autonomy loop — the self-driving cycle (git-native)

**Status:** current (machinery built; **standing activation gated — see §Activation**)
**Scope:** how arbi runs the observe→decide→act→learn loop on a schedule, in Claude Code
**Last verified:** 2026-07-10
**Owner:** James enables standing autonomy; arbi runs within the guardrails
**Superseded by:** N/A

The hourly/daily loop you asked for — built on **Claude Code Routines + git + GitHub**, no
Managed Agents required. Managed Agents is an optional hosted backend, not a prerequisite
(`arbi-managed-agent-spec.md` is the map for that later option).

---

## The cycle

```
Routine fires (ARBI_UNATTENDED=1)                         ← scheduler (Claude Code Routine)
  → /arbi            observe live state, decide THE ONE THING          (I0-I1)
  → /arbi-run        dispatch the named specialists in parallel        (I4, reversible)
  → implement        on a claude/** branch                            (I2-I3)
  → test             make check / targeted pytest + ruff(0.7.0) + mypy
  → review loop      security-engineer / refactoring-expert / technical-writer
  → open a PR        CI runs; report to James                          (I3, draft)
  → STOP at merge    ← James merges (I6 = prod deploy)                 ← THE HUMAN GATE
  → /arbi-close      append run-ledger + decision-log + working memory (I2)
weekly:  /arbi-dream    consolidate → dream-candidate PR
monthly: /arbi-promote  candidate → approved-lessons (James merges)
```

The loop drives itself to a **green PR** and stops. It does not merge — merge = prod deploy,
reserved to James (I6). It learns every cycle (the ledgers) and consolidates weekly
(the dream), so it stops repeating mistakes.

## What makes an unattended run SAFE (three mechanical layers)

Not prompt-hope — mechanical, defense-in-depth:

1. **`unattended-guard.sh`** (`.claude/hooks/`, armed by `ARBI_UNATTENDED=1`): a PreToolUse
   hook that DENIES push/merge to `main`, force-push, RW-DB SQL, migrations, Render
   mutations, PR merges, secret reads, and edits to authority/boundary files. Attended
   sessions: total no-op. (Verified 13/13 cases 2026-07-10.)
2. **GitHub branch protection on `main`** (the real merge/deploy backstop — server-side,
   unbypassable from a session): require PR + `full-check` green + CODEOWNERS approval; no
   direct pushes; arbi's identity cannot self-approve. *Config step for James/backend-architect.*
3. **R2 read-only Postgres role** for agent MCP sessions (`m14_candidate_agent_db_role_scoping`):
   the real DB-write backstop. *Not yet landed — the guard is the interim.*

The hook reduces risk **R5** (prompt-only enforcement) from total to partial; (2) and (3)
are what actually bound the irreversible tiers. See `arbi-permission-model.md §Runtime
enforcement honesty` — the infra **I5–I6** and portfolio **P5–P6** tiers stay
treated-as-disabled until (2)+(3) land (P6 execution is already enforced by no execution
tool being mounted).

## Activation — NOT on by default

Standing unattended autonomy (the loop writing/dispatching on a schedule) is **PR 7b/8**,
gated. Turn it on only when ALL hold:

1. **Model A dispute resolved** (or explicitly accepted) — decay first-pass says *keep the
   quarantine* (`docs/model-a-decay-analysis-2026-07-10.md`); the loop must not act on Model
   A for capital regardless.
2. **Branch protection** configured on `main` (layer 2 above).
3. **R2 read-only DB role** landed (layer 3 above).
4. **Track record** — several attended cycles logged in the run-ledger with clean scorecards.
5. **James's explicit enable.**

Until then: **run it attended** — you invoke `/arbi` → `/arbi-run` → review → PR, exactly
as this session did (the loop's inner cycle, run by hand). That already works today.

## The Routine (ready to enable — do NOT enable before the gate)

A daily/weekly Claude Code Routine (`create_trigger`) firing a fresh session whose prompt:
sets the loop, runs `/arbi` → (if a clear reversible #1) `/arbi-run` → implement on a branch
→ test → review → open a **draft** PR → report; **never merges**. The session env carries
`ARBI_UNATTENDED=1` so the guard is armed. Cadence suggestion: a **weekly `/arbi-dream`**
first (lowest-risk write — candidate on a branch), then a daily build-loop once the gate
clears. PR 7a (the read-only morning brief) is already live (`trig_01PiLVYg…`).

## Cost

Runs under this environment's Claude Code plan — **no separate API bill** (unlike Managed
Agents' metered usage). Cost is model tokens per cycle: a brief is cents; a full build-loop
cycle with fan-out is more. Cap cadence to control spend.
