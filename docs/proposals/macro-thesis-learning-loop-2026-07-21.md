# Macro-thesis learning loop — evaluate falsifiers, score calibration, feed the dream

**Status:** proposed (arbi draft — James-requested 2026-07-21)
**Scope:** the *monitor → learn* half of the macro-thesis lifecycle — a mechanism that scores
each approved `macro_theses` row's catalyst/falsifier against accumulating `market_context`
history, records outcomes, and feeds calibration signal into the existing arbi dream/promotion
loop. **Not** the allocator, not capital deployment, not a signal engine.
**Last verified:** 2026-07-21 (live: `macro_theses` = 2 approved rows #6/#7; `market_context`
= 11 daily rows and growing; `check_thesis_invalidations` cron live for per-symbol theses)
**Owner:** arbi draft → needs `system-architect` + `backend-architect` sign-off (new module +
new table) → James scope sign-off before build
**Depends on:** `docs/product/arbi-dream-policy.md` (the consolidation loop this feeds),
`docs/product/arbi-promotion-gate.md`, `jobs/check_thesis_invalidations.py` (the pattern this
mirrors), `migrations/0035_macro_theses_and_governance_columns.sql` (the rows being scored)
**Superseded by:** N/A

Triggered by James (2026-07-21): "I do like the macro read. I think if we can build a learning
loop or dream state about this that could improve over time." Written the same session two macro
theses (#6 breadth-led catch-down, #7 sticky AU long end) were approved into
`governed_active_macro_theses` — the first content this loop would ever have to learn from.

---

## 1. Why this is buildable *now* and wasn't a week ago

A learning loop needs three things that only just came into existence together:

1. **Falsifiable, machine-checkable claims.** The `macro-economist` agent contract forces every
   proposal to carry a `catalyst` and a `falsifier` stated against named `market_context_current`
   columns — not vague sentiment (`.claude/agents/macro-economist.md`, "both concrete and
   checkable against future data"). Concretely, thesis #6's falsifier is *"pct_above_200d_ma >=
   0.50 on 10 consecutive daily rows with asx200_close staying above 8,600"* and thesis #7's is
   *"aus_10y_yield closes below 4.25 on 5 consecutive daily rows."* These are **evaluable SQL
   predicates over a time series**, not prose a human has to adjudicate.
2. **An accumulating time series to check them against.** `market_context` was a single row on
   2026-07-03 (evidence_id 16/29 in run #3/#4 flagged this as the hard limit — *"contains exactly
   1 row… every trend-shaped claim is capped at inferred"*). It is now 11 daily rows and grows one
   per weekday via `asxos-ingest-market-context`. The single-snapshot limitation the first theses
   apologised for is **dissolving on its own** — by each thesis's 2026-09-30 catalyst horizon
   there will be ~50 trading days of history to score against.
3. **Approved rows to score.** Zero until this session. Now two.

None of this touches rule #11: macro theses are model-independent (no Model A signal attaches),
so scoring them is squarely on the model-independent moat, not the shelved ML engine.

## 2. The gap — the loop is half-built and the built half is the wrong half

The per-symbol thesis lifecycle already has a monitor: `jobs/check_thesis_invalidations.py`
evaluates price-based invalidation conditions daily against the latest close and emails on a
trigger. **Macro theses have no equivalent.** A macro thesis's `catalyst`/`falsifier` fields are
written at approval and then never looked at again — nothing computes whether the world moved the
way the thesis predicted. So today:

- A macro thesis can be **flat wrong for months** and still sit `approved` in
  `governed_active_macro_theses`, silently feeding future discovery agents a stale prior.
- There is **no record of authoring quality** — which quadrant calls held up, which falsifiers
  were well-constructed vs never-triggerable, whether the `macro-economist` agent (or its manual
  stand-in) is calibrated. The dream loop (`arbi-dream-policy.md`) consolidates *committed doc
  artifacts*; it has no macro-thesis outcome data to consolidate because none is produced.

This is the same class of gap the coverage framework named for `theme_holdings` — *"schema
exists, never fed"* — one rung up: the *outcome* schema doesn't exist at all.

## 3. The three layers (each independently useful)

### Layer A — Falsifier/catalyst evaluator (a cron + a new outcomes table)

The concrete, mechanical core. A daily job (`jobs/score_macro_theses.py`, mirroring
`check_thesis_invalidations.py`'s structure — `JobMonitor`, `require_personal_use_job`, UPSERT)
that, for each `approved` non-retired macro thesis:

- Evaluates its catalyst and falsifier predicates against the `market_context` **history**
  accumulated since the thesis's `created_at` (not just the latest row — these are multi-day
  conditions: *"10 consecutive rows,"* *"the majority of daily rows through 2026-09-30"*).
- Writes a row to a **new `macro_thesis_outcomes` table** (`macro_thesis_id`, `as_of`,
  `catalyst_progress`, `falsifier_triggered`, `days_elapsed`, `days_to_horizon`,
  `evaluation_detail` JSONB). Re-derivable, append-friendly — **not** governance content, same
  classification as `screening_runs`/`portfolio_daily_snapshots` (not in
  `backup_irreplaceable.sh`).
- On a **falsifier trigger**, does *not* auto-retire — it flags for James (the same "credits are
  never auto-removed" / "system proposes, human decides" discipline as everywhere else). A
  falsified macro thesis becomes a `james-inbox`-style review item, and its retirement (an
  existing governance transition, `governance_status → retired`) stays a human act.

**Honest scope note:** the evaluator must parse structured predicates. The macro-economist's
catalyst/falsifier text is more free-form than `check_thesis_invalidations`'s narrow price
regexes — *"pct_above_200d_ma below 0.40 in the majority of daily rows"* needs a small grammar
or a structured-condition field the agent emits alongside the prose. **Recommendation:** add an
optional `machine_conditions` JSONB to the `MacroThesisProposal` schema (a list of
`{column, op, threshold, window, aggregation}`) so future proposals are evaluable by construction,
and hand-annotate the two existing theses once. This is the real design question for
`backend-architect`, and it's why this is a proposal, not a patch.

### Layer B — Calibration scorecard (aggregation over outcomes)

Once Layer A produces outcomes, a read-only rollup (a CLI command + a brief card, mirroring
`asx theme coverage`): per regime-quadrant hit rate, falsifier-quality distribution (how many
were ever-triggerable vs vacuous), authoring source (macro-economist agent vs manual stand-in vs
human), and horizon-calibration (did 6-month calls resolve in 6 months). This is the **evidence a
dream consolidates** — it turns "we wrote some macro theses" into "falling-growth calls at thin
breadth have held N/M times; the agent's falsifiers trigger cleanly but its catalysts are often
un-observable."

### Layer C — Feed the dream / promotion loop (reuse, don't rebuild)

Layer B's scorecard becomes an input to the **existing** `/arbi-dream` consolidation
(`arbi-dream-policy.md`): a weekly dream reads the macro-thesis outcome history + the calibration
scorecard and extracts durable lessons (*"disinflationary-slowdown calls need a CPI observable the
system doesn't ingest — stop tagging the inflation leg as anything but a placeholder"* — a lesson
these very theses' own text already gropes toward). Those lessons go through
`/arbi-promote`'s CODEOWNER-gated merge into `approved-lessons.md` — **no new learning
machinery**, just a new data source feeding the loop that already exists. Critically, this keeps
learning "mediated through memory + evaluation, never model weights" (`arbi-dream-policy.md`) —
the macro-economist agent improves because its *prompt/context* carries promoted lessons, not
because anything retrains.

## 4. What's buildable now vs. what needs a decision

**Buildable now (no new dependency):**
- Layer A's `macro_thesis_outcomes` table + evaluator cron — but **only after** the
  `machine_conditions` schema decision (below), else the evaluator is guessing at free text.
- Hand-annotating theses #6/#7 with structured conditions (they're already written in
  near-machine form).

**Needs James / architect decision first:**
- The `machine_conditions` schema addition to `MacroThesisProposal` — touches the governance
  proposal schema (`asxos/domain/theses/schemas.py`), so `backend-architect` scopes it and it's a
  migration-adjacent change. **This is the gating decision.**
- Whether falsifier-triggered theses auto-flag into `james-inbox.md` or a new review surface.

**Explicitly out of scope:** any auto-retire/auto-approve; any capital action; any Model
A/signal input; changing the `macro-economist` agent's authoring logic (that improves via
promoted lessons, not a code change here).

## 5. Ranked next steps

1. **`backend-architect`: scope the `machine_conditions` structured-predicate schema** — the one
   decision everything else waits on. Without it Layer A parses free text; with it, evaluation is
   correct by construction.
2. **Build Layer A** (table + `jobs/score_macro_theses.py`) once the schema lands; backfill the
   two existing theses.
3. **Layer B scorecard** (CLI + brief card) once ≥1 thesis has ~30 days of outcome history
   (~2026-08-20 for #6/#7).
4. **Wire Layer C** — point the next `/arbi-dream` at the outcome history; no new machinery.

## 6. How this connects to the north star

`north-star.md` defines the product as the **identify → monitor → change** loop over theses, made
dynamic: *"a thesis can be correct when written and stop being correct as macro moves… the
system's job is to monitor it and change it when the world changes."* This proposal is the
**monitor + change** half for *macro* theses specifically — the exact analogue of the CBA
stale-thesis discipline James asked to automate (`james-inbox.md`), applied one level up at the
regime layer. Its sibling proposal (`macro-workflow-automation-2026-07-21.md`) is the **identify**
half.
