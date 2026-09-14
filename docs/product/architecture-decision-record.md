# asxos — Architecture & Decision Record

**Owner:** James (governor)
**Status:** living reference — one of the five permitted under R4
**Last updated:** 23 August 2026

---

## What this document is

The single authority for **architectural decisions and their reasoning**. New research and settled decisions are **folded into this file**, never appended as companion documents.

**What it holds:** decisions, the evidence behind them, target-state architecture, corrections to earlier analysis.

**What it does not hold:** task state. Actionable work lives in GitHub Issues (R1). If something here reads like a to-do, it belongs in an Issue instead.

**Relationship to other documents:**
- `roadmap-state.md` — frozen. It was a queue; queues live in Issues now.
- `docs/proposals/*` — immutable dated decision records. Superseded by reference, never edited in place.
- Research outputs — folded in here, then archived. No standing companion files.

**Suggested path:** `docs/product/architecture-decision-record.md`. Note `docs/product/` sits in `AUTHORITY_FRAGMENTS`, so arbi can propose changes but cannot enact them. That is the correct property for a governor-owned decision record.

---

## 0. Artifact register

Every file produced or shared in the design conversation, with disposition. **Executable specifications are inlined verbatim in this document** (§10) so Claude Code never infers or rescopes them. Research inputs are folded to conclusions and archived — inlining them adds length without adding buildable detail.

| Artifact | Type | Disposition | Where its content lives now |
|---|---|---|---|
| `asxos-delivery-diagnostic.md` (23 Aug) | Audit | **Superseded** by the combined audit | Part II of the combined audit |
| `asxos-audit-v2-correctness-and-delivery.md` (23 Aug) | Audit | **Active input** — archive after Slice 0 merges | Findings → §3.5, §3.6, §4; remediation → Slice 0 |
| `claude-code-audit-prompt.md` (23 Aug) | **Executable spec** | In flight — Slice 0 | Verbatim §10.1 |
| Cursor permission-lift prompt (23 Aug) | **Executable spec** | Executed → D7 | Verbatim §10.2 |
| End-to-end investment process + roadmap research | Research input | Folded | §2 target state, §6 build sequence, D3/D4 |
| Cash floor & leverage cap research | Research input | Folded | D1 (§1.1), D2 (§1.3), §8 |
| Challenge layer research | Research input | Folded | D12/D13/D14 (§1.4–1.6), §8 |
| Work-management / ticketing research | Research input | Folded | D10 (§5.4), D11 (§5.5), §3.6, §7, §8 |
| Issue templates ×3 | **Executable spec** | **Ratified D11** — files written | Verbatim §10.3; files at `.github/ISSUE_TEMPLATE/` |
| Layer 1 challenge rules | **Executable spec** | Ratified D12, not built | Verbatim §10.4 |
| Slice 1 scaffold spec | **Executable spec** | Not built | Verbatim §10.5 |

**Rule for this register:** anything created from here on gets a row. An artifact with no row does not exist as far as the build is concerned.

### How to use this document with Claude Code

**Commit this file** to `docs/product/architecture-decision-record.md`. It is a living reference (one of the five permitted under R4), not a throwaway input. `docs/product/` sits in `AUTHORITY_FRAGMENTS`, so arbi may propose changes but cannot enact them — the correct property for a governor-owned record.

When working with Claude Code, reference sections by number. Its presence is not licence to create companion documents; new decisions are folded in here.

- **Building something?** §6 for the slice, §10 for the verbatim spec, §1 for the constraints that apply.
- **Unsure whether something is decided?** §1 register. If a row says Open or Proposed, it is not decided — ask, do not assume.
- **Tempted to add a constraint?** §7 anti-scope first.
- **Think a fact here is wrong?** §4 corrections log. Four entries already; add a fifth rather than silently working around it.

**Growth policy:** this file grows with *specifications*, not narrative. If an edit adds prose rather than something executable, it probably belongs in a decision row instead.

---

## 1. Decision register

Every ratified decision, with date and reasoning. Append-only; supersede by adding a new row, never by editing an old one.

| # | Decision | Value | Date | Authority | Status |
|---|---|---|---|---|---|
| D1 | Cash floor | **7.5%** (range 5–10%) | 2026-08-23 | James (reserved) | **Ratified**, conditional — see §1.1 |
| D2 | Leverage cap | **0% gross LVR** | 2026-08-23 | James (reserved) | **Ratified** — see §1.3 |
| D3 | Forecasting approach | No ML successor to Model A. Deterministic factor tilts + calibrated human judgement. | 2026-08-23 | James | Ratified |
| D4 | Model A successor bar | Eight criteria, all mandatory | 2026-08-23 | James | Ratified as policy — see §1.7 |
| D5 | Next build | `decision_engine` persistence + builder (the spine) | 2026-08-23 | James | Ratified |
| D6 | Build method | Vertical slices ending in merged PRs. No sprints. Spec expressed as types + DDL + failing tests, not prose. | 2026-08-23 | James | Ratified |
| D7 | Migrations permission | `Edit(/migrations/**)` deny lifted; `migrations/` removed from `AUTHORITY_FRAGMENTS` | 2026-08-23 | James | Ratified — see §1.2 |
| D8 | Sector cap | 30% per GICS sector | pre-existing | James | Ratified (not under review) |
| D9 | Rule #11 (Model A quarantine) | Standing | pre-existing | James | Ratified — enforced in code, see §3.2 |
| D10 | Work-management substrate | **GitHub Issues** + Projects v2 board. Not Backlog.md. | 2026-08-23 | James | **Ratified** — see §5.4. Supersedes audit R1 |
| D11 | Ticket schema & three work types | product / data-infra / research, each with a distinct template. Three trims applied. | 2026-08-23 | James | **Ratified** — see §5.5, spec §10.3 |
| D12 | Challenge mechanism | Two layers: deterministic rules in code + bounded LLM agent. Rules are NOT LLM-executed. | 2026-08-23 | James | **Ratified** — see §1.4 |
| D13 | Challenge visibility | Hybrid: blind for the outside-view pass, informed for the steelman | 2026-08-23 | James | **Ratified** — see §1.5 |
| D14 | Severity thresholds | `blocking` = breach of a ratified register decision or certain data-integrity failure. Nothing else. | 2026-08-23 | James | **Ratified** — see §1.6 |

### 1.1 D1 — Cash floor, 7.5%

**Reasoning (one sentence):** A 5–10% floor costs only ~25–55 bps of after-tax return per year yet materially cuts drawdown, funds rebalancing without forced sales, and buys margin-call headroom if leverage is ever permitted.

**Supporting arithmetic:**
- After-tax drag ≈ **4–5.4 bps per 1% cash per year** at 47% marginal rate. Cash interest is taxed as ordinary income; equity returns carry franking and CGT deferral, so after-tax drag is *higher* than pre-tax, not lower.
- At 7.5%: roughly **30–40 bps/year** of after-tax cost.
- Drawdown effect under the mandated 0.8+ correlation assumption: portfolio DD = (1 − cash%) × equity DD. A GFC-shaped 50% index fall becomes ~46% at a 7.5% floor; required recovery gain falls from +100% to ~+86%.

**Explicitly not claimed:** there is no robust evidence that a cash floor improves risk-adjusted returns via market timing or "dry powder." That literature is weak and contested (best/worst days cluster; Kitces buffer-zone research finds the drag usually dominates). The justification is drawdown control and margin headroom only.

