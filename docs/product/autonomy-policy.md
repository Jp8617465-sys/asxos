# Autonomy policy — enforcement map, activation, rationale

Companion to `AGENTS.md`. Owner-facing. Agents do not load this per session.
Save as `docs/product/autonomy-policy.md`.

> **Everything below is target state.** As verified on 2026-09-08, live GitHub
> has `main` as the only branch of interest, no `AUTONOMY` variable, no
> `risk-classify`, `breaker` or `restore` workflows, and a CODEOWNERS file that
> does not yet cover `AGENTS.md`, `.github/**` or the protected paths. The
> pre-activation ceiling in `AGENTS.md` §0 binds until §3 passes.

---

## 1. Why the model looks like this

Broad authority is granted because a small set of prohibitions are made
physically true, and human attention is spent where a non-engineer can judge:
acceptance criteria before work, a digest after it lands, and one approval at
the moment of real-world effect. Prose gates that ask an agent to self-report
compliance were removed; they were not controls.

**Gate at merge, not at a promotion step.** Production is workflows running
from `main`, so merge is deploy. A `release` branch with a held promotion was
rejected because a held Amber commit would also block every later Green
commit, revert and hotfix, so a breaker trip during a hold could not be fixed
without James. Cherry-picking Green past Amber was rejected because it
abandons linear history, which is what makes `git revert` trustworthy for a
solo owner. `main` stays the single source of truth and rollback stays
unattended.

**Conditional approval on GitHub.** Rulesets cannot require approvals only
for some PRs. A global approval requirement would also block unattended Green
PRs, so the ruleset does not impose one. The external `risk-classify` required
check does: it passes Green without review and passes Amber only when an
APPROVED review from James has `commit_id == current head SHA`. It re-runs on
`pull_request` `synchronize` and every `pull_request_review` event.

The authority check is not implemented by mutable product-branch code. A thin
base-owned `pull_request_target` product caller is pinned to an immutable
`asxos-control` verifier commit. It never checks out or executes the PR head;
the pinned workflow's observation job uses only a read-only `GITHUB_TOKEN` to
query the PR head, policy bytes, CODEOWNERS, reviews and changed paths through
provider APIs. A following verifier process runs network-disabled with only the
content-addressed observation mounted and no credential environment. A separate
check-publisher job references the Verifier App private key only through a
`risk-classify-publisher` product environment restricted to protected `main`,
mints an exact checks-only token, and posts the
required check against the provider-observed PR head SHA. Its ordinary
`GITHUB_TOKEN` has no permissions. No `secrets: inherit` is permitted. This
placement is explicit because cross-repository reusable workflows execute in
the caller context and do not inherit secrets automatically. Activation tests
prove that ordinary event or merge-ref SHAs cannot satisfy the required check.

**Required-check source bootstrap is not an authority bypass.** While
`AUTONOMY=ATTENDED`, the real classifier correctly cannot emit a passing
decision, yet GitHub must observe one App-owned green check before its source can
be selected in the ruleset. A temporary owner-dispatched bootstrap workflow may
therefore post `risk-classify` exactly once to a dedicated disposable commit
that is neither `main` nor the head of any open PR. It verifies those exclusions
through the API, records the check and target digests, and is deleted immediately
after source binding. The bootstrap path cannot target a PR and is not present
at activation. A failure check is the only outcome on ambiguity.

**Migration merge and application are separate.** A migration-file PR is Amber,
but merging the definition is git-revertible and does not apply it in this repo.
Application is the irreversible I5 action and remains owner-only behind a role
that the agent identity cannot assume. SQL keyword scanning is retained as a hint
only.

**Investment output is banded, not blanket Red.** A blanket "could read as
advice" rule would make the product's core work permanently non-delegable.
Impersonal research and recommendations are Amber with an explicit-yes AC.
Personalised recommendations conditioned on a user's objectives, circumstances
or holdings are Red. Orders are permanently Red. The classifier cannot see
personalisation, so that call is James's at AC time, informed by the agent's
declared estimate.

**Protected paths cover what exists, not only what is planned.** Email logic
already lives in `asxos/brief/email.py` and `asxos/jobs/utils/fallback_email.py`;
investment output already lives across `asxos/brief/` and
`asxos/domain/decision_engine/`. The classifier protects those today.
Reserved paths are destinations for future code and for one-time relocation.

