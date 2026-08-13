---
title: Guards backlog
location: docs/maintenance/guards-backlog.md
auto_activate:
  agents:
    - system-architect
  skills:
    - feature-plan
priority_review_cadence: weekly during paper-trade window, monthly thereafter
owner: james
last_updated: 2026-05-28
docs_truth_correction: 2026-08-13 (SB0-01) — see the STALE PREMISE banner below
---

> ### ⚠️ STALE PREMISE — annotated 2026-08-13 (SB0-01 doc-truth sweep)
>
> **This file auto-attaches to `system-architect`, so its framing reaches architecture work
> unprompted — which is exactly why this banner is here rather than in a report.**
>
> Its risk narrative assumes a **live Model A signals → allocator → trade-proposal path in
> production**. Most sharply at `:107`: *"if `sync_prices` failed in the cron and
> `generate_signals` ran anyway, signals are generated on stale prices … Tomorrow's
> `build_portfolio` reads them and proposes trades against yesterday's reality … production
> trading proposals on stale inputs."*
>
> **That path is dormant and being retired.** (1) Model A was **shelved 2026-07-11** after the
> decay analysis found no usable edge on 19,032 matured signals
> (`docs/model-a-decay-analysis-2026-07-11.md`); CLAUDE.md rule **#11** bars its output from any
> real capital decision. (2) The allocator is mechanically gated on
> `model_versions.approved_for_allocation`, which was revoked — with 0 approved rows it
> **refuses to run** (`.claude/rules/portfolio-conventions.md` §Contamination-isolation).
> (3) Render was **deleted** 2026-08-12 (`docs/product/roadmap-state.md:116`), so the crons this
> file reasons about are not executing on the platform it assumes. (4) A Model A **retirement**
> programme (`P1-01`…`P1-05`) is in progress.
>
> **This banner does not retire the guards.** The *staleness-propagation* class of defect it
> describes is real and generalises to every scheduled job (it is the same shape as the
> 2026-08-05 news-brief incident: a guard that asserts on job status rather than on the
> artifact). Read the guards as **model-independent pipeline-integrity requirements**; do not
> read the Model-A-and-trade-proposal framing as a description of the live system.
>
> Noted for `P1-05`: this file carries live capital-adjacent Model A assertions with **zero
> `model_a`/`Model A` tokens**, so the token-driven sweep behind
> `docs/product/model-a-reference-manifest.md` cannot see it. See the truth map
> (`docs/product/doc-truth-map-2026-08-13.md` §6) for the false-negative finding.
<!--
================================================================================
CLAUDE CODE — AUTO-ACTIVATION DIRECTIVE
================================================================================
When this file is opened, attached as context, or referenced in a session:
  1. Invoke the `system-architect` agent for any item being designed or reviewed.
     This file's items are architectural, not feature work — they affect
     guarantees, not capabilities.
  2. Invoke the `/feature-plan` skill before promoting any item from TODO to
     IN-PROGRESS. Each item should have a feature plan generated against it
     before code is written.
  3. Auto-attached rules apply: portfolio-conventions.md, job-conventions.md,
     screening-conventions.md remain authoritative on Decimal discipline,
     hard-fail invariants, and pure/DB split.
  4. Do NOT promote items P2+ during the M13.8 paper-trade window unless an
     incident makes it P0. Operational discipline during the window is more
     valuable than backlog burndown.
If the routing layer does not auto-activate the above, the user runs:
  /route
  /feature-plan @docs/maintenance/guards-backlog.md
