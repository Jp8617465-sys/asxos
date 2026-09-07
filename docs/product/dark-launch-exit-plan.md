# Dark-launch exit plan — ship, delete, or keep-dark-with-an-expiry

**Status:** current
**Scope:** every code-complete-but-gated-off surface in asxos. For each one: a **ship / delete /
keep-dark** decision, the reason, an **expiry** if kept dark, and the exact gate that flips it.
Closes risk R4 (built-but-dark ≠ released) by refusing to let a surface sit dark with no decision.
**Last verified:** 2026-09-02 (`/arbi` wake — **surfaces #1 and #4 found EXPIRED since 2026-08-31 and formally re-raised**; countdown block and summary rows corrected; #3 unexpired at 28 days. Verdict drafts are campaign node H1-G, the rulings are James's). Prior: 2026-08-21 (`/arbi-run` — **surface #2 issued a fresh SHIP verdict** on a
read-only production probe of both restated conditions; the 8-day-old "no fresh verdict exists"
gap is closed, and two stale claims inside that section were falsified by the same probe and
corrected in place). Prior: 2026-08-13 (SB0-01 doc-truth sweep — surface #2's verdict reverted to
UN-SHIPPED per this file's own `:133-138` rule; expiry countdowns restated). Prior: 2026-07-11
(post ML-shelf; the model-independent product is now THE product)
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

### 2. News / sentiment brief — `ASXOS_NEWS_BRIEF_ENABLED=1` (**SHIP — fresh verdict issued 2026-08-21**)

- **✅ VERDICT: SHIP — issued 2026-08-21 by arbi (`/arbi-run`), on live re-verification of the
  restated conditions.** This is the fresh verdict the 2026-08-13 re-raise demanded; it
  supersedes the UN-SHIPPED entry below, which is retained as the record of the interim state.
  Owner check per this file's own rule at `:220-221` ("A SHIP verdict that only arbi can flip,
  arbi flips"): the re-decision crosses no firewall or
  capital gate (the surface is model-independent, reads as context, and has no rule-#11
  exposure), and the summary table names the flip owner as **arbi/main loop** — so it is
  arbi's to issue, not a `james-inbox.md` row.

  **Condition (a) — MET.** Restated as: `job_runs` must show `ingest_news` with
  `status='success'` **and** `rows_written > 0`, *and* `holding_news` must be non-empty.
  Probed read-only 2026-08-21 against production:

  | Evidence | Observed |
  |---|---|
  | `ingest_news` last six runs (`rows_written`) | 3 · 2 · 2 · 1 · 0 · 4 — every run `status='success'` |
  | Latest run | 2026-08-20 20:57:24Z, `success`, 3 rows |
  | `holding_news` | **9 rows** (non-empty) |
  | `signal_sentiment` | **9 rows** |
  | `ingest_news` lifetime successes | 54 |

  Status alone is explicitly not evidence of work, per the restatement — hence `rows_written`
  is cited per-run rather than in aggregate. The one `0` row-count in the window is *consistent
  with* a quiet day, and is no longer producible by the failure mode that voided the original
  condition: that failure was a guard which *could not* fail (`is_ok=lambda r: isinstance(r,
  int) and r >= 0` against a worker returning `0` on caught exceptions) producing a three-week
  streak of zero-row "successes". That guard is gone — the predicate is now
  `is_ok=lambda r: isinstance(r, tuple)` (`jobs/ingest_news.py:242`) against a worker whose
  failure sentinel is `None`, never `0` (`:66`, `:81-85`) — and four of the last six runs wrote
  rows, so the guard is now discriminating. **Condition (a) rests on those four runs, not on a
  reading of the one `0`:** the job's own docstring is deliberately stricter than this verdict
  needs — "a returned `0` is still not proof of a quiet day" (`:87-88`) — and calling that `0` a
  *confirmed* quiet day would claim more than the probe shows.

  **Condition (b) — unchanged and still holds** (reads as context, never implied buy/sell).

  **Two stale claims in this section are falsified by the same probe**, and are corrected here
  rather than left to mislead the next reader:
  - The "symbol-mapping bug" named below as the operative cause is **not** the cause, and is
    not open. `jobs/ingest_news.py:186` selects `DISTINCT symbol FROM current_holdings`, and
    there is exactly **one open lot** — so coverage is bounded by portfolio breadth, not by a
    mapping defect. (This was already corrected on 2026-08-17 in `roadmap-state.md`'s
    **News/sentiment M14a/M14b** cross-walk row, `:644`; this file did not carry the correction
    across.)
  - `signal_sentiment` is **not** empty — it holds 9 rows, which falsifies that same cross-walk
    row's "`signal_sentiment` downstream remains empty" — struck at source 2026-08-22.
    (Both bullets cited `roadmap-state.md:589` until review caught it; the target had shifted to
    `:644`. Cite the row by name first, the offset second.)

  **No flag flip is required by this verdict.** `ASXOS_NEWS_BRIEF_ENABLED: "1"` is already live
  in `.github/workflows/daily-brief.yml:61` (with `ASXOS_PERSONAL_USE: "1"` at `:60`, the gate
  that fires first), so the section has been *enabled* throughout — which is not the same as
  populated: before PR #73 an empty result made it vanish entirely, per the precision note
  below. What was missing was a *valid verdict*, not a config change — the surface sat in the
  "SHIPPED-but-void" state `:222-227` says cannot exist. That is now closed. Nothing in
  `.github/` was touched.

- ~~**Verdict: UN-SHIPPED · RE-RAISED 2026-08-13 · awaiting a fresh SHIP / DELETE /
  KEEP-DARK verdict.**~~ *(superseded 2026-08-21 by the SHIP verdict above; retained as the
  record of the interim state.)* Applied by the SB0-01 doc-truth sweep under this file's own rule at
  `:133-138`: *"A SHIPPED surface whose ship condition is later falsified reverts to
  un-shipped, and must earn a fresh verdict."* Condition (a) was falsified on 2026-08-05 and
  no fresh verdict has been issued in the 8 days since, so the surface sat in a state this
  document says cannot exist. It is now formally back in the queue. **Owner needed** — arbi
  may propose the fresh verdict; James owns it only if the re-decision crosses a firewall or
  capital gate, which on current evidence it does not.
- **Live-state divergence the reader must not miss:** reverting the *verdict* does **not**
  turn the surface off. `ASXOS_NEWS_BRIEF_ENABLED: "1"` is still set in the executing
  scheduler at `.github/workflows/daily-brief.yml:61`, so the section still renders
  daily. (Precision, post-#73: before that PR an empty result made the section *vanish*
  entirely; it now renders an explicit state line — quiet vs unverified — so "still renders"
  is true today for a different reason than when this line was written.) Flipping the flag is a config change and was deliberately **not** made by this
  docs-only sweep. ~~The fresh verdict decides whether the flag goes to `0` (keep-dark until the
  symbol-mapping bug is fixed) or stays at `1` (ship, once (a) is genuinely met).~~ *(Answered
  2026-08-21 by the SHIP block above: the flag stays at `1`, and the "symbol-mapping bug"
  premise is itself falsified.)*
- ~~**Verdict: SHIPPED, but condition (a) is void — the surface has been rendering
  empty every day since the redeploy.**~~ *(superseded 2026-08-13 — "SHIPPED, but void" is
  precisely the un-decided state `:133-138` forbids; retained for history.)* Condition (b)
  still holds. Condition (a) was verified against `job_runs.status`, a field the ingest job
  could not fail to write as `success`: `holding_news` had **zero rows** for the entire
  window, and the operative cause (`_normalise_symbol` mapping the sole US holding to a symbol
  the filter drops) is still open. See `docs/market-trends-report-2026-08-05.md` §1.
  **Re-verify before this may be called shipped again** — the restated condition is
  in (a) below.
- ~~**Verdict: SHIP · both conditions verified 2026-07-11.**~~
- **Why:** News/sentiment (`asxos/ingestion/{news,sentiment}.py`, M14a/b) is fully
  model-independent — it feeds the market-context and discipline narrative, not a signal. It
  directly serves the "know the backdrop before it costs money" moat layer and has no rule-#11
  exposure. This is exactly the kind of surface the post-shelf product should turn on.
- **Ship conditions — (a) VOID as of 2026-08-05, ~~currently NOT MET~~ → MET 2026-08-21;
  (b) still holds:**
  (a) **RESTATED** — this wording is the operative one and it is now satisfied, per the SHIP
  block above — `job_runs` must show `ingest_news` runs with
  `status='success'` **AND `rows_written > 0`**, *and* `holding_news` must be non-empty.
  Status alone is not evidence of work.
  ~~*(original, void)*: `job_runs` shows `ingest_news` status='success' every scheduled
  business day for 3+ weeks (2026-06-21 through 2026-07-09, zero failures).~~ That streak
  was produced by a guard that could not fail (`is_ok=lambda r: isinstance(r, int) and
  r >= 0` against a worker returning `0` on caught exceptions), and every one of those runs
  wrote zero rows. The predicate and the brief's freshness gate were fixed 2026-08-05
  (`deea76a`); ~~the reason the table is empty is a separate, still-open symbol-mapping bug.~~
  *(Falsified 2026-08-21: the table is not empty — 9 rows — and no symbol-mapping defect is
  open; coverage is bounded by a one-lot portfolio, `jobs/ingest_news.py:186`.)*
  (b) **reads as context, never implied buy/sell** — verified by direct read + a `security-engineer`
  s766B pass (PASS): `brief.html.j2`'s news block (the `news_status` branch) renders only
  symbol, linked article title, publish date, and an optional sentiment tag — zero generated
  advisory text. Re-verified post-#73, which added two static status sentences (a quiet-day
  line and an unverified-ingest disclaimer) to the non-`ok` branches; both are operational
  state about the pipeline, carry no security-specific view, and do not change the PASS.
  `compose.py`'s `NewsItem`/`_holding_news` is a pure passthrough of the `holding_news`
  table (no LLM call, no synthesis); `sentiment` is EODHD's third-party article-tone classifier,
  structurally decoupled from `signal_sentiment` (the Model A feature-engineering table) — no
  path from quarantined Model A output into this section. `ASXOS_PERSONAL_USE=1` gates first,
  ahead of the feature flag, in both branches.
