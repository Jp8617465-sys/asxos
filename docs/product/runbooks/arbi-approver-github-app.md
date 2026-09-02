# Runbook — GitHub App reviewer (`asxos-arbi-approver`)

**Status:** current · awaiting James's execution
**Scope:** one GitHub App James creates in the browser. An agent session
**must not create the App, mint the private key, or write Actions secrets.**
**Last verified:** 2026-08-24 (Amendment G)
**Owner:** James
**Supersedes as the chosen identity path:**
`docs/product/runbooks/second-github-identity.md` (second *account* — kept as
the rejected alternative, not deleted)

## Why an App and not a second account

Amendment G ruling 2 (James, 2026-08-24): short-lived installation tokens via
`actions/create-github-app-token`, scoped to this one repo, revocable, no seat,
no second 2FA, no long-lived PAT in secrets. A second human account needs all
of that and is a broader credential. The App is more setup once and stricter
least-privilege after.

`GITHUB_TOKEN` cannot submit an approving review (blocked to stop workflows
self-approving). That is why a separate identity exists at all.

## What this buys — and what it does not

**Buys:** a non-author identity that can `APPROVE`, so
`required_approving_review_count: 1` can be set without the 2026-08-12
self-approval deadlock.

**Does not buy:** a second pair of eyes. James still reads the diff and keeps the merge click
(Amendment G ruling 3 — no auto-merge).

**Does not buy:** mechanical CODEOWNERS on James-authored PRs. GitHub forbids
the PR author from being the CODEOWNER reviewer. The App is not
`@Jp8617465-sys`. PRs James authors that touch CODEOWNERS paths will still
deadlock `require_code_owner_reviews` after the App exists. Decide that
consciously before flipping the count: either leave `require_code_owner_reviews`
off (count=1 from the App is the gate) or accept an admin bypass / a different
*author* on authority-file PRs.

## Least privilege (load-bearing)

| Permission | Grant? | Why |
|---|---|---|
| `pull-requests: write` | yes | submit an approving review |
| `contents: write` | **no** | would let the App push and merge; ruling 3 forbids auto-merge |
| `administration` | **no** | must not bypass rulesets |
| `workflows` | **no** | must not edit Actions |

Install **only** on `Jp8617465-sys/asxos`. Do not install on every repo the
account owns.

## Steps (browser + secrets — James only)

1. GitHub → Settings → Developer settings → GitHub Apps → New.
   Name: `asxos-arbi-approver`. Homepage can be the repo URL. Webhook:
   **inactive** (no inbound events required for a review-submitting App).
2. Repository permissions: **Pull requests = Read and write.** Everything
   else No access. Save.
3. Install the App on **this repo only**.
4. Generate a private key. Store it as repo Actions secret
   `ARBI_APPROVER_APP_PRIVATE_KEY`. Store the App ID as
   `ARBI_APPROVER_APP_ID`. Never commit either. Never paste either into a
   prompt.
5. Do **not** yet set `required_approving_review_count: 1` or
   `enforce_admins: true`. Those flips happen only after the throwaway-branch
   test below is green.

A later attended mission may draft the workflow that mints a token with
`actions/create-github-app-token` (pin the action by full commit SHA) and
submits `event=APPROVE` **only when**:

- the PR is **not draft**
- required checks including `full-check` are **success** (not pending, not
  skipped-as-green)
- the PR does not enable auto-merge (`enable_pr_auto_merge` stays denied)
- the token used is the App installation token, never `GITHUB_TOKEN`

That workflow is **not** in this runbook. Drafting `.github/workflows/**` is a
separate, authority-path PR. Do not treat this file as license to add it.

## Throwaway-branch test (do all four before trusting it)

Use a disposable `cursor/app-review-probe-*` branch and a draft-then-ready PR
that touches **no** CODEOWNERS path.

- The App can `APPROVE` that PR.
- `GITHUB_TOKEN` still cannot `APPROVE` (control).
- Merge still requires James's merge click. Auto-merge remains disabled.
- `push-guard.sh` / `pr-draft-guard.sh` still deny auto-merge surfaces from
  agent sessions.

Only then consider `required_approving_review_count: 1`. Only after that
count is live and not deadlocking, consider `enforce_admins: true`.

## Failure modes to refuse

- `pull_request_target` with an agent that checks out fork code (Comment and
  Control / CVSS 9.4 class). This repo's review agent stays
  `pull-requests: read` and secret-free; the App job must not widen that.
- Approving drafts.
- Approving while `full-check` is red or pending. `migration-drift` red on
  `main` was the 2026-08-24 example of why "green means mergeable" is not yet
  a standing claim — even after #176 landed the 0047 *file*, the next drift
  run is the observation, not this runbook.
- Adding `contents: write` "so it can merge later." Ruling 3 would have to
  be reversed first, in writing, with a CFR/MTTR baseline that does not
  exist today.

## Verify-before-row-close

Do not mark the CODEOWNERS-advisory caveat in `CLAUDE.md` closed until
the throwaway-branch test has passed and the count flip is observed, not
promised. This App path does **not** close risk-register R2 (agent DB
role) or R5 (prompt-only enforcement) — those are a different problem.
The App also does not make CODEOWNERS mechanical on James-authored
authority-file PRs.
