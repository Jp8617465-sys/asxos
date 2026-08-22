# Permission and guard friction — measured, with the patches James must apply

**Superseded as operating SoT (2026-08-22):** permission-mode mapping, two-speed
routing, and risk-tiered consult now live in `docs/product/harness-profiles.md`.
Keep this file as the measured 32-row / 3-denial evidence and the James-owned
patch list (§4).

**Status:** draft proposal — requires James to apply (both targets are authority paths)
**Prepared:** 2026-08-21, from one full working session (the HUBS position review)
**Evidence:** `.claude/permission-requests.log` (32 rows), 3 observed hook denials
**Owner of the fix:** James. arbi may only DRAFT changes to `.claude/settings.json` and
`.claude/hooks/` via a reviewed PR — this file is that draft.

---

## 0. Why this is a draft and not a commit

James granted broad access verbally in-session. That grant cannot be self-applied, for two
independent mechanical reasons, and both are working as designed:

1. **Permissions live in config, not conversation.** The harness reads
   `.claude/settings.json`; it does not read chat. A verbal grant changes nothing.
2. **This repo denies the agent write access to its own permission surface.**
   `settings.json` carries `Edit(/.claude/settings.json)` and `Edit(/.claude/hooks/**)` in its
   deny array, *and* `authority-guard.sh` re-checks the canonical path on every
   Edit/Write/MultiEdit/NotebookEdit. Either alone blocks the edit; both are active.

That second one is the control that survives a verbal instruction, and it should. The correct
path is the one the constitution already specifies: draft, review, merge.

**The most important thing to know:** granting permissions will **not** remove the guard blocks
in §2. Permissions and hooks are separate mechanisms. `authority-guard.sh` is explicitly
`ALWAYS-ON (not ARBI_UNATTENDED-gated)`, so no permission mode — including a fully permissive
one — disables it. Only a change to the hook itself will.

---

## 1. Permission-prompt friction — measured

`.claude/permission-requests.log` recorded **32 ASK rows and 0 DENY rows** across one session.

### 1.1 The allowlisted MCP tool prompted 24 times anyway

Rows 1–24 are `mcp__supabase-ro__execute_sql`, which **is already allowlisted**
(`settings.json:4`). It prompted on every call regardless. One call (row 2, the
`information_schema` query at 04:09:58) came back `Denied by user` — and the `PermissionDenied`
hook logged nothing for it.

Two readings, and this is worth one verification rather than a guess:

- the project `permissions.allow` array is not being honoured for MCP tools on this
  remote/web surface; or
- the `PermissionRequest` hook fires on every request including auto-approved ones, in which
  case 24 of those rows are noise and only the single denial was real friction.

**Verify before patching:** run any allowlisted MCP call in an interactive session and see
whether it prompts. If it does, the allowlist is not loading and no amount of adding entries
will help.

### 1.2 The MCP server IDs rotated mid-session — and this one is not fixable by allowlist

Rows 25–32 are `mcp__9d7520d7-9986-4699-9d4a-ee0fcc9bf4d6__execute_sql`. The Supabase MCP
server disconnected mid-session and re-registered under a **UUID** rather than the stable
`supabase-ro` alias. That name matches nothing in the allowlist, so every subsequent SQL call
prompted.

Allowlisting the UUID is not a fix — it will differ next session. The real options are:

- pin the server alias so it re-registers as `supabase-ro` (preferred, if the surface allows it);
- accept the prompts for MCP SQL and keep the allowlist honest;
- add the UUID via `/permissions` at the start of a session where it matters.

Do **not** paste rotating UUIDs into `settings.json` — it grows an allowlist that silently
stops matching and reads as coverage that isn't there.

### 1.3 Plain allowlist gap — `sed`

`Bash(sed:*)` is absent, and a read-only `sed -n '/CREATE TABLE theses/,/^);/p'` was refused
outright. `cat`, `head`, `tail`, `grep`, `wc` are all present; `sed` reading a line range is the
same class of operation.

### Proposed additions to `permissions.allow`

Read-only utilities only. Nothing here can mutate a file, and none of them is a new capability
class — each has a near-twin already on the list.

```json
"Bash(sed -n:*)",
"Bash(find:*)",
"Bash(rg:*)",
"Bash(cut:*)",
"Bash(sort:*)",
"Bash(uniq:*)",
"Bash(diff:*)",
"Bash(realpath:*)",
"Bash(git rev-parse:*)"
```

`sed -n` rather than `sed:*` deliberately: `-n` is the print-selected-lines mode and cannot
write in place, whereas `sed -i` can. Keep the narrower form.

**Also worth deleting while you are in there:** the last entry in the current allow array is a
`curl` against `api.render.com` with `$RENDER_API_KEY`. Render was deleted 2026-08-12
(commit `59fb835`). It is a dead grant on a live credential.

