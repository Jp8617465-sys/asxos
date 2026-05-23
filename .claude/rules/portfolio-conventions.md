# Portfolio conventions — asxos M13

Invariants and design decisions for the M13 portfolio construction layer.
Read this before touching any file under `asxos/domain/portfolio/`.

---

## Regulatory firewall (Part 0 Q1)

Every CLI entry point and every job that touches portfolio data MUST call
`_require_personal_use()` (CLI) or check `os.environ.get("ASXOS_PERSONAL_USE") == "1"`
(jobs). This is the architectural firewall preventing personal-advice outputs
(under s766B Corporations Act 2001 / the Westpac v ASIC boundary) from
being surfaced in a multi-user context.

The brief's section 6 requires a SECOND gate: `ASXOS_PORTFOLIO_BRIEF_ENABLED=1`.
This stays `0` until 4 weeks of paper-trade sign-off completes (M13.8).

---

## v1 risk-blindness invariants (plan I.1)

The constraint waterfall does NOT protect against market-wide co-movement.
The v1 allocator is risk-blind to systematic ASX beta clustering. The ASX 200
has tight beta clustering that doesn't map cleanly to GICS sectors — Materials
and Financials are >40% of the index and move together more than the sector
taxonomy implies. A 20-name inverse-vol portfolio with a 30% sector cap can
still carry 0.8+ pairwise correlation across half the names.

**Capital preservation in a 2008/2020-style drawdown is the user's
responsibility.** The cash floor and leverage cap are the only structural
protections in v1.

A crude market-beta cap (max aggregate beta across the portfolio) is a v2
candidate (`m14_candidate_beta_cap`). Out of v1 scope.

---

## Risk-tolerance → position-count heuristic (plan I.2)

The mapping (conservative=30, balanced=20, growth=15, aggressive=10) is a
**UX heuristic, not a finance-research-grade model**. It conflates variance
tolerance with concentration preference; an aggressive investor might
rationally want more names in higher-volatility segments, not fewer.

Revisit with realised performance data in M14+. The defaults are tunable
per profile via `risk_tolerance_scalar` directly — a user who knows what
they want can bypass the label.

---

## Composite score weighting (plan I.3)

The default 0.6 / 0.4 split on `prob_up` / `expected_return` is a
**starting prior, not a calibrated ratio**. On a model where prob_up is
the dominant calibration signal, 0.8/0.2 might be right; on a
well-calibrated expected_return model, the inverse.

The weight pair lives in `profiles.score_weights_json` with a ±0.001
tolerance on the sum. Application code normalises to exact Decimal("1") on
read. Revisit in M14+.

---

## Loss-harvest tagging — Part IVA / TR 2008/1 disclaimer (plan I.5)

The `rationale_tags['reason']='loss_harvest'` tag is **INFORMATION ONLY**.

- It does **not** endorse harvesting.
- It does **not** assess wash-sale risk under TR 2008/1.
- It does **not** advise on Part IVA ITAA36 application.
- The system does **not** track or warn on rebuy timing.

**The user (James) is solely responsible for ATO compliance on any rebuy
after a harvest sale.**

This disclaimer must be cited verbatim in any code surface that emits the
tag (module docstring + function docstring for `tag_loss_harvest`).

---

## §5.1 boundary-defer (plan I.4)

The `defer_near_boundary_sells` check happens inside `compute_deltas`
(M13.6 `rebalance.py`), NOT in the allocator or tax overlay. This ensures
that allocator-reductions, full exits, and `universe_inactive` forced-sells
all receive the same CGT-eligibility treatment.

The window is 30 calendar days. A lot with `days_to_cgt_discount=0` is
already eligible; no deferral needed. Calendar arithmetic per spec §5.1:
`disposal_date >= acquired_at + relativedelta(years=1) + timedelta(days=1)`.

---

## account_type on HoldingSnapshot (plan H.1 CRITICAL-1 resolution)

`HoldingSnapshot.account_type` is derived from the **active profile** at
snapshot time in `build.py`. The `holding_lots` table does not have an
`account_type` column; the system is single-user and the profile is the
canonical source of account type. Do not add `account_type` to `holding_lots`.

---

## No-active-profile hard-fail (plan H.1 CRITICAL-5)

`PortfolioService.build()` raises `RuntimeError` if no profile is active.
This is a hard-fail, not a graceful warning (CLAUDE.md non-negotiable #10).
The CLI renders the error as a red message and exits 1.

The `set_active_profile()` Postgres function enforces the exactly-one-active
invariant (plan I.8). Never bypass it with raw `UPDATE profiles SET is_active`.

---

## Lowest-conviction unconstrained BUY tiebreaker (plan H.1 R2)

When `defer_sells_near_boundary()` needs to identify the lowest-conviction
unconstrained BUY to absorb a deferred sell, the tiebreaker is:
`inv_vol_score ASC` then `symbol ASC` (alphabetical).

Document this in any code that selects "the weakest buy to absorb a
deferred sell" so the logic is transparent. Currently not yet implemented
(this function lives in M13.6 compute_deltas; the absorption logic is a v2
candidate for a more sophisticated implementation).

---

## Decimal-only arithmetic

No numpy in any M13 domain module (`allocator.py`, `volatility.py`,
`constraints.py`, `tax_overlay.py`, `rebalance.py`). Python 3.12 `Decimal.ln()`
for log returns. The vol calculation over 30 names × 60 closes produces ~1,770
`Decimal.ln()` calls per build, estimated 0.1–0.4s — acceptable for weekly
cadence and on-demand CLI use.

---

## Hard-fail invariants (plan Part C)

| Condition | Raises |
|---|---|
| No active profile | `RuntimeError` in `PortfolioService.build()` |
| Empty buy universe after filtering | `RuntimeError` in `allocator.allocate()` |
| Non-convergent constraint waterfall (>5 iterations) | `RuntimeError` in `constraints.apply_constraints()` |
| Insufficient price history for vol | symbol silently omitted from candidates |
| Missing reference price in `compute_deltas` | `RuntimeError` |
| Stale signals (>2 days old) | `RuntimeError` in `PortfolioService.build()` |

No `logger.warning(...); continue` on any of these paths.

---

## Weekly cron cadence

Saturday 20:00 UTC = Sunday 06:00 AEST. Monday's brief picks up the result.
If the cron fails, section 6 of the brief is omitted (not partial, not stale).
The brief freshness gate: `job_runs.status='success'` for `build_portfolio`
with `as_of >= brief_date - 2`.
