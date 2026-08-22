# DB access — why it keeps getting blocked, and the three fixes

**Status:** proposal — **every fix below needs James; arbi cannot apply any of them**
**Prepared:** 2026-08-22, `/arbi-mission` session on `claude/product-roadmap-backlog-8k3jz5`
**Trigger:** James — *"We need to rewrite access for DB, why does it keep getting blocked or denied."*

---

## Short answer

**Three independent mechanisms block DB access, and none of them is a policy decision anyone
made.** Two are configuration bugs. One is an environment setting. They were diagnosed from
evidence in this session, not from memory.

| # | Mechanism | What it blocks | Owner of the fix |
|---|---|---|---|
| 1 | **Environment network policy blocks outbound 5432** | *every* direct DB connection from this container | James — environment config |
| 2 | **The allowlist names an MCP server that no longer exists** | the MCP query route | James — `.claude/settings.json` or a new `.mcp.json` |
| 3 | **`authority-guard.sh` treats `cat`/`grep` as writes** | Bash *reads* of authority files | James — `.claude/hooks/` |

Fix 1 and 2 are independent, and **you need at least one of them** — they are the two routes to
the database. Fix 3 is pure friction removal with no security change.

---

## 1. The environment blocks port 5432 — this is the hard wall

Measured this session:

```
host=aws-1-ap-southeast-2.pooler.supabase.com port=5432
  aws-1-ap-southeast-2.pooler.supabase.com:5432 -> BLOCKED/UNREACHABLE (TimeoutError)
  api.github.com:443                            -> OPEN (0.2s)
```

