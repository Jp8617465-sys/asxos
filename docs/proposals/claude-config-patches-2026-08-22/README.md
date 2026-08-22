# `.claude/**` patches — ready to apply, 2026-08-22

**Status:** drafted; **NOT applied**. James authorised applying these; the tooling refused.
**Why they are here and not in `.claude/`:** every attempt was denied by
`permissions.deny` before it even reached `authority-guard.sh` —
`File is in a directory that is denied by your permission settings.` A `cp` to merely *back
up* `settings.json` was refused too. This is the **fourth** recorded instance in one session
of the same fact: an authorisation changes intent, never capability.

**I did not route around it.** `~/.claude/settings.json` sits outside the repo and is covered
by neither the deny array nor the guard's repo-relative fragment list, so setting
`defaultMode` there would have worked. That is exploiting a known gap in a control, which is
James's call to make, not mine to take — it is named in `authority-guard.sh`'s own header as
an accepted residual risk.

Apply order below is by value: **C first** — it is the only one that touches a live
capital-adjacent hazard.

---

## C — `.claude/agents/thesis-coherence-guard.md` (do this one first)

```bash
cp docs/proposals/claude-config-patches-2026-08-22/thesis-coherence-guard.md \
   .claude/agents/thesis-coherence-guard.md
```

**Why.** The agent's step 1 is `SELECT signal_label, prob_up, shap_factors FROM signals WHERE
model = 'model_a'`. PR #144 deleted every writer to `signals`, so the query still returns rows
and the agent keeps emitting confident COHERENT/CONTRADICTED verdicts from frozen evidence —
into the `/pm-review` synthesis that informs real holding decisions. Worse than an error,
because it looks like a working answer. Its frontmatter said use **PROACTIVELY**, so not
running `/pm-review` did not contain it.

**Amputation, not retirement.** The revision-fatigue check is live, model-independent, and the
only automated check on that failure mode; deleting the agent would throw it away. The
replacement keeps it, drops the three Model A steps, removes the PROACTIVELY trigger, and
carries an inline note so nobody restores the SHAP path by "fixing" the file later.

**Verify:** `grep -c "FROM signals" .claude/agents/thesis-coherence-guard.md` → `0`.
Closes `james-inbox.md:53`.

---

## A — `.claude/settings.json`

Two edits. **Do not touch the `deny` array.**

```diff
 {
   "permissions": {
+    "defaultMode": "bypassPermissions",
-    "allow": [
-      "mcp__supabase-ro__execute_sql",
-      ... all 57 entries ...
-    ],
+    "allow": [],
     "deny": [ ...unchanged... ]
   },
   "hooks": { ...unchanged... }
 }
```

The 57 archived entries are preserved verbatim in
`docs/proposals/permission-allowlist-archive-2026-08-22.md` §2.

**Why both edits, and why neither alone.** The allowlist grants nothing — it only suppresses
prompts. Its one failure mode is the one that bit us: `mcp__supabase-ro__execute_sql` stopped
matching when the servers moved to per-session UUIDs, so it silently degraded to *prompting*,
invisibly, until nobody was there to approve. `defaultMode` makes the allowlist redundant, so
the brittleness disappears rather than being patched. **Emptying `allow` without setting
`defaultMode` makes things strictly worse** — `git status`, `pytest`, `ruff`, `cat` and `grep`
all start prompting again.

**Two things deliberately kept:**
- `Edit(/.claude/settings.json)` **stays in `deny`.** A one-time grant must not make itself
  permanent; removing it would let the agent rewrite its own permission model from here on.
- The **whole `deny` array stays.** It is the only thing between an agent and the tables
  `backup_irreplaceable.sh` exists for. There is no undo for a corrupted CGT cost base.

**Note:** `defaultMode` does **not** disable hooks. All five `PreToolUse` hooks keep firing.
It may also need a session restart to take effect.

**Verify:** run one read-only query, then check `.claude/permission-requests.log` records an
allow rather than `ASK`. Config that "looks right" is not evidence.

---

## B — `.claude/hooks/authority-guard.sh`

Two surgical changes to the `Bash)` branch (~line 213). Everything else, including all four
`Edit`/`Write`/`MultiEdit`/`NotebookEdit` matchers, is untouched — those are the real control.

**The bug.** `write_verb` matches `>>?` — *any* redirect, anywhere in the command — and
`authority_ref` matches the path *anywhere in the command text*. So a heredoc writing to
`/tmp` is blocked merely for **mentioning** an authority path in its body. Observed today:

| Command | Wrote to | Blocked? |
|---|---|---|
| `cat > /tmp/scratch <<EOF … .claude/agents/ … EOF` | `/tmp` | yes — wrongly |
| `git commit -F -` with a message quoting authority filenames | git object store | yes — wrongly |
| `wc -l docs/product/arbi-evals.md` | nothing | yes — wrongly |
| `cp .claude/settings.json /tmp/backup.json` | `/tmp` | yes — the authority file was the **source** |

Every one of those files was then read successfully with the **Read** tool, which the hook
does not gate for reads. So the rule costs a retry per occurrence and prevents nothing.

### B1 — strip heredoc bodies before matching

A heredoc body is data, not a command. Insert immediately after the `[ -n "$cmd" ] || exit 0`
line:

```bash
    # A heredoc BODY is data, not a command — a commit message or a scratch file that
    # merely NAMES an authority path is not a write to it. Strip bodies before matching.
    # (Blocked 4 legitimate commands on 2026-08-22, including a git commit whose only
    # offence was quoting authority filenames in its message.)
    cmd="$(printf '%s' "$cmd" | awk '
      /<<-?[A-Za-z_"'"'"']/ && !inbody { print; inbody=1; next }
      inbody && /^[[:space:]]*[A-Za-z_]+[[:space:]]*$/ { inbody=0; next }
      !inbody { print }
    ')"
```

### B2 — a redirect only counts when it targets an authority path

Replace the bare `>>?` alternative in `write_verb` with a form that requires the authority
path to directly follow the operator:

```diff
-    write_verb='(>>?|python[0-9.]*[[:space:]]|…'
+    write_verb='(>>?[[:space:]]*("|'"'"')?('"$(_authority_regex_alt)"')|python[0-9.]*[[:space:]]|…'
```

**Left deliberately conservative:** `cp`, `mv`, `python`, `perl`, `ruby`, `node` and the rest
still match on mere mention. Narrowing those needs argument-position parsing, and a false
*refusal* there costs a retry while a false *accept* costs an authority file. B1 alone removes
most of the observed friction.

**Verify:** `bash tests/…` has no coverage for this hook's Bash branch — the existing
`tests/test_review_gate_hook.py` covers the *review-gate* hook only. Test B by hand:
`cat > /tmp/x <<'EOF'` … mentioning `CLAUDE.md` … `EOF` should now pass, while
`echo x > CLAUDE.md` must still be denied.

---

## What is NOT in this patch set

- **No `.mcp.json`.** A project-defined Supabase server needs `SUPABASE_ACCESS_TOKEN`, which
  is **not in this environment** (checked by name). `permission-pack-connector-binding-2026-08-16.md`
  §4 already records that provisioning it is James's alone. Its preferred variant
  (`server-postgres` against a least-privilege connection string) is **now void here** —
  that needs port 5432, which the environment blocks.
- **No network-policy change.** Outbound 5432 is blocked at the environment level; that is
  configured outside the repo.
- **No `deny`-array narrowing**, and specifically no removal of `Edit(/.claude/settings.json)`.
