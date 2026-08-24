# Session handoff — 2026-08-24

**Status:** current
**Read priority:** read first
**Supersedes:** `docs/session-handoff-2026-08-22.md` (the newest handoff on `main`).
Does **not** supersede the three unmerged 2026-08-23 close records — see STOP 3.
**Written for:** a new session with zero context.
**Close:** `/arbi-close` after the PR review train + blocked merge train.
Ledger row `close-2026-08-24-pr-review-train`. Score **4.5 provisional**.

---

## STOP — read first

**1. Rule #11 (Model A quarantine) STANDS.** Do not use Model A output —
signals, candidate scans, allocator runs, or new thesis proposals derived from
it — as a basis for real capital decisions. Removal still requires a **new**
model clearing a pre-registered decay bar AND earning `approved_for_allocation`.

Reading those tables is *not* forbidden and never was — the decay analysis that
settled the dispute was itself a read of 19,032 `signal_outcomes`. #161's
`roquery.py` docstring now states that distinction; do not "fix" it into a
blocklist.

**2. `main` is UNMOVED at `b352eef`.** This session merged nothing. Every one of
the 13 open PRs is still open and still **draft**.

**3. There are now FOUR unmerged close records competing for 2026-08-23/24.**
#164, #166 and #172 each append a 2026-08-23 `/arbi-close` to the same three
ledger files, and #166/#172 both create `docs/session-handoff-2026-08-23.md`
(146 vs 79 lines, add/add). **This handoff is dated 2026-08-24 specifically to
avoid becoming a fifth collision** — it does not contend for that filename.
Merge order for those three is James's call; #164 is the stale one (written
before #163 landed, and #172's own record says so).

**4. #175 is CI-RED and must not be merged.** Three commits added **Stage 1**
(843 lines: `bluf.py`, `deltas.py`, a detail template, tests) *after* the review
that approved Stage 0. `full-check` now fails on:

```
tests/test_brief_outcome.py::test_collect_never_reads_capital_aud_and_never_touches_a_model
AssertionError: capital_aud read: SELECT as_of, capital_aud, holdings_mv_aud, ...
                                  FROM portfolio_daily_snapshots ...
```

Stage 1's delta query reintroduces `capital_aud` into the brief's collect path —
the exact read a standing guard forbids and that `compose.py` already carries a
comment about ("the omission is the fix, not an oversight"). A real regression
against a deliberate invariant, not a flake.

**5. The agent cannot un-draft a PR.** `.claude/hooks/pr-draft-guard.sh` denies
`update_pull_request(draft:false)` with no attended exception, while the *same*
hook lets `merge_pull_request` through silently in an attended session. The
designed split is **James marks ready → agent merges**. `gh` is not installed,
so there is no Bash route, and using one would be circumvention. Do not retry
this; ask James.

---

## What this session did

**Reviewed all 13 open PRs**, one comment each, and fixed one defect.

Four findings only visible across the set, not per-PR:

- **#169 strictly contains #168** — same six commit SHAs plus one; the tip-to-tip
  diff is a single file (`nightly-check.yml`). Merge #169, **close** #168. It will
  not auto-close: after a squash merge its SHAs are not ancestors of `main`.
- **#167 carries a merge-deadlock trap.** It adds `paths-ignore` to the
  `pull_request` trigger of `full-check` — a **required** status check. A required
  check that never *starts* never reports, so any future PR touching only
  `docs/ops/github-issues-snapshot.json` sits on "Expected — waiting for status"
  forever. The `push` half is correct and is the half actually wanted.
- **#167 also pushes directly to `main`** as `github-actions[bot]`, against branch
  protection — likely a 403 on first real use, i.e. dead on arrival while looking
  configured.
- **#170 documents a workflow that only exists in #169**, so it must merge after it.

**Fixed and pushed `3d51766`** to #175: the `> 5` price-staleness threshold had
grown to three copies. `resolved_sections` now reads the canonical
`self.prices_stale` property. Behaviour-identical; 2656 passed / 1 skipped, ruff +
`ruff format` + mypy clean. (This commit is still good — it is Stage 1 on top of it
that is broken.)

