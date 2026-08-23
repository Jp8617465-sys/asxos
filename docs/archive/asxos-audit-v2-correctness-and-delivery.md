# asxos: Correctness & Delivery Audit

**Prepared:** 23 August 2026 · supersedes `asxos-delivery-diagnostic.md` (23 Aug), which is folded in below
**Scope:** repo-wide static analysis of `asxos-main` (781 files, 7.7 MB)
**Method:** static analysis plus one executed lint run. No git history in the archive, so commit cadence is inferred from document references. **No live database access**, so every claim about production state is derived from what the repo asserts about production, not from production itself. That distinction turns out to be the finding.
**Out of scope by instruction:** regulatory/AFSL exposure. Sole-user status resolves the compliance question. It does not resolve the execution-safety question, which is retained below as §F.

---

## Executive summary

Two audits, one root cause.

The first pass asked how work moves through the repo and found that you had rebuilt a ticketing system in prose. This pass asked whether the system is *correct*, and found the same failure mechanism operating one layer down, with money attached.

**The unifying finding: asxos maintains a large set of claims about itself in prose, and there is no mechanism forcing those claims to match reality.** Migration headers say DRAFT for migrations that are live in production. `REQUIRED_MIGRATIONS = 97` against 43 migration files on disk. `ASXOS_TZ = "Australia/Sydney"` is set in two workflows and read by exactly zero lines of code. The s766B firewall exists only as markdown. Proposal status fields are wrong in both directions.

Every one of those is the same bug: **a claim in one place, the truth in another, and nothing that fails when they diverge.**

The good news is genuinely good, and it matters for where you spend effort. **The money math is exemplary and you should not touch it.** `NUMERIC(18,6)` on every price, quantity and cost base. `Decimal` throughout Python with explicit "Never float()" contracts. CGT discount uses `relativedelta(years=1) + timedelta(days=1)` and the docstring explicitly forbids the naive `>= 365` approach, with leap-year boundary tests to prove it. SMSF discount is an exact `Fraction(1,3)`. Survivorship bias is handled by ingesting delisted symbols. When Model A turned out to have no edge (+0.032 at 5d, −0.030 at 21d across 19,032 matured signals) you measured it, wrote it up honestly, and quarantined it.

**The defect is not in the code that calculates. It's in the code and configuration that describe.**

Highest-severity finding: your production schema cannot be reconstructed from this repo, and the guard designed to catch that cannot detect it by construction.

---

# Part I — Correctness findings

Severity is by money-at-risk and detectability, not by effort.

## P0-1. Production schema is unreproducible from the repo

`asxos/api/main.py:14`:

```python
REQUIRED_MIGRATIONS = 97  # bump each time a new migration is applied; ...
                          # observed count from supabase_migrations.schema_migrations
```

There are **43** `.sql` files in `migrations/`. Production reports **97** applied rows. Even allowing for Supabase's own bootstrap migrations inflating the count, the repo cannot tell you which 97 those are.

The guard:

```python
if count < REQUIRED_MIGRATIONS:
    raise RuntimeError(...)
```

This is a `<` comparison on a **count**. By construction it cannot detect:

- a migration applied to production that is not in the repo (count rises, guard passes)
- a migration substituted for another (count unchanged, guard passes)
- any divergence in migration *content*

`asxos/secondbrain/contradictions.py:132` already documents this limitation in a comment. The knowledge exists; the control doesn't.

The number itself is hand-maintained ("bump each time"), which is the prose-control pattern again, wearing a Python variable as a disguise.

**Why this is P0:** `holding_lots` carries your actual CGT cost bases. If production schema and repo schema have silently diverged, the code computing your tax position is running against a shape it doesn't fully describe. You would not find out from a test.

**Fix:** replace the count guard with a name-and-checksum comparison. Query `supabase_migrations.schema_migrations` for the applied migration *names*, diff against `ls migrations/*.sql`, fail on any asymmetry in either direction. Roughly 30 lines. Run it in CI, not just at app startup.

## P0-2. Six migration files carry false state headers