**Autonomy state is written only by workflows.** Agents dispatch `restore`
and provide evidence; the workflow verifies and flips. The agent identity has
no `variables: write` permission.

**AC approval is content-addressed.** The control plane canonicalises and
hashes the latest frozen AC. James approves with
`APPROVE-AC sha256:<digest>`. A verifier accepts only James's comment matching
that exact ledger-recorded digest, so an approval cannot survive an AC change.

---

## 2. Where each rule will live

Client-side controls (`.claude/settings.json`, PreToolUse hooks, Cursor rules)
are advisory in the limit because an agent with write access can edit them.
Server-side controls are real. Every irreversible external consequence in
`AGENTS.md` §8 has a server-side row; local secret-file access cannot be made a
GitHub server invariant, so the design also withholds secrets from agent
identities and retains fail-closed client guards.

| Rule | Mechanism | Location | Exists today |
|---|---|---|---|
| No direct or force push to `main` | Ruleset | Repository or org ruleset | **Yes** — active ruleset `asxos-main` (19077432) |
| No `--admin`, no bypass | Agent identity has no repository-admin role; ruleset has an empty bypass list | GitHub App permissions + repository or org ruleset | **Partial** — both active rulesets have empty bypass lists; agent identity still needs proof |
| Required checks green on current head | Ruleset required checks | Repository or org ruleset | **Partial** — strict `full-check` exists; `risk-classify` does not |
| Green has no global approval gate | Ruleset has no required approving-review count; conditional approval is enforced only by `risk-classify` | Repository or org ruleset | **Yes** — approval count 0 and last-push approval false |
| Tier assignment; unlabelled cannot merge | Base-owned `pull_request_target` caller pinned by immutable SHA to the `asxos-control` verifier; it never checks out or runs PR code; path allowlist defaults to Amber and fails closed | Product caller + `asxos-control` | **No** |
| Check publication is separated from verification | Read-only observer emits content-addressed input; network-disabled verifier receives no credential environment; a credential-isolated publisher job uses the product `risk-classify-publisher` environment to mint the Verifier App's exact checks-only token; ordinary `GITHUB_TOKEN` permissions are empty | Product environment + `asxos-control` observer/verifier/check-publisher boundary | **No** |
| Amber needs James's approval on current head | Verifier evaluates `pull_request` (`opened`, `synchronize`, `reopened`) and `pull_request_review` evidence; passes only when James's APPROVED review has `commit_id == head SHA` | `asxos-control` verifier | **No** |
| Existing sensitive code protected | Classifier path list includes `asxos/brief/**`, `asxos/domain/decision_engine/**`, `asxos/brief/email.py`, `asxos/jobs/utils/fallback_email.py`, `migrations/**` | same | **No** |
| Red paths cannot merge | Classifier fails outright on `asxos/insights/personal/**`, `asxos/capital/**` | same | **No** |
| Relocation PRs | Label `relocation`; classifier requires James approval and a diff that is a pure move (`git diff --stat -M100%`) | same | **No** |
| Spend ask | `workflow_dispatch` jobs under `production` environment with James as required reviewer | Repo environments | **No** |
| Policy self-amendment | CODEOWNERS routes to James; `risk-classify` mechanically requires James's current-head approval for `AGENTS.md`, `CLAUDE.md`, `docs/product/**`, `.github/**`, `.claude/**`, `asxos/capital/**`, `asxos/insights/**`, `asxos/brief/**`, `asxos/domain/decision_engine/**`, `migrations/**` | `.github/CODEOWNERS` + `asxos-control` verifier | **No** (file exists, coverage does not) |
| Secret values | Actions secret scoping, push protection, no plaintext in repo | GitHub + Supabase | Verify |
| Capital orders | Broker credentials never issued to any agent identity or agent-reachable workflow | Broker + secret store | Verify |
| Destructive prod SQL | Agent-reachable Supabase role has no DDL and no unbounded write on user tables; migration role only in the migrate workflow's secrets | Supabase roles | **Partial** — `db-write-guard.sh` (always-on) denies a write/DDL-shaped query reaching the read-only connection, client-side; the role itself is unverified — the role, not the hook, is the real backstop |
| Migration application (activation item 17) | Merging a migration-bearing PR is ordinary Amber merge authority — a merged migration sits unapplied. Applying one is denied to the agent identity unconditionally | `db-write-guard.sh` (always-on, not `ARBI_UNATTENDED`-gated) | **Partial** — client-side deny exists today; no attested application workflow exists yet, so applying a migration remains manual, by James |
| `.env` reads and writes to Red paths or `.claude/**` | Deny rules + PreToolUse hooks; agent runtime receives no production secret values | `.claude/settings.json`, `.claude/hooks/`, runner credential boundary | **No** |
| Autonomy state | `AUTONOMY` repo variable; agent identity lacks `variables: write` | Repo variables + App permissions | **No** |
| Autonomy-state mutation | Dedicated State Controller App has metadata read + variables write only; only attested breaker/restore/activation workflows may assume it | `asxos-control` + GitHub App permissions | **No** |
| Breaker trips | `breaker` workflow flips to `ATTENDED`, opens incident issue, records event in ledger | `.github/workflows/breaker.yml` | **No** |
| Restore | `restore` workflow (`workflow_dispatch`), runs under its own identity, verifies fix merged, checks green, 60 min clean, incident updated, restore count < 2 in 7 days, then flips to `STANDING`; refuses otherwise | `.github/workflows/restore.yml` | **No** |
| Breaker thresholds | Checked-in registry names each monitored workflow, metric, threshold, evaluation window and evidence query; required missing/stale telemetry trips | `asxos-control` breaker registry | **No** |
| AC freeze and explicit-yes | Ledger records canonical AC + SHA-256 digest; explicit-yes passes only for James's `APPROVE-AC sha256:<digest>` comment matching the latest frozen digest | Control ledger + verifier | **No** |

