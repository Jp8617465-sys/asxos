# Guard carve-outs — reducing James-keystroke friction for verified-safe shapes

**Status:** drafted 2026-08-12 at James's direction ("I trust arbi to do them and just get
arbi to create the shell and then copy and paste it anyway"); each artifact requires James
to apply — hooks and settings are authority surfaces arbi may only draft against
**Scope:** three artifacts — GitHub branch protection, push-guard dispatch carve-outs,
settings allow-rules
**Decision owner:** James (permission-model boundary changes, `arbi-constitution.md` §reserved)

## Rationale

The 2026-08-12 session repeatedly hit the pattern: arbi authors an exact command, James
pastes it unreviewed. The keystroke's real security value is not James's review — it is
that a prompt-injected session cannot fire I5/I6 actions by itself. That value is
preserved by relaxing only *named, verified-safe shapes* while (a) standing up the
server-side backstop (branch protection) that every guard header already cites as the
prerequisite, and (b) keeping merge, un-draft, production dispatches, secrets, and
authority-file writes exactly as reserved as before.

Deliberate asymmetry, kept intact: the in-CI harness (claude-execute) still may NOT
dispatch `backup.yml` — `tests/test_claude_execute_harness.py:27` pins this. These
carve-outs apply to the **local attended session's** guards only.

## Artifact 1 — GitHub branch protection on `main` (James's GitHub action)

`scratchpad/branch-protection.json`, applied with:

```bash
gh api -X PUT repos/Jp8617465-sys/asxos/branches/main/protection \
  --input <path-to>/branch-protection.json
```

Settings: require the `full-check` status check; require a PR with 1 approving review and
Code Owner review (activates `.github/CODEOWNERS` as the memory-poisoning firewall for
agent-authored PRs); block force pushes and deletions; `enforce_admins: false` so James
(admin) is never deadlocked — the protection binds tokens and agents, not the governor.
This is the named prerequisite for any future allow-emitting hook and the real backstop
for every guard's admitted regex gaps (executor-arbitrary-code path).

**Status: applied 2026-08-12, then CORRECTED the same session.** The first apply set
`required_approving_review_count: 1` + `require_code_owner_reviews: true`. Verification
against the live repo showed that was both redundant and harmful: two rulesets
(`asxos-main` id 19077432 and `main` id 18221894) were **already active** and already
enforced PR-required, `full-check`, deletion-blocked and non-fast-forward — so the only
net-new constraint was an approval requirement that, on a solo repo where GitHub forbids
self-approval, turns **every** merge into an `enforce_admins:false` admin bypass. That is
weaker audit evidence than the 0-approval state, for zero added enforcement. Re-applied
with `required_approving_review_count: 0` and `require_code_owner_reviews: false`;
`full-check`, force-push block and deletion block retained. Re-verify before any doc or
hook cites this: `gh api repos/Jp8617465-sys/asxos/branches/main/protection`.

**Consequence for the CODEOWNERS firewall:** with Code Owner review no longer *required*,
`.github/CODEOWNERS` is advisory again — it requests James's review but does not block a
merge without it. The governance docs that describe CODEOWNERS as the mechanical
memory-poisoning firewall (`arbi-promotion-gate.md`, `arbi-dream-policy.md`) therefore
still overstate it. Closing that properly needs a review identity that is not the PR
author — a second account or a GitHub App — which is a governor decision, not a settings
tweak. Recorded here rather than silently left to a future reader.

Two facts this artifact should not omit:

- **It is a re-configuration, not a first configuration.** A ruleset with the same shape but
  **0 required approvals** ("solo-repo-safe") went live 2026-07-17
  (`docs/product/session-handoff-2026-07-17.md:16`). Several docs still assert branch
  protection is unconfigured (list in the reconciliation section below) — those were already
  stale before this artifact and are now doubly so.
- **`required_approving_review_count: 1` on a solo repo means an admin bypass on every
  merge.** GitHub forbids a PR author from approving their own PR, and James is the only
  human. With `enforce_admins: false` he can still merge — but the audit trail then reads
  "admin override" rather than "review satisfied," which is weaker evidence than the
  2026-07-17 `0`-approval ruleset produced. If the intent is a mechanical grader≠producer
  gate, the approval must come from an identity that is not the PR author; if the intent is
  just "nothing lands without CI + a PR," `0` is the honest setting. James's call — but the
  two settings are not interchangeable and this doc should not imply they are.

## Artifact 2 — push-guard dispatch allowlist extension (James applies)

Replacement `.claude/hooks/push-guard.sh` (built from the live post-PR-#92 version; diff
is exactly: header note + a seven-line comment + `backup\.yml|claude-execute\.yml` added
to the existing per-segment allowlist regex + the deny message updated). Behavioral
matrix verified against the replacement hook:

| Command | Result |
|---|---|
| `gh workflow run backup.yml -f restore_drill=true --ref main` | pass → normal prompt |
| `gh workflow run claude-execute.yml -f prompt=...` | pass → normal prompt |
| `gh workflow run full-check.yml` | pass (pre-existing) |
| `gh workflow run daily-brief.yml` / `us-positions.yml` | DENY |
| safe dispatch `&&` unsafe dispatch (compound smuggling) | DENY |
| `gh release create` / `gh pr merge` / `gh pr ready` | DENY (unchanged) |

