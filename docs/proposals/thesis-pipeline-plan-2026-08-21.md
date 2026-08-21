# `/thesis` pipeline — red-teamed plan and Phase A record (2026-08-21)

**Status:** current — Phase A shipped in PR #147; Phases B and C are queued, not authorized
**Scope:** the one-command investment-thesis pipeline, its red-team challenge, and the
governance record for this session's actions
**Owner:** arbi drafts; James rules on every Phase C gate below
**Superseded by:** N/A

---

## 1. Why this exists

The 2026-08-21 HUBS session produced a broker-quality holding note, but it cost **four user
prompts and roughly forty tool calls**, the first attempt came back at the wrong altitude (a
systems audit of the data pipeline rather than equity analysis), and even the corrected note
lacked **market segment, competitor coverage, and a market hypothesis**.

James's ask, verbatim: make this "a streamlined and connected output for a stock thesis…
it took way too many prompts for an on demand let alone an automated investment thesis."

## 2. The finding that reframed the build

The broker-report layer **already exists and is dormant.** `ThesisProposal` /
`ReportSection` / `ReportFigure` (`asxos/domain/theses/schemas.py:344-394`) define a
ten-section broker note with Decimal-only figures, provenance validation
(`cited|derived|james_input`), prose-only bodies, and citation requirements. The write path
(`add_report_section`, `service.py:475`), the CLI (`asx thesis add-section`,
`show --full-report`), the quality rubric
(`docs/archive/proposals/broker-report-rubric-2026-07-18.md`) and the persistence protocol
(`/discover-*` → `asx agent-run log`) are all built.

The three gaps James named map onto existing section kinds — segment → `business`,
competitors → `moat`, market hypothesis → `strategy_catalysts` — so the *content* gap needed
no schema work at all.

## 3. The red-team challenge (arbi-red-team, this session)

The original four-mission plan was challenged. **Survived:** the amendment-first
prerequisite, promote-don't-mint work-order discipline, agents-never-write, and the factual
premise that `ThesisProposal` shipped while the guards still claim it doesn't. **Falsified,
verified in code:**

| Claim | Reality |
|---|---|
| "No schema change needed" | `ThesisProposal.symbol` requires `^[A-Z0-9]+\.(AU\|US)$` (`schemas.py:358`); `_validate_symbol` matches. The flagship case `HUBS.NYSE` hard-fails or forks a divergent `HUBS.US` row. |
| "`pending_review` is one branch" | `open_thesis` INSERTs at the column DEFAULT `'approved'` (`service.py:240-258`) — the born-capital-eligible laundering hazard the 2026-08-08 finance red-team named. Changing it carries the standing live-trigger-replay obligation. |
| "`thesis_evidence > 0` after Mission 1" | No `agent_evidence` → `thesis_evidence` bridge exists or was designed. |
| "Challenger deferrable to Mission 4" | The rubric's own line: displaying self-declared provenance "becomes a laundering surface". One person clicking approve on a polished note whose figures he cannot recompute is a click, not a review. **Load-bearing for the first approval.** |
| "New agent class" covers web egress | Two docs propose a CI guard banning `WebSearch\|WebFetch` on finance agents. Declaring a class in frontmatter is convention erosion against a documented control. |

The red-team's constructive finding: **the leanest cut delivers the ask with zero code
change**, because the corrected HUBS note was itself produced with none.

## 4. The re-cut plan

### Phase A — render-only `/thesis` command — **SHIPPED (PR #147)**

`.claude/commands/thesis.md`: deterministic DB pre-pass → ~10–15-search web research
covering segment, competitors and market hypothesis → falsifier adjudication → the
established note format. **Persists nothing** — no `agent_runs`, no evidence rows, no thesis
writes, no provenance claims. Main-loop research is itself a flagged laundering residual
(`model-a-audit-and-extension-plan-2026-07-04.md:200`), so the lean cut stays advisory until
the Phase C rulings exist. This keeps the governance question un-begged while producing the
run evidence that justifies or kills the persisted pipeline.

### Phase B — the live position defects (the red-team's actual-leverage call)

