# Session handoff — 2026-07-04

**Status:** current
**Scope:** whole repo / session handoff
**Last verified:** 2026-07-04
**Read priority:** read first
**Superseded by:** N/A

Read this before doing anything else in this repo. It supersedes the tone (not
the facts) of `docs/next-session-backlog.md`'s older entries — that file's
itemized backlog is still accurate line-by-line, but this document is the
one that says what actually matters right now.

---

## STOP — read this first: Model A's signal reliability is in dispute, unresolved

James's own words, ending this session (2026-07-04): *"Model A has had a lot
of issues and has been proven to not have any reliable signals as they
greatly diminish after 5 days and completely swing around at 21 days."* He
also said he is bringing a separate audit from a ChatGPT-based investigation
of this project into the next session.

**This has not been independently verified from inside this session** — no
audit content was actually pasted before the session ended, and no rigorous
decay analysis has been run against the real `signals` history. But the claim,
if true, is structurally serious, not a minor quality nit:

- Model A (`model_a v1_5`, trained 2026-05-21, `roc_auc≈0.71`, `is_active=true`,
  `approved_for_allocation=true` in `model_versions` as of tonight) is the
  **only** model in the system, and it gates every BUY/SELL signal, the
  allocator, and — per tonight's ad-hoc candidate scan — the raw material for
  any future thesis. If its useful signal genuinely collapses inside 5 days
  and reverses by day 21, it cannot support the theses this system is
  actually built around: HUBS.NYSE alone has a 365-day timeline. A model
  whose edge dies in single-digit days cannot be the basis for a position
  meant to be held for months. That is a **horizon mismatch at the core of
  the product**, not a tuning problem.
- Nothing about tonight's governance work (Phase 0 through 2b, all shipped
  and merged) protects against this. The contamination-isolation gate
  (`approved_for_allocation`) verifies a model was *deliberately approved* —
  it says nothing about whether that model's signal is *actually reliable
  over the holding periods the system assumes*. Those are different
  questions, and only the second one is in doubt right now.
- What IS known, checked live tonight (2026-07-04): `signals` has 15 distinct
  `as_of` dates for `model_a`/`v1_5`, spanning 2026-05-20 → 2026-07-02
  (25,514 rows, 1,725 symbols) — enough real history to attempt a genuine
  decay check, just not yet done. `generate_signals` is running successfully
  on schedule (not disabled at the infrastructure level); only the
  **retrain** cron (`asxos-retrain-model-a`) is suspended, meaning the model
  is frozen at its May 21 training snapshot and has not learned anything
  since. Whether "disabled" meant "retrain is paused" (confirmed) or
  "signals shouldn't be trusted right now" (not reflected in any DB flag)
  was an open question at end of session — resolve this explicitly with
  James before trusting anything downstream of `signals`.

### What the next session should do, in order

1. **Ask James for the ChatGPT audit** before doing anything else that
   depends on Model A. Read it fully; it may already answer everything below.
2. **Run the actual decay check** rather than trusting the claim or
   dismissing it. Concretely: for a sample of symbols with signals on
   multiple `as_of` dates ≥5 and ≥21 days apart, compare `prob_up` /
   `expected_return` / `signal_label` at day 0 vs day+5 vs day+21 — does the
   *ranking* hold up, flip, or go to noise? Rank correlation (Spearman) across
   the three horizons is the right tool. 15 dates over ~44 days is enough to
   attempt this, not enough for a rigorous walk-forward — say so plainly if
   the sample is too thin to be conclusive either way.
3. **If the claim holds up**: this is a `system-architect` / `backend-architect`
   conversation about what a model whose edge lives in a 0-5 day window
   actually implies for this system — a much faster rebalance cadence, a
   completely different position-holding philosophy, a different model
   architecture, or accepting Model A only for very short-horizon
   signals with a different mechanism for the medium/long-horizon thesis
   layer. Do not just re-tune hyperparameters and re-ship the same shape.
4. **If the claim doesn't hold up** (data was too thin, methodology error,
   or genuinely wrong): say so, show the numbers, and don't let this
   dispute linger unresolved into a third session.
5. **Either way**, this blocks Phase 2c (theme-researcher, instrument-selector)
   and any real (non-paper) capital deployment. The discovery/governance
   layer built tonight is real and worth keeping — it's just currently
   pointed at an engine whose reliability is an open question.

**Non-negotiable added to `CLAUDE.md` for this reason** (temporary, remove
once resolved): do not use Model A output, or anything downstream of it
(candidate scans, allocator runs, new thesis proposals), as a basis for real
capital decisions until this is resolved.

---

## The honest framing, for whoever reads this next

