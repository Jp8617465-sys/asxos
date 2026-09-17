# Runbook — scanning for investment opportunities with what already exists

**Status:** current
**Owner:** arbi (procedure), James (every judgement inside it)
**Built:** 2026-09-17. Live figures in §2 are a snapshot of the 2026-09-16 valuation
sweep — re-derive them, never quote them.
**Scope:** how to go from 1,879 ASX equities to a broker-grade research report with a
price target and bull/base/bear scenarios, **using only surfaces that exist on `main`
today**. No new features. Nothing here requires code to be written.

---

## 0. Read this before you use it

Three things this runbook will not do, so you do not discover them halfway through.

**It will not hand you a ranked list of buys.** `jobs/discover_opportunities.py` used
to do exactly that — rank by value/price × liquidity and open the top-K as theses with
a target, an entry band and a stop derived from the model. It was **demoted on
2026-09-16 (#306)** because the sealed value-to-price test returned null (#304), and
the response was pre-committed by James before any result existed
(`asxos/domain/research/registry/vp.py::RESPONSE_RULE`): the residual-income model
*"stops emitting target prices, entry bands and ranked 'opportunities'"*. The screen
still runs and still records who passes. It emits a **set, in symbol order** — not a
rank, not a proposal. That is the machine being honest about what it measured, and the
runbook is built on top of it rather than around it.

**The scenarios come from your price plan; the street's targets have their own home.**
Two different things, and conflating them undersells what exists. The governed report's
bull case is your recorded `target_price`, its bear case your recorded `stop_price`,
its base case 0% — the system challenges those numbers against the book, the tax
position, the liquidity and its own independent valuation, makes them permanent and
hashed, and scores them later. It does not invent them, and a system that invented them
is what rule #11 quarantined.

Separately, **analyst consensus and dated target moves are first-class persisted
fields** — `theses.analyst_consensus_target` and analyst-move revisions, written by
`asx thesis update-consensus` and `asx thesis log-analyst`, and already read by the
daily brief. §6.1 is the step that fills them. Skip it and the street's targets exist
only as prose in a markdown file.

**Nothing it produces is actionable, by construction.** `derive_state()`
(`decision_engine/builder.py:220`) can only return `watch` or `abstain` today: an
action state additionally requires a capital-risk calibration (C-13) that has no
producer yet, so the function raises rather than guessing a direction. Every report
renders at 0% size with "non-actionable — paper only". Capital is James's (AGENTS.md
§2). The report is the research; the decision is not the system's to make.

What you get instead is genuinely valuable and rare: **an explainable funnel where
every exclusion has a stated reason, and a report that cannot show a number its
evidence chain does not carry.**

---

## 1. The two report surfaces

They are different tools and you will use both. Do not confuse them.

| | `/thesis <SYMBOL>` | `asx decision report` |
|---|---|---|
| What it is | LLM-authored equity research note | Governed render of a persisted contract chain |
| Where targets come from | Street consensus + your own analysis, cited | `theses.target_price` / `stop_price` |
| Scenarios | Bull and bear argued in prose, with the evidence | `bull/base/bear` %, probabilities, rationale |
| Web research | Yes (~10–15 fetches) | No — DB only |
| Writes to DB | **Nothing** (Phase A constraint) | Yes, content-addressed and append-only |
| Reproducible | No | Byte-reproducible with `--evaluated-at` |
| Triggered | You run it | **The packet is built nightly**; you render it |
| Output | `docs/reviews/thesis-<symbol-slug>-<date>.md` | `<out>/<packet_id>/<sha256>.md` |

The first is how you *form* a view. The second is how you *commit* one so it can be
challenged and, later, scored against what actually happened. Skipping the second is
how a research process becomes a collection of opinions nobody ever marks.

---

## 2. The funnel, with live numbers

Measured 2026-09-17 against the 2026-09-16 sweep and screening run. Re-derive with
§4.2 — do not quote these.

**Start from the right number.** `universe.is_active` is 2,396, but the valuation sweep's
population is `security_kind = 'au_equity' AND is_active` (`valuation/universe.py:74`),
which is **1,879**. The other 517 are not dropped silently, they are out of the
residual-income model's domain by construction:

| Active, not `au_equity` | Count |
|---|---:|
| `etf` | 487 |
| `hybrid` | 18 |
| `lic` | 12 |

A residual-income model on tangible common equity has nothing to say about an ETF.
Those 517 are the product's **thinnest moat layer, not its out-of-scope pile** — the
theme lane in §4.3 is the surface that covers them, and it has barely been run.

The funnel proper, in the order the job applies it — liquidity is the **pre-filter**,
not the last gate:

| Stage | Names | Gate |
|---|---:|---|
| ASX equity universe | 1,879 | `security_kind='au_equity' AND is_active` |
| Liquidity pre-filter | 537 | ADV ≥ A$250k **and** market cap ≥ A$100m |
| Valued by the RI model | 332 | the rest are `blocked` with a named gap |
| Currency verified | 270 | `currency_unverified` excluded — the HUBS error class |
| Quality | 138 | 3-period **average** ROE > Ke mid |
| Value, both conventions | **16** | value ≥ price under registered **and** average-ROE sensitivity |

Across the whole sweep, 1,306 of 1,879 are `blocked`. That is not a failure — gaps are
rows, never omissions (`jobs/run_valuation.py`). A name with no book value or no ROE
history cannot be valued by a residual-income model, and the model says so by name
instead of quietly dropping it.

**Sixteen names is the honest output of a weekly scan.** That is a reading list, not a
buy list, and it is small enough to actually read.

---

## 3. Preflight — four checks, two minutes

Run these before any scan. A scan on stale inputs is worse than no scan, because it
looks identical.

```sql
-- 1. Prices current (expect today or the last trading day)
SELECT max(dt) FROM prices;

-- 2. The sweep ran and is fresh (expect the most recent Saturday)
SELECT max(as_of), count(*) FILTER (WHERE outcome='valued') FROM valuation_runs
 WHERE as_of = (SELECT max(as_of) FROM valuation_runs);

-- 3. Fundamentals PIT — the valuation's input. FY-reported, so a lag is normal;
--    a lag of more than ~5 months means sync_financial_statements is not landing.
SELECT max(as_of) FROM rs_fundamentals_pit;

-- 4. The weekly chain concluded
SELECT job_name, status, as_of FROM job_runs
 WHERE job_name IN ('run_valuation','discover_opportunities','derive_fundamentals_pit')
 ORDER BY started_at DESC LIMIT 6;
```

If the sweep is stale, dispatch it rather than working around it — the chain is
ordered and idempotent, so re-running is always safe:

```bash
gh workflow run weekly-research.yml
```

Step order **is** the dependency graph: `sync_financial_statements` →
`derive_fundamentals_pit` → `run_valuation` → `discover_opportunities` →
`sync_fundamentals`. A failed step blocks everything below it.

---

## 4. Stage 1 — Scan

### 4.1 Let the weekly chain do it

`weekly-research.yml` runs Saturday 16:00 UTC (Sunday 02:00 AEST) and already does the
whole scan. `discover_opportunities` logs the liquidity screen to `screening_runs` and
records the passing set. **You do not need to run anything to get a weekly scan** —
you need to read the result.

### 4.2 Read the passing set

**Gate 1 is already persisted — do not re-derive it.** `screening_runs.matched_symbols`
is a `TEXT[] NOT NULL` holding *every* passing symbol, unbounded by `--limit` and
ordered by symbol so two runs over identical data produce byte-identical arrays
(`migrations/0038_screening_evaluator_wiring.sql:60`, written by
`screening/evaluator.py:697`). The audit row records the whole answer by design.

Either read the stored array, or reproduce it exactly:

```bash
asx screen run discovery-liquidity-v1 --no-log --limit 600
```

Then apply the three value/quality gates to what the screen matched. This query
re-derives `asxos/domain/discovery/ranker.py::passing` gates 2–4 over the persisted
gate-1 set — read-only, no side effects:

```sql
WITH latest_run AS (
  SELECT matched_symbols FROM screening_runs ORDER BY run_at DESC LIMIT 1
), scr AS (
  SELECT unnest(matched_symbols) AS symbol FROM latest_run   -- gate 1, as stored
), g AS (
  SELECT symbol, value_per_share,
         (payload->'inputs'->>'last_close')::numeric  AS last_close,
         -- ranker.py:89-91 falls back to value_per_share when the sensitivity
         -- is absent. Without this COALESCE the comparison yields NULL and
         -- silently DROPS a name that should pass.
         COALESCE((payload->'sensitivities'->>'average_roe_ke_mid')::numeric,
                  value_per_share)                    AS avg_roe_value,
         (payload->'ke'->>'ke_mid')::numeric          AS ke_mid,
         COALESCE((payload->'inputs'->>'roe_average')::numeric,
                  (payload->'inputs'->>'roe_trailing')::numeric) AS roe,
         COALESCE(payload->'flags','[]'::jsonb)       AS flags
    FROM valuation_runs
   WHERE as_of = (SELECT max(as_of) FROM valuation_runs) AND outcome = 'valued'
)
SELECT g.symbol, u.sector, u.security_kind,
       round(g.last_close,3) AS close, round(g.value_per_share,3) AS model_value,
       round(g.value_per_share/NULLIF(g.last_close,0),2) AS value_to_price
  FROM g
  JOIN scr ON scr.symbol = g.symbol
  JOIN universe u ON u.symbol = g.symbol
 WHERE NOT g.flags ? 'currency_unverified'
   AND g.roe > g.ke_mid
   AND g.value_per_share >= g.last_close
   AND g.avg_roe_value  >= g.last_close
 ORDER BY g.symbol;                 -- symbol order. The rank was deleted on purpose.
```

**Never hand-roll the liquidity gate.** A previous draft of this runbook computed ADV
as `avg(close*volume)` over 130 calendar days. `screening/evaluator.py:160-177` names
that exact shape as one of *"two distinct hazards, both of which would make the gate
admit the LEAST liquid names, the exact inverse of its purpose"* — a symbol trading 10
days in 90 gets scored on those 10 days alone, a ~9× overstatement. The evaluator
divides by a fixed 90 and guards `dt <= CURRENT_DATE` (a single future row once
overstated an ADV by ~524×). Use the stored array or `asx screen run`; nothing else.