**Conditionality — unresolved.** The research stated this value is conditional on two inputs only James holds:
- **(a) Drawdown tolerance** — if genuinely low, move toward 10%.
- **(b) Near-term non-portfolio liquidity calls** — if material calls are foreseeable within ~3 years, move to 10%+.

Neither input has been stated. **7.5% is ratified as the working value; the record notes it was set without (a) or (b) being supplied.** Amend if either changes the picture.

### 1.3 D2 — Leverage cap, 0%

**Decision:** 0% gross LVR. The sizer will never propose a borrowed position. All positions funded from held capital.

**Reasoning (one sentence):** Leverage multiplies edge, and there is currently no measured edge of any kind to multiply — Model A's was measured and found absent (rule #11), and the layer that would measure human judgement does not yet exist.

**Supporting reasoning:**

1. **No measured edge.** Model A: +0.032 / −0.030 correlation across 19,032 matured signals. Quarantined. Human-judgement calibration is Slice 5, blocked on Slice 4 (outcome-materialisation rebuild). The honest prior on an unmeasured edge is zero, and borrowing against zero amplifies variance only.
2. **Controls do not yet run.** The sizer is dormant, `decision_engine` has no persistence, and the D1 cash floor is a number in a document rather than an enforced constraint. Enabling leverage before the machinery that governs it exists inverts the intended order — particularly for a system whose purpose is discipline scaffolding.
3. **Thin spread, full downside.** After-tax cost of margin at 47% ≈ 5.17%; after-tax equity return ≈ 7–8%. A 2–3 point expected spread against full amplification of a 0.8+ correlated drawdown. Deductibility also weakens on a growth-tilted book: no assessable dividends, no deduction.

**What this does NOT rest on:** drawdown tolerance or liquidity calls (inputs (a) and (b), §1.1). The correlation problem is a property of portfolio construction, not temperament — it does not improve with a higher risk appetite. This is why D2 could be settled while those inputs remain outstanding, and D1 could not.

**Reversibility:** 0% costs nothing to set now and can be revisited. Taking on leverage before controls exist is materially harder to unwind.

**Revisit conditions — all three required:**
1. Slices 1–3 shipped, sizer live and demonstrably enforcing the 7.5% cash floor
2. A calibration record showing measured edge — Brier meaningfully better than 0.25 across enough resolved theses to be non-noise
3. A genuinely lower-correlation book (the 30% sector cap alone does not deliver this)

If all three hold, revisit at **≤30% starting LVR via NAB Equity Builder only** (principal-and-interest, no margin calls). Never a margin-callable facility. At a 7.5% cash floor, 30% gross behaves as ~22.5% net, surviving a ~70% fall.

**Standing caveat:** this is analysis against the stated mandate, not licensed financial advice. Any future decision to gear a real portfolio warrants review by a licensed adviser with sight of the full position.

### 1.4 D12 — Challenge mechanism

**Decision:** two layers. Deterministic rules run as **code**, not as an LLM executing a checklist. A bounded LLM agent handles only the judgement-dependent parts, and every finding it produces must carry ≥1 `evidence_id` or a deterministic signal id.

**Refinement of the original instruction.** The stated preference was for the rule set to be "run by an agent." The evidence argues against that specific arrangement: an LLM executing deterministic checks loses reproducibility (the same thesis can yield different findings on different runs) and inherits documented LLM-as-judge biases — position, verbosity, self-preference, sycophancy. The rules are code; the *agent orchestrates them* and owns the parts that genuinely need judgement. That preserves the intent while keeping the mechanical layer deterministic.

**Layer 1 — deterministic (code). Owns most `blocking` findings.**
Mechanically checkable: position cap, GICS sector ≤30% pro-forma, gross leverage = 0%, no derivatives/shorting, 7.5% cash floor post-trade, data staleness, thesis age without revisit, invalidation-condition field populated, implied CAGR/multiple computed from the target price, liquidity (ADV vs intended size, spread, days-to-exit).

**Layer 2 — LLM agent. Three bounded jobs, nothing else.**
1. Construct `strongest_bear_case` (a genuine steelman — the contract already requires it, `min_length=1`).
2. Outside-view pass: restate the target price as an implied claim and flag deviation from a reference class. **Until Slice 4 exists, it may only flag the *absence* of any base-rate justification — never assert a base rate**, because any rate it produced would be fabricated.
3. Test each invalidation condition for **falsifiability** (field-populated is mechanical; falsifiable is judgement).

**Why the LLM is bounded this tightly:**
- **Nemeth, Brown & Rogers (2001):** assigned devil's advocacy is markedly weaker than authentic dissent and can trigger *defensive bolstering* — the challenged party generates more reasons it was right. An LLM is intrinsically an assigned advocate, so its value cannot come from rhetorical force. It must come from evidence that can't be argued with.
- **Huang et al. (2023), Kamoi et al. (2024 TACL):** LLMs cannot reliably self-correct reasoning without external feedback; many positive results relied on oracle labels or weak baselines.
- **Khan et al. (2024 ICML):** adversarial structure raised judge accuracy only under information asymmetry with a verified-quote tool. A persuasive *single advocate* made judges **worse**.

**Diagnosticity is the governing test.** A challenge is informative only if it is more likely to fire on a bad thesis than a good one. A free-form objection fires on everything — likelihood ratio ≈ 1, posterior unchanged, however plausible it reads. The contract's `evidence_ids` `min_length=1` already makes an unevidenced finding unconstructable; that is the single most valuable primitive already in the spec.

### 1.5 D13 — Challenge visibility (hybrid)

**Decision:** the challenger sees the position, the data and the falsifiable claims for the **outside-view pass**, but not the author's persuasive narrative. It sees the full argument for the **steelman pass**.

**Reasoning.** The blind instinct was right about the risk it targets — anchoring — but the evidence says apply it where anchoring actually bites. Peer-review RCTs (Godlee et al. 1998 JAMA; van Rooyen et al. 1999 BMJ) found blinding reviewers to author identity did *not* significantly improve review quality, so blindness is not a general-purpose objectivity lever. Intelligence-community practice (CIA Red Cell, IDF *Ipcha Mistabra*) favours **independent reconstruction** over critique-of-a-presented-argument, which is exactly what the outside-view pass is. The steelman, by contrast, requires understanding the argument to strengthen it — blinding it would be self-defeating.

Note the contract already hard-codes `independent_of_author: Literal[True]`. That is *a different agent*, which is not the same property as *blind to the author's reasoning*. D13 sets the second.

**Confidence: Medium.** This is a reasoned synthesis across peer review and IC practice, not a configuration directly tested on investment theses.

### 1.6 D14 — Severity thresholds

**`blocking` = breach of a decision already ratified in §1, or a certain data-integrity failure. Nothing else earns it.**

This resolves the threshold question more cleanly than a risk-appetite dial. The blocking tier does not impose *new* restrictions — it enforces constraints already set: gross leverage 0% (D2), 7.5% cash floor (D1), 30% sector cap (D8), position cap, no derivatives/shorting. Every blocking finding is therefore objective, reproducible, and traceable to a decision made deliberately and calmly. It cannot be argued with in the moment, because it was set outside the moment.

- **`material`** — a diagnostic concern with cited evidence requiring a `required_response`, but not mechanically forbidding the trade: outside-view deviation, unfalsifiable invalidation condition, correlation above threshold, valuation at an extreme percentile.
- **`monitor`** — real but not actionable now: thesis-age clock approaching, liquidity thinning. Deliberately cheap, so the tiers above stay rare and credible.

