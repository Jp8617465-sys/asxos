<!-- Landed from the 2026-09-19 planning session. Source of the ranked build: this file. The 2026-09-18 plan is superseded by it; see its header. -->

# asxos — mandate → sleeves that pick and size → paper book → weekly brief

**Status:** FINAL for approval · **Author:** arbi · 2026-09-19
**Evidence:** `docs/product/capability-atlas-2026-09-18.md` (on branch), three explorer reports, one design pass, every load-bearing claim re-verified live.

---

## Context — why this, why now

James, in his words: *"we get the data from EODHD, we structure said data, follow an investment
model that's dynamic … it continually monitors, builds a brief for each, looks for opportunities to
make money and gives that back to me. We're 9 months in with no trades evaluated. It's sticking to
CBA and HubSpot. We want to build out a portfolio."*

He is right, and the cause is mechanical — **four gates in series, one of them waiting on him:**

| Gate | Where | Effect |
|---|---|---|
| 1. Action state unreachable | `decision_engine/builder.py:251,837` — `derive_state(… calibration=None)`; non-None **raises** `NotImplementedError("C-13")` | every packet is `watch`/`abstain` |
| 2. Calibration is a James ruling | `james-inbox.md` H-32 → `p5-01-risk-calibration-2026-09.md` §6 — **parked since 2026-09-06** | "every packet closes `abstain` by policy" |
| 3. Paper intent needs an action state + accept | `delivery.py:181-188` | no paper position can open |
| 4. **The paper book cannot hold positions** | `paper_book.py:87-93` raises on `holdings_count > 0`: *"no paper holdings ledger exists"* | nowhere to put one |

Self-sealing: calibration needs outcome episodes, which need positions, which need action states,
which need calibration. **D15 (A$25k paper book) and D16 (arbi may approve theses on paper) were
both ruled to break this and neither reached `derive_state`.** The paper book has sat at
A$25,000 / 100 % cash / 0 holdings since 2026-09-07.

**What exists and is reused (verified):** data spine (`prices` 806k rows *from 2025-01-02 only*;
`rs_fundamentals_pit` to 1987 incl. 1,515 delisted; `rs_corporate_actions` 43k); factor engine
`research/factor_scores.py` (value/quality/momentum/low_vol/yield, sector-neutral; composite =
value×quality, *unscheduled*); `alpha_eval.py` (effective-t, decile monotonicity, liquidity split);
decision spine `decision_engine/{builder,challenge,sizer,staging,delivery,outcomes}` incl.
**`StagedOrder` — the brokerage instruction already exists** (qty, limit, notional, CGT lots,
`not_executable=True`); registry `research_hypotheses → strategy_versions → research_runs`
(append-only); reply channel `apply_github_decisions.py` (APPROVE/REJECT/DISPOSE only); V1 brief +
**ten dark V2 collectors**; 20 workflows; 4,725 tests green.

**Defects the build must fix first:** D-1 regime credit arm dead (bps vs %); D-2 ~⅓ of the value
screen is LIC/A-REIT (no `security_kind` backfill); D-3 `tax_settings` empty; D-6 profile caps
unsatisfiable at live capital; **`adj_close` frozen at ingest — 52 symbols, max 1,250× step**;
`portfolio-policy.md:26` names XJOAI (the Buy-Write index) as the accumulation benchmark (it is XJOA).

### Remote sync
Working tree is current to `32f8b83` (#339); real `origin/main` is `56ec1dd` (#341, two docs PRs
later). Local `main` *pointer* is 44 PRs stale — harmless. Unmerged prior work on remote:
`agent/investment-engine-dossier` (PR #70, 40k lines, never merged — its own review found five
defects), the quant benchmarking guide v2, the strategy research pack. Ratified-but-unbuilt:
`segment-valuation-portfolio-architecture-2026-08-18.md` (L4: "never emits a target weight").

