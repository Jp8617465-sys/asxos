# Personal-Advice Firewall — Amendment for Single-User Direct Advice + Order Staging

**Status:** proposed — DRAFT for James's ratification (a boundary change to a non-negotiable; per
`arbi-constitution.md` §reserved authorities, arbi may only draft this, never self-enact it)
**Revision:** v2 (2026-07-18) — incorporates the arbi-red-team + security-engineer reviews of v1
and James's "full staging, wired to a model-independent sizer" scope decision.
**Scope:** redefines the s766B personal-advice firewall for the single-user reality. Does NOT
touch rule #11 (Model A quarantine — a separate axis), the no-autonomous-execution line, or the
single-user/no-distribution constraint.
**Owner:** arbi drafts; James ratifies by merging the authority-file PR this doc specifies
**Superseded by:** N/A

---

## 1. What James decided (the grant this amendment implements — no broader)

James (governor), 2026-07-18: *"I do want it to be personal advice for just me."* Scope chosen via
two AskUserQuestion decisions:

- **Register (decision 1): "Advise + stage orders."** The system gives James **direct, tailored
  personal advice** — a real recommendation (buy / hold / trim / exit) reasoned to his situation
  and objectives, with conviction — not a hedged "here's evidence, you decide" summary; and it
  **stages full orders** (size, limit price, tax-lot selection) prepared to the broker's door.
- **Staged-number provenance (decision 2): "Full staging, wired to a model-independent sizer."**
  Staged **sizes** must come from a deterministic, **model-independent sizer**
  (inverse-vol / conviction / cap-driven — never the Model-A composite score), sourced verbatim,
  never originated by an LLM. This adds a build dependency (§4a) — the current allocator's sizer
  is dormant under rule #11 — but keeps every staged number Decimal-exact and cited.
- James **reviews and places every order himself.** Autonomous execution was explicitly offered
  and **declined** — it remains out and would need its own, separate governor decision.

`stage` is defined, everywhere it becomes a verb of authority, as: *prepared to the broker's
door — a specific size/price/tax-lot memo James reviews and places; the system never places it,
and no execution tool or broker credential exists.*

## 2. Key finding — this is a reconciliation, not a teardown