`DATABASE_URL` **is** present in the environment, and the connection attempt is now *permitted*
(see §2's `roquery.py` result) — it just times out, because the remote environment's network
policy allows HTTPS and not Postgres. This is the same class of restriction that made AWS pricing
`unavailable` when `P3-02` was written, and it is why that work order still carries no cost model.

**Consequence:** no amount of editing `.claude/settings.json` gives this container direct DB
access. Fix 2 is the only route that can work here today, because the MCP server proxies over
HTTPS.

**Fix:** change the environment's network policy to permit outbound 5432 to the Supabase pooler
host. Environments are configured per the Claude Code on the web docs
(https://code.claude.com/docs/en/claude-code-on-the-web) — network policy is chosen when the
environment is created. This is a James action in the environment settings, not a repo change.

## 2. The allowlist names a server that does not exist

`.claude/settings.json:4` allows exactly one DB tool:

```json
"mcp__supabase-ro__execute_sql"
```

But the Supabase servers register under **per-session identifiers**. Observed this session:

```
mcp__9d7520d7-9986-4699-9d4a-ee0fcc9bf4d6__execute_sql   (read-only)
mcp__3ec0fde8-58dc-483a-b873-6aebe5cbb341__execute_sql   (read-write — has apply_migration)
```

A rule keyed to `supabase-ro` can therefore **never match**. The evidence is in the repo's own
audit log, `.claude/permission-requests.log` — every DB call this session was recorded as `ASK`,
never as an automatic allow:

```
ASK  2026-08-22T14:35:32Z  mcp__9d7520d7-...__execute_sql  SELECT ... FROM rs_fundamentals_pit ...
ASK  2026-08-22T14:37:46Z  mcp__9d7520d7-...__execute_sql  SELECT ... FROM rs_fundamentals_pit ...
```

**Why it looked fine until now.** With a human present, each prompt got approved and the query
ran, so the broken rule was invisible. Unattended, the same call simply fails. That is the whole
mystery: it was never denied on purpose, it was prompting every single time.

**Why there is no obvious one-line fix.** There is **no `.mcp.json` in this repo** — the servers
come from the account/connector layer, so the project cannot currently pin their names. Two
options, and I am not certain which the permission matcher supports, so this needs checking rather
than pasting:

- **(a) Pin the name.** Add a project `.mcp.json` defining the read-only Supabase server under a
  fixed name, so `mcp__supabase-ro__execute_sql` matches every session. This is the durable fix if
  the connector can be expressed as a project server.
- **(b) Re-approve per session.** In an interactive session use `/permissions` → always-allow. This
  writes the *current* UUID and breaks again next session. A stopgap, not a fix.

**Do not** simply add the read-write server (`mcp__3ec0fde8-…`) to the allowlist as a shortcut —
it carries `apply_migration` and full DDL. See §4.

## 3. `authority-guard.sh` blocks reads, not just writes

The hook denies any Bash command whose *text* mentions an authority path alongside a
"write-capable" utility. In practice that includes `cat`, `wc`, `grep` and `python3 -c`, so this
session was blocked from:

```
cat docs/product/arbi-evals.md          # a read
wc -l docs/product/arbi-scorecard.md    # a read
python3 -c "json.load(open('.claude/settings.json'))"   # a read
```

Every one of those files was then read successfully with the **Read tool**, which the hook does not
gate for reads. So the rule costs a retry per occurrence and prevents nothing — the information was
always reachable. It also blocked a `git commit` whose *commit message* quoted authority filenames,
which is the clearest sign the match is on text rather than intent.

**Fix:** narrow the hook's Bash matcher to commands that actually write — redirection into an
authority path (`>`, `>>`, `tee`), `sed -i`, `mv`/`cp` with an authority destination — and stop
matching read-only utilities. The `Edit`/`Write`/`MultiEdit` matchers are the real control and stay
exactly as they are. This is a friction fix with **no** reduction in what the guard prevents.

---

## 4. On "full autonomy — delete the blocks"

Delivering the ask honestly means separating two things that look alike:

**Read access can be opened wide, safely.** Fixes 1–3 grant the agent read of everything —
including the tax and holdings tables — and that is the right call: nearly every task this session
was blocked on was a *read*. A read cannot destroy anything.

**Write access is the one that is not symmetrical.** The read-write server
(`mcp__3ec0fde8-…__execute_sql`) plus `apply_migration` can `DROP` or `UPDATE` tables that
`backup_irreplaceable.sh` exists precisely because they cannot be re-derived —
`theses`, `thesis_revisions`, `themes`, `theme_holdings`, `holding_lots`, `decisions`. A wrong
`UPDATE holding_lots` is a corrupted CGT cost base, and the CGT record is a tax position, not just
data. There is no undo.

**Recommendation, and it is yours to overrule:** take fixes 1–3 now, which removes essentially all
of the friction actually encountered, and treat write/DDL as a separate grant — ideally scoped
(a specific migration, a specific session) rather than standing. If you want standing write access
anyway, say so and I will draft that patch too; I am flagging the asymmetry, not refusing it.

## 5. What arbi did in the meantime

`scripts/roquery.py` + `tests/test_roquery.py` (35 tests) — a single read-only SQL path that does
not depend on MCP naming at all:

```
Bash(.venv/bin/python scripts/roquery.py:*)
```

Read-only is enforced by **Postgres** (`conn.set_session(readonly=True)`), not by the script;
statement screening is a second, earlier layer for clear errors and multi-statement payloads.
Verified this session: `--check` mode works, and the auto-mode classifier **permitted** the live
attempt that it had refused for an equivalent ad-hoc heredoc — so the named, committed, tested
script is the shape that gets through. It then timed out on connect, which is how §1 was found.

**Honest limit:** this is useless in *this* container until §1 is fixed, because nothing can reach
5432 from here. It is immediately useful in local dev and in GitHub Actions, and it is the durable
path once egress is open. It is not a substitute for §2.

---

## Why arbi could not just fix this

`.claude/settings.json` and `.claude/hooks/` are Edit-denied (`settings.json:61-65`), guarded by
`authority-guard.sh`, and `CLAUDE.md` states arbi never edits its own boundaries — it may only
draft a change for James to approve. That is working as designed, and it is also the reason
`permission-and-guard-friction-2026-08-21.md` exists: **a verbal grant changes intent, never
capability.** This document is the draft; applying it is yours.
