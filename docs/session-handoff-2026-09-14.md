# Session handoff — 2026-09-14 (governor-directed, no `/arbi` wake)

**Status:** current
**Read priority:** read first — then `session-handoff-2026-09-10.md`, whose residue list is
still live and is carried here by reference, not re-copied.

**Session shape:** two halves, both James-directed. First, the grants question that PR #256
settled (its decision-log row is 2026-09-14 row 1). Second, a one-line FYI — "Supabase is now
Pro; make Opus the default" — that arbi turned into a planned docs PR, had red-teamed, and
dropped; then the four off-repo steps from the 09-10 handoff, closed by James with
click-by-click guidance. No `/arbi` wake, so no arbi-ranked "one thing". The close is this
PR, docs only.

Every figure below is **measured** with the command shown, or marked *inferred*.

## STOP — read this first: Model A's quarantine (rule #11) stands, untouched

Nothing this session read `signals`, `model_versions`, or any Model A artefact. `AGENTS.md`
§8 and `CLAUDE.md` rule 11 are unchanged by #256. `0042` stays reserved; `0045` stays
unapplied (verified live 2026-09-14 from James's laptop MCP: head `20260903025557`, ledger
clean back to `20260217004354`). Rule #11 is standing policy, not up for reinterpretation.

## What landed

- **#254** `481e5cd` — the chief-of-staff rollout (the 09-10 handoff's PR; merged this session).
- **#256** `ac05c4c` — *arbi can change what the system does; arbi cannot change what arbi is
  allowed to do.* Granted: merge-own-PR-on-green, `apply_migration`, workflow dispatch,
  `.github/workflows/` edits. Reserved: `.claude/**` alone. `AGENTS.md` §2/§8/§14 and
  `CLAUDE.md` amended to match.
- **`main` @ `ac05c4c`.** `make check`: ruff clean, mypy clean, **4134 passed, 1 skipped** —
  identical to 09-10, correct for a session that changed no code.

## What was dropped, and why it matters more than what landed

James's Supabase FYI became a plan: correct four "free tier" doc lines, recommend the §2 cap
drop to A$5/day, append a log row. He asked for it red-teamed on Fable. **Verdict: drop.**
Accepted in full (decision-log 09-14 row 2; lessons **L46**, **L47**):

- It chased the last chat line while the 09-10 residue's *blocking* items and a live §7
  incident sat untouched, in a session James had set to read-only.
- It relitigated a §2 number he had already declined to set, against a budget figure that
  exists only in the transcript, misreading "I don't know what it's for" as "too high".
- It would have written "I think is pro" into `CLAUDE.md:38` as fact, and a recalled PITR
  claim (a paid add-on, not included in Pro) into the runbook §8's migration floor leans on.

**Verified read-only instead** (`mcp__Supabase__get_organization` / `get_project`, 09-14):
Supabase plan **`pro`**; Postgres **17** (`17.6.1.063`). `CLAUDE.md:38` is wrong on both
words ("free tier", "Postgres 16"); `backup.yml:6` already says 17. Both go into the residue
sweep with whichever wake touches those docs — not their own PR.

## Rulings taken this session

1. **Grants split** (row 1): `.claude/**` reserved; four grants; the migration precondition is
   a *read* `backup.yml` conclusion, not a prompt — the permission layer sees commands, never
   results.
2. **Drop the Supabase-tier PR** (row 2). *Reversal:* nothing to reverse; two facts parked.
3. **Spend cap recommendation withdrawn.** The line is James's (`AGENTS.md` §2, literally:
   "James changes the number by editing this line"). What it governs, stated once for him:
   one-off variable bursts — bulk EODHD pulls, backfills, model calls at volume. Not Supabase,
   not anything recurring.

## Yours — `AGENTS.md` §2

**One item, no urgency:** the A$50/day spend-cap number. Everything else that was "yours" on
09-10 is closed:

