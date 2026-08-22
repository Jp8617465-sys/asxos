# Session handoff — 2026-08-22

**Status:** current
**Read priority:** read first
**Supersedes:** `docs/session-handoff-2026-08-21.md`
**Dream:** `claude/arbi-mem/2026-08-22` — **draft PR #153** (held; shares 18/20 commits with #152)
**Read next:** `docs/proposals/db-access-remediation-2026-08-22.md` — DB reach still James's.

## STOP — read first

**Rule #11 (Model A quarantine) is STANDING POLICY, not a blocker awaiting lift.** Resolved
2026-07-11 against Model A on 19,032 matured signals: `corr(ml_prob, 21d) = −0.03`, STRONG_BUY
21d −0.09% vs HOLD +5.07%. Never use Model A output — signals, scans, allocator runs, thesis
proposals — as a basis for a real capital decision.

**`/pm-review` is unsafe until patch C lands.** `thesis-coherence-guard` step 1 queries
`signals WHERE model='model_a'`; PR #144 deleted every writer, so it returns **frozen Model A
evidence presented as a current answer** into holding decisions. Its frontmatter says use
PROACTIVELY, so declining to run `/pm-review` does **not** contain it. The fix is drafted and
unapplied at `docs/proposals/claude-config-patches-2026-08-22/thesis-coherence-guard.md`.

**The personal-advice firewall (s766B) is structural and unchanged.**

## What James must do (nothing below is arbi's)

1. **Apply the three `.claude/**` patches** — `claude-config-patches-2026-08-22/README.md`.
   **C first**: it is the only one touching a live capital-adjacent hazard.
2. **Permit outbound 5432** in the environment's network policy. Independent of the repo.
3. **Merge or reject #152 and #153.** Both draft.
4. **Dark surfaces #1 and #4** — expire 2026-08-31, decide-by **2026-08-28**. Rule them together.
5. **`AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` are set in this environment**, while F6 says no
   credentials are authorised and `P3-02` was written assuming none existed. Not used. May mean
   `P3-03`'s restore leg is closer than the work order assumes.
6. **Rule on the `close-2026-08-22` ledger row's `defect:` field** — see the ledger; the stretch
   is stated in the row rather than hidden.

---

## STOP — read first

**1. Rule #11 (Model A quarantine) STANDS.** Do not use Model A output — signals,
candidate scans, allocator runs, or new thesis proposals derived from it — as a
basis for real capital decisions. Removal still requires a **new** model clearing
a pre-registered decay bar AND earning `approved_for_allocation`.

**2. `/pm-review HUBS.NYSE` owed by #149 is OBSERVED.** Four fan-out agents, zero
Model A / `signals` figures, verdict **REVIEW**. Direct `thesis-coherence-guard`
on thesis 2: **NEEDS REVIEW** (revisit due 2026-08-03, 19d overdue). The
mechanical residual is still James's — and it is a **repoint**, not a REVOKE
against `asxos_agent_ro` (that role is inert; see §2 below).

**3. W1-1 is integration evidence, not Stage 4.** `asxos_pit_db` is a hashed
research-store snapshot. G2 (ASX announcement feed) stays closed. First honest
outcome is `abstain` with G2/G3/G5 named. Do not label PIT as an announcement
and do not label a fixture `data_mode=real`. **Merged to main as #155**
(`d7e8242`).

**4. #154's two code units are on this branch** (migration-drift asymmetry +
stop-out message). They are in the merge train after #151. Do not open a
parallel PR for either.

---

## Already on main this train

| PR | Result |
|---|---|
| **#155** | W1-1 `asxos_pit_db` path. TLS.AU FY2024 `renders:` abstain, sha256 `1224d5f35440e55eb721bba0fbb65c12d018202bf79cdb6051517f81df7baac0`. |

## This PR (#154)

Migration-drift test + `REQUIRED_MIGRATIONS` 96→97; stop-out now names the
stop (not the unused target). Review-gate allow-rule still James's
(`.claude/settings.json`).

## 1. The `REQUIRED_MIGRATIONS` unit — the test matters more than the bump

Live ledger re-measured: `supabase_migrations.schema_migrations` = **97**, latest
`20260821080458`. `asxos/api/main.py:14` read **96**.

The bump is trivial. The finding is that **nothing tested `count > REQUIRED_MIGRATIONS`** — not
an edge case but the normal state of every apply-then-bump window, since a migration reaches
production before the constant recording it can merge. The guard is deliberately
`count < REQUIRED_MIGRATIONS`; tightening it to `!=` turns each of those windows into a startup
outage, and **both existing drift tests pass under that mutation.**

