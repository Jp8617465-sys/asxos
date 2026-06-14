# 03 — Architecture Trade-offs

> **Status: analysis only. No architecture decision is approved.** Each
> trade-off lists a *recommended default* — the conservative choice that
> minimises change during recovery — and a *revisit trigger*. See
> `09-decision-backlog.md` for the decision-owner view.

Format per trade-off: context · options · pros · cons · failure modes · what
breaks first · recommended default · revisit when · evidence required.

---

## TO-1 — Many Render crons vs master daily orchestrator

- **Context.** 22 jobs run as individual Render cron services. `render.yaml`
  declares 24 services; only 13 are live; 11 are declared-but-absent. The
  fan-out is the dominant drift surface.
- **Options.** (a) Keep independent crons; (b) one master daily orchestrator
  that runs the loop in sequence; (c) hybrid — orchestrator for the daily loop,
  independent crons for backup and weekly jobs.
- **Pros.** (a) failure isolation, simple mental model, independent retries;
  (b) single deploy surface, ordered execution, one place for drift; (c)
  isolation where it matters + ordering where it matters.
- **Cons.** (a) N drift surfaces, N healthcheck UUIDs, N env copies, ordering is
  implicit-by-schedule; (b) single point of failure, one OOM kills the whole
  loop, harder partial retry; (c) two patterns to maintain.
- **Failure modes.** (a) a cron silently stops being scheduled (the predecessor's
  `news-ingestion`/`earnings-sync` ghost-services); (b) orchestrator crash =
  total loop outage; (c) the seam between orchestrated and independent jobs.
- **What breaks first.** (a) drift + the absent monitoring tier; (b) memory on
  Render's 512MB tier when the loop runs in one process.
- **Recommended default.** **(a) keep independent crons + enforce
  `make check-drift`** for now. The drift problem is a *process* problem
  (services never created), not an architecture problem.
- **Revisit when.** Loop stable ≥1 month AND symbol count > ~2,000 AND the
  ordering-by-schedule becomes fragile.
- **Evidence required.** 1 month of `job_runs`; memory headroom data per job;
  a measured count of drift incidents.

## TO-2 — Render cron vs DB queue worker

- **Context.** Crons are time-triggered; a queue worker is event/work triggered.
- **Options.** (a) cron only; (b) DB-backed queue worker (a long-running service
  polling a `jobs` table); (c) both.
- **Pros.** (a) zero new infra, native to Render; (b) backpressure, retries,
  prioritization, decouples trigger from schedule; (c) cron seeds the queue.
- **Cons.** (a) no backpressure, no prioritization; (b) a new always-on service
  (cost + a new failure surface + idempotency contract); (c) most moving parts.
- **Failure modes.** (a) thundering-herd at 20:30 UTC if jobs overlap; (b) queue
  worker stall = silent backlog; (c) double-execution if both fire.
- **What breaks first.** (a) EODHD free-tier quota under burst; (b) worker
  liveness with no monitor.
- **Recommended default.** **(a) cron now.** A queue worker is a scale answer to
  a problem ASXOS does not yet have.
- **Revisit when.** > ~2,000 symbols, or per-symbol ingest needs prioritization/
  backpressure, or real-time data enters scope.
- **Evidence required.** Quota-exhaustion incidents; ingest durations vs the cron
  window.

## TO-3 — One orchestrator vs hybrid (orchestrator + independent backup)

- **Context.** Backup is the one job that must survive even if the rest of the
  loop is down — it is the disaster-recovery floor.
- **Options.** (a) backup inside the orchestrator; (b) backup always independent,
  regardless of loop topology.
- **Pros.** (a) one surface; (b) backup runs even if the loop/orchestrator is
  broken — the property that saved us this incident.
- **Cons.** (a) an orchestrator bug can take backup down with it; (b) one extra
  standalone service.
- **Failure modes.** (a) the exact incident we just had, except backup would
  also have failed; (b) negligible.
