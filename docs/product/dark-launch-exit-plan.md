# Dark-launch exit plan — ship, delete, or keep-dark-with-an-expiry

**Status:** current
**Scope:** every code-complete-but-gated-off surface in asxos. For each one: a **ship / delete /
keep-dark** decision, the reason, an **expiry** if kept dark, and the exact gate that flips it.
Closes risk R4 (built-but-dark ≠ released) by refusing to let a surface sit dark with no decision.
**Last verified:** 2026-07-11 (post ML-shelf; the model-independent product is now THE product)
**Owner:** arbi maintains the decisions + expiries (I2, command-invoked); James owns any decision
that flips a real-capital or firewall gate (those are `james-inbox.md` items).
**Superseded by:** N/A

A dark launch is a promise to decide later. "Later" without a date is how dead code accretes. Every
surface below carries one of three verdicts — **SHIP** (flip the gate on a named condition),
**DELETE** (remove the code; it doesn't serve the moat), or **KEEP-DARK** (justified, with an
expiry date at which arbi re-raises it). No fourth "leave it and forget" state exists.

---

## Surfaces

### 1. Portfolio brief — `ASXOS_PORTFOLIO_BRIEF_ENABLED=0`

- **Verdict: KEEP-DARK · expiry 2026-08-31.**
- **Why:** The M13 allocator brief section is model-independent in its non-signal cards (tax,
  discipline, thesis, regulatory) but the *allocator* path it fronts is dormant policy
  (rule #11 standing; `approved_for_allocation=0`). Shipping the section as-is would front an
  allocator that is deliberately not allowed to run. The valuable model-independent cards already
  reach James through the main brief, so there's no user-facing loss in keeping this off.
- **Gate to ship:** `ASXOS_PORTFOLIO_BRIEF_ENABLED=1` **and** `ASXOS_PERSONAL_USE=1` — but only
  after 4 weeks of paper-trade sign-off (M13.8) **and** the section is re-scoped to display the
  discipline/tax cards *without* implying an allocator recommendation. Until the allocator has a
  revival path (a new model past the decay bar), ship the model-independent cards or nothing.
- **Owner of the flip:** James (firewall gate 1 + capital-adjacent) — a `james-inbox.md` item when
  the paper-trade window closes.

### 2. News / sentiment brief — `ASXOS_NEWS_BRIEF_ENABLED=1` (SHIPPED 2026-07-11 · **ship condition (a) VOID 2026-08-05**)

- **Verdict: SHIPPED, but condition (a) is void — the surface has been rendering
  empty every day since the redeploy.** Condition (b) still holds. Condition (a) was
  verified against `job_runs.status`, a field the ingest job could not fail to write
  as `success`: `holding_news` had **zero rows** for the entire window, and the
  operative cause (`_normalise_symbol` mapping the sole US holding to a symbol the
  filter drops) is still open. See `docs/market-trends-report-2026-08-05.md` §1.
  **Re-verify before this may be called shipped again** — the restated condition is
  in (a) below.
- ~~**Verdict: SHIP · both conditions verified 2026-07-11.**~~
- **Why:** News/sentiment (`asxos/ingestion/{news,sentiment}.py`, M14a/b) is fully
  model-independent — it feeds the market-context and discipline narrative, not a signal. It
  directly serves the "know the backdrop before it costs money" moat layer and has no rule-#11
  exposure. This is exactly the kind of surface the post-shelf product should turn on.
- **Ship conditions — (a) VOID as of 2026-08-05, (b) still holds:**
  (a) **RESTATED, and currently NOT MET** — `job_runs` must show `ingest_news` runs with
  `status='success'` **AND `rows_written > 0`**, *and* `holding_news` must be non-empty.
  Status alone is not evidence of work.
  ~~*(original, void)*: `job_runs` shows `ingest_news` status='success' every scheduled
  business day for 3+ weeks (2026-06-21 through 2026-07-09, zero failures).~~ That streak
  was produced by a guard that could not fail (`is_ok=lambda r: isinstance(r, int) and
  r >= 0` against a worker returning `0` on caught exceptions), and every one of those runs
  wrote zero rows. The predicate and the brief's freshness gate were fixed 2026-08-05
  (`deea76a`); the reason the table is empty is a separate, still-open symbol-mapping bug.
  (b) **reads as context, never implied buy/sell** — verified by direct read + a `security-engineer`
  s766B pass (PASS): `brief.html.j2`'s `news_items` block (lines 106-118) renders only symbol,
  linked article title, publish date, and an optional sentiment tag — zero generated advisory
  text; `compose.py`'s `NewsItem`/`_holding_news` is a pure passthrough of the `holding_news`
  table (no LLM call, no synthesis); `sentiment` is EODHD's third-party article-tone classifier,
  structurally decoupled from `signal_sentiment` (the Model A feature-engineering table) — no
  path from quarantined Model A output into this section. `ASXOS_PERSONAL_USE=1` gates first,
  ahead of the feature flag, in both branches.
- **Flipped:** `render.yaml` `ASXOS_NEWS_BRIEF_ENABLED` `"0"→"1"` — git-tracked (CLAUDE.md #2:
  Render changes go through `render.yaml` + git push, never a direct dashboard/API mutation).
  Takes effect only once this branch's PR merges and Render redeploys — no live change yet.
- **Still pending (James's go, mirroring the R8 pattern):** the `asx news signoff` CLI command
  (`asxos/cli/news.py`) records this decision as a `[m14_news_signoff]` row in the `decisions`
  table — a production DB write, so it wasn't run unprompted. Its own printed next-step (a raw
  `curl -X PUT` to the Render API) was **not** followed either — that would bypass `render.yaml`
  as source of truth and desync `make check-drift`; the git-tracked edit above is the correct
  path per CLAUDE.md #2. The CLI's coverage pre-check (`ingest_news` success within 7 days) was
  independently re-verified via live `job_runs` before this edit, so the signoff INSERT is a
  formality, not a blocking prerequisite — but it's still a DB write awaiting James's word.
- **Owner of the flip:** arbi proposes; main loop flips (reversible ops, no capital). ✅ done —
  git-tracked flip drafted; live effect gated on PR merge + redeploy, same as every other change
  this session.

### 3. V2 brief tree

- **Verdict: KEEP-DARK · expiry 2026-09-30.**
- **Why:** The V2 brief tree (`asxos/domain/brief/collectors/*`, `brief_v2.html.j2`) was designed
  around a *trusted signal engine* that no longer exists (ML shelved). Its model-independent
  collectors (`active_theses`, discipline, tax) are the keepers; the signal-driven framing is
  stale. Deleting now would throw away the reusable model-independent collectors; shipping now
  would ship the stale signal framing. So: keep dark, and use the window to **descope it to the
  model-independent collectors** and retire the "V2 needs a trusted signal engine" framing
  (`ml-engine-shelf-2026-07-11.md` next-action #4).
- **Gate to ship:** the proposed single master gate `ASXOS_V2_BRIEF_ENABLED` (not yet plumbed),
  flipped only after the tree is re-scoped model-independent and its collectors are the same ones
  proven in the live brief. Partial-ship allowed here (collector by collector), unlike the
  portfolio section.
- **Owner of the flip:** arbi drives the re-scope; James flips if any card is capital-adjacent.

### 4. Paper-trade evaluator

- **Verdict: KEEP-DARK · expiry tied to surface #1, re-raise 2026-08-31.**
- **Why:** The paper-trade evaluator (`asxos/domain/portfolio/paper_trade.py`) exists to *earn* the
  4-week sign-off that gates surface #1 — it is the instrument that produces the evidence to ship
  the portfolio brief, so it is correctly dark until that evaluation is actually being run.
  Deleting it would remove the only mechanism that can retire surface #1's KEEP-DARK. It stays,
  unshipped, as scaffolding with a job to do.
- **Gate to ship:** not a user-facing gate — this is an internal evaluator. "Ship" here means
  **start the 4-week paper-trade run** (record its results to feed the M13.8 sign-off), not expose
  output to James. Begins when James decides to open the portfolio-brief evaluation window.
- **Owner of the flip:** James starts the window (it commits to a capital-adjacent evaluation);
  arbi runs and records once started.

---

## Summary

| Surface | Verdict | Gate | Expiry / condition | Flip owner |
|---|---|---|---|---|
| Portfolio brief | KEEP-DARK | `ASXOS_PORTFOLIO_BRIEF_ENABLED=1` + `ASXOS_PERSONAL_USE=1` | 2026-08-31 · re-scope to model-independent cards + 4wk sign-off | James |
| News/sentiment brief | **SHIPPED — condition (a) VOID 2026-08-05** | `ASXOS_NEWS_BRIEF_ENABLED=1` (live on `main`) | re-verify (a): `rows_written > 0` **and** non-empty `holding_news` | arbi/main loop |
| V2 brief tree | KEEP-DARK | `ASXOS_V2_BRIEF_ENABLED` (unplumbed) | 2026-09-30 · descope to model-independent collectors | arbi / James |
| Paper-trade evaluator | KEEP-DARK | start the 4wk run (internal) | 2026-08-31 · re-raise with surface #1 | James |

## How arbi uses it

- **Every wake, check no dark surface is past its expiry.** An expired KEEP-DARK is a re-raise: the
  surface must earn a fresh SHIP / DELETE / KEEP-DARK verdict, not silently roll over.
- **Never count a dark-launched surface as delivered** in the scorecard or the brief's "recently
  completed" (risk R4). Built is not released; the ledger is honest about the difference.
- **A SHIP verdict that only arbi can flip, arbi flips** (reversible, non-capital). A SHIP/START
  that crosses a firewall or capital gate becomes a `james-inbox.md` row.
- **A SHIPPED surface whose ship condition is later falsified reverts to un-shipped, and must
  earn a fresh verdict.** Added 2026-08-05, from the news-brief incident: this document had a
  rule for an expired KEEP-DARK and no rule for a SHIP whose evidence turned out to be wrong,
  so nothing forced a re-raise. Shipping is not a one-way ratchet. When the condition is
  falsified, strike the verdict in place (do not delete the history), restate the condition so
  it cannot be satisfied the same false way twice, and re-raise the surface.
- **A ship condition must assert on the ARTIFACT, never on a job's status alone.** `job_runs.status`
  records that a job completed, not that work happened — the news brief shipped on a 3-week green
  streak from a job that wrote zero rows on every run. Require `rows_written > 0`, or join the
  table the job is supposed to populate (as the portfolio gate joins `rebalance_runs`). Two checks
  reading the same field are one check, and one defect clears both.
