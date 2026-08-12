# ASXOS research-to-decision engine — live slice brief

**Date:** 2026-08-10  
**Status:** Implemented local prototype; proposed production direction  
**Authority:** Read-only, synthetic, paper-only demonstration. No production mutation, financial
instruction, broker connection, or migration authority.  
**Architecture basis:**
[`asxos-research-to-decision-engine-target-architecture-2026-08-10.md`](asxos-research-to-decision-engine-target-architecture-2026-08-10.md)  
**Observed base:** `main` at `1b471b6` before the prototype changes

## 1. Outcome

ASXOS now has a runnable vertical slice showing what the target architecture feels like as a
product, not just a diagram.

Run it from the repository root:

```bash
make decision-demo
```

Then open:

- cockpit: <http://127.0.0.1:8790/>
- exact brief contract: <http://127.0.0.1:8790/api/brief>
- one decision case: <http://127.0.0.1:8790/api/cases/paper-ready>
- generated API schema: <http://127.0.0.1:8790/docs>

The cockpit demonstrates two complete paths:

1. **Positive control:** synthetic evidence passes independent challenge and portfolio constraints,
   producing a fictional paper-only `initiate` packet with a size range.
2. **Negative control:** unresolved tradeability and concentration fail deterministic gates,
   forcing `abstain` and a zero size range even though scenarios still exist.

The important result is not the fictional verdict. It is that the HTML, JSON, challenge,
portfolio assessment, and decision ask all resolve to the same immutable packet identity.

## 2. What is genuinely live

```text
synthetic point-in-time evidence
  → EvidencePacket with cutoff + content hash
  → ThesisVersion with bull/base/bear cases
  → independent ChallengeResult
  → deterministic PortfolioAssessment
  → immutable DecisionPacket with content hash
  ├─→ human cockpit
  └─→ exact JSON/API contract
```

The implementation enforces:

- immutable, unknown-field-rejecting Pydantic contracts;
- Decimal-only financial inputs—float input fails validation;
- `known_at <= knowledge_cutoff` for every admitted evidence item;
- complete evidence → thesis → challenge → portfolio → decision identity links;
- exact bull/base/bear coverage and scenario probabilities summing to 100;
- independent challenge capable of changing the outcome;
- failed constraints blocking capital deployment;
- unresolved inputs blocking `initiate`/`add` states;
- `avoid` and `abstain` carrying a zero size range;
- stable SHA-256 content identity for evidence and decision packets;
- Model A excluded from the decision basis; and
- a pure renderer with no finance or allocation calculation.

## 3. Why this shape fits ASXOS

The prototype does not replace the current system. It adds the missing decision spine through the
parts that are already valuable.

| Target responsibility | Existing ASXOS capability to reuse | Prototype / next adapter |
|---|---|---|
| Point-in-time evidence | Prices, PIT fundamentals, financial statements, regulatory/news ingestion, research store | `EvidencePacket` is implemented; Supabase read/freeze adapter is next |
| Theme and candidate research | Screening evaluator, factor research, macro theses, themes and theme holdings | Map admitted outputs into candidate/evidence identities; do not use Model A |
| Investment thesis | `ThesisProposal`, report sections, thesis service and revisions | `ThesisVersion` demonstrates the target boundary; reconcile rather than duplicate |
| Independent challenge | Existing advisory finance-agent workflow | `ChallengeResult` contract is implemented; governed producer and approval path are next |
| Portfolio and capital | Profile, constraints, volatility, tax overlay, rebalance and paper portfolio | `PortfolioAssessment` boundary is implemented; deterministic adapter is next |
| Decision truth | No complete cross-domain object today | `DecisionPacket` and cross-object validation are implemented |
| User surface | FastAPI, Jinja brief, CLI/email patterns | Cockpit and JSON render from the same object today |
| Disposition | Journal/decision concepts and governance transitions | Exact packet-hash response record still required |
| Outcome and learning | Paper trade, snapshots, signal outcomes, benchmark returns | Cross-object outcome and learning adapters still required |