- **What breaks first.** (a) shared-fate between loop health and DR.
- **Recommended default.** **(b) backup always independent.** Backup already
  proved its value precisely because it is standalone and uses raw `pg_dump`
  (no Pydantic round-trip). Never couple it to loop topology.
- **Revisit when.** Never, unless backup itself needs orchestration (it does
  not).
- **Evidence required.** None — this is a settled DR principle.

## TO-4 — Env groups vs direct service-level env vars

- **Context.** Today each service holds its own copy of `DATABASE_URL` etc.
  Only a legacy "ASX Portfolio OS" env group exists, linked to a legacy service,
  with an ineffective value. The DATABASE_URL incident was a *propagation*
  problem: a rotated value reached some services and not others.
- **Options.** (a) keep service-level copies; (b) migrate all services to a
  shared env group for shared secrets.
- **Pros.** (a) no migration, full isolation, single-key PUT works today; (b)
  rotate once, propagate everywhere — directly prevents this incident class.
- **Cons.** (a) rotation is N updates and drift-prone (this incident); (b)
  Render `fromService`/group links apply at *creation* time, not on push — a
  documented footgun (guards-backlog P3-1); a bad group value breaks every
  linked service at once (blast radius).
- **Failure modes.** (a) partial propagation (what happened); (b) single bad
  group value = total outage.
- **What breaks first.** (a) the next credential rotation; (b) the migration
  itself, if done during recovery.
- **Recommended default.** **(a) keep service-level for now; (b) is the target
  state but DEFERRED** until the loop is proven. Do not migrate env groups
  during recovery.
- **Revisit when.** Loop stable; a planned credential rotation is upcoming.
- **Evidence required.** A documented, tested group-link behaviour on Render
  (the `fromService` timing footgun must be understood first).

## TO-5 — Dashboard-managed Render config vs render.yaml / Blueprint-managed

- **Context.** The predecessor drifted because services were created/edited in
  the dashboard, diverging from `render.yaml`. CLAUDE.md non-negotiable #2
  mandates render.yaml + git + `check-drift`.
- **Options.** (a) dashboard edits; (b) render.yaml/Blueprint as source of truth,
  MCP/API for mutations, `check-drift` enforced.
- **Pros.** (a) fast, visual; (b) auditable, reproducible, drift-detectable.
- **Cons.** (a) untracked drift — the original sin; (b) Blueprint sync does not
  auto-*create* services; manual creation step remains a drift entry point.
- **Failure modes.** (a) silent divergence (current 24/13/11 state); (b) forgot
  to create a declared service (current state again — the gap is creation, not
  config).
- **What breaks first.** (a) reconciliation impossible; (b) the human
  create-service step.
- **Recommended default.** **(b), already mandated.** Add: a checklist/automation
  that flags declared-but-absent services after every `render.yaml` change
  (guards-backlog P3-1 territory).
- **Revisit when.** Never on direction; iterate on the creation-gap automation.
- **Evidence required.** None on direction.

## TO-6 — Render native runtime vs Docker

- **Context.** The backup cron broke (build_failed ×3) because its build used
  `apt-get`; the fix (`2c3e50b`) removed `apt-get` and relies on `pg_dump` being
  present in the native image (`test_render_backup_build.py` asserts
  `pg_dump --version`).
- **Options.** (a) native runtime; (b) Docker images per service.
- **Pros.** (a) zero image maintenance, fast builds, Render manages the base;
  (b) full control over system deps (e.g. guaranteed `pg_dump`, lightgbm libs),
  reproducible.
- **Cons.** (a) implicit dependence on what the native image ships (the backup
  break); (b) image build/registry overhead, slower deploys, more to maintain.
- **Failure modes.** (a) a native-image change removes a binary you depended on;
  (b) image drift, registry auth.
- **What breaks first.** (a) system-binary assumptions (just happened); (b) build
  pipeline complexity.
- **Recommended default.** **(a) native runtime.** The backup fix already
  aligned to native; the ML jobs are the only candidates that might justify
  Docker later (lightgbm/sklearn system deps).