### James's rulings, 2026-09-19
| Question | Ruling | Consequence |
|---|---|---|
| Paper output | **Sleeves pick and size** | amends Aug-19 L4 + D16 "never emits a weight" **for paper only**; live book stays memo-only |
| Capital | **"The financial agents should decide, from my income goals and ambitions"** | a **mandate layer** (goals → derivation → memo → ratification); resolves C-13/H-32 by derivation, not eight hand numbers |
| Structure | **"For the finance agents to decide"** | ETF-core vs single-name split is a mandate *output*; ETF core is a first-class sleeve |
| Cadence | **Weekly narrated brief, monthly rebalance** | hold-band rebalancing; discipline flags stay daily |

---

## The shape

Three layers, each parameterised by the one above. **M** turns goals into deployable capital, risk
budget, N, ETF split and sleeve allocations — ratified once. **B** sleeves pick and size inside
those numbers and trade forward on the paper book through the existing challenge → packet →
disposition → intent chain. **A** is the ledger and the one gate that lets a position exist.
**D** is the brief that reaches James's phone with verbs he can answer. Live book: memo-only
throughout; `derive_state`'s live branch is byte-identical.

Constraints honoured: rule #11 (no Model A), D3 (no ML), D4 (no *forecasting* successor reaches
capital — paper is not capital), D12 (LLM only bounded + evidence-cited), `RESPONSE_RULE` (the RI
model still emits no targets; sleeves are a different generator with their own pre-registration),
s766B (`DIRECTIVE_TERMS` ban on brief copy; the sleeves card states positions and quantities, never
"buy"), §2 (every real order is James's).

---

## M. The mandate layer — the first PR

**M-a. Storage — `migrations/0061_mandate.sql` (Amber).** Two append-only tables (0050's
`_forbid_mutation` pattern), both `REVOKE SELECT FROM agent_readonly` (income is not for the RO
agent role), governed by the 0034 trigger with `governance_events.object_type` widened to `'mandate'`:
- `financial_goals` — goal_version_id PK, as_of, investable_assets_aud, income_aud_pa,
  savings_aud_pa, target_wealth_aud, horizon_years, drawdown_tolerance_pct, liquidity_needs JSONB
  `[{due, amount_aud}]`, emergency_months, account_type, marginal_rate, brokerage_aud_per_side,
  stated_by CHECK='james', content_hash.
- `mandates` — mandate_id PK, goal_version_id FK, derivation_version, outputs JSONB, memo_html,
  governance_status draft→pending_review→approved, content_hash.
Why a table not a doc: `sizer.py`, `build_decision_packets.py` and the sleeve job read it nightly;
a row is content-addressed and its ratification is a `governance_events` fact a trigger can check.
`profiles` keeps the **live** book's caps; the paper book's policy comes only from the ratified mandate.

**M-b. Derivation — `asxos/domain/mandate/{types,derive}.py`**, pure Decimal, `Goals → Mandate`,
every output carries `traced_to`. Declared constants of `derivation_version = "v1"` (James ratifies
them by ratifying the memo):

| Output | Rule | Trace |
|---|---|---|
| `liquidity_reserve_aud` | Σ needs due ≤ 3y + emergency_months × (income − savings)/12 | D1 §1.1(b) |
| `deployable_capital_aud` | investable − reserve | — |
| `cash_floor_pct` | 7.5 %; 10 % if drawdown_tolerance < 20 % or reserve > 10 % of deployable | D1 §1.1(a)/(b) — the two inputs never supplied |
| `min_position_aud` | max(1,000, 2 × brokerage ÷ 1 %) | round-trip cost ≤ 1 % |
| `n_single_feasible` | floor(deployable × (1 − cash_floor) ÷ min_position), cap 20 | C1 arithmetic |
| `position_cap_pct` | min(10 %, 2 × (1 − cash_floor)/n) | C4, D8 |
| `stop_band_pct` / `risk_per_position_pct` | 25 % / position_cap × 20 % (= 2 %) | C3 / C2 |
| `portfolio_dd_review_pct` | drawdown_tolerance, review-only | C5 |
| `etf_core_pct` | max(30 % if savings_pa > 25 % of deployable, 1 − n_single_feasible/20) | contributions dominate selection when capital is small |
| `sleeve_allocations` | (1 − etf_core) split equally over single-name sleeves | B1 |
| `rebalance` | monthly; hold-band 2N; turnover budget 100 % p.a.; CGT-aware ordering via `tax.lots.select_min_cgt` | ruling 4 |

Test `tests/test_mandate_derive.py`: a fixture reproduces P5-01 §3's recommended values exactly
(C2 2 %, C3 25 %, C7 7.5 %); A$25k → n=20; A$7,749 → n=7, `etf_core_pct` 65 %.

**M-c. Memo.** Deterministic Jinja body over `outputs` (`mandate/memo.py`) + one bounded LLM pass
(same validator as D: cites `[mandate:<field>]`, every number verbatim in the inputs, no
`DIRECTIVE_TERMS`, no base rates). `portfolio-coherence-reviewer`'s checklist becomes the prompt.
Model: `claude-opus-5` (once per mandate; judgement-heavy).

**M-d. Intake + ratification.** James does not run CLIs, and income must not sit on a GitHub
issue. So: **attended-session interview → arbi runs `asx mandate init`** (new `cli/mandate.py`,
typer prompts, `ASXOS_PERSONAL_USE=1`) → `financial_goals` row → `asx mandate derive` writes the
`mandates` row at `pending_review`; memo emailed in the brief (private). Ratification: **`MANDATE
approve <id> <reason>`** on the pinned decisions issue (new verb via `apply_governance_transition`,
`actor='human'`). The comment carries only the id.

**M-e. Feed.** `mandate.sizing_policy_from(mandate) → SizingPolicy` replaces `load_sizing_policy`
for every paper packet (`build_decision_packets.py:76`); sleeves read `sleeve_allocations`,
`n_single_feasible`, `etf_core_pct`; ratification writes a declaring `paper_book_snapshots` row
(`capital_aud = deployable_capital`) — exactly how `paper_book.py:115-126` says capital changes.
**C-13 / H-32 is resolved here:** the mandate *is* the calibration; `derive_state`'s live branch
keeps `calibration=None` (memo-only by ruling); the paper branch (A3) needs no calibration object.

---

## A. Unlock the paper loop

**A1. Ledger — `migrations/0062_paper_book_ledger.sql` (Amber).** Append-only: `paper_intents`
(today `apply_github_decisions.py:214` builds a `PaperIntent` and drops it); `paper_book_fills`
(fill_id, thesis_id, intent_id UNIQUE, sleeve_id, symbol, side, qty>0, price_aud>0, cost_aud,
notional_aud, fill_session, reference_convention CHECK IN('next_open','next_close'); CHECK
notional = qty × price); `paper_book_positions` (snapshot_id FK, symbol, qty, close_aud, mv_aud,
sector; PK(snapshot_id, symbol)). A deferrable CONSTRAINT TRIGGER asserts at commit
`SUM(mv_aud) = holdings_mv_aud AND COUNT(*) = holdings_count`, so 0053's balance CHECK holds.
Test: extend `tests/test_paper_book_c1.py` so the new tables are named only by `paper_book.py`;
an integration case where mis-summed positions fail at COMMIT.

**A2. Loader/writer — `decision_engine/paper_book.py`.** Replace the raise at `:87-95` with a read
of `paper_book_positions` → weights as `portfolio_state.py:193-211` computes them; sector/close ride
on the row so the loader still reads only paper tables. New `write_daily_paper_snapshot(conn, *,
as_of, declared_capital, marks)`: cash = declared − Σbuy(notional+cost) + Σsell(notional−cost);
daily `capital_aud` = NAV. `declared_paper_capital` (`:151`) → latest row whose label does not
start with the daily prefix. `jobs/snapshot_paper_book.py` supplies marks from `prices`.
Test: one fill 100 @ 10.00 → cash 23,997.50, count 1.

**A3. `derive_state` paper branch — `builder.py:221-256`.** Add `book: Literal["live","paper"]
="live"` and `paper_position: PaperPositionContext | None` (held_weight_pct, thesis_status,
stop_breached, size: SizeRange, sleeve_target_pct). **Live branch byte-identical** (still raises on
non-None calibration). Paper: `abstain` if challenge ≠ pass; `watch` if tax_readiness == "fail" or
no context or `size.maximum_pct == 0`; `exit_review` if stop breached or sleeve rank-exit;
`initiate` if not held; held → `add` if weight < target − 1 pp, `trim` if > target + 1 pp, else
`watch`. **Fill weight = clamp(sleeve_target_pct, size.min, size.max)** — the sleeve sizes, the
challenge's feasible set bounds it. Call site `:836` passes `book=context.book`; `:886` carries
`indicative_size` for action states. **[R1] James ratifies the D17 wording** (arbi drafts): "D16 and
L4's 'never emits a weight' are amended for paper scope only, 2026-09-19."
Test `tests/test_decision_state_derivation.py`: live cases unchanged incl. the C-13 raise; a
9-row paper truth table.

**A4. Disposition → intent → fill.** Ruling 1 means no per-name `DISPOSE`: widen
`Disposition.recorded_by` (`delivery.py:92`) to `Literal["james","agent"]`. New nightly
`jobs/fill_paper_intents.py` after "Sync prices": for each action-state packet of a `book='paper'`
thesis from the previous session → agent disposition (note = the sleeve rule) → persist intent →
fill at **next session's `prices.open`** (fallback close, convention recorded — the packet is built
after the close, so the next open is the first price arbi could not have known, and it is what
`StagedOrder.limit_price` models). Quantity via `staging.stage_order()` (capital = paper NAV,
paper lots for sells, `PAPER_COST_BPS = 25`/side); first buy → `enter_thesis()`; exit →
`exit_thesis()`. James's own `DISPOSE` stays for non-sleeve theses.