### Existing infrastructure retained

- **Python 3.12:** domain and adapter language.
- **Pydantic:** strict contracts at every boundary.
- **FastAPI:** read/query and later governed-command surface.
- **Jinja:** deterministic human rendering.
- **Supabase/Postgres:** future operational store for governed objects and serving state.
- **Render:** future hosting for the API/renderer and single scheduler owner.
- **GitHub:** source, review, CI, and release—not decision truth or production scheduling.
- **Resend:** future delivery transport behind an outbox.

No microservices, streaming platform, new warehouse, frontend framework, vector database, or broker
integration was introduced.

## 4. Deliberate prototype boundary

The prototype runs as `asxos.prototype.app`, separately from `asxos.api.main`.

This is intentional. Production startup currently requires Supabase, migration parity, email
settings, and a warmed Model A artifact. A visual architecture demonstration should neither require
those credentials nor weaken the production hard-fail rules. The production integration should
reuse the domain contracts and renderer through real adapters; it should not merge the prototype
startup path into the production lifespan.

The prototype currently:

- reads no Supabase rows;
- calls no data provider or LLM;
- writes no database or object-store record;
- sends no email;
- creates no paper-trade row;
- uses only fictional symbols and values; and
- cannot execute a trade.

It proves the interaction and contract shape, not investment edge or production readiness.

## 5. Product experience represented

The surface puts the investor’s questions in the right order:

1. What changed?
2. What is the investment question and variant view?
3. What evidence was actually known at the cutoff?
4. What are the bull, base, and bear paths?
5. What did the independent challenger find?
6. Which portfolio constraints passed, failed, or remain unknown?
7. What size range and loss budget survive those checks?
8. What is missing?
9. What exact decision is being asked of James?

It also shows that abstention is a successful engine output. ASXOS must not force every thesis or
price condition into an action.

## 6. Source map

| File | Role |
|---|---|
| `asxos/domain/decision_engine/types.py` | Immutable logical contracts and cross-object gates |
| `asxos/domain/decision_engine/demo.py` | Deterministic synthetic positive and negative controls |
| `asxos/domain/decision_engine/renderer.py` | Finance-free Jinja renderer |
| `asxos/prototype/app.py` | Read-only FastAPI cockpit and JSON endpoints |
| `asxos/brief/templates/decision_engine_prototype.html.j2` | Human decision surface |
| `tests/test_decision_engine_prototype.py` | Temporal, precision, identity, gate, render, and API tests |
| `Makefile` | `make decision-demo` entry point |

## 7. Production integration architecture

The contracts should remain in the domain layer. Infrastructure enters through adapters:

```text
Existing Supabase tables              Existing deterministic services
prices / fundamentals_pit             themes / screening / theses
research store / governance           constraints / tax / paper portfolio
          │                                          │
          └──────────── read-only adapters ──────────┘
                              │
                    Decision case composer
                              │
              validate → challenge → capital gates
                              │
                 append-only DecisionPacket store
                    │                       │
             brief/API renderer       transactional outbox
                    │                       │
                    └──── James disposition ┘
                              │
                  paper outcome + benchmark
                              │
                       LearningReview
```

The adapters must translate existing ASXOS records; they must not hide DB access inside the
contracts or renderer. A production packet is written only after every identity and gate validates
inside one governed application-service transaction.

## 8. Recommended next work order

Do **one read-only real-data adapter**, not a migration or broad rewrite.

### Objective

Reconstruct one ordinary ASX equity case from existing approved Supabase data at a declared
historical cutoff and render it through the new contract without persisting a `DecisionPacket`.

### Scope

1. Ratify or amend the prototype contract fields against the target architecture and current
   thesis/portfolio schemas.
2. Select one ordinary ASX equity—not HUBS/ESS—as the positive-control case.
3. Implement a read-only evidence adapter over existing PIT fundamentals, prices, approved themes,
   thesis evidence, and a portfolio snapshot.
