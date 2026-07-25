# Migration Plan

## Rules

- Re-read `migrations/`, live `supabase_migrations.schema_migrations`, and
  `asxos/api/main.py::REQUIRED_MIGRATIONS` before allocating a migration number.
- The dossier baseline is migration 0041 applied with observed required count 95. This is a
  snapshot, not permission to assume the next number.
- Migration files may be authored and tested in an attended sprint.
- Only James authorizes a remote `mcp__supabase__apply_migration` action.
- Apply migration, verify live shape/count, update `REQUIRED_MIGRATIONS`, and deploy matching code
  as one controlled sequence.
- Core-program migrations are additive. No table/column drop or historical rewrite is in scope.
- All monetary/statistical database columns use `NUMERIC(18,6)`.
- Single-user posture remains: no `user_id`, auth, multi-tenancy, or new RLS design.

## Planned migration groups

| Sprint | Additive persistence | Reuse |
|---|---|---|
| 1 | Proposal-envelope version/producer columns only if preflight proves the canonical JSON envelope cannot safely carry them; otherwise no migration | `agent_runs`, existing JSON proposal payload, governance events |
| 2 | No migration expected | `agent_runs`, `agent_evidence`, `theses`, `thesis_evidence`, governance events |
| 3 | Report-version header, canonical hash, case/revision/evidence linkage and version-linked sections/figures where migration 0040 JSONB is insufficient | `theses.report_sections`, thesis revisions/evidence |
| 4 | Review cycles and immutable point-in-time context snapshots | Existing governance/audit conventions |
| 5 | Blind assessments, findings, replacement-assessment links and deterministic eligibility decisions | Review cycles/context snapshots |
| 6 | Thesis/report monitor events and proposed-revision linkage | Existing invalidation jobs and JobMonitor |
| 7 | Versioned construction/risk/sizing/staging policies, effective security-classification/trading-rule snapshots, trading-calendar observations, portfolio snapshots, proposals, sizing decisions and typed lineage manifests | Existing holdings/lots/security master/theme loaders remain authoritative inputs; the snapshot stores IDs/hashes rather than cloning labels; never legacy score weights |
| 8 | Evaluator/evaluation-policy configs, dependency-isolation evidence, origin schedule, books and frozen starting snapshots | Legacy paper tables remain read-only |
| 9 | Paper intents, simulated orders/fills/settlements and append-only branch-ledger events | Existing Decimal monitor functions |
| 10 | Corporate-action/FX/tax-profile/cost attributes, immutable benchmark snapshots and daily branch NAV where existing stores cannot represent them | Existing corporate actions, FX, tax lots, fee inputs |
| 11 | Episode outcomes, cohort statistics, defect records and immutable operational/strategy gate decisions | Existing benchmark and job-monitor infrastructure |
| 12 | Staged order sets/orders, promotion decision and separate James disposition audits | Existing holdings remain authoritative; approval is not a fill |

Linked manual external-fill reconciliation is intentionally unsequenced after this programme. It
requires a separate contract and review; S12 does not infer a fill, write live holdings, or add a
broker-derived identifier.

## Authoring checklist

1. Inspect dependencies with `pg_depend` where an existing object is touched.
2. Write explicit constraints, enums/checks, indexes, comments, and timestamps.
3. Preserve immutable source/version/hash fields.
4. Add foreign keys/unique keys that make the typed lineage resolvable; a generic
   JSON hash map is not sufficient.
5. Use separate state columns for artifact validity, evidence tier, deployment
   visibility, staged-package state, and James disposition.
6. Use a clean Postgres integration fixture to apply the full migration chain.
7. Test invalid rows, `NUMERIC(18,6)` boundaries, canonical hashes and idempotent
   job/service retries.
8. Document live preflight, expected row/backfill counts, post-apply probes, and rollback.
9. Do not schedule a writer before its migration and code are live.

No migration in this dossier is pre-authorised. Each sprint must first inspect
the concrete repository and live dependency graph, then either document "reuse,
no migration" or produce one attended additive migration mission. A fresh Claude
must not allocate a number from this planning table.

## Rollback

The default rollback is code/job disablement plus forward repair. Additive tables remain for audit.
If a new table cannot be trusted, stop its writer, retain its rows, and mark outputs
`INCOMPLETE`/non-promotion. Destructive rollback requires a separate James-approved migration and
dependency audit.
