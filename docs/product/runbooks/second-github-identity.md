# Runbook — second GitHub identity for agent-authored PRs

> **SUPERSEDED as the chosen path, 2026-08-24 (Amendment G ruling 2).** James
> picked a GitHub App over a second account. The standing procedure is
> `docs/product/runbooks/arbi-approver-github-app.md`. This file is kept as
> the rejected alternative (author-side identity) so the CODEOWNERS-on-
> James-authored-PRs caveat in that runbook has somewhere to point. Do not
> create `asxos-agent`. Do not mint a second-account PAT.

**Status:** superseded as chosen path · retained as rejected alternative
**Why (still true):** the review gate is structurally inert with one identity. `Jp8617465-sys` is both the author of every agent PR and the sole CODEOWNER; GitHub forbids self-approval, so the only reachable states are gate-everything (deadlock) or gate-nothing (today — PR #137 merged touching `CLAUDE.md` with zero review). Demonstrated, not theoretical. The App path solves the *approver* side of that deadlock, not the *author* side.
**What this buys:** author/approver **separation** — required reviews become mechanically enforceable. It does **not** buy a second pair of eyes; James still reads every diff himself.
**Source spec:** PR #140's appendix ("the least-technical route"); this runbook is the standing copy so the procedure survives that PR's merge-or-close.

## The five steps (~20 minutes, one-time)

1. **Create a second free GitHub account** (e.g. `asxos-agent`), with its own email. This is the *author* identity for agent work; `Jp8617465-sys` remains governor, CODEOWNER, and merger.
2. **Invite it as a repo collaborator** with **Write** (not Admin — it must never be able to bypass branch protection): repo → Settings → Collaborators → invite `asxos-agent`; accept from the new account.
3. **Mint a fine-grained PAT on `asxos-agent`** scoped to this one repo: Contents read/write + Pull requests read/write, nothing else, with an expiry. Install it as the credential in whichever agent runtimes author PRs (Claude Code remote session git credentials / `claude-execute.yml`'s token secret). From then on, agent branches and PRs are authored by `asxos-agent`.
4. **Set `required_approving_review_count: 1`** on `main` (`require_code_owner_reviews` is already **on but inert** — per CLAUDE.md, verified 2026-08-18 — so only the count needs changing; it becomes load-bearing the moment the count is 1). This deadlocked before because author == owner; with agent PRs authored by `asxos-agent`, James can now be requested and approve.
5. **Set `enforce_admins: true`** — closes the admin-token bypass PR #140 also flagged. After this, even the governor's own account goes through the PR gate.

## Verify (do all three before trusting it)

- An `asxos-agent`-authored test PR **cannot merge** without James's approval (the merge button stays blocked).
- A `Jp8617465-sys`-authored PR touching an owned path (e.g. `CLAUDE.md`) now **also requires a review** — which means James's own direct PRs need the agent account (or `--admin` is gone entirely, per `enforce_admins`); decide the workflow for his own edits consciously rather than discovering it mid-change.
- The R13/R12 hooks and `push-guard.sh` still fire in agent sessions under the new credential (they key on commands, not identity — but verify, don't assume).

## Known consequences to accept in advance

- **James's own solo PRs get slower**: with count=1 + enforce_admins, he can't one-click-merge his own work either. The escape valves are (a) authoring his own changes from `asxos-agent` and approving from the main account, or (b) accepting the friction. Pick one deliberately.
- The scorecard/promotion-gate "grader ≠ producer" line gets mechanically real for merges — a long-standing assumption finally enforced.
- This closes risk-register **R2/R5** and the CODEOWNERS-advisory caveat carried in `CLAUDE.md`'s slash-commands section and `roadmap-state.md` since 2026-07-17; update those rows when step 5 is verified, not before.
