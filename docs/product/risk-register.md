# arbi risk register — known risks arbi tracks and surfaces

**Status:** current
**Scope:** the standing risks arbi carries into every brief until they're closed
**Last verified:** 2026-07-10
**Owner:** arbi maintains (Tier 2, command-invoked); James owns the risk appetite
**Superseded by:** N/A

The durable risk list arbi surfaces (BLOCKERS / NEW BUGS-RISKS) and updates as risks open or
close. James owns the risk *appetite*; arbi owns *keeping the list honest and visible*.
Severity: **P0** (blocks real capital / foundation) · **P1** (blocks a phase) · **P2**
(quality/latent). Append/adjust rows; never silently drop a risk — close it with a dated note.

---

## Register

| ID | Risk | Sev | Status | Mitigation / next step | Source |
|---|---|---|---|---|---|
| R1 | **Model A horizon mismatch** — signal edge may collapse in <5d and reverse by 21d, vs multi-month holding | **P0** | open | Run the decay check; do not act on Model A for real capital (rule #11) | `session-handoff-2026-07-04.md` |
| R2 | **Agent DB role scoping** — agents' SELECT-only is prompt-enforced only; an injected agent could emit writes | P1 | open | Read-only Postgres role for agent MCP sessions (`m14_candidate_agent_db_role_scoping`) before Phase 2c | `portfolio-conventions.md`, `next-session-backlog.md:256` |
| R3 | **Allocator risk-blindness** — v1 allocator ignores ASX beta clustering; 30% sector cap ≠ diversification | P2 | open (accepted v1) | Market-beta cap `m14_candidate_beta_cap` (v2); cash floor + leverage cap are the only v1 protections | `portfolio-conventions.md:200-206` |
| R4 | **Dark-launched-≠-released** — M13/M14a are built but gated off; "built" can read as "live" | P2 | open | Track gate status in `roadmap-state.md`; don't count dark-launched work as delivered | V2 arch audit Part A |
| R5 | **Prompt-only enforcement** — every arbi boundary/tier is prompt+doc enforced today, not mechanical | P1 | open | Managed Agents permission policies + read-only DB role; treat Tiers 5–7 as disabled until then | `arbi-permission-model.md` |
| R6 | **Reward hacking** — a naive self-improvement metric degrades arbi silently | P1 | mitigated-by-design | Multi-objective hard-gated scorecard + external grader + promotion gate | `arbi-scorecard.md`, `arbi-promotion-gate.md` |
| R7 | **Memory poisoning** — untrusted input written to a read-write store, later read as trusted | P1 | mitigated-by-design | Read-only authority stores; arbi never writes what it reads as authority | `arbi-memory-policy.md` |

## How arbi uses it

- **Surface the open P0/P1 rows every brief** — R1 (Model A) leads BLOCKERS until closed.
- **Close with a note, don't delete.** When a risk clears (e.g. rule #11 lifts → R1 closed),
  set status `closed <date>` and record how; keep the row for audit.
- **New risks land here first**, then get referenced from `roadmap-state.md` — this is the
  canonical risk list.
