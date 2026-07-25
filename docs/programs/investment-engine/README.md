# Investment Engine Programme

**Status:** accepted bootstrap dossier; implementation remains unbuilt until sprint PRs merge
**Owner:** James (governor); Arbi maintains programme state
**Base:** refresh `current-state.md` and `docs/product/roadmap.yaml` before each mission

This directory is the durable implementation contract for ASXOS's twelve-sprint,
model-independent investment engine programme. It turns the accepted product decisions into
schemas, fixtures, sprint work orders, tests, and operating gates that a fresh Claude session can
execute without access to the planning conversation.

The programme builds an institutional-style, single-user decision engine. It does not connect to a
broker, execute an order, distribute advice to another person, or use Model A in a capital-relevant
path.

## Read order for Claude

1. Repository [`CLAUDE.md`](../../../CLAUDE.md), especially non-negotiable rules 4, 5, 8, and 11.
2. [`decisions.md`](decisions.md) for governor-ratified product choices and any
   explicitly marked recommendation still awaiting James.
3. [`model-a-decommission.md`](model-a-decommission.md) for the recommended
   runtime-off/evidence-retention target and its separate James approval gate.
4. [`current-state.md`](current-state.md) for the pinned repository truth and reuse/retire map.
5. [`architecture.md`](architecture.md) and the referenced contract document for the active sprint.
6. Canonical [`roadmap.yaml`](../../product/roadmap.yaml).
7. Exactly one file under [`sprints/`](sprints/).
8. [`acceptance-matrix.md`](acceptance-matrix.md), the relevant schemas, and fixtures.
9. [`operations-and-rollout.md`](operations-and-rollout.md) before any migration, scheduled job,
   capital-adjacent state change, or release.

Do not load all sprint files into an implementation prompt. The roadmap identifies the active
initiative; the sprint file links only the contracts and fixtures needed for that outcome.

## Source-of-truth precedence

When documents disagree:

1. `CLAUDE.md`, the tax specification, and ratified authority documents win.
2. A versioned JSON Schema wins over explanatory examples.
3. Live repository and migration truth wins over `current-state.md`.
4. The canonical roadmap wins over generated views, handoffs, and issue mirrors.
5. The active sprint work order wins over historical proposals.

Stop with `DOSSIER_DRIFT` when a conflict affects scope, financial meaning, authority, or data
integrity. Repair the dossier in a separate reviewed change; do not silently choose a convenient
interpretation.

## North star

The programme improves three measured outcomes:

- **Capital Under Discipline:** invested NAV backed by a current, approved, evidence-complete,
  independently reviewed, monitored, policy-compliant thesis with no overdue critical finding,
  divided by total invested NAV.
- **Material-event latency:** P95 time from an observable material event to a surfaced alert,
  targeted below one complete trading session.
- **Prospective investment result:** after-tax, after-cost active return versus genuine XJO total
  return, always shown with drawdown, sample size, and the hold/no-action counterfactual.

These remain separate measurements. No generic weighted score may substitute for them.

## Programme boundaries

- James is the only user, policy governor, order approver, and external executor.
- AI drafts and challenges research and may express qualitative intent.
  Deterministic code validates, constructs targets, accounts, evaluates risk,
  sizes, stages, and enforces gates.
- Model A is targeted for complete runtime/product/evidence-path decommission
  under a separate James-approved mission. Its checksummed historical evidence
  remains read-only; capital contracts reject Model A fields.
- V1 capital output is long-only XASX/AUD; foreign theses remain research-only.
- Target weights use a transparent James-ratified loss-at-risk budget, never a
  generic weighted score, predicted return, Model A rank, or LLM-authored number.
- Database-bound monetary/statistical values use canonical six-place Decimal
  strings in JSON and `NUMERIC(18,6)` in Postgres.
- A staged order is an expiring proposal. Approval changes audit state only.
- Construction, risk, sizing, and staging fail closed until James ratifies every
  required policy and case-specific loss anchor.
- The twelve-week build ends hidden and `PAPER_ONLY`. Operationally uncalibrated
  staging requires 30 clean prospective sessions after the full lineage freezes.
- An evidence-backed edge claim requires 252 prospective sessions and 20 matured 63-session
  pre-registered episodes; origins may overlap and carry dependency groups.

## Running a mission

Start from [`prompts/sprint-start.md`](prompts/sprint-start.md) using
[`mission-template.yaml`](mission-template.yaml). Use the eight-hour recipe for a bounded vertical
slice and the twelve-hour recipe for a cross-layer capability. Close with
[`prompts/sprint-close.md`](prompts/sprint-close.md).

The builder never self-grades. A fresh-context reviewer checks the frozen diff and evidence packet
before a sprint can be marked shipped.

## Validation

Run:

```bash
.venv/bin/python scripts/validate_investment_program.py
.venv/bin/python -m pytest tests/test_investment_program_dossier.py -q
```

The environment must resolve Python 3.12. System Python 3.9 is unsupported.

The bootstrap dossier contains specifications and synthetic fixtures only. It
does not implement product runtime, change production data, apply migrations,
schedule jobs, deploy, or enable tailored output. Product acceptance tests that
import unbuilt code are added in the sprint that implements that code.
