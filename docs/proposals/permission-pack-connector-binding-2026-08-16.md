# Permission pack — surgical grants + agent DB connector binding (2026-08-16)

**Status:** draft proposal · every change here edits an authority-guarded surface → **James
applies/merges; nothing in this document is self-applied**
**Origin:** James asked (2026-08-16) whether to bypass all hard stops; arbi's answer was that
the felt friction is specific and surgical. This is the surgical pack, with the L23 enumeration
attached to each grant. Section 4 is task #21 (the connector binding), which is a live defect,
not a convenience.

Per L23 (2026-08-14 promotion batch): each grant below lists the concrete production side
effects it newly reaches, by name, and enumeration is necessary but never sufficient — each
grant is judged by the widest capability it confers.

---

## 1. Grant: backup-repo operations (narrow allow-rules)

**Friction observed:** the one-time signal-evidence archive push (task #17) was
classifier-blocked at `git clone …asxos-backups`, leaving the off-site copy pending a hand-run
command.

**Proposed `settings.json` allow rules:**

```json
"Bash(git clone --depth=1 --quiet https://github.com/Jp8617465-sys/asxos-backups.git*)",
"Bash(bash /Users/jpcino/Projects/asxos-archive/push_archive.sh)"
```

**L23 enumeration — what this newly reaches:** clone of, and (via the pinned script only)
one commit + push to, `Jp8617465-sys/asxos-backups` — the private repo already holding daily
dumps of `holding_lots` and `theses`. Additive git writes; recoverable with `git revert` on
that repo. **Widest capability:** the second rule executes whatever
`~/Projects/asxos-archive/push_archive.sh` contains at run time — the file lives outside the
repo and outside review. If that is unacceptable, drop rule 2 and keep the push hand-run; rule
1 alone removes the clone friction. Neither rule touches this repo, `main`, the DB, or any
scheduler.

## 2. Grant: docs-only auto-merge carve-out (decision, not a default)

**Friction observed:** twelve of the last thirteen merges were docs-only PRs James had to
hand-merge.

**Proposed shape:** permit `gh pr merge --squash` on a PR **iff** its changed-file list
contains no path under `asxos/`, `migrations/`, `.claude/`, `.github/`, `scripts/`, and no
`.py` anywhere — mechanically checkable before the merge command runs. Requires amending the
packet §8 merge stop and `pr-draft-guard.sh` (both James-only edits).

**L23 enumeration — what this newly reaches:** merge-to-main of `docs/**` content. That is
not "just docs" here: `docs/product/**` is **authority-ladder level 4** — arbi reads it every
wake as truth. An auto-merged doc becomes level-4 authority with no human review, which is the
exact poisoning channel `arbi-memory-policy.md` firewalls for level 6. **Widest capability:**
arbi promoting its own words to level 4 unreviewed.
**Two narrowings, pick one or reject both:**
- (a) carve-out excludes `docs/product/**` entirely (auto-merge only `docs/proposals/**`,
  `docs/session-*`, dated records) — safe, less useful;
- (b) carve-out includes `docs/product/**` except `arbi-*.md`, `north-star.md`, `memory/**`,
  `rubrics/**` — more useful, and accepts that state docs (`roadmap-state.md`,
  `risk-register.md`) can land unreviewed.
arbi's recommendation: **(a)**. The hand-merge burden is mostly proposals and session records;
state docs are exactly where a bad unreviewed sentence compounds.

## 3. Fix: the drafting-channel false-deny (promotes 21.4)

**Friction observed (≥5 occurrences, two sessions):** `authority-guard.sh` denies read-only
commands — `grep`, `tail`, `cat`, `wc` pipelines — whenever a protected path appears in the
command text, because its utility list treats read-only tools as write-capable. The grader hit
it three times; this session hit it twice more. Effect: the *drafting* workflow (read the
guarded file → draft its replacement) is what gets blocked, which is 21.4's definition of a
governance bug ("a deny that removes the drafting channel").

**Proposed edit (to `authority-guard.sh`, James-only):** require an actual write form —
`sed -i`, `tee`, `>`/`>>` redirection targeting the protected path, `cp`/`mv`/`install`/
`patch`/`truncate`/`sponge`/`dd of=`, interpreter-with-file-write — and stop matching bare
`cat`/`tail`/`head`/`grep`/`wc`/`ls` pipelines. The Edit/Write-tool deny layer is untouched;
this narrows only the Bash text-matcher's false-positive surface.

**L23 enumeration — what this newly reaches:** nothing. It grants no write path (Edit/Write
denies and the hook's write-verb denies all stand); it removes a read-only false positive.
The risk direction is the reverse: verify the narrowed regex still catches every genuine write
verb — the edit must ship with the hook's test file extended to pin
`grep foo CLAUDE.md` → allow and `sed -i s/x/y/ CLAUDE.md` → deny.

## 4. Task #21 — the agent DB connector binding (live defect)

**Defect:** eleven live files pin `mcp__supabase-ro__execute_sql`
(`.claude/settings.json`, `.claude/agents/README.md`, `.claude/hooks/unattended-guard.sh`,
and all eight data-backed agent definitions), while the connector currently resolves as
`mcp__claude_ai_supabase-ro__*`. All eight data-backed agents — the entire `/pm-review`
evidence layer plus the three discovery agents — declare a DB tool that does not resolve.
Verified safe in the deny direction: `unattended-guard.sh`'s catch-all `mcp__*` deny swallows
every renamed server, so the rename over-blocks rather than under-blocks.

**Why not rename the eleven files:** the connector-layer name has changed across sessions
before ( `mcp__Supabase__*` → `mcp__supabase-ro__*` → `mcp__claude_ai_supabase-ro__*` ).
Renaming chases the claude.ai connector layer and breaks again on the next change. L18
(2026-08-14 promotion): fix the pipe, not the name.

**Proposed fix — a project-owned `.mcp.json` that recreates the pinned name:**

```json
{
  "mcpServers": {
    "supabase-ro": {
      "command": "npx",
      "args": [
        "-y", "@supabase/mcp-server-supabase",
        "--read-only",
        "--features=database",
        "--project-ref=<PROJECT_REF>"
      ],
      "env": { "SUPABASE_ACCESS_TOKEN": "${SUPABASE_ACCESS_TOKEN}" }
    }
  }
}
```

Because the server is project-defined with the name `supabase-ro`, its tools resolve as
`mcp__supabase-ro__execute_sql` etc. — **all eleven pinned references become correct again with
zero file edits**, the binding survives claude.ai connector-layer renames forever, and the
existing `settings.json` allow rules and `unattended-guard.sh` classifiers match unchanged.

**What only James can do:** create `.mcp.json` (mounting an MCP server is a tool-surface
change = authority), and provision `SUPABASE_ACCESS_TOKEN` in the local environment (a
credential). **Security notes for that decision, stated before the rationale per L23:**
- A Supabase PAT is a **management-API credential for the whole project**, not a DB role. The
  flags `--read-only` + `--features=database` constrain the server to read-only SQL, but the
  *token* is strictly more powerful than the current `supabase_read_only_user` DB role the
  claude.ai connector uses. Widest capability = whatever the PAT can do if the flags are
  dropped by a future edit of `.mcp.json`.
- Mitigations: scope the PAT to this one project; keep `.mcp.json` in the authority-guard's
  protected set so flag changes require the draft-PR route; keep the claude.ai connector as
  fallback.
- Alternative with a smaller credential: a plain Postgres MCP server (e.g.
  `@modelcontextprotocol/server-postgres`) pointed at a `supabase_read_only_user` connection
  string — credential is the existing read-only DB role (least privilege), but its tool is
  named `query`, not `execute_sql`, so the eleven files would need one final rename to
  `mcp__supabase-ro__query`. More edits, strictly weaker credential.
- arbi's recommendation: **the Postgres-server variant** (least-privilege credential beats
  zero-edit convenience; the one-time rename is bounded and final because the name is
  project-owned thereafter).

---

## 5. Session window grants — the fail-closed answer to "unblock now, reinstate at close"

**James asked (2026-08-16):** can the hard stops be lifted for a session and reinstated at
`/arbi-close`? The reinstate-at-close shape has three defects: (a) re-arming a guard does not
undo whatever irreversible action crossed while it was down — the stop's rule is restored, the
state is not; (b) the exit depends on the agent the window constrains — if the session dies
before `/arbi-close` (this one has already crash-compacted once), the stops stay down; (c) the
error-catching layer is off precisely during peak activity, and it caught three real errors
this week.

**Proposed mechanism that keeps the intent and fails closed — a scoped, self-expiring window
grant:**

- James writes `.claude/window-grant.json` (a new authority-guarded file):

  ```json
  {
    "granted_by": "james",
    "granted_at": "2026-08-16T10:00:00Z",
    "expires_at": "2026-08-16T16:00:00Z",
    "lifted": ["merge-docs-only", "backup-repo-push"]
  }
  ```

- Each deny hook, before denying, checks the grant file: if the file exists, is
  well-formed, names the specific stop being hit in `lifted`, and `expires_at` is in the
  future → allow, and print an `[window-grant]` line so every use is visible in the log.
  Anything else — absent file, expired, malformed, stop not named — → deny as today.
- **Fail-closed by construction:** expiry is checked at each use, so the window closes itself
  mid-session with nothing to remember; a crashed session leaves only a file that expires.
  `/arbi-close` records (not performs) the closure: which grants existed, what crossed under
  them, when they lapsed.
- **Named stops only, never `"all"`:** the hook rejects a grant whose `lifted` contains a
  wildcard. The un-liftable floor stays un-liftable regardless of grant content: capital
  execution, personalised financial instruction (s766B), rule #11's quarantine, migration
  0042. The hook ignores those stop-names in any grant file.
- Writing the grant file is itself authority-guarded — only James creates it (that is the
  point), and arbi drafting one for James to place is the ordinary drafting channel.

**L23 enumeration — what this newly reaches:** whatever each named stop guards, for the grant
window, visibly. The design's exposure is bounded by the narrowest thing James names, not by
the mechanism. The hook edits are James-only; this section is the draft.

---

## Not in this pack

A blanket bypass of all hard stops. If James wants it after this pack lands, it is a
constitution-level amendment he authors; arbi's position is recorded: the stops caught the
`gh run rerun` grant, the `$(...)` bypass, and two false control-strength claims inside one
week — a blanket bypass converts that error class from denied attempts into production
events. The s766B firewall, capital execution, and personalised-advice floors are not
bypassable by configuration in any case.