| 09-10 item | Closed how |
|---|---|
| `~/.claude/settings.json` | Auto-mode block with `$defaults` first in both arrays, `.claude/` **excluded** from the edit grant, `model: claude-opus-5`; validated with `jq` |
| `ARBI_GITHUB_TOKEN` | Fine-grained PAT, `asxos` only, Actions / Contents / Issues / Pull requests / Workflows RW, 90-day expiry (calendar reminder is James's — **it expires silently**) |
| `SUPABASE_ACCESS_TOKEN` | **Scoped** token (new Supabase feature, on his account): Migrations RW + Database / Logs / Advisors / Project Settings R, one project. Permission→tool table: supabase.com/docs/guides/platform/personal-access-tokens |
| Writable Supabase MCP in arbi's sessions | Laptop: hosted server, OAuth, `project_ref` pinned, `--scope user`, verified. Mobile/web: via the claude.ai Supabase connector, already attached (this session used it) |
| Merge the rollout PR | #254, #256 |

The `main` ruleset step (09-10 item 2) is **not proven yet** — see first-wake item 3.

## First wake — in this order, with reasons

1. **`.github/runner/claude-user-settings.json:16`** still reads "Editing files under `.claude/`
   and `.github/workflows/`". #254 wrote it; #256 reserved `.claude/**` and missed it. So `main`
   currently hands the headless lanes the one grant the contract withholds. `.github/**` is
   arbi's; fix it before any lane runs with the new PAT. Five minutes, Green.
2. **§7 incident: `issue-snapshot.yml`** has failed on schedule daily since 09-06 (A-24). Route B
   is drafted at `docs/proposals/claude-config-patches-2026-09-06/issue-snapshot.md`. It was a
   James click on 09-06; it is arbi's now. Incidents before features — nothing else merges first.
3. **Prove the ruleset.** With the PAT, attempt a direct push to `main` on a throwaway commit;
   a refusal is the pass and changes nothing. If it is *not* refused, stop and tell James the
   same day — every grant above assumes the server-side backstop holds.
4. **First dispatch of `claude-execute.yml`** with a trivial task, then read the log for the two
   things the 09-10 handoff says no test can prove: the session actually got `auto` (not a
   silent fallback to Manual, where a headless run looks successful having merged nothing), and
   `CLAUDE_PROJECT_DIR` resolved so `secrets-guard.sh` ran rather than exiting 127. **No
   `schedule:` before both are confirmed** (A-22).
5. **`asxos/backlog.py` `DENIED_FILES`** — blocks the `backlog-roll` lane (09-10 residue 1).
6. **`.claude/skills/reversible-work-window`** — draft-only, behavioural (09-10 residue 2).
   `.claude/**`: a patch for James into the existing bundle under
   `docs/proposals/claude-config-patches-2026-09-06/`.
7. **A real `/arbi` wake**, the first since 09-06, re-ranking the 09-06 queue (all still open)
   against live state. The residue sweep — 359 citations (09-10 residue 3) plus the two
   `CLAUDE.md:38` corrections — rides with it.

## Conventions confirmed this session (not new rules; written so they are not re-derived)

- **Reads through `supabase-ro`; the writable `supabase` server only when the task needs a
  write** — the analysis-agent split, extended to the main loop by habit. James's local session
  stated the same convention unprompted.
- **Backup success is measured, not assumed:** a `backup.yml` run watched to `success` in the
  session, never a green-looking row in history. `AGENTS.md` §8 step 2 verbatim.
- **Source per claim.** L47. After one fabrication this session, three skill-sourced specifics
  and one head-sourced one went out at the same confidence; only the sourced ones survived.

## Not done, and not started, deliberately

No code, workflow, `.claude/**`, migration, DB write, dispatch, or schedule change this
session after #256. James set read-only for the second half and it held; the only write is
this close, per `/arbi-close` Step 4 ("a close that ends with an unmerged handoff has not
closed").
