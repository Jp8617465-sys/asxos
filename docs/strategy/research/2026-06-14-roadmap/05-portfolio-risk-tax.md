# 05 — Portfolio, Risk, and Tax

> **Status: planning only. No portfolio output is approved for action.**
> - `build_portfolio` stays stopped until the loop is green (see restart
>   criteria, §11).
> - Tax logic is frozen (source of truth: `docs/foundation/spec/tax-alpha.md`).
> - The personal-use / regulatory firewall is non-negotiable (§9).
>
> Portfolio outputs are **decision support for one user (James)**, never
> personal financial advice.

---

## 1. What already exists

The portfolio/tax stack is one of the most complete parts of ASXOS:

| Component | Module | Notes |
|---|---|---|
| Allocator | `domain/portfolio/allocator.py` | Inverse-vol, Decimal-only |
| Constraints | `domain/portfolio/constraints.py` | Per-name + sector caps; convergence hard-fail >5 iters |
| Tax overlay | `domain/portfolio/tax_overlay.py` | Loss-harvest tagging (info-only) |
| Rebalance | `domain/portfolio/rebalance.py` | `compute_deltas`, §5.1 boundary-defer |
| Volatility | `domain/portfolio/volatility.py` | `Decimal.ln()` log returns |
| Profile | `domain/portfolio/profile.py` | Single active profile (exactly-one invariant) |
| Paper trade | `domain/portfolio/paper_trade.py` | Shadow-book scaffolding |
| Tax engine | `domain/tax/{cgt,div_296,franking,medicare,fx_gain,lots,dividends,positions,import_csv}.py` | Spec-cited; CGT calendar arithmetic |
| Position monitor | `domain/position_monitor/*` | Exists; **`check_us/au_positions` services absent** |
| Theses / themes | `domain/theses/*`, `domain/themes/*` | Landed; dark-launched in brief |

## 2. Decision ledger

- **Current.** `decisions` journal table + `asx journal add/list/review` CLI.
- **Direction.** A *provenance* view (guards-backlog P3-3) joining each proposed
  trade to the exact signal row, `model_version`, profile state, and input-data
  freshness that produced it. This makes "why did the system propose this?"
  answerable in one query.
- **Why it matters.** Auditability is the product. A trade you cannot explain is
  a trade you should not act on.
