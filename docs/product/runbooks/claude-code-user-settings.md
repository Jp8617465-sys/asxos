# Runbook — Claude Code user settings (`defaultMode: auto`)

**Status:** current · awaiting James's execution
**Scope:** one local setting James applies on his machine. An agent session
**must not apply this.**
**Last verified:** 2026-08-24 (Amendment G — this is now the first step of a
dated measurement, not an undated follow-up)
**Owner:** James

Official Claude Code docs: `"auto"` in project `.claude/settings.json` or
`.claude/settings.local.json` does **not** take effect. The value belongs in
`~/.claude/settings.json`.

Amendment G ruling 1 (James, 2026-08-24): turn this on **first**. Do **not**
rewrite `push-guard.sh` / `pr-draft-guard.sh` to emit `allow` until a week of
log data says a closed set of prompts remains. Re-read the log ~**2026-08-31**.
That date coincides with dark-launch #1/#4 expiry — do not conflate the two.

## Steps

1. Open `~/.claude/settings.json` (create if missing).
2. Merge:

```json
{
  "permissions": {
    "defaultMode": "auto"
  }
}
```

3. Do **not** set `bypassPermissions`. Do **not** put `defaultMode` in the repo.
4. New terminal session. Status bar should show auto mode.
5. Confirm deny still binds on remaining authority paths
   (`authority-guard.sh` is ALWAYS-ON; `auto` does not disable hooks).

## Week-of-data protocol (ruling 1)

The log is `.claude/permission-requests.log` (gitignored via `*.log`; written
by the `PermissionRequest` / `PermissionDenied` hooks in repo
`.claude/settings.json`). TSV columns: `ASK|DENY`, UTC timestamp, tool name,
command/path/query/url.

**How to read it — do not treat ASK count as prompt count.**

- `PermissionRequest` has been observed to fire on already-allowlisted MCP
  calls as ASK (`docs/proposals/permission-and-guard-friction-2026-08-21.md`
  §1.1, 24 of 32 rows). Those rows are noise unless you also saw a prompt.
- `PermissionDenied` once missed a user-clicked deny on an allowlisted SQL
  call (same §1.1). DENY count is a lower bound.
- Cursor Cloud Agents **do not write this log** (R17). The week is a Claude
  Code local/attended measurement only.
- Your own noticed-prompt count is the fatigue metric. The log's job is to
  capture **literal command strings** for any closed set that still prompts
  after `auto` is on — that is the only input a later exact-match allowlist
  is allowed to use, and the only shape that is red-teamable.

**After ~2026-08-31, one of two outcomes:**

- Most noticed prompts are gone → hook rewrite stays deferred. Do not reopen
  the 2026-07-14 asymmetric-risk decision for nothing.
- A specific closed set still prompts → bring the exact strings. A later
  ruling may authorise a *narrow exact-match* allow arm. The Compass sample
  regex (`^git (status|log|diff|fetch|add|commit|switch)`) is **not** that
  allowlist.

Do not start the hook rewrite from this Cloud Agent. Do not fall through to a
blanket `allow`.
