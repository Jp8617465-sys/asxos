# asxos — next-session backlog (updated 2026-06-30)

---

## P0 — HIGHEST PRIORITY: Multi-sleeve global architecture (2026-06-30)

Full design in `.claude/plans/greedy-jumping-unicorn.md` (plan file). This is the
next major development direction for the system. Summary of decisions made and
blockers found by the 2026-06-30 agent review (system-architect,
portfolio-invariant-guard, portfolio-coherence-reviewer).

### Sleeve architecture (agreed design)

**Thesis sleeve** (live now, primary): human conviction-driven, 6-18mo, drives
`theses`/`thesis_revisions`/`holding_lots`. Currently the only real sleeve.

**ML 5d paper sleeve** (always separate): Model A IC reverses at 21d — never
allocates capital. Lives as evidence input to the agentic thesis-drafter layer
(`asx thesis assist`). The 5 pm-review agents already surface SHAP for this.

**Factor/Value×Quality sleeve** (sequenced): earns weight via `alpha_eval` gate
(positive IC at 126/252d, `approved=TRUE` in `alpha_eval_runs` table). Phase 1
builds data infrastructure only — factor sleeve is disabled (`sleeve_weights_json`
stays `{"thesis": 1.0, "factor": 0.0}`) until the gate is met.

**Momentum sleeve** (sequenced after factor): same gate at 63d IC.

### Pre-implementation blockers (must fix before Phase 1 coding)