---

## 2. `authority-guard.sh` false positives — 3 in one session

This is the higher-cost item, and unlike §1 it is a genuine defect rather than a config gap.

The Bash branch (`authority-guard.sh:229-233`) denies when **both** regexes match the raw
command string:

- `authority_ref` — any authority path fragment appears anywhere in the text
- `write_verb` — includes a bare `>>?`, i.e. **any `>` character anywhere**

Because both are substring scans over untokenised command text, they fire on commands that
write nothing.

### Case 1 — read-only grep, blocked by `2>/dev/null`

```
grep -rn "fx_rates|FROM fx" --include=*.py --include=*.sql -i asxos/ migrations/ jobs/ 2>/dev/null | head -20
```

`authority_ref` matched `migrations/`. `write_verb` matched the `>` inside `2>/dev/null`.
Denied. The command is a pure read.

### Case 2 — read-only inspection of the settings file itself

```
ls -la .claude/ | head -20; cat .claude/settings.json; cat .claude/settings.local.json 2>/dev/null
```

Same mechanism. Reading the permission config to report on it is blocked by the guard that
protects it from writes.

### Case 3 — writing a non-authority file that merely *discusses* authority files

A heredoc writing `docs/reviews/hubs-position-review-2026-08-21.md` was denied because the
document's **prose** cites `CLAUDE.md`, `.claude/hooks/` and `migrations/`. The redirect target
was a plain docs path; the authority names were content, not destination.

This is the worst of the three: it means **no document about the governance surface can be
written through Bash**. Any future audit, runbook or postmortem naming these files hits it.

### Fix A — minimal, ships today

Scrub `/dev/null` and `/dev/stderr` redirects before the write-verb test. One line, inserted
after `cmd` is read at `:214`:

```bash
scrub="$(printf '%s' "$cmd" | sed -E 's#[0-9]*>>?[[:space:]]*/dev/(null|stderr)##g')"
```

then test `authority_ref` and `write_verb` against `$scrub` instead of `$cmd`.

This kills cases 1 and 2 and weakens nothing: `echo x > CLAUDE.md` still matches, because its
redirect target is not `/dev/null`. The security-engineer rationale at `:222-225` for including
a bare `>>?` is about *shell redirection performing a write* — a redirect to `/dev/null`
performs no write to any authority path by construction.

### Fix B — the real one, for case 3

Test the **redirect targets**, not the whole command string. Extract what follows each `>` /
`>>` and check only those against `authority_ref`; keep the interpreter and `cp`/`mv`/`tee`
checks scanning the full text, since those take their targets as arguments.

This is a larger change and deserves its own review. Until it lands, the workaround is real and
costless: **use the Write tool instead of a Bash heredoc.** The Edit/Write branch
(`:203-207`) checks `tool_input.file_path` through `canonical_path()` — it resolves the actual
destination and ignores file content entirely, which is correct behaviour. That is how the HUBS
review eventually got written.

### What must not change

The guard's core job — blocking an interpreter or redirect that genuinely targets an authority
path, including through a symlink alias — is sound and should stay exactly as strict. Neither
fix above touches that. Do not widen this by disabling the hook.

---

## 3. Three MCP servers need OAuth — only James can do this

Three servers reported `requires authentication`:

```
2c4b59a6-91dc-4e4c-acf6-f4cdbda72395
5b9fa627-c6b3-4909-9bed-12f134f40735
ab257f33-3af0-497b-92b1-e03662bf8832
```

This session is non-interactive, so the OAuth flow cannot run here — this is not a permission
that can be granted, it is a browser round-trip. For claude.ai connectors, authorize under
claude.ai connector settings; for other servers, via `claude mcp` or `/mcp` in an interactive
session. Until then those capabilities are simply unavailable.

---

## 4. What to do

| # | Action | Who | Effort |
|---|---|---|---|
| 1 | Verify whether `permissions.allow` loads at all for MCP tools on this surface (§1.1) | James | 1 min |
| 2 | Apply the allowlist additions, drop the dead Render `curl` grant (§1) | James | 2 min |
| 3 | Apply guard Fix A — the `/dev/null` scrub (§2) | James, or arbi drafts the PR | 5 min |
| 4 | Schedule guard Fix B — redirect-target checking (§2) | Build | own review |
| 5 | Authorize or dismiss the three OAuth servers (§3) | James | 2 min |
| 6 | Pin the Supabase MCP alias so it stops re-registering as a UUID (§1.2) | James | unknown |

Items 2 and 3 both touch authority paths. Neither can be applied by the agent, by design. If
you want them as a PR rather than a hand edit, say so and this draft becomes one — but the
merge is still yours.