**Merge train: zero merges**, blocked at step 1 per STOP 5.

**Two state traps caught by re-probing rather than trusting:**

1. Local `main` was **24 commits stale**, which made every
   `git diff main...<branch>` report ~240 files instead of the real diff. Caught
   before any of it reached James. **Always verify local `main` freshness before a
   three-dot diff.**
2. #175's head moved mid-session (`3d51766` → `17e54ae`), so the green I had
   verified earlier was no longer the current green. **Re-probe CI at merge time.**

---

## The merge train, ready to run

A copy-paste Cursor prompt for waves 1–2 was handed to James this session. Order:

**Wave 1** — `#174` → `#173` → `#171` → `#165` → `#161` last (`#161` is **behind**
by 2 commits and needs a branch update plus a fresh CI cycle first).

**Wave 2** — `#169` first → **close** `#168` → `#170` last.

Per PR: mark ready → confirm `mergeable_state == "clean"` → confirm `full-check`
**and** `targeted-ml-tests` green on the *current* head → **squash** merge (the
convention: every recent `main` commit has exactly one parent). After each merge,
re-check the rest — `#161` reporting `behind` while others report `clean` suggests
"require branches up to date" is on, which would serialise the train. No tool in
that session could read branch protection to confirm it.

---

## Pending, requiring James

| # | Item | Why it's yours |
|---|---|---|
| 1 | **Flip 8 drafts to ready** (#174 #173 #171 #165 #161 #169 #170, and #168 to close) | `pr-draft-guard.sh` — the agent cannot, by design |
| 2 | **#165 merges a widening of arbi's own Bash allow-list** (`.claude/settings.json` → four `gh issue` verbs) | Raised and ruled **merge it** on 2026-08-24; recorded because it completes a self-grant the repo normally routes through you |
| 3 | **#167's direct push to `main`** — branch-protection bypass entry, or a PR-based flow? | Neither is the agent's to choose; do not weaken protection to make it work |
| 4 | **#164 / #166 / #172** — three competing same-day close records | Adjudicate order; the two handoffs need merging, not picking, or a session's record is lost |
| 5 | **#175's Stage 1** — `capital_aud` firewall regression + 843 unreviewed lines | Needs a fix and a re-review; it will also need a rebase once wave 1 lands |
| 6 | **`HC_NIGHTLY_URL` Actions secret** does not exist | Until created, #169's deadman is inert — the workflow passes while pinging nothing |

---

## Carried forward, not addressed this session

- **`asxos/domain/tax/{positions,cgt}.py` keep three bare `date.today()` calls**,
  allow-listed by #171's guard. #171 documents this honestly as a finding it did
  not fix. It needs a `tax-spec-conformance` pass: rule #6 makes CGT 12-month
  arithmetic calendar-exact, and a disposal evaluated a day early can flip the
  discount (spec §5.1). Latent rather than live — every current caller overrides
  the default.
- **#171's guard covers `date.today()` only.** `datetime.utcnow()` survives in
  `asxos/domain/brief/_runner.py` (×3, deprecated in 3.12, warns on every suite
  run). Timezone-neutral there (duration deltas), so not a correctness bug.
- **The agent DB role is still inert** — `asxos_agent_ro` exists; the MCP
  authenticates as `supabase_read_only_user`. Unchanged this session. #161's
  review adds one live detail: `scripts/roquery.py` connects on `DATABASE_URL`,
  *not* the MCP session's role, so the planned repoint plus `REVOKE ... ON signals`
  does **not** reach that path unless the script moves with it.
- **Migration `0042` reserved; `0045` unapplied.** 46 files on disk.

---

## Files to commit

This close wrote four files. They must reach **`main`** to be seen next session —
a handoff that lives only on a feature branch is a process defect
(`docs/README.md`).

- `docs/session-handoff-2026-08-24.md` (this file)
- `docs/product/roadmap-state.md` (Last wake snapshot)
- `docs/product/decision-log.md` (one appended row)
- `docs/product/arbi-run-ledger.md` (one appended row, score **4.5 provisional**)

No merge, no push to `main`, no migration, no DB write, no capital action was
taken from this close. That is `/ship`'s job, done deliberately.
