---
paths:
  - asxos/domain/screening/**
  - asxos/cli/screen.py
---

# Screening Conventions — asxos Tier 2a

Tier 2a mechanical screening: `screening_rules` (schema-only since migration 0001, zero
readers/writers until 2026-07-12) wired to a real evaluator. Read this before touching
`asxos/domain/screening/{types,evaluator}.py` or `asxos/cli/screen.py`. See
`docs/proposals/thesis-coverage-framework-2026-07-11.md` Tier 2a for the design rationale
and `asxos/domain/screening/evaluator.py`'s module docstring for implementation detail —
this file is conventions, not a restatement of either.

## Field/op whitelist — the SQL-injection safety boundary

Every `rule_json` condition is validated against `evaluator._FIELD_MAP` (closed column
whitelist) and `_ALLOWED_OPS`/`_TEXT_OPS` (closed op whitelist) inside `parse_rule()`,
BEFORE `compile_where_clause()` ever emits SQL. Column identifiers in generated SQL come
only from `_FIELD_MAP`'s hardcoded Python constants, never from `rule_json`-controlled
strings; `rule_json`-controlled *values* always reach the query as bound `$N` parameters.
A new screenable field means adding an entry to `_FIELD_MAP` explicitly — there is no
fallback path that accepts an unlisted field or op.

## Governed vs ungoverned — `screening_runs` is not investment content

`screening_runs` (draft migration `0038`, **NOT yet applied**) carries no
`governance_status` and no `agent_runs` linkage, unlike `theses`/`themes`/`macro_theses`.
It's a re-derivable data-filter audit log — same category as `prices`/`fundamentals`/
`portfolio_daily_snapshots` — and is deliberately excluded from
`scripts/backup_irreplaceable.sh`. Running a screen requires no governance gate; the
governance boundary starts one step later, when a human turns a `ScreenMatch` into a
`theme_holdings`/`thesis` entry via the existing manual CLI commands. Don't add
`governance_status` to `screening_runs` as an incidental change — that would be a
deliberate scope change to make, not a fix.

## `source_method` is permanently restricted to `curated_composite`

Migration `0038` (draft) adds `CHECK (source_method = 'curated_composite')` to
`screening_rules`. The column's old comment-only vocabulary also listed
`shap_threshold`/`surrogate_tree` — Model A artifacts from the prior, dead repo. Under
CLAUDE.md rule #11 (Model A quarantine, standing), no signal-derived screening rule may
ever be written. Never widen the `CHECK` to re-admit either value; a future non-Model-A
automated rule-extraction method needs its own new, explicitly-audited value.

## Decimal-only JSONB decode hazard

`screening_rules.rule_json` / `screening_runs.rule_json_snapshot` come back from asyncpg
as a raw JSON string (this repo registers no asyncpg JSONB codec). Always decode with
`evaluator.decode_rule_json()` (`json.loads(raw, parse_float=Decimal)`) — never a bare
`json.loads()`, which would silently turn a numeric threshold into a `float` before
`Decimal` ever sees it (CLAUDE.md #5). Same hazard documented in
`asxos/domain/theses/schemas.py` and `asxos/domain/macro_theses/service.py`.

## Scope: `au_equity` only, v1

The evaluator's base query hardcodes `u.security_kind = 'au_equity'` — not
author-controlled, not in `_FIELD_MAP`. ETF/LIC/hybrid screening needs its own
kind-appropriate criteria (asset-class/geography/breadth, not PE/PB fundamentals); that
taxonomy is undesigned, not a bug in this module — see
`docs/proposals/thesis-coverage-framework-2026-07-11.md` Tier 1's non-equity segmentation
note.

## Testing

`tests/test_screening_evaluator.py`: pure-function tests for `parse_rule`/
`compile_where_clause` (no DB), plus async tests against a mocked `asyncpg.Connection`.
The emitted SQL was additionally verified against a real throwaway Postgres instance with
adversarial seed data — mocked tests prove call shape, not planner-level correctness; see
`.claude/rules/portfolio-conventions.md`'s "Verification lesson" for why that distinction
has bitten this codebase before.
