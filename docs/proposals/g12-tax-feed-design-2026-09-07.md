# G12 — the tax feed: what a `readiness="pass"` actually requires (design spike, 2026-09-07)

**Status:** design spike for James's ruling — **no code.** Sprint `production-sprint-r1-2026-09-07.md`
slice **S3a**; backlog **C-14** (design half). **Work-Item:** F-E2E/S3a · **Contract-Revision:** r1.
**Question:** *what does a `TaxAssessmentReference` with `readiness="pass"` need for a new **paper**
ASX position, and can it be built from data that already exists?*
**Answer in one line:** yes for the security-level characterisation, no for a position-level one —
and the blocking decision is not data, it is **what a `pass` is asserting**.
**Every figure measured** 2026-09-07 (`supabase-ro`, `git grep` at `fd6172c`) unless marked *inferred*.
Model-independent throughout: no `signals`, no `asxos.domain.models`, rule #11 untouched.

---

## 1. What the contract refuses today, and the three gates that hold it

`asxos/domain/results_review/contracts.py:230-251` is the only constructor in the package, and its
docstring is explicit (`:237-243`):

> "Build the only tax reference this package can produce: an unresolved one. … This package
> deliberately offers **NO constructor for `readiness="pass"`** — a pass can only come from the named
> producers in `TAX_ASSESSMENT_PRODUCERS`, fed with real dividend and realised-gain inputs, in a
> later work order."

`TAX_ASSESSMENT_PRODUCERS` (`:216-219`) is two dotted **strings**, not callables —
`asxos.domain.tax.positions.tax_view_individual` and `…tax_view_smsf`. So **S3b must add a
pass-constructor somewhere else**; this package will not host one.

Three separate gates then stand between a `pass` and an action state. All three must be satisfied,
and two are commonly missed:

| # | Gate | Where |
|---|---|---|
| 1 | `readiness != "pass"` forbids an action state | `decision_engine/types.py:514` |
| 2 | a non-empty `missing_or_uncertain_inputs` **independently** forbids one | `types.py:506-507` — and `builder.py:494` seeds it with `"Real dividend/realised-gains feed for tax readiness (G12)"`, so leaving that line in blocks an action state *even with a pass* |
| 3 | `readiness == "pass"` while `data_mode != "real"` **fails** the `tax_readiness_earned` gate — *"the claim is unearned"* | `results_review/gates.py:281-289` |
| — | structural: `applicability="uncertain"` + `readiness="pass"` is unconstructable | `types.py:414-415` |

**A `pass` therefore forces `applicability="applicable"`** — an affirmative claim that the tax
treatment *is* determinable for this position — **on real-mode inputs.** That is the whole design
problem; the arithmetic is the easy part.

**Worth stating plainly:** the state machine never needs an action state for r1. `builder.py:600`
emits only `watch`/`abstain` and `:601,632,676` force `ZERO_SIZE`. **`readiness="pass"` with state
`watch` is legal and is the honest target** — S3b does not have to unlock `initiate`.

## 2. The producers and their real inputs

`asxos/domain/tax/positions.py`, both keyword-only:

- `tax_view_individual(*, lots, realised_gains, dividends, config: IndividualConfig, today=None)` (`:44-51`)
- `tax_view_smsf(*, lots, realised_gains, dividends, config: SmsfConfig, tsb_ref=None, div296_*…, today=None)` (`:107-119`)

Beyond dividends and gains they need a **config**, and here is the finding that changes the shape of
S3b:

> **`tax_settings` has existed since migration `0004_tax_alpha.sql:16-36` with a column for every
> config field — `marginal_rate`, `medicare_levy_rate`, `fund_pension_proportion`,
> `fund_segregated_eligible`, `div296_election_made`, `div296_reset_date`,
> `carried_forward_capital_loss`, `franking_refundable`, PK `(financial_year, account_type)` — and
> has *zero* readers.** [measured] `git grep -l tax_settings origin/main -- asxos/ jobs/ scripts/
> tests/` returns exactly one file, `asxos/schema_drift.py`, and that is a drift note, not a read.
> `universe.corporate_tax_rate` (`0004:13-14`) likewise has zero readers.