James's other statement tonight, verbatim: *"we've been building for 6
months and still aren't at a point where we can use this to start building
toward financial freedom."* That's a fair, sobering assessment and it should
not be argued away by pointing at feature velocity. Tonight alone shipped a
governance architecture, fixed a critical trigger-ordering bug that would
have broken Phase 1's approve/reject on first real use, resurrected an
entire dead data pipeline (12 of 29 render.yaml services had never been
provisioned — including the exact discipline-alert cron that should have
caught the HUBS stop breach three weeks before anyone noticed), and ran the
system's first real governed discovery cycle. All of that is genuine
progress on the *scaffolding*. None of it answers whether the thing the
scaffolding exists to serve — a model whose predictions are worth acting on
for months at a time — actually works. That is the real question, it is
still open, and infrastructure maturity does not substitute for answering
it. The right move now is exactly what happened: stop, question the
foundation, bring in outside review, and not build another layer on top
until it's resolved.

---

## Session summary (2026-07-04) — for context, not action

Three PRs merged to `main` (branch `claude/edmund-yong-open-items-7iaz23`,
now reset onto post-merge `main`, tree clean at `f5191e1`):

- **#11** — governance-first architecture Phase 0.5 through 2b (contamination
  isolation gate, 6-state governance workflow on theses/macro_theses/themes/
  theme_holdings, the `macro-economist` discovery agent, `/discover-macro`).
  Includes the critical fix: `apply_governance_transition()` did
  UPDATE-then-INSERT against `BEFORE UPDATE` triggers requiring a
  same-transaction audit row — order was backwards, would have failed
  Phase 1's shipped `asx thesis approve/reject` on first real use. Found via
  live rolled-back-transaction verification, not by any test or review pass.
- **#12, #13** — `ingest_market_context` had never executed in production;
  its first live runs (triggered manually tonight after provisioning) found
  and fixed four latent bugs in one evening: a fatal CTE alias typo, a join
  fan-out inflating every breadth ratio ~5×, a nonexistent EODHD ticker for
  AVIX (real one is `AXVI.INDX`, found by live-probing), and a fetch window
  that made three fields permanently `None`. Also fixed a token-leak into
  `ingestion_warnings` on fetch failure.
- **Provisioned 12 previously-nonexistent Render cron services** (of 29 total
  in `render.yaml` — no Blueprint has ever been connected to this repo, so
  render.yaml was never actually the deploy mechanism it was assumed to be).
  10 are live; 2 (`ingest_market_context`, `ingest_underlyings`) needed
  `FRED_API_KEY`, found on an existing service and copied over, now live too.
  This includes `check_us_positions` / `check_au_positions` /
  `check_thesis_invalidations` — the discipline-alert layer that would have
  emailed the HUBS stop breach on 2026-06-03 had it existed.
- **First real `/discover-macro` cycle**: `market_context_current` got its
  first-ever row; `macro-economist` proposed two theses (bracketing the one
  inflation leg the snapshot can't observe), logged as `agent_runs` #3 and
  #4 — validated through the real Pydantic/evidence pipeline, awaiting
  human review (`asx macro-thesis open --from-agent-run <3|4>` then `approve`).
- **HUBS.NYSE thesis**: full `/pm-review` — verdict was EXIT-CANDIDATE (stop
  breached 20 consecutive sessions, zero prior discipline trail, an
  FX-rate-dependent sign flip in the AUD P&L). James clarified HUBS is an
  ESPP grant in a **locked trading window** — cannot be sold regardless of
  the verdict. Thesis revised (revision #13, its first-ever) to record the
  lock and reframe the stop as a watch-level, not an executable trigger, for
  the duration. Earnings date set (Q2 FY26, ~Aug 5 2026, per external
  research — re-verify closer to the date). Portfolio demo config
  (`profiles.capital_aud=$500k`) switched off — `capital_aud` now reflects
  the real ~$6,667 (24 HUBS shares, the only holding), `cash_floor_pct=0`
  (no cash — it's all in HUBS).

## Pending, requiring James specifically

- The ChatGPT audit (see top of doc)
- Model A reliability resolution (see top of doc)
- HUBS lock-window end date (from the ESPP plan administrator) — add to
  `theses.tax_notes` once known
- HUBS acquisition FX rate — `holding_lots.acquisition_fx_rate=0.6450` is
  flagged "estimated" and disagrees with vendor FX (0.7171) by 11%, which
  flips the sign of the AUD P&L. Check the brokerage statement.
- Review/approve or reject `agent_runs` #3 and #4 (the two macro thesis
  proposals) — or let them sit; they don't expire
- Healthchecks.io API key, if he wants the 12 new crons' deadman monitoring
  set up programmatically rather than by hand (12 checks needed)
- Everything else in `docs/next-session-backlog.md`'s existing itemized
  list (ATO feed re-add, IRON.COMM/VIX.US/AUCBCNTO broken tickers, the HY-OAS
  units question macro-economist flagged, a real Render Blueprint connection)
  is still accurate and still lower priority than the two items above it.
