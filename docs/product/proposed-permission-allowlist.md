# Proposed Claude Code permission allow-list — arbi's reversible remit

**Status:** DRAFT for James to apply (governor-only change) · **Drafted:** 2026-07-11 by arbi
**Why a draft:** editing `.claude/settings.json` is a self-permission-grant; the harness
auto-mode classifier **denies** arbi writing it (the remit-expansion firewall — arbi cannot
widen its own powers; only the governor can). This is the mechanical realization of
`arbi-constitution.md` ("arbi may only *draft* a boundary change for James to approve").
**Aligns with:** `docs/product/arbi-permission-model.md` — the Infrastructure ladder I0–I4
(reversible) is auto-allowed; the irreversible tiers stay gated.

---

## What this does

Stops the repeated "authorise this?" prompts for **read-only + reversible** operations James
will always approve, while keeping every **irreversible / capital-adjacent** action gated.

- **`allow`** — read-only Supabase (RO server), GitHub *read* methods, reversible git
  (status/log/diff/add/commit/fetch/checkout + push to the `claude/*` working branch only),
  test/lint tooling, and `make check-drift` (the sanctioned Render-*read* path per CLAUDE.md #2).
- **`ask`** — loud, explicit gate on the crown jewels: push to `main`, read-write Supabase,
  migrations, PR create/merge, and GitHub file-write methods. (Anything not in `allow` already
  prompts by default; these are listed so the boundary is self-documenting and can't be
  silently widened by a future broad `allow`.)

**Deliberately NOT auto-allowed:** raw `curl … api.render.com`. Prefix-match rules can't tell a
GET from a POST/DELETE, so allowing it would leak Render *mutations*. Render reads go through
`make check-drift`; Render *writes* stay gated (and the `unattended-guard.sh` hook blocks them
mechanically for scheduled runs regardless).

**The two hooks are independent of this.** `review-gate.sh` (staged-`*.py` commit gate) and
`unattended-guard.sh` (blocks irreversible tiers for `ARBI_UNATTENDED=1` scheduled runs) still
fire on top of these permissions. This allow-list only reduces prompts for **attended,
interactive** sessions where James is present — it does not loosen the unattended firewall.

---

## How to apply (pick one)

1. **Interactive Claude Code:** run `/permissions` and add the rules below (writes to
   `.claude/settings.json` or `settings.local.json`), or
2. **Paste:** merge the `permissions` block below into `.claude/settings.json`, keeping the
   existing `hooks` block, then commit.

Scope choice: `.claude/settings.json` (committed) makes this a documented, version-controlled
part of arbi's remit — recommended, since the container is ephemeral and uncommitted config is
lost. Use `.claude/settings.local.json` (gitignored) if you'd rather keep it personal/local.

---

## The block

```json
{
  "permissions": {
    "allow": [
      "Read",
      "Glob",
      "Grep",

      "mcp__supabase-ro__execute_sql",
      "mcp__supabase-ro__list_tables",
      "mcp__supabase-ro__list_extensions",
      "mcp__supabase-ro__list_migrations",

      "mcp__github__get_me",
      "mcp__github__list_pull_requests",
      "mcp__github__pull_request_read",
      "mcp__github__list_commits",
      "mcp__github__get_commit",
      "mcp__github__list_branches",
      "mcp__github__get_file_contents",
      "mcp__github__list_issues",
      "mcp__github__issue_read",
      "mcp__github__search_issues",
      "mcp__github__search_pull_requests",
      "mcp__github__search_code",
      "mcp__github__list_tags",
      "mcp__github__get_tag",
      "mcp__github__actions_list",
      "mcp__github__actions_get",
      "mcp__github__get_job_logs",
      "mcp__github__get_check_run",

      "Bash(git status:*)",
      "Bash(git log:*)",
      "Bash(git diff:*)",
      "Bash(git show:*)",
      "Bash(git branch:*)",
      "Bash(git rev-parse:*)",
      "Bash(git merge-base:*)",
      "Bash(git add:*)",
      "Bash(git commit:*)",
      "Bash(git fetch:*)",
      "Bash(git checkout:*)",
      "Bash(git restore:*)",
      "Bash(git stash:*)",
      "Bash(git config user.email:*)",
      "Bash(git config user.name:*)",
      "Bash(git push -u origin claude/*)",
      "Bash(git push origin claude/*)",

      "Bash(ruff:*)",
      "Bash(mypy:*)",
      "Bash(pytest:*)",
      "Bash(python -m pytest:*)",
      "Bash(python -m py_compile:*)",
      "Bash(python -m ruff:*)",
      "Bash(python -m mypy:*)",
      "Bash(make check:*)",
      "Bash(make check-drift:*)"
    ],
    "ask": [
      "Bash(git push origin main:*)",
      "Bash(git push -u origin main:*)",
      "mcp__Supabase__execute_sql",
      "mcp__Supabase__apply_migration",
      "mcp__github__merge_pull_request",
      "mcp__github__create_pull_request",
      "mcp__github__push_files",
      "mcp__github__create_or_update_file",
      "mcp__github__delete_file"
    ]
  }
}
```

Keep the existing `"hooks": { ... }` block in `.claude/settings.json` — merge, don't replace.

---

## After applying

Consider recording this in `docs/product/arbi-permission-model.md` as the **mechanical
realization** of the Infrastructure ladder's reversible tiers (I0–I4 auto-allowed; I5–I6 gated),
so the doc and the live settings stay in sync — and note it in `decision-log.md` as a
governor-directed remit expansion (2026-07-11).