| File | Header claims | Actual (per your own 2026-08-22 finding) |
|---|---|---|
| `0039_agent_readonly_role.sql` | DRAFT — NOT APPLIED | **Applied.** Role `asxos_agent_ro` exists in production |
| `0043_price_revisions.sql` | PRODUCTION-READY | **Applied** 2026-08-12 |
| `0044_fundamentals_pit_currency.sql` | DRAFT — NOT APPLIED | **Applied** 2026-08-21 |
| `0038_screening_evaluator_wiring.sql` | DRAFT — NOT APPLIED | unverified |
| `0041_macro_thesis_learning_loop.sql` | DRAFT — NOT applied by the build session | unverified |
| `0045_segment_map.sql` | DRAFT — NOT APPLIED | correct, per your doc |

Numbers **18** and **42** are absent from the sequence entirely (42 is reserved by parked PR #80; 18 is unexplained).

A file header is a claim about production state stored in a file that production never reads. It will always drift. **Delete the headers.** The applied-state source of truth is the database, surfaced by the check in P0-1.

## P0-3. Backups are never automatically verified

`scripts/backup_irreplaceable.sh` dumps 14 tables — `holding_lots`, `decisions`, `theses`, `thesis_revisions`, `governance_events` and others. The scoping judgement is right: these are the human-entered records that cannot be re-derived from EODHD.

The restore drill exists in `backup.yml`. Its trigger:

```yaml
if: ${{ github.event_name == 'workflow_dispatch' && inputs.restore_drill }}
```

Manual dispatch, plus an explicit opt-in flag. **It is never scheduled.** So the dump is written daily and its restorability is verified only when someone remembers to ask.

Compounding this, the workflow's own header records that an `apt-get` failure "masked the pg_dump version mismatch above for the entire life of this workflow." The backup has already had a silent-failure period.

An unverified backup is a hypothesis. `holding_lots` is the most valuable data in the system and the only data you cannot rebuild.

**Fix:** schedule the restore drill weekly. Assert row counts on the restored copy. One line of YAML plus a schedule block.

## P1-4. `ASXOS_TZ` is a dead configuration knob

`asxos/config.py:36` defines `asxos_tz: str = "Australia/Sydney"`. Two workflows set it explicitly in `env:`.

**No code reads it.** The only occurrence of `asxos_tz` anywhere in `asxos/` or `jobs/` is its own definition.

A setting that appears to control timezone behaviour, is deliberately set in production workflows, and does nothing, is worse than no setting — it creates false confidence that timezone is handled.

## P1-5. Two competing date-resolution strategies, one of them clock-anchored in the wrong timezone

58 uses of `date.today()` across `asxos/` and `jobs/`. `date.today()` resolves against the *system* timezone. GitHub Actions runners are UTC.

`daily-brief.yml` fires at `30 20 * * 0-4`. The arithmetic:

| Cron fires (UTC) | Sydney local | `date.today()` on runner | Actual Sydney date | Match? |
|---|---|---|---|---|
| 2026-07-15 20:30 | 2026-07-16 06:30 AEST | 2026-07-15 | 2026-07-16 | **No** |
| 2026-01-15 20:30 | 2026-01-16 07:30 AEDT | 2026-01-15 | 2026-01-16 | **No** |

Off by one day, year-round, in both AEST and AEDT. `compose_brief.py:154` falls back to `date.today()` and the workflow passes no `--as-of`.

The nuance that makes this worth fixing rather than panicking about: **`snapshot_portfolio.py` does it correctly.** Its docstring: *"The auto daily run anchors as_of to the latest COMPLETE trading day in `prices`."* Data-anchored, not clock-anchored. Immune to runner timezone entirely.

So two strategies coexist. One is robust; the other is a day behind Sydney. They can disagree about what "today" means within a single pipeline run, and the brief is the artifact you actually read each morning.

I cannot determine from static analysis whether this manifests as a visible defect — some call sites may want "the last completed trading day," for which UTC-yesterday is *accidentally* close to right. That accidental correctness is the hazard: it works until a DST boundary or a Monday makes it not work, with no test that can tell the difference.

**Fix:** adopt the `snapshot_portfolio` pattern everywhere. Date should be derived from data (latest complete trading day) or passed explicitly, never read from a wall clock. If a clock is unavoidable, read `settings.asxos_tz` — which finally makes P1-4's knob real.

## P1-6. Database session timezone is unpinned, and the code knows it

`asxos/brief/compose.py:694-698` contains this, which is better analysis than most production systems ever get:

> Every boundary is explicitly `timestamptz` at UTC. `$1::date ± INTERVAL` alone yields `timestamp without time zone`, which Postgres compares to `finished_at` by converting through the session `TimeZone` GUC — unpinned here, since `asxos/db.py::init_pool` passes no `server_settings`. Setting the database or role timezone to `Australia/Sydney` would then slide this window seven hours off the 20:30–22:30 UTC pipeline it exists to cover, **with no error and no failing test**.

I verified the premise: `init_pool` passes no `server_settings`. The invariant holds by luck — nobody has set a role-level timezone.

**Fix:** pass `server_settings={'timezone': 'UTC'}` in `init_pool`. One line, converts a documented hazard into an enforced invariant. This is the cheapest fix in the report.

## P1-7. Alert delivery failures are silent and unobservable

Three sites swallow exceptions with bare `pass`:

- `asxos/jobs/utils/job_monitor.py:189` — healthcheck ping. **Correct**, and the comment explains why: a failed ping must not mask the job's own exception.
- `jobs/validate_price_data.py:59` — alert email send
- `jobs/check_au_positions.py:146` — alert email send

The latter two are the problem. If Resend is down, the API key rotates, or `BRIEF_TO_EMAIL` is wrong, the alert vanishes and nothing records that it vanished. **The failure mode of an alerting system is precisely the one you cannot afford to be silent.** You would experience this as "the system has been quiet lately."

**Fix:** keep the swallow (correct — don't let a notification failure crash the job) but write a `job_runs` row or increment a counter on the failure path, so alert-delivery failure is itself detectable.

## P2-8. Execution-safety controls exist only as prose

You've set the regulatory question aside, which is fair. But `personal-advice-firewall-amendment-2026-07-18.md` encodes three constraints that are about *your money*, not about ASIC:

1. no autonomous execution
2. staged position sizes must come from a deterministic, model-independent sizer, "sourced verbatim, never originated by an LLM"
3. every staged number Decimal-exact and cited

Grep for `personal_advice`, `advice_firewall`, `not_advice`, `general_advice` across `asxos/` and `tests/`: **zero hits.**

Constraint 2 is the one that matters. It exists to stop an LLM inventing a dollar figure that reaches your broker. That is a safety property, and right now it is enforced by a markdown file marked DRAFT since 18 July, in a repo where this audit has demonstrated markdown status fields are unreliable in both directions.

**Fix:** make it a test. Assert that any staged order's size field traces to the deterministic sizer's output, and that the code path constructing it is unreachable from an LLM-generated value. If that assertion is hard to write, that difficulty *is* the finding.

## P2-9. Post-Model-A decision provenance is unclear

Model A is quarantined under rule #11 for measured absence of edge — correct call, honestly made. But `personal-advice-firewall-amendment` notes "the current allocator's sizer is dormant under rule #11."

I cannot determine from the repo what currently drives a buy/hold/trim decision, or whether that replacement has been validated to the standard Model A was held to. It may be entirely deliberate (human judgement in the loop, system as evidence-assembler). But the same measurement rigour applied to Model A should apply to whatever succeeded it, and I can't find that measurement.

**This is the most important open product question in the repo** and it is not answerable from the code.

## Tooling note (not a defect)

The repo pins `ruff==0.7.0`. I ran current ruff (0.16.4) and got 11 findings — `C420`, `RUF022`, `RUF043`, `RUF059`, `UP047`. **All are rules that did not exist in 0.7.0, and all are cosmetic.** Your CI passes. This is version skew, not breakage. Worth noting only because a lint gate pinned roughly a year back is a slowly-decaying signal.

---

## Confirmed healthy — do not spend effort here

Listed because an improvement programme's main risk is wandering into the parts that already work.

| Area | Evidence |
|---|---|
| **Money types** | `NUMERIC(18,6)` on every price, quantity, cost base, proceeds column. `DOUBLE PRECISION` used only for ML probabilities and returns, which is correct |
| **Decimal discipline** | 74 files import `Decimal`. `float(` appears in 9, all in statistics (`alpha_eval`, `factor_scores`) where appropriate. Explicit "Never float()" contracts in `theses/types.py` |
| **CGT correctness** | `relativedelta(years=1) + timedelta(days=1)`, docstring forbids `>= 365`, exact `Fraction(1,3)` for SMSF, boundary tests including the 367-day leap case. Cost base column cites `s 110-25 ITAA97` |
| **Loss ordering** | Non-discount gains offset before discount gains — the optimal ordering, per `s 102-5` |
| **Survivorship** | `exchange_symbols_delisted` ingests delisted securities; comment explains the missing delisted-date field |
| **Model honesty** | Model A measured across 19,032 matured signals, found to have no edge, quarantined rather than defended |
| **Idempotency** | `portfolio_daily_snapshots` uses `ON CONFLICT (as_of) DO UPDATE`. Re-runs are safe |
| **Dependencies** | Exact-pinned (`==`) throughout. `defusedxml` for untrusted RSS. No hardcoded secrets anywhere |
| **Test substance** | 3,847 assertions across 2,070 test functions. Not smoke tests |
| **Failure ordering** | Post-brief steps deliberately sequenced after the send so a downstream failure cannot cost you the brief |

---

# Part II — Delivery diagnostic (folded in)

The original finding stands unchanged; it now reads as the same disease presenting in a different tissue.

## The numbers

| Layer | Files | Lines |
|---|---|---|
| Markdown | 269 | 57,945 (573,092 words ≈ 1,150 pages) |
| Python source | 170 | 32,473 |
| Python tests | 128 | 37,142 |

**Prose-to-source ratio 1.78 : 1.** Document creation is accelerating: 6 in June, 44 in July, 54 in the first 22 days of August (2.45/day).

**Eight competing backlogs.** Four carry hand-written `⚠️ NOT A QUEUE` banners pointing at `roadmap-state.md`, which is 1,686 lines. 42% of documents contain `SUPERSEDED`; there are 562 occurrences of `STALE`. `doc-truth-map-2026-08-13.md` (56 KB) exists solely to track which other documents are still true.

**Status fields are unreliable in both directions.** `multi-instrument-expansion` says "NOT yet built" — it shipped (`_TYPE_TO_KIND`, `migrations/0037_security_kind.sql`, code comments citing the proposal's own §7.3). `thesis-coverage-framework` says "NOT yet built" — substantially shipped. `portfolio-team-visibility` says "NOT yet built" — genuinely isn't.

**Context tax:** 26 agents (113 KB) + 33 commands (89.5 KB) + `roadmap-state.md` (145 KB) + `CLAUDE.md` (25 KB) ≈ 423 KB, roughly 106,000 tokens of process before any work starts.

**Session handoff tax:** 16 documents, 154 KB, averaging 9.6 KB. A fixed cost at both ends of every session that exists only because state lives in prose.

## Recommendations (unchanged)

- **R1.** GitHub Issues becomes the sole system of record. `/sprint-state` already calls `gh issue list` as step 5 of 5 — promote it to step 1. Rule into `CLAUDE.md`: *documents may describe, argue and record; documents may not hold state.*
- **R2.** Delete seven of the eight backlogs. `roadmap-state.md` becomes a **generated** view.
- **R3.** Kill the session handoff. Replace with `gh issue list --state open` plus a 10-line overwritten `WHERE-I-STOPPED.md`.
- **R4.** Two document classes: **immutable decision records** (dated, never edited, superseded by reference) and **≤5 living references** with named owners. Everything else archived or deleted.
- **R5.** Cut to ~8 agents and ~10 commands. Instrument invocation for two weeks first, then retire the zeroes. Recovers roughly 60k tokens per session.
- **R6.** Definition of done is a merged PR. *A proposal is not progress.*
- **R7.** WIP limits: max 3 open proposals, max 1 new document per session, proposals auto-expire at 30 days. Nine currently fail this.
- **R8.** No further doc-truth reconciliation sweeps. Delete `doc-truth-map`, don't update it.

---

# Part III — The synthesis

Read the two parts together and the same sentence explains every finding:

> **A claim lives in one place, the truth lives in another, and nothing fails when they diverge.**

| The claim | The truth | What forces agreement |
|---|---|---|
| Migration header says DRAFT | Applied in production | Nothing |
| `REQUIRED_MIGRATIONS = 97` | 43 files on disk | A `<` comparison that cannot detect extras |
| `ASXOS_TZ = "Australia/Sydney"` | No code reads it | Nothing |
| Proposal says "NOT yet built" | Shipped in PR | Nothing |
| `roadmap-state.md` says stage not started | PR merged | A human sweep, run occasionally |
| Firewall doc says model-independent sizer | No code reference | Nothing |
| Backup dump exists | Restorability unknown | A manual flag nobody sets |
| Query assumes UTC session TZ | GUC unpinned | A comment |

Report I framed this as "prose can't hold state." That was too narrow. The accurate framing is:

> **asxos has a large control plane, and almost none of it is executable.**

The engineering culture here is unusually rigorous. The CGT boundary arithmetic, the timezone GUC analysis, the Model A quarantine — this is careful, honest work by someone who thinks hard about correctness. The failure isn't rigour. **It's that the rigour was expressed in prose, where it can't run, can't be tested, and decays silently.**

## The one prescription

**Convert claims into assertions.** For every invariant that matters, ask: what fails if this stops being true? If the answer is "nothing," it isn't a control, it's a note.

Ranked by value per hour:

| # | Action | Effort | Converts |
|---|---|---|---|
| 1 | Pin `server_settings={'timezone':'UTC'}` in `init_pool` | 1 line | Comment → enforced invariant |
| 2 | Migration name-diff check in CI | ~30 lines | Hand-bumped integer → real drift detection |
| 3 | Schedule the restore drill weekly | 3 lines YAML | Hypothesis → verified backup |
| 4 | Delete all migration file state headers | delete | Removes a permanently-drifting claim |
| 5 | Log alert-send failures to `job_runs` | ~5 lines | Silent failure → observable |
| 6 | Single date-resolution helper, data-anchored | ~20 lines | Two strategies → one; makes `ASXOS_TZ` real |
| 7 | Test asserting sizer provenance | ~40 lines | Prose safety control → executable one |
| 8 | R1–R3 from Part II | 1 day | Prose queue → queryable one |

Items 1 to 5 total well under a day and remove three P0/P1 classes.

## Metrics

| Metric | Now | Target |
|---|---|---|
| Migrations in repo vs applied in prod | 43 vs 97, undetectable | Exact match, CI-enforced |
| Prose-to-source line ratio | 1.78 : 1 | < 0.5 : 1 |
| Living documents | ~162 | ≤ 5 |
| `SUPERSEDED` + `STALE` occurrences | 860 | < 50 |
| Config settings defined but unread | ≥ 1 (`ASXOS_TZ`) | 0 |
| Days since last verified restore | unknown | ≤ 7 |

## What not to do

**Don't refactor the money code.** It's the best part of the repo.

**Don't write a plan for this plan.** If the first artifact produced in response is a document, the pattern has reasserted itself. The first action is `server_settings={'timezone': 'UTC'}`.

**Don't fix the 11 ruff findings.** Version skew, cosmetic, not your CI.

**Don't reconcile the docs.** Cut them. `doc-truth-map` gets deleted, not updated.

---

## Caveats on method

- **No live DB.** Every production claim is what the repo asserts about production. P0-1 and P0-2 need a live `schema_migrations` query to size precisely. That the repo cannot answer this itself is the finding.
- **No git history.** Commit cadence and merge rates inferred from PR references in docs.
- **Tests not executed.** The suite needs the ML extras. Assertion density is measured statically; I have not verified the suite is green.
- **P1-5 impact unconfirmed.** The timezone offset is arithmetic and certain. Whether it produces a wrong brief depends on per-call-site intent, which needs a live run to settle.