**Why blocking stays narrow — alarm fatigue.** The Joint Commission estimates 85–99% of clinical alarms are non-actionable; Bonafide et al. (2015) observed 5,070 alarms over 210 hours with 87.1% of PICU and 99.0% of ward alarms non-actionable, and response time degraded measurably as non-actionable alarms accumulated. A gate that fires often gets overridden reflexively, and then it protects nothing. **A high risk appetite is an argument for a challenger with real teeth, not a looser one** — but teeth means precision, not volume.

**Calibration:** log every finding, its severity, and the disposition (accept/override) from day one. Override rate on `blocking` is the primary health metric. If it exceeds a small fraction, the thresholds are wrong and tighten; if the challenger never fires on an eventual loser, they are too loose.

### 1.7 D4 — Validation bar for any Model A successor

**All eight required. Pre-register 1–4 in writing before any backtest is run.** Rule #11 is not lifted until every one is met and the evidence is recorded in this file.

1. **Economic hypothesis first** — why the edge should exist and why it should persist, written before any data is touched.
2. **Point-in-time data only** — no look-ahead. Already supported (`rs_fundamentals_pit`, price revisions).
3. **Survivorship-clean** — delisted securities included. Already supported.
4. **Purged / combinatorial-purged walk-forward** — standard k-fold CV violates time-series dependence (López de Prado). Parameters locked before the out-of-sample window; a genuine single-use lockbox.
5. **Multiple-testing correction** — report the **deflated Sharpe ratio** (Bailey & López de Prado 2014) and the **probability of backtest overfitting** (Bailey et al. 2017). **Log the number of trials attempted** — an unreported trial count invalidates the DSR.
6. **t-statistic > 3.0**, not 2.0 (Harvey, Liu & Zhu 2016: 316 factors catalogued; "most claimed research findings in financial economics are likely false").
7. **Beat the incumbent** — must materially outperform the deterministic factor-tilt baseline **net of costs**, not merely beat zero.
8. **Pre-committed kill criteria and live decay monitoring** — a state and a date, set before deployment. McLean & Pontiff (2016): predictor returns decline ~26% out-of-sample and ~58% post-publication.

Scored on the same `signal_outcomes` basis Model A faced (correlation of predicted vs realised 5-day and 21-day return) — which requires Slice 4, since the writer no longer exists (§3.3).

**A `research` ticket proposing a successor that ships code has failed its own definition of done (§10.3).**

### 1.2 D7 — Migrations permission

**Reasoning:** the control was mis-layered. `Edit(/migrations/**)` blocked *authoring* a `.sql` file, which is inert — nothing auto-applies migrations. The real gate is the allow-list, which grants only `mcp__supabase-ro__execute_sql` and does **not** grant `apply_migration` or read-write `execute_sql`. The only dispatchable workflow touching migrations, `migration-integration.yml`, runs against an ephemeral `postgres:17` service container, never production.

**What did not change:** the allow-list. The apply gate stands.

**Executed by:** Cursor, not Claude Code — an agent must not edit its own permission surface. James is the governor making the decision; Cursor is the hands, and gains nothing from the change.

---

### 1.8 D15 — C1, the paper book

**Ruled by James, 2026-09-07.** 25,000.000000 AUD at 100% cash, its own snapshot id, flagged paper so no live-book query can read it.

**Why it exists.** The live book's cash is **0.00** [measured, 2026-09-07], so `rule_cash_floor` (`challenge/rules.py:229`) blocks every proposal at the D1 floor and `headroom_max_pct` (`sizer.py:112`) clamps every size to zero. No calibration changes that. The sizing gates therefore cannot be exercised against the live book at all, and an evidence-positive case cannot be distinguished from an evidence-negative one — both end in a zero size. C1 is the book on which a 10% position produces a real, non-zero answer.

**What it is not.** It is not capital, not an intent to deploy, and not a claim that any position should be taken. A case built against C1 is a paper case; the execution boundary (P6) is untouched.

**Implementation — `migrations/0053_paper_book_snapshots.sql`, drafted 2026-09-07, NOT YET APPLIED.**

- **A separate table, not a `book` flag on `portfolio_daily_snapshots`.** With a flag, invisibility becomes a property of every SELECT ever written against that table, and one forgotten `WHERE book = 'live'` mixes paper money into the live cash floor, the sizer's headroom and the brief. Separate tables make it structural: a live query cannot read the paper book because it does not name it. The cost is a second loader; the benefit is that the failure mode requires an act of commission rather than an omission.
- **`asxos/domain/decision_engine/paper_book.py` is the only module that queries it**, and it queries no live table. Two tests hold that line: `test_no_module_issues_sql_against_both_books` and `test_exactly_one_module_queries_the_paper_book`.
- **Append-only** (`BEFORE UPDATE OR DELETE`), like the 13 decision/research tables — a paper book editable after a case was challenged against it is not evidence of anything.
- **CHECK constraints** pin `book = 'paper'`, that the book balances (`capital = holdings_mv + cash`), and that a book with no holdings is all cash.
- **`asx decision build --paper-book <snapshot_id>`** challenges against it. One book or the other, never a blend.

**Measured consequence:** on C1 a 10% position leaves 90% post-trade cash and clears D1; 95% is still blocked; the boundary is exact to the millionth (92.500000 passes, 92.500001 breaches). The register value is unchanged — the paper book relaxes the *balance*, never D1.

**Fixture rows — ruled 2026-09-07.** The theme and candidate rows written for the first positive control are **listable and inert, not removable**. `theme_versions` and `candidate_snapshots` are append-only (`migrations/0051_theme_candidates.sql:61-62`, `:93-94`) and that ratified guarantee stands: a delete path scoped to fixture ids is still a delete path. The rows are the audit trail of the first positive control and are retained as such.

- **Marked** by an `f-e2e-` prefix on `theme_version_id` and `candidate_id` (`asx candidates build --fixture`). The prefix sits inside the id and the id sits inside the content hash, so a fixture row is a *different identity*, not a production row wearing a label.
- **`data_mode` stays `'real'`** — the data is live; only the purpose is fixture. `test_fixture_prefix_changes_identity_not_data_mode` fails if the flag ever assigns `data_mode`.
- **Listing query of record:**
  ```sql
  SELECT 'theme_versions' AS table_name, theme_version_id AS id, theme_code AS subject,
         as_of, data_mode, created_at
  FROM theme_versions WHERE theme_version_id LIKE 'f-e2e-%'
  UNION ALL
  SELECT 'candidate_snapshots', candidate_id, symbol, as_of, data_mode, created_at
  FROM candidate_snapshots WHERE candidate_id LIKE 'f-e2e-%'
  ORDER BY table_name, id;
  ```
- **Inertness is tested, not asserted:** `tests/test_fixture_rows_f_e2e.py::test_no_live_book_aggregation_reads_fixture_rows` checks that none of the five live-book aggregation queries (`SQL_SNAPSHOT`, `SQL_HOLDINGS`, `SQL_CLOSE`, `SQL_FX`, `SQL_PROFILE`) reads `theme_versions`, `candidate_snapshots` or `paper_book_snapshots`; a companion test refuses any future migration that adds a `DELETE FROM` or drops the append-only trigger on either table.

**Applying 0053 is a production write and is not yet granted.** The standing I5 grant of 2026-09-07 covers only `asx candidates build --persist` for the F-E2E run. Recorded in `schema_drift.EXPECTED_UNAPPLIED` so drift detection stays honest until it is applied.

---

### 1.9 D16 — Arbi may author and approve a thesis, paper book only

