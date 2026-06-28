# Design notes — 4 Design-MED items (2026-06-28)

Design-only. No code in this change. Each item below states the problem, the
recommended fix, alternatives + trade-offs, data/schema/query shape, edge cases,
and the tests that would pin it. Authored from the `backend-architect` advisory
pass and fact-checked against the tree (migration counter, column types).

Source findings: `docs/audit-2026-06-27.md` (MED triage). The four items are
independent — no shared file or migration.

Status legend: **READY** = implementable as designed; **NEEDS-OWNER-DECISION** =
one open choice flagged for James before code.

---

## Item 1 — position_monitor multi-lot aggregation  (READY)

> **IMPLEMENTED 2026-06-28 (active-profile scoping; supersedes the
> `mixed_account_types` warn/fail option below).** A deep-research pass
> established that individual and SMSF are separate CGT taxpayers, so lot
> aggregation is SCOPED to the active profile's `account_type` (filter, never
> pool) rather than averaged across account types with a mixed-account flag.
> The "Open decision" / mixed-account-type cross-cutting flag is therefore
> moot. Shipped: per-lot CGT ladder, an `all_eligible` flag, deterministic
> `ORDER BY`, and a no-active-profile hard-fail at the CLI. Files: `asxos/domain/
> position_monitor/{service,types,display}.py`, `asxos/cli/position.py`; tests in
> `tests/test_position_monitor_lots.py` + `tests/test_cli_position.py`. The rest
> of this block is retained as the design record.

**File:** `asxos/domain/position_monitor/service.py:178-234` (`load_position_context`);
consumers `display.py:64-76,222-256` and `_build_scenarios` (`service.py:78-99`);
carrier `types.py:33-36` (`MonitorInput`).

### Problem
The query `LEFT JOIN holding_lots ... ON symbol AND disposed_at IS NULL` with
`ORDER BY t.opened_at DESC LIMIT 1` collapses a multi-lot position to ONE lot, and
the `ORDER BY` is on `theses.opened_at` (not lot acquisition), so *which* lot
survives is effectively arbitrary / non-deterministic. From that single lot it
derives two wrong figures:
- `cost_per_share = cost_base_normal / quantity` — one lot's per-share cost, not
  the position's.
- `cgt_date = acquired_at + 1yr + 1day` — one lot's eligibility, applied as if the
  whole position flips at once.

Example failure: 100 @ $30 acquired 13 months ago + 100 @ $40 acquired last week is
misrepresented on both cost and CGT-eligibility, non-deterministically.

### Recommended fix
Aggregate in SQL; carry a **position-level summary** plus a **per-lot CGT ladder**.
- `cost_usd` = weighted-avg cost-per-share = `SUM(cost_base_normal) / SUM(quantity)`.
- `shares` = `SUM(quantity)`.
- `lots: tuple[LotCgt, ...]`, `LotCgt = (quantity, acquired_at, cgt_eligible_date,
  cost_base_normal)`, ordered `acquired_at ASC`.
- `cgt_date` (headline scalar, backward-compatible): the `cgt_eligible_date` of the
  **earliest lot not yet eligible as of `as_of`**; if all eligible → `None` plus an
  explicit `all_eligible=True` flag (distinct from "no lot"); if all ineligible →
  soonest eligible date.

CGT-eligibility is **per-lot and must not be collapsed to one date.** Compute
`cgt_eligible_date` in Python (`acquired_at + relativedelta(years=1) +
timedelta(days=1)`) to keep the §5.1 calendar arithmetic in one place.

### Query shape
```sql
SELECT t.thesis_id, t.stop_price, t.target_price,
       t.analyst_buy_count, t.analyst_neutral_count, t.analyst_sell_count,
       t.analyst_consensus_target,
       agg.total_cost, agg.total_qty, agg.lots
FROM theses t
LEFT JOIN LATERAL (
    SELECT SUM(hl.cost_base_normal) AS total_cost,
           SUM(hl.quantity)         AS total_qty,
           jsonb_agg(jsonb_build_object(
               'quantity', hl.quantity,
               'acquired_at', hl.acquired_at,
               'cost_base_normal', hl.cost_base_normal,
               'account_type', hl.account_type
           ) ORDER BY hl.acquired_at) AS lots
    FROM holding_lots hl
    WHERE hl.symbol = t.symbol AND hl.disposed_at IS NULL AND hl.quantity > 0
) agg ON TRUE
WHERE t.symbol = $1 AND t.status = 'active'
ORDER BY t.opened_at DESC
LIMIT 1;
```
`LIMIT 1` now legitimately selects the active thesis (1-per-symbol-active); the lot
aggregation is independent and complete.

### Alternatives + trade-offs
- **(A) Pick earliest-acquired lot.** Cheapest, deterministic, but still wrong cost
  and over-optimistic CGT. Rejected.
