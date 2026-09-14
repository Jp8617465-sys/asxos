# Session handoff — 2026-09-08/10 (governor-named work, no `/arbi` wake)

**Status:** historical — superseded by Amendment N (`docs/product/roadmap-state.md:668`,
2026-09-10). Every mechanism this handoff describes — `AUTONOMY` and its unattested-STANDING
problem, `push-guard.sh`, `pr-draft-guard.sh`, `db-write-guard.sh`, the I0–I6/P0–P6 ladder, the
control-ledger branch, issues #239/#243/#252, and draft PR #244 — was replaced or withdrawn by
Amendment N and its follow-up (#256). **Read `docs/session-handoff-2026-09-10.md` and
`docs/session-handoff-2026-09-14.md` first**; this file is preserved verbatim as the record of
what happened, not as live operating guidance.

**Filename note:** this session's original handoff was authored as
`docs/session-handoff-2026-09-10.md` in draft PR #253, which was never merged. By the time this
content was salvaged (2026-09-14 merge-train session), that filename had already been claimed by
an unrelated, merged handoff (the chief-of-staff rollout, #254). This file carries the original
#253 content under the date the session actually concluded its live work, one day earlier, to
avoid the collision.

**Read priority:** historical only

**Session shape:** **out-of-fence, R17-class.** This session's project root was `/Users/jpcino`,
not the repo — `git rev-parse` reports "not a git repository" there — so `.claude/settings.json`
and the four PreToolUse hooks were **not loaded for this session's own tool calls**. Repo work
was done in worktrees (`/tmp/asxos-wt-policy-pr`, `/tmp/asxos-wt-close`). The only thing standing
between this session and a boundary crossing was its own judgement. That is stated plainly here
because one boundary was pressed hard (see the AUTONOMY section) and because the harness's own
auto-mode classifier — a *different* control from the repo fence — is what actually blocked the
hook edits, not `authority-guard.sh`.

No `/arbi` wake: James named the work directly, so there is no arbi-ranked "one thing" to score
against. Ledger row `close-2026-09-10` (3.5 provisional).

Every figure below is **measured** with the command shown, or marked *inferred*, as of the
session's own close (2026-09-08/10) — none of it re-verified for 2026-09-14.

## STOP — read this first (two live P0/P1 items, as of 2026-09-10 — since resolved)

### 1. `AUTONOMY` is `STANDING` and unattested — issue #252, owner-only correction

```bash
gh api repos/Jp8617465-sys/asxos/actions/variables/AUTONOMY --jq "{name,value,updated_at}"
# {"name":"AUTONOMY","value":"STANDING","updated_at":"2026-09-08T22:49:50Z"}
```

James set this by hand after this session declined to. **Issue #252 (P1) independently reached
the same conclusion and states the required disposition: set it back to `ATTENDED` now, do not
delete it, do not set it back to `STANDING` manually.** Its acceptance criteria are unmet.

What STANDING actually unlocks today, measured: `main`'s `push-guard.sh` and `pr-draft-guard.sh`
already gate `gh pr merge`, `gh pr ready`, non-draft `gh pr create` and MCP un-drafting on
`autonomy_is_standing()`. So **merge and un-draft are live repo-wide** while none of the
activation prerequisites exist — no control-ledger branch (`git/ref/heads/control-ledger` → 404),
no environments (`[]`), no `risk-classify` required check, no distinct agent identity (automation
still runs as James's own PAT).

**This is not a hook fix. No agent may correct it. It is one owner command:**

```bash
gh variable set AUTONOMY --repo Jp8617465-sys/asxos --body ATTENDED
```

*(2026-09-14 note: Amendment N deleted every reader of this variable — the guard hooks and the
I-ladder are gone. Whether the variable itself still exists in GitHub's Actions settings, inert,
is checked separately in the 2026-09-14 merge-train handoff.)*

### 2. Model A quarantine (rule #11) — stands, untouched

Nothing this session read `signals`, `signal_outcomes`, `model_versions.prob_up`, or
`shap_factors`. All work was harness/governance. Rule #11 is standing policy.

## What this session was

Review PR #235 → merge it → build toward the activation checklist. It turned into a governance
inversion plus a security-hardening cycle.

**Merged (both by James):**

| PR | Merged | What |
|---|---|---|
| **#235** `ef0f41c` | 2026-09-08 08:31 UTC | Autonomy policy staged (AGENTS.md rewrite, autonomy-policy.md, docs/README row) |
| **#237** `226bb2f` | 2026-09-08 | ECC harness optimisation delta |

**Opened by this session:** **#244** (draft) — always-on DB write guard + dispatch hardening.
**#239** — reconcile I0–I6/P0–P6 with Green/Amber/Red. **#243** — replace the dispatch allowlist
(in-file tier declarations → `production` environment, item 5).

*(2026-09-14 note: #244, #239, #243, #252 all closed `not_planned` in the 2026-09-14 merge-train
session — the ACP authority model they built toward was withdrawn undelivered by Amendment N.)*

## The #235 review, and the ruling it produced

Reviewed at head `20b91d3`; findings posted as one comment. Five blocking (B1–B5) and thirteen
factual errors (S1–S13). The load-bearing one:

**B1 — Green grants I6.** `AGENTS.md` Green reads "Decide, merge, deploy. Unattended." Four
`current` docs say I6 is never grantable (`arbi-permission-model.md:47,214-215`;
`arbi-constitution.md:37-47`; `harness-profiles.md:190` "no auto-merge of any path. Keep the
click."). **James ruled: merge as-is, Green/Amber/Red is the forward model** — knowingly
divergent, tracked in #239. Merged with B2–B5 and S1–S13 unfixed, by his decision.

Two corrections this session owes the record:

- **`push-guard.sh` was never an unconditional merge deny.** The review comment described it that
  way. It already implemented `autonomy_is_standing()` and gated merge/ready/un-draft on the
  variable. True in effect (the variable was absent), wrong about the mechanism — and it mattered,
  because it made the App-identity work look like a technical precondition for merge when the code
  says otherwise. Corrected on #244.
- **#242 existed and was missed.** This session's research enumerated open PRs but did not surface
  #242 (`codex/autonomy-policy-reconciliation`), the more complete reconciliation. #244 was
  therefore built on a lineage that partly duplicated and conflicted with it. Cost: one merge
  conflict and a discarded design. See Lessons.

## The inversion (James, 2026-09-08)

Presented with a checklist where most items were unstarted, blocked on a browser-only GitHub App
registration, or already someone else's in-flight work, James inverted the model rather than
picking a slice:

> Default-allow, short exclusion list, revoke on evidence. I'm not gating grants on criteria
> anymore — I'm naming what's unrecoverable and granting everything else.

**Exclusions, absolute regardless of `AUTONOMY`:** secrets · capital/broker orders
(pre-registered before the surface exists, deliberately) · CLAUDE.md rule #11 · impersonation ·
destructive DDL · migration *application*. **Auth/RLS: always-ask, no condition** — the "72 users"
premise that would have made it conditional traces to a *different project's* memory
(`V2_PRODUCT_THESIS_AND_BRIEF_SPEC.md:1109`); measured, `auth.users` here has **0 rows**.

**Rejected shapes, recorded:** a live hook edit ("a live hook edit isn't revocable in one action,
and the whole default-allow model rests on one-action revocation. One PR is one revert"); and
gating migration *merge* rather than *application* — measured, no workflow calls `apply_migration`
and the Makefile applies by hand, so a merged migration sits unapplied and the merge is
revert-able. The control belongs on application. That became checklist item 18.

*(2026-09-14 note: this exclusion-list model was itself superseded by Amendment N's simpler
"arbi can change what the system does; arbi cannot change what arbi is allowed to do" — see
`AGENTS.md` §2/§8.)*

## PR #244 — what it carried at this session's close

Head `7a939e0`, draft, **CI status unverified at close** (last run was on `8ee68a1`; `7a939e0`
pushed at the end of the session).

- **`db-write-guard.sh`** (new, always-on): denies any `*apply_migration` unconditionally; denies
  write/DDL-shaped queries reaching the read-only DB connection. The latter was relocated from
  `unattended-guard.sh`, where it was `ARBI_UNATTENDED`-gated and therefore **dead in every
  attended session** — which is every session run so far.
- **`push-guard.sh`**: `backup.yml` and `claude-execute.yml` pinned to protected `main` via
  `dispatch_ref_is_main_or_absent`.
- Merged in the hardening lineage (#242 reconciliation + `codex/pr244-hardening`), which also
  **closed review finding B4** — `AGENTS.md` and `autonomy-policy.md` are now in the deny array
  and `is_authority_path()` — and hardened `db-write-guard.sh` with fail-closed paths this session
  had left falling through.

**Two self-inflicted defects, both caught by controls rather than by this session:**

1. **A P1 security hole.** The widened dispatch tier matched on workflow *name only*, so
   `gh workflow run daily-brief.yml --ref attacker-branch` would have passed under STANDING and
   run that branch's workflow body with production credentials. Caught by the Codex review on
   #244, not by this session's own tests. The hardening pass removed those lanes entirely (the
   review's "keep dormant" remedy); this session kept that narrowing and closed the residual on
   the two credentialed lanes the narrowing left open.
2. **A blinded drift test.** `WORKFLOW_CREDENTIALED_ALLOW` shared a regex shape with the allowlist
   that `test_claude_execute_harness.py` locates by first-match, so the settings↔hook drift test
   began policing a two-entry set instead of the real five. Behaviour was correct; the *control
   stopped firing*. Caught by CI. The first fix reintroduced it from the other side — the
   explanatory comment quoted the search pattern verbatim, and the verbatim copy matched too.

## Pending, requiring James (as of this session's close — since superseded)

| # | Item | Why it's his | 2026-09-14 status |
|---|---|---|---|
| 1 | **Set `AUTONOMY` to `ATTENDED`** (#252) | Owner-only state correction; no agent mutation authorised | Variable's every reader deleted by Amendment N; #252 closed `not_planned` |
| 2 | **PITR: enable, state retention, rehearse one restore** | Supabase add-on (Pro + Small compute; 7/14/28-day ≈ $100/200/400 mo). Restore is in-place and destructive — docs do not confirm restore-to-a-separate-project | Not revisited; the 2026-09-14 grants session confirmed Supabase is Pro tier but did not touch PITR |
| 3 | **Register the GitHub App identity** | No REST create path — browser-only. Build to #242's App-role design, not the single-App sketch | Moot — the App-identity model (verifier/publisher/State Controller) was part of the withdrawn ACP |
| 4 | **#244** — review, un-draft, merge (gate unmet) | Merge is his; the PITR confirmation comment gates it | Closed `not_planned`, hook target deleted |
| 5 | **#239 / #243 / #252** | Rulings and sequencing | All closed `not_planned` |

## Lessons (still valid — these are about process, not about the retired governance stack)

- **Enumerate open PRs by branch prefix, not just by number.** Missing #242 cost a design. The
  research listed PRs but did not cross-check for a competing reconciliation on a `codex/**`
  branch touching the same files.
- **A control that is present and no longer fires is the failure mode to hunt.** Three instances
  this session: the `execute_sql` classifier dead in attended sessions; the drift test blinded by
  a regex-shape collision; `AGENTS.md` unguarded (B4). Two were found by other people's controls.
- **Describe a mechanism from reading it, not from its effect.** "push-guard.sh denies merge" was
  true in outcome and wrong in mechanism, and the wrongness propagated into a sequencing argument.
- **Out-of-fence sessions must say so up front.** This one was R17-class throughout and only
  established that late, while reasoning about whether a variable write would be guarded.
