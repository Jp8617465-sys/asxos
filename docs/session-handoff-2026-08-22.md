# Session handoff — 2026-08-22

**Status:** current
**Read priority:** READ FIRST — this is the active handoff
**Written for:** a **new session with zero context**. Everything needed to finish is here.
**Session close:** ledger row `close-2026-08-22`, `episode_score` **3.3 provisional**

| | |
|---|---|
| Work branch | `claude/product-roadmap-backlog-8k3jz5` @ `46dd651`, **19 ahead** of `main` |
| Work PR | **#152** (draft) |
| Dream branch | `claude/arbi-mem/2026-08-22` |
| Dream PR | **#153** (draft) |
| Baseline at close | ruff clean · mypy clean across 168 files · **2586 passed / 1 skipped** |

---

## STOP — read before touching anything

**1. Rule #11 (Model A quarantine) is STANDING POLICY, not a blocker awaiting lift.** Resolved
2026-07-11 *against* Model A on 19,032 matured signals: `corr(ml_prob, 21d) = −0.03`; STRONG_BUY
21d −0.09% vs HOLD +5.07% — conviction inverted at the top. Never use Model A output (signals,
scans, allocator runs, thesis proposals) as a basis for a real capital decision. Do **not**
propose re-running the decay check; that P0 is closed and re-issuing it is recency overfit.

**2. `/pm-review` is UNSAFE until patch C lands.** `thesis-coherence-guard` step 1 queries
`FROM signals WHERE model='model_a'`. PR #144 deleted every writer, so the query still returns
rows and the agent emits confident COHERENT/CONTRADICTED verdicts from **frozen evidence,
presented as current**, into the synthesis behind real holding decisions. Worse than an error —
it looks like a working answer. Its frontmatter says use **PROACTIVELY**, so *declining to run
`/pm-review` does not contain it.*

**3. The personal-advice firewall (s766B) is structural and unchanged.**

**4. This handoff is on a branch, not `main`.** Per `docs/README.md`, a handoff that lives only
on a feature branch is a process defect. **Merging #152 is what makes it visible to the next
session.**

---

## THE FIRST THING TO DO