Mutation-verified twice, independently (by me, and again by `security-engineer`, which copied the
tree to scratch and re-ran it).

Two docs were actively instructing a future session to break this, and are now fixed:

- `docs/audit-2026-06-27.md:163` carried an open `[bug]` line calling `count <` a defect.
  Closed as by-design, citing the test.
- The same file's `[untested] asxos/api/main.py` line is resolved.

The doc half merged first (`f021795`); the code half landed in `abc434a`, which is what makes
that audit trail true rather than aspirational.

## 2. The agent read-only role is inert — and the planned fix aimed at the wrong principal

Full write-up: `docs/proposals/agent-db-role-the-control-is-inert-2026-08-22.md`.

`asxos_agent_ro` **exists in production** (its migration file still says `DRAFT — NOT APPLIED` —
a third false header alongside `0043` and `0044`; `0045`'s DRAFT header is correct). But the
agent MCP session does not authenticate as it: `current_user` is **`supabase_read_only_user`**.

So the control has been **inert since the day it was applied** — exactly the contingency
`0039`'s own header names. `signals` remains SELECT-able: **64,189 rows**, latest `as_of`
2026-08-05.

A `REVOKE ... FROM asxos_agent_ro` — the fix the 08-21 handoff called "the only mechanical
control that would survive a prompt edit" — **would have changed nothing**, while being recorded
as rule #11's mechanical enforcement. The same closes-the-leak-in-the-report failure PR #149
caught eight days ago.

The fallback is dead too, measured not assumed: `supabase_read_only_user` has
`rolbypassrls = true` and is a member of **`pg_read_all_data`**, a built-in role granting SELECT
on every table. A table-level REVOKE cannot remove an inherited privilege; RLS cannot backstop it.

**Repointing the MCP at `asxos_agent_ro` is the only viable path.** Order is load-bearing:
repoint → verify `current_user` → then REVOKE.

## 3. The thesis trajectory message — two defects in one line

`asxos/domain/theses/discipline.py:389` interpolated `target` in **every** trajectory state and
rendered raw `NUMERIC(18,6)`:

```
HUBS.NYSE: STOP VIOLATED (current 215.170000, target 318.000000)   ← before
HUBS.NYSE: STOP VIOLATED (current 215.17, stop 230)                ← after
```

A stop-out printed the one number the classification had **not** used — an ~88-point gap on the
live HUBS thesis between the figure shown and the figure the verdict rested on. Fixed by reusing
the existing `_fmt_price` (`discipline.py:197`), already written for this and already used by
`_data_sanity`. `ABOVE_TARGET` keeps `target` — there it *is* the deciding leg.

`classify_trajectory` was already correct and is untouched.

**The review loop caught two defects that were mine, and both are worth knowing about:**

- **The sub-cent test was vacuous.** Its fixture used `0.01`/`0.02` — precisely the band where
  `_fmt_price` and a blanket `:.2f` render byte-identically — so the `:.2f` mutation its own
  docstring named **survived all seven assertions**. Found independently by `refactoring-expert`
  and `security-engineer`. Fixture is now `0.004`/`0.005` with a positive `endswith()` assertion;
  the negative form cannot express it, because `"0.004"` contains the substring `"0.00"`. All
  eight mutations are now caught.
- **A comment claimed `_data_sanity` uses `_fmt_price`. It does not** — it still interpolates raw
  Decimals (`discipline.py:249-251`) and ships `live price 168.000000 is 2.8× the recorded target
  60.000000` into the same email. The real second caller is `data_sanity_escalation`. Attribution
  corrected; the sibling defect is **recorded, not drive-by-fixed**, since routing `_data_sanity`
  through `_fmt_price` is behaviour-visible and needs its own assertion.

Also added: `directive_terms` + the surface regex are now asserted on the stop-out. It was the
module's most action-adjacent string and the only red-level message with **no** s766B vocabulary
guard — the two existing guards cover `data_sanity_escalation` and `_timeline` only.

**Correction to an earlier claim in this session:** `test_above_target_still_names_the_target` no
longer "passes either way". It now also pins the target leg's formatting, which was genuinely
broken pre-fix (`target 15.000000`), so it fails against the old code too. Its over-correction
role is instead verified by an always-stop mutation.

## 4. The owed `/pm-review` verification is still owed — and is not producible by any session

The mechanical half **passes**: zero live `FROM signals` query paths remain in `.claude/agents/`
(only historical notes and explicit prohibitions), and `/pm-review` fans out exactly **four**
agents with `thesis-coherence-guard` excluded. The amputation held.

The runtime half was blocked twice, and the second blocker is the finding:

1. The four investment-analysis dispatches were denied by the permission classifier.
2. **All five investment-analysis agents declare `mcp__supabase-ro__execute_sql` in static
   frontmatter. That MCP server disconnected and rotated to a UUID name twice during this
   session.** An agent dispatched across that boundary has **no DB tool at all** — it does not
   error, it answers from the repo or from memory.

Had dispatch succeeded, the run would have been **blind and false-clean**: four agents, zero
Model A figures, and zero evidence of anything. That is a worse artifact than none.

This is a third independent instance of the R5/R16/R17 MCP-ID-rotation defect. **The fix is
structural — a stable MCP alias or dynamic tool resolution — not a re-run.** Until then, treat
any agent output citing no live figure as "could not query", not "found nothing"; the two are
indistinguishable today.

---

## Pending, requiring James

1. **Add the review-gate permission rule** (§STOP 1) — makes Python commits deterministic instead
   of a coin-flip against the classifier.
2. **Choose the agent-DB principal and complete the Supavisor repoint** — Branch A is the only
   viable path (§2).
4. **Four false/stale headers**, all Edit-denied to agents: `0039`, `0043`, `0044` migration
   headers; `CLAUDE.md:40` (`through 0043; REQUIRED_MIGRATIONS = 96`) and its "Known test
   environment gaps" section; `docs/README.md:39` (says the live count *must equal*
   `REQUIRED_MIGRATIONS`, contradicting the now-pinned asymmetry).