---

## B. Sleeves that pick and size (forward-tested; weekly scoring, monthly rebalance)

**B1. Pre-registration — `research/registry/sleeves.py`** (shape of `vp.py:139-`): five
`ResearchHypothesis` + `StrategyVersion` pairs via `registry/repository.py`; widen `FactorName`
(`registry/types.py:19`). Common to single-name sleeves: `security_kind='au_equity'` and ∉ {lic,
reit}; liquidity gate via `screening/evaluator.evaluate_rule` (the rule `discover_opportunities.py`
owns); close ≥ 0.20; adj-step exclusions (B5); N and per-name weight from the mandate; **monthly**
rebalance on the first weekly run of the month; **rank-hold** (enter ≤ N, hold until rank > 2N);
caps from the mandate; cash floor honoured; benchmark `unavailable` until XJOA exists (F1).

| id | universe / rank | weighting | stop |
|---|---|---|---|
| `slv-etf-core-v1` | `security_kind='etf'`; pre-registered categories (AU broad, global broad, AU small) → highest-ADV ETF per category; `etf_core_pct` split 60/40 AU/global | fixed, 5 pp drift band | none |
| `slv-mom-12-1-v1` | `momentum` | equal | trailing −20 % |
| `slv-quality-v1` | `quality` | inverse-vol (`allocator.inverse_vol_weights`) | rank-exit |
| `slv-vq-control-v1` | `composite` (the incumbent, **untouched** — the control) | equal | rank-exit |
| `slv-low-vol-v1` | `low_vol` (falsifier discloses **trial count 24**) | equal | rank-exit |

