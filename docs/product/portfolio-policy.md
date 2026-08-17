# Portfolio policy — James's capital mandate

**Status:** current
**Scope:** the governor-set objectives, risk appetite and hard constraints that every
portfolio memo (`portfolio-manager-charter.md`) must sit inside. The investment-policy
statement arbi's portfolio capacity operates within.
**Last verified:** 2026-08-10
**Owner:** **James (governor) — this file is his mandate.** arbi may *draft* a change (P5,
draft-only); only James approves it. Changing a constraint here is a boundary change.
**Superseded by:** N/A

This is the **policy** layer, not the **code** layer. The load-bearing code invariants live
in `.claude/rules/portfolio-conventions.md` and the allocator (`asxos/domain/portfolio/`);
this file states *James's intent* that those invariants serve, and is the thing arbi checks a
memo against. Where a number here is James-specific and not yet fixed in the repo, it is
marked **[governor to set]** — arbi must read the value from the active `profiles` row or ask
James, and must **never invent one.**

---

## Objectives (governor-set)

- **North star:** financial freedom via **disciplined, thesis-driven ASX investing** — a
  small number of opinionated, explainable positions held over a **weeks-to-months** horizon
  (`north-star.md`). Not trading; not index-hugging; not signal-chasing.
- **Benchmark (amended 2026-08-10, governor ruling F1):** the canonical AUD benchmark is the
  **official S&P/ASX 200 Accumulation Index (XJOAI)**, measured after tax and costs. Alpha is the
  point; matching the index is failure of the thesis, not success of the tool.
  - `AXJO.INDX` (`asxos/domain/portfolio/monitor_loader.py:34`) is EODHD's **price** index. It may
    remain **price-context only** and **must never carry a total-return label**.
  - **If licensed XJOAI history is not available, report benchmark measurement as `unavailable`.**
    Do **not** silently substitute a proxy. Data acquisition is a later approved work order.
- **Global exposure (F2):** report a **separate global sleeve**. Do not blend HUBS or any future
  global holding into the ASX benchmark until global exposure is a deliberate, material allocation.