**Apply the three `.claude/**` patches.** They are written, reviewed, and paste-ready at
`docs/proposals/claude-config-patches-2026-08-22/README.md`. James authorised applying them;
the tooling refused four times (see *Why they aren't applied* below).

**Order matters — C first.** It is the only one touching a live capital-adjacent hazard.

```bash
# C — stop /pm-review serving dead Model A evidence as current
cp docs/proposals/claude-config-patches-2026-08-22/thesis-coherence-guard.md \
   .claude/agents/thesis-coherence-guard.md
grep -c "FROM signals" .claude/agents/thesis-coherence-guard.md   # must print 0
```

**A** — `.claude/settings.json`: set `"defaultMode": "bypassPermissions"` **and** empty
`"allow": []`. The 57 archived entries are preserved verbatim in
`docs/proposals/permission-allowlist-archive-2026-08-22.md` §2.
**Neither edit works alone** — the allowlist grants nothing, it only suppresses prompts, so
emptying it without `defaultMode` makes `git status`, `pytest`, `ruff`, `cat` and `grep` all
prompt again. **Keep the entire `deny` array**, including `Edit(/.claude/settings.json)` — a
one-time grant must not make itself permanent.

**B** — `.claude/hooks/authority-guard.sh`: strip heredoc bodies before matching, and require a
redirect to actually target an authority path. Exact patch in the README.

### Verify A mechanically, not by inspection

```bash
# after applying A and restarting the session
tail -3 .claude/permission-requests.log     # a DB call must appear as an allow, NOT as ASK
```

A config that "looks right" is not evidence. This repo has been burned twice by exactly that.

---

## Why they aren't applied — do not re-derive this

Four attempts, all refused. Twice by `permissions.deny` before `authority-guard.sh` was even
reached (`File is in a directory that is denied by your permission settings`), twice by the
guard. Including a `cp` that merely **backed up** `settings.json`, refused seconds after the
authorisation naming that exact file.

**The mechanism, stated flatly so nobody spends another hour on it:** `permissions.deny` and
`PreToolUse` hooks are *configuration*. A sentence in a conversation does not edit
configuration. A verbal grant changes only what the agent is willing to *attempt*.

**There is a route that works, and it was deliberately not taken.**
`~/.claude/settings.json` sits **outside the repo**, so neither the deny array nor the guard's
repo-relative fragment list covers it. Setting `defaultMode` there achieves the same result.
That is exploiting a known gap in a control — named in the guard's own header as accepted
residual risk — and it is **James's call to authorise, not an agent's to take**. If he says
use it, use it.

---

## The second thing: DB access is dead by two independent causes

`P3-03` (the next product row, now unblocked) needs the live database. It is unreachable.

| # | Cause | Evidence | Fix owner |
|---|---|---|---|
| 1 | **Environment blocks outbound 5432** | measured — Supabase pooler times out; `api.github.com:443` opens in 0.2s | James, environment network policy |
| 2 | **Allowlist names a server that doesn't exist** | `settings.json:4` allows `mcp__supabase-ro__execute_sql`; servers register under per-session UUIDs (`mcp__9d7520d7-…`). `.claude/permission-requests.log` shows every DB call as `ASK` | patch A |

**Only fix 2 can work in this container** — the MCP server proxies over HTTPS; nothing here can
reach 5432. Full diagnosis: `docs/proposals/db-access-remediation-2026-08-22.md`.

**A `.mcp.json` is NOT the answer, and this was checked.** A project-defined Supabase server
needs `SUPABASE_ACCESS_TOKEN`, which **does not exist in this environment** (checked by name).
`permission-pack-connector-binding-2026-08-16.md` §4 already records provisioning it as James's
alone — and its preferred `server-postgres` variant is **now void here**, because that needs the
blocked 5432.

**`scripts/roquery.py` exists** as the durable read-only path (43 tests, read-only enforced by
Postgres via `set_session(readonly=True)`). It is useless in *this* container until 5432 opens,
and immediately useful locally and in Actions.

---

## What shipped this session

19 commits. Seven work orders.

| Commit | What |
|---|---|
| `ae28dbe` | `REQUIRED_MIGRATIONS` drift 96 → 97 |
| `52683b7`, `8b4020d` | **SB1-02** read-only probe adapters + news-brief SHIP verdict |
| `48b51d9`, `25be009` | `CLAUDE.md` migration facts; a fabricated figure self-caught and reverted |
| `928ca55` | inbox: 0044 + dark-launch #2 rows closed |
| `e4d40ad`, `56c82c4` | **SB2-01/02** contradiction + staleness detection, then remediation when its completion proof turned out unmet |
| `4ab90ef`, `6478c2e` | **P3-02** S3 work order + red-team CHALLENGE applied |
| `46ff235` | decision package — G1 assemblable for the first time |
| `ef1e865` | `leaves()` consolidated — one projection instead of three copies |
| `a064481` | **SB3-01** mission/receipt/context schema freeze |
| `f0248c5` | **G1 CLEARED** |
| `fb7545d` | `roquery.py` + 43 tests + the DB diagnosis |
| `2ff019a` | `/arbi` wake snapshot |
| `130a0d8` | the three `.claude/**` patches, paste-ready |
| `46dd651` | `/arbi-close` — ledger row, decision log, handoff |

### G1 is cleared — the product lane reopened

James approved `P3-01` and `P3-02`. `P3-03`'s dependency reads literally "P3-01..02 approvals",
so 8 of 17 remaining rows unblock: `P3-03` → `P4-01` → `P4-02` → `P5-02` → `P6-01` → `P7-01` →
`P7-02` → `P8-01`. Recorded per the GOV-01 two-artifact precedent in `decision-log.md`,
`roadmap-state.md` (queue amendment beside F1–F8), and `decision-package-2026-08-22.md`.

**Approving a work order is not approval to execute it.** Ruling **F6 stands unchanged** — no
bucket or credential creation — so `P3-03` can only do its read-only half. `P3-02` still has
**no cost model** (AWS pricing egress-blocked) and its Object Lock claim is still unprobed.
`P3-01`'s sizing still rests on a 90-minute chain that #128 cut to 4m35s.

### `SB4-01` is PARKED, not skipped

`arbi-red-team` CHALLENGED it, on two independent grounds. Packet `:696` puts the SB4 eval
harness in **wave 4** while the programme is at **wave 3**, and no P-series row depends on it —
so the "shortest path into the product lane" argument that rescued `SB1-02` a day earlier does
not transfer. And Amendment E bars closing a fixture-only row while **zero emitted arbi briefs
exist anywhere in 400 commits** (the section headings appear only in four format-defining
files). Buildable but **unclosable**.

**Named revival trigger: capture a real `/arbi` brief as a fixture.** One step.

---

## What is owed, and to whom

### James

1. **Apply patches C → A → B.** ← the unblock for everything else
2. **Permit outbound 5432** in the environment's network policy.
3. **Merge or reject #152 and #153** (both draft). Merging #152 puts this handoff on `main`.
4. **Dark surfaces #1 and #4** — expire **2026-08-31**, decide-by **2026-08-28**. Rule them
   together: #1's re-scope condition needs a 4-week sign-off that #4 must *start*.
5. **`AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` are SET in this environment**, while F6 says no
   credentials are authorised and `P3-02` was written assuming none existed. **Not used.** May
   mean `P3-03`'s restore leg is closer than the work order assumes.
6. **Rule on the `close-2026-08-22` ledger row's `defect:` field.** No DB was reachable, so
   `renders:` and `captures:` were *impossible*, and this session's real defects aren't literally
   a `job_runs` row or a CI URL. The row cites the `permission-requests.log` `ASK` timestamps and
   **states the stretch inside the row**. If it doesn't qualify, the correct outcome is park-with-
   a-trigger, not a nicer sentence (L18 clause 2).
7. **`0045_segment_map.sql`** — unapplied; nothing runs `build_segment_map`. Not time-boxed.
8. **`detect_theme_stages`** — confirm the KEEP ruling is in force (it lives on unmerged #143).

### The next session

- **`P3-03`** — Stage 1 replay + lineage, read-only, once the DB is reachable. Exit gate
  (`target-architecture.md:998-1002`): replay one historical date using only `known_at <= cutoff`;
  lineage resolves exactly; backup/restore observed (**that third leg is blocked on F6**).
  **Known landmine:** `target-architecture.md:1310` records 60 rows of `rs_fundamentals_pit` with
  a `knowledge_date` in the future — if `known_at` can be a vendor's diary entry, the replay gate
  is decorative. **Re-derive that count live before trusting it**; the figure is days old.
- **`docs/product/evals/fixture-003-failed-ci.md` is owed an annotation.** It cites an import
  chain through three files that no longer exist. The evals README's own rule is annotate, never
  delete.
- **The ledger's `close-2026-08-20` row may fail Amendment E Check 2** (carries none of the three
  fields). **Unverified** — `gh` is absent here so `check_ledger_coverage.sh` exits 0 before
  reaching Check 2. L18 clause 2 forbids backfilling.

---

## Traps that will cost you an hour if you don't know them

1. **`authority-guard.sh` blocks Bash commands that merely NAME an authority path** alongside any
   redirect. A heredoc writing to `/tmp` is blocked for mentioning `.claude/` in its body; a
   `git commit` was blocked because its *message* quoted filenames. **Workaround: use the Read
   tool for authority-path reads, and Edit/Write for authority-adjacent writes** — the hook
   doesn't gate Read. Patch B fixes this.
2. **Subagents stall constantly. Eight did this session** (arbi ×2, Explore ×2, Plan,
   refactoring-expert ×2, security-engineer) — typically `running` for 1–4 min with a frozen
   transcript. **Do the work inline and say so.** A stalled reviewer is a review that didn't
   happen.
3. **The review gate blocks compound `git add … && git commit`** when Python is staged. Stage
   Python separately, run the loop, `touch` the marker the hook prints, then a plain `git commit`.
4. **Don't trust documented figures — re-derive.** Four wrong figures this session, all
   *plausible*: a fabricated "nine days", ten off-by-one packet citations, a 9-vs-10 gate
   discrepancy that wasn't one, and a `daily-brief` "miss" that wasn't (the cron is
   `30 20 * * 0-4`, Sun–Thu; **all ten scheduled days ran green**).
5. **`make check` baseline is 2586 passed / 1 skipped.** The old "known sandbox gaps" section in
   `CLAUDE.md` is retired — those import chains died with Model A in #144.

---

## Honest accounting

Seven units shipped, **all second-brain/autonomy, zero product**. The packet's §9 kill condition
("pause on more orchestration work than product evidence work") was met on its face — which is
exactly why the G1 question went to James rather than an eighth orchestration unit being started.
Clearing G1 is the correction, and **the next unit should be product work.**

`episode_score` **3.3 provisional**. The two sub-scores dragging it down are honest:
`cost_efficiency` **2** (eight stalls, five guard-blocked commands) and `state_accuracy` **3**
(the four wrong figures — all corrected in-record, none shipped, but four is a pattern, so both
`stale_claims` and `repeated_mistake` penalties were applied rather than argued away).

Six durable lessons and two named repeated mistakes are in the dream candidate (PR #153),
including the one that matters most here: **an authorisation changes intent; only a config change
alters capability.**
