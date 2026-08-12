# Recommendation schema — the shape of an action memo

**Status:** current — **DERIVED RENDER VIEW** (see the boundary note below)
**Scope:** the required structure of every decision-support artifact arbi produces under the
portfolio-manager charter (single-position memo or portfolio allocation proposal), so none is
uncited, incomplete, or silently model-dependent.
**Last verified:** 2026-08-12 (declared a derived render view of the canonical contract per
`target-architecture.md` B.2 + the governor's 2026-08-12 (c) ruling; fields unchanged) · 2026-07-10
**Owner:** James (governor) approves the schema; arbi fills it. arbi may draft schema changes.
**Superseded by:** N/A

> **This file is a DERIVED RENDER VIEW of the canonical decision contract. It is not a rival
> contract.** Required by `target-architecture.md` Appendix **B.2** ("`recommendation-schema.md` →
> **ADAPTED** to the human memo/render view *derived from* a `DecisionPacket`. It is not a rival
> contract and must carry a header saying so") and recorded here on **2026-08-12** under the
> governor's ruling (c) in **B.4**.
>
> The canonical contract is `asxos/domain/decision_engine/types.py`, on `main` since commit
> `7aa8507` (PR #87). What that means in practice:
>
> - **Where this file and the code disagree, the code wins** on validator strictness, hashing,
>   temporal enforcement and internal structure; **Appendix B** wins on which artifacts exist,
>   which fields are mandatory, and the ruled semantic tables (state→verdict, F3 horizons, the
>   five F4 universal gates).
> - A memo's `verdict` vocabulary is **not** free here: it is the B.3 mapping from
>   `DecisionPacket.recommendation_state`, implemented as `memo_verdict_for()`
>   (`types.py:85-99`). **No surface may invent a third vocabulary** — the
>   no-fourth-definition rule is part of Appendix B.
> - **Known shape divergence, to be resolved in favour of the code.** The `model_independence`
>   row below defines an enum, `model-independent | uses-model-A`. The canonical contract types it
>   as `Literal[True]` (`types.py:466`), which makes non-independence **unrepresentable** rather
>   than merely invalid — strictly stronger, and consistent with rule #11. Treat the code as the
>   binding shape; this row is retained as the memo-render wording until it is amended.

A recommendation is a **memo James reads and acts on**, never an order (`portfolio-manager-charter.md`).
This schema is what makes every memo decision-ready and auditable: it forces the evidence,
the model-independence assertion, the tax and risk framing, and the explicit decision ask.
A memo missing a **required** field is not emitted — it is incomplete, not advice.

The `/pm-review` synthesizer already produces the P2 (single-position) shape informally; this
schema formalises it and extends it to P3 (portfolio proposal), and adds the fields the
`portfolio-outcome-ledger.md` needs to close the learning loop.

---

## Fields

| Field | Req? | Meaning |
|---|---|---|
| `recommendation_id` | ✔ | stable slug, e.g. `rec-2026-07-10-BHP` or `rec-2026-07-10-rebalance` |
| `date` | ✔ | date produced |
| `type` | ✔ | `single-position` (P2) or `portfolio-proposal` (P3) |
| `scope` | ✔ | the symbol(s), or `whole-portfolio` |
| `verdict` | ✔ | per-position: `GOOD HOLD` / `TRIM` / `ADD` / `REVIEW` / `EXIT-CANDIDATE`; portfolio: `REBALANCE` / `HOLD` / `REVIEW` |
| `rationale` | ✔ | the case, in prose — **every claim ties to a cited data point** (below), never an unanchored opinion |
| `evidence[]` | ✔ | list of citations, each tiered (below). No evidence → no memo. |
| `model_independence` | ✔ | `model-independent` \| `uses-model-A`. **While rule #11 stands, must be `model-independent` or the memo is VOID** (`portfolio-policy.md`). |
| `policy_check` | ✔ | which `portfolio-policy.md` hard constraints were checked and the result (e.g. "sector cap 30%: post-trim Materials 26% ✓"). A breach → this is a P5 policy-change proposal, not a recommendation. |
| `sizing` | proposal only | target weight or delta per symbol — a **proposal**, not an order. State the basis (inverse-vol, thesis conviction, cap-driven). |
| `tax_implications` | ✔ if a sell | CGT eligibility (calendar rule, spec §5.1), discount status, any loss-harvest tag **with the Part IVA / TR 2008/1 disclaimer verbatim** (`portfolio-policy.md`). Cite spec sections for numbers. |
| `risk_framing` | ✔ | concentration after the move + the **v1 risk-blindness caveat** verbatim when concentration is touched (caps don't protect against co-movement). |
| `decision_ask` | ✔ | the single explicit thing James must decide ("Trim BHP from 8% to 5%? y/n"), phrased so declining is a first-class option. |
| `not_this` | ✔ | the standing disclaimer (below) — this is not advice, not an order, not auto-executed. |
| `confidence` | ✔ | arbi's own confidence + what would change the call (a falsifier). Thin evidence must say so (`arbi-harness.md` §Required citations). |
| `outcome` | filled later | James's decision + realised result — written into `portfolio-outcome-ledger.md`, not the memo. |

## Evidence tiering (mirrors the governance evidence model)

Each `evidence[]` item is one of — and says which:

- **verified** — a live value read this run (a `signals`/`prices`/`theses`/tax figure, a
  benchmark gap, a concentration %), with the source (table/thesis_id/query). Replayable.
- **inferred** — a conclusion arbi drew from verified inputs (e.g. "trajectory is stalling").
  Name the inputs.
- **speculative** — a forward view (e.g. "if the RBA holds, the thesis catalyst slips").
  Clearly flagged; never dressed as verified.

A memo whose verdict rests on a **speculative** claim must say so in `confidence`.

## The standing `not_this` disclaimer (every memo carries it)

> This is single-user decision-support for James, not licensed financial advice. It is a
> proposal, not an order — nothing executes unless James places it in his own broker. It uses
> no Model A output while rule #11 stands. Figures trace to cited live data; declining is a
> valid outcome.

## Worked shape — a model-independent TRIM memo (illustrative)

```
recommendation_id: rec-2026-07-10-XYZ
type: single-position   scope: XYZ.AU   verdict: TRIM
model_independence: model-independent
rationale: XYZ hit its thesis target (thesis_id 42: target 14.20, last 14.35) and the
  position is 9.1% vs the policy's concentration intent. This is a discipline TRIM on a
  target hit, not a signal call.
evidence:
  - verified: theses.thesis_id=42 target_price=14.20, prices XYZ.AU last=14.35 (2026-07-09)
  - verified: current_holdings XYZ.AU weight 9.1%
  - verified: holding_lot acquired 2025-02-01 → CGT-discount eligible (spec §5.1)
policy_check: sector cap ✓ post-trim; position-count intent ✓; cash floor [read profile]
sizing: trim to ~5% (proposal; basis: back to conviction-sized, discount-eligible lots first)
tax_implications: discount-eligible; no loss-harvest tag (gain). Cite spec §5 for CGT calc.
risk_framing: post-trim concentration lower; NB v1 caps don't protect against ASX co-movement.
decision_ask: Trim XYZ from ~9% to ~5%, selling discount-eligible lots? (y / n / other)
confidence: high on the target-hit fact; the sizing is a prior, not calibrated.
not_this: <standing disclaimer above>
```

Everything in that memo is model-independent — it would stand unchanged if Model A did not
exist. That is the test for every memo produced while rule #11 holds.
