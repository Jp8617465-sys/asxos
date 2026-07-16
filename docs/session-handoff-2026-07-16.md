# Session handoff — 2026-07-16

**Status:** current
**Scope:** whole repo / session handoff
**Last verified:** 2026-07-16
**Read priority:** read first
**Superseded by:** N/A

Read this before doing anything else in this repo. The reconciled state in
`docs/product/roadmap-state.md` and the decision log in
`docs/product/decision-log.md` remain accurate; this says what actually matters
right now and what is waiting on James.

---

## STOP — read first: rule #11 (Model A quarantine) is STANDING policy

Unchanged and untouched this session. The Model A dispute is **RESOLVED (2026-07-11,
against Model A** — no usable edge on 19,032 matured signals); the ML engine is **SHELVED**;
rule #11 is **standing policy**, not a P0 to resolve. Do not act on Model A output for
capital, do not re-run the decay check, do not remove rule #11 on the basis of v1_5.
`asxos-retrain-model-a` stays suspended. **Everything this session shipped is
model-independent.**

---

## What shipped this session (7-hour dev-mode session)

All on branch `claude/dev-mode-planning-gz83bh`, open as **draft PR #47** (NOT merged —
James's call). Nothing reached `main` this session.

**Commit `d11a570` — regulatory-feed degraded-note visibility.** `regulatory_events` is
starved (~2 rows) while `ingest_regulatory` reports green: `assert_partial_success(0.5)`
passes on RBA alone while Treasury is WAF-403'd from Render egress — a dead source hiding
behind a green cron. Fix surfaces it: `JobMonitor.note` → `error_message` on a success run;
`_degraded_note()` in `ingest_regulatory`; `check_cron_health` check #4 raises a `DEGRADED:`
alert; `html.escape` hardening on the alert body. Model-independent, no migration.

**Commit `b4baf5e` — CGT tax-actions fold (James's "fold it (1)").** The 12-month
CGT-boundary fact already shipped as the standalone, **ungated** "Tax actions" table (a real
R12-class firewall gap — it rendered personal CGT facts without the `ASXOS_PERSONAL_USE`
gate its siblings have). Folded onto one gated, quiet-by-default surface: retired
`TaxAction`/`_tax_actions`/the template table; added `_cgt_boundary_findings()` (gated,
reuses `days_to_eligibility` §5.1, evidence-only `info` findings, `s 115-25(1) ITAA 1997`).
Closes the ungated leak.

Both went through the full review loop (security · tax-spec · refactor · docs) and are
ruff/py_compile/mypy-clean; new unit tests run in **CI only** (no project venv in the sandbox
— the documented dep gap).

**Process note:** `/arbi` wake → `arbi-red-team` **CHALLENGE** of the ONE THING (correctly —
the requirements-analyst spec revealed the "CGT flag" was **already shipped**, avoiding a
duplicate build) → James steered to stream B + the fold.

## Pending, requiring James (nothing below is arbi's to self-serve)

1. **Merge PR #47** (or split its 2 commits onto separate branches). Draft; not merged.
2. **Treasury feed remediation** — the actual fetch fix needs a **Render-egress diagnostic**
   (`curl -A <UA> -v https://treasury.gov.au/news/rss` from Render) → then a cookie/Referer
   fix, retire like ATO, or add an ASIC/ATO source. Capital-independent; PR #47 only makes
   the dead feed *visible*, it does not revive it.
3. **Supabase read-only MCP grant** — the read-write server returned "requires approval" on
   every call (the verbal OK never registered a permission grant) and `supabase-ro` was not
   connected. **No live-state verification was possible this session** (freshness/job_runs are
   state-thin). Needed to verify the brief end-to-end and to feed the dynamic-announcement work.
4. **Standing rule James set (2026-07-16):** "when I say *end session*, run `/arbi-close`
   automatically." Honoured this session; to persist across sessions it needs a line in
   `CLAUDE.md` (or the arbi command docs) — both deny-listed for agent edits, so it's a
   one-line add for James or a drafted change for approval.

## Next-build candidates (self-drivable once unblocked)

- **Dynamic "tax actions on new legislation"** — surface `regulatory_events` with
  `kind='tax'` (Div 296 / ATO / franking) as evidence-only findings in the same tax/discipline
  surface. Designed this session; gated on the tax feed being alive (item 2), and dedup vs the
  existing holdings-matched `_regulatory_hits` section; true "new since yesterday" wants the
  PR3 findings-sink (unbuilt).
- **`cgt.eligibility_date()` DRY helper** — centralize the §5.1 `+1yr+1day` formula (now a
  3-way copy of a rule-#6-governed expression: `cgt.py:34`, `cgt.py:41`, `compose.py`);
  flagged by both the tax-spec and refactoring reviewers.
- **`.claude/rules/job-conventions.md`** — note that `error_message` can carry a degraded
  note on a `success` run (deny-listed this session).
- Dead `tax_rows` test fixture in `test_brief_compose.py` (~14 sites, inconsequential).

## Files touched this session (branch `claude/dev-mode-planning-gz83bh`, PR #47)

`asxos/jobs/utils/job_monitor.py`, `jobs/ingest_regulatory.py`, `jobs/check_cron_health.py`,
`tests/test_ingest_regulatory_job.py`, `tests/test_check_cron_health.py`,
`tests/test_job_monitor.py` (commit `d11a570`); `asxos/brief/compose.py`,
`asxos/brief/templates/brief.html.j2`, `tests/test_brief_compose.py` (commit `b4baf5e`).

Plus the `/arbi-close` docs: this handoff, `docs/product/decision-log.md`, and
`docs/product/roadmap-state.md`. **These close docs must reach `main` to be seen next session**
(a handoff on a feature branch only is a process defect, `docs/README.md`) — commit them and,
on the next `/ship`, get them to main.
