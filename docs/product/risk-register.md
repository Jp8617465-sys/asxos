# arbi risk register — known risks arbi tracks and surfaces

**Status:** current
**Scope:** the standing risks arbi carries into every brief until they're closed
**Last verified:** 2026-07-10
**Owner:** arbi maintains (I2, command-invoked); James owns the risk appetite
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
| R5 | **Prompt-only enforcement** — every arbi boundary/tier is prompt+doc enforced today, not mechanical | P1 | partial (`unattended-guard.sh` pre-filters I5–I6 unattended) | Managed Agents permission policies + read-only DB role; treat I5–I6 / P5–P6 as disabled until then; P6 (execution) is already enforced by no execution tool ever being mounted | `arbi-permission-model.md` |
| R6 | **Reward hacking** — a naive self-improvement metric degrades arbi silently | P1 | mitigated-by-design | Multi-objective hard-gated scorecard + external grader + promotion gate | `arbi-scorecard.md`, `arbi-promotion-gate.md` |
| R7 | **Memory poisoning** — untrusted input written to a read-write store, later read as trusted | P1 | mitigated-by-design | Read-only authority stores; arbi never writes what it reads as authority | `arbi-memory-policy.md` |
| R8 | **Behavioral-only Model A quarantine** — nothing in code/DB enforces rule #11; migration 0032 grandfathered `model_a` to `approved_for_allocation=TRUE`, and that gate verifies *approval, not reliability*, so `build()` would pass Model A to the allocator if invoked with `ASXOS_PERSONAL_USE=1` | P1 | contained | Allocator surface is dark (`ASXOS_PORTFOLIO_BRIEF_ENABLED=0`) + not invoked. Do NOT rely on the approval gate as the quarantine — see R9 before revoking approval | scan `wf_f54323f5-d7d`; `build.py:205-219`, migration 0032 |
| R9 | **Brief hard-couples to model approval** — V1 `collect()` (`compose.py:190`) + V2 `active_theses` collector call `resolve_production_model()` unconditionally (RuntimeError on 0 approved); revoking approval to harden the quarantine would hard-fail the whole brief / hide every thesis card — the Model-A-*independent* discipline layer | P1 | **fixed 2026-07-10** | DONE: `resolve_production_model()` gained `required=False`; both brief sites best-effort (skip Model A reads on 0/>1 approved), allocator keeps `required=True` hard-fail. Revoking approval now hardens the quarantine without hiding thesis cards. Tests: `test_production_gate.py` + flipped brief tests | scan `wf_f54323f5-d7d`; `production_gate.py`, `compose.py:190`, `active_theses.py` |
| R10 | **`cost_base_normal` currency is ambiguous** — it stores the **AUD tax base** for foreign holdings (HUBS.NYSE: 6978.23 AUD = 24 × US$187.54 ÷ 0.6450 acq-FX), but nothing in the column signals that. In the 2026-07-11 `/pm-review`, **2 of 5 analysis agents** (milestone, benchmark) read it as a USD cost total (÷24 = US$290.76) and reported HUBS **−29% / stop-violated / −28pp vs XJO** — all false; the position is ≈ flat (+9.8% USD). A single-agent review would have shipped that error into a capital-relevant memo. The acquisition FX (0.6450) is **confirmed** against the brokerage statement (James, 2026-07-11) — an ESPP fill FX differing from spot is expected, not an error — so the remaining issue is purely the column's currency **labeling**, not the number | **P1** | open | Make the currency explicit: a `cost_base_ccy` marker or split `cost_base_aud`/`_usd`; until then any consumer mixing `holding_lots` (native) with `portfolio_daily_snapshots` (AUD) must FX-convert. See cleanup-backlog RC1 | `/pm-review` 2026-07-11; agents milestone/benchmark/coherence; `holding_lots` id=1, thesis_revision #13 |
| R11 | **`conviction_level` is NULL on all 13 theses** — the size-vs-conviction discipline check (`portfolio-coherence-reviewer`) cannot run for *any* position, including the one name that is 100% of capital. A whole discipline dimension is unpopulated, so conviction→exposure coherence is uncheckable portfolio-wide | P2 | open | Backfill conviction on live theses; consider requiring it on `enter_thesis()`. See cleanup-backlog RC4 | `/pm-review` 2026-07-11; `portfolio-coherence-reviewer`; `theses.conviction_level` |

## How arbi uses it

- **Surface the open P0/P1 rows every brief** — R1 (Model A) leads BLOCKERS until closed.
- **Close with a note, don't delete.** When a risk clears (e.g. rule #11 lifts → R1 closed),
  set status `closed <date>` and record how; keep the row for audit.
- **New risks land here first**, then get referenced from `roadmap-state.md` — this is the
  canonical risk list.
