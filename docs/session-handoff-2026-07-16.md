# Session handoff — 2026-07-16

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