Deny rules and hooks are enforced by the harness, not the model, and apply
even in bypass-permissions modes. They are a good second layer, not the first.

---

## 3. Activation checklist

Keep `AUTONOMY` absent or `ATTENDED`; `AGENTS.md` §0 remains the ceiling until
every item passes. Do 1 to 5 first; nothing else is load-bearing without them.

1. **Distinct agent identity.** A GitHub App (preferred) or machine user for
   all agent pushes and PRs, with no repository-admin or `variables: write`
   permission.
2. **Ruleset on `main`.** PR required, squash-only merge, required checks on
   the latest head, linear history, no force push and empty bypass list. Do not
   require an approving review or most-recent-push approval globally; either
   would disable Green autonomy. Verify with a disposable branch that direct
   push, force push and an admin-style bypass all fail.
3. **`risk-classify` verifier and check publisher.** Implement the authoritative
   verifier in `asxos-control`. A read-only observation job emits a canonical,
   content-addressed input; the verifier runs network-disabled with no credential
   environment. Implement the separate credential-isolated check-publisher path
   using the Verifier App.
   The distinct branch Publisher App has no checks permission and is outside
   this merge-gate path. Use a base-owned `pull_request_target` caller pinned to
   the verifier's immutable commit SHA; never check out or execute PR content.
   The publisher job alone references the Verifier App key from the
   `risk-classify-publisher` product environment, whose deployment branch policy
   admits protected `main` only; it mints a checks-only token and has an empty
   ordinary `GITHUB_TOKEN`. Do not inherit secrets into the reusable workflow.
   Green allowlist; protected existing and reserved paths; Red paths fail
   outright; same-repository head ID; Amber requires James's APPROVED review
   with `commit_id == current head SHA`; relocation handling; content-addressed
   AC freeze and explicit-yes checks. Before binding, run the temporary
   owner-only bootstrap once against a dedicated non-main, non-PR commit, record
   its evidence, bind the exact check name and App, then delete the bootstrap
   workflow. Tests prove a bootstrap cannot target `main` or any PR head, and
   stale heads, fork heads, merge refs, stale AC approvals, mutable verifier
   refs, skipped/neutral conclusions and missing results fail closed.
4. **CODEOWNERS** per the table above, used for routing. The verifier remains
   the conditional approval enforcement point. Add a drift test that fails if
   its path list and CODEOWNERS disagree.
5. **`production` environment** with James as required reviewer, attached to
   every spend `workflow_dispatch` job.
6. **Database roles.** Confirm per the table above.
7. **Deny rules and hook.** Per the table above. Deny writes to `.claude/**`
   from within the harness. Keep `unattended-guard.sh`'s merge deny until the
   activation path can verify ledger attestation independently of mutable product
   code or a repository variable; `AUTONOMY=STANDING` alone is not a key.