ETF notes: 487 ETFs are in `universe` via `ingestion/universe.py:30`; verify `is_active` so
`sync_prices.py:102` prices them; no MER data (EODHD ETF endpoint unused) so ADV is the declared
scale proxy. Falsifier per single-name sleeve: after 12 rebalances, NAV − control with eff-t ≤ 2
(`alpha_eval.effective_t`) retires the sleeve. Test: hashes stable; `promotion.py:36` forbidden
words absent.

**B2. Weekly scoring + second composite (Amber).** `weekly-research.yml`: "Compute factor scores"
after "Derive fundamentals PIT", then "Run sleeves"; delete the retirement comment at `:16-18`.
`factor_scores.py`: `_COMPOSITE_CATEGORIES` (`:79`) untouched; add
`_COMPOSITE_V2_CATEGORIES = ("momentum","low_vol")` → `rs_factor_scores.composite_v2` (0063).
Test: `composite` bit-identical before/after.

**B3. Engine — `asxos/domain/sleeves/{universe,rank,rebalance,nav}.py`** pure Decimal;
`jobs/run_sleeves.py` (weekly) → `sleeve_positions` (sleeve_id, as_of, symbol, target_weight_pct,
rank, action, reason); `jobs/mark_sleeves.py` (nightly) → `sleeve_nav` (sleeve_id, dt, nav_index,
n_positions, turnover_pct, benchmark_level, benchmark_state). Both in 0063. **Not
`paper_portfolio_nav`** — that is Model A's shape (FK to `rebalance_runs`, `signal_label` columns,
0 rows, no writer); flag for a later drop. Sleeve NAV (weight-based, base 100) is the forward
test; the paper book's realised NAV is the second number.