- **Flipped:** ~~`render.yaml` `ASXOS_NEWS_BRIEF_ENABLED` `"0"→"1"` — git-tracked (CLAUDE.md #2:
  Render changes go through `render.yaml` + git push, never a direct dashboard/API mutation).
  Takes effect only once this branch's PR merges and Render redeploys — no live change yet.~~
  **Superseded 2026-08-13 (SB0-01):** Render was **deleted** (James's governor ruling
  2026-08-12, `roadmap-state.md:116`), so `render.yaml` no longer sets any live environment.
  The flag's actual live source is now `.github/workflows/daily-brief.yml:61`
  (`ASXOS_NEWS_BRIEF_ENABLED: "1"`). Any future flip of this gate is a workflow edit, not a
  `render.yaml` edit.
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

🔴 **Expiry status as of 2026-09-06 (`/arbi` wake, window AW-01): surfaces #1 and #4 are six days
past their 2026-08-31 expiry and still unruled — re-raised again.** The verdict drafts (KEEP-DARK to
2026-11-30, tied to Stage 4 case delivery) merged to `main` in #190, so each is a one-word ruling
(backlog **D-1 / D-2**, inbox H-16). Surface #3 has 24 days to 2026-09-30 (**D-15**). Surface #2
remains SHIP (2026-08-21).

