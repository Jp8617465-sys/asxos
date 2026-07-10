# Portfolio policy — James's capital mandate

**Status:** current
**Scope:** the governor-set objectives, risk appetite and hard constraints that every
portfolio memo (`portfolio-manager-charter.md`) must sit inside. The investment-policy
statement arbi's portfolio capacity operates within.
**Last verified:** 2026-07-10
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
- **Benchmark:** beat the **XJO total-return** benchmark after tax and costs
  (`benchmark-performance-analyst`). Alpha is the point; matching the index is failure of the
  thesis, not success of the tool.
- **Return / drawdown targets:** **[governor to set]** — arbi does not assume a number.

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

While CLAUDE.md rule #11 stands, **no allocation decision or memo may use Model A output**
(signals, allocator, candidate scans, opportunity-cost ranking). Allocation memos are
**model-independent** — driven by thesis discipline, realised benchmark gap, tax/CGT state,
concentration vs the caps above, and theme stewardship. The signal-driven allocator path is
quarantined until the decay dispute resolves (`docs/model-a-decay-analysis-2026-07-10.md`;
`decision-log.md`). This is the single most important constraint on the portfolio capacity
today.

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
