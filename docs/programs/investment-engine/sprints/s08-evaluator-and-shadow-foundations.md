# S08 — Evaluator configuration, origin registry, and shadow foundations

**Initiative:** EVAL-02
**Phase:** prospective-evidence infrastructure
**Weekly outcome:** the full evaluation protocol is pre-registered and the system
can durably represent an empty evaluator, an open/blocked origin and five identical
starting branches without look-ahead
**Maximum evidence tier:** `PAPER_ONLY`
**Acceptance rows:** AC-33–36
**Depends on:** S07 frozen construction/risk/sizing/staging bundle; S06 current
monitor watermark
**Unlocks:** causal paper orders/fills/ledger in S09

## Outcome and evidence ceiling

Create the persistent building blocks from which `paper-evaluator-v1` will later
derive a digest:

- `evaluation-policy-v1`;
- `evaluator-config-v1`;
- `dependency-isolation-evidence-v1`;
- `evaluation-origin-v1`;
- `portfolio-snapshot-v1`;
- continuous shadow-book/session identity; and
- five frozen branch identities.

S08–S12 development sessions are harness evidence, not operational-gate sessions.
The 30-session and 252-session clocks start only after the final production-shaped
S12 lineage is frozen and James authorises hidden observation.

## Protocol decisions frozen before an origin opens

The evaluator config pins exact IDs, semantic versions and hashes for:

- portfolio construction, risk, sizing and staging policies/kernels;
- report/review/monitor contract bundle;
- fill model (base and stress);
- accounting/tax/cost policy and James tax-profile version;
- security master, XASX trading calendar and timezone;
- price/quote/volume and corporate-action sources/revision policy;
- genuine XJO-TR benchmark source/series/revision policy;
- evaluator/origin/ledger/NAV/outcome/statistics contracts;
- feature/data manifest, code SHA and environment lock; and
- Model A structural/perturbation isolation test version.

An unresolved source licence/provider/series or semantic version blocks config
activation. “XJO-like”, adjusted-close proxy or latest-revised data is not enough.

## Origin and branch contract

Origins follow a pre-registered schedule. Each scheduled origin is retained with
one of:

```text
OPEN, BLOCKED, REJECTED, NO_ACTION, INVALID, MATURED, UNAVAILABLE
```

The origin freezes:

- schedule ID/origin ordinal/dependency group;
- knowledge cutoff and recommendation timestamp;
- investment-case lineage, proposal and sizing identities/hashes;
- complete starting holdings/lots/cash/reservations/external-flow policy;
- price/FX/benchmark/action/source manifest;
- primary horizon of 63 XASX sessions; and
- five branches: `PROPOSAL_BASE`, `PROPOSAL_STRESS`, `HOLD`, `XJO_TR`, `CASH`.

All five begin from an economically equivalent frozen state. Branch-specific
transformation occurs only through later versioned events. An evaluator with zero
origins and an origin with no matured outcome are valid records.

Chronology:

```text
published_at <= available_at <= retrieved_at <= knowledge_cutoff
knowledge_cutoff <= recommendation_at <= origin_opened_at
origin_opened_at < first_eligible_paper_fill_event
```

## Primary estimands

- **Portfolio skill:** continuous shadow-portfolio cash-flow-aware time-weighted
  return minus identical-flow genuine XJO-TR, after explicit estimated tax and
  costs. This is the primary inferential daily series.
- **Idea skill:** each pre-registered 63-session proposal branch versus its
  hold/no-action branch. This is breadth/diagnostic evidence.
- **Cash branch:** pinned eligible cash return/tax treatment, diagnostic only.

After-tax portfolio return versus gross XJO-TR is labelled a conservative hurdle,
not benchmark-neutral alpha. An investable after-tax/risk-matched diagnostic may be
reported but cannot replace the locked XJO-TR comparison.

## Episode dependence and statistics registration

Origins may overlap. Every origin receives an overlap/dependency group and remains
in counts. The evaluation policy freezes:

- origin schedule and rejected/no-action denominator treatment;
- daily primary statistic and episode diagnostic statistics;
- moving-block-bootstrap resampling unit, block-length rule, repetitions, seed,
  PRNG, interval estimator and one-sided 90% gate;
- effective-sample and overlapping-episode diagnostics;
- missing observation and delisting policy;
- candidate-family/pre-registration ID and all attempted version history;
- multiple-testing/selection-bias report and block-length/95% sensitivity outputs;
- economically meaningful hurdle reported separately from the locked `> 0` gate;
- gate predicate and reset semantics.

Changing any item creates a new evaluator lineage.

## Additive persistence

After live preflight, add immutable evaluation-policy/config, shadow-book/session,
origin, branch and input-manifest records. Enforce unique schedule ordinal, canonical
hashes, origin chronology, typed lineage and prospective/reconstructed status.
Reconstructed records use a separate mode and can never pass a gate.

## Mission decomposition

### Mission S08-A — provider and protocol freeze (12h, docs/contracts/tests PR)

- Resolve actual XJO-TR, price/volume, corporate-action and calendar providers,
  series identifiers, revision/availability semantics and licensing constraints.
- Freeze estimands, origins, branches, denominators, overlap treatment, bootstrap
  and candidate-family rules with Opus/Ultra.
- Build empty/open/blocked/rejected/future-data/config-change fixtures.
- Exit: no implementer must choose a financial/statistical meaning.

### Mission S08-B — migration and repositories (12h, product PR + evidence PR)

- Add config/book/origin/branch/manifests after migration preflight.
- Implement immutable create/get/list and exact idempotency/conflict semantics.
- Validate zero-origin and open-origin lifecycle.
- Exit: no outcome/aggregate/gate boolean is trusted or required.

### Mission S08-C — origin scheduler and branch fork (12h, product PR)

- Implement prospective schedule resolution and point-in-time loader.
- Fork five equivalent branch starts atomically.
- Add no-look-ahead, revised-source, missing-source, stale-monitor and duplicate
  session tests.
- Schedule remains disabled/offline until S12 observation authorisation.

### Mission S08-D — replay and independent red-team (8h, evidence-only)

- Bit-identical config/origin/branch replay.
- Static/perturbation Model A and broker firewall.
- Fresh-context Opus/Ultra reviews statistics, benchmark, time, source revisions,
  migrations and lineage.

## Required tests

- empty evaluator and zero matured episodes validate;
- every origin state and transition;
- five branches share exact starting state and external-flow policy;
- origin schedule ordinal/dependency groups are complete and stable;
- point-in-time chronology and revised/future data rejection;
- missing genuine XJO-TR/source/profile/policy blocks;
- prospective versus reconstructed isolation;
- config/code/contract/policy change starts a new lineage;
- exact replay/idempotency/conflict/failure atomicity;
- Model A deletion/randomisation leaves bytes identical;
- no broker or live-holdings writer is reachable.

## Observability

Emit config/book/session/origin/branch IDs/hashes, dependency group, source
versions, knowledge cutoff, prospective/reconstructed mode, fresh/stale/missing
counts, replay match, status, duration and stable reason. A development session is
never called clean or prospective promotion evidence.

## Rollback

Pause writers, preserve immutable origins, deploy compatible prior code, mark
affected config blocked and create a new config/cohort after forward repair. Never
rewrite an origin or transplant it into a new lineage.

## Definition of Done

- [ ] The complete protocol and version bundle are frozen before any origin.
- [ ] Zero/open/blocked/rejected/no-action/invalid/matured/unavailable states are representable.
- [ ] Five branches begin from equivalent point-in-time state.
- [ ] Model A removal/randomisation proof is immutable and hash-linked to the config.
- [ ] Overlap/dependency and statistical protocol are decision-complete.
- [ ] Reconstructed/development sessions cannot enter gate denominators.
- [ ] Migration/replay/forward recovery and full CI pass.
- [ ] Fresh-context Opus/Ultra red-team passes; combined worktree is clean.
