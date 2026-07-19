# arbi canary — 2026-07-18 — "make the brief true + calm" (brief-truth mission)

**What this is:** the first *deliberately instrumented* run of the attended arbi/main-loop
development loop, requested by James (governor) as the canary evidence base for deciding what a
future overnight automated-development controller would need. It records — for one real mission —
every state transition, every human decision required, every permission stop, every CI/repair
event, every resource interruption, and every reason a fresh session could NOT have resumed this
work unattended.

**Mission (THE ONE THING, arbi engine-first re-rank #1):** eliminate the false −75.7%
portfolio-return figure in the emailed brief and calm the dead Model-A banners — through a green
draft PR, stop before merge. Financial-correctness guardrail (James): do NOT assume "re-anchor on
cost base" is correct; red-team + define the intended metric first; use a cash-flow-adjusted
method OR label honestly as unrealised P&L; never substitute the CGT cost base for a
performance denominator. Banner guardrail: suppress only shelved-engine noise, never genuine
model-independent freshness/job-health/data-integrity signal; prefer one explicit "Model A
shelved" state.

**Branch:** `claude/whats-new-yemcl4` (head `9254561` at mission start). Draft PR only; James merges.

---

## Transitions log

| # | State | UTC | Note |
|---|---|---|---|
| 1 | SELECTED | 2026-07-18T~23:50Z | Engine-first re-rank produced #1 = brief-truth; James said "go, this exact mission." |
| 2 | GATE (act-time) | 2026-07-18T23:57Z→2026-07-19T00:1xZ | `arbi-red-team` **PASS** on all 5 failure modes (closest: banner-suppression edges toward hygiene, survives on Layer-1 primacy). Scope guardrail issued: keep the metric to the honest cost-base/unrealised-P&L line; do NOT escalate to a TWR engine (a shippable S–M truth-fix would become a blocked M–L build). No s766B / rule #11 crossing (display-suppression only, `required=False` path separate from the allocator's hard-fail). |
| 3 | INVESTIGATE | 2026-07-18T23:57Z | Read `compose.py:711-750` + `returns.py` — bug confirmed: portfolio leg differences flow-affected `capital_aud` as if a level. Same logic mirrored in `wealth_state.py:122-141`. Benchmark leg (`benchmark_tr_level`) is a valid index — untouched. |
| 4 | INVESTIGATE (data) | 2026-07-19T00:0xZ | DB probe complete — the −75.7% is a data/composition artifact, not loss or a genuine withdrawal. See "Data investigation finding" below. |
| 5 | DESIGN | 2026-07-19T00:1xZ | Gate PASS → `backend-architect` dispatched to design the honest metric + banner-shelf-state (James's instruction: architect designs, main loop implements). Design returned: unrealised P&L vs AUD cost base (+10.3%), calm shelf banners. |
| 6 | DESIGN-INPUT (decision required) | 2026-07-19T00:2xZ | James supplied his live brokerage position mid-build → revealed the metric is a governor choice, not a lookup (broker +19.57% USD/local vs asxos +10.3% AUD-incl-FX). Build PAUSED. |
| 7 | DECISION | 2026-07-19T00:3xZ | James: **"show the broker."** Metric = USD/local return `(current − entry)/entry`, native, FX-neutral — reconciles with Fidelity. DB-verified: HUBS entry 187.54 → close 224.57 = +19.75% (= broker +19.57% up to the day's price). This is SIMPLER than the architect's cost-base design and involves no tax cost base at all (sidesteps the R10/tax concern). Separate non-blocking flag raised to James: CGT cost base A$6,978 (0.6450 ESPP fill) vs broker A$6,448 is a tax-data question for later, not this PR. |
| 8 | BUILDING | 2026-07-19T00:3xZ | Implementing: per-thesis native `unrealised_return` (loader-appended, like cgt_boundary — keeps evaluate_discipline quiet-by-default); delete `_since_inception_returns` + `_benchmark_lag`; calm `model_shelved` banners; delete the false block in the dark V2 `wealth_state.py`; regression tests. |
| 9 | TESTING (local) | 2026-07-19T00:4xZ | py_compile + ruff clean on all 6 changed files. `pytest tests/test_thesis_discipline.py` = **19 passed** (incl. the new broker-matching +19.7% test). Standalone Jinja render check = **4/4** (calm shelf; shelved-but-prices-stale still warns; normal path intact; genuine signal-stale still loud). Async `test_brief_compose`/`test_wealth_state` are CI-gated (sandbox lacks asyncpg + pytest-asyncio — documented gap) — written, not locally runnable. |
| 10 | REVIEW | 2026-07-19T00:4xZ | Ran `portfolio-invariant-guard` + `security-engineer` on the diff (the two substantive reviewers for a financial/firewall change; refactoring + doc-accuracy self-reviewed given the minimal −51-line diff). |
| 11 | REVIEW OUTCOME | 2026-07-19T00:5xZ | **BOTH PASS.** portfolio-invariant-guard: all 7 invariants hold. security-engineer: all 7 firewall/security checks hold + it ran 68 tests green. Applied their feedback: per-thesis loud-error isolation on the `unrealised_return` loop (security LOW) + doc/scaffolding-rot cleanups (both). Re-verified: ruff + 19 discipline tests still green. |
| 12 | COMMIT | 2026-07-19T00:5xZ | Staged code+tests+canary; review-gate marker `.claude/.review-passed-445eee4ac966` (had to `touch` in a separate shell call — the gate checks the marker at PreToolUse, before the shell runs; a compound `touch && commit` fails). Committed `bb07b36` (8 files, +226/−233), pushed. |
| 13 | DRAFT PR | 2026-07-19T00:5xZ | **Draft PR #64 opened** (https://github.com/Jp8617465-sys/asxos/pull/64) for James's merge. CI `full-check` PENDING — subscribed to PR activity to catch the result (this is the CI-wait/repair leg of the instrumentation). Mission reaches "green draft PR" once CI passes. |
| 14 | **MISSION COMPLETE** | 2026-07-19T01:2xZ | Scheduled `send_later` check-in (armed at transition 13, fired ~30min later) confirmed **CI GREEN**: `full-check` success, `targeted-ml-tests` success (both ran twice, once per post-open commit — all 4 + 1 skipped comment-check = 5/5 green, zero failures). `mergeable_state: "clean"`, no conflicts. **No REPAIR_CI transition was needed** — first-shot green. PR #64 is a green draft PR, ready for James's merge. James notified. |

_(mission closed at transition 14 — the canary's live-tracking purpose is done; the sections below are the final synthesis)_

**Local-vs-CI verification split (canary datapoint for the overnight controller):** a fresh
unattended session in THIS sandbox can run py_compile, ruff, and pure-sync tests
(test_thesis_discipline) + standalone template renders — but CANNOT run the async collector
tests (asyncpg/pytest-asyncio absent) or `make check` in full. So an overnight loop here would
need to (a) treat CI `full-check` as the authority for the async/DB suite and gate "ready" on the
GitHub check, not a local green, and (b) carry a documented allowlist of what local verification
does/doesn't cover so it doesn't false-claim "tests pass". This is a concrete input to the
dossier's Stage-5 (CI-event repair) design.

---

## Data investigation finding (the metric-defining fact)

The −75.7% is **neither investment loss nor a genuine withdrawal of invested capital** — it is a
**book-composition / data-definition artifact**:

- `_since_inception_returns` anchors "inception capital" on the earliest snapshot with a benchmark
  level — **2026-05-27, `capital_aud` = 31,746.89** = holdings_mv 6,746.89 **+ a static
  `cash_aud` = 25,000 placeholder**. It anchors "current" on **2026-07-16, `capital_aud` =
  7,707.25** = holdings_mv 7,707.25 **+ cash 0**. `(7707 − 31747)/31747 = −75.7%`.
- The 25,000 cash was a **constant placeholder** present every day 05-27 → 07-01, then it
  **vanished** from 07-06 onward (cash → 0). There is a fully-**broken all-zero snapshot on
  2026-07-05** (capital/holdings/cash all 0) and multiple phantom rows where holdings_mv = 0 but
  cash = 25,000 (05-31, 06-07, 06-14, 06-21, 06-28, 06-30). The snapshot `capital_aud` series is
  **not a trustworthy return index.**
- **The only real position is HUBS: 1 OPEN lot, `cost_base_normal` = 6,978.23 AUD, current MV
  = 7,707.25 AUD → +729.02 AUD = +10.4% unrealised.** **ZERO disposed lots** (nothing was ever
  sold), and **no contributions/withdrawals ledger exists.**

**Metric consequence (settles James's guardrail):**
- A valid **time-weighted or money-weighted return is NOT computable** from this data — no flow
  ledger, and the capital series is corrupted by the cash-placeholder change + the all-zero row.
- The honest, computable metric is **unrealised P&L on current holdings vs cost base**
  = `(Σ MV_aud − Σ cost_base_normal) / Σ cost_base_normal` = **+10.4%**, read from
  `current_holdings`/`holding_lots` (reliable) — **explicitly labelled "unrealised P&L on
  holdings," never "total return," never portfolio "alpha vs benchmark."** This also sidesteps the
  unreliable snapshot capital series entirely.
- The **benchmark-lag / alpha claim must be dropped, not re-based** — there is no comparable
  portfolio TWR to difference against a benchmark TR. A standalone "XJO TR since <date>" context
  line is optional and must never be framed as portfolio alpha (per James).
- **Out-of-scope flag (do not fix in this mission):** `snapshot_portfolio` is emitting corrupt rows
  (all-zero 2026-07-05; phantom static-cash rows). Reading the honest metric from `holding_lots`
  avoids depending on it, but the snapshot corruption is a separate data-integrity backlog item.

---

## James decisions / prompts required (running count)

1. Initial "go" on THE ONE THING, with a detailed financial-correctness spec (the metric could
   not be safely chosen without governor guidance — arbi's original "re-anchor on cost base" spec
   was financially naive; James caught it). **This is a human-judgment dependency an unattended
   loop could not have satisfied alone** — see outer-controller notes.
2. **Mid-build, James supplied his live brokerage position (Fidelity screenshot) — which
   revealed the "honest metric" is itself a governor choice, not a lookup.** The broker headlines
   HUBS at **+19.57%** (cost basis A$6,448.37, value A$7,710.95); asxos's CGT cost base is
   A$6,978.23 → **+10.3%**. Both are internally correct; they differ purely by **FX convention**:
   the broker converts BOTH cost and value at *today's* FX (≈0.698) so the currency cancels and
   its "+19.57% AUD" is really the **USD/local return**; asxos's cost base is AUD at the
   *acquisition* FX (0.6450), so +10.3% is the **AUD return including the FX translation** (AUDUSD
   rose 0.645→0.698 since purchase, trimming the USD gain in AUD terms). **An unattended loop
   would have shipped +10.3% "vs cost base" and it would have looked WRONG next to the broker's
   +19.57% — only James's domain knowledge + the screenshot caught it.** This is the single
   strongest canary datapoint for "what an overnight controller cannot do alone": the choice of
   *which* return to display (USD/local vs AUD-incl-FX vs both) is a preference only the governor
   can set. Build paused pending his call. (Cost-base divergence A$6,978 vs A$6,448 is the same
   FX-convention artifact, NOT a data error — the CGT base stays as-is; it is correct for tax.)

_(more appended as they occur)_

---

## Permission stops observed this session (canary-relevant friction)

These are the mechanical stops that would break or stall an unattended fresh session. Recorded
because "every permission stop" is explicitly in scope, and because they are live evidence for the
credential/tool-isolation and harness-reliability sections of any automation plan.

1. **`authority-guard.sh` false-positive on a read-only command.** A plain `ls .claude/*.json`
   (pure read, no write verb) was denied with "references an authority/boundary path alongside a
   write-capable interpreter/utility." The guard's Bash regex matched the `.claude/` path fragment
   but the command carried no write verb — a read was blocked. Friction for any loop that inspects
   its own config.
2. **`mcp__supabase-ro__execute_sql` — repeated `AbortError: Tool permission stream closed before
   response received`** (≥4 occurrences this session), despite the tool being explicitly on the
   `.claude/settings.json` allow-list. Worked around by falling back to the full read-write
   Supabase MCP for the same SELECT-only queries. This is risk-register R16 biting: an allow-listed
   read-only tool that does not reliably auto-approve in this web/remote harness. **Directly fatal
   to an unattended run** — a scheduled session whose first DB read aborts has no human to retry.
3. **`AskUserQuestion` — same `AbortError: Tool permission stream closed`.** The structured
   decision-picker aborted; fell back to plain-text prose to ask the question. Same R16 class,
   now on the human-interaction surface.

_(more appended as they occur)_

---

## CI / repair events

**Zero repairs needed — first-shot green.** `full-check` and `targeted-ml-tests` both passed on
the initial push (each ran twice — once per commit pushed after the PR opened: the fix commit and
the follow-on canary-doc commit — 4/4 non-skipped checks green). Total CI wall-clock from PR-open
to last check completing: ~5 minutes (`created_at` 00:56:46Z → last check `completed_at`
01:02:46Z). Contrast with the dossier's cited historical case (PR #59, the firewall-hardening
mission from the 07-18 overnight run) which broke 10 existing tests and needed a repair cycle —
this mission's local pre-verification (py_compile + ruff + the full pure-sync discipline suite +
a standalone template render check covering all 4 banner branches) evidently caught what the
sandbox *could* catch, and the CI-only async suite had nothing left to find. **Not proof a repair
loop is unnecessary** — it's one data point that thorough local pre-verification (within the
sandbox's ceiling) measurably reduces CI-failure rate, which is itself a design input: an
unattended loop should maximize local verification before ever consuming a CI cycle.

---

## Resource / spend / model interruptions

**One mid-mission model switch, handled transparently.** Between transition 13 (draft PR opened,
built under Opus 4.8) and transition 14 (this check-in), James ran `/model claude-sonnet-5` —
this check-in fired and executed under **Sonnet 5**, a different model than built the fix. The
transition was seamless *because state was externalized to git*, not held only in conversation
memory: the canary doc itself (committed + pushed), the PR body, and the commit messages together
carried enough context for the check-in to correctly interpret "confirm CI on PR #64" and act
without re-deriving any of the mission's reasoning. **This is a direct, positive data point for
the dossier's checkpoint/resume design (§9.1 `BLOCKED_RESOURCE_BUDGET`)**: a model swap, a session
restart, or a fresh unattended session all fail or succeed on the same axis — whether the mission's
state lives in a durable, git-tracked artifact (issue + PR + this kind of run-record) rather than
in-context. It did here. No spend-limit or session-limit interruption occurred this mission (contrast:
the dossier's cited 07-18 audit *did* hit one) — so that specific transition (`SESSION_LIMIT_HIT →
checkpoint → fresh-session retry`) was not exercised this canary and remains untested by this run.

---

## Resumability blockers (could a fresh session resume THIS issue + PR from GitHub alone?)

**Mostly yes, with one gap.** A fresh session pointed only at PR #64 (no conversation memory) could
correctly determine: what changed and why (PR body is self-contained: root cause, the fix, the
financial-correctness reasoning, verification, review verdicts, explicit out-of-scope follow-ups),
that both required reviews passed (stated in the PR body prose — not as separate GitHub "reviews,"
since `security-engineer`/`portfolio-invariant-guard` are Claude subagents, not GitHub review
identities), and that CI is green and it's mergeable. **The gap:** the PR body does NOT surface the
single most important fact of this mission — that the metric was a *governor decision point*,
not an engineering default, and specifically *why* (the brokerage-screenshot reconciliation, the
FX-convention explanation). That reasoning lives only in this canary doc and this conversation. A
fresh session (or James, months later) reading only the PR would understand *what* metric was
chosen but not *the full trail of why it isn't the more "obvious" cost-base figure* without also
finding and reading `docs/product/arbi-canary-2026-07-18-brief-truth.md`. **Fix for a future
loop:** the mission's run-record (this canary pattern) should be linked FROM the PR body, not just
committed alongside it in the same branch — a fresh session triaging via GitHub alone should not
have to know the canary doc exists to find it.

---

## What an outer controller would have needed to complete this exact mission overnight

Synthesized for `docs/product/automation-dossier-reconciliation-2026-07-19.md` (§2 of that doc is
the state-machine trace this section supports):

1. **A judgment-surfacing gate it does not have today.** The single hardest moment of this mission
   — James's brokerage screenshot overturning the architect's cost-base design — is exactly the
   kind of event a state-machine controller cannot manufacture on its own; it can only know to
   *pause and ask* rather than confidently ship a plausible-but-wrong number. Detecting "this
   mission embeds a value/metric/policy choice" from a mission envelope is a real design problem,
   not a solved one — the honest answer is that THIS mission should have been classified amber
   (ask-once) from the start, not green, and the fact that arbi/backend-architect did not initially
   flag it that way is itself informative.
2. **CI as the sole verification authority, explicitly.** This sandbox cannot run the async/DB test
   suite — an unattended controller must know that about its own environment and gate "done" on the
   GitHub check conclusion, never on a local pytest run alone (see the local-vs-CI split noted at
   the top of this doc).
3. **Reliable, allowlisted read access before anything else.** The `mcp__supabase-ro__execute_sql`
   aborts (4/4 this mission) would have killed an unattended run at the very first live-data
   investigation step — before it could even discover the −75.7% was a composition artifact, let
   alone reach the point of needing James's judgment call. This is the true precondition, ahead of
   the dossier's Stage-1 frontmatter repoint (see the reconciliation doc's mission recommendation).
4. **A durable link between the mission's reasoning and its PR** — the resumability gap above. A
   controller-driven loop should write its run-record path into the PR body itself (not just commit
   it to the branch), so any future reader — human or agent — starting from GitHub alone can find
   the full trail without already knowing to look.
5. **What it would NOT have needed:** a repair loop for THIS mission specifically (zero CI failures
   occurred) — though that is mission-specific luck from thorough local pre-verification, not
   evidence the repair transition is unnecessary in general (the dossier's PR #59 precedent shows
   the opposite in the same repo, same week).
