# Dark-launch exit plan — ship, delete, or keep-dark-with-an-expiry

**Status:** current for unrelated legacy surfaces; investment-engine rows are
superseded by `roadmap.yaml` and the twelve-week dossier
**Scope:** every code-complete-but-gated-off surface in asxos. For each one: a **ship / delete /
keep-dark** decision, the reason, an **expiry** if kept dark, and the exact gate that flips it.
Closes risk R4 (built-but-dark ≠ released) by refusing to let a surface sit dark with no decision.
**Last verified:** 2026-07-24 for programme precedence; individual legacy-surface
facts still require live refresh
**Owner:** arbi maintains the decisions + expiries (I2, command-invoked); James owns any decision
that flips a real-capital or firewall gate (those are `james-inbox.md` items).
**Superseded by:** `roadmap.yaml`, S08–S12, and
`programs/investment-engine/operations-and-rollout.md` for portfolio construction,
paper evaluation, staging, and their release clocks.

A dark launch is a promise to decide later. "Later" without a date is how dead code accretes. Every
surface below carries one of three verdicts — **SHIP** (flip the gate on a named condition),
**DELETE** (remove the code; it doesn't serve the moat), or **KEEP-DARK** (justified, with an
expiry date at which arbi re-raises it). No fourth "leave it and forget" state exists.

---

## Surfaces

### 1. Portfolio brief — `ASXOS_PORTFOLIO_BRIEF_ENABLED=0`

- **Verdict: KEEP-DARK · reassess only at the S12 handoff.**
- **Why:** The M13 allocator brief section is model-independent in its non-signal cards (tax,
  discipline, thesis, regulatory) but the *allocator* path it fronts is dormant policy
  (rule #11 standing; `approved_for_allocation=0`). Shipping the section as-is would front an
  allocator that is deliberately not allowed to run. The valuable model-independent cards already
  reach James through the main brief, so there's no user-facing loss in keeping this off.
- **Gate to ship:** the legacy four-week/M13.8 gate is retired. The surface may
  only be removed or adapted as a thin reader of the S12 governed artifact after
  the S01–S12 acceptance chain, the separate authority ratification, and the
  post-freeze 30-clean-session operational gate. `ASXOS_PORTFOLIO_BRIEF_ENABLED`
  and `ASXOS_PERSONAL_USE` remain necessary but cannot substitute for those
  predicates. Strategy/edge language additionally requires 252 prospective
  sessions and 20 matured pre-registered 63-session episodes.
- **Owner of the flip:** James (firewall gate 1 + capital-adjacent) — a
  `james-inbox.md` item only after the S12 lineage and operational gate close.

### 2. News / sentiment brief — `ASXOS_NEWS_BRIEF_ENABLED=1` (SHIPPED 2026-07-11, draft-PR pending merge)

- **Verdict: SHIP · both conditions verified 2026-07-11.**
- **Why:** News/sentiment (`asxos/ingestion/{news,sentiment}.py`, M14a/b) is fully
  model-independent — it feeds the market-context and discipline narrative, not a signal. It
  directly serves the "know the backdrop before it costs money" moat layer and has no rule-#11
  exposure. This is exactly the kind of surface the post-shelf product should turn on.
- **Ship conditions — both verified 2026-07-11 (arbi wake + autonomy window):**
  (a) **ingestion cron green + fresh** — `job_runs` shows `ingest_news` status='success' every
  scheduled business day for 3+ weeks (2026-06-21 through 2026-07-09, zero failures); the
  `check_cron_health` deadman that watches it was itself fixed this session (shelf-aware
  `check_model_staleness`, no longer polluting the deadman).
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

### 4. Legacy paper-trade evaluator

- **Verdict: LEGACY PROTOTYPE · do not start its four-week promotion clock.**
- **Why:** `asxos/domain/portfolio/paper_trade.py` is repository evidence to
  inventory and selectively reuse, not the accepted evaluator. It lacks the
  frozen origins, five branches, causal fills, branch ledger/NAV, XJO-TR,
  accounting/tax lineage, prospective statistics, and fail-closed gates specified
  by S08–S11.
- **Gate:** no user-facing release. Build the S08–S11 evaluator through reviewed
  sprint PRs. Only after S12 freezes the complete lineage may James start the
  30-clean-session operational clock; the 252-session/20-episode strategy clock is
  separate and cannot be shortened by legacy history.
- **Owner:** Arbi coordinates the build and evidence; James alone authorises the
  post-S12 clocks and any product flip.

---

## Summary

| Surface | Verdict | Gate | Expiry / condition | Flip owner |
|---|---|---|---|---|
| Portfolio brief | KEEP-DARK | S01–S12 acceptance + authority ratification + 30 clean post-freeze sessions; flags remain necessary | S12 handoff; no legacy four-week sign-off | James |
| News/sentiment brief | **SHIPPED 2026-07-11** | `ASXOS_NEWS_BRIEF_ENABLED=1` (drafted, pending PR merge) | both conditions verified | arbi/main loop |
| V2 brief tree | KEEP-DARK | `ASXOS_V2_BRIEF_ENABLED` (unplumbed) | 2026-09-30 · descope to model-independent collectors | arbi / James |
| Legacy paper-trade evaluator | PROTOTYPE ONLY | no promotion gate; selectively reuse behind S08–S11 contracts | superseded by canonical evaluator | Arbi coordinates; James authorises clocks |

## How arbi uses it

- **Every wake, check no dark surface is past its expiry.** An expired KEEP-DARK is a re-raise: the
  surface must earn a fresh SHIP / DELETE / KEEP-DARK verdict, not silently roll over.
- **Never count a dark-launched surface as delivered** in the scorecard or the brief's "recently
  completed" (risk R4). Built is not released; the ledger is honest about the difference.
- **A SHIP verdict that only arbi can flip, arbi flips** (reversible, non-capital). A SHIP/START
  that crosses a firewall or capital gate becomes a `james-inbox.md` row.