- **(B) Weighted-avg cost + single earliest cgt_date.** Correct cost; CGT still
  misleading (a recent lot shown as eligible). Acceptable only as a documented
  simplification — not recommended for a tax-discipline product.
- **(C) Full per-lot ladder (recommended).** Most code (new `LotCgt`, display
  ladder), fully correct. Worth it: CGT is the monitor's headline.

### Edge cases
- Zero open lots (thesis active, position disposed): `total_qty` NULL/0 →
  `cost_usd=None`, `lots=()`, no CGT scenario.
- `quantity = 0` lot: excluded in WHERE (already above) so it can't pollute the
  weighted-avg denominator.
- Lots with differing `account_type` (individual + SMSF, same symbol): averaging
  cost across account types is semantically invalid for CGT — surface
  `mixed_account_types: bool` and render a warning (or hard-fail per CLAUDE.md #10),
  do **not** silently average.
- All lots eligible: `cgt_date=None`, `all_eligible=True`; display says "all
  eligible", not "no CGT data".
- Partial eligibility (motivating case): ladder shows eligible_qty vs pending_qty
  and the next milestone date.

### Tests
1. Single lot → weighted-avg == that lot's cost-per-share; cgt_date unchanged
   (regression parity).
2. Two lots, different cost & acquired_at → `cost_usd == SUM(cost)/SUM(qty)` exact
   Decimal; `lots` length 2 ascending.
3. Two lots, one eligible / one not, `as_of` between → headline `cgt_date` = the
   ineligible lot's date; ladder eligible_qty / pending_qty correct.
4. All eligible → `cgt_date=None`, `all_eligible=True`.
5. Zero open lots, active thesis → empty lot fields, no CGT scenario, stop/target
   present.
6. `quantity=0` lot → excluded.
7. Determinism: repeated calls → identical `cost_usd` (guards the old arbitrary-lot
   bug).
8. Mixed account_type → `mixed_account_types=True` (or hard-fail per chosen policy).

**Open decision:** mixed-account-type lots → warn-flag vs hard-fail. Recommend
hard-fail (CLAUDE.md #10), but it's a behaviour choice.

---

## Item 2 — opportunity_cost baseline  (NEEDS-OWNER-DECISION)

**File:** `asxos/domain/brief/collectors/opportunity_cost.py:24,87-91`.

### Problem
The docstring and `_MEANINGFUL_DELTA` comment claim ">5% net return ADVANTAGE over
the current holding" (a delta), but line 89 tests `net_expected_return >
_MEANINGFUL_DELTA` — the **alternative's absolute** CGT-adjusted net, with no
current-holding baseline fetched or subtracted. It's a *level* screen mislabelled
as a *delta*.

### Is there a baseline source? — No clean one.
`opportunity_cost_scenarios` has no `current_net_expected_return`. Candidates for
the held symbol:
- `signals.expected_return` — model-derived but **gross / different horizon**, not
  comparable to the scenario's CGT-adjusted net.
- `theses.target` — a price target, **wrong unit** (not an annualised return).

Subtracting either would manufacture a delta from incomparable quantities — *worse*
than the honest level test because it looks principled while being wrong.

### Recommended fix — two phase
1. **Interim (ship now, no schema change):** rename `_MEANINGFUL_DELTA →
   _MEANINGFUL_NET_LEVEL`; correct docstring/comment to: "yellow when an
   alternative's *absolute* CGT-adjusted net expected return exceeds 5%; a level
   screen, not a delta vs the current holding." Removes the false claim immediately.
2. **Endpoint (schema-governed, Phase-5 producer):** add
   `current_net_expected_return NUMERIC(18,6)` to `opportunity_cost_scenarios`,
   populated by the producer using the **same CGT-friction model applied to the held
   position** (the producer already has thesis context + a CGT engine to compute the
   alt's `estimated_cgt_friction`). Then collector computes
   `delta = net - current` and tests `delta > _MEANINGFUL_DELTA`. Where `current`
   is NULL → explicit "baseline unavailable" note, **not** silent level fallback.

### Alternatives + trade-offs
- **(A) Reconstruct baseline at display time from `signals`.** No producer change;
  unit/basis mismatch → misleading delta. Rejected.
- **(B) Rename/redocument only.** Zero risk, immediately honest, never delivers the
  delta. Correct stopgap, not endpoint.
- **(C) Baseline column in the table (recommended endpoint).** Producer owns the
  comparable computation; collector stays a pure renderer. Cost: migration +
  Phase-5 producer change.

**Recommendation:** ship (B) now (false-claim fix is non-negotiable), schedule (C)
as the Phase-5 producer's responsibility.

### Tests
1. (Interim) docstring/constant no longer claim "advantage over current holding";
   alt net 6%, no baseline → yellow (level), test asserts documented == computed.
2. (Endpoint) alt 6%, current 4% → delta 2% < 5% → green (proves delta not level;
   old code flagged yellow).
3. alt 9%, current 2% → delta 7% → yellow.
4. current NULL → "baseline unavailable", not level fallback.
5. current negative, alt positive → large positive delta → yellow; sign correct.

**Open decision:** ship interim (B) now and defer (C) to Phase-5, or wait and do
(C) in one go? Recommend (B) now — the false claim is live.

---

## Item 3 — paper_trade weeks gate  (NEEDS-OWNER-DECISION)

> **IMPLEMENTED 2026-06-28 (B-refined: maturation AND cron-continuity;
> min_matured_runs=1, 14-day gap tolerance).** The NEEDS-OWNER-DECISION on the
> predicate is resolved: the `backend-architect`-defined success criteria were
> adopted. The old gate (≥4 runs each ≥4 weeks old → ~7 weeks under weekly
> cadence) is replaced by a decoupled two-part predicate: **maturation** (≥
> `min_matured_runs` runs ≥ `maturation_weeks`*7 days old, over `rebalance_runs`)
> AND **continuity** (the weekly `build_portfolio` cron actually observed the
> window — over `job_runs` status='success', no >14-day blackout, currently
> alive), via the new `_cron_was_continuous` helper. CLI message corrected. Files:
> `asxos/domain/portfolio/paper_trade.py`, `asxos/cli/portfolio.py`; tests in
> `tests/test_portfolio_paper_trade.py` (6 pure-continuity + 5 gate tests). The
> rest of this block is retained as the design record.

**File:** `asxos/domain/portfolio/paper_trade.py:235-270`.

### Problem
`has_enough_paper_weeks(min_weeks=4)` calls `list_evaluable_runs(weeks=4)` (runs
with `as_of <= today-28d`) then asserts `len(runs) >= 4`. That binds **two
independent conditions** to one number: ≥4 runs AND each ≥4 weeks old. Under weekly
cadence you reach ~1 evaluable run at 4 weeks, so the gate actually opens ~7 weeks
out — stricter than the M13.8 "4 weeks of sign-off" intent.

### Recommended semantics
The sign-off question is "≥4 weeks of observed paper-trade evidence?" → **time-based
with an explicit, decoupled minimum-run guard**:

> oldest run is ≥ `min_weeks` old  AND  run count ≥ `min_runs` (default 1)

```python
async def has_enough_paper_weeks(conn, *, min_weeks=4, min_runs=1, today=None) -> bool:
    # MIN(as_of) <= today - min_weeks*7  AND  COUNT(*) >= min_runs
```
Fetch `MIN(as_of)` and `COUNT(*)` from `rebalance_runs`. `list_evaluable_runs` is
unchanged (separate legitimate use: enumerating runs ready to evaluate). The bug is
purely the gate's count/weeks conflation.

### Alternatives + trade-offs
- **(A) Time-based: oldest run ≥4 weeks (recommended, `min_runs=1`).** Literal
  reading of "4 weeks". Risk: one early run then a gap passes → mitigated by
  `min_runs`.
- **(B) Count-based: ≥4 evaluable runs.** ~8 weeks to satisfy under weekly cadence
  (contradicts wording); a same-day backfill of 4 runs spuriously passes.
- **(C) Weeks-of-evidence spanning ≥N runs (current accidental behaviour).**
  Strictest; only right if M13.8 means "4 weekly observations each matured 4 weeks"
  — the brief does not say that.

### Edge cases
- Zero runs → `MIN(as_of)` NULL → False (don't flip the brief flag with no evidence).
- Exactly 28 days old → inclusive `<=` passes; match `list_evaluable_runs`' own `<=`.
- Same-day backfill of recent runs → fails under (A) until 4 weeks elapse (correct);
  passes under (B) (wrong).

### Tests
1. Single run `as_of=today-28` → True.
2. Single run `as_of=today-27` → False (inclusive boundary).
3. Zero runs → False.
4. Four runs all `today-1` → False under (A) (pins time-based).
5. `min_runs=4`, one old + three recent → False (count decoupled & enforced).
6. Regression contrast: 1 run 5 weeks old → old code rejected, new accepts.

**Open decision:** confirm the M13.8 intent — `min_runs=1` (pure time, recommended)
vs a real minimum-observation count. Needs the sign-off owner (James) to lock.

---

## Item 4 — fundamentals.market_cap migration  (READY — but production apply needs sign-off)

**Files:** `asxos/ingestion/fundamentals.py:55,89-93,96+` (propagate);
`migrations/0001_initial.sql:33` (`universe.market_cap`),
`migrations/0002_fundamentals_add_market_cap.sql:7` (`fundamentals.market_cap`);
precedent `migrations/0028_widen_research_dollar_columns.sql`;
counter `asxos/api/main.py:15` (`REQUIRED_MIGRATIONS = 82`).

### Problem
`fundamentals.market_cap` is `NUMERIC(18,6)` → max < 10^12. Market caps approach /
exceed this; written from EODHD `MarketCapitalization`. Research-store columns hit
the same wall and were widened to `NUMERIC(24,6)` in 0028; `fundamentals.market_cap`
was missed.

**Hidden second column (verified):** `universe.market_cap` (0001:33) is **also
`NUMERIC(18,6)`** and is fed from this column via `propagate_market_cap_to_universe`
(`fundamentals.py:96+`). Widening only `fundamentals` leaves the propagation step to
overflow on write. **Both must be widened in the same migration.**

### Migration — `migrations/0029_widen_market_cap_columns.sql`
```sql
-- 0029_widen_market_cap_columns.sql
-- Widen absolute-dollar market_cap columns NUMERIC(18,6) -> NUMERIC(24,6).
-- Mirrors 0028: 18,6 caps < 10^12; large-cap market caps approach/exceed it.
-- NOTE: unlike 0028 (empty research tables), fundamentals & universe are POPULATED,
-- so PG validates/rewrites the column — this is NOT metadata-only.
ALTER TABLE fundamentals ALTER COLUMN market_cap TYPE NUMERIC(24,6);
ALTER TABLE universe     ALTER COLUMN market_cap TYPE NUMERIC(24,6);
```
Widening precision while keeping scale (6→6) is value-preserving: (18,6) ⊂ (24,6),
so no existing value can fail validation; no fractional or integer truncation.

### Dependent objects — check before apply
- `current_holdings` view (over `holding_lots`) — unaffected (no market_cap).
- Run a catalog check (`list_tables` / `information_schema`) for any **view,
  generated column, or expression index** on `fundamentals.market_cap` /
  `universe.market_cap`. A plain NUMERIC widening needs no index rebuild (no
  operator-class change) and PG handles dependent views for a compatible type
  change; verify no expression index narrows the type.

### REQUIRED_MIGRATIONS bump
The counter is a **row count in the migrations-tracking table**, not the file number
(28 files ≠ 82). After applying 0029, read the observed post-apply count and set
`REQUIRED_MIGRATIONS` to **that exact value** (do not guess `+1`). Update the
trailing comment to reference 0029.

### Rollback — effectively forward-only
Narrowing back to (18,6) only succeeds if no interim value exceeds 10^12 — but the
whole point is to store values that don't fit (18,6). Document forward-only: to
revert you must first delete/clamp out-of-range rows. Matches 0028's posture.

### Production sign-off (CLAUDE.md MCP-driven management)
Applied via `mcp__supabase__apply_migration` on **populated** tables (column
rewrite/validation). Flag for explicit human sign-off before apply:
1. Run the dependent-object catalog check.
2. Capture before-image: `max/min/count(market_cap)` for both tables.
3. Apply in a low-traffic window.
4. Bump `REQUIRED_MIGRATIONS` to the observed post-apply count in the same change.
5. After-image verification (below). **Do not auto-apply.**

### Tests
1. Schema assertion: both columns report precision 24, scale 6.
2. Ingestion round-trip: `parse_fundamentals` with `MarketCapitalization =
   3_000_000_000_000` upserts without overflow.
3. `propagate_market_cap_to_universe` with a >10^12 source writes to `universe`
   without overflow (pins the second column).
4. Startup: `REQUIRED_MIGRATIONS` matches the live count (existing drift check covers
   it once bumped).

---

## Cross-cutting flags
- **Item 1** mixed-account-type lots and **Item 4** one-way rollback / production
  apply both warrant a hard-fail or explicit sign-off posture (CLAUDE.md #10 +
  MCP-driven management).
- **Item 4**'s hidden `universe.market_cap` must be widened in the same migration or
  `propagate_market_cap_to_universe` overflows — easy to miss.
- **Item 2**'s correct fix is owned by the Phase-5 producer (schema + producer); the
  collector-only fix is an interim honesty patch.
- **Item 3**'s `min_runs` default needs M13.8-owner confirmation before locking.

## Decisions needed from James
1. **Item 1:** mixed-account-type lots → hard-fail (recommended) or warn-flag?
2. **Item 2:** ship interim rename now + defer the baseline column to Phase-5
   (recommended), or wait and do the full delta in one change?
3. **Item 3:** `min_runs=1` pure-time gate (recommended) or a real
   minimum-observation count? What number?
4. **Item 4:** approve drafting migration `0029` and scheduling the production apply
   (the apply itself stays gated on your explicit go).