8. **State Controller.** Create the dedicated metadata-read/variables-write App
   and bind it only to the attested activation, breaker and restore workflows.
   The verifier, publisher and ordinary agent identities cannot assume it.
9. **`AUTONOMY` variable and attestation.** Create it as `ATTENDED`. Record an
   activation entry that binds the exact `AGENTS.md` digest, verifier commit,
   publisher identity and checklist evidence. A mismatched record fails closed.
10. **Breaker registry and workflow.** Check in a registry naming each monitored
   workflow, metric, threshold, evaluation window and evidence query. Missing,
   malformed or stale required telemetry trips. The workflow monitors `main`,
   rollbacks and the registry, flips to `ATTENDED`, opens the incident issue,
   and records the event.
11. **`restore` workflow.** Verifies evidence and count, flips to `STANDING`
    or refuses. Runs under a workflow identity that agents cannot assume.
12. **Digest workflow** at 07:00 AEST.
13. **Harness alignment.** Import `AGENTS.md` from `CLAUDE.md` using the
    documented `@AGENTS.md` syntax; remove conflicting old I5/I6 prose. Claude's
    PR guards resolve the exact product repository from `origin`, read its live
    `AUTONOMY` repository variable through `gh`, and fail closed on a missing
    CLI, wrong repository, lookup failure, malformed state, or any value other
    than `STANDING`. Only then may PR creation, readying and server-gated squash
    merge fall through. Direct/force push to `main`, non-squash, auto/admin
    merge, direct mutation of `AUTONOMY`, and every §8 stop remain denied. This
    remote state read is feedback, not attestation: the external required check
    and ruleset remain the enforcement boundary. Test both states and confirm
    the commands in `AGENTS.md` §3 against the Makefile. This policy PR relaxes
    the always-on Claude push/PR guards only; `ARBI_UNATTENDED=1` remains
    mechanically draft-only. Standing scheduled merge therefore remains an
    open part of this activation item and needs a separate explicit ruling.
14. **Relocations.** Decide explicitly before activation: either land one
    relocation PR moving email logic to `asxos/comms/`, or record a deferral and
    prove the existing email paths are protected. Investment-output code stays
    where it is; protect it in place.
15. **Revert drill.** Ship a harmless, observable Green canary, confirm its
    production revision, revert it through a second Green PR, and confirm the
    prior revision is restored unattended with no data mutation or manual
    deployment step. Time it. If it does not work end to end, stay `ATTENDED`.
16. **Restore drill.** In an isolated test repository or workflow dry-run mode,
    trip an operational breaker, exercise the evidence sequence, and prove a
    third restore inside seven days is refused. Do not consume the live restore
    allowance merely to test it.
17. **Migration authority split.** The Amber gate permits a migration-file PR to
    merge, but the ordinary agent, verifier and publisher identities cannot call
    `apply_migration` or assume the production migration role. Prove the denial
    with the ordinary agent identity. Migration `0042` remains reserved.
18. **Activate.** Owner approves one activation dispatch while `ATTENDED`.
    The workflow re-verifies items 1–17, matches the policy/ledger/verifier
    digests and uses the State Controller to flip `AUTONOMY` to `STANDING`.
    A partial checklist or digest mismatch refuses activation.

---

## 4. Known limits and next revisions

- **Spend is always-ask.** After a month of digests, set a daily A$ ceiling
  under which spend becomes ordinary Amber.
- **Migration-file PRs are Amber indefinitely.** Application is not part of that
  grant and remains owner-only. Reconsider application only after a tested
  forward-recovery model and mechanically scoped production role exist.
- **Personalisation is a human call.** The classifier cannot distinguish
  impersonal from personalised output. The explicit-yes AC gate is the
  control; the agent's declared estimate is input, not decision.
- **Green stacked on Amber waits.** By design. The rule is not to stack.
- **Promotion ladder needs volume.** Some Amber classes will never reach the
  threshold at solo scale; acceptable. Revisit quarterly.
- **Subagent inheritance.** Subagents may not inherit hooks or deny rules.
  Server-side rows are what actually hold.
- **Claude Code and `AGENTS.md`.** Native reading is not shipped. Keep the
  `@AGENTS.md` import in `CLAUDE.md` and remove it when native support lands.