Today the rates come from CLI flags with defaults (`asxos/cli/tax.py:14` `marginal_rate=0.37`,
`:15-17` pension proportion, `:18` carried-forward loss). The G12 hardcode itself is one line
(`cli/tax.py:84`):

```python
view = tax_view_individual(lots=lots, realised_gains=[], dividends=[], config=cfg)
```

*(Citation repair owed: `contracts.py:222-223` cites `asxos/cli/tax.py:93,99` for the hardcode. On
`fd6172c` the real sites are `:84` (individual) and `:90-96` (SMSF); `:99` is a Rich table column.)*

## 3. Data availability — field by field, measured

`rs_corporate_actions` (`migrations/0027_research_store.sql:51-62`) is the **only** per-event dividend
source. `public.dividend_history` and `dividends_calendar` were dropped (`0030:50`);
`fundamentals.dividend_yield` and `rs_fundamentals_pit.dividend_ttm` are derived ratios, not events.

Live shape [measured 2026-09-07]: **38,803 dividend rows across 1,827 symbols.**

| `Dividend` field (`tax/types.py:67-87`) | Status | Evidence |
|---|---|---|
| `symbol` | **available** | same `CBA.AU` namespace as `universe` / `holding_lots` |
| `pay_date` (required, non-optional) | **available, 17.2 % NULL** | 6,686 of 38,803 NULL; **441 of 1,827** most-recent-per-symbol NULL (24.1 %). Needs a documented rule (fall back to `ex_date`, or drop the row) |
| `cash_dividend` (**total AUD**, not per share — used raw at `franking.py:28`) | **derivable only with a quantity** | `dividend_amount` is **per share** (`0027:56`). A paper position has no lot, so the quantity has **no source** — it would have to come from the sizer, or the design adopts a per-unit convention |
| `franking_pct` (fraction 0–1, validated `types.py:86-87`) | **available, 17.5 % NULL, unit conversion needed** | 6,803 of 38,803 NULL; **448 of 1,827** most-recent NULL (24.5 % — elevated on exactly the dividend a new position would receive, but *not* the dominant case). Stored 0..100, contract wants 0..1 |
| `corporate_tax_rate` | **derivable, one join, unread today** | `universe.corporate_tax_rate` default 0.30; nobody classifies base-rate entities (spec §3) |
| `franking_credit_override` (the registry-statement dollar value) | **NO SOURCE** | spec §1:11 / §3:43 say trust the registry statement; **no registry-statement table exists in any migration** |
| currency | **no column** (available upstream) | EODHD returns `currency`; ingestion drops it (`asxos/ingestion/corporate_actions.py:10-13`) |
| DRP | **NO SOURCE** | no column, no ingested field |
| `CapitalGain` ×4 (`types.py:90-97`) | **honestly empty is correct** | `positions.py:55` / `:123` gate the CGT branch on `if realised_gains:`, so `net_capital_gain=None` is a valid `TaxView` — a new paper position has no disposals |

**Correction to the sprint plan.** `production-sprint-r1-2026-09-07.md:80` says "no franking source".
That is **too strong** and is corrected here: `rs_corporate_actions.franking_pct` *is* a franking
source with 82.5 % coverage. The real gaps are (a) no franking-**credit** dollar figure, which is what
spec §3:43 says to trust, and (b) NULLs concentrated on the most recent event.

**And for the candidate class that matters, coverage is complete** [measured]: CBA.AU's last six
dividends are all fully populated — most recent ex 2026-08-19, pay 2026-09-29, $2.70, **100 % franked**.

## 4. The collision the spike exists to surface

The spec and the schema give **opposite** rules for a missing franking percentage:

- `docs/foundation/spec/tax-alpha.md:49` — *"When a dividend record is missing its franking
  percentage, **treat as unfranked (franking_pct = 0)**. Silent assumption … is forbidden."*
- `migrations/0027_research_store.sql:57` — *"`franking_pct` … **NULL = undeclared (NOT 0)**"*, and
  `asxos/ingestion/corporate_actions.py:14-16` calls the distinction *"material"*, COALESCEing on
  upsert so a later NULL never overwrites a known value.

Both are deliberate and they cannot both govern the feed. On 448 most-recent dividends the spec's
rule would systematically **understate** franking; the schema's rule leaves the field unusable
without a fallback. **This is a spec-vs-schema conflict, not an implementation choice** — it is
decision 2 below.

