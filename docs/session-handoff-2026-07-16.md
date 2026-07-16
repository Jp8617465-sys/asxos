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

---

# Session handoff — 2026-07-16 (earlier same-day session: dream protocol + automation planning)

_Second handoff for the same date, from the `claude/dreams-protocol-arbi-6zaqk0`
session (PR #46). Kept in full below; the dev-mode handoff above is the later
session. Both are current._

**Status:** current
**Scope:** whole repo / session handoff (the dream-protocol + automation-planning session)
**Last verified:** 2026-07-16
**Read priority:** read first
**Supersedes:** `docs/session-handoff-2026-07-13.md` (its pending items are carried below)

Read this before doing anything else in this repo. This session was arbi-operating work
(memory consolidation + autonomy planning), not product-lane code — no `.py` touched, no
migration applied, no test delta.

---

## STOP — read first: rule #11 (Model A quarantine) is STANDING policy, not an open question

Unchanged from the 07-13 handoff: the Model A dispute is **RESOLVED (2026-07-11, against Model
A)** on 19,032 matured signals (`corr(ml_prob,21d)=−0.03`; STRONG_BUY −0.09% vs HOLD +5.07% at
21d). The ML engine is **shelved**; rule #11 is standing and mechanically enforced
(`approved_for_allocation=FALSE` → allocator hard-fails). Do not re-run the decay check, do not
act on Model A output for capital, do not remove rule #11 on the basis of v1_5.

---

## What this session did (all on draft PR #46, branch `claude/dreams-protocol-arbi-6zaqk0`)

1. **First live `/arbi-dream`** → `docs/product/memory/dream-candidates/2026-07-15-dream.md`:
   consolidated the 07-11..07-14 window (inputs captured by SHA). Proposes lessons **L8–L17**
   (primary L8–L14; L11 extends approved L7, L12 extends L1), names 3 repeated-mistake
   patterns, proposes retiring approved-lessons **L6** (superseded by the 07-11 Model A
   resolution — strike in place + append L14, append-only), surfaces **3 contradictions for
   James** (L-cand-2/3 numbering collision across working notes; `/pm-review` template still
   assumes a Model A signal vs rule #11; double-`0038` migration collision), and carries
   rule #11 / s766B / permission-tier text **verbatim**. Candidate only (ladder 7).
2. **Dream-automation plan** → `docs/proposals/arbi-dream-automation-2026-07-15.md`, from a
   4-agent fan-out (requirements-analyst, backend-architect, security-engineer GO-WITH-CONTROLS,
   arbi-red-team CHALLENGE). Reconciled call: **do NOT enable an unattended weekly dream yet** —
   the promotion gate has never been exercised (0 promotions ever), there is no backlog to
   dream, and unattended is the wrong mode for synthesis. Sequence: **Phase 0** promote #46 →
   **Phase 2** an emit-only demand-gated *poke* Routine (PR-7a-shaped, available any time) →
   **Phase 3** the unattended RUN only when earned, under a 7-control set. Durable findings:
   the **DB-role precondition is moot for the git-only dream slice** (replace with "no DB
   mount"); `ARBI_UNATTENDED=1` cannot be self-armed (must be in the Routine launch env); the
   GitHub MCP write path is denied unattended (a Routine must use `gh pr create --draft`);
   3 L16-class false-deny traps on the dream's write path (Write tool only, clean commit
   message, `--body-file`).
3. **Branch protection on `main` is PLAN-GATED — resolved as unavailable.** James attempted it;
   GitHub reserves branch protection + rulesets for paid plans on private repos (API 403s the
   same as the UI — no workaround; rulesets are public-repo-only on free). James declined the
   upgrade. Consequences recorded in the plan's **§Amendment** + risk-register **R5**:
   **CODEOWNERS is inert on this plan** (mechanical grader≠producer unavailable; promotion is a
   disciplined-process gate — James clicks merge). Substitute: a **detective `main-push-guard`
   Action** now (alarms on any direct push to `main`; ready-to-apply YAML embedded in
   §Amendment — arbi's Write to `.github/workflows/` was session-permission-denied and was NOT
   worked around, per the lockout lesson) + the **fork/machine-identity model** as the
   server-side backstop if Phase 3 is ever earned.
4. **Ledgers updated:** decision-log row `dream-2026-07-15`, run-ledger row `dream-2026-07-15`,
   roadmap-state header update, risk-register R5 amendment.

## Pending, requiring James (nothing below is arbi's to self-serve)

1. **Promote or reject draft PR #46** (`/arbi-promote`) — the highest-leverage item. This is the
   **first-ever exercise of the promotion gate** (promotion-log has only the 2026-07-10 seed).
   Expect to cull: L8–L14 are the core set, L15–L17 optional; adjudicate the 3 surfaced
   contradictions (the dream cannot). Merging #46 is also what lands this handoff + the ledger
   rows on `main` — until then they live only on the branch (the known process defect).
2. **Add `.github/workflows/main-push-guard.yml`** — copy the YAML from the plan's §Amendment
   (~2 min via the GitHub web UI). Note: it will alarm on your OWN direct pushes too (close the
   alert issue with a note — that closure is the audit trail).
3. **Poke Routine — arm or hold?** An emit-only weekly reminder to run `/arbi-dream` when ≥N new
   working notes exist. Zero unattended write; available whenever you say go.
4. **Carried from 07-13 (still open):** CBA thesis #1 fix-or-retire (data-entry error, revisit
   overdue); VGS.AU/VAS.AU holding-lot data (unblocks ETF Slice 2); PR #5 close recommendation;
   agent DB read-only role migration + MCP re-point (Phase 2c prereq; note the double-`0038`
   numbering collision — whichever applies first, the other renumbers to 0039).

## Files committed this session (branch `claude/dreams-protocol-arbi-6zaqk0`, draft PR #46)

`docs/product/memory/dream-candidates/2026-07-15-dream.md`,
`docs/proposals/arbi-dream-automation-2026-07-15.md`, `docs/product/risk-register.md` (R5),
`docs/product/decision-log.md` (+1 row), `docs/product/arbi-run-ledger.md` (+1 row),
`docs/product/roadmap-state.md` (header update), and this handoff.

These reach `main` when PR #46 merges (James's call — promotion and merge are the same act
here, so review the dream candidate before merging).
