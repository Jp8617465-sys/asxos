# Session handoff — 2026-09-18, `daily-product` routine

**Status:** current
**Read priority:** read after `docs/session-handoff-2026-09-17-selection.md`. Routine handoffs carry
`-routine`; interactive ones keep the bare date.

**STOP — read first.** Rule #11 stands; nothing here read `signals`. **Incident #327 is still open
and `pipeline-health` is still red.** The code path is fixed (#328); the data is not there yet, and
it cannot be until `weekly-research` runs — which is James's to dispatch. Do not read the merge as
the fix landing.

## What fired

`trig_019hfSFbVCdKQA5PPxJM9MMH` → bound session `session_01HyKLpP6LMTm9wio1oL9e5m`, fire
**2026-09-17T17:37:10Z**, `doc_sha=abfd110`, budget 120 min.

**Two process findings, and both are the kind that look like nothing.**

1. **The fire could not post its START at fire time.** The session was in **plan mode**, which
   forbids every write, so the routine could not execute and the ledger stayed silent while the
   scheduler recorded the wake as delivered. That is exactly the silent-failure shape
   `_preamble.md` §1 exists to detect. James released it at **20:47Z**; START was posted then, with
   the reason on the comment.
2. **The fire was already past its 120-minute budget at START** (T+190). It continued anyway on the
   `AGENTS.md` §7 ground that an open incident outranks the clock — recorded on the ledger rather
   than quietly exceeded. Worth a rule one day: a fire held by the harness should probably restart
   its budget at release, not at fire time.

**Gate, re-run against current state rather than the 17:37 reads** (`main` had moved three commits):

| gate | result |
|---|---|
| (a) `nightly-check` most recent on `main` | `success` |
| (b) no open `incident` issue | **FAILED — #327 open.** Taken as the one thing, the gate's own stated exit |
| (c) no dangling ledger START | clean |
| (d) ready item | PR **#319** open, but `claude/agent-safety-clauses` is a `.claude/` draft — not a routine branch, and not the routine's to merge |

## The one thing — #327, and why its own remedy was wrong

The incident: `HUBS.NYSE`, an approved and actively held thesis, had **zero**
`rs_financial_statements` rows, so `build_decision_case` raised "no admissible yearly income row"
every night. That note is a DEGRADED marker and `check_cron_health` pages on it, so
`pipeline-health` went red and would have stayed red indefinitely.

**#327 blamed `_load_symbols` appending `AND is_active` and proposed widening that filter.**
Measured live before writing code:

| | |
|---|---|
| `rs_security_master` total | **4,439** |
| of which `.AU` | **4,439** |
| of which non-AU | **0** |
| `HUBS.NYSE` in the master | **absent entirely** |

`asxos/ingestion/security_master.py:63-64` fills that table from `exchange_symbols("AU")` — an ASX
master by design. **Dropping the filter cannot surface a row that does not exist.** The proposed fix
would have shipped, changed nothing, and looked done.

**#328 instead** sources held US names from `holding_lots`, the one place that does not route
through `universe.is_active`. `get_us_holding_symbols` **moves** out of `jobs/sync_prices.py` into
`asxos/domain/portfolio/holdings.py::held_foreign_symbols` — a move and not a copy, because
`asxos/domain/prices/fx.py`'s header warns about exactly the stale-copy bug this would otherwise
become. `_load_symbols` returns the master unioned with the held set; **`--limit` caps only the
master half**, since capping the held set away would silently reintroduce the bug on a limited run.

Tests **mutation-checked** per L50 — removing the union turns 3 of 8 red, and
`test_dropping_active_only_is_not_the_fix` pins the superseded remedy so nobody re-derives it from
the issue text.

Class **Amber** (investment output by consequence: it decides whether the only live US holding can
ever receive a decision packet). Reversal one revert; the change writes no data.

## Verification

- `make check`: **4653 passed / 13 skipped**, ruff + mypy clean on 233 files.
- `full-check` ×2 and `targeted-ml-tests` ×2 green on the head before merge; merged `8211290`;
  `nightly-check` dispatched on `main` as the §4 proof.
- Migrations unchanged — ledger head `20260917000622` (0059); 0045 absent, 0042 reserved.
- No migration, no capital action, no Model A output, no Supabase write.

## What is NOT done, and must not be read as done

- **#327 is open.** `rs_financial_statements` gains HUBS rows only when `weekly-research` runs.
  That workflow is **reserved to James** by #311's dispatch-scope rule (scheduled, carries
  `EODHD_API_KEY`). Saturday 16:00 UTC, or his dispatch.
- **Tonight's 22:00 UTC `pipeline-health` will still be red.** Expected, not a regression.
- **Unproven: does EODHD answer its fundamentals endpoint for a US ticker at all?** The sandbox has
  no key, so only the live run settles it. If it does not, the follow-up is to make
  `build_decision_case` *report* the gap rather than raise — which is what actually turns one absent
  row into a nightly red watchdog, and is its own change.

## Yours

- **#327** closes when `rs_financial_statements` holds HUBS rows **and** a `build_decision_packets`
  run reports 0 of 2 failing. Both need `weekly-research`.
- **PR #319** — `.claude/`, drafted for you, still open.
- **K-08** — the three routine deadman URLs; `deadman=unset` again tonight.

## Next fire

Gate (d) will find #327 still open until the data lands, so a fire before Saturday should read this
handoff and **not** re-take the incident: the code half is done and the remaining half is James's
dispatch. Take the ranked queue instead.
