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
  2026-06-29). Implemented in `dividends.py::check_45_day_warnings` + wired into
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