## 5. The call-site delta — not a one-line swap

`builder.py:643-648` constructs the unresolved reference from four literals, with no DB read. To
call a real producer, S3b needs **four** changes, one of which is governed:

1. **A dividend read the builder is currently forbidden.** `pit_db._ADMISSIBLE_TABLES`
   (`asxos/domain/decision_engine/pit_db.py:68-75`) allows only `rs_security_master`,
   `rs_financial_statements`, `rs_fundamentals_pit`, `prices`. `rs_corporate_actions` is **not** on
   it, and `holding_lots` is on `_FORBIDDEN` (`:59`). Widening the allowlist is a governed edit.
2. **The tax knobs must reach the builder** — neither `ChallengeContext` (`:168-184`) nor
   `PortfolioState` carries `account_type` or `marginal_rate`. Either a new parameter or a
   `tax_settings` + `profiles.account_type` read.
3. **De-seed `missing_or_uncertain_inputs`** (`builder.py:494`) or gate 2 blocks regardless.
4. **A pass-constructor** in `asxos/domain/tax/`, since `contracts.py` refuses to host one.

Pinned by `tests/test_decision_builder_wave5.py:144`, `test_decision_engine_persistence.py:270-273`,
`test_results_review_contracts.py:264-269`. The only `pass` in the repo today is the synthetic demo
fixture (`demo.py:295-302`).

## 6. Scope — is "dividends only, no realised gains" a coherent `pass`?

**Mechanically yes** (§3, last row). **Contractually, it depends on what the pass asserts.** The spec
scopes the module to *held* positions — §1:7 *"for each position the user holds"* — and §1:11 *"the
system does not derive X — the user or an ingestion process supplies it."* A paper position is not
held, so any dividend figure attached to it is forward-looking, and the spec's only precedent for
that is §5.4, explicitly *"a decision-support hint, not a tax computation."* Foreign holdings are out
of v1 scope (§1:9), which is why HUBS.NYSE — the only open lot — cannot be the vehicle; an **ASX**
paper position is in scope by asset class.

## 7. The three decisions for James

> **D1 — What does `readiness="pass"` assert for a position that does not exist yet?**
> **(a) Security-level characterisation** *(recommended)* — trailing-12-month dividends and franking
> for the **security**, from `rs_corporate_actions`, quantity-free or per-unit. Real-mode, buildable
> this sprint, needs no quantity, and is true independent of the eventual position size.
> **(b) Position-level prospective figure** — an after-tax number for the proposed position. Needs a
> quantity from the sizer and invents a forward-looking convention the spec does not have (§5.4-class
> heuristic). *This ruling also settles whether `applicability` for a paper ASX name is `applicable`
> or stays `uncertain`.*

> **D2 — Missing franking: which of three?** (i) follow **spec §3:49** and treat NULL as 0 % —
> spec-sanctioned, but understates on 448 of 1,827 most-recent dividends; (ii) **carry the last
> non-null** franking for the symbol — defensible for a stable franker like CBA, an inference the
> spec does not authorise; (iii) **James supplies franking per candidate** (§1:11, "trust the share
> registry statement"), and absent input the reference stays `uncertain` / `unknown`.
> *Whichever wins, `migrations/0027:57`'s "NULL ≠ 0" comment or spec §3:49 must be amended so they
> stop contradicting each other.*

> **D3 — Do we un-orphan `tax_settings`?** It has every column S3b needs and zero readers since
> migration 0004. Either S3b reads it (+ `profiles.account_type`) — small, closes a long-standing
> orphan — or the rates stay parameters and the table stays dead. Bundled: widening
> `pit_db._ADMISSIBLE_TABLES` to admit `rs_corporate_actions` is unavoidable for any builder-side
> dividend read, and `holding_lots` being `_FORBIDDEN` independently argues for D1(a).

## 8. What this spike does not do

No code, no migration, no allowlist edit, no spec amendment — those are S3b, after the ruling. It
recommends no security, size or trade; it reads no `signals`. If all three decisions are deferred,
the packet keeps emitting `readiness="unknown"`, which is a **valid and honest** outcome, not a bug.