================================================================================
-->
# Guards backlog
Tracking item for guard-clause improvements identified during the 2026-05-28 architectural review of `asxos` job and API entry points. The review followed the cron-failure resolution (commit `40e0eac`) and the M14b REV-K landing.
The current guard inventory (hard-fail / soft-fail / weak-or-missing) is captured in `docs/architecture/guards-inventory.md`. This file tracks *additions and changes* to that inventory.
## How to work this backlog
1. Items are bucketed by priority. P0 items get worked before any new feature milestone opens. P1 items get worked during the M13.8 paper-trade window, in the spare attention that operational mode allows. P2+ items wait until post-signoff.
2. Every item has explicit acceptance criteria. An item is not "done" until those criteria are verifiable in a test, a Sentry rule, or a documented procedure.
3. Before opening an item, invoke `/feature-plan` against it and capture the plan inline. The plan supersedes the "Proposed implementation" stub in this file.
4. Items that touch external APIs or service boundaries should pass through `system-architect` review before implementation. Items that are pure additions to existing patterns (e.g. extending the assert_partial_success helper to a new job) skip the review.
## Triage summary
| Priority | Items | Total effort | Window |
|---|---|---|---|
| P0 | 3 | ~1 hour | Pre-paper-window. Land this week. |
| P1 | 4 | ~3-4 hours | During paper window (spare attention). |
| P2 | 6 | ~1 day | Post-M13.8 signoff. |
| P3 | 3 | Variable | Backlog; revisit quarterly. |
---
## P0 — Land this week (pre-paper-window)
### P0-1 — Aggregate failure threshold in resilient gather jobs
**Category:** Hard-fail (promoted from absent)
**Effort:** ~30 minutes including tests
**Files affected:**
- `asxos/jobs/_helpers.py` (new shared helper)
- `jobs/sync_fundamentals.py`
- `jobs/ingest_regulatory.py`
- `jobs/ingest_news.py`
- `jobs/ingest_sentiment.py`
- `tests/test_job_helpers.py` (new)
**Motivation.** All four resilient-gather jobs currently use the same per-symbol `return_exceptions=True` pattern, swallowing individual failures and logging them. None has an aggregate threshold. If EODHD returns errors for 80% of the universe one day (auth issue, rate limit, partial outage), the job exits 0 with 20% of data updated and 80% silently stale. Sentry alert volume looks normal; you find out a week later when a derived metric is wrong.
**Proposed implementation.**
```python
# asxos/jobs/_helpers.py
def assert_partial_success(
    results: list,
    *,
    threshold: float = 0.75,
    label: str,
) -> int:
    """Hard-fail if fewer than `threshold` of `results` succeeded.
    Returns count of successes. Raises RuntimeError below threshold."""
    n_ok = sum(1 for r in results if not isinstance(r, Exception))
    n_total = len(results)
    if n_total == 0:
        return 0
    ratio = n_ok / n_total
    if ratio < threshold:
        raise RuntimeError(
            f"{label}: only {n_ok}/{n_total} succeeded ({ratio:.1%} < {threshold:.0%} threshold)"
        )
    return n_ok
```
Wire into each job after the `gather`:
```python
results = await asyncio.gather(*tasks, return_exceptions=True)
n_ok = assert_partial_success(results, threshold=0.75, label="ingest_news")
monitor.rows_written = sum(r for r in results if isinstance(r, int))
```
**Acceptance criteria.**
- `assert_partial_success` lives in a shared helper module with full test coverage.
- Each of the four jobs calls it after its `gather`.
- Default threshold is 0.75; per-job override allowed via kwarg.
- A test exists per job that constructs a `results` list with the right proportion of exceptions and asserts the hard-fail fires.
- A separate test asserts the happy path (all success) returns the expected count.
**Dependencies.** None.
---
### P0-2 — Promote upstream_ok warnings to hard-fails in cron context
**Category:** Hard-fail (promoted from warn-and-continue)
**Effort:** ~20 minutes per job × 2 jobs = ~40 minutes
**Files affected:**
- `jobs/generate_signals.py`
- `jobs/ingest_sentiment.py`
- `tests/test_generate_signals.py`
- `tests/test_ingest_sentiment.py`
**Motivation.** The current behaviour: if `sync_prices` failed but `generate_signals` runs anyway (manual or cron retry), it warns and proceeds. The defensible argument is "I'm operating, I know prices are stale, let me through." The undefended argument is the automated path — if `sync_prices` failed in the cron and `generate_signals` ran anyway, signals are generated on stale prices and written to the `signals` table with a current `as_of`. Tomorrow's `build_portfolio` reads them and proposes trades against yesterday's reality. This is the worst class of silent failure: production trading proposals on stale inputs.
**Proposed implementation.**
Distinguish manual-run (explicit opt-in) from cron-run (hard-fail):
```python
parser.add_argument(
    "--allow-stale-upstream",
    action="store_true",
    help="Override upstream freshness check. Manual operator use only.",
)
args = parser.parse_args()
if not upstream_ok and not args.allow_stale_upstream:
    raise RuntimeError(
        "Upstream sync_prices failed (or no recent success in job_runs); "
        "refusing to generate stale signals. Use --allow-stale-upstream for "
        "manual override."
    )
if not upstream_ok and args.allow_stale_upstream:
    log.warning("Proceeding on stale upstream by explicit operator override.")
```
Same pattern for `ingest_sentiment.py` reading `ingest_news` upstream status.
**Acceptance criteria.**
- Cron path (no flag): hard-fails with diagnostic when upstream stale.
- Manual path (`--allow-stale-upstream`): proceeds with warning log.
- `job_runs` row records which mode was used.
- Render `render.yaml` startCommand does NOT include the flag (cron is hard-fail by default).
**Dependencies.** None.
---
### P0-3 — Top-level recovery in compose_brief
**Category:** Observability + soft-fail
**Effort:** ~15 minutes
**Files affected:**
- `jobs/compose_brief.py`
- `asxos/brief/fallback.py` (new, minimal)
- `tests/test_brief_fallback.py` (new)
**Motivation.** If `collect()` raises mid-execution (Postgres connection drop, asyncpg timeout, asyncio cancellation), the brief email doesn't send and there's no in-band signal. Sentry catches it — but Sentry alerts are out-of-band and you've exhausted that quota once already. The brief itself is the channel you read every morning; making sure *something* arrives is more important than the something being perfect.
**Proposed implementation.**
```python
async def main() -> None:
    monitor = JobMonitor(job_name="compose_brief", ...)
    async with monitor.run() as ctx:
        try:
            await init_pool()
            async with acquire() as conn:
                data = await collect(conn, as_of=date.today())
                html = render_html(data)
                await send_email(html, subject=...)
        except Exception as exc:
            log.exception("Brief composition failed; sending fallback")
            await send_fallback_email(exc)
            raise  # let JobMonitor record the failure
        finally:
            await close_pool()
# asxos/brief/fallback.py
async def send_fallback_email(exc: Exception) -> None:
    """Minimal failure notification. Bypasses the full template."""
    subject = f"[asxos] Brief composition FAILED — {date.today().isoformat()}"
    body = (
        f"The morning brief failed to compose.\n\n"
        f"Exception: {type(exc).__name__}: {exc}\n\n"
        f"Check Sentry for full traceback. Investigate before tomorrow's run."
    )
    # Direct Resend API call; no template dependency
    ...
```
**Acceptance criteria.**
- Any uncaught exception in `compose_brief.main()` produces a fallback email to the operator's inbox.
- Fallback email does NOT use the same template stack (must not depend on whatever broke).
- The `try` still re-raises so `JobMonitor` writes the failure row and Healthchecks reports red.
- Test simulates a `collect()` raising and asserts the fallback path fires.
**Dependencies.** None.
---
## P1 — During paper-trade window (spare attention)
### P1-1 — Migration version check inside each cron job
**Category:** Hard-fail (extending an existing pattern)
**Effort:** ~45 minutes
**Files affected:**
- `asxos/db/migration_check.py` (new)
- `asxos/api/main.py` (refactor to use shared helper)
- All cron entry points (`jobs/*.py`)
**Motivation.** Your API checks `REQUIRED_MIGRATIONS` at lifespan startup. Cron jobs don't. If you apply a migration that adds a column to `holding_lots`, redeploy the API, but a cron is mid-execution against the old schema, you get half-converted state. The blast radius of "API and crons running against different schema assumptions" is much larger than the API-alone case.
**Proposed implementation.** Extract the lifespan check into a shared `assert_migrations_at_or_above(conn, required: int)` helper. Call it from each job's `init_pool()` block.
**Acceptance criteria.**
- Shared helper has its own test file.
- Every cron entry point calls it before any business logic runs.
- The hard-fail message includes which migration is required vs which is applied.
**Dependencies.** None.
---
### P1-2 — External-service auth ping at lifespan startup
**Category:** Hard-fail (validity, not just presence)
**Effort:** ~1 hour
**Files affected:**
- `asxos/external/health.py` (new)
- `asxos/api/main.py` (lifespan)
- `asxos/ingestion/eodhd.py` (add ping)
- `asxos/email/resend_client.py` (add ping, if not present)
- `tests/test_external_health.py` (new)
**Motivation.** `BriefSettings` validates *presence* of Resend / EODHD keys, not *validity*. If a key is rotated and the new value is wrong (invalid format, expired token), the failure surfaces only when `send_email()` or `eodhd.fetch()` runs. For a daily-cron-driven product, time-to-detection is up to 24h.
**Proposed implementation.** Each external client exposes an `async def ping() -> bool` that makes a minimal authenticated call (`/me`, `/account`, or equivalent). API lifespan calls each at startup, hard-fails on auth error. Cron jobs do NOT call ping at startup (cost adds up) — they rely on the API having validated at last redeploy.
**Acceptance criteria.**
- Each external client has a `ping()` method.
- API lifespan calls all `ping()`s in parallel; hard-fails if any return False.
- Failure message identifies which service failed, with the underlying error.
**Dependencies.** None.
---
### P1-3 — Stale-section indicator in brief operational footer
**Category:** Observability
**Effort:** ~45 minutes
**Files affected:**
- `asxos/brief/compose.py`
- `asxos/brief/templates/brief.html.j2`
- `tests/test_brief_footer.py` (new)
**Motivation.** When a section is suppressed for staleness (news >24h, portfolio >2d), the brief omits the section silently. "The news section disappeared three days ago and I didn't notice" is a real failure mode in an unattended system. The brief is your in-band operational channel; it should tell you about its own degraded states.
**Proposed implementation.** Add a small "Section health" block at the bottom of the brief:
```
Section health (last ingest):
  Signals: 2026-05-27 ✅
  Tax actions: 2026-05-27 ✅
  Regulatory: 2026-05-27 ✅
  News: 2026-05-25 ⚠️ stale (suppressed)
  Portfolio: 2026-05-26 ✅
```
The collector returns a dict of `{section_name: last_seen_date}` regardless of whether the section rendered. Template iterates and applies the freshness warning.
**Acceptance criteria.**
- Every brief includes the Section health footer.
- A test asserts the footer renders even when all sections are empty.
- A test asserts a stale section shows the warning indicator with the actual last-seen date.
**Dependencies.** None.
---
### P1-4 — Aggregate cron staleness alert
**Category:** Observability
**Effort:** ~1 hour
**Files affected:**
- `jobs/check_cron_health.py` (new)
- `render.yaml` (new cron service)
- `tests/test_cron_health.py` (new)
**Motivation.** Sentry sees job *failures*. It does not see *missing* jobs — the failure mode where Render's cron scheduler itself stops triggering a job (rare but documented). A daily check that any expected-daily job hasn't run in >36h closes that gap.
**Proposed implementation.**
```python
async def main() -> None:
    expected = {
        "sync_prices": timedelta(hours=36),
        "generate_signals": timedelta(hours=36),
        "ingest_regulatory": timedelta(hours=36),
        "ingest_news": timedelta(hours=36),
        "ingest_sentiment": timedelta(hours=36),
        "compose_brief": timedelta(hours=36),
        "sync_fundamentals": timedelta(days=8),
    }
    async with acquire() as conn:
        rows = await conn.fetch(
            "SELECT job_name, MAX(completed_at) AS last "
            "FROM job_runs WHERE status='success' GROUP BY job_name"
        )
    last_by_job = {r["job_name"]: r["last"] for r in rows}
    now = datetime.now(timezone.utc)
    stale = []
    for job, threshold in expected.items():
        last = last_by_job.get(job)
        if last is None or (now - last) > threshold:
            stale.append((job, last))
    if stale:
        # Hard-fail so Sentry picks it up; also send direct email
        raise RuntimeError(f"Stale crons: {stale}")
```
Cron schedule: daily at 22:00 UTC (~8:00 AEST), after all other crons should have completed.
**Acceptance criteria.**
- New `check_cron_health` service in `render.yaml`.
- Stale check covers all 7 (or N) expected-daily jobs.
- Hard-failure surfaces in Sentry AND sends a direct fallback email (same pattern as P0-3).
- A test asserts the stale detection works on a synthetic `job_runs` table.
**Dependencies.** P0-3 (uses the same fallback email pattern).
---
## P2 — Post-M13.8 signoff (operational maturity)
### P2-1 — Allocator output sanity assertions
**Category:** Hard-fail (defence in depth)
**Effort:** ~1.5 hours
**Files affected:**
- `asxos/domain/portfolio/rebalance.py` (assemble_result extensions)
- `tests/test_rebalance_sanity.py` (new)
**Motivation.** The constraint engine guarantees per-name cap, sector cap, and target-sum invariants. But a future refactor could introduce a bug that violates them. Asserting at the output boundary catches the bug before the trade list reaches the brief.
**Proposed checks at `assemble_result`:**
- Total proposed_trades AUD ≤ capital_aud × (1 + leverage_cap).
- No single proposed_trade > per_name_cap × capital_aud × (1 + leverage_cap).
- No sell exceeds the held quantity for that symbol.
- Proposed cash position is non-negative.
- No proposed_trade has a None or zero reference_price.
- Sum of target_weight across target_allocations + cash_floor_pct ≈ 1 + leverage_cap (within Decimal precision).
**Acceptance criteria.** Each check raises a distinct error; each has a test that triggers the failure.
**Dependencies.** None. This is purely additive.
---
### P2-2 — Pydantic boundary models for external API responses
**Category:** Hard-fail (shape changes)
**Effort:** ~3 hours
**Files affected:**
- `asxos/ingestion/eodhd_models.py` (new)
- `asxos/ingestion/eodhd.py` (use new models)
- All EODHD-consuming code (parse functions)
**Motivation.** External APIs change. EODHD adds a field, removes a field, changes a date format. `_parse_sentiment`'s three-shape defensive helper is exactly this pattern, ad hoc. Generalising via Pydantic models at the boundary means schema changes hard-fail at parse time with a clear "shape changed" error, not deep in aggregation logic with a `KeyError` 200 lines later.
**Proposed implementation.** One model class per endpoint (`NewsItemRaw`, `SentimentEntryRaw`, `FundamentalsRaw`, etc.). `strict=True`. Parse at the EODHD client boundary, raise on validation failure.
**Acceptance criteria.** Every EODHD endpoint that's currently consumed has a boundary model. Validation errors hard-fail with the field path. Existing `_parse_sentiment` defensive code can be removed.
**Dependencies.** None.
---
### P2-3 — Idempotency audit of ingest jobs
**Category:** Documentation + assertion
**Effort:** ~2 hours
**Files affected:**
- `docs/architecture/idempotency.md` (new)
- Tests added per job that runs the same job twice and asserts identical end-state
**Motivation.** What happens if `ingest_news` runs twice (Render retry, manual re-run)? `UNIQUE(url)` protects you, but the failure mode is "constraint violation, transaction rolls back, partial ingest." Each ingest job should have a documented idempotency story and a test enforcing it.
**Acceptance criteria.** Each ingest job has either `ON CONFLICT DO UPDATE` or a documented "second run is a no-op" story. Each has a test that runs the job twice in a row and asserts no error and identical end-state.
**Dependencies.** None.
---
### P2-4 — Decimal-contamination test
**Category:** Test (precision guard)
**Effort:** ~1 hour
**Files affected:**
- `tests/test_decimal_purity.py` (new)
**Motivation.** Somewhere in the pipeline a Decimal could pick up float contamination — usually at a JSONB roundtrip or an asyncpg boundary. Not a runtime guard; a test that asserts no `float` instance appears in `RebalanceResult`, `ProposedTrade`, `AllocationTarget`, or `Profile`.
**Proposed implementation.** Use `dataclasses.asdict` + recursive type check. The test seeds the DB, runs `build_portfolio`, then walks every dataclass attribute and asserts no float values.
**Acceptance criteria.** Test exists and is part of the default test run. CI fails if float contamination is introduced.
**Dependencies.** None.
---
### P2-5 — Time-of-day awareness in build_portfolio
**Category:** Soft-fail (warn-and-document)
**Effort:** ~30 minutes
**Files affected:**
- `asxos/domain/portfolio/service.py`
- `tests/test_portfolio_service.py`
**Motivation.** If `build_portfolio` runs at 23:00 AEST Friday, markets are closed; prices are stale by definition. The job would produce a Saturday-morning proposal you can't act on until Monday. Probably fine, but worth a warning citing the actual `signals_as_of`.
**Acceptance criteria.** When `build_portfolio` runs outside ASX hours, the result includes a warning string in `summary['operational_warnings']`. Brief surfaces the warning when present.
**Dependencies.** None.
---
### P2-6 — External-service convention file
**Category:** Documentation
**Effort:** ~30 minutes
**Files affected:**
- `.claude/rules/external-service-conventions.md` (new)
**Motivation.** The `get_client()` API key check pattern your `eodhd_api_key` fix established is now the canonical example for external-service clients. Capture it in a conventions file before the next client is added (M16 LLM summariser, or whatever consumes a news-summary model). Auto-attach via path pattern `asxos/ingestion/**` and `asxos/external/**`.
**Acceptance criteria.** File exists, documents the pattern, includes the canonical `eodhd.py:get_client()` example. Referenced from CLAUDE.md router block.
**Dependencies.** None.
---
## P3 — Backlog (revisit quarterly)
### P3-1 — Render fromService gotcha documentation
**Category:** Documentation
**Effort:** ~15 minutes
**Motivation.** Render's `fromService` env var links in `render.yaml` are applied at service *creation* time, not on subsequent pushes. This is the failure mode that caused the cron failure saga. Document it in `.claude/rules/render-conventions.md` (or create the file) so it doesn't recur in 6 months.
**Acceptance criteria.** A short prose entry in `render-conventions.md` with the symptom, the diagnosis, and the workaround (use `envVars` with `sync: false` + upload via Render MCP).
---
### P3-2 — Trade-list reasonableness sanity check (semantic, not arithmetic)
**Category:** Soft-fail (warn)
**Effort:** ~2 hours
**Motivation.** Arithmetic sanity checks (P2-1) catch invariant violations. Semantic sanity checks catch "this is technically valid but probably wrong" — e.g. a single proposal that turns over 80% of the portfolio in a day, or a sell of an entire position based on a single signal flip. Surface as warnings in the brief, not hard-fails.
**Proposed checks:** turnover-as-percent-of-capital warning thresholds; concentration-shift warning thresholds; "this is the first sell of this symbol in 90 days" indicator.
---
### P3-3 — Replay log for proposed trades
**Category:** Observability (audit)
**Effort:** ~half a day
**Motivation.** Every proposed_trade should be traceable to the exact signal row, model_version, profile state, and external-data freshness that produced it. The data exists in five tables; reconstructing is tedious. A new view `v_proposed_trade_provenance` that joins everything for one trade_id would make audits trivial. Worth doing once the AFSL conversation matures (Path A → Path B) because explainability obligations get teeth.
---
## Changelog
| Date | Change |
|---|---|
| 2026-05-28 | Initial file. 16 items captured from the post-`40e0eac` architectural review. |
## Cross-references
- `CLAUDE.md` non-negotiable #1 (hard-fail discipline)
- `CLAUDE.md` non-negotiable #2 (render.yaml + check-drift)
- `CLAUDE.md` non-negotiable #5 (NUMERIC(18,6) Decimal)
- `.claude/rules/portfolio-conventions.md` (Decimal purity, rationale_tags schema)
- `.claude/rules/job-conventions.md` (JobMonitor pattern, init_pool/close_pool)
- `docs/architecture/guards-inventory.md` (the source-of-truth inventory)
- `docs/build/M13_BUILD_GUIDE.md` (M13.8 paper-trade window is the binding gate for P2+ work)
