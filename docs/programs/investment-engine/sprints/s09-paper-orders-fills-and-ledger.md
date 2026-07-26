# S09 — Causal paper orders, fills, settlement, and branch ledger

**Initiative:** EVAL-03
**Phase:** prospective-evidence infrastructure
**Weekly outcome:** a frozen S08 origin produces non-routable paper intents, causal
base/stress fill or no-fill outcomes, settlement and balanced append-only branch
ledger events
**Maximum evidence tier:** `PAPER_ONLY`
**Acceptance rows:** AC-37–40
**Depends on:** S08 config/origin/branch bundle; S07 proposal/sizing/staging policy
**Unlocks:** complete accounting and NAV in S10

## Authority boundary

These are evaluator records, not James staged orders and not broker orders. No
object contains a broker account, credential, endpoint, route, external order ID,
submission/modification/cancellation method or inferred real fill. No record writes
live holdings or cash.

## Normative contracts

- `paper-intent-v1`
- `paper-order-v1`
- `paper-fill-v1`
- `fill-model-v1`
- `trading-calendar-v1`
- `branch-ledger-v1`
- S08 evaluator/origin/branch contracts
- S07 proposal, sizing and staging policy references

## Paper state machine

```text
INTENT_RECORDED
  -> ORDER_OPEN
  -> ELIGIBLE_NEXT_SESSION
  -> PARTIALLY_FILLED
  -> FILLED | EXPIRED | CANCELLED_BY_PROTOCOL | NO_FILL
  -> SETTLEMENT_PENDING
  -> SETTLED
```

Every transition is append-only. A later correction appends a linked reversal and
replacement; it never edits a prior event. An order is never a position. Cash and
asset recognition follow the pinned trade-date/settlement-date accounting policy.

## Frozen fill model

The actual S08 provider/granularity decision controls implementation. If only
point-in-time daily OHLCV is licensed, v1 uses this conservative pre-registered
rule:

1. An order first becomes eligible on the next complete XASX session after
   `recommendation_at`; same-session fills are impossible.
2. Suspended, halted, missing-volume, zero-volume and incomplete bars produce no
   fill and a stable reason.
3. A buy limit is touched only when the unadjusted low trades through the limit by
   at least the effective tick; a sell limit only when the unadjusted high trades
   through by at least one tick. A touch without trade-through is no fill.
4. Base eligible quantity is:

   ```text
   floor_to_board_lot(
     min(remaining_quantity, session_volume * base_participation_rate)
   )
   ```

5. Stress quantity uses its separately ratified lower participation rate and
   wider trade-through buffer. The simulated price is the order limit, the
   conservative allowed price; spread/impact/latency penalties not observable in
   the bar reduce fill eligibility/quantity and are separately posted as the
   pinned cost model requires.
6. Opening/closing auctions are excluded unless the source explicitly separates
   auction prints and the fill model has ratified auction rules.
7. Partial fills continue until filled or policy expiry. No later bar rewrites an
   earlier no-fill/fill.

If quote/trade data is available, the contract instead freezes quote side, trade
condition, latency, queue/participation, impact and price-improvement rules. Claude
must not silently substitute a richer model.

## Intent, order, fill, and settlement invariants

- Intent quantity/direction is derived exactly from S07 sizing; it cannot be raised.
- Paper limit/stages/expiry are derived exactly from the ratified staging policy.
- Worst-case notional plus fees never exceeds the sizing cap.
- Base and stress branches share intent but use their named fill-model parameters.
- `filled_quantity <= intended_quantity`; all quantities are integer strings.
- Fill source record ID/hash, availability time and effective session are required.
- Settlement calendar/version and date are explicit.
- Unfilled/expired intended notional and opportunity cost remain in evaluation.

## Double-entry branch ledger

Every business event has balanced legs, branch/base currency, event/source hashes,
effective/recorded times and idempotency key. Minimum event kinds:

```text
ORDER_RESERVATION
TRADE_ASSET
TRADE_CASH_PAYABLE_OR_RECEIVABLE
BROKERAGE_PAYABLE
SETTLEMENT_CASH
SETTLEMENT_RELEASE
ORDER_EXPIRY_RELEASE
CORRECTION_REVERSAL
```