**Ruled by James, 2026-09-08.** Arbi may author, evidence, price, challenge **and approve** an investment thesis without human review, scoped to a thesis whose only sizing surface is the C1 paper book (D15). The human transition is execution, and execution is not in scope here at all.

**What made this necessary — measured 2026-09-08.** The system has never had an accepted thesis:

| | |
|---|---|
| `theses` rows | 13 |
| `governance_status = 'approved'` | 13 |
| `governance_events` where `object_type='thesis'` | **0** |
| `theses.source_run_id` non-null | **0** |
| `thesis_evidence` rows | **0** |
| `conviction_level` non-null | **0** |

Every one of the 13 carries `approved` from the migration-0033 column `DEFAULT`, never from a decision. Eleven were bulk-opened on 2026-06-24 with a zero-width entry band, NULL stop/target/timeline and a `thesis_text` of exactly 201 characters — identical boilerplate across all eleven. The one `active` row (HUBS, #2) carries a stop of 230 above an entry band of 185–190, which is incoherent for a long. `approve_object()` and `reject_object()` are dead code against every existing row: both require a source state nothing in the codebase can produce.

**Scope, exactly.**

- **Granted:** author a thesis from a reproducible valuation run; write its evidence; set its entry band, stop, target, timeline and conviction; run it through the deterministic challenge layer; and perform all three governance transitions — `draft → evidence_complete → pending_review → approved`, **all with `actor='agent'`**.
- **Not granted, unchanged:** P6 execution. `portfolio-manager-charter.md:70` — *"There is **no P-tier, and no tool, that lets arbi act on its own recommendation.**"* — **stands unamended for live capital.** This decision does not touch it; it carves a paper-only exception beneath it.
- **Not granted, unchanged:** P3 sizing. `arbi-permission-model.md:169` records target weights and sizing as *"not granted yet — draft-only"*, and this ruling does not change that. The run emits a **value range** and a thesis. It never emits a target weight.

**Relationship to §3.6.** §3.6 ("The agent-output evidence base — constrains the approval model") concludes that *"the existing L1/L2/L3 tiering is the right defence and should be **tightened** as models improve, not relaxed."* This decision relaxes the approval tier, and the two are reconciled **only by the scope limit**: the surface is a paper book holding no capital, where an agent-approved thesis cannot move a dollar. Extending this grant to a live book would contradict §3.6 directly and requires a separate, co-ordinated amendment across `portfolio-manager-charter.md`, `portfolio-policy.md` and `arbi-permission-model.md` §Portfolio ladder — the charter's own amendment clause (`:116-120`) requires all three in one change.

**Why the approval sits with the agent and not with James.** The measurement this exists to produce is the S0 agreement rate. If James performs the approval, the metric records his override rate on a proposal instead — a different measurement. His datapoint is the **disposition** of the resulting decision packet, downstream of approval.

**Consequence if it cannot be implemented.** `theses/service.py:803-828` does not currently forward an `actor` to `apply_governance_transition`, so every thesis transition would record `actor='human'` by default. If the approval path cannot record an agent actor, the work **stops and reports** rather than routing the approval to James — a human-actor row would silently misdescribe who decided.

---

## 2. Target-state process

Stage-gated pipeline, idea to exit to learning loop. Annotation: `[EXISTS]` / `[DORMANT]` / `[PARTIAL]` / `[BUILD]`.

| # | Stage | Module | Status |
|---|---|---|---|
| 0 | Universe & context | ingestion, market context | `[EXISTS]` — survivorship-free ~1,873 symbols, PIT fundamentals, price revisions |
| 1 | Idea sourcing | — | `[BUILD]` — no structured intake; variant perception not captured |
| 2 | Screen / triage | `screening`, `research/factor_scores`, `regime` | `[EXISTS]` |
| 3 | Research dossier & thesis | `domain/theses` | `[EXISTS]` — strong; missing pre-mortem field and probability-weighted scenario tree |
| 4 | Forecast layer | — | `[BUILD]` — replaces Model A with calibrated human probabilities |
| 5 | **Decision gate** | `domain/decision_engine` | `[PARTIAL]` — **contracts complete, no persistence, no builder. The missing spine.** |
| 6 | Deterministic sizing | `domain/portfolio` allocator | `[DORMANT]` — inverse-vol sizer, dormant because it sat downstream of Model A |
| 7 | Order staging | — | `[BUILD]` — size, limit, tax-lot selection to the broker's door |
| 8 | Monitoring | `position_monitor`, `macro_theses`, thesis invalidation | `[EXISTS]` |
| 9 | Exit | `theses` + `tax` | `[PARTIAL]` — needs CGT-aware timing incl. the 1 Jul 2027 split |
| 10 | Learning loop | `results_review`, `journal`, `signal_outcomes` | `[PARTIAL]` — reader side works, **writer is gone** (§3.3) |

**The shape of the problem:** stages 0–3 and 8 are genuinely strong. Stage 5 is a fully specified contract with nothing behind it. Everything upstream currently terminates at a human with no structured hand-off.

---

## 3. Established facts

Verified against the codebase. These constrain every decision above.

### 3.1 The architecture spec already exists as code

`asxos/domain/decision_engine/types.py` (31 KB) is an **executable specification**, not a stub. Contract chain:

```
EvidencePacket → ThesisVersion → ChallengeResult → PortfolioAssessment
              → DecisionPacket → DecisionCase → DecisionBrief
```

All content-addressed via `_canonical_digest` / `verify_content_hash`.

**Do not write a prose architecture document for this layer.** It would be a lower-fidelity restatement of something that already type-checks.

### 3.2 Governance constraints are enforced by the type system, not by prose

This corrects the audit (§6). Enforced in `DecisionPacket`:

- `model_independence: Literal[True]` — a non-model-independent packet is unconstructable
- `_MODEL_A_RE` in the manifest validator → *"Model A and v1_5 are quarantined from the decision basis"*. **Rule #11 is enforced in code.**
- Action states require `tax_assessment_reference.readiness == "pass"`
- Non-action states require `size_range.maximum_pct == 0`
- Non-empty `missing_or_uncertain_inputs` makes an action state unconstructable
- Expiry pinned to the trading calendar (5 or 21 trading days); event-driven expiry must be strictly earlier than default

### 3.3 `signal_outcomes` is frozen, not live

- 60,072 rows; 32,769 matured at 21d
- **Nothing writes to it.** No INSERT/UPDATE anywhere in `asxos/`, `jobs/`, `scripts/`. No workflow reference. PR #144 retired the training chain and took the writer with it.
- Five readers: `alpha_loader.py`, `pit_db.py`, `product_health.py`, `alpha_eval.py`, one test
- Created ad-hoc by the now-deleted `jobs/track_signal_outcomes.py` — origin unreproducible from the repo
- Backup coverage: a **one-time** hashed export (`signal-evidence-2026-08-16/`), explicitly noted at line 43 of the backup script as "nowhere else mentioned in this script." **Not in the daily `--table=` list.**

**Consequence:** rule #11's evidentiary basis sits in a frozen table whose creating code is deleted. The verdict is almost certainly right; the input cannot currently be reproduced.

### 3.4 Model A verdict

LightGBM v1_5, evaluated against 19,032 matured signals (Dec 2025 – Mar 2026): correlation of `ml_prob` vs actual 5-day return **+0.032**, vs 21-day **−0.030**. No usable edge. Quarantined under rule #11; finding survived re-testing.

This was correct and honest work. It is also the standard any successor must meet (D4).

### 3.6 The agent-output evidence base (constrains the approval model)

Load-bearing for keeping L2/L3 gates tight. All cautionary, all from 2025–26:

- **METR RCT** (arXiv 2507.09089, Jul 2025): 16 developers, 246 tasks. Developers forecast AI would cut completion time 24%; measured result was a **19% increase**. METR's Feb 2026 follow-up estimates ~18% *speedup* on late-2025 tooling, so the gap is closing — but the instruction stands: measure it in your own context rather than assuming.
- **CodeRabbit** (Dec 2025, 470 PRs): AI-coauthored PRs averaged **10.83 issues vs 6.45** for human PRs (~1.7×); logic/correctness 1.75×, security 1.57×.
- **GitClear** (211M changed lines, 2020–24): code churn — rewritten or deleted within two weeks — nearly doubled from 3.1% to 5.7%; refactoring fell from ~25% toward under 10%; duplicated code exceeded moved code for the first time.
- **SlopCodeBench** (2026): no agent solved any problem end-to-end across 11 models; structural erosion in ~80% of trajectories.
- **Kiro / AWS** (Dec 2025): an agent given broad permissions chose to delete and recreate an environment, causing a ~13-hour outage.

**Implication:** the existing L1/L2/L3 tiering is the right defence and should be *tightened* as models improve, not relaxed. It also argues for a Definition-of-Ready gate on agent-opened tickets, so agents cannot flood the backlog with items that were never work.

### 3.5 Schema state

> **Rewritten 2026-09-02 (campaign node H1-F). Every line of the 2026-08-23 version had gone
> stale**, because it described the world Slice 0 was about to change and was then not revisited
> after Slice 0 merged. Corrections row 6 records what it said. The rule this section now
> follows: **state the mechanism, not the counts** — a document that restates a live number goes
> stale by construction, which is the same lesson `docs/next-session-kickoff.md` has now learned
> three times.

- **Drift detection is a migration-*name* set difference** (`asxos/schema_drift.py`, imported by
  `asxos/api/main.py`), with a **directional** allowlist: entries assert *expected-unapplied* and
  fail if later applied, so exceptions self-expire. Shipped 2026-08-23.
- **`REQUIRED_MIGRATIONS` is deleted.** The old guard was `count < REQUIRED_MIGRATIONS`, a count
  comparison that cannot detect extras by construction. No count is maintained anywhere; do not
  reintroduce one.
- **`0018_perf_indexes` was reconstructed** from `pg_get_indexdef()` and is in the repo (Slice 0,
  #163). The "no file in the repo" gap is closed.
- **`0025` and `0045` are deliberately unapplied**; `0042` is RESERVED by parked PR #80 and must
  never be applied. So the on-disk file set, the ledger set, and the allowlist are three
  different sets *by design* — a divergence is not automatically a defect.
- For the live picture, read `supabase_migrations.schema_migrations` and the on-disk
  `migrations/` directory. Neither number is restated here.

---

## 4. Corrections log

Recording what earlier analysis got wrong. This section exists because a decision record that only accumulates confident claims becomes untrustworthy.

| Date | Claim | Correction |
|---|---|---|
| 2026-08-23 | Audit: "the s766B firewall and sizer-provenance constraints are prose-only, zero code references" | **Wrong.** Enforced in `types.py` under different names — `model_independence`, `_MODEL_A_RE`, `ACTION_STATES`/`NON_ACTION_STATES`, `SizeRange`. The grep used the wrong terms. The recommended sizer-provenance test is partly redundant. |
| 2026-08-23 | Roadmap: "wire calibration scoring using the existing `signal_outcomes` infrastructure" | **Incomplete.** Reader side exists and is good; **writer does not exist**. Phase 2 has an unbudgeted prerequisite: rebuild the outcome-materialisation job first. |
| 2026-08-23 | Permission analysis conflated "James lifts the deny" with "the agent lifts its own deny" | These are different. The second is the anti-pattern; the first is the governor exercising authority. The objection to option 1 was about permanence and drift, not principle. |
| 2026-08-23 | `signal_outcomes` "is not backed up" | **Imprecise.** A one-time hashed export exists (2026-08-16). It is absent from the *recurring* dump. |
| 2026-08-23 | §0 and the bundle README: "`docs/product/` sits in `AUTHORITY_FRAGMENTS`" | **Wrong.** `.claude/hooks/authority-guard.sh:60-76` enumerates individual `docs/product/*.md` files plus `docs/product/rubrics/`; there is no directory-prefix entry for `docs/product/`, and the deny array in `.claude/settings.json` mirrors that same file list. This record is therefore **unguarded** as committed — arbi can edit it directly — and it is absent from `CODEOWNERS`. The governor-owned property claimed for it does not hold until both lists name the path. |
| 2026-09-02 | §3.5 "Schema state" as written 2026-08-23: "43 migration files in repo; **97 applied**"; "`0018_perf_indexes` … reconstruction in progress"; "Being replaced by a name-set diff" | **Every line stale, and stale in the same direction: it described the world Slice 0 was about to change, and was not revisited when Slice 0 merged (#163).** By 2026-09-02: 47 files on disk through `0048`; latest applied ledger version `20260901062502`; `0018` reconstructed and in-repo; the name-set diff shipped 2026-08-23 and `REQUIRED_MIGRATIONS` was deleted, so "being replaced" describes a completed migration and a constant that no longer exists. §3.5 is rewritten to state the *mechanism* and cite no counts — the counts are what rotted. |
| 2026-09-02 | §6 Slice 0 and §4's backup row: "plus `signal_outcomes` and `signals` into the daily backup table list" (`:353`, `:467`) | **Contradicts the backup design and must not be executed literally.** `scripts/backup_irreplaceable.sh:33-48,127-130` deliberately excludes both: they stopped changing when P1-02 deleted their writers, so a daily dump would commit ~124k identical rows into the backup repo forever. They were captured once instead, as the hashed `signal-evidence-2026-08-16/` archive, and the script *asserts* that capture still exists. Anyone following the ADR literally reintroduces exactly what the current design avoids. The real Slice 0 gap was that nothing verified the archive — closed 2026-08-23 by the assertion, which then caused its own 12-run outage (see campaign node H0-B). Slice 0 is otherwise **DONE**; §6's "(in flight)" label is also stale. |

---

## 5. Open decisions

### 5.1 ~~D2 — Leverage cap~~ — CLOSED

Ratified 2026-08-23 at 0%. See §1.3. Supporting arithmetic retained there.

### 5.2 ~~Challenge threshold~~ — CLOSED

Ratified 2026-08-23. Mechanism D12 (§1.4), visibility D13 (§1.5), thresholds D14 (§1.6).

### 5.4 D10 — Work-management substrate — RATIFIED: GitHub Issues

**Decision:** GitHub Issues as the system of record for actionable work, with a Projects v2 board for state. Not Backlog.md. This supersedes audit R1's phrasing while keeping its requirement: *state must be structured and queryable, never prose.*

**Decisive evidence — the permission surface.** `npm`, `npx`, `bun` and `node` are **entirely absent** from `permissions.allow`. Adopting Backlog.md would mean permitting a JavaScript toolchain in a Python repo, adding a writable MCP server, and allow-listing its commands — a material expansion of the surface tightened under D7. GitHub Issues needs roughly four additions: `gh issue create/list/view/edit`. Read-mostly, no new runtime, no new MCP.

**Second decisive factor — a known defect in a class already encountered.** `tests/test_hook_worktree_scope.py` exists because `push-guard.sh` and `unattended-guard.sh` anchored path lookups to `$CLAUDE_PROJECT_DIR` rather than the tool call's checkout, so calls inside a worktree "silently failed open." Backlog.md's documented limitation is that its MCP server writes to the main repo rather than the current worktree. Same class of bug, and `claude/**` worktrees plus a separate Cursor checkout are in active use.

**What Backlog.md was right about, recorded honestly:** in-repo state is genuinely better in principle. "One task = one context window = one PR" matches D6 exactly and is adopted regardless of substrate. The rejection is about this repo's permission surface and worktree topology, not about the tool's design.

**Accepted cost:** state lives off-repo. Clone the repo in five years and tickets are absent.
**Mitigation (required, not optional):** a periodic `gh issue list --json` export committed to the repo. Without it this reproduces the §3.3 failure — evidence the repo cannot reproduce from itself.

**Prerequisite:** add `gh issue create/list/view/edit` to `permissions.allow`. Same governance path as D7 — James edits the permission surface, not the agent.

### 5.5 D11 — Ticket schema and three work types — RATIFIED

Full spec at **§10.3**. Three trims applied to the researched proposal:

1. **`horizon` dropped as a label** — duplicates the Projects board column. Two sources of truth for one fact is the failure the audit diagnosed.
2. **Three types kept, not folded to two.** `data-infra` earns separation: migrations are L3, and schema drift caused four of six production bugs in one sprint. A template forcing migration-first ordering and a drift-check box attacks the documented top failure mode directly.
3. **Definition of Ready promoted to load-bearing.** The researched proposal underplayed it. It is the gate that stops agent-opened tickets flooding the backlog, and per §3.6 an agent that can open issues freely will. It applies to agent-opened tickets **without exception**.

**The `research` shape is the one that matters.** Its definition of done is *a decision or an ADR, never shipped code* — that is what stops an experiment quietly becoming a build. Its pre-registration block is D4 (§1.7) made structural rather than remembered. A research ticket that ships code has failed its own definition of done.

**Prioritisation:** value/effort gut-call, plus Shape Up *appetite* (time it is worth, decided up front) and *circuit breaker* (blowing the timebox kills the item; no automatic extension). RICE/ICE/WSJF dropped — Reach is meaningless at N=1 and the arithmetic is false precision over guesses.

### 5.3 Delegable to arbi

Per `arbi-constitution.md` §"What arbi is authoritative for", its decision stands unless overridden:

| Decision | Basis |
|---|---|
| What populates `EvidencePacket` | Verbatim arbi authority: *"what evidence counts as current truth"* |
| Persistence shape (append-only vs updatable) | Engineering shape. Note the contract already implies immutable-with-supersession via `ContentAddressedContract` + `supersedes_packet_id` |
| ~~`ChallengeResult` mechanism~~ | **Closed** — D12/D13/D14 settled it. What remains delegable is the *implementation* of the Layer 1 rules, not their design. |

**Constraint when dispatching:** deliverable is a **scaffold PR** — migration DDL, repository module, failing tests. Not a proposal. Reject a document as non-delivery. Verify arbi is operating first; `arbi-run-ledger.md` carries a self-recorded `KNOWN COVERAGE GAP` on its own core invariant.

---

## 6. Build sequence

Vertical slices. Each ends in a merged PR that works end-to-end, however narrow. Definition of done is the test list, not a document section.

**Slice 0 — audit remediation** (in flight)
Six commits: timezone pin, migration name-diff check + CI, restore-drill schedule, header strip, alert observability, `0018` reconstruction. Plus `signal_outcomes` and `signals` into the daily backup table list.

**Slice 1 — decision spine**
> **Prerequisite, currently undecided:** a `DecisionPacket` requires an `evidence_packet_id`, and what populates `EvidencePacket` is delegated to arbi (§5.3) but not yet settled. Either settle it first, or scope Slice 1 to a minimal `EvidencePacket` (thesis + current price + portfolio state) and widen later. Do not let an agent invent the evidence contract mid-build.

Migration creating `decision_packets` and upstream contract tables, DDL matching the pydantic field constraints. Repository module: `save` / `load` / `supersede`. Builder composing a real `DecisionPacket` from live thesis + portfolio + tax data instead of `build_demo_brief` fixtures.
*Done when:* round-trip fidelity holds, `verify_content_hash` passes after load, every validator in §3.2 still raises, and one real thesis produces one real persisted packet.

**Slice 2 — reactivate the sizer**
Inverse-vol sizer feeding `SizeRange`, downstream of the decision gate rather than of Model A. Cash floor 7.5% enforced, gross leverage pinned at 0% (D2). No longer blocked.

**Slice 2.5 — thin challenge layer**
Layer 1 deterministic rules in code (D12). LLM steelman + falsifiability pass with mandatory evidence citation. Finding/disposition log from day one — it is the only calibration signal available before Slice 4. Outside-view pass ships flagging *absence* of base-rate justification only.
*Done when:* a thesis breaching any ratified register decision cannot produce `outcome="pass"`, and every LLM finding carries an evidence id.

**Slice 3 — order staging**
Size, limit price, tax-lot selection via the tax module. Staged to the broker's door. No autonomous execution.

**Slice 4 — outcome materialisation rebuild**
Replace the deleted `track_signal_outcomes.py`. Prerequisite for anything measuring forecasts.

**Slice 5 — calibration layer + base-rate challenge**
Thesis records capture base rate, probability-weighted scenario tree, conviction, specific invalidation conditions, pre-mortem. Brier scoring and calibration curve wired into `results_review`. Unblocks the outside-view pass in Slice 2.5 to assert base rates rather than only flag their absence. Depends on Slice 4.

---

## 7. Anti-scope

Explicitly not building:

- **A new ML forecasting engine** — until D4's bar is met
- **Autonomous execution** — forbidden; human-in-the-loop permanently (the P4→P6 gap)
- **Derivatives, shorting, structured products, capital-protected loans** — out of mandate
- **Intraday execution optimisation / smart order routing** — irrelevant for long-only with manual approval
- **Prime-broker or borrow infrastructure**
- **Large-team performance attribution** — the `benchmark` module suffices
- **Sprint ceremony** — no coordination benefit for one operator; it is the instinct that produced eight backlogs
- **A prose architecture document for `decision_engine`** — `types.py` is the spec
- **A free-form "find problems with this thesis" LLM prompt** — fires on everything, likelihood ratio ≈ 1, pure theatre
- **An LLM that self-scores confidence or self-corrects unaided** — contradicted by Huang et al. and Kamoi et al.
- **Any base-rate challenge before Slice 4** — the rate would be fabricated
- **A multi-agent debate rig** — Khan et al.'s gains needed information asymmetry and a verified-quote tool; unjustified overhead at 5–10 hrs/week
- **Reinstating Model A as the adversary** — it was measured and has no edge; resurrecting it would be false authority
- **Further doc-truth reconciliation sweeps** — `doc-truth-map` gets deleted, not updated
- **Story points and velocity** — no team to calibrate against
- **RICE / ICE / WSJF scoring** — false precision over guesses at N=1
- **Backlog grooming as ceremony, and a large maintained backlog** — prune aggressively; close anything untouched for a quarter, since important ideas come back
- **MADR or heavyweight ADRs on every ticket** — Nygard's format (Title/Status/Context/Decision/Consequences), reserved for L3 decisions
- **Multi-tool setups** (separate tracker + wiki + roadmap tool) — one in-repo system plus a thin inbox
- **Fully autonomous agent merging beyond L1** — see §3.6; the evidence says tighten these gates as models improve, not loosen them

---

## 8. Evidence index

Research folded into this document. Sources retained for audit; do not maintain these as living documents.

| Topic | Key findings | Confidence |
|---|---|---|
| Cash floor | RBA cash rate 4.35% (11 Aug 2026); best retail ~5.1%; ASX 200 accumulation ~9%/yr trailing decade; CFA IPS liquidity guidance | High on rates, Medium on equity return (period-dependent) |
| Dry powder | Best/worst days cluster; Kitces buffer-zone research finds drag dominates | High that the evidence is weak |
| Margin lending | CommSec buffer 5%, cure by 2pm next business day; NAB variable 9.75%; Equity Builder ~7.75% P&I with no margin calls | High |
| Deductibility | Interest deductible where income-producing purpose; TR 2000/2, TR 95/25; Part IVA on split loans (Hart); capital-protected borrowing interest **not** deductible | High |
| CGT transition | Treasury Laws Amendment (Tax Reform No. 1) Act 2026, Act No. 49, assent 26 Jun 2026. 50% discount → CPI indexation + 30% minimum from 1 Jul 2027; deemed sale/reacquisition just before that date preserves pre-2027 discount | High |
| Challenge design | Nemeth 2001 (assigned < authentic dissent); Schweiger/Sandberg/Ragan 1986; Schwenk 1990 meta-analysis (effect not robust for ill-structured tasks); Janis groupthink weaker than its fame (Park 2000: 2 of 23 predictions confirmed) | High on studies, Medium on transfer to N=1 |
| LLM critique limits | Huang et al. 2023; Kamoi et al. 2024 TACL; Khan et al. 2024 ICML (debate 76%/54%/48%); LLM-as-judge biases | High |
| Alarm fatigue | Joint Commission 85–99% non-actionable; Bonafide et al. 2015 (5,070 alarms, 210 hrs) | High |
| Checklists | Haynes 2009 (death 1.5%→0.8%) vs Urbach 2014 Ontario null replication; read-do vs challenge-response; Duke kill criteria; Klein pre-mortem | High on the mixed record. **The "~30% better risk identification" pre-mortem figure is UNCITABLE** |
| Work management | Now/Next/Later (Bastow); Shape Up appetite + circuit breaker + "no backlog"; INVEST; Given/When/Then as tests; spikes timeboxed not estimated; dual-track discovery/delivery backlogs | High on the frameworks; Medium on transfer to N=1 |
| Agent output quality | METR 19% slowdown RCT; CodeRabbit 1.7× defects; GitClear churn doubling; SlopCodeBench | High — see §3.6 |
| Schema drift playbook | Migration-first commit ordering; never hand-edit production; regenerate-and-diff CI gate; replay full history into a clean DB; expand-contract for renames | High — validates Slice 0 |
| Decision records | Nygard format over MADR; one decision per record; never edit an accepted one, supersede instead; PEP/RFC/KEP as the numbered-status precedent; "decision documentation theatre" as the dominant failure | High |
| Forecasting | Harvey-Liu-Zhu t > 3.0; López de Prado DSR/PBO; McLean-Pontiff post-publication decay ~58%; Tetlock calibration/Brier; AQR "evolutionary not revolutionary" on ML | High |

**Implication of the CGT finding worth carrying forward:** pre-2027 accrued gains retain the 50% discount whenever later sold. There is **no need to realise early** to capture it.

---

## 9. Change log

| Date | Change |
|---|---|
| 2026-08-23 | Document created. D1 ratified (conditional). D3–D9 recorded. Corrections log opened. Cash floor / leverage cap research folded in. |
| 2026-08-23 | Corrected §0: this file IS committed (`docs/product/`), not a throwaway input. Slice 1 prerequisite flagged — `EvidencePacket` population undecided. |
| 2026-08-23 | **D10 ratified: GitHub Issues** (§5.4), superseding audit R1. **D11 ratified** with three trims (§5.5). Issue template files written. |
| 2026-08-23 | §0 artifact register + Claude Code usage added. §10 executable specifications inlined verbatim (Slice 0 prompt, permission lift, issue templates, Layer 1 rules, Slice 1 scaffold). D4 expanded to full eight-criteria bar (§1.7). |
| 2026-08-23 | **Challenge layer closed** — D12 mechanism (§1.4), D13 hybrid visibility (§1.5), D14 severity (§1.6). §5.2 closed. Slice 2.5 added. Anti-scope extended. |
| 2026-08-23 | Work-management research folded in. D10 opened (§5.4) — conflicts with audit R1, stated rather than overwritten. D11 proposed (§5.5). §3.6 added on agent-output evidence. Anti-scope and evidence index extended. |
| 2026-08-23 | **D2 ratified at 0% gross leverage** with three revisit conditions (§1.3). §5.1 closed. Slice 2 unblocked — both structural protections now set. |
| 2026-08-23 | Placed into the repo at this path. Correction #5 added (§4): `docs/product/` is **not** an `AUTHORITY_FRAGMENTS` directory prefix — only enumerated files are — so this record is unguarded as committed. Audit v2 and the work-management research archived alongside. |

---

## 10. Executable specifications (verbatim)

Reproduced in full so nothing is inferred. Paraphrasing anything in this section is a rescope.

### 10.1 Slice 0 — audit remediation prompt

Status: in flight. Six commits on `claude/audit-p0-remediation`.

**Phase 0 — verify (read-only, no writes, no branch).** Settle what static analysis could not:
1. Query `supabase_migrations.schema_migrations` for applied migration **names**. Diff against `ls migrations/*.sql`. Produce three columns: applied-and-in-repo / applied-not-in-repo / in-repo-not-applied.
2. Check header claims for `0038`, `0039`, `0041`, `0043`, `0044`, `0045` against applied reality.
3. Determine what migration `18` was. `42` is reserved by parked PR #80.
4. Confirm `asxos/db.py::init_pool` passes no `server_settings`, and that `settings.asxos_tz` is read by no code path.
5. `gh run list --workflow=backup.yml` — find the last run where the restore drill actually executed.
6. Establish what `as_of` recent `compose_brief` runs used, and whether it matched the intended Sydney trading day.

**Stop. Report as a table. Wait for go-ahead.**

**Phase 1 — six commits, each independently revertable.**
1. `asxos/db.py::init_pool` → `server_settings={'timezone': 'UTC'}`. Converts the hazard documented at `asxos/brief/compose.py:694-698` into an enforced invariant.
2. Replace `if count < REQUIRED_MIGRATIONS` with a **name-set diff failing on asymmetry in either direction**. Delete the hand-maintained integer. Add as its own CI step, not only at app startup. Allowlist entries must assert **expected-unapplied** and fail if the migration is later applied, so exceptions self-expire. Allowlist `0025`, `0045`.
3. `backup.yml` — schedule the restore drill **weekly**, not manual-dispatch-only. Assert row counts on the restored copy. **Add `signal_outcomes` and `signals` to the daily `--table=` list** (currently covered only by the one-time `signal-evidence-2026-08-16` export; the script's own comment at line 43 flags this).
4. Strip DRAFT / NOT APPLIED / PRODUCTION-READY / APPLIED headers from every `migrations/*.sql`.
5. `jobs/validate_price_data.py:59` and `jobs/check_au_positions.py:146` — keep the bare `except: pass` (a notification failure must not crash the job) but record the failure to `job_runs`. **Leave `asxos/jobs/utils/job_monitor.py:189` alone** — correct as written, and its comment explains why.
6. Reconstruct `migrations/0018_perf_indexes.sql` from production `pg_get_indexdef()` output **verbatim**, with a header comment stating it is a reconstruction (date + source query). That is a true claim about provenance, unlike the false state headers being deleted in commit 4.

**Gate:** `make check` green. Open the PR. Do not merge.

**Hard constraints:** read-only DB (every probe a `SELECT`); no migrations applied; **do not touch `asxos/domain/tax/`**, no `Decimal`→`float`, no `NUMERIC` column changes; do not fix the 11 current ruff findings (rules newer than the pinned `ruff==0.7.0`, cosmetic, CI passes); create no new files under `docs/` beyond ≤10 lines in `WHERE-I-STOPPED.md`; if a sixth change appears necessary, stop and ask.

### 10.2 D7 — permission lift (executed)

Executed in Cursor, not Claude Code — an agent must not edit its own permission surface.

1. `.claude/settings.json` — remove `"Edit(/migrations/**)"` from `permissions.deny`. **Do not touch `permissions.allow`.** Diff must be exactly one line.
2. `.claude/hooks/authority-guard.sh` line 64 — `".github/" "migrations/" "docs/product/rubrics/"` → `".github/" "docs/product/rubrics/"`. Feeds both `is_authority_path()` and `_authority_regex_alt()`; removing the element updates both.
3. `tests/test_authority_guard_hook.py` — four cases assert `migrations/` is an authority path (~117, ~254, ~371–372). **Move each to its allowed counterpart rather than deleting it**, so the suite positively asserts `migrations/` is writable. If `test_deny_bash_redirect_to_authority_after_scrub` is left empty, substitute another protected path — it guards a real bypass technique and must not silently stop testing.

**Verification assertion (the whole basis for this being safe):** `[x for x in allow if 'supabase' in x]` must print exactly `['mcp__supabase-ro__execute_sql']`. Anything else, stop.

### 10.3 Issue templates — D11 (ratified)

Three shapes. `approval_tier` is required on all three.

**`product`**
```markdown
type: product
approval_tier: L2        # L1 | L2 | L3
area: [pipeline|ml|db|cli|email|cron|screens]

## Problem / outcome
<one sentence: the problem, and why it matters now>

## Files to touch (expected)
<paths, or "unknown — spike first">

## Acceptance criteria (Given/When/Then)
Given <state> When <action> Then <observable result>

## Out of scope
<explicit no-gos>

## Definition of done
- [ ] `make check` green
- [ ] Conventional commit
- [ ] Acceptance criteria demonstrably met by a test
- [ ] PR merged
```

**`data-infra`** — as above, plus:
```markdown
approval_tier: L3        # migrations are always L3

## Migration ordering
- [ ] Migration commits before the code that depends on it
- [ ] Schema source of truth is the migration, never hand-edited production
- [ ] Drift check passes (name-set diff, zero asymmetry)
- [ ] Expand-contract used for any rename — never rename in place

## Definition of done
- [ ] Migration applied by James (never the agent)
- [ ] `make check` green including migration-integration.yml
- [ ] PR merged
```

**`research`** — a different shape. No acceptance criteria.
```markdown
type: research
approval_tier: L3
timebox: <hours — this is the circuit breaker, not a deadline>

## Question
<what is genuinely unknown>

## Hypothesis (pre-registered — written BEFORE any data is touched)

## Success metric & threshold (decided BEFORE seeing results)

## Falsification condition
<what result would make me abandon this>

## Out of scope

## Definition of done
- [ ] A decision recorded in the ADR, or an ADR written
- [ ] NOT shipped code — a research ticket that ships code has failed
- [ ] If the timebox blew: the item dies and is re-shaped. No automatic extension.
```

**Definition of Ready** — blocks entry to `ready`. Applies to agent-opened tickets **without exception** (§3.6):
1. Framed as a problem or outcome, not a feature
2. `approval_tier` set
3. Files-to-touch listed, or explicitly "unknown — spike first"
4. Acceptance criteria present, or a pre-registration block for `research`
5. Out-of-scope stated
6. `data-infra` only: migration ordering noted

**Labels:** `type` (3), `approval_tier` (3), `area` (7). **No `horizon` label** — it duplicates the board column.
**States:** `backlog → ready → in-progress → in-review → done`, plus `blocked`, `archived`.

### 10.4 Layer 1 challenge rules — D12

Deterministic **code**, not LLM-executed. Runs pro-forma (post-proposed-trade), not on current state.

| Rule | Check | Severity |
|---|---|---|
| Gross leverage | Any borrowing > 0 (D2) | `blocking` |
| Derivatives / shorting | Any instrument outside long-only cash equity | `blocking` |
| Cash floor | Post-trade cash < 7.5% (D1) | `blocking` |
| Sector cap | Post-trade GICS sector > 30% (D8) | `blocking` |
| Position cap | Post-trade single position > cap | `blocking` |
| Data integrity | Decision priced on stale or missing data beyond threshold | `blocking` |
| Data staleness | Price/fundamentals older than N days (below the blocking threshold) | `material` |
| Correlation | Pairwise/cluster correlation above threshold | `material` |
| Valuation percentile | Sector valuation percentile at an extreme | `material` |
| Implied growth | CAGR/multiple implied by target price, computed from history | `material` |
| Invalidation field | `invalidation_conditions` empty | `material` |
| Liquidity | ADV vs intended size, spread, days-to-exit | `material` |
| Thesis age | Days since last revisit approaching threshold | `monitor` |
| Liquidity trend | ADV declining | `monitor` |

Every `blocking` row is enforcement of a decision in §1 — no new restrictions (D14).

**Layer 2 (LLM), three bounded jobs only:**
1. `strongest_bear_case` — genuine steelman. Sees the full argument (D13 informed pass).
2. Outside-view — sees position, data and falsifiable claims only, **not** the author's narrative (D13 blind pass). **Until Slice 4: may flag the absence of base-rate justification, must never assert a base rate.**
3. Falsifiability of each invalidation condition (field-populated is Layer 1; falsifiable is judgement).

Every Layer 2 finding must carry ≥1 `evidence_id` or a Layer 1 signal id. The contract already enforces this (`ChallengeFinding.evidence_ids`, `min_length=1`) — an unevidenced finding is unconstructable.

### 10.5 Slice 1 scaffold — decision spine

**Migration:** `decision_packets` plus upstream contract tables. **DDL must match the pydantic field constraints in `types.py`** — string `max_length`, `NUMERIC(18,6)` for all monetary values, `timestamptz` for every datetime. Append-only with `supersedes_packet_id`, matching `ContentAddressedContract`.

**Repository module:** `save(packet)`, `load(id)`, `supersede(old_id, new)`.

**Builder:** composes a real `DecisionPacket` from live thesis + portfolio + tax data. Replaces `build_demo_brief` fixtures.

**Failing tests that constitute the definition of done:**
- Round-trip fidelity: `save` then `load` returns an identical packet
- `verify_content_hash(loaded)` is True after a DB round-trip
- Every validator in §3.2 still raises: blocking finding with `outcome="pass"`; `as_of` ≠ `knowledge_cutoff.date()`; action state with non-empty `missing_or_uncertain_inputs`; non-action state with `size_range.maximum_pct != 0`; action state with `tax_assessment_reference.readiness != "pass"`; a manifest containing Model A or v1_5
- One real thesis produces one real persisted packet

**Do not:** modify `types.py` to make persistence easier. The contract is the spec; the schema conforms to it, not the reverse.