`value_to_price` is in the output because you will want to see it. **It is a
diagnostic, not a score.** The one test of whether it predicts anything returned null
(#304). Sorting by it is re-introducing the rank the response rule removed; if you
find yourself doing it, you are using the model as an oracle again.

### 4.3 The second lane — themes, not screens

The screen is bottom-up and will only ever find what is cheap on book. The
theme lane is top-down and finds what is *changing*. Both feed the same funnel.

**This is the thinnest layer of the moat, and it is where the 517 non-`au_equity`
names from §2 live.** The standing count is 2,377 tracked instruments against 13
theses, 1 theme, 2 theme-holdings and **zero ETF/LIC/hybrid coverage**, with two agents
built for exactly this that have never been run once (`decision-log.md:161`). If you
only ever run §4.2, the screen will keep handing you cheap small-caps and the ETF
sleeve will stay empty. Budget at least one session a month here.

```bash
/discover-macro                        # → agent_runs rows, one per proposal
asx macro-thesis open --from-agent-run <run_id>     # → draft, auto-advanced to pending_review
asx macro-thesis approve <macro_thesis_id> --reason "<why>"

/discover-theme <macro_thesis_id>      # → theme + theme_holding proposals tracing to that macro read
asx theme approve <theme_code> --reason "<why>"
asx theme holding approve ...
asx theme coverage                     # → sectors where you have no exposure at all
```

Agents propose; they never write. A proposal becomes a row only when you run the
`open` verb, and reaches `approved` only via the `approve` verb — enforced by a
Postgres trigger, not just the service layer (migration 0034/0036).

**`/discover-sector` is broken today.** `sector-screener` screens on four columns that
are 0 non-NULL across 147,474 rows. The fix is in **PR #319, open and waiting on
James** (it is a `.claude/**` change, which arbi drafts and James merges). Until it
merges, that lane returns nothing and you should not spend a session on it.

---

## 5. Stage 2 — Triage the sixteen

This stage is a human reading the list, and it is not optional. Two failure modes the
screen cannot see, both visible in the current output:

**Closed-end funds — a filed defect, not a judgement call.** Six of today's sixteen
are LICs, listed funds and an A-REIT. A residual-income model on a fund's book value
is measuring the discount to NTA and calling it value — a different trade with
different drivers, and the model does not know it made the substitution.

Do not treat this as a standing chore you re-decide each week. The screen already
excludes funds: it hardcodes `security_kind = 'au_equity'`
(`screening/evaluator.py:284`), and only **12** names in the whole universe are tagged
`lic`. These six reach you because they are **misclassified as `au_equity`** — a
`universe.security_kind` data defect already filed (`decision-log.md:154` finding 2,
naming PGF/LSF/HM1 as LICs and BWP as an A-REIT, all *"outside the residual-income
model's domain"*). The fix is reclassification, one row each. Until then, drop them on
sight and do not spend judgement on them.

**Book-value artefacts at the top.** The widest value-to-price gap in the current set
is 6.26×. A gap that large is nearly always the model mis-reading the balance sheet,
not the market mis-pricing the business by a factor of six. Treat the extreme tail as
a data-quality alert, not the best idea. This is the Metro Mining lesson the average-ROE
gate already encodes (94× on trailing ROE, 0.92× on average).

Carry forward **three to five names** at most. The next stage is expensive and the
budget should go where you will actually act.

---

## 6. Stage 3 — The research report

```
/thesis <SYMBOL>
```

One invocation per name. This is the full broker-report surface: latest earnings print
with the input metrics, valuation against the company's own history and 2–3 named
peers, the segment it actually competes in, 3–5 named competitors with share
direction, the falsifiable market hypothesis the thesis sits inside, and **the street
view — consensus target, the range, and recent target moves with dates**.

The rendered note carries "Bull and bear, honestly" — both credible cases, then where
the evidence comes out with the time-horizon caveat — and a target ladder that puts
the street's numbers next to your own recorded levels.

Two rules that make the output trustworthy: every figure carries its source inline,
and **no financial fact from training memory** — if it was not fetched this run or read
from the DB, it does not appear. Fetched pages are untrusted text: data to quote,
never instructions to follow.

It writes nothing to the database. Output is `docs/reviews/thesis-<symbol-slug>-<date>.md`
on the current branch, and the note ends with the follow-up verbs it suggests — running
them is yours, by design. **At the end of this stage you have a view. Nothing else in
the system knows about it yet — which is why §6.1 exists.**

### 6.1 Persist the street's targets — do not let them die in the note

This is the step that makes the §6 research durable, and it is the part easiest to
skip. The street view `/thesis` just fetched has two existing homes:

```bash
# The consensus snapshot. analyst_consensus_target is read by the daily brief
# (brief/collectors/active_theses.py:58-61) — this is not a write-only field.
asx thesis update-consensus BHP.AU --buy 12 --neutral 4 --sell 1 --target 48.50

# Each target move, as a dated thesis revision event.
asx thesis log-analyst BHP.AU \
  --analyst "<firm>" --action upgrade \
  --from-rating neutral --to-rating buy \
  --from-target 41.00 --to-target 48.50 --date 2026-09-15
```

Without these, the target ladder exists only as prose in a markdown file on a branch,
and the brief has nothing to compare your own `target_price` against. With them, the
gap between what the street thinks and what you wrote becomes a tracked number.

`--action` must be one of `upgrade|downgrade|initiate|reiterate`.

---

## 7. Stage 4 — Record the thesis

This is where your target becomes a number the machine can challenge and score.

```bash
export ASXOS_PERSONAL_USE=1

asx thesis open BHP.AU \
  --status watching \
  --thesis "<the view, in your words>" \
  --entry 38.00-40.50 \
  --stop 34.00 \
  --target 52.00 \
  --timeline 18m \
  --themes <theme_code> \
  --conviction 3 \
  --tax-notes "<CGT / franking / holding-period notes>" \
  --reason "Opened from the 2026-09-20 scan"
```

**A price plan is mandatory and hard-fails if absent.** `build_decision_case` raises
rather than invent scenario numbers with no plan behind them (`builder.py:480`). What
it needs is a **reference price plus a stop and a target**: either the full entry band,
or an `actual_entry_price` on an entered thesis, which substitutes for the band
(`builder.py:481-494`). Stop and target are required either way. That refusal is the
feature.

Then the ten broker-report sections, one command each:

```bash
asx thesis add-section BHP.AU --kind identity_classification --body "..." 
asx thesis add-section BHP.AU --kind business --body "..."
asx thesis add-section BHP.AU --kind moat --body "..."
asx thesis add-section BHP.AU --kind capital_allocation --body "..."
asx thesis add-section BHP.AU --kind strategy_catalysts --body "..."
asx thesis add-section BHP.AU --kind risks_bear --body "..."
asx thesis add-section BHP.AU --kind valuation --body-file /tmp/val.md --figure "EV/EBITDA=5.8"
asx thesis add-section BHP.AU --kind position_plan --body "..."
asx thesis add-section BHP.AU --kind verdict_conviction --body "..."
asx thesis add-section BHP.AU --kind evidence_ledger --body "..."
```

Prose bodies cannot carry inline `$`/`%`/`x` literals — every capital-relevant number
goes through `--figure "Label=Value"` as a raw decimal and is recorded with explicit
provenance. That constraint exists to make an uncited number *structurally
unrepresentable as trustworthy*, and it applies to your own numbers too.

Lift the sections straight from the §6 note. The note is the draft; this is the record.

**One gap to know about:** `asx thesis revise` cannot set `invalidation_conditions` —
the service layer supports the field but no CLI flag reaches it. Without them, the
challenger raises a *material* (not blocking) finding: *"The thesis records no
invalidation condition."* Your falsifiers live in the §6 note and in
`--kind risks_bear` until a flag exists. Worth an issue; not worth blocking on.

---

## 8. Stage 5 — Governance status

`build_decision_case` refuses any thesis whose `governance_status` is not `approved`
(`builder.py:328`). Where that status comes from depends on who wrote the thesis, and
the distinction matters:

**A thesis you opened with `asx thesis open` is already `approved`.** The human CLI
path defaults to it (`service.py:285`) — 0033 grandfathers human-authored theses on
the reasoning that you reviewing your own work at the keyboard *is* the review. **No
approve step is needed; go straight to §9.**

**A thesis a system or agent proposed enters at `pending_review`** and cannot open as
`approved` at all — `open_thesis` raises if a non-human source tries. That one needs:

```bash
asx thesis approve <thesis_id> --reason "<why this passes review>"
```

Note it takes the **numeric `thesis_id`, not the symbol**, and hard-fails unless the
current status is exactly `pending_review`. It also enforces a 14-day evidence
staleness check, overridable only with `--accept-stale-evidence` and a logged reason.

The transition is enforced by a `BEFORE UPDATE` trigger requiring a matching
`governance_events` row in the same transaction — a direct `UPDATE` fails loudly.
Migration 0059 dropped the column DEFAULT that had laundered eleven unreviewed rows
into `approved`, so the gate is real for everything that is not the human path.

---

## 9. Stage 6 — The governed packet and its broker report

**The packet is already built for you.** `jobs/build_decision_packets.py` runs nightly
in `daily-brief.yml` (after the brief is sent, so a failure here can never cost the
brief) and builds a challenged packet for **every** thesis with
`governance_status='approved'` and no close date. It is same-day idempotent: a packet
already stored for the day is skipped, never rebuilt. So once §7 and §8 are done, the
routine path is simply to render tonight's packet:

```bash
asx decision report --packet-id <decision_packet_id> --out docs/reviews/packets --persist
```

Find the id with:

```sql
SELECT decision_packet_id, as_of, recommendation_state
FROM decision_packets ORDER BY created_at DESC LIMIT 5;
```

**Since #325 (migration 0060), a built packet also writes a `packet_examined` revision**
on the thesis, recording that the system examined it and what state it reached. That
revision type sits deliberately *outside* the brief's staleness allowlist, so it never
resets `revisit_due_at` — every clock reset stays a human keystroke. A machine
examination does not buy you another 30 days.

Build by hand only when you need an off-cycle or backdated packet:

```bash
asx decision build --thesis-id <id> --as-of 2026-09-20 --theme <theme_code> --persist
```

**Mind which book you challenge against.** The nightly job uses the **paper book**
(`paper_book_snapshots`, never the live book — C1/D15). `asx decision build` defaults
to `--context`, which is the **live** book. Pass `--paper-book <snapshot_id>` to match
the nightly convention; one or the other, never a blend. If you build by hand with the
default and compare it to last night's packet, you are comparing two different books.

`--theme` is optional: supplying it builds a Stage 3 `CandidateSnapshot` for the
symbol and rides it into the packet as extra evidence. Omit it if the symbol is not a
member of an approved theme.

`build` composes the chain — evidence packet → thesis version → challenge →
portfolio assessment → tax assessment → decision packet — and every artifact is
content-addressed and re-validated on the way out. `report` reconstructs all five
contracts from their stored payloads, so **the report can never show a number the
stored chain does not carry.**

What the rendered report contains:

- Verdict, recommendation state, paper sizing, expiry and expiry reason
- The investment case: question, variant view, summary, catalysts, falsifiers
- **Scenarios** — bull (your target, 25%), base (0%, 50%), bear (your stop, 25%),
  each with the return computed from your entry-band midpoint or actual entry price
- **Independent challenge** — 16 rules, the strongest bear case, and every finding
  with its required response
- Portfolio and policy state: marginal risk, opportunity cost, tax readiness, every
  constraint checked
- Missing or uncertain inputs, declared rather than hidden
- The full evidence manifest, each item tiered verified / inferred / speculative
- Content hashes for the whole chain

**Be clear about the base case.** It is hardcoded to 0% at 50% probability with the
rationale *"No structured base-case target exists on the theses table."* It is a
placeholder, not a forecast. The bull and bear numbers are real and are yours; the base
is a stated absence. If you want a genuine three-point distribution, that is a schema
change and therefore a new feature — out of scope here, and worth an issue.

### What will block you on the first run

Both of the current blocking findings on the live CBA packet are fixable, and you will
hit them:

1. **`sector_cap` — "No GICS sector is recorded for the proposed security."** Blocking.
   **538 of 2,396 active symbols have no sector.** Check yours before you build:
   `SELECT sector FROM universe WHERE symbol = 'BHP.AU';` If it is null, the packet
   cannot clear the D8 cap check.
2. **`price_detached`** — the last close is too far from the entry band. This is why
   thesis #1 (CBA, entry 42–45, last close 151.54, opened 2026-05-28) abstains. Keep
   the price plan current or the packet is correctly telling you the plan is stale.

All three packets in the database today are `abstain` for exactly these reasons. The
pipeline works end to end; it has never been given a thesis with a current price plan
and a sector.

---

## 10. Stage 7 — Dispose, then let it score itself

### 10.1 Dispose — the step that closes the loop

A packet that is delivered but never answered is the north-star's named honest miss.
`roadmap-state.md:594` calls *"delivered and disposed"* Stage 4's exit gate. Your verdict
is the other half of the record:

```bash
asx decision dispose --packet-id <id> \
  --verdict accept|request_revision|reject|defer \
  --note "<why>" --persist
```

Without this, the outcome data below measures what the system claimed and never what
you decided — which makes it a scorecard for a machine nobody was listening to.

### 10.2 Outcome observation — already automatic

`jobs/observe_decision_outcomes.py` runs nightly in `daily-brief.yml`, right after the
packet builder. Two append-only passes: t0 for any packet without one, then any horizon
whose due session has arrived. **You do not need to run these by hand.** The manual
verbs exist for off-cycle work:

```bash
asx decision record-t0 --packet-id <id> --persist
asx decision observe --packet-id <id> --as-of 2026-10-20 --persist
```

Outcomes materialise at **21 / 63 / 126 trading days**, measured from the packet's
reference price to the last close at or before the *promised* session, never the
catch-up date. The benchmark leg reports unavailable until `AXJOA.INDX` exists in
`prices` — a named unavailability, never a proxy (governor ruling F1).

Model A had 19,032 matured observations before anyone checked whether its conviction
was monotonic; it was inverted (STRONG_BUY −0.09% at 21d vs HOLD +5.07%). The
valuation model had **zero** when it was already emitting targets for 23 names. The
observation loop is automatic now — the part that is still yours is §10.1.

---

## 11. Cadence

| When | What | Whose |
|---|---|---|
| Nightly, in `daily-brief.yml` | `build_decision_packets` → `observe_decision_outcomes` | automatic |
| Sat 16:00 UTC | `weekly-research.yml` — the sweep and the screen | automatic |
| Sunday | §3 preflight, §4.2 read the set, §5 triage to 3–5 names | yours |
| As earned | §6 `/thesis` on those names — the expensive, valuable step | yours |
| Same sitting | §6.1 persist the consensus target and any analyst moves | yours |
| When a view firms | §7 record the thesis; §9 render tonight's packet | yours |
| Within a few days of each packet | §10.1 `dispose` — the exit gate | yours |
| Monthly | `/discover-macro` → `/discover-theme`; `asx theme coverage`. The thinnest moat layer — do not let this slide | yours |
| Quarterly | Re-read §0. If the funnel has started producing rankings again, something has drifted back | yours |

The two automatic rows are the reason this runbook is shorter than it looks: the
packet build and the outcome observation happen whether or not you open a terminal.
What is actually yours is triage, research, the thesis record, and the disposition.

---

## 12. Standing boundaries

- **Rule #11.** Never read `signals`, `signal_outcomes`, `model_versions`, or any
  Model A artefact. The packet contract enforces this mechanically — `model_independence`
  is `Literal[True]` and a Model A string in the manifest raises.
- **The valuation model is a discipline device.** It states a falsifiable number per
  thesis. It does not emit targets, entry bands or rankings. That ruling was
  pre-committed before the result existed; do not relitigate it on a disappointing
  scan.
- **s766B firewall.** Every command touching holdings, cash or the profile requires
  `ASXOS_PERSONAL_USE=1`. Output is evidence and analysis, never a personalised
  instruction.
- **No capital action.** No broker credential exists anywhere an agent can reach, and
  `asxos/capital/` stays empty. Paper trading, simulation, memos and order *drafts* are
  in scope; placing an order is James's alone (AGENTS.md §2).

---

## 13. Known limits of this runbook

Stated here so they are not rediscovered as surprises. None of them are fixed by this
document, and fixing them means building features — deliberately out of scope.

| Limit | Effect | Where it would be fixed |
|---|---|---|
| Action states unreachable (no C-13 calibration) | Every report is `watch`/`abstain` at 0% size | C-13 capital-risk calibration |
| 538 active symbols have no sector | `sector_cap` blocks those packets | `sync_security_master` / sector backfill |
| Base case hardcoded to 0% | No real three-point distribution | `theses` schema change |
| `invalidation_conditions` unreachable from the CLI | Material finding on every new thesis | one flag on `asx thesis revise` |
| `sector-screener` screens all-NULL columns | `/discover-sector` returns nothing | **PR #319, open, James's merge** |
| `segment_map` never built (0045 unapplied) | Peer sets are GICS labels, not real segments | `build_segment_map` |
| The value screen has no measured edge | The set is a reading list, not a signal | a registered model that passes the bar |
| LICs/A-REITs misclassified as `au_equity` | Fund structures reach the value screen, which excludes funds by design | `universe.security_kind` reclassification (`decision-log.md:154`) |
| `HUBS.NYSE` has 0 `rs_financial_statements` rows | Its packet fails nightly; the watchdog stays red | `sync_financial_statements --active-only` never fetches it — `is_active=FALSE` for held US names (`m14_candidate_security_kind_enum`) |
| The brief does not render the packet | `asx decision report` is the only broker-report surface | S6 — the templates exist, nothing calls them |

---

## 14. References

| Subject | Authority |
|---|---|
| Why the model cannot emit targets | `asxos/domain/research/registry/vp.py::RESPONSE_RULE` |
| Why Model A is quarantined | `docs/model-a-decay-analysis-2026-07-11.md`, CLAUDE.md #11 |
| The value screen's four gates | `asxos/domain/discovery/ranker.py` |
| The decision contracts | `asxos/domain/decision_engine/types.py` |
| The broker report render | `asxos/domain/decision_engine/renderer.py::render_broker_report` |
| The 16 challenge rules | `asxos/domain/decision_engine/challenge/rules.py` |
| The research-note command | `.claude/commands/thesis.md` |
| Governance triggers | migrations `0034`, `0036`, `0059` |
| Alert response | `docs/RUNBOOK.md` |
