# Codex external audit — reconciliation against repo truth (2026-07-27)

**Status:** current · PARKED awaiting the source artifact (~2026-08-01)
**Scope:** verification of an external (Codex) audit's claims about asxos against the actual
code at `9d442de`. Not a proposal — a fact-check to make the pending dossier safe to act on.
**Last verified:** 2026-07-27 (repo @ `9d442de`, clean tree)
**Owner:** main loop (read-only session); arbi surfaces the two live items on wake
**Superseded by:** N/A — supersede once the dossier lands and is reconciled

---

## Why this file exists

An external Codex session audited asxos and produced an *"ASXOS Claude Implementation Dossier
and 12-Week Build Program"* (44 subagents). **Only the conversation reached this repo — the
dossier artifact itself did not**, and the Codex credits ran out before it could be retrieved.
James retrieves it ~2026-08-01.

The audit is directionally useful but was **already stale in at least one confirmed place**.
This file pins what is actually true at `9d442de` so the dossier can be *reconciled in minutes*
rather than re-audited — or worse, executed on stale premises.

**Read this before acting on any part of that dossier.**

---

## Claim-by-claim verification

| Claim | Verdict | Evidence at `9d442de` |
|---|---|---|
| `ThesisProposal` exists but its consumer always raises | **TRUE** | Schema `asxos/domain/theses/schemas.py:344`; hard-raise `asxos/domain/theses/service.py:792` + `asxos/domain/governance/agent_run_service.py:147` |
| Stale in-code comments claim the schema doesn't exist | **TRUE** | `agent_run_service.py:60-64` — *"'thesis' deliberately omitted — no ThesisProposal schema exists yet"* — false since PR #56 |
| `_KNOWN_AGENTS` holds only `macro-economist` | **FALSE** | `agent_run_service.py:54` — three agents since PR #67 (`macro-economist`, `sector-screener`, `theme-researcher`) |
| `ThesisProposal` is merely a schema | **UNDERSTATED** | It already enforces rule #11 structurally: `monitor_only` figures barred from basis sections (`schemas.py:332-341`) and from entry/stop/target (`schemas.py:380-390`) |
| `/pm-review` is coupled to Model A | **TRUE** | `.claude/commands/pm-review.md:27` (SHAP coherence as a fan-out question) and `:47` (`Model A BUY 0.68` worked example) |
| No review-scoring / idea-outcome persistence | **TRUE** | Zero repo-wide matches: `review_cycles`, `review_assessments`, `idea_score`, `idea_predictions`, `idea_outcomes` |
| Paper evaluator is thin | **TRUE** | `asxos/domain/portfolio/paper_trade.py:133` — trade-level P&L vs zero. No NAV, benchmark, costs, dividends, FX, partial fills |
| No sizer / order staging exists | **TRUE as code** | No `staged_order` / `broker_order` tables. But the *authority* for it is already drafted — see below |
| 8/12-hour recipes are unratified standing authorization | **PARTLY MOOT** | `docs/product/arbi-goal-recipes.md` already states *"James launches"* — attended-by-design, not standing. The concern that James didn't know they existed is still fair |

---

## Two findings the external audit missed

### 1. `1A` (advise + stage orders) is already drafted and unratified — actionable now

`docs/proposals/personal-advice-firewall-amendment-2026-07-18.md`, status
*"proposed — DRAFT for James's ratification."* It scopes **exactly** the grant James chose in
the Codex session (advise + stage orders, sizes from a model-independent sizer, James places
every order), and names the **model-independent sizer as its §4a build dependency**.

This is a **merge decision, not a build**, and it gates the sizer + staged-order lanes
downstream. **It does not depend on the dossier.** Ratifying before the dossier lands means it
arrives against an unblocked repo. Raised as a `james-inbox.md` row.

### 2. The audit's "Fix #1" is already arbi's own #2 ranked action

`docs/product/roadmap-state.md:231` — *"`instrument-selector` + wire
`create_thesis_from_agent_run` (Phase E), the last leg of the discovery chain."*
This is **convergence with the existing roadmap, not a new direction** — worth stating plainly
so the dossier doesn't get read as a competing plan.

---

## Corrections to my own earlier caveats

- **Migration 0041 IS applied.** `asxos/api/main.py:15` — `REQUIRED_MIGRATIONS = 95`, 0041
  applied 2026-07-24. The 07-24 handoff's "James still to apply 0041" item is **closed**.
- **`0040_thesis_report_sections.sql` already persists `ReportSection`**, so the broker-report
  render path is further along than the audit implied.

---

## On resume (~2026-08-01)

1. Read the dossier.
2. **Reconcile against the table above before executing any of it.** It was authored on a read
   already stale in at least one confirmed place, and will be ~10 days older by then.
3. Decide the firewall amendment **separately** — it does not depend on the dossier.

No code, schema, or config was changed in the session that produced this file.