Why these two are safe: `backup.yml` only ever *reads* the production DB (`pg_dump`) and,
on the opt-in `restore_drill=true` path, replays that dump into a disposable CI container —
no production write exists on either path, so its worst case is a wasted run;
`claude-execute.yml` is the governed harness whose workflow definition carries its own tool
ceiling, and the action's anti-tamper check refuses to execute any non-`main` modification
of it.

**Precision the one-liner above loses — state it, don't let a future reader rediscover it.**
`backup.yml` *is* secret-bearing: it mounts `DATABASE_URL`, `BACKUP_GITHUB_TOKEN` and
`BACKUP_REPO` (`.github/workflows/backup.yml:41-43`), and its default path
(`restore_drill=false`) is not read-only at the boundary — `scripts/backup_irreplaceable.sh`
commits a dump of the irreplaceable tables into the external `$BACKUP_REPO`. The disposable
container belongs to the opt-in `restore_drill` job only. The carve-out is still defensible
(the external write is append-only backup data, into a repo whose whole purpose is receiving
it, with a project-ref identity assertion at `backup.yml:78-86` refusing an unverified
source), but it is a **narrowing exception to a standing rule**, not an instance of it:

| Doc | Says | After this carve-out |
|---|---|---|
| `docs/product/arbi-permission-model.md:109-111` | dispatch limited to validation-only workflows; "production or secret-bearing workflows stay approval-gated" | true of the **in-CI harness**; no longer true of the **local attended session** |
| `docs/product/arbi-harness.md:152-154` | "running production/secret-bearing jobs remains approval-gated" | same split |

Both are authority-guarded, so this doc records the delta and James applies it. The
governing distinction to write into them: *attended-local* vs *unattended-in-CI*, not
*validation* vs *production*.

## Artifact 3 — settings allow-rules (James applies)

Replacement `.claude/settings.json` (diff is exactly three added allow rules):

```
"Bash(gh workflow run backup.yml:*)",
"Bash(gh workflow run claude-execute.yml:*)",
"Bash(gh run rerun:*)",
```

These stop the permission layer re-prompting for the same shapes the hook now permits.
`gh run rerun` is read-triggering only (re-executes an existing, already-authorized run).

## Stale claims these artifacts create (James applies; all authority-guarded)

Every line below asserts branch protection is absent. All are wrong as of 2026-07-17 and
doubly wrong after Artifact 1. Listed so the correction is one pass, not five discoveries:

| File:line | Stale text | Correction |
|---|---|---|
| `.claude/hooks/push-guard.sh:38` | "confirmed NOT configured as of 2026-07-11" | configured 2026-07-17 (ruleset), re-applied 2026-08-12 |
| `docs/product/arbi-permission-model.md:288-292` | friction reduction "gated on ... branch protection ... (still NOT done, confirmed 2026-07-11)" | precondition met; the carve-outs are the first draw-down on it |
| `docs/product/arbi-permission-model.md:307-308` | executor-arbitrary-code path's "real backstop is GitHub branch protection" (implied absent) | backstop now exists — keep the residual, drop the "unconfigured" framing |
| `docs/product/risk-register.md:24` (R5) | "still not configured" + "PLAN-GATED ... James declined the upgrade" + "CODEOWNERS is **inert**" | GitHub Pro active since 2026-07-17; CODEOWNERS is live once Code Owner review is required |
| `docs/product/arbi-full-auto-activation-2026-07-15.md:61-72` | "❌ BLOCKED on the GitHub plan ... precondition consciously waived" | unblocked; the waiver is no longer needed |
| `docs/product/arbi-operating-backlog.md:87` (R-A2) | "Branch protection on `main` is **NOT configured**" | close R-A2 |
| `docs/product/arbi-autonomy-loop.md:44-46` | layer 2 backstop marked "*Config step for James/backend-architect*" | step done — mark MET, keep the layer |
| `docs/product/arbi-autonomy-loop.md:67` | activation precondition 2, "Branch protection configured on `main`" | ✅ MET 2026-08-12; preconditions 3 (RO DB role), 4 (track record), 5 (James's enable) still open |
| `docs/product/guilfoyle-mission-control.md:82-83` | standing operation "gated on branch protection for `main`, the agent read-only DB role (R2), and the scorecard track record" | first of the three is now satisfied; the gate still holds on the other two |
| `docs/product/memory/dream-candidates/archive/2026-07-15-dream.md:272` | "still not configured" | archived artifact — leave as-is, it is a dated record |

Non-guarded and already corrected in this pass: `docs/product/runbooks/claude-execute.md`
("if configured ... do not assume they are present" → configured 2026-08-12, with the
verify command).

## What does NOT change

Merge and `gh pr ready` remain James's (the permission model's James-instructed attended
merge execution path already covers "James says merge #N" without a paste). Production
dispatches (`daily-brief`, `us-positions`, anything secret-bearing), secrets, migrations,
authority files, Render/deploy surfaces: all exactly as before. Standing/unattended
autonomy is untouched — it stays behind the promotion gate's track-record precondition.
