# Allowlist archive + permission rework — 2026-08-22

**Status:** proposal — **James authorised the change; arbi cannot apply it** (see §6)
**Authorisation:** James, 2026-08-22: *"I want to archive the allowlist until we rework it. I
authorise this change. Ensure it's documented."*
**Supersedes nothing.** `.claude/settings.json` is unchanged on disk; this file is the archive and
the drafted replacement.
**Companion:** `docs/proposals/db-access-remediation-2026-08-22.md` — the diagnosis this follows from.

---

## 1. The instinct is right, and it needs one pairing

Archiving the allowlist is the correct move, for a reason worth stating plainly: **the allowlist
exists only to suppress permission prompts.** It grants nothing on its own. So its one failure mode
is the one we hit — an entry that silently stops matching (`mcp__supabase-ro__execute_sql` against
servers that register under per-session UUIDs) degrades to *prompting*, invisibly, until nobody is
there to approve.

**But archiving it alone makes things strictly worse.** Every entry removed is a command that
starts prompting again: `git status`, `pytest`, `ruff`, `mypy`, `gh run list`, `cat`, `grep`. An
empty allowlist is maximum friction, not minimum.

The pairing that makes it work is `permissions.defaultMode`. Set that, and the allowlist becomes
genuinely redundant — nothing prompts, so there is nothing for a stale entry to fail to suppress.
**The brittleness disappears rather than being patched.** That is why this is a rework and not a
deletion.

## 2. The archive — current `permissions.allow`, verbatim

Preserved here so the rework can start from what existed rather than from memory. 57 entries as of
`fb7545d`.

```jsonc
// MCP (2 of these are the broken ones — see §3)
"mcp__supabase-ro__execute_sql",
"mcp__github__get_me", "mcp__github__list_pull_requests", "mcp__github__pull_request_read",
"mcp__github__list_commits", "mcp__github__list_branches", "mcp__github__get_job_logs",

// git
"Bash(git status:*)", "Bash(git log:*)", "Bash(git branch:*)", "Bash(git rev-list:*)",
"Bash(git merge-base:*)", "Bash(git fetch:*)", "Bash(git diff:*)", "Bash(git show:*)",
"Bash(git remote -v)", "Bash(git add:*)", "Bash(git checkout:*)", "Bash(git switch:*)",
"Bash(git stash:*)", "Bash(git rebase:*)", "Bash(git merge:*)", "Bash(git commit:*)",
"Bash(git push:*)",

// test / lint / type
"Bash(pytest:*)", "Bash(python -m pytest:*)", "Bash(python -m py_compile:*)",
"Bash(python3 -m pytest:*)", "Bash(python3 -m ruff:*)", "Bash(ruff:*)", "Bash(mypy:*)",
"Bash(make check:*)",

// gh
"Bash(gh workflow run full-check.yml:*)", "Bash(gh workflow run targeted-ml-tests.yml:*)",
"Bash(gh workflow run migration-integration.yml:*)", "Bash(gh workflow run backup.yml:*)",
"Bash(gh workflow run claude-execute.yml:*)", "Bash(gh run list:*)", "Bash(gh run view:*)",
"Bash(gh run watch:*)", "Bash(gh pr create:*)", "Bash(gh pr view:*)", "Bash(gh pr comment:*)",

// shell read utilities
"Bash(ls:*)", "Bash(cat:*)", "Bash(head:*)", "Bash(tail:*)", "Bash(wc:*)", "Bash(grep:*)",
"Bash(echo:*)", "Bash(date:*)", "Bash(which:*)", "Bash(mkdir:*)",

// Render (dead — Render was deleted 2026-08-12; drop on rework)
"Bash(curl -s --max-time 25 -H \"Authorization: Bearer $RENDER_API_KEY\" \"https://api.render.com/v1/:*)"
```

**Two entries are already known-dead** and should not be carried into the rework: the
`mcp__supabase-ro__*` entry (server name no longer exists) and the Render curl (Render was deleted
2026-08-12, per CLAUDE.md non-negotiable #2).

## 3. The three layers, and which one actually blocks

Conflating these is why "grant access" has repeatedly changed nothing. They are independent.

| Layer | What it does | Effect of archiving the allowlist |
|---|---|---|
| **`permissions.allow`** | suppresses prompts for named tools | removing it → **more** prompts |
| **`permissions.deny`** | hard-blocks (40 entries: authority files + `.env`) | unaffected |
| **Hooks** (5 × `PreToolUse`) | run **regardless of permission mode** | unaffected |

The practical consequence: **`defaultMode` does not disable hooks.** `authority-guard.sh`,
`review-gate.sh`, `push-guard.sh`, `pr-draft-guard.sh` and `unattended-guard.sh` keep firing. So
"full autonomy" via permission mode alone still leaves the guard blocking `cat` on an authority
path and the review gate arming on staged Python. Both were hit repeatedly today.

## 4. The drafted replacement

```jsonc
{
  "permissions": {
    // Archived to docs/proposals/permission-allowlist-archive-2026-08-22.md §2.
    // Intentionally empty: with defaultMode set, per-tool pre-approval is redundant,
    // and an entry that silently stops matching is the failure mode being removed.
    "allow": [],
    "defaultMode": "bypassPermissions",
    "deny": [ /* ...unchanged, all 40 entries... */ ]
  },
  "hooks": { /* ...unchanged... */ }
}
```

**Keep the `deny` array.** It is the only thing standing between an agent and the tables
`backup_irreplaceable.sh` exists for — `theses`, `thesis_revisions`, `theme_holdings`,
`holding_lots`, `decisions` — plus `.env` and the governance set. It costs nothing when nothing is
trying to write there, and there is no undo for a corrupted CGT cost base.

**One entry deserves a deliberate decision rather than a default:** `Edit(/.claude/settings.json)`.
Removing it would let arbi edit its own permission model — which `arbi-constitution.md` forbids and
which is the single change that makes every other boundary advisory. Recommendation: **keep it**,
and accept that permission reworks stay manual. That friction is the control.

## 5. Recommended sequencing

1. **Apply §4** — archive the allowlist, set `defaultMode`, keep `deny`. Fixes the stale-MCP-name
   problem by making it irrelevant.
2. **Narrow `authority-guard.sh` to writes** — it currently matches command *text*, so it denies
   `cat`, `wc`, `grep` and `python3 -c` that only read, and denied a `git commit` because the
   commit *message* quoted authority filenames. The `Edit`/`Write`/`MultiEdit` matchers are the
   real control and stay as-is. Pure friction removal, no reduction in what is prevented.
3. **Environment network policy** — outbound 5432 is blocked, so the DB is unreachable regardless
   of permissions. Independent of this file; see the companion doc §1.

Steps 1 and 3 are both needed for live-data work. Step 1 alone does not reach the database.

## 6. Why arbi could not apply this despite the authorisation

Attempted this session, after the authorisation was given. A plain `cp` to **back up**
`.claude/settings.json` was refused:

```
authority-guard: this Bash command references an authority/boundary path alongside a
write-capable interpreter/utility — blocked. arbi may only DRAFT authority changes via a
reviewed PR.
```

Three independent layers, and a verbal grant moves none of them: the `deny` entry
(`settings.json:61`), `authority-guard.sh` (always-on, not mode-gated), and `CLAUDE.md`'s rule that
arbi never edits its own boundaries and may only draft a change for James to approve.

This is the third recorded instance of the pattern in
`permission-and-guard-friction-2026-08-21.md`: **an authorisation changes intent, never
capability.** The design is working as intended — and it does mean the apply step is James's, by
hand, every time.