S10 adds corporate action, FX, tax and complete cost postings. Until then those
coverage flags are `INCOMPLETE`, so no development session is clean.

## Additive persistence

After migration preflight, add immutable intent/order/state-event/fill/settlement
and branch-ledger event/leg records. Database constraints enforce chronology,
positive quantities, no overfill, balanced currency legs, unique idempotency,
source hashes and no FK/write to live holdings.

## Existing code reuse

Brownfield survey per review finding DR-04. Every path and table named below was
read in the repository; where the repository cannot supply what this sprint
assumes, the row says so plainly rather than assuming a capability.

| What exists today | What this sprint needs | Gap | Decision required |
|---|---|---|---|
| `asxos/domain/portfolio/paper_trade.py` (`evaluate`, `evaluate_run_from_db`, `list_evaluable_runs`, `has_enough_paper_weeks`, `record_signoff`) — the M13.8 paper-trade evaluator | Causal intents, orders, eligibility, partial fills and settlement | It is a single-point P&L-vs-cash evaluator over a persisted `rebalance_runs` row: entry is assumed filled in full at the build-date close (`entry_close == reference_price`), there is no order, no eligibility session, no partial fill, no expiry and no ledger. It is also model-coupled through `target_allocations.signal_label`/`prob_up` | James: retire `paper_trade.py` with the legacy allocator, or keep it as a legacy scoreboard clearly outside the evaluator lineage. It cannot be extended into `paper-fill-v1` |
| `paper_portfolio_run_metrics`, `paper_portfolio_nav`, `paper_portfolio_position_perf` (`migrations/0024_paper_portfolio_perf.sql`) | Immutable intent/order/state-event/fill/settlement records and a balanced double-entry `branch-ledger-v1` | These are single-entry derived metrics keyed to `rebalance_runs(run_id)`, recomputed and UPSERTed per `eval_as_of`. Nothing in the repository is double-entry; there are no ledger legs, no idempotency keys and no append-only correction discipline | Disposition: coexist read-only or supersede. Either way the new ledger is additive and must not FK to `rebalance_runs` |
| `prices` (`open`, `high`, `low`, `close`, `volume`, `adj_close`; daily EODHD bars via `asxos/ingestion/prices.py` and `jobs/sync_prices.py`) | The frozen fill model's inputs: unadjusted low/high trade-through, session volume for participation, halt/suspension state, auction print separation | `high`/`low`/`volume` are present, so trade-through and participation are computable. **Halt and suspension state has no source** — the repo stores no security status feed, so the "suspended, halted" branch of the fill rule is unimplementable as written. Auction prints are not separated in a daily bar. `adj_close` exists and must not be used as the fill basis | James/PROC-01: procure a status/halt feed, or ratify that missing-bar and zero/absent `volume` are the only detectable no-fill conditions and rewrite rule 2 to say exactly that. Do not let "halted" silently mean "no bar" without saying so |
| `asxos/domain/prices/coverage.py::latest_complete_trading_day` | "Next complete XASX session after `recommendation_at`", per-stage `not_before`, and a settlement calendar | No holiday calendar (stated intentional in the module header) and **no settlement convention anywhere in the repository** — no T+2 constant, no settlement date column on `holding_lots` | James: XASX trading + settlement calendar source (shared with S07, S08, S12) |
| Security reference data: `universe`, `rs_security_master` | `floor_to_board_lot(...)` in the base-quantity formula, and the effective tick used for the trade-through buffer | **No board-lot and no tick data exists** (repo-wide search for `board_lot`/`tick_size`: zero hits). The fill formula as written cannot be evaluated | Same decision as S07: source board lot and tick, or ratify the checks as structurally blocked. This sprint inherits whatever S07 decides; it must not invent a default |
| `JobMonitor` + `job_runs`, and the repo's UPSERT-everywhere idempotency convention (`.claude/rules/job-conventions.md`) | An idempotent session processor that stays offline/hidden | Directly reusable for run tracking. The append-only + idempotency-key discipline this sprint needs is stricter than UPSERT-on-conflict and is new work | None. Reuse the job harness; do not reuse UPSERT semantics for ledger events |
| Execution firewall — current state | "No broker account, credential, endpoint, route, external order ID, submit/modify/cancel" | Verified: the repository contains **no broker or order-routing code**. Every occurrence of "broker" is either `holding_lots.broker_ref` (a free-text field from `asxos/domain/tax/import_csv.py`) or the phrase "broker report" in the thesis modules | None. The firewall is currently absolute; the test must pin that, and `broker_ref` must be excluded from the deny pattern so it does not produce a false positive |
| `_require_personal_use()` (`asxos/cli/_common.py`) / `require_personal_use_job()` (`asxos/jobs/_helpers.py`); `asxos/cli/holdings.py` — the only `INSERT INTO holding_lots` in the repository, fed by the `asxos/domain/tax/import_csv.py` parser | Proof that no evaluator record writes live holdings | There is exactly one live-holdings writer, so a static deny test is tractable and cheap | None. Pin `asxos/cli/holdings.py` as the sole permitted `holding_lots` writer and assert no evaluator module reaches it |

