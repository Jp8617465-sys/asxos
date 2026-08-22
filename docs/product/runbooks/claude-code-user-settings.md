# Runbook — Claude Code user settings (`defaultMode: auto`)

**Status:** current · awaiting James's execution
**Scope:** one local setting James applies on his machine. An agent session
**must not apply this.**
**Last verified:** 2026-08-22
**Owner:** James

Official Claude Code docs: `"auto"` in project `.claude/settings.json` or
`.claude/settings.local.json` does **not** take effect. The value belongs in
`~/.claude/settings.json`.

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
5. Confirm deny still binds on remaining authority paths.

Granting `auto` does **not** disable hooks.