- **Revisit when.** ML retraining moves to Render and native lacks the libs, or a
  native-image change breaks a job again.
- **Evidence required.** A reproducible native-image dependency failure for a
  specific job.

## TO-7 — `job_runs` observability vs external-only logs

- **Context.** `job_runs` is the canonical in-DB completion tracker (the legacy
  `job_completions` table is explicitly *not used* per `job-conventions.md`).
  Backup currently writes **no** `job_runs` row.
- **Options.** (a) in-DB `job_runs` as source of truth; (b) external logs/
  Healthchecks only.
- **Pros.** (a) queryable, joins to data, powers `check_cron_health`; (b) zero
  schema, no DB dependency for observability.
- **Cons.** (a) requires DB up to observe (acceptable — DB up is a precondition
  anyway); (b) not queryable, no cross-job correlation, can't power the monitor.
- **Failure modes.** (a) a job that bypasses `JobMonitor` is invisible (backup
  today); (b) you find out from a missing email, late.
- **What breaks first.** (b) silent gaps; (a) only the bypass case.
- **Recommended default.** **(a) `job_runs` everywhere**, including a lightweight
  row for backup (a small insert after the shell script, not a rewrite). Keep
  Healthchecks as the out-of-band deadman.
- **Revisit when.** Never on direction.
- **Evidence required.** None.

## TO-8 — API/MCP observability vs manual dashboard checks

- **Context.** Recovery used read-only Render API + Supabase SELECT extensively;
  it worked well and left an audit trail.
- **Options.** (a) programmatic read-only API/MCP introspection; (b) manual
  dashboard inspection.
- **Pros.** (a) scriptable, repeatable, fingerprint-without-exposing-secrets,
  diffable; (b) zero setup.
- **Cons.** (a) API version quirks (e.g. `/logs` `resource=` param, per-service
  env-groups 404 in this API version); (b) not repeatable, error-prone, no
  audit trail.
- **Failure modes.** (a) an API endpoint shape changes; (b) human misreads a
  dashboard panel.
- **What breaks first.** (b) consistency.
- **Recommended default.** **(a) programmatic read-only**, exactly as used in
  recovery. Build a small read-only "drift/health" script (Lane A/B) rather than
  clicking.
- **Revisit when.** Never on direction.
- **Evidence required.** None.

## TO-9 — Auto review creation vs auto remediation

- **Context.** The governance line. "Event → review (a queued item + a suggested
  prompt)" is safe. "Event → production mutation (the system fixes itself)" is
  not, until a governance layer exists.
- **Options.** (a) auto-create reviews only (human acts); (b) auto-remediate
  (system mutates prod); (c) auto-remediate a whitelisted, reversible subset.
- **Pros.** (a) scales attention, keeps human in the loop, no new blast radius;
  (b) fastest MTTR; (c) bounded autonomy.
- **Cons.** (a) human is still the bottleneck (acceptable for solo + daily
  cadence); (b) reintroduces the exact silent-mutation risk the postmortem
  warns against; (c) whitelist scope-creep and the "is this really reversible?"
  problem.
- **Failure modes.** (a) review backlog ignored; (b) an automated fix makes a
  bad situation worse with no human gate; (c) a "reversible" action turns out
  not to be.
- **What breaks first.** (b) trust, irrecoverably, on the first bad auto-fix.
- **Recommended default.** **(a) auto-create reviews only.** No autonomous
  DB/Render/Git mutation until a signed-off governance layer exists.
- **Revisit when.** `review_queue` has months of human-handled history showing a
  small, provably-reversible class of actions worth automating.
- **Evidence required.** A track record of identical incidents resolved
  identically and reversibly by a human, before any of it is automated.

---

## Cross-cutting principle

Every default above is **"change the least during recovery."** The architecture
is mostly sound; the failures were *process* (services never created, a credential
rotated to some surfaces and not others) and *observability* (monitor written but
not deployed). Fix process and observability before reaching for new architecture.
