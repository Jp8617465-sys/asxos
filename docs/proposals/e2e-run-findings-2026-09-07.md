# First live end-to-end run — findings (2026-09-07)

**Status:** record of the first execution of the Stage 1→5 chain against the **live production
database** on **live `origin/main` code**. Sprint `production-sprint-r1-2026-09-07.md`; contract
revision **r1**. **Work-Item:** F-E2E/S4.
**Authority:** James, 2026-09-07 — merge train then "test the product end to end on 1 investment
… on live data/code, report issues etc and iterate"; `--persist` writes explicitly granted for this
run. **Machine:** James's Mac, `origin/main` @ `4603d55`, `asxos/` byte-identical to `main`.
**Every figure measured.**

## Headline

**The chain runs, and it was broken in two places that no test could see.** Both defects are fixed
in **#225**; the run then completed and produced a correct, governed, honest `abstain`.

The long-standing blocker was also wrong. Six recorded instances say *"asyncpg cannot complete a
connection to the pooler"* (`roadmap-state.md`, `arbi-run-ledger.md:188`). Those were **remote
sandboxes**. From this machine `asx replay show` returned in **2.7 s** with
`reproducible=yes lineage_complete=True`. **The pooler was never the problem here.**

## What ran, in order

| Stage | Command | Result |
|---|---|---|
| 1 | `asx replay show CBA.AU --cutoff 2026-09-04` | `reproducible=yes`, `lineage_complete=True`, sha `470383a7…` |
| 2 | `asx research run --as-of 2026-09-04 --dry-run` | `outcome=evaluated`, `reproducible=yes`, panel `c5551423…` |
| 3 | `asx candidates build --theme big-4-banks --symbol CBA.AU --as-of 2026-09-04 --dry-run` | **all five quality checks pass**, `quality_passed=True` |
| 4 | `asx decision build --thesis-id 1 --as-of 2026-09-04 --theme big-4-banks --persist` | `packet=dpk-cba-1-2026-09-04 state=abstain challenge=abstain persisted=True` |
| 4 | `asx decision dispose … --verdict defer --persist` | `dispositions_on_packet=1` |
| 5 | `asx decision record-t0 … --persist` | `rows_on_packet=4` |

Persisted, verified by direct query: `decision_packets` 2 · `delivery_receipts` 1 (`cli d6aa2cbc…`)
· `decision_dispositions` 1 (`defer`) · `thesis_outcomes` 4 · `evidence_packets` 2 ·
`challenge_results` 2.

## D1 — `asyncpg.Record` is not a `Mapping` (fixed, #225)

`_income_known_at` opened `if not isinstance(row, Mapping): return None`. Measured:
`issubclass(asyncpg.Record, collections.abc.Mapping)` is **False** (asyncpg 0.31) — `Record` has
`.get()` but is not registered on the ABC. So **every row a live connection returned was discarded**
and `build_decision_case` raised *"no admissible yearly income row for CBA.AU at knowledge cutoff
2026-09-04T23:59:59+00:00"* — while CBA's real row derives `knowledge_date 2026-08-11`, tier
`filed`, and **is** admissible. Class: a type guard written against the test double rather than the
production type.

## D2 — the live book was cited as evidence but never in the frozen packet (fixed, #225)

`load_portfolio_state` mints `portfolio-state-<as_of>`; five register rules cite it
(`challenge/rules.py:213,235,254,266,328`); `DecisionCase` refuses a case that *"cites evidence
outside the frozen packet"* (`types.py:610`). **Every `--context` build therefore failed
validation** — the live-book path had never produced a case. Fixtures supply their own copy of that
item, so CI never saw it; my first cut then hit *"evidence_id values must be unique"*, which is the
fixtures catching the duplicate. Class: two code paths (fixture vs live) that were never reconciled.

**Why CI was green for both.** Every builder fixture is a `dict`, and every test context carries its
own portfolio-state evidence. The suite was testing a shape the database never returns. The new
tests in #225 use a `_RecordLike` row that is asserted **not** to be a `Mapping`, so the regression
cannot silently stop testing anything.

## What the product actually said

The packet is not a stub. Two blocking findings, both correct:

- **`cash_floor`** — post-trade cash **0.000000%** is below the D1 floor of 7.5%, cited against
  `portfolio-state-2026-09-04`. This is the live-measured confirmation of what the P5-01 draft
  (#220) predicted analytically: **no calibration can produce a non-zero size while cash is 0.00.**
- **`price_detached`** — close **160.42** vs entry band **42–45**, detached by **2.653333** of the
  band edge. *(Correction to my own earlier note: I quoted 2.69× computed from the band midpoint;
  the rule measures from the band edge. Same conclusion, different definition.)*

Plus one material (`invalidation_field` — nothing on file can falsify the thesis) and three
honestly unevaluable (`correlation`, `valuation_percentile`, `liquidity_trend`).

**`abstain` is the pass.** The Stage 4 exit gate requires that *"missing evidence forces
abstention"*. The gate's first clause — every identity resolving evidence → thesis → challenge →
portfolio → packet → render → delivery → disposition — is now **satisfied by rows, not by fixtures**.

## Observations, not defects

1. **`decision build --theme X --persist` does not persist the ThemeVersion or CandidateSnapshot.**
   Measured: both tables are still 0 after a persisting build. `--persist` is documented as *"Save
   the case (0048) and receipts (0052)"*, so this is by design — but it means
   `asx decision positive-control`, which reads **persisted** `candidate_snapshots`, will still exit
   3 until `asx candidates build --persist` is run separately. Worth stating because the two
   commands look like they cover each other and do not.
2. **63d and 126d horizons record as `unobservable`.** By construction —
   `calendar.DEFAULT_SESSION_COUNT = 21`, so the forward calendar cannot reach them. Honest
   reporting, not a bug, and it is what the code already documents.
3. **C-5 is smaller than the record says.** `theme_holdings.governance_status` is
   `NOT NULL DEFAULT 'approved'` (`migrations/0035:85-86`), its audit trigger is `BEFORE UPDATE`
   only (`0036:123-125`), `attach_thesis` never names the column, and the member query does not
   filter on it. So **one `asx theme attach` creates a born-approved member with no
   `governance_events` row.** Whether that *should* be the path is a governor call — the audited
   route (`theme holding open --from-agent-run` → `approve`) exists. Flagged because a row that is
   approved-by-default without an audit event is worth knowing about on its own terms.

## Iterate — what this run changes

- **#225 must merge** before any further live run; without it Stage 4 cannot execute at all.
- **The positive control still needs a thesis with a price plan.** Of 13 theses only CBA #1 has a
  stop and target, and it is the negative control by design. Your ruling was to author a fresh
  thesis; the four numbers (`--entry`, `--stop`, `--target`, `--conviction`) are yours — the
  firewall reserves them, and `--from-agent-run` is wired but always fails (no `ThesisProposal`
  schema, backlog D-12).
- **r1 is now half observed.** The negative-control half of the Stage 4 gate is closed with real
  rows. The positive-control half is one thesis away.