## Mission decomposition

### Mission S09-A — fill-model golden vectors (12h, contracts/tests PR)

- Audit provider granularity and legacy paper code for look-ahead, adjusted-close,
  signal allocator and live-holding assumptions.
- Freeze base/stress fill, auction/halt, partial, expiry, cancellation, settlement,
  correction and fee-reservation semantics with Opus/Ultra.
- Create no-fill, touch-only, trade-through, partial multi-day, full, halt,
  missing-volume, expiry and correction vectors.

### Mission S09-B — order/fill persistence and pure kernel (12h, product PR)

- Add append-only state records and constraints.
- Implement exact fill kernel and order state truth table.
- Property tests prove no same-session/future fill, no overfill and input-order
  determinism.

### Mission S09-C — ledger/settlement kernel (12h, product PR)

- Implement balanced events/legs, reservations and settlement.
- Crash/retry/failure injection proves fill and ledger are atomic.
- Branch isolation proves no mutation of live holdings or another branch.

### Mission S09-D — session processor and independent red-team (8h, product/evidence PR)

- Idempotent session command/job remains offline or hidden.
- Reconcile every golden branch and source hash.
- Fresh-context Opus/Ultra reviews microstructure, settlement, accounting,
  migration, broker boundary and Model A isolation.

## Negative behavior

- same-session, future/unavailable/revised source, stale manifest, invalid
  chronology, overfill, non-board-lot quantity or sizing mismatch: reject/block;
- missing price/volume/halt state: explicit no-fill or incomplete, never assumed;
- duplicate same idempotency/payload: return existing; different payload: integrity
  conflict;
- ledger imbalance: atomic transaction failure;
- later correction: linked reversal/new event, never mutation;
- broker field or live holding write: build/runtime circuit breaker.

## Observability

Emit evaluator/origin/branch/intent/order/fill/settlement/ledger identities/hashes,
intended/filled/unfilled notional, participation/capacity, fill latency, touch/no-fill
reason, reserved/settled cash, balance/replay result, incomplete coverage flags,
duration and status. Always label simulated fills as simulated.

## Rollback

Pause the hidden session writer, retain immutable records, mark affected branches
incomplete and forward-fix with a new fill/config lineage plus linked corrections.
Never delete or reprice a simulated fill. Live holdings remain unaffected.

## Definition of Done

- [ ] Every simulated fill uses a real later eligible source event.
- [ ] Base/stress/no-fill rules are exact and versioned.
- [ ] Partial fill, expiry and settlement are complete state machines.
- [ ] Every ledger event balances and crash/retry is atomic.
- [ ] Unfilled/expired intents stay in evaluation.
- [ ] Live holdings, Model A and broker surfaces are mechanically unreachable.
- [ ] Migration/reconciliation/recovery and full CI pass.
- [ ] Fresh-context Opus/Ultra red-team passes; combined worktree is clean.