- **B1**: `sleeves.py` does not exist — Phase 1 must build it from scratch
- **B2**: `compose.py` regime query needs `WHERE model = 'model_a'` (not a
  tiebreaker — the proposed `signal_id` column doesn't exist)
- **B3**: `build.py` signal fetch is unfiltered by model — add
  `WHERE model = 'model_a'` to signal fetch AND `model_versions` fetch. Do this
  BEFORE Phase 1 rows land in `signals`.
- **B4**: `signals` FK needs a `model_versions` seed row for `factor_sleeve`
  before `factor_signal_writer` can write any rows
- **B5**: `factor_signal_writer.py` needs `ASXOS_PERSONAL_USE=1` gate (first check)
- **B6**: `factor_signal_writer` interface underspecified — define calibration
  mapping for `prob_up`, `confidence`, `signal_label`, `regime` from z-scores
- **B7**: `blend_sleeves()` must be Decimal-only (no numpy); add to module docstring
- **B8**: `sleeve_weights_json` needs DB CHECK constraint + closed key-set validator
  (same pattern as `score_weights_json` in `types.py:130-134`)
- **B9**: `revision_source='agent_draft'` is a CHECK constraint DROP+re-ADD, not ADD COLUMN
- **B10**: `alpha_eval_runs` table schema needed (JSONB report + scalar gate fields)
- **B11**: `compute_factor_scores.py` needs a staleness guard on `knowledge_date`
  before writing factor scores (hard-fail if `rs_fundamentals_pit` data > 14 days old)

### Financial coherence findings (portfolio-coherence-reviewer)

- **FC1**: Model A quarantine is documented but not enforced in `build.py` —
  `WHERE model = 'model_a'` fix (B3) is also the quarantine enforcement
- **FC2**: Value×Quality sleeve has zero evidence base; must earn weight via
  `alpha_eval` gate, not be deployed as Phase 1 production path
- **FC3**: **HUBS.NYSE requires a `thesis_revisions` entry NOW** — stop $230
  violated (close $184.47), pm-review = EXIT-CANDIDATE, no revision logged.
  Required by the framework. Run `asx thesis revise HUBS.NYSE`.
- **FC4**: Horizon mismatch (5d/63d/126d/252d) in one weekly cron — state the
  per-sleeve cadence explicitly or accept weekly as documented compromise
- **FC5**: Thesis-overrides-factor direction needs a decision: low-conviction
  thesis should NOT veto high-conviction factor signal (inverts conviction-weighting)
- **FC6**: Cross-market factor scoring needs normalisation methodology before any
  non-ASX symbol enters the factor sleeve

### Phase 1 execution sequence (when ready to start)

1. Fix `build.py` + `compose.py` model filters (B2+B3) — one commit, standard review
2. Populate research store: 5 sequential Render jobs
   (`sync_security_master → sync_corporate_actions → sync_financial_statements →
   derive_fundamentals_pit → compute_factor_scores`)
3. Migration 0032: `profiles.sleeve_weights_json`, `alpha_eval_runs` table,
   `model_versions` seed for `factor_sleeve`, `signals_model_as_of_idx` index
4. Build `sleeves.py` from scratch (Decimal-only, `blend_sleeves()`)
5. Build `factor_signal_writer.py` with calibration contract + all gates
6. Wire `sleeves.py` into `build.py` (with per-model staleness windows)
7. Schedule `asxos-compute-factor-signals` cron in `render.yaml` (disabled by gate)

### Required decisions (not code — before Phase 1 starts)

1. HUBS.NYSE revision event (see FC3 above — run `asx thesis revise HUBS.NYSE`)
2. Per-sleeve rebalance cadence: weekly for all (compromise), or per-sleeve crons?
3. Override direction: any-thesis-veto vs conviction-threshold gate vs no-override
4. Cross-market scope: confirm factor sleeve is ASX-only until normalisation is documented

---

# asxos — next-session backlog (open follow-ups, as of 2026-06-28)

Open items left after branch `claude/edmund-yong-subagent-wecr3g` (SMSF CGT
break-even fix + spec §5.4, 4 Design-MED items, shared-project audit, migrations
0029/0030). Grouped by priority. Each line: what + why + governing file / owner.

Source docs: `docs/db-shared-project-audit-2026-06-28.md`,
`docs/design-med-2026-06-28.md`, `docs/proposals/cgt-break-even-amendment-2026-06-28.md`,
`docs/backlog-test-coverage.md`, and CLAUDE.md "Known coverage gaps" /
"Known test environment gaps".

---

## P1 — spec-governed / correctness

- **TC-20 Div 296 cost-base reset (s 296-50)** — unimplemented, not just untested;
  `div296_reset_date` config field is consumed by nothing. Requires a
  spec-amendment-governed change (CLAUDE.md non-negotiable #8 + `tax-spec-conformance`).
  Tracked in CLAUDE.md "Known coverage gaps".
- ~~**TC-21 45-day franking warning (s 207-145)**~~ — **CLOSED** (session
  2026-06-29). Implemented in `dividends.py::check_45_day_warnings_smsf` + wired into
  `tax_view_smsf()`. Four tests cover the positive case and three boundary cases.
- ~~**SMSF ECPI-on-CGT numeric path is unverified**~~ — **CLOSED** (session
  2026-06-29). TC-24 added to spec §11 (v1.4) with matching test
  `test_tc24_smsf_ecpi_stacks_with_cgt_discount`. Implementation was already correct.

## P2 — endpoints / honesty completions

- **opportunity_cost Phase-5 producer** — add `current_net_expected_return
  NUMERIC(18,6)` to `opportunity_cost_scenarios`, populated by the producer with the
  same CGT-friction model applied to the held position, so the screen becomes a true
  delta (`delta = net − current`). The 2026-06-28 rename
  (`_MEANINGFUL_DELTA → _MEANINGFUL_NET_LEVEL`) only made the level-screen honest; it
  is a stopgap, not the endpoint. Governing: `docs/design-med-2026-06-28.md` Item 2;
  schema change → `backend-architect`.
- **Test-coverage sprint** — ~31 confirmed-untested gaps remain in
  `docs/backlog-test-coverage.md` (33 minus the two now closed: `cgt_break_even_price`
  and any others marked COVERED). Highest-value is P0 there: `api/main.py` lifespan /
  migration-drift / REQUIRED_MIGRATIONS has zero tests on success or RuntimeError
  branches (CLAUDE.md non-negotiable #1). See that doc for the full per-file list and
  the mock pattern.

## P3 — DB tidy-ups (optional, low risk) and CI / scope

- **Drop schema `archive_dropped_20260628`** — the 14 archived tables from the 0030
  wipe (CTAS backup). Drop once confident nothing is needed from it, to reclaim space.
  Governing: `docs/db-shared-project-audit-2026-06-28.md` §3.
- **Drop ~12 orphaned foreign trigger/helper functions** — left inert by 0030
  (e.g. `update_model_versions_timestamp` / `update_updated_at_column`). They were not
  dropped because dropping shared-named ones could affect kept asxos triggers; verify
  none are referenced by an asxos trigger before dropping. Governing: audit doc §3.
- **Drop empty `public.schema_migrations` leftover** — confirm it is the dead foreign
  leftover and not asxos's live migration-tracking table before dropping. Governing:
  audit doc (inventory §1) + the migration-tracking-table count behind
  `REQUIRED_MIGRATIONS`.
- **Make `full-check` a REQUIRED status check** — needs a paid GitHub plan to enforce
  server-side branch protection. Meanwhile the pre-push hook + CI signal cover it; the
  user runs `make install-hooks` locally. Governing: CLAUDE.md (CI / `full-check`).
- **break-even: thread the user's real marginal rate into the position monitor** —
  currently the disclosed `0.45` default flows through `cgt_break_even_price()`. Real
  per-user rate is **out of v1 scope**, noted only. Governing:
  `docs/proposals/cgt-break-even-amendment-2026-06-28.md` + spec §5.4.

---

## TC-20 kickoff (next session)

**Branch:** create a new `claude/**` branch from `main` after PR #9 merges.

**Task:** Implement TC-20 — Div 296 cost-base reset (s 296-50, spec §6.4/§6.5).

**State entering the session:**
- `SMSFConfig.div296_election_made` (bool) — consumed only for a static advisory
  string; the actual election branching logic is unimplemented.
- `SMSFConfig.div296_reset_date` (date) — never consumed anywhere.
- `holding_lots.cost_base_div296` column (migration 0001) — initialised to
  `cost_base_normal` on lot creation; never written post-reset or read in any
  gain-computation path.
- `div296_liability()` in `div_296.py` receives `ncg.net_capital_gain` (computed
  from `cost_base_normal`). The spec requires a separate Div-296 earnings figure
  computed from `cost_base_div296` when the election is made.
- The depreciated-asset warning body (`positions.py`) is a static string; actual
  detection of which lots are depreciated is not implemented.

**Files to read first:**
- `docs/foundation/spec/tax-alpha.md` §6.4, §6.5, §11 (TC-20 row absent — must
  be added as spec amendment)
- `asxos/domain/tax/div_296.py` (full)
- `asxos/domain/tax/positions.py` lines 148–160 (current Div 296 earnings path)
- `asxos/domain/tax/types.py` — `SMSFConfig`, `HoldingLot`, `Div296Outcome`
- `migrations/0001_*.sql` — `holding_lots` schema (dual cost-base columns)

**TC-20 worked example (spec §11):**
Acquired 2020-01-01 $50,000; MV at 2026-06-30 $80,000; disposed 2027-01-01
$100,000; SMSF accumulation; election made.
- Fund CGT (ordinary): gain $50,000 → 1/3 discount → net $33,333 → tax 15% = $5,000.
- Div 296 earnings (reset base): gain $20,000 → 1/3 discount → included $13,333.

**Mandatory implementation order:**
1. Read spec §6.4, §6.5, §11 in full.
2. Consult `tax-spec-conformance` agent on the proposed spec amendment.
3. Amend spec (v1.5): add TC-20 to §11 matrix; flesh out §6.4 disposal branching
   (ordinary CGT vs Div 296 paths); add §13 change log entry.
4. Implement in `positions.py`: when `config.div296_election_made is True`,
   compute a separate Div-296 gain using `cost_base_div296` and feed it (not
   `ncg.net_capital_gain`) into `div296_liability()`.
5. Add depreciated-asset detection (lot where `cost_base_div296 > current_mv` at
   reset date) to replace the static §6.5 advisory with a data-driven warning.
6. Tests: pin TC-20 worked example across all five output fields.
7. Full review loop (security-engineer / refactoring-expert / technical-writer)
   before committing. review-gate marker required.

**Governance:** CLAUDE.md non-negotiable #8 — spec amendment first, then code.
No schema changes needed (dual cost-base columns exist from migration 0001).
Estimated scope: 6–10 hours.