**B4. Sleeve → theses (all sleeves fill on paper, per ruling 1).** Each entry:
`open_thesis(source="system_sleeve")` (widen 0057's CHECK); evidence cites `strategy_version_id` +
`content_hash` + the `rs_factor_scores`/ADV row (`proposals.py:105-` shape); plan from the sleeve's
own rule (band ref×0.98–1.02, stop as above, timeline 12 rebalances, **no target**);
`approve_object(..., actor="agent")` — thread `actor` through `apply_governance_transition` (D16's
own consequence note). `RESPONSE_RULE` binds the RI model only; `proposals.py`'s breakers are not on
this path. **[R2]** `has_price_plan` and the builder's scenarios require a target a rank-hold
sleeve honestly lacks → add `theses.plan_kind CHECK IN('price','rank_hold')`, `theses.book`,
`theses.sleeve_id` (0063); `rank_hold` passes with stop + timeline, bull scenario omitted — a
frozen `types.py` edit James ratifies.

**B5. `adj_close` — `research/adjusted_prices.py::split_adjusted_closes`**: `close × Π_{ex_date>dt}
1/split_ratio` from `rs_corporate_actions`; `factor_scores.py` reads it; residual one-day
|log step| > ln 5 excludes the symbol and is counted. `alpha_loader.py` unchanged (probe lane).

**B6. Backfill — its own Amber PR after a call budget.** `ingestion/eodhd.py`: `Budget` on the
client (`EODHD_DAILY_CALL_CAP`; `/fundamentals` = 10 units; `BudgetExhausted`); `JobMonitor`
writes `job_runs.api_calls / api_units` (0063). Then `jobs/backfill_price_history.py` →
`rs_prices_history` off `rs_security_master` incl. delisted, resumable by `MAX(dt)`;
`price-backfill.yml` dispatch-only. **[R3] James confirms the EODHD plan tier and daily cap.**

---

## C. Monitoring + outcomes
`outcomes.py` / `observe_decision_outcomes.py` unchanged — paper packets get t0 + 21/63/126 rows;
per-sleeve = join on `theses.sleeve_id`. `discipline.py` unchanged; `compose.py::
_thesis_discipline_inputs` (`:1211`) includes `book='paper'` theses. `check_thesis_invalidations.py:85`
adds `AND book='live'` to the *email* path — paper breaches surface as discipline findings and
`exit_review`, not as alert emails.

---

## D. The brief that reaches James (daily deterministic; weekly narrated)

- **Keep V1; add sections; do not flip `ASXOS_V2_BRIEF_ENABLED`** (all-or-nothing at
  `composer.py:94`, stale framing). **[R4]** the V2 tree's KEEP-DARK expiry is James's — recommend
  DELETE, porting `theme_dashboard`/`watchlist` ideas into V1 when needed. New `SECTION_ORDER`
  entries: `decisions_owed` **first**, `mandate` (memo when pending), `sleeves` after `portfolio`;
  collectors in `brief/compose.py`; blocks in `brief.html.j2`; `materialise_brief_sections.py:69`.
- **Sleeves card:** NAV index, since-inception vs XJOA (or `unavailable`), turnover, positions
  **with paper quantities and A$ notionals** — the "copy into your broker" surface, as statements,
  never `DIRECTIVE_TERMS` — what changed this week and the rule that changed it.
  **[R5]** fix `portfolio-policy.md:26` XJOAI → XJOA.
- **Decisions owed:** pending theses, pending mandate, stop breaches, overdue reviews, expired
  snoozes; age tiers ≥ 30 d loud / 7–29 d amber / < 7 d plain; ≥ 3 snoozes loud. Test: the 46-day
  HUBS flag sorts first.
- **Narrative — `jobs/narrate_brief.py`, weekly** (Sunday-UTC run = Monday AEST edition): reads
  that day's `brief_section_gold`, frozen system prompt (cacheable), ≤ 350 words citing
  `[section:<name>]`; validator: cited sections exist, every numeric token appears verbatim in the
  input, no `DIRECTIVE_TERMS`; failure → gold row MISSING, brief renders without it. Model:
  `claude-sonnet-5` (a bounded rendering task; ≈ US$0.03/edition, ~US$1.50/yr). Not a Routine (no DB
  path from the sandbox, config outside git, a documented silent-liveness record); not
  `claude-execute.yml` (no `DATABASE_URL` by design, ~100× the tokens). Needs the `anthropic`
  dependency + `ANTHROPIC_API_KEY` (James supplies the secret).
- **Verbs — `governance/github_commands.py:51`:** `HOLD thesis <id> <reason>` → `review_thesis`;
  `REVISE thesis <id> <field>=<value> <reason>` → `revise_thesis`; `EXIT thesis <id> <reason>` →
  paper: exit intent (fills next open); live: refused with "record after the real fill via `asx
  thesis exit`"; `SNOOZE thesis <id> <days ≤ 30> <reason>` → new `service.snooze_thesis`
  (revision_type `snoozed`, widen 0060's CHECK); `MANDATE approve|reject <id> <reason>`.
  Every verb writes a `thesis_revisions` row. Tests in `test_github_commands.py` /
  `test_apply_github_decisions_job.py`.

---

## E. Agent layer
Port and retire: `thesis-milestone-monitor` → `discipline.py` (already covers it);
`benchmark-performance-analyst` → outcome + sleeves sections; `portfolio-coherence-reviewer` →
challenge caps + the mandate memo prompt (one new `conviction_vs_weight` finding). Keep **monthly,
attended**: `macro-economist`, `theme-researcher`, `sector-screener` (no sandbox write path;
unattended LLM authorship of investment content is what D12 bounds). Retire into the narrative
step: `thesis-coherence-guard`, `market-context-narrator`.

## F. Fix-first (each Green unless noted)
1. Regime units — `regime/classifier.py:33-34` → `6.00`/`4.50` (FRED percent), `CLASSIFIER_VERSION`
   v1.1; a test that reads a real stored `us_hy_oas` value.
2. `security_kind` — CHECK already admits `etf/lic/reit`; the fix is the **backfill** (59 A-REITs kept
   `au_equity` in 0037, no LIC classified) from `rs_security_master` type/GICS sub-industry; verify
   ETFs are `is_active`. Every sleeve's universe filter needs it. (Amber — data migration.)
3. `tax_settings` — the FY2027 row is sourced from `financial_goals.account_type/marginal_rate`
   and written by `asx mandate derive`.
4. Profile — `build_decision_packets.py:76` loads the *live* profile (A$7,749) into `SizingPolicy`
   for paper packets → min/capital = 12.9 % > cap → `ZERO_SIZE` nightly. Interim: `capital_aud =
   state.capital_aud`; permanent: M-e.

---

## G. Sequencing (AGENTS.md §6 classes; every `migrations/` + `.github/workflows/` edit is Amber)

| PR | Class | Content | Depends |
|---|---|---|---|
| **PR-M — FIRST** | Amber (mig) | 0061 + `domain/mandate/` + `asx mandate init/derive` + `MANDATE` verb + memo template | — |
| PR-0 | Green | F1 regime; F4 interim; builder `:840` label | — |
| PR-1 | Amber (wf+mig) | B2 weekly scoring + B5 adj_close + `composite_v2` | — |
| PR-2 | Amber (mig) | B6 call budget + F2 `security_kind` backfill | — |
| PR-3 | Amber (mig+wf) | B1/B3 sleeves + `sleeve_nav` + sleeves brief section (memo mode until PR-4) | PR-M, PR-1, PR-2 |
| PR-4 | Amber (mig+wf) | A1–A4 ledger, loader, paper `derive_state`, fill job | PR-M, **R1** |
| PR-5 | Amber (mig) | decisions_owed + HOLD/EXIT/REVISE/SNOOZE | — |
| PR-6 | Amber (dep+wf) | narrative step (brief + mandate memo) | secret |
| PR-7 | Amber (mig) | B4 sleeve→theses, `actor='agent'`, `plan_kind/book/sleeve_id` | PR-3, PR-4, **R2** |
| PR-8 | Amber (wf) | backfill lane | PR-2, **R3** |

**Why PR-M first:** every downstream number — paper capital, N, per-name cap, cash floor, ETF
split, sleeve allocations, `tax_settings` — is a mandate output; building sleeves first would
hard-code A$25k / N=20 in five places (the exact defect James named on 09-16). The code merges on
fixture inputs; the derivation runs for real the day James sits the interview. **Parallel now:**
{PR-M, PR-0, PR-1, PR-2, PR-5}. **Next:** {PR-3, PR-4, PR-6}. Then PR-7, PR-8.

**James's, and nothing else:** the mandate interview (M-d) and `MANDATE approve`; R1 D17 wording;
R2 `plan_kind` / `types.py`; R3 EODHD cap; R4 V2 delete; R5 XJOA; `ANTHROPIC_API_KEY`; applying
migrations per §8 (arbi runs the sequence under the standing grant); `weekly-research` stays
reserved — the first sleeve run lands on its Saturday schedule.

## H. The substrate question
**Python + GitHub Actions for everything scheduled — including the weekly LLM narrative and the
mandate memo as one validated, evidence-cited job step** — because step order is the dependency
graph, failures are visible, secrets live in one store, and the job is code in git. **Claude Code
sessions are for James's steering** (the mandate interview, weekly reading, `MANDATE`/`HOLD`/`EXIT`
typed on his phone) **and arbi's building and review.** Routines carry scheduled Claude *judgement*
only if they get an in-git, auditable write path; they have none today, so monthly discovery stays
attended. The CLI is the right tool for authorship and review and the wrong tool for the nightly
loop — this plan keeps it out of that loop.

---

## Verification (end to end)

1. `make check` green on every PR; `tests/test_domain_purity.py` allow-list shrink-only.
2. PR-M: `asx mandate derive` on the fixture reproduces P5-01 §3 values; a `mandates` row lands at
   `pending_review`; `MANDATE approve` from the pinned issue flips it with one `governance_events` row.
3. PR-1: `factor-probe.yml` dispatched on one date → `composite` bit-identical, `composite_v2`
   populated, adj-step exclusions counted in `job_runs`.
4. PR-4: nightly `daily-brief` produces one `initiate` packet for a paper thesis → `paper_intents`
   row → `paper_book_fills` row at next open → `paper_book_snapshots.holdings_count = 1` and the
   deferrable trigger passes. `paper_book.py` still names no live table (`test_paper_book_c1.py`).
5. PR-3/7: first Saturday `weekly-research` → `sleeve_positions` for five sleeves; N per the
   mandate; no LIC/REIT in any single-name sleeve; `sleeve_nav` base 100 next night.
6. PR-5/6: Monday brief opens with "You owe N decisions", HUBS's 46-day flag first; narrative
   validator passes; `HOLD thesis 2 …` from the phone → `thesis_revisions` row, flag clears.
7. Live-verify every `governance_status` transition's statement ORDER against the real triggers in
   a rolled-back transaction (the Phase 2a lesson) before merging PR-M and PR-7.
