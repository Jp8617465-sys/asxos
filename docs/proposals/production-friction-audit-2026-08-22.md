# Production friction audit — what actually blocks production code, and who can fix it

**Status:** draft — for James
**Prepared:** 2026-08-22, session `claude/production-friction-audit-e341uu`
**Method:** every claim below was probed live in this session (a command actually run, a file
actually read, a query actually issued against production read-only) — not inferred from prior
docs. Where a prior doc's claim is re-confirmed, that is stated; where it could not be confirmed,
that is stated too. Two claims in the source material turned out to need correction (noted inline
in §A rows 1 and 9b) and one new defect was found live while investigating (§A row 3).
**Inputs read:** `docs/session-handoff-2026-08-22.md`, `arbi-run-ledger.md` row `close-2026-08-22`,
`docs/proposals/review-gate-allow-rule-2026-08-22.md`, `docs/proposals/agent-db-role-the-control-
is-inert-2026-08-22.md`, `docs/proposals/permission-and-guard-friction-2026-08-21.md` — all four
of the last three live only on the unmerged branch `claude/production-code-session-tasks-5hqs5n`
(draft PR #154), not on `main`; fetched to read them.
**Constraints honoured:** no fix applied, no denied path edited, no merge, no migration, no DB
write, rule #11 untouched (no read of `signals`, no Model A citation).

---

## Summary

Of the eight roadblocks investigated, **five are HARNESS** (Claude Code / MCP infrastructure —
not fixable from this repo), **six are REPO** (settings/hooks/docs — fixable, diffs below, but
every one sits behind the same lock: the files that would carry the fix are Edit-denied to any
session, so only James can apply them), and **one is ENVIRONMENT** (sandbox setup — fixable with
a `SessionStart` hook, itself a REPO-class settings.json change). Some items are both a REPO
symptom and a HARNESS root cause; the table marks both.

The single highest-leverage fix is one line, already drafted and unapplied since 2026-08-22:
adding `touch` for the review-gate marker to `permissions.allow`. It does not remove the review
gate — it removes the coin-flip on whether a session can commit Python *at all*.

On the structural question: yes, the friction is asymmetric and it does bias the project toward
prose. Measured across the last 30 merged PRs, 19 (63%) touch zero `.py` files. But the
counter-hypothesis is also real and measurably explains part of it — see §D.

---

## A. Roadblock classification

| # | Roadblock | Class | Evidence (probed this session) |
|---|---|---|---|
| 1 | Review-gate marker (`touch .claude/.review-passed-*`) denied unpredictably | **HARNESS** (root cause) / **REPO** (the fix) | `touch` is absent from `permissions.allow` entirely (`grep -n "Bash(touch" .claude/settings.json` → no match) — it is not denied by any rule, it is *unlisted*, so its outcome depends on ambient/session permission handling outside repo config. I ran the identical command (`touch .claude/.review-passed-probe-test-...`) in this session and it **succeeded immediately, no prompt** — proof the block is not a fixed rule keyed to that path. See §A.1 discussion below for what this does and doesn't establish. |
| 2 | No in-session path to edit `.claude/settings.json` or `.claude/settings.local.json` | **REPO — by design, not a bug** | Read `.claude/settings.json:61-62`: both paths are explicit `Edit(...)` deny entries. Read `authority-guard.sh:61` (`.claude/settings.json`, `.claude/settings.local.json` both in `AUTHORITY_FRAGMENTS`) and its Bash-command branch (`:213-234`), which also blocks a heredoc/redirect/interpreter route to either file. Two independent layers, both intentional (`arbi-constitution`: arbi may only draft authority changes). `settings.local.json` does not currently exist (`ls` confirms). No in-session path exists for either file — confirmed by reading the enforcement code, not by attempting the write (see note below). |
| 3 | `authority-guard.sh` false-positives on reads that merely redirect stderr | **REPO**, fixable, diff in §C | **Reproduced live, this session, a variant not covered by the already-drafted fix.** `head -20 .claude/agents/thesis-coherence-guard.md 2>&1` was denied; the identical command **without** `2>&1` succeeded. The 2026-08-21 proposal's drafted "Fix A" only scrubs `/dev/null` and `/dev/stderr` redirect targets before the write-verb test — it does **not** scrub `2>&1` (fd-duplication, a far more common idiom than `2>/dev/null`). This is a fourth false-positive instance, and the first one whose trigger the existing draft fix would still miss. |
| 4 | `Makefile` `PY` defaults to `/usr/local/bin/python3.12`, doesn't exist in this sandbox | **ENVIRONMENT** (sandbox) / **REPO** (the fix) | `ls /usr/local/bin/python3.12` → no such file. Real interpreter: `/usr/bin/python3.12` (confirmed present, executable). Bare `python3` → 3.11.15. `pyproject.toml requires-python = ">=3.12,<3.13"`. Confirmed exactly as claimed. |
| 5 | No `.venv` at session start | **ENVIRONMENT** | `ls .venv` → no such file, at session start. Confirmed. |
| 6 | CLAUDE.md's "Known test environment gaps" (joblib chain) is stale | **REPO**, fixable, diff in §C | `grep -rn "import joblib\|lightgbm\|sklearn\|shap" asxos/ jobs/ tests/` → 2 hits, both **inside a docstring/comment in `tests/test_cli_model_independence.py`** guarding *against* those imports, zero real imports. Then built a real venv per the `Makefile`'s own `install` target (`/usr/bin/python3.12 -m venv`, `pip install -e ".[dev]"`) and ran the actual gates: **`ruff check .` → All checks passed. `mypy asxos` → Success: no issues found in 164 source files. `pytest -q` → 2423 passed, 1 skipped, 0 collection errors** (41s). This independently reproduces the 2026-08-22 measurement (that session reported 2427/1/0 — the 4-test difference is normal drift from commits since, not a discrepancy in the finding). The documented gap does not exist. Section is dead. |
| 7 | `permissions.allow`'s `pytest`/`ruff`/`mypy` patterns don't match `.venv/bin/*` | **REPO**, fixable, diff in §C | Confirmed the literal patterns: `Bash(pytest:*)`, `Bash(ruff:*)`, `Bash(mypy:*)` (prefix-matched against the command string). `.venv/bin/pytest -q` does not start with `pytest`, so it does not match. **Nuance the source docs didn't note:** `Bash(make check:*)` *does* match a bare `make check` invocation, which internally runs `$(VENV)/bin/pytest` etc. — so a full-suite run via `make check` is unaffected. The gap is real only for a **direct, narrower** invocation (`.venv/bin/pytest -k some_test`), which is the common case when iterating on one failing test. |
| 8 | MCP server IDs rotate mid-session; static allowlist/frontmatter stop matching | **HARNESS** | **Reproduced live, unprompted, while investigating it.** `mcp__supabase-ro__execute_sql` was listed as a deferred tool at conversation start; by the time I called it, the server had disconnected and reappeared as `mcp__9d7520d7-9986-4699-9d4a-ee0fcc9bf4d6__execute_sql` (confirmed via the tool-availability notice: *"mcp__supabase-ro__* (4) [is] no longer available (MCP server disconnected)"*). Zero code or config changed between the two states. `permissions.allow` allowlists the literal string `mcp__supabase-ro__execute_sql` (`settings.json:4`) — it stopped matching, with no warning, no error; the call simply required a fresh permission prompt under the new name. This is the third independent instance of the R5/R16/R17 defect class, now including my own session. |
| 9a | Agent frontmatter declares the DB tool statically, can't track a rotation | **HARNESS** (no fix surface exists) | Read five agent frontmatters. `thesis-coherence-guard.md:4` already lists **two** names (`mcp__claude_ai_supabase-ro__execute_sql`, `mcp__supabase-ro__execute_sql`) — evidence of a prior attempted mitigation. Neither matches a UUID. Claude Code agent `tools:` frontmatter has no wildcard or dynamic-resolution syntax that I could find or verify; I could not confirm a fix surface exists at all, in the repo or in the harness's documented config. Flagged as unresolved, not fabricated. |
| 9b | Read-only agent DB role (`asxos_agent_ro`) is inert | **ENVIRONMENT** (infra — Supavisor connection string, outside repo files) | **Re-verified live, independently, this session:** `SELECT current_user` via the (rotated-UUID) MCP tool → `supabase_read_only_user`, not `asxos_agent_ro`. Exactly reproduces the 2026-08-22 finding, from a fresh query I wrote myself. `supabase_read_only_user` is a Supabase-managed role; nothing in this repo's files controls which role the MCP session authenticates as — that is an out-of-repo connector/connection-string setting. Plausible to complete without exposing a credential *to a session*, if the Supavisor connection string is set at the MCP connector's own config surface rather than pasted into a prompt or a repo file — but I cannot confirm where that surface lives from inside this session, so treat this as "likely, not verified." |
| 10 | MCP write tools (e.g. migration apply) always prompt; fatal for unattended runs | **REPO — deliberate, correct, and only half-configurable** | `unattended-guard.sh:340-345`: when `ARBI_UNATTENDED=1`, any `mcp__supabase__*`/`mcp__Supabase__*` call (the write-capable server) is hard-denied mechanically, unconditionally — *"Writes/migrations are reserved to James."* This is **not configurable** from any session, by design, and is the correct behaviour (it is rule #11 / capital-safety adjacent). For an **attended** session (no `ARBI_UNATTENDED`), it is technically configurable — adding the exact tool name to `permissions.allow` would stop the prompt — but doing so would remove human review from a migration-apply action, which is not advisable and is not recommended here. |
| 11 | `.github/**` and `migrations/**` are Edit-denied to this (interactive) session | **REPO — deliberate, load-bearing, per path** | Both are explicit `Edit(...)` deny entries (`settings.json:68-69`) and explicit directory-prefix fragments in `authority-guard.sh` (`:63`), covering the Bash-interpreter/redirect route too. `docs/product/arbi-permission-model.md:275-290` documents this as intentional and previously *tuned*: an earlier broad `.claude/**` deny caused a self-inflicted lockout (arbi-run-ledger, 2026-07-14) and was deliberately narrowed to name `.github/**`/`migrations/**` explicitly, not loosened. `.github/**` guards CI/scheduling and — critically — `claude-execute.yml` itself (letting a session edit its own dispatch-authority workflow would be a real self-escalation path). `migrations/**` guards schema changes reaching production. Neither reads as precaution that has outlived its cause; both are load-bearing for the stated reason. |
| 12 | `claude-execute.yml` (the unattended-in-CI harness) may edit workflow/migration files where this session cannot | **UNRESOLVED — could not verify either way** | `claude-execute.yml:144`'s `--allowedTools` string grants unrestricted `Edit,Write` with **no path scoping baked into the flag itself**, and its own runbook (`docs/product/runbooks/claude-execute.md:26-29`) authorises the dispatched run to *"edit code, documentation, and configuration needed for the task"* without carving out `.github/**` or `migrations/**` — only specific *actions* (credentials, destructive DB, direct push to `main`, PR merge, migration `0042` specifically named, Model A) are named as stop conditions, which by contrast implies authoring *other* migration files or workflow edits is in scope. What I could **not** verify: whether `anthropics/claude-code-action@v1` loads and honours the checked-out repo's `.claude/settings.json` deny array inside a GitHub Actions run, or operates purely off the `claude_args` flags. I did not dispatch the workflow to test this (out of scope per this task's constraints — a live run does real, scoped work). If settings.json's deny *does* apply there too, the asymmetry in row 11 doesn't actually exist in practice; if it doesn't, the indirect path is real and is the one place in this repo's current tooling where `.github/**`/`migrations/**` edits are authored, reviewed only via the resulting draft PR. Recommend James check a past `show_full_output` debug-mode run log, or the action's own source, rather than assume either direction. |
| 13 | `detect_theme_stages` has no current scheduling | **REPO** (needs `.github/workflows/**`, Edit-denied — see row 11) | `jobs/detect_theme_stages.py` exists. `grep -rn detect_theme_stages .github/workflows/` → no matches in any of the 10 current workflow files. Confirmed unscheduled today; did not independently verify the "since ~2026-08-12" date, which isn't load-bearing to the finding. |

### Note on row 1 and row 2 — why I didn't just try the denied write

For row 2, I verified the block by reading the enforcement code (the settings deny array plus
`authority-guard.sh`'s Bash-redirect/interpreter checks) rather than by attempting an actual
`Write` to `.claude/settings.local.json`. That's a deliberate choice: the task constraints say not
to edit a denied path, and the code is unambiguous — every plausible route (`Edit`/`Write` tool,
Bash redirect, Bash `tee`, a Python `open()` call) is covered by one of the two layers. Attempting
it would have added no certainty and risked exactly the outcome the constraints rule out.

For row 1, I *did* run the actual command, because `.claude/.review-passed-*` markers are
explicitly *not* an authority path (`authority-guard.sh:56-58`: *"loose root-level markers are
INTENTIONALLY absent from this list and MUST remain writable"*) — there is no rule anywhere that
this touch should be denied, which is exactly the finding. It succeeded. That doesn't prove the
2026-08-22 session's repeated denials didn't happen — I have no way to reproduce a negative from
here — but it does rule out "there is a standing rule against this path," which was one of the two
live hypotheses. What's left is: the outcome for an *unlisted* Bash command depends on ambient
session/permission-mode behaviour that isn't visible in any repo file, which is unfixable from
here by definition — and is exactly why an explicit allow-list entry (removing the command from
"unlisted" to "always allowed") is the correct fix regardless of the exact mechanism.

---

## B. Ranked fix list

Ordered by effort, cheapest first — the cheap ones dominate expected value here because every one
of them is currently costing entire sessions their execution budget.

| Rank | Fix | Effort | Expected effect | Class |
|---|---|---|---|---|
| 1 | Add `Bash(touch .claude/.review-passed-*)` to `permissions.allow` | **1 line** | Makes every future Python commit's review-gate step deterministic instead of a coin-flip. This is the fix that would have let the 2026-08-22 session ship both its code units without four rounds of retry. | REPO |
| 2 | Drop the dead `curl …api.render.com…` grant (Render deleted 2026-08-12) | **1 line delete** | Removes a live-credential grant with no remaining use. | REPO |
| 3 | Extend `authority-guard.sh`'s redirect scrub to fd-duplication (`2>&1`, `1>&2`, …), not just `/dev/null`/`/dev/stderr` | **~3 lines** | Fixes the false positive I reproduced live (row 3) plus the two from 2026-08-21 that Fix A already covered. Read-only commands stop being denied for incidental stderr handling. | REPO |
| 4 | Fix `Makefile`'s `PY` default to resolve a real interpreter instead of a hardcoded absolute path | **1 line** | `make install`/`make check` work on first try in this sandbox instead of failing on a missing binary. | ENVIRONMENT/REPO |
| 5 | Add `.venv/bin/pytest`, `.venv/bin/ruff`, `.venv/bin/mypy` (or `.venv/bin/*`) to `permissions.allow` | **3–4 lines** | Removes prompts for the exact commands an installed sandbox actually runs when iterating on a single test/file rather than the whole suite via `make check`. | REPO |
| 6 | Delete CLAUDE.md's "Known test environment gaps (do not chase)" section | **1 deletion** | Stops future sessions burning time chasing a gap that PR #144 already closed. At minimum this session and the 2026-08-22 session both had to re-derive this from scratch; likely more, per that doc's own note that the affected-file list "rotted from 4 → 14 → 16" while still being trusted. | REPO |
| 7 | Add a `SessionStart` hook that runs `make install` (or the equivalent venv-build) before the first turn | **~15–30 min to author + test** (one-time; the `session-start-hook` skill exists in this environment for exactly this) | Removes rows 4/5/6/7 as a *class* — no session would start without `.venv` again. Requires a `.claude/settings.json` hooks-block edit, so it is gated behind the same Edit-deny as everything else in this list; James applies once, benefits every future session indefinitely. | ENVIRONMENT (fix) / REPO (mechanism) |
| 8 | Schedule `detect_theme_stages` in a workflow file | **~10 lines of YAML**, but blocked — `.github/**` is Edit-denied (row 11, by design) | Restores a built mechanism that currently has no trigger. Requires either a hand-edit by James or routing through `claude-execute.yml` once row 12 is resolved. | REPO, gated |
| 9 | Complete the Supavisor repoint to `asxos_agent_ro`, then REVOKE the frozen Model A surface | **Infra step, unknown effort — outside repo files** | Makes the read-only agent role load-bearing for the first time since `0039` merged; makes rule #11's mechanical control real rather than nominal. | ENVIRONMENT, James-only |
| 10 | Pin/verify a stable MCP server alias for Supabase read access | **Unknown — depends on what the connector surface allows** | Would remove row 8/9a as a class. No evidence a repo-side fix exists; this is the one item where the honest status is "investigate the platform side," not "here is a diff." | HARNESS, unresolved |

Items 1–6 are all one-to-few-line diffs. None of them touches what the review gate, the authority
guard, or the Edit-deny list actually protect — they remove false friction, not real friction.

---

## C. Exact diffs — drafted, not applied

All four target Edit-denied files. Presented as diffs for James to paste directly.

### C.1 — `.claude/settings.json`

Three independent changes to `permissions.allow`, plus one deletion. Applying only the touch line
(C.1a) is sufficient to fix Rank 1; the others are batched here since they're all in the same
denied file and the marginal review cost of doing them together is near zero.

```diff
--- a/.claude/settings.json
+++ b/.claude/settings.json
@@ permissions.allow, after "Bash(git push:*)"
       "Bash(git push:*)",
+      "Bash(touch .claude/.review-passed-*)",
+      "Write(.claude/.review-passed-*)",
       "Bash(pytest:*)",
       "Bash(python -m pytest:*)",
       "Bash(python -m py_compile:*)",
       "Bash(python3 -m pytest:*)",
       "Bash(python3 -m ruff:*)",
       "Bash(ruff:*)",
       "Bash(mypy:*)",
+      "Bash(.venv/bin/pytest:*)",
+      "Bash(.venv/bin/ruff:*)",
+      "Bash(.venv/bin/mypy:*)",
       "Bash(make check:*)",
@@ permissions.allow, drop the dead Render grant (Render deleted 2026-08-12, commit 59fb835)
-      "Bash(mkdir:*)",
-      "Bash(curl -s --max-time 25 -H \"Authorization: Bearer $RENDER_API_KEY\" \"https://api.render.com/v1/:*)"
+      "Bash(mkdir:*)"
```

`Write(.claude/.review-passed-*)` is included alongside the `Bash(touch …)` rule because the
2026-08-22 session reported denials on *both* tool paths — belt-and-suspenders, since either one
alone should now be deterministic, but there's no reason to leave the other exposed to whatever
ambient behaviour caused the original denials.

### C.2 — `.claude/hooks/authority-guard.sh`

Extends the redirect-target scrub the 2026-08-21 proposal already drafted (as unapplied "Fix A")
to also strip fd-duplication redirects (`2>&1`, `1>&2`, …), which is the trigger I reproduced live
this session. Insert after `cmd` is read (currently line 214):

```diff
--- a/.claude/hooks/authority-guard.sh
+++ b/.claude/hooks/authority-guard.sh
@@ -213,6 +213,10 @@ case "$tool" in
   Bash)
     cmd="$(printf '%s' "$payload" | jq -r '.tool_input.command // empty')"
     [ -n "$cmd" ] || exit 0
+    # Scrub redirects that cannot target an authority path by construction:
+    # /dev/null|/dev/stderr targets, and fd-duplication forms (2>&1, 1>&2, …).
+    # A pure read that happens to redirect stderr must not trip the write-verb
+    # test below (permission-and-guard-friction-2026-08-21.md Fix A, extended).
+    cmd="$(printf '%s' "$cmd" | sed -E 's#[0-9]*>>?[[:space:]]*/dev/(null|stderr)##g; s#[0-9]*>&[0-9]##g')"
     # Interpreter-based writes (the docs-confirmed gap): python/perl/ruby/node opening a
```

This keeps every genuine write trigger intact — `echo x > CLAUDE.md` still matches (its redirect
target is neither `/dev/null` nor an fd), and the interpreter/`cp`/`mv`/`tee` checks are untouched.

### C.3 — `Makefile`

```diff
--- a/Makefile
+++ b/Makefile
@@ -1,6 +1,6 @@
 .PHONY: help install dev decision-demo test lint type format check migrate shell logs deploy check-drift clean

-PY ?= /usr/local/bin/python3.12
+PY ?= $(shell command -v python3.12 2>/dev/null || echo python3.12)
 VENV ?= .venv
 ACTIVATE = source $(VENV)/bin/activate
```

Resolves whatever `python3.12` is actually on `PATH` (`/usr/bin/python3.12` in this sandbox,
`/usr/local/bin/python3.12` wherever that's the real location) instead of a hardcoded absolute
path that doesn't exist here. Falls back to the bare name (which then fails with a clear "command
not found" from `venv` itself, rather than this Makefile's own silent wrong-path failure) if
`python3.12` isn't on `PATH` at all.

### C.4 — `CLAUDE.md`

Delete the entire "Known test environment gaps (do not chase)" section (the block beginning `##
Known test environment gaps` and ending immediately before `## Known coverage gaps`). It describes
an import chain PR #144 deleted; the two remaining `joblib` mentions in the whole tree are a test
docstring guarding against its reintroduction, not a live gap. Also update line 40
(`REQUIRED_MIGRATIONS = 96`) — re-verified live this session: production is at **97** applied
migrations (latest `20260821080458`), matching the still-unmerged fix on PR #154. Both edits are
docs-only in effect but the file itself is Edit-denied, hence a diff rather than an applied change:

```diff
--- a/CLAUDE.md
+++ b/CLAUDE.md
@@ (the "Read first" bullet listing migrations)
-**`migrations/` (currently through 0043; `REQUIRED_MIGRATIONS = 96`) is the canonical schema**
+**`migrations/` (currently through 0044; `REQUIRED_MIGRATIONS = 97`) is the canonical schema**
@@
-## Known test environment gaps (do not chase)
-
-Some tests permanently collection-error in the remote Claude Code sandbox because
-`joblib` (transitively `lightgbm` / `sklearn`) is not installed in the sandbox Python
-env, ... [entire section through the closing bullet about test_train_walk_forward.py]
-
 ## Known coverage gaps (verify, don't assume)
```

**Do not apply this diff verbatim without checking the exact current migration filename for
"0044"** — I did not enumerate `migrations/` past what's already documented; the number is from
the live `count(*)` query (97), not from reading every filename. Confirm the top filename in
`migrations/` before committing this line.

---

## D. The structural question — does the friction bias toward prose over code?

**Yes, measurably, and the counter-hypothesis explains a real but minority share of it.**

### The ratio, beyond the one session

Classified all 30 of the most recent merged commits on `main` (each is one squash-merged PR) by
file type touched:

- **19 of 30 (63%) touch zero `.py` files** — pure docs/governance/memory commits.
- **11 of 30 touch `.py`** — of these, **4 are the `results_review` PRs** (#113/#115/#119/#122)
  independently reconfirmed this session to have **zero DB access**
  (`grep -rn "asyncpg\|acquire(\|SELECT " asxos/domain/results_review/` → no matches, exit 1).

So even within the "code" bucket, over a third landed with no live-data path at all. That's not a
one-session artifact — it's the standing shape of the last several weeks of merges.

### Why: Amendment E exists because of exactly this pattern

`docs/product/roadmap-state.md:207-225`: Amendment E was ratified 2026-08-20 specifically because
units were closing "correct and empty" — passing tests, shipping clean code, rendering nothing
against live data. The four `results_review` PRs are named in the ratification text itself as the
motivating case. This is not a new theory; it's the documented reason a governance rule already
exists.

### The counter-hypothesis, tested against a live query

Ran directly against production (read-only, no `signals` table):

| Table | Row count |
|---|---|
| `holding_lots` (open) | **1** |
| `holding_lots` (disposed) | **0** |
| `themes` | **1** |
| `theme_holdings` | **1** |
| `screening_runs` | **0** |
| `theses` | **13** |
| `macro_theses` | **4** |
| `agent_runs` | **4** |
| `portfolio_daily_snapshots` | **56** |

The thin-substrate claim is **true for exactly the lanes it was claimed for** — disposal/CGT work
(0 disposals) and screening-rule work (0 screening runs) would legitimately close empty right now,
independent of any permission. But it is **not thin across the board**: 13 live theses, 4 macro
theses, 56 portfolio snapshots is real, non-trivial substrate that code work could target and
render against today.

Quantifying against the one session with a full accounting: the 2026-08-22 handoff records that
of arbi's eight planned units, **3 were closed before work began by a live probe** — CBA
automation already shipped, the tax unit would close empty at 0 disposals, and
`detect_theme_stages` was unreachable. Of those three, only **2** (the tax unit, and arguably CBA)
are genuinely data-thinness; the third (`detect_theme_stages`) is the `.github/**` Edit-deny (row
11 above), a permission finding wearing a data-thinness label. The remaining **5 of 8** units were,
per that handoff's own "Not done, and why" section, *"displaced by the permission friction, which
consumed most of the session's execution budget."*

**Answer:** the counter-hypothesis accounts for roughly a quarter to a third of any single
session's shortfall (2–3 of 8 units in the one case with a full accounting), concentrated in two
specific lanes (disposals, screening). It does not explain the 63% docs-only rate across 30 merged
PRs — most of those are governance/roadmap/memory documents with no relationship to whether
`holding_lots` or `theses` had rows in them. That rate is better explained by the asymmetry itself:
a doc commit has never once, in the material reviewed, hit a gate, a classifier, or an Edit-deny;
a Python commit reliably hits at least the review-gate marker step, and as of 2026-08-22 that step
was not reliable. Effort routes toward the path that reliably finishes.

---

## E. A monthly measurement

Three cheap, repeatable checks — none require write access, none touch `signals`. Run all three
and compare month over month; the friction question resolves itself once there's a second data
point.

**1. Doc-vs-code ratio over the last 30 merged commits on `main`:**

```bash
for c in $(git log --oneline -30 main | cut -d' ' -f1); do
  files=$(git show --stat --format="" "$c" | grep -v "files\? changed" | awk '{print $1}')
  py=$(echo "$files" | grep -c '\.py$')
  echo "$c py=$py"
done | awk '{split($2,a,"="); if (a[2]=="0") docs++; else code++} END {print "docs-only:", docs, " touches-py:", code}'
```

**2. Zero-DB-access check on any package under active development** (generalizes the
`results_review` check — swap the path):

```bash
grep -rln "asyncpg\|\.acquire(\|SELECT " asxos/domain/<package>/ || echo "<package>: zero DB access"
```

**3. Friction log + live substrate, together, so a low PR-code-rate can be read against whether
there was anything to build against that month:**

```bash
# friction proxy — DENY rows in the permission log (rotate/archive this file monthly to keep the count meaningful)
grep -c '^DENY' .claude/permission-requests.log 2>/dev/null || echo 0

# substrate proxy — same query used in this audit, minus the signals table (rule #11)
# SELECT (SELECT count(*) FROM holding_lots WHERE disposed_at IS NULL) AS open_lots,
#        (SELECT count(*) FROM holding_lots WHERE disposed_at IS NOT NULL) AS disposed_lots,
#        (SELECT count(*) FROM themes) AS themes, (SELECT count(*) FROM theses) AS theses,
#        (SELECT count(*) FROM screening_runs) AS screening_runs,
#        (SELECT count(*) FROM portfolio_daily_snapshots) AS snapshots;
```

A rising code-touch share with a flat or rising substrate count is the friction thesis losing; a
flat code-touch share with a rising substrate count (more to build against, same output) is it
winning.