- **Return / drawdown targets:** **DEFERRED (governor ruling F4, 2026-08-10)** with a named blocker:
  **"James must complete the capital/risk calibration before Stage 4."** arbi does not assume a
  number. Until the calibrated mandate exists, volatility, beta, correlation and drawdown are
  **reporting-only**, and these hard universal gates apply and are not deferrable: no leverage by
  default · no Model A capital input (rule #11) · no action on unresolved tradeability or ownership ·
  no action on stale or missing decision-critical evidence · no broker execution.
  Stage 1 evidence work is **not** blocked by this deferral.

## Measurement contract (amended 2026-08-10 — `target-architecture.md` Appendix C)

Governor ruling: performance is measured **after tax, cash-flow-adjusted, benchmark-relative**.
Five quantities, computed and reported **separately** — never collapsed into a single score:

1. **after-cost portfolio TWR** — selection/process skill, neutral to contribution timing
2. **after-tax portfolio TWR** — skill net of the tax consequences of the decisions taken
3. **money-weighted return / IRR** — the actual wealth outcome
4. **benchmark-relative result**
5. **tax / franking / FX bridge** — the reconciliation explaining the gap between the above

A figure is not comparable to anything until these conventions are fixed: external-flow timing
(start/end-of-day + the sub-period breaking rule), valuation cutoff and timezone, realised vs
unrealised tax treatment, franking gross-up basis and refundability, FX convention for non-AUD
lots, and **whether the benchmark is compared pre-tax or under a stated tax assumption**.

**Tax framing (governor correction, 2026-08-10).** Tax is **not guaranteed alpha**. It is a
quantifiable implementation advantage and a decision constraint **whose benefit must be measured,
not asserted**. Plain return vs index is invalid under irregular contributions — that is why TWR
and MWR are reported separately rather than as one number.

## Risk appetite (governor-set, per active profile)

- Risk tolerance is expressed through the active `profiles` row
  (`risk_tolerance` + `risk_tolerance_scalar`), which drives the **position-count heuristic**
  (conservative≈30 · balanced≈20 · growth≈15 · aggressive≈10 names). This mapping is a **UX
  heuristic, not a calibrated model** (`portfolio-conventions.md` plan I.2) — it conflates
  variance tolerance with concentration preference. arbi surfaces it as a prior, not a law.
- Active profile / risk tolerance today: **[read from `profiles WHERE is_active`]** — never
  assumed.

## Hard constraints (the mandate arbi memos must respect)

These are the structural protections. A memo that would breach one is **not a
recommendation** — it is a policy-change proposal (P5), and arbi must present it as such.

| Constraint | Value | Source |
|---|---|---|
| Sector cap (per GICS sector) | **30%** | `portfolio-conventions.md` I.1 / constraints waterfall |
| Position count | by risk tolerance (see above) | `portfolio-conventions.md` I.2 |
| Cash floor | **[governor to set / read from profile]** — a structural protection, one of only two in v1 | `portfolio-conventions.md` I.1 |
| Leverage cap | **[governor to set / read from profile]** — the other v1 structural protection | `portfolio-conventions.md` I.1 |
| Composite score weighting | 0.6 `prob_up` / 0.4 `expected_return` (a starting prior, tunable in `profiles.score_weights_json`) | `portfolio-conventions.md` I.3 |
| CGT 12-month rule | **calendar arithmetic**, never day-count: `disposal ≥ acquisition + relativedelta(years=1) + timedelta(days=1)` | CLAUDE.md #6, spec §5.1 |
| Near-boundary sell deferral | 30 calendar days | `portfolio-conventions.md` §5.1 boundary-defer |

**Known v1 risk-blindness (governor accepts):** the allocator is **risk-blind to systematic
ASX beta clustering** — a 20-name inverse-vol book under a 30% sector cap can still carry
0.8+ pairwise correlation. **Capital preservation in a 2008/2020-style drawdown is James's
responsibility**; the cash floor and leverage cap are the only structural protections in v1
(`portfolio-conventions.md` I.1). A market-beta cap is a v2 candidate. Any memo touching
concentration must state this caveat, not imply the caps protect against co-movement.

## The Model A quarantine (rule #11) — binds allocation

Rule #11 is now **standing policy**: **no allocation decision or memo may use Model A output**
(signals, allocator, candidate scans, opportunity-cost ranking). Allocation memos are
**model-independent** — driven by thesis discipline, realised benchmark gap, tax/CGT state,
concentration vs the caps above, and theme stewardship. The decay dispute is **resolved
(2026-07-11, against Model A** — no usable edge on 19,032 matured signals,
`docs/model-a-decay-analysis-2026-07-11.md`), and James **shelved** the ML engine
(`ml-engine-shelf-2026-07-11.md`); the signal-driven allocator path stays **dormant by
standing policy**, not pending a resolution. Model-independence is therefore not a temporary
constraint on the portfolio — it is the permanent shape of every memo until a *new* model
passes a pre-registered decay bar.

## Tax discipline (governor intent; spec is authoritative)

- Tax math is per `docs/foundation/spec/tax-alpha.md` (CLAUDE.md #8) — this policy does not
  restate it, it defers to it. Memos cite spec sections, not this file, for tax numbers.
- **Loss-harvest tags are information only.** They do **not** endorse harvesting, assess
  wash-sale risk under TR 2008/1, or advise on Part IVA ITAA36. The system does not track
  rebuy timing. **James is solely responsible for ATO compliance on any rebuy after a harvest
  sale** (`portfolio-conventions.md` I.5, cited verbatim in any memo that emits the tag).

## What requires James's explicit approval

- **Any capital deployment** — every buy, trim, add, or exit. arbi proposes; James executes
  in his broker.
- **Any change to this policy** — objectives, risk appetite, or any hard constraint above.
  arbi may draft it (P5); only James enacts it.

## Reading this policy

arbi reads this file before producing any P2/P3 memo, resolves every **[governor to set]**
against the active profile or by asking James, and checks the proposal against every hard
constraint. A memo that omits this check, or invents a governor-set number, is void
(`arbi-scorecard.md` circuit breakers).
