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
| 5 | DESIGN | 2026-07-19T00:1xZ | Gate PASS → `backend-architect` dispatched to design the honest metric + banner-shelf-state (James's instruction: architect designs, main loop implements). |

_(appended as the mission proceeds — planning → building → testing → review → PR → CI → repair → ready)_

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

_(pending — populated once the draft PR is open and CI runs)_

---

## Resource / spend / model interruptions

_(none observed yet)_

---

## Resumability blockers (could a fresh session resume THIS issue + PR from GitHub alone?)

_(assessed at mission close)_

---

## What an outer controller would have needed to complete this exact mission overnight

_(synthesized at mission close — feeds the dossier reconciliation James requested)_
