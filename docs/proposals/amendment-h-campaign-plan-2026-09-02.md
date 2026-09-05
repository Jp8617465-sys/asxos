# Amendment H — the autonomous completion campaign (Stages 0→6) — campaign plan

_Plan drafted 2026-09-02 from the `/arbi` wake of the same day. All file:line cites verified
against `main` @ `55f2619` this session. Approving this plan = "go" on Wave 0._

## Context

James's instruction (2026-09-02): take the 2026-09-02 wake, turn it into a comprehensive task
list covering the live defects **and** Stages 0→6, authorise all of that work and the agents
required, and have arbi run it in an autonomous session via `/arbi-mission` until finished —
decisions delegated to arbi against the north star, the governance set, and the roadmap docs.

What prompted it: the wake found the product spine moving (Slice 1 decision packet live, #183)
while the operational floor is cracked (`backup.yml` red 12 runs, dark surfaces #1/#4 expired
unruled, no `/arbi-close` for the 09-01/02 session) and the Stages 1→6 table has not moved since
2026-08-10.

Intended outcome: one ratified campaign envelope (**Amendment H**) that lets the main loop chain
missions end-to-end without returning to James per unit, with every hard stop named up front so
the run never stalls on an unasked question and never silently crosses a boundary.

## What "full autonomy and authority" can legally mean here — read first

The governance set distinguishes two things James might be delegating. One is grantable; the
other is not — by James's own constitution, and mechanically by hooks that do not read prose.

**Grantable — SEQUENCING and in-tier DECISIONS.** Precedent: Amendment B
(`docs/product/roadmap-state.md:136-170`, "execute remaining to-do list to completion") and
Amendment D (`:172-210`, dispatch rows "without returning to James for per-item
authorization"). Recorded as **Amendment H** in the GOV-01 two-artifact form (roadmap-state
amendment + `decision-log.md` row; template `decision-log.md:102`). Letter C is burned
(`:347-348`); H is next.

**Not grantable — TIER.** I5/I6 (merge, migrate, secrets, prod DB writes, deploy) and P5/P6
(capital) are "never promotable… No track record unlocks these"
(`arbi-permission-model.md:46-47, :203, :253-254`; `arbi-constitution.md:37-47`). Mechanically:
`push-guard.sh:156,161-162` kills `gh pr merge`/`gh pr ready`; `pr-draft-guard.sh:53-89` forces
draft PRs; `settings.json:71-107` + `authority-guard.sh` deny edits to `.github/**`,
`docs/README.md`, `north-star.md`, the `arbi-*` governance set, `.claude/**`, `render.yaml`,
`rubrics/**`. Standing unattended mode (`ARBI_UNATTENDED=1`) is off and its preconditions are
open (`arbi-autonomy-loop.md:95-116`).

**Therefore the run shape is:** an *attended* session window James opens (recipe-grant form,
`arbi-goal-recipes.md:16-75`) inside which the main loop chains missions without per-item
approval, produces draft PRs, and accumulates a numbered **James click-list**. James's
involvement collapses from "approve each unit" to "clear the click-list per wave". That is the
maximum autonomy the constitution and the hooks permit.

| James-only action | Why | Where it falls |
|---|---|---|
| Merge / mark ready | constitution `:37-47`; hooks above; Amendment G ruling 3 "keep the click" | end of every mission |
| Apply a migration | I5; `unattended-guard.sh:313-315` | 0049–0052, 0045 |
| Edit `.github/**` | deny list; observed live 2026-08-25 | backup env line, schedules |
| Create a secret | constitution; `claude-execute.yml` hard stop | backup deadman, S3 |
| Dispatch a production workflow | I6; `push-guard.sh:205` | backup re-run + restore drill |
| Flip a dark-launch env var | P5/P6; `dark-launch-exit-plan.md:234-236` | dark surfaces #1/#4 |
| Edit governance set / `docs/README.md` / rule #11 | Tier C | doc-drift text drafted, James applies |
| S3 bucket, Dagster spend, risk calibration | F6 / F5 / F4 rulings | Stage 1 close, Stage 4 action state |

## 1. Amendment H — text James ratifies (goes into `roadmap-state.md` after Amendment G + a decision-log row)

> **Amendment H — campaign sequencing + bounded decision delegation (James, 2026-09-02).**
> James instructed: pull the 2026-09-02 `/arbi` wake into a complete task list covering
> Stages 0→6, authorise all reversible work and every roster agent, and let arbi run it via
> `/arbi-mission` until complete, decisions delegated to arbi against `north-star.md`, the
> governance set and `roadmap-state.md` / `target-architecture.md`. Effect:
> 1. **Sequencing.** arbi may chain the Wave-plan missions in any dependency-respecting order,
>    including parallel packet missions, without James naming each pair (extends Amendment B
>    `:136-159` and its rider `:160-170`). Stacking per Amendment A; a merge conflict stops the chain.
> 2. **Decisions arbi makes alone** — anything inside `arbi-constitution.md:30-34` ("what
>    matters next, what is blocked, which specialist, what evidence counts as current truth,
>    when a PR is good enough, when a claim is stale"): backup-membership calls, contract-recording
>    calls, slice ordering, replay-date and positive-control **method**, doc-drift corrections in
>    unguarded `docs/**`.
> 3. **Decisions arbi drafts, James ratifies** — dark-surface verdicts, migration application,
>    any workflow/schedule, any environment flip, capital/risk calibration (F4), authority-set
>    edits, ADR rulings named James-only.
> 4. **Hard stops, unchanged** — no merge/ready/un-draft, no non-draft PR, no migration apply,
>    no secrets, no prod DB write, no deploy/scheduler cutover, no `.github/**` or authority-set
>    edits, no capital action, rule #11 standing, `signals` never read as evidence, W1-2 never #1.
> 5. **Click-list.** Every mission writes its James clicks into `docs/product/james-inbox.md`
>    under `## Amendment H click-list`, numbered `H-nn`, each with the exact command / secret
>    name / ruling text. arbi never blocks on a click while an independent node exists
>    (recipe R1 "JAMES_NEEDED → pivot", `arbi-goal-recipes.md:63-66`).
> 6. **Completion.** The campaign ends when every node is `done`, `parked-with-trigger`, or
>    `JAMES_NEEDED`, and no Stage cell has flipped without its `target-architecture.md` §15 exit
>    gate cited (`roadmap-state.md:58-60` anti-drift: never flip a cell because a work order landed).
> 7. **Expiry / kill switch.** H expires at the end of the attended session window in which it
>    is ratified, on James saying "stop", on any `arbi-permission-model.md` circuit breaker, or on
>    two consecutive NOT-READY passes on one mission. `ARBI_UNATTENDED=1` stays off.

## 2. Wave plan

Route legend: `/build` one-file · `/arbi-mission` multi-node · `/arbi-team` large parallel ·
**James** = click only. Every mission: `arbi-red-team` vet → `guilfoyle` graph → specialists →
`make check` → draft PR on `claude/<id>` → readiness pass → ledger row `task_type: mission` +
decision-log row + Amendment E field (`renders:`/`captures:`/`defect:`) + `episode_score`.

### Wave 0 — record, close, contain irreversible loss (THE ONE THING)

**H0-A · Record Amendment H + `/arbi-close` for 2026-09-01/02** — `/build` (docs).
Agents: `technical-writer`. Files: `docs/product/roadmap-state.md` (amendment after `:348`),
`docs/product/decision-log.md`, `docs/product/arbi-run-ledger.md`, `docs/product/james-inbox.md`
(click-list heading), new `docs/session-handoff-2026-09-02.md`. Done when: amendment text
present; ledger row for the 11-PR session with a real `episode_score`; inbox has `H-01…`.
Clicks: **H-01** ratify Amendment H (reply "ratified"); **H-02** merge.

**H0-B · Fix `backup.yml` red (12 runs since 08-23)** — `/arbi-mission`. Advances Stage 1
exit clause (3) "backup/restore is observed" (`target-architecture.md:986-1002`) under Errata E7
"contain irreversible loss first". Agents: `security-engineer` (credential path + assertion
blast radius), `backend-architect`, `refactoring-expert`, `technical-writer`.
Diagnosis fact already in hand: the 2026-09-01 log (run `33537342381`) says "no file… matches
the recorded sha256 for signals" — the archive directory exists; the digest does not match.
Steps: (1) Re-order `scripts/backup_irreplaceable.sh` so the dump `cp` + commit (`:178+`)
precede the frozen-evidence check (`:147-176`); the check becomes a trailing step that still
exits non-zero with a distinct message — dump is safe, integrity signal preserved, assertion
NOT deleted. (2) Add the five 0048 tables (`evidence_packets, thesis_versions,
challenge_results, portfolio_assessments, decision_packets`) to the dump list `:88-101` (arbi
decision D-1 below). (3) `tests/test_backup_script.py`: pin the five tables; pin that `cp
"$DUMP_GZ"` appears before the `SIGNALS_SHA256` loop; pin the deadman env name appears in
`backup.yml:41-45` (fails until H-04 lands — keep as an xfail-with-reason until then, not skipped).
(4) `docs/RUNBOOK.md:122-131` add the frozen-evidence cause; `roadmap-state.md:516` replace
"OBSERVED GREEN" with the red span + fix PR. (5) PR body carries the exact two-line
`backup.yml` patch (env line + 0048 tables in the restore-drill array `:226-230`) for James.
Done when: `pytest tests/test_backup_script.py` and `make check` green; draft PR.
Clicks: **H-03** add secret `HEALTHCHECK_URL_BACKUP_IRREPLACEABLE`; **H-04** apply the
`backup.yml` patch; **H-05** merge; **H-06** `workflow_dispatch backup.yml` then
`restore_drill=true`; **H-07** (conditional) inspect `$BACKUP_REPO`'s
`signal-evidence-2026-08-16/` + `MANIFEST.txt` and report the file digests so the constant can be
corrected in a follow-up `/build`. Evidence: `defect:` failing run id + green run id after H-06.

### Wave 1 — hygiene + governor drafts (all parallel; no DB, no schema)

**H1-A · `check_cron_health` weekend false positive (B5)** — `/build`.
`jobs/check_cron_health.py:86-101`: per-job expected cadence (weekday-only jobs allow ≥60h over
weekends) instead of a flat 36h. Test: a Monday-UTC run does not flag a Friday job.
Click: **H-08** merge. Evidence: `defect:` the 08-31 `job_runs` row.

**H1-B · RENDER-RETIRE residue (B2/B3)** — `/build` for `jobs/check_us_positions.py:5`
(13:30 → 21:30 UTC). `render.yaml` is authority-guarded: arbi drafts the removal PR body +
`tests/test_render_backup_build.py` disposition per `scheduler-inventory-2026-08-13.md` §5.
Click: **H-09** James commits the `render.yaml` removal.

**H1-C · Migration headers 0039/0043/0044 (B8/C18)** — `/build`. Editable under D7
(`architecture-decision-record.md:185`). Replace "NOT APPLIED" with ledger version + date
(0043 `20260812092925`; 0044 `20260821080458`; 0039 `20260716105339`). 0045's DRAFT header is
correct — untouched. Click: **H-10** merge.

**H1-D · Orphaned 08-21 snapshot (B9)** — `/build`: land it as
`docs/archive/arbi-wake-2026-08-21-orphaned.md` with a superseded banner. Click: **H-11** merge.

**H1-E · Dependabot #178 + C10** — `/arbi-mission`. Agents: `tech-stack-researcher`
(CLAUDE.md:215 routing), `refactoring-expert`. Files: `ruff.toml`, `mypy.ini`,
`pyproject.toml:76-77` (pytest-asyncio 1.x mode/loop-scope). Done when: a branch stacked on
#178 with config deltas and `make check` green under the bumped pins; one-paragraph memo each
on `mypy-baseline` / `pip-audit`. Clicks: **H-12** merge #178 + follow-up; **H-13** rule C10.

**H1-F · Doc-drift sweep (D3–D11; D1/D2 drafted)** — `/arbi-mission`. Agents:
`technical-writer`, `requirements-analyst`. Editable: `docs/next-session-kickoff.md`,
`docs/next-session-backlog.md:354`, ADR §4 corrections rows 6 (§3.5 stale post-#163) and 7
(ADR `:353,:467` "add signals/signal_outcomes to daily backup" contradicts
`backup_irreplaceable.sh:33-48,:127-130`), `dark-launch-exit-plan.md` countdown `:212-215,
:227,:230`, `james-inbox.md:56-57` deadlines, `roadmap-state.md:51` (F5/F6 work orders WERE
written and approved at G1, `decision-log.md:94`). Deny-listed → exact replacement text in the
PR body: `docs/README.md:20,39`, `.claude/rules/api-conventions.md:16-17,50-51`, the 11
`REQUIRED_MIGRATIONS` refs under `.claude/agents|commands/**`. Done when:
`grep -rn REQUIRED_MIGRATIONS docs/` returns only historical rows.
Clicks: **H-14** merge; **H-15** James applies the deny-listed text.

**H1-G · Governor-draft pack (C1/C2/C3/C5/C14/C15)** — `/arbi-mission`, read-only + docs.
Agents: `portfolio-invariant-guard`, `security-engineer`, `technical-writer`. Output
`docs/proposals/governor-drafts-2026-09-02.md`: (i) dark surfaces #1+#4 verdict draft —
recommend **KEEP-DARK, new expiry 2026-11-30, tied to Stage 4 case delivery** (the M13.8
4-week paper window never opened; SHIP would front a dormant rule-#11 allocator; DELETE would
remove the only instrument that can retire #1 — `dark-launch-exit-plan.md:26-39,194-206`);
(ii) #3 V2 tree pre-draft for 09-30; (iii) CBA thesis #1 `price_detached` check scheduled as
code in H5-C; (iv) ADR §3.5 rewrite text; (v) C15 recorded as arbi's decision (D-1).
Clicks: **H-16** ratify dark verdicts; **H-17** one-word retire CBA #1 row.

### Wave 2 — Stage 1 evidence foundation (P3-03; F5/F6 halves are James's)

**H2-A · `knowledge_date` future-guard** — `/arbi-mission`. Advances Stage 1 clause (1).
Agents: `backend-architect`, `refactoring-expert`, `requirements-analyst`. Files:
`jobs/derive_fundamentals_pit.py` + its domain step; new `migrations/0049_pit_knowledge_tier.sql`
(`knowledge_tier` = `filed | scheduled`); tests. Rule from `target-architecture.md:1310-1332`:
`report_date`-derived rows land as `scheduled`; replay reads `filed` only; never both under one
column. Done when: fixture with a future `report_date` yields `scheduled`; readers exclude it;
the live count (60 rows at 2026-09-13 when measured 08-18) is re-measured and recorded.
Clicks: **H-18** apply 0049; **H-19** merge. Evidence: `captures:` post-apply count by tier.

**H2-B · Replay harness + lineage resolver** — `/arbi-mission`. Advances clauses (1)+(2).
Agents: `system-architect`, `backend-architect`, `performance-engineer`, `refactoring-expert`.
Files: new `asxos/domain/replay/{cutoff,lineage}.py`, CLI `asx replay --date`, tests; reads
`rs_security_master`, `rs_financial_statements`, `rs_fundamentals_pit` (`0027`), `prices`,
`price_revisions` (`0043`). Replay date (arbi, D-4): TLS.AU 2025-08-21 cutoff already rendered in
#155. Done when: replay output hash identical across two runs; every canonical row resolves to a
raw source row id; `renders:` the replay table. Click: **H-20** merge.

**H2-C · F5/F6 execution (James)** — arbi drafts the S3 bucket policy (versioning, Object Lock
governance, lifecycle, least-privilege IAM) and a Dagster cost sheet from P3-01 (#117) /
P3-02 (#152). Clicks: **H-21** create S3 bucket + credentials; **H-22** approve Dagster spend;
**H-23** rule the Stage 1 cell wording ("gates (1)(2)(3) met in-repo, F6 raw-object retention
carried" vs OPEN). arbi does not flip the cell.

### Wave 3 — Stage 2 research registry (P4-01)

**H3-A · Contracts + registry** — `/arbi-mission`. Agents: `backend-architect`,
`system-architect`, `refactoring-expert`, `portfolio-invariant-guard`. Files: extend the
existing `asxos/domain/research/` package (currently `alpha_eval.py, alpha_loader.py,
factor_scores.py, segment_map.py`) with `{types,repository,harness,walkforward,promotion}.py`;
`migrations/0050_research_registry.sql`; tests. `ResearchHypothesis`/`ResearchRun`/
`StrategyVersion` content-addressed like `decision_engine/types.py:145`; promotion state
machine with **no code-reachable transition to capital** (gate 3, `target-architecture.md:
1016-1018`); failed variants retained (gate 2). Benchmark reports `unavailable` per F1
(`asxos/domain/benchmark/outcome.py:31-33`, `AXJOA.INDX` absent) — never proxied.
Done when: one hypothesis (arbi picks a simple, model-independent one, e.g. 12-1 momentum on
`prices` at 25 bp cost) reproduced twice with identical run hash from raw `prices`; a
deliberately failing variant remains listed; `renders:` the run table.
Clicks: **H-24** apply 0050; **H-25** merge.

### Wave 4 — Stage 3 theme + candidate engine (P4-02)

**H4-A · ThemeVersion + CandidateSnapshot** — `/arbi-team` (≤4 parallel). Agents:
`macro-economist`, `theme-researcher`, `sector-screener` (evidence), `backend-architect`,
`refactoring-expert`, `requirements-analyst` (LLM boundary spec). Files: extend the existing
`asxos/domain/themes/` (`service.py, stage_classifier.py, types.py`) with
`{measures,extraction_boundary,candidates}.py`; `migrations/0051_theme_candidates.sql`; tests.
Deterministic measures only in code; LLM output enters only as `EvidenceItem` with a tier
(`decision_engine/types.py:214-225`); `CandidateSnapshot` carries `expires_at` + quality checks.
Done when: one theme + one candidate reproducible from cited evidence ids, and no field named
recommendation/action exists on either (`target-architecture.md:1020-1033`); `renders:` the
candidate table. Clicks: **H-26** apply 0051; **H-27** merge; **H-28** schedule
`detect_theme_stages` (C4/D12 — F5 forbids new schedules unless James rules).

### Wave 5 — ADR §6 slices 2.5 → 2 → 3 (decision-engine generalisation)

**H5-A · Slice 2.5 challenge layer (first, D-3)** — `/arbi-mission`. Agents:
`backend-architect`, `portfolio-invariant-guard`, `tax-spec-conformance`, `refactoring-expert`.
Files: new `asxos/domain/decision_engine/challenge/{rules,steelman}.py`; shape reused from
`asxos/domain/results_review/challenger.py`; the 14 Layer-1 rules verbatim from ADR `:566-594`;
findings require `evidence_ids` (`types.py:310-317`); finding/disposition log from day one.
Done when: a fixture thesis breaching the cash floor cannot produce `outcome="pass"`; every
LLM finding carries an evidence id; outside-view pass flags absence of base-rate only.

**H5-B · Slice 2 sizer** — `/arbi-mission`, after H5-A. Re-home the existing Decimal-only
`asxos/domain/portfolio/allocator.py:156 inverse_vol_weights` and `constraints.py:189
apply_constraints` behind the ChallengeResult gate, emitting `SizeRange` (`types.py:348`);
cash floor 7.5%, LVR 0 (ADR D1/D2). Zero Model A import (regex test). Done when: `SizeRange`
non-zero only when challenge passes; property test cash ≥ 7.5% post-trade.

**H5-C · Generalise builder + CBA discipline + Slice 3 staging** — `/arbi-mission`.
`builder.py:130 build_cba_decision_case` → `build_decision_case(candidate_snapshot)`; add the
`price_detached` Layer-1 rule (C5); order staging via the tax module, non-executing (ADR `:368`;
`tax-spec-conformance` consult). Clicks: **H-29/H-30/H-31** merges.

### Wave 6 — Stage 4 one governed paper case (P5-02)

**H6-A · Positive-control case** — `/arbi-mission`. Agents: the 5 investment-analysis agents,
`portfolio-invariant-guard`, `tax-spec-conformance`, `security-engineer`, `technical-writer`.
Symbol method (arbi, D-5): top `CandidateSnapshot` from H4-A by quality score, an ordinary ASX
equity, excluding HUBS/CBA/ESS and anything lock/tax-uncertain (`target-architecture.md:
1035-1038`). Chain per `:1040-1051`; CLI and email renders byte-identical; `DeliveryReceipt` via
`brief_runs`. Done when: all identities resolve via `repository.load_case`; missing evidence →
`abstain`; renderers import no financial logic; process non-executing. **Without P5-01 (F4) the
case closes at `abstain`; an action-state packet also needs a real tax feed (`readiness ==
"pass"`) — recorded honestly, not fabricated.** Clicks: **H-32** P5-01 risk calibration;
**H-33** merge; **H-34** James Disposition; **H-35** rule C17 ThesisProposal authorship.

### Wave 7 — Stage 5 first observation (P7-01 + ADR Slice 4)

**H7-A · Outcome materialisation rebuild + t0 observation** — `/arbi-mission`. Generalise the
`macro_thesis_outcomes` pattern (`migrations/0041_macro_thesis_learning_loop.sql`) into a
`thesis_outcomes` migration `0052`; the 21/63/126-session read path drafted as workflow text for
James (F5). Captures t0 only. Clicks: **H-36** apply 0052; **H-37** merge; **H-38** schedule.

### Wave 8 — campaign close
`/arbi-close`, scorecard, ledger, handoff; Stage cells updated only with gate citations.
Click: **H-39** merge.

## 3. The James click-list (39 clicks, wave order)

| Wave | Clicks |
|---|---|
| 0 | H-01 ratify H · H-02 merge · H-03 secret · H-04 `backup.yml` patch · H-05 merge · H-06 dispatch backup + restore drill · H-07 inspect `$BACKUP_REPO` (conditional) |
| 1 | H-08 merge · H-09 `render.yaml` removal · H-10 merge · H-11 merge · H-12 merge #178 stack · H-13 rule C10 · H-14 merge · H-15 apply deny-listed doc text · H-16 dark verdicts · H-17 retire CBA #1 |
| 2 | H-18 apply 0049 · H-19 merge · H-20 merge · H-21 S3 bucket · H-22 Dagster spend · H-23 Stage 1 cell ruling |
| 3 | H-24 apply 0050 · H-25 merge |
| 4 | H-26 apply 0051 · H-27 merge · H-28 schedule `detect_theme_stages` |
| 5 | H-29 · H-30 · H-31 merges |
| 6 | H-32 P5-01 calibration · H-33 merge · H-34 Disposition · H-35 rule C17 |
| 7 | H-36 apply 0052 · H-37 merge · H-38 schedule |
| 8 | H-39 merge |

Carried, unscheduled (James, no wave dependency): B7 Supavisor repoint to `asxos_agent_ro`
then C9 `REVOKE SELECT ON signals`; C8 apply 0045; C6/C7 Amendment G environment steps; C13 D10
vs roadmap-state; B1 needs two green scheduled Saturdays (observe only); B6 `HC_NIGHTLY_URL`.

## 4. Decisions

**Arbi decides alone (authority `arbi-constitution.md:30-34`; Amendment H §2):**
- **D-1 · 0048 tables are irreplaceable: YES.** Content-addressed, append-only, record what
  James saw and decided (`0048_decision_packets.sql` header; `types.py:145`); not re-derivable.
  Into the dump list (arbi) and the restore-drill array (James, H-04).
- **D-2 · EvidencePacket contract.** Record the de-facto minimum shipped in #183 (thesis +
  price + portfolio state, `types.py:234`) as the Slice 1 answer to ADR `:356`; widen only via
  H4-A evidence tiers.
- **D-3 · Slice 2.5 before Slice 2.** The ADR places the sizer "downstream of the decision
  gate" (`:362`); that gate does not exist until 2.5; the sizer's blocking constraints are
  Layer-1 rules; the sizer is reuse (`allocator.py:156`) while the challenger is net-new, so
  net-new first surfaces design risk earliest. Both ship in one wave.
- **D-4 · Replay date** TLS.AU 2025-08-21. **D-5 · Positive-control method** as in H6-A.
- **D-6 · Backup fix shape** dump-before-verify under E7, assertion kept.
- **D-7 · Stage 1 split**: doable now = knowledge tier, replay, lineage, backup observed;
  blocked on James = raw object retention (F6), Dagster (F5).

**Drafted for James:** dark verdicts (C1/C2/C3), Stage 1 cell wording (H-23), P5-01
calibration, schedules (H-28/H-38), migrations 0049–0052, C17, C10, C13, C6/C7, C8,
`render.yaml`, deny-listed doc text, and Amendment H itself.

## 5. Stop conditions and recording
- Any hook denial on a write → record JAMES_NEEDED, pivot to an independent node; never route
  around (`decision-log.md:95-97` precedent).
- Two NOT-READY readiness passes → that mission stops. Red-team CHALLENGE on a wave envelope →
  that wave halts, next independent node proceeds.
- Merge conflict on a stacked branch → chain stops until James merges the predecessor.
- `make check` red after one fix attempt → PR stays draft, node parked with trigger.
- A node that cannot fill `renders:`/`captures:`/`defect:` → parked, not merged (Amendment E).
- Per mission: ledger row (`arbi-run-ledger.md:81-82` columns), decision-log row (`:102`
  template), `episode_score` from `arbi-scorecard.md` (never `—`), `james-inbox.md` H-nn rows.

## 6. Honest limits — what cannot finish in the session even with full delegation
S3 bucket/credentials (F6), Dagster deployment/spend (F5), P5-01 risk calibration (F4), any new
production schedule, `ARBI_UNATTENDED` mode, B1's two scheduled Saturdays, B7's Supavisor
repoint. Stage 5's 21/63/126-session horizons need roughly 1/3/6 months of paper observation
after Wave 6 — the session captures t0 only.
**Realistic end state:** backup green and observed; Stage 1 clauses (1)(2)(3) met in-repo with
F6 carried (cell flip is H-23); Stage 2 and 3 gates met with cited evidence; Stage 4 case
delivered and disposed by James — at `abstain` unless H-32 lands first; Stage 5 t0 captured, no
learning review; Stage 6 not reachable (needs a complete learning episode,
`target-architecture.md:1081-1083`). Programme "done" (`:1093-1112`) is not reachable this session.

## 7. Verification per wave
- **W0** `pytest tests/test_backup_script.py`; `make check`; the H-06 run shows `backup:
  success` + `restore_drill: success` with 19 table counts (`mcp__github__actions_get`);
  `mcp__supabase-ro__list_migrations` latest still `20260901062502`.
- **W1** `make check`; `pytest --co -q | tail -1` count not lower; `grep -rn
  REQUIRED_MIGRATIONS docs/` empty of live claims; CI green on the #178 stack.
- **W2** post-apply `SELECT knowledge_tier, count(*) FROM rs_fundamentals_pit GROUP BY 1`;
  replay hash equal on two runs; lineage 100% for the replay date.
- **W3/W4** run-hash reproducibility test; row counts on new tables after apply; grep proving
  no capital transition and no Model A import.
- **W5** property tests for cash floor and gate ordering; `pytest tests/ -k decision_engine`.
- **W6** CLI and email render sha256 equal; `brief_runs` DeliveryReceipt row; Disposition row.
- **W7** `thesis_outcomes` t0 row count; benchmark `unavailable` recorded, not proxied.
- **All** `make check`, CI `full-check` green, draft state confirmed via
  `mcp__github__pull_request_read`, ledger + decision-log rows present before each close.

## Immediate next action on approval
Run **H0-A** (record Amendment H, `/arbi-close` the 09-01/02 session, open the click-list),
then dispatch `arbi-red-team` on **H0-B** and execute it via `/arbi-mission`. Wave 1 nodes
start in parallel as soon as H0-B's draft PR is up.
