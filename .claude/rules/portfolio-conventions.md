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

## Contamination-isolation model gate (plan H.1 CRITICAL-4 + governance Section 4.4 Step B)

`PortfolioService.build()` and `compose.collect()` no longer pick the
production model by a hardcoded name. Both query
`model_versions WHERE is_active = TRUE AND approved_for_allocation = TRUE`
and hard-fail on 0 rows (nothing approved) or >1 rows (multiple approved —
multi-sleeve blending is out of v1 scope). `approved_for_allocation`
(migration 0032) is orthogonal to `is_active`: `is_active` means "current
version of this model," `approved_for_allocation` means "this model is
allowed to influence the live portfolio/brief at all." A new model row can
exist, be activated, and be iterated on entirely within its own model
namespace without ever reaching the allocator or the brief, because that
requires a second, separate, explicit approval action.

In `build.py` the gate is Step 2 in `build()`'s docstring step list —
inserted ahead of the signals fetch (now Step 3) because that query
needs the gated model name to filter on (`WHERE model = $1` in both
signals branches). In `compose.py` the gate is the first statement
inside `collect()`'s connection block, for the same reason
(`production_model` feeds the regime and signal-change queries
downstream).

The CLI actions implied by both hard-fail messages —
`asx model approve <model> <version>` and `asx model revoke <model>
<version>` — **do not exist yet**. `asxos/cli/model.py` currently has
only `activate` and `list`. Until `approve`/`revoke` ship, the only way
to set `approved_for_allocation` is a manual UPDATE via
`mcp__supabase__execute_sql` (or a fresh migration, as 0032 did for the
one-time `model_a`/`v1_5` grandfather). Adding the CLI verbs is tracked
in `docs/next-session-backlog.md` under the governance-architecture plan,
Phase 1+ — not scoped to Phase 0/0.5.

---

## Governance-status gate on enter_thesis() (governance architecture Phase 1)

`enter_thesis()` (`asxos/domain/theses/service.py`) hard-fails unless
`governance_status = 'approved'` (migration 0033/0034), alongside its
existing status/thesis_text/stop_price/target_price checks. This is
orthogonal to the contamination-isolation model gate above: that gate
protects which MODEL's signals reach the allocator; this gate protects
whether a specific THESIS row is trustworthy enough to have capital
deployed against it, regardless of model. `governance_status` DEFAULTs to
`'approved'` for all human-authored theses (zero friction for the existing
CLI flow) — the guard is only load-bearing for agent-originated drafts,
which as of Phase 1 cannot yet be created end-to-end (no `ThesisProposal`
schema exists — see `asxos/domain/theses/schemas.py`). See
`docs/proposals/governance-first-architecture-2026-06-30.md` Section 4.1/4.7.

The transition from `pending_review` to `approved`/`rejected` is enforced at
the DB level, not just the service layer: `theses_governance_audit` (migration
0034) is this codebase's **first Postgres trigger**. It rejects any
`governance_status` UPDATE that lacks a matching `governance_events` row
written in the same transaction (checked via `pg_current_xact_id()`
equality). `approve_object()`/`reject_object()` in `service.py` are the only
functions that satisfy this — a direct `UPDATE theses SET
governance_status=...` fails loudly. Deliberately NOT a generic cross-table
function (see the migration 0034 header comment for why the originally
planned single-shared-trigger design across `theses`/`macro_theses`/`themes`/
`theme_holdings` fails at runtime — PL/pgSQL validates `NEW`/`OLD` field
references against the trigger's bound table even in unreached `CASE`
branches).

**Deferred** (`m14_candidate_governance_aware_revisit_cadence`):
`approve_object()` does not reset `revisit_due_at`/`last_revisited_at`, even
though the design doc describes agent-originated theses getting a 7-day
cadence that should widen to 30 days on approval. Nothing else in Phase 1
wires up a governance-status-aware revisit cadence, so implementing just the
reset in isolation would be untested and disconnected from any consumer.
Revisit alongside a real cadence mechanism, not as an isolated change.

---

## Phase 2a governance expansion — macro_theses/themes/theme_holdings triggers

Migration 0036 adds three MORE independent trigger functions
(`_check_macro_theses_governance_audit()`, `_check_themes_governance_audit()`,
`_check_theme_holdings_governance_audit()`), each modeled character-for-
character on the corrected `_check_theses_governance_audit()` (including the
`from_status = OLD.governance_status` check from day one, not as a later
retrofit). **Not a shared function with `TG_ARGV` dispatch** — the design
doc's Section 5.5 originally showed exactly that broken pattern
(`_check_governance_audit('macro_thesis')`), which is the same bug Phase 1
already found and fixed for `theses`; Section 5.5 has been corrected to match
this migration, not the other way around. `theme_holdings`'s trigger checks
`NEW.holding_id` (a new `BIGSERIAL UNIQUE` surrogate, migration 0035) rather
than the composite `(theme_id, symbol)` natural key — this surrogate exists
specifically so `governance_events.object_id` can reference one BIGINT
uniformly across all four governed tables.