4. Produce explicit missing/uncertain inputs rather than fabricating values.
5. Connect existing deterministic portfolio constraints through a thin adapter.
6. Render the resulting case locally through the same HTML and JSON surfaces.

### Acceptance gates

- Every admitted item has source identity, `observed_at`, `known_at`, and quality.
- No fact after the historical cutoff enters the packet.
- No Model A signal, label, probability, expected return, or SHAP value enters the basis.
- No LLM supplies a capital-relevant number.
- Every thesis and challenge citation resolves inside the frozen evidence packet.
- Missing evidence forces `watch` or `abstain`.
- Existing portfolio hard constraints remain authoritative and Decimal-exact.
- The HTML and JSON packet hashes agree.
- The run is repeatable for the same cutoff and code SHA.
- No production write, migration, email, or paper trade occurs.

### Stop condition

Stop after presenting the reconstructed case and a reuse/gap report to James. Do not persist the
new object model until the contract has been ratified from this real-data exercise.

## 9. Following production increments

Only after the read-only adapter is accepted:

1. **Governed persistence:** append-only packet identities, revisions, and an idempotent materialiser.
2. **Disposition:** James accepts, rejects, defers, or requests revision against an exact packet hash.
3. **Paper intent:** an accepted packet may create a non-executing, separately identified paper intent.
4. **Reliable delivery:** transactional outbox plus retryable receipt state.
5. **Outcome:** price, benchmark, FX, costs, and portfolio contribution observed at declared horizons.
6. **Learning:** separate thesis correctness, sizing/timing, process adherence, and financial result.
7. **Surface cutover:** the normal ASXOS brief consumes admitted packets instead of recomputing logic.

Object storage, Parquet/DuckDB, and Dagster should enter when the point-in-time evidence and
research-replay work order begins. They are not prerequisites for validating this decision
contract against one existing Supabase case.

## 10. Risks and design decisions still open

| Open decision | Why it matters |
|---|---|
| Exact total-return benchmark | Determines whether “outperform” is measurable rather than rhetorical |
| Primary evaluation horizon | Controls thesis expiry, outcome windows, and turnover expectations |
| Risk/loss budget policy | Separates capital protection from arbitrary stop prices |
| Contract reconciliation | Avoids parallel `ThesisProposal` and `ThesisVersion` truths |
| Challenge authority | Defines which findings block, revise, or merely monitor |
| Portfolio adapter semantics | Existing allocator is Model-A-shaped and cannot enter the capital path unchanged |
| Persistence granularity | Logical contracts do not imply one table per model |
| Scheduler owner | Production jobs must have one owner, not Render plus GitHub duplication |

The existing allocator’s dependence on Model A is especially important: reuse its Decimal,
constraint, portfolio, and tax mechanics, but replace the candidate merit/ranking input before it
can support this engine.

## 11. Instructions for Claude/Arbi

Treat the prototype as an executable architecture question, not a pre-approved feature.

1. Run `make decision-demo` and inspect both the cockpit and JSON.
2. Review the new contracts against existing schema, authority, north-star, finance, reliability,
   and personal-advice boundaries.
3. Identify duplicated concepts and propose a reconciliation—not a second object hierarchy.
4. Challenge whether the positive and negative controls prove the right gates.
5. Return a contract ratification/change packet and one bounded read-only adapter work order.
6. Do not apply a migration, change production, send an email, open a paper trade, or start a broad
   orchestration/storage programme.
7. Do not apply paused migration `0042` or import the paused rules-build wholesale.

The next useful result is one real-data, historical-cutoff reconstruction through this boundary.
It is not a full engine build and not another programme roadmap.

## 12. Success statement

This slice makes the target architecture concrete while preserving ASXOS’s strongest existing
assets. It also makes the remaining gap honest:

> ASXOS can now demonstrate the shape of an evidence-to-decision engine. It does not yet prove
> that real ASXOS evidence can flow through that shape, that the decisions outperform a benchmark,
> or that outcomes change the next decision.

The next milestone is therefore integration evidence, not more architecture prose.