5. **Three dark-launch surfaces expire 2026-08-31 — decide by 2026-08-28.** Six days. Unchanged
   from the 08-21 handoff and still nobody's.
6. **Production DB writes** — deliberately not taken despite a full-autonomy grant, because they
   are judgments about real money, not engineering: `timeline_days` 365→366 on thesis 2 (moves a
   CGT discount date), the Q2 falsifier adjudication (19 days overdue), the `snapshot_portfolio`
   backfill (56 rows), and the A$701 HUBS acquisition-FX question.
7. **Is HUBS's 230.00 stop a raised trailing stop or a data-entry error?** It sits *above* the
   187.54 entry. A trailing stop is the benign reading and the one the pending validator design
   assumes. Only James knows. It gates the "false `STOP_VIOLATED` on 77% of sessions" claim.

---

## Found in passing, not in any diff — worth its own look

`jobs/compose_brief.py:97` does an unconditional `print(html)` of the **entire brief** —
holdings, thesis ladder, stops and targets — and that is the run log of
`.github/workflows/daily-brief.yml:103`. If `Jp8617465-sys/asxos` is a public repository, every
Actions run log is world-readable and this is a standing financial-PII exposure far larger than
anything in this session's diff. Repository visibility could not be verified from the sandbox
(`gh` absent; `api.github.com` 403s at the proxy). **Check the repo's visibility; if public, this
is urgent.** Surfaced by `security-engineer` while reviewing the trajectory change.

Adjacent, and it corrects the s766B coverage map: `asxos/domain/position_monitor/service.py:117`
emits `f"Price breaks below ${inputs.stop_price} on volume → exit"` — a literal `exit` beside a
stop price, on a surface with no `directive_terms` guard at all. Narrower blast radius (CLI, not
the brief), pre-existing, but it means the discipline module is *not* the system's most
action-adjacent stop-out string.

---

## Not done, and why

Units 6 (open-time thesis price-ordering validator), 7 (memory-gap brief line) and 8 (V2 brief
descope) were scoped and unstarted — displaced by the permission friction, which consumed most
of the session's execution budget. Unit 4 (doc-expiry sweep, 25 expired docs) was doc-only and
reachable, and was displaced the same way.

Unit 6 carries one design note worth keeping: `open_thesis()` (`service.py:202`) validates
**only the symbol suffix** — no price ordering at all, not even `entry_band_lower <=
entry_band_upper`, which exists solely on the `ThesisProposal` schema (`schemas.py:375`) that
nothing can reach yet. Enforcement must be **open-time only and revision-exempt**, because a
legitimately raised trailing stop sits above entry (see Pending item 7). Against the 13 live
theses: CBA passes, HUBS fails, the other 11 have NULL stop/target and take the NULL path.

---

## End-state

- `main` @ `d7e8242` (`#155` squash-merged). `#151` rebased onto that tip; `#154` rebasing in this train.
- Migrations: **97** applied; `REQUIRED_MIGRATIONS` now reads 97 on the branch (`abc434a`).
- Tests: **2427 passed, 1 skipped, 0 collection errors** at pinned versions with `.[dev]`.
- Rule #11 intact and better understood; s766B firewall intact; migration `0042` untouched; no
  migration applied, no DB write, no capital action. James authorized this merge train.
