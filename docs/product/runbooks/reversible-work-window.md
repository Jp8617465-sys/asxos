# Runbook — launching a reversible work window

**Status:** current
**Scope:** operator steps for James to launch, bound, and audit a long working window
**Last verified:** 2026-09-14 (rewritten alongside the skill; the 2026-07-14 version
described the I0–I6 ladder, the four-guard fence and a draft-PR stopping point, none of
which exist after the chief-of-staff rollout #254)
**Owner:** James (operator); the recipes are `docs/product/arbi-goal-recipes.md`
**Superseded by:** N/A

## What changed, and why this file was wrong

The 2026-07-14 version told you the window "merged nothing" and that your job afterwards was
to pick a merge order. Under `AGENTS.md` that is no longer true, and reading it as true would
have you waiting for PRs that arbi has already landed. `AGENTS.md` §8 gives arbi the whole
sequence — branch, `make check`, **ready** PR, wait for required checks, squash-merge — and
§0 says there is "no draft-PR ceiling". Your review is after the fact, on a reversible
change (§7).

The four guard hooks this runbook leaned on (`authority-guard.sh`, `push-guard.sh`,
`pr-draft-guard.sh`, `unattended-guard.sh`) and the `ARBI_UNATTENDED` variable are gone.
So is "PR-2 (Permission Friction Pack)", which step 4 waited on.

## Before launching

1. **Main is current** — merge or park anything the window would collide with; the window
   branches off `main` (`arbi-goal-recipes.md` rule: fresh branches per mission).
2. **Pick the recipe** — R1 (12-hour, 3–5 PRs) or R2 (8-hour, ≤3 PRs) from
   `arbi-goal-recipes.md`. Do not free-hand the boundaries; the recipe *is* the envelope.
3. **Know what will still stop** — the `reversible-work-window` skill pre-allows the §8
   landing loop. What it does not reach: `AGENTS.md` §2 (capital, the personal-use
   invariant and `north-star.md`, spend over the A$50/day cap), `.claude/` (arbi's own
   permissions — drafted, never self-landed), and applying a migration.
4. **Accept the documented residual (red-team 2026-07-14, still open):** the skill's
   `Edit`/`Write` are unscoped and its pre-allowed test runners execute whatever the tree
   contains, so an edited `conftest.py` or `Makefile` is an arbitrary-code path that does
   not pass through the Bash allowlist. The mitigation is no longer a hook — it is the
   `main` ruleset (PR required, `full-check` on the current head, no force push, empty
   bypass list) plus `full-check` itself. Nothing reaches `main` except through a PR with
   green required checks.
5. **Optional (teams):** if the window may run an `/arbi-team` mission, set the **local/user**
   env `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` (see `runbooks/agent-team-mission.md`).
   Never commit this to repo config.

## Launch

6. Paste the recipe's `/goal` block verbatim (edits to its hard floor or discipline block are
   boundary changes — make them in the recipe doc via PR first, not ad-hoc in the prompt).

## During (what the window may and may not do)

- **May:** arbi wake → red-team → Guilfoyle-led missions → builders on `claude/**` branches →
  ready PRs → squash-merge on green. Reversible calls are made without asking and recorded as
  `DECISION / TAKING / REVERSAL` rows (L-cand-2,
  `memory/working/2026-07-12-scope-reversible-without-asking.md`; `AGENTS.md` §7).
- **May not (hard floor):** capital or broker anything · a change to the personal-use
  invariant or `north-star.md` · spend over the cap · a `.claude/` change landed rather than
  drafted · applying a migration from inside an unmonitored window · leaving a finished
  artifact branch-only.
- **Binding conduct:** the **PR transaction discipline** block (L-cand-4/5) for every branch
  touch, and every PR classed in its body (`AGENTS.md` §6).

## After — the audit trail (10 minutes)

7. Read the **digest** (`AGENTS.md` §12): merged · applied · decided · yours · risks ·
   incidents. It is one screen and it is the report.
8. Check `docs/product/decision-log.md` for the `DECISION / TAKING / REVERSAL` rows and the
   ONE THING → outcome pair.
9. Spot-check one merged PR: diff ⊆ its stated scope, required checks green on the head that
   merged, class and reversal cost stated.
10. **Reverse anything you disagree with** — that is the review, and it is why every class is
    written down. A Green PR is one `git revert` away. An Amber one names its reversal cost
    in the body. A migration does not roll back (§3): it is undone only by a forward
    migration, so those are the rows to read first.