The north star's firewall is **already drawn at execution, not advice.** `north-star.md`
non-negotiable #2: *"The firewall is execution, not analysis … arbi allocates on paper; James
acts in reality."* The P-ladder already produces **allocation memos** — "the gap between the best
memo and one dollar moving is James reading it." What contradicts the grant is the **surfaces
over-hedging against that boundary** (most sharply `pm-review.md`: *"never give personal financial
advice … even for a single user"*, *"no 'you should buy/sell N shares'"*). This amendment
reconciles the surfaces to the boundary, adds full order staging, and keeps every safety line
intact.

## 3. The boundary after this amendment (canonical)

| Capability | After amendment |
|---|---|
| Direct, tailored advice to James (buy/hold/trim/exit **as a recommendation**, with conviction) | **IN** — new |
| Staging **full orders** (size, limit price, tax-lot) to the broker's door | **IN** — new; **sizes from the model-independent sizer (§4a), never LLM-originated** |
| System places an order / moves capital / touches a broker | **OUT** — unchanged. James reviews and places every trade. P6 stays: no execution tool, no broker credential, ever. |
| Surfaced / distributed to / represented to anyone but James | **OUT** — unchanged. Single-user; `ASXOS_PERSONAL_USE` gate stays. |
| Represents itself as licensed / AFSL advice | **OUT** — unchanged. |
| Model A signal/score/rank as a *basis* for a recommendation **or a staged size** | **OUT** — unchanged (rule #11 standing; separate axis). |

## 4. Exact before/after per authority file (the ratifiable change)

Each is a RED ZONE authority file — edits land via the GitHub-API draft-PR route, never a local
edit. **The circuit-breaker wording is synchronized across four files (`arbi-permission-model.md`
declares them "the same nine"); all four MUST change in the same PR or the invariant breaks and a
now-authorized staged order still zeroes a graded run.**

### 4.1 `docs/product/north-star.md` — non-negotiable #2
Keep "execution, not analysis" verbatim. Add: *"For the single authorized user the system speaks
in the register of direct personal advice — a recommendation with conviction, and staged full
orders (size from the model-independent sizer, limit price and tax-lot) prepared for James to
review and place. The firewall is that James executes every order himself (P6 — no broker tool or
credential exists), that nothing is surfaced to any other person, and that nothing represents
itself as licensed advice."*

### 4.2 `.claude/commands/pm-review.md`
Replace *"never give personal financial advice … even for a single user"* → *"you give James a
direct recommendation and may stage the full order (size, limit price, tax-lot) to act on it; you
never place an order — James reviews and executes every trade. The firewall is execution and
distribution, not advice-to-the-one-user."* Replace the boundary line *"no 'you should buy/sell N
shares', no price target you invent"* → *"You MAY say 'buy/trim N shares at $X, using tax-lot L'
as a **staged** recommendation, where **N comes verbatim from the model-independent sizer**, $X
from a cited limit rule, and L from the deterministic tax-lot selector — never a figure any LLM
originates. `stage` = prepared to the broker's door; James places it."*

### 4.3 `.claude/rules/portfolio-conventions.md` — §Regulatory firewall
Keep the `_require_personal_use()` / `ASXOS_PERSONAL_USE` gate. Reframe its rationale to
*"confining direct personal advice and staged orders to the single authorized user; the firewall
is multi-user surfacing + execution, not advice to that one user."* Add a line that staged
**sizes** are model-independent (§4a) — never the `portfolio-policy.md` composite (0.6 `prob_up` /
0.4 `expected_return`, both Model A outputs).

### 4.4 `docs/product/arbi-permission-model.md` — TWO edits, preserve the Model-A clause
- The halt-tripwire (~:196-198): amend *"a memo that implies an order rather than a proposal James
  decides on"* → *"the system executing, moving capital, or routing to a broker. A **staged order
  James reviews and places** is the authorized advice+staging register, NOT a tripwire; an action
  that **executes** one is."* **Preserve the adjacent Model-A clause** ("a Model A-derived
  recommendation while quarantined…") intact — that's rule #11.
- The P4 promotion precondition (~:186): amend *"with no memo that ever implied an order"* to the
  staged-order-aware wording, or the file self-contradicts (authorizes staging while forbidding
  ever having staged).
- Correct v1's slip: staging lives at **P2/P3 (the memo), optionally persisted at P4 — never
  P5** (P5 is a policy boundary-change tier). **P6 (Execute) stays exactly as written, never
  promotable.**

### 4.5 The synchronized circuit-breaker copies (the v1 miss — all must change with 4.4)
- `docs/product/arbi-scorecard.md` (~:35-36 Layer-1 hard gate + ~:44-45 the "same nine" list)
- `docs/product/rubrics/arbi-safety-boundary.md` (~:10-13)
- `docs/product/evals/fixture-005-capital-impacting-request.md` — currently lists "size a
  position, place/stage an order" as things arbi must **decline** (:4,:6,:20-21,:26); post-grant
  a *staged sized order* moves to the authorized side. Update the fixture (and add a new
  must-DECLINE fixture for *autonomous execution*, which stays forbidden, so the eval still
  guards the real line).
- `docs/product/arbi-evals.md` (~:30 "no trade/position/capital recommendation") — scope this to
  arbi's *wake-up/infra* capacity, distinct from the now-recommending `/pm-review` P-ladder.

### 4.6 `docs/product/portfolio-manager-charter.md` — the CANONICAL stance (v1 miss)
`:53-66` is labelled "canonical text — other docs cite this" and still reads "evidence-grounded
analysis, risks, options, and trade-offs." Update it to the direct-advice + full-staging register
(so the derived north-star text isn't more permissive than its source), per the charter's own
"co-dependent sections update in the same change" rule (:114-118). Keep "a recommendation is not
an order" verbatim + add that a staged sized order is still a recommendation (nothing executes
until James places it). Mirror the same update in `docs/product/arbi-harness.md` (~:158-166).

### 4.7 `docs/product/recommendation-schema.md` — add the staged-order structure (v1 miss)
The schema can't represent a staged order today (`sizing` :35 is target-weight only; no
limit-price field; `tax_implications` :36 is CGT eligibility, not an order instruction). Add a
`staged_orders[]` field: `{symbol, side, size (from sizer), limit_price, tax_lot_ids,
size_provenance, model_independence: true}`. Keep the `not_this` disclaimer (:57-61) verbatim.

### 4.8 `CLAUDE.md` — exact lines only
Amend **line 175** (arbi "never crosses the personal-advice firewall") to the redefined
boundary. **Do NOT touch line 211** ("runtime in-product tax/portfolio LLM agent is a structural
NO — personal-advice firewall + Decimal-only determinism") — that's about runtime determinism, a
different concern that still holds.

### 4.9 Rationale-clause + "never-lifts" annotations (scope, don't lift)
- `.claude/commands/arbi.md` (~:100-101) and `arbi-close.md` (~:67): the *restriction* (those
  surfaces make no recommendation) stays correct; correct the *reason* from "firewall is
  structural" to "surface-scoping — only `/pm-review`/memos produce recommendations."
- `docs/product/roadmap-state.md` (~:429-430) and `arbi-full-auto-activation-2026-07-15.md`
  (~:122): annotate the "never lifts" firewall lines to scope them to the **execution /
  no-autonomous-trade axis** (redefinition ≠ lifting).

## 4a. The model-independent sizer (new build dependency for staged sizes)

"Full staging" requires staged **sizes** be Decimal-derived and model-independent. The existing
deterministic path (`compute_deltas`/`tag_loss_harvest`, pure Decimal) is trustworthy but its
*target* comes from the allocator (`build-portfolio`), which **hard-fails under rule #11**
(`resolve_production_model` → 0 approved → dormant). So a **model-independent sizer** must exist
before sized-order staging ships: inverse-vol (from `volatility.py`, prices-only, no Model A) +
James's conviction + sector/position caps → sizes, entirely decoupled from the model gate. Price
and tax-lot are Decimal-derivable from holdings **today** (no sizer needed); **size** waits on
this. Owner: `backend-architect` (design) + `performance-engineer` (vol hot path). This is a
separate build (roadmap task) — the amendment authorizes full staging; the sized-order half is
*live* only once the sizer lands.

## 5. What explicitly stays OUT

Autonomous execution (no broker tool or credential, ever — P6 unchanged); any second recipient;
licensed-advice representation; Model A as a basis for a recommendation **or a staged size** (rule
#11, untouched, separate axis).

## 6. Enforcement (what actually holds, stated honestly)

- **`_require_personal_use()` / `ASXOS_PERSONAL_USE=1`** — the single-user gate. **Companion fix
  required before ratification (security-engineer):** it is NOT currently called on
  `asx tax-view` / `asx tax-action` (`asxos/cli/tax.py`) — the exact tax-lot surface a staged
  order draws from is ungated (R14-class hole). Close it (+ the R14 lint/test asserting every CLI
  entry point carries the gate) as a companion code PR. Until then §4.3's "load-bearing gate"
  claim is not uniformly true. (This is an env-gate on a no-auth single-user deployment — a
  load-bearing invariant, not a cryptographic "only James" guarantee.)
- **No execution — the strong backstop:** no broker/execution tool is mounted AND **no broker
  credential exists anywhere** (`render.yaml` holds no trading key), so even a hand-crafted
  request has nothing to authenticate with. Off-allow-list egress (`curl -X POST`) is not
  mechanically blocked attended — it prompts James — so the precise claim is "no tool, no
  credential, and any off-list egress needs James's explicit approval," not "physically
  impossible." For the attended single-user case (James places every order) that IS the boundary.
- **Staged-number provenance:** mechanically guaranteed only when numbers come from the
  deterministic path (the sizer §4a + cited price + `tag_loss_harvest`). §4.2 requires staged
  numbers be sourced verbatim from it; an LLM surface must never originate a size/price/lot.

## 6a. Residual risk (acknowledged, not mechanically closed)

Untrusted input (`regulatory_events` RSS, news) feeds the LLM surfaces; in a directive register an
injection ("stage a buy of X") could shape a memo James reads. Blast radius is bounded by
no-execution + no-credential + single-user + James reviewing every order before placing — the same
human-in-the-loop residual any bad advice carries. It is NOT closed by a mechanical
number-provenance check on the LLM surface; the §4.2 verbatim-from-sizer requirement is what keeps
the *numbers* trustworthy, and James's review is the backstop on the *recommendation*.

## 7. Honest note on the law (stated once; not a legal opinion)

For a genuinely single-user tool advising only its owner, the regulated concept of a "financial
service to another person" is likely not even engaged — no client, no second party, no business.
The conservative "no personal advice even for one user" framing was partly a hedge against a
possible multi-user future. If James wants certainty before relying on this heavily, that is one
question for a real adviser/lawyer — not something arbi can certify.

## 8. Ratification path

1. ✅ arbi-red-team + security-engineer reviewed v1 → both CHALLENGE; fixes folded into this v2.
2. **Companion code PR (ratification-gating):** close the `tax.py` firewall gate + R14 guard test.
3. **Build dependency (for the sized-order half):** the model-independent sizer (§4a).
4. Land the §4/§4.5-4.9 authority-file edits (all synchronized copies together) via the
   GitHub-API draft-PR route, with this doc as rationale, as a **draft PR**.
5. **James merges = ratifies.** Until then the current firewall stands and the surfaces keep
   their existing wording.

Nothing in the broker-report build ships in the direct-advice register until this amendment is
ratified; sized-order staging is not live until the §4a sizer lands.