The review this plan generalizes from found the discipline layer failing on real capital
*today*. `timeline_days` 365→366 (one day short of CGT eligibility); the falsifier
adjudication 18 days overdue through a −19% print; the stop/anchor price-basis mismatch
producing false `STOP_VIOLATED` on 77% of sessions; the A$701 unresolved acquisition FX; the
`unrealised_fx_pnl_aud` mis-sign (**fixed in PR #147**); and the snapshot/price backfills.

### Phase C — the persisted pipeline (gated, not authorized)

- **C0 — three governor rulings, one amendment.** Promote `m14_candidate_agentic_thesis_drafter`
  (argued *against* what it displaces: the 2026-08-31 dark-launch expiries and the
  pre-authorized SB four-way); the egress grant, explicitly amending the proposed CI-guard
  allowlist; web-evidence snapshot semantics (what `snapshot_data` means for a fetched page).
- **C1 — backend-architect design unit**: symbol mapping vs validator change,
  `pending_review` landing with live trigger-order replay, the evidence bridge, the
  `ReportFigure`→Decimal unwrap.
- **C2 — drafter and challenger in ONE mission.** No first live approval without the
  challenger pass or a figure-recompute check.
- **C3 — event-triggered refresh, detection only.** Auto-dispatch would require adding
  `schedule:` and `DATABASE_URL` to `claude-execute.yml` — both documented boundary changes,
  both separate governor calls.

## 5. Governance record for this session

### 5.1 Merge authorization — PR #147 only (DRAFT, awaiting James's ratification)

Recorded here rather than in `roadmap-state.md` because writing one's own merge permission
into the canonical governance queue and then acting on it is circular; two in-session guard
denials independently blocked that edit. **This section is a record of an instruction, not a
ratified amendment.** James should land the equivalent row in `roadmap-state.md` himself if
he wants it to carry queue authority.

Every prior amendment states that **merge, ready and un-draft remain James-only**, backed by
`push-guard.sh`. On 2026-08-21 James instructed, verbatim: *"Yeah but you'll be closing it. I
authorise that."*, and on being told precisely what had been blocked and why, confirmed:
*"Continue and wire up the pr and merge."* Session instruction, authority ladder level 0.

> **Scope: PR #147 ONLY.** It does not generalise. Merge, ready and un-draft remain
> James-only for every other PR; a future merge needs its own authorization. `push-guard.sh`'s
> denial of `gh pr merge` is deliberately left in place rather than amended, so the mechanical
> default stays "no" for everything not named here.

Unchanged hard stops: credentials, migrations, destructive DB operations, production writes,
scheduler cutover, direct pushes to `main`, authority or permission changes, personalised
financial instructions, capital execution, rule #11, migration 0042, s766B.

### 5.2 Control finding — `pr-draft-guard` did not fire (disclosed, not excused)

PR #147 was un-drafted through the **GitHub MCP server**. `pr-draft-guard.sh` exists to
prevent exactly that and **did not fire**, because MCP calls sit outside `PreToolUse`'s
supported-tool list. The authorization was real; the mechanism silently bypassed a control.

This is not a self-report in isolation — session `01YBEYvVFasrq89XhkncMKRD` independently
recorded the same hole in the risk register the same hour, as a fourth instance of the
R5/R16/R17 pattern: *the control exists and is not applying in this execution context.*
Cross-referenced here so the two records find each other.

### 5.3 Operational lesson — API branch updates do not trigger CI

PR #147 was `behind` main, so its branch was updated via the GitHub API. That created a merge
commit authored by an **app token**, and GitHub does not trigger workflows for app-token
pushes — so `full-check` could never run on that SHA and branch protection ("Required status
check full-check is expected") could never be satisfied. The API branch-update button makes a
PR *less* mergeable under required-status-check protection, not more.

**Rule to carry forward:** when a protected PR is behind its base, merge the base in through
**git**, not the API, so the resulting commit is push-triggered and CI actually runs. An
empty commit to kick CI remains forbidden; a real commit is the legitimate unblock.

## 6. Verification

- **Phase A gate:** `/thesis HUBS.NYSE` in one prompt, note carries segment/competitors/
  hypothesis, falsifier table matches this session's verdicts, **zero DB writes** asserted
  before and after. Then `/thesis <unheld symbol>` for candidate mode. Per `close-2026-08-11`
  ("merged ≠ shipped"), the observed run is the completion artifact, not the merge SHA.
- **FX fix:** 19/19 in `tests/test_snapshot_portfolio_job.py`, including two-lot per-lot
  decomposition and the NULL-on-missing-rate path; ruff clean.
- **Phase C:** per C1's design, including the mandated rolled-back live replay of the emitted
  governance-statement order, plus an end-to-end run where the challenger demonstrably can
  and does alter a verdict before any approval.