**Module boundary decision**: `asxos/domain/macro_theses/` is its own new
package, not folded into `asxos/domain/themes/`, despite `themes.macro_thesis_id`
creating a dependency between them. A macro thesis has an independent
lifecycle driven by its own agent (`macro-economist`) — it can exist, be
approved, and be retired with zero themes ever linked to it
(`ON DELETE SET NULL`) — matching this codebase's existing one-package-per-
major-entity convention (`theses/` and `themes/` are already separate despite
`theses/service.py::open_thesis()` writing directly into `theme_holdings`).
`theme_holdings` governance (`approve_theme_holding()`/`reject_theme_holding()`)
stays in the existing `themes/service.py`, not a fourth package — it has no
identity outside a theme.

The `governance_events`-INSERT-then-UPDATE pairing — **in that order, and the
order is load-bearing** — that satisfies every one of these triggers is now a
single shared helper,
`asxos/domain/governance/transitions.py::apply_governance_transition()` —
extracted from the theses-specific version once a 4th call site (macro_theses)
needed the identical shape. Every audit trigger is `BEFORE UPDATE`: its
`EXISTS` check runs synchronously at the moment the UPDATE statement fires, so
the matching `governance_events` row must already be visible within the same
transaction *before* the UPDATE — INSERT-after-UPDATE is rejected by the
trigger every time. `table_name`/`id_column` are f-string-interpolated
(Postgres identifiers can't be `$N`-bound); every call site passes a hardcoded
literal, never caller-supplied input.

**Verification lesson (Phase 2a live-fire finding, encode-don't-repeat):** the
original helper (and Phase 1's shipped inline ancestor in `theses/service.py`)
did UPDATE-then-INSERT, and it passed every mocked unit test AND two full
review loops AND Phase 1's manual live verification — because mocked
connections don't enforce trigger semantics, and the manual check verified
hand-written SQL that happened to use the correct order rather than the actual
statement sequence the Python emits. Phase 1's `asx thesis approve|reject`
would have failed against the live trigger on first real use. The bug only
surfaced when Phase 2a's verification replayed the *exact Python-emitted
statement sequence* against prod (in a rolled-back transaction). Rule: any new
or changed code that performs a `governance_status` transition must have its
emitted statement ORDER live-verified against the real triggers at least once
(rolled-back transaction is fine) — mocked tests and hand-replicated SQL do
not count. `tests/test_governance_transitions.py` pins the order at the unit
level (a shared ordered call log across execute/fetchrow), but that only
guards the shared helper, not novel call patterns around it.

**Deferred** (`m14_candidate_macro_thesis_evidence_staleness_check`):
`macro_theses/service.py::approve_object()` does not check evidence staleness
before approval, unlike `theses/service.py::approve_object()`. theses' check
queries `thesis_evidence` directly (a table with a `thesis_id` FK);
`macro_theses` has no equivalent direct FK from `agent_evidence` — its
evidence link is indirect (`macro_theses.source_run_id` ->
`agent_runs.proposed_object.evidence_citation_ids` -> `agent_evidence.evidence_id`).
Land the join-based check when a second evidence-heavy discovery agent
(Phase 2c) makes the pattern worth generalising.

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

## `universe.is_active` overload — `security_kind` follow-up (`m14_candidate_security_kind_enum`)

`universe.is_active` is overloaded across three concerns: price-fetching, the
ASX-equity **ML universe** (every `WHERE is_active` reader — generate_signals,
retrain, sync_fundamentals, loader, coverage, …), and delisting/forced-sell. This
forces non-ASX-equity symbols (indices, held US equities) to be `is_active=FALSE`
and selected by *suffix* conventions instead: `.INDX` via `get_index_symbols()`,
held US holdings via `get_us_holding_symbols()` (open lots + `foreign_symbol_sql`),
and excluded from the forced-sell in `build.py`. `is_active=FALSE` therefore means
"not an ASX-equity-universe member," NOT "we don't hold/track it" (that's
`holding_lots` / `current_holdings`).

The clean end-state is a `security_kind` enum (`au_equity | us_equity | index`) so
each consumer selects by kind and the three suffix/flag conventions collapse into
one column. Deferred (`m14_candidate_security_kind_enum`): it's a 9+-site migration
plus a backfill; the suffix-based detection above is the incremental first step and
is correct until then. Build the enum when there is migration headroom (post-M13.8).

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
| 0 models both `is_active` and `approved_for_allocation` | `RuntimeError` in `PortfolioService.build()` / `compose.collect()` |
| >1 models both `is_active` and `approved_for_allocation` | `RuntimeError` in `PortfolioService.build()` / `compose.collect()` |
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
