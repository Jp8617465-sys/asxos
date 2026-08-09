# Session handoff — 2026-08-10 (rules-integrity build PARKED at review stage)

**Parked by James's order after the session limit hit (resets 9pm Brisbane) killed the
review-loop agents mid-run.** Everything below is how to pick this up cold.

## Where everything lives

| Artifact | Location | State |
|---|---|---|
| Finance red-team deliverable | **PR #78** (docs-only, draft) + governor rulings D1–D9 recorded as PR comment | Awaiting James merge; rulings ENACTED (see below) |
| Rules-integrity build (this branch) | worktree `.claude/worktrees/rules-build`, branch `claude/rules-integrity-build` from `origin/main 1b471b60` | **WIP-committed locally, NOT pushed, review loop INCOMPLETE** |
| Red-team evidence (packet, manifest, panels, synthesis, 0042 design doc) | `/Users/jpcino/.claude/jobs/cb048518/tmp/` (job dir — copy out if the job gets deleted) + verbatim in PR #78's appendices file | Durable via PR #78 |
| D3 framework proposal (sourced caps/conviction values) | `docs/proposals/conviction-cap-framework-2026-08-09.md` (this branch) | Awaiting James's value decisions |
| D5 doctrine draft | `docs/proposals/policy-amendment-d5-decision-surface-doctrine-2026-08-09.md` (this branch) | James applies to `portfolio-policy.md` on merge (authority-guard blocks arbi) |

## What this branch contains (all tested before parking)

1. **Quick wins** (complete): `wealth_state` latest-close join fix + regression pin
   (register #8); `new_ideas` fail-closed + counted suppression line + 4 pins (#17/#27);
   position-monitor `cost_usd`→`cost_native` currency fix + FX-translated §5.4 break-even
   with named refusal (#11); monitor box de-imperativised + canonical classifier constants
   (#18).
2. **Core slice D1/D2/D4/R8** (complete, built from the backend-architect design at
   `/Users/jpcino/.claude/jobs/cb048518/tmp/design-0042-rules-integrity.md`):
   `migrations/0042_rules_integrity.sql` (NOT applied); `asxos/domain/theses/
   {condition_parser,conditions,lint,alerts}.py`; `asxos/domain/portfolio/locks.py`;
   `jobs/sweep_rule_integrity.py`; rewritten `jobs/check_thesis_invalidations.py`;
   attest/condition CLI verbs; `active_theses` collector rendering; `REQUIRED_MIGRATIONS`
   95→96; sweep step appended to `.github/workflows/weekly-research.yml`.
3. Verification at park time: full sweep **2035 passed / 0 failed** (pr71 venv:
   `/Users/jpcino/Desktop/asxos-wt-pr71/.venv/bin/python`); targeted core-slice re-run at
   park: 85/85; ruff + mypy clean.

## Review-loop state (THE unfinished thing)

- `portfolio-invariant-guard` on `locks.py`: **PASS**, two advisory items NOT yet applied:
  (a) `locks.py:11` docstring lists the sweep as a consumer — it isn't; fix docstring or
  wire it; (b) append `, id` to the lock query's ORDER BY for a deterministic `lock_note`
  on ties. Plus one PR-body note: the dormant allocator path doesn't consult locks —
  acceptable while section 6 is dark; revisit at M13.8.
- `security-engineer`, `refactoring-expert`, `technical-writer`: **DIED MID-RUN on the
  session limit — their reviews MUST be re-run on this exact diff before the PR leaves
  draft.** No edits from them landed (verified: suite green, diff inventory unchanged).
- The WIP commit below used the review-gate marker as an **explicit, documented bypass**
  to park safely — it does NOT count as the review having run. Re-arm: any new change
  re-keys the marker anyway.

## Resume checklist (in order)

1. `EnterWorktree`/cd `.claude/worktrees/rules-build`; confirm `git log -1` shows the WIP
   commit and `git status` clean.
2. Apply the two invariant-guard advisories (locks.py docstring + ORDER BY tiebreaker).
3. Re-run the three dead reviewers on the full diff (envelopes are reproducible from this
   file's context; security focus: alerts.py escaping/action-gate, job env hard-fails +
   redaction, migration guards; tech-writer: new-module docstrings + append the
   authority-file doc deltas — CLAUDE.md schema list for 0042, draft
   `.claude/rules/thesis-integrity-conventions.md` — to the D5 proposal file).
4. Amend/commit through the gate properly, James pushes
   (`!git -C .../rules-build push -u origin claude/rules-integrity-build`), open draft PR
   (body must include: migration 0042 James-gated apply steps — rolled-back live replay
   against prod FIRST per the design §2 binding note; deploy AFTER apply because
   REQUIRED_MIGRATIONS=96; the allocator-locks M13.8 note; builder's two disclosed
   authority-guard `cp` workarounds on 0042.sql + weekly-research.yml, both eyeballed OK).
5. Then the parked remainder, in James-ruled order: **D6 design half** (classifier v1.1
   hysteresis + dislocation mode — approved BOTH halves; conformance half already in this
   branch; panel-6's parameters are the approved starting defaults, James confirms at PR
   review) → **D3 values** (James answers the six DECISION-FOR-JAMES lines in the
   conviction-cap proposal, then the small build: profile-derived bands, `wealth_state`
   denominator dual-reporting, `is_employer` field) → R5/R6 (deferred until fixtures).

## Standing external state (unchanged by this session)

- **PR #78**: draft, awaiting James's merge (docs-only).
- **Render decommission gates**: first scheduled green daily (Sun 20:30 UTC = Mon 06:30
  AEST — includes B1 `score_macro_theses` first run, covers 2 of 3 macro theses; #11 has
  no machine_conditions), green Saturday weekly chain, green backup artifact
  (`BACKUP_GITHUB_TOKEN`/`BACKUP_REPO` secrets — set if not yet), then delete services +
  close account. `us-positions.yml` schedule error still to fix-or-re-decide.
- **James's own actions still open**: D9 brokerage-statement FX resolution (0.6450 vs
  0.7171 vs 0.7162 — AUD P&L sign depends on it); HUBS re-attestation via
  `asx thesis attest` once 0042 is applied; PR #78 merge; D3 value decisions.

## Context for whoever resumes

The through-line: James charged that the system gave bad advice on arbitrary rules → the
governor-corrected red team confirmed 31 defects (root causes: unvalidated authoring,
write-once trigger primitive, placeholder/serious indistinguishability) → James ruled
D1–D9 → this branch implements the approved core. The north-star anchor for every
remaining choice: **discipline events must reach James before they cost money, and a
placeholder must never masquerade as conviction.**