- **Manual vs automated.** Ledger *recording* can be automated; ledger
  *decisions* (act / don't act) stay manual.

## 3. Position monitor

- **Current.** Code complete (`domain/position_monitor/*`,
  `test_position_monitor.py`); `check_us_positions` / `check_au_positions`
  services **not live**.
- **Direction (Lane A after green).** Deploy the monitors so held positions are
  watched daily (stops, thesis invalidation via `check_thesis_invalidations`).
- **Dependency.** Loop green + monitoring tier deployed first (so we can see the
  monitors themselves run).

## 4. Tax overlay and CGT-aware decisions

- **Frozen.** All tax math is per `docs/foundation/spec/tax-alpha.md`; deviations
  require a spec amendment. Do not touch.
- **CGT 12-month rule.** Calendar arithmetic, never day-count:
  `disposal_date >= acquisition_date + relativedelta(years=1) + timedelta(days=1)`
  (spec §5.1).
- **Boundary-defer.** `defer_near_boundary_sells` (30-day window) lives in
  `compute_deltas` so all sell paths get the same CGT-eligibility treatment
  (`portfolio-conventions.md`).
- **Loss-harvest tag.** `rationale_tags['reason']='loss_harvest'` is
  **information only** — it does not endorse harvesting, assess wash-sale risk
  (TR 2008/1), or advise on Part IVA. James is solely responsible for ATO
  compliance on rebuy timing. This disclaimer is cited verbatim in the code that
  emits the tag.

## 5. Liquidity

- **Current.** Not explicitly modelled in v1 sizing.
- **Direction (Lane B).** Incorporate average daily volume / spread into sizing
  so proposals are actionable at realistic size. Out of v1 scope.

## 6. Sizing

- **Current.** Inverse-vol weights within per-name and sector caps;
  position-count heuristic (conservative=30 … aggressive=10) — a **UX heuristic,
  not a finance-grade model** (`portfolio-conventions.md`).
- **Direction (Lane B).** Revisit with realised data; `risk_tolerance_scalar`
  already allows bypassing the label.

## 7. Sector / style / risk exposure

- **Current — documented v1 risk-blindness.** The constraint waterfall does
  **not** protect against market-wide co-movement. The ASX 200 has tight beta
  clustering that doesn't map to GICS; a 20-name inverse-vol portfolio with a 30%
  sector cap can still carry 0.8+ pairwise correlation. **Capital preservation
  in a 2008/2020-style drawdown is the user's responsibility.** The cash floor
  and leverage cap are the only structural protections in v1.
- **Direction (Lane B / v2 candidate).** A crude market-beta cap
  (`m14_candidate_beta_cap`) — max aggregate portfolio beta. Explicitly out of
  v1 scope.

## 8. Thesis integration

- **Current.** `theses` / `themes` / `theme_holdings` / `thesis_revisions`
  landed; dark-launched in the brief (V2). Backed up as irreplaceable.
- **Direction (Lane B).** Thesis-driven decisions and the thesis-revisit engine
  are part of the V2 reshape — parked.

## 9. Brief vs recommendation boundary + regulatory firewall

- Every CLI entry point and job touching portfolio data must call
  `_require_personal_use()` (CLI) or check `ASXOS_PERSONAL_USE=="1"` (jobs).
- A **second gate** `ASXOS_PORTFOLIO_BRIEF_ENABLED=1` stays `0` until 4 weeks of
  paper-trade sign-off (M13.8).
- This is the architectural firewall preventing personal-advice outputs (s766B
  Corporations Act / Westpac v ASIC boundary) from surfacing in a multi-user
  context. **Non-negotiable.**
- **Boundary rule.** The brief presents *information and decision support*; it
  never instructs. No "you should buy X."

## 10. Manual override log + attribution

- **Manual override log (Lane B).** When James acts against (or without) a
  proposal, record it. Overrides are data — they reveal where the model and the
  operator disagree, and why.
- **Attribution (Lane B).** Decompose realised P&L by source (signal, theme,
  market beta, FX). `portfolio_attribution` table exists as scaffolding.

## 11. `build_portfolio` restart criteria

`asxos-build-portfolio` is live on Render but carries the **stale** DB
fingerprint `fca87bb5cc` (deliberately excluded from the rollout). It will fail
with `InvalidPasswordError` at its next Saturday run until rolled.

**Restart sequence (all gated, each needs approval):**

1. Core loop GREEN for the current `as_of` (gate G1).
2. Signals fresh (gate G2) — `build_portfolio` reads `signals`; building on
   stale signals proposes trades against yesterday's reality.
3. Roll its DATABASE_URL (`fca87bb5cc` → `a07ca95a44`) via single-key PUT.
4. Manual test run / observe one Saturday cycle before trusting weekly output.
5. **`ASXOS_PORTFOLIO_BRIEF_ENABLED` stays `0`** — building the portfolio is
   separate from surfacing it in the brief.

## 12. What should remain manual / be automatable / need approval

| Item | Stance |
|---|---|
| The decision to act on any proposal | **Always manual.** |
| Recording proposals + provenance | Automatable (Lane B). |
| Position monitoring + alerts | Automatable (Lane A after green) — alert, do not act. |
| Tax-action *suggestions* | Automatable as info-only; **acting is manual + James's ATO responsibility.** |
| `build_portfolio` runs | Automatable (weekly cron) **after** restart criteria met. |
| Surfacing portfolio in the brief | Needs the double gate + 4-week paper sign-off. |
| Any order placement / execution | **Out of scope. Not built. Not planned for autonomy.** |

## 13. Evidence required before portfolio output is trusted

1. Loop green ≥5 trading days (signals demonstrably fresh).
2. `build_portfolio` runs clean on the corrected credential.
3. Shadow paper book agrees with expectations over the paper-trade window
   (links to `04-quant-research-and-ml.md` §8).
4. Decision-ledger provenance view exists so every proposal is explainable.
5. The v1 risk-blindness limitation (§7) is explicitly acknowledged by the
   operator at each use.