🔴 **Expiry status as of 2026-09-02 (`/arbi` wake): surfaces #1 and #4 are EXPIRED — two days
past, verdict overdue, and re-raised.** Their 2026-08-31 expiry passed with no ruling, and the
"decide by 2026-08-28" date in `james-inbox.md` passed five days ago. Per this file's own rule
below, an expired KEEP-DARK does **not** roll over: each must earn a fresh SHIP / DELETE /
KEEP-DARK verdict with a new expiry. Surface #3 expires **2026-09-30** (28 days out, not yet
expired). Surface #2 is closed — SHIP issued 2026-08-21.

The scheduling fact named in the 2026-08-21 countdown below came true exactly as stated: the
4-week window was never opened, so #1 and #4 re-raise together with no new evidence to decide
on. A verdict draft for both — recommending KEEP-DARK to 2026-11-30, tied to Stage 4 case
delivery rather than to a date — is campaign node H1-G; the ruling itself is James's
(click H-16), because both gates are capital-adjacent.

_Superseded countdown (2026-08-21 `/arbi-run`), kept as the record of what was known then:_
_surfaces #1 and #4 expire **2026-08-31 — 10 days out**; surface #3 expires **2026-09-30 — 40
days out**. None has expired yet. **Surface #2 is no longer awaiting a verdict** — SHIP issued
2026-08-21. ⚠️ #1 and #4 are James's and are inside their decision window; both are flagged in
`james-inbox.md` with "decide by 2026-08-28" — seven days out. #4's gate ("start the 4-week
paper-trade run") cannot produce evidence before #1's own 2026-08-31 expiry, so if the window
is not opened this week the two re-raise together with no new evidence to decide on. That is a
scheduling fact, not a recommendation._

_Prior countdown (2026-08-13, SB0-01 sweep): #1/#4 18 days out, #3 48 days out._

| Surface | Verdict | Gate | Expiry / condition | Flip owner |
|---|---|---|---|---|
| Portfolio brief | 🔴 **EXPIRED 2026-08-31 — re-raised, awaiting a fresh verdict** (was KEEP-DARK) | `ASXOS_PORTFOLIO_BRIEF_ENABLED=1` + `ASXOS_PERSONAL_USE=1` | **EXPIRED 2026-08-31** (was: 10d as of 2026-08-21) · re-scope to model-independent cards + 4wk sign-off | James |
| News/sentiment brief | ✅ **SHIP — fresh verdict 2026-08-21** (was UN-SHIPPED · RE-RAISED 2026-08-13) | `ASXOS_NEWS_BRIEF_ENABLED=1` already live via `.github/workflows/daily-brief.yml:61` — no flip needed | (a) re-verified 2026-08-21: `rows_written` 3·2·2·1·0·4 all `success`, `holding_news` 9 rows; (b) unchanged | arbi/main loop — **issued** |
| V2 brief tree | KEEP-DARK (not expired) | `ASXOS_V2_BRIEF_ENABLED` (unplumbed) | 2026-09-30 (**28d** as of 2026-09-02) · descope to model-independent collectors | arbi / James |
| Paper-trade evaluator | 🔴 **EXPIRED 2026-08-31 — re-raised, awaiting a fresh verdict** (was KEEP-DARK) | start the 4wk run (internal) | **EXPIRED 2026-08-31** (was: 10d as of 2026-08-21) · re-raised with surface #1 | James |

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
