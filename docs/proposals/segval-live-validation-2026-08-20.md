# L0 substrate: live-data validation + the three patches arbi cannot apply

**Status:** findings recorded 2026-08-20; **two** code fixes landed on this branch (the
derivation and the producer that originates the bad values), **three** patches pending James —
each blocked by a session Edit denial, not a judgement call.
**Correction 2026-08-22:** Patch 0 is **overtaken** — `0044` was applied 2026-08-21 and its
`COMMENT ON COLUMN` was corrected at apply time. See the banner on Patch 0 for what remains
(a repo-side file/database reconciliation, not a database change). Patches 1 and 2 are
unaffected by this annotation.
**Scope:** dry-runs the D1/D2/D3 substrate merged in PR #142 against **production, read-only**,
because every test shipped with it was `FakeConn`-mocked. Records what live data falsified.
**Owner:** arbi (findings + the two reversible code fixes); James (the three patches below).
**Supersedes:** nothing. Amends the **D3** section and **§8.1** of
`docs/proposals/segment-valuation-portfolio-architecture-2026-08-18.md` with measured numbers.
**Deliberately NOT amended:** that doc's **D1** and **§9 appendix**, which still carry the
superseded "612 non-AUD / 102 unknown-currency / 14-currency spread" figures. Those are scoped
to a different population (symbols with PIT rows) than this validation's (`rs_financial_statements`
yearly), so re-numbering them in place would swap one unscoped figure for another. They need
their own re-measurement, tracked as follow-up, not a blind find-and-replace.

---

## Why this exists

PR #142's substrate shipped with 69 green tests, all driven by `FakeConn` — no query ever
reached Postgres. This repo already learned that this is not sufficient
(`.claude/rules/portfolio-conventions.md`, "Verification lesson (Phase 2a live-fire finding)":
a governance helper passed every mocked test **and two full review loops** while being wrong
against the real triggers, because mocks don't enforce semantics the DB does).

So the merged code was dry-run against production with read-only SELECTs before anything
scheduled could touch it. Four findings follow. **One is a defect in the shipped code.**

---

## F1 — DEFECT (fixed on this branch): blank currency stored as `''` rather than NULL

`compute_pit_factors` carried currency through as:

```python
currency = (income or {}).get("currency") or (balance or {}).get("currency")
```

Live `rs_financial_statements` (period_type='yearly') carries **three kinds** of value where the
code assumed two — a real code, NULL, and blank:

**Partial table — the four values that matter here, out of 20 distinct currency codes** (NZD,
EUR, CAD, CNY, INR, GBP and 10 more are omitted; the rows below do **not** sum to the table
total). Symbol counts **overlap**: 1,159 symbols appear in more than one bucket, because
different periods and statement types can carry different values for the same symbol — so these
columns are not a partition and must not be added together.

| currency | rows | symbols |
|---|---|---|
| `AUD` | 129,866 | 3,122 |
| *NULL* | 10,590 | 861 |
| `USD` | 8,675 | 289 |
| `''` (blank) | 1,150 | **86** |

Distinct symbols with **at least one** unusable (NULL-or-blank) yearly row: **947**, measured
directly rather than by summing the two rows above — of 3,362 symbols with yearly statements.

When income **and** balance are both `''`, Python's `or` returns the last falsy operand — so
the column receives `''`, not NULL. A downstream `WHERE currency IS NULL` (the obvious way to
find unconverted reporters before the FX step) would silently skip those 86 symbols.

Every fixture in `tests/test_fundamentals_pit.py` used `"USD"` or `None`. None used `''`.
That is precisely the gap mocks cannot close: the fixture author picks the inputs, and blank
never occurs to you until the data shows it.

**Fixed** by a `_currency()` normaliser mirroring the file's existing `_num()` convention
(`x == ""` → None), plus five tests: two pinning the live-observed blank case, and three
covering values the census does **not** report seeing (`'   '`, `'  AUD  '`, `'aud'`) — those
three are deliberate hardening against a vendor change, not regressions, and are labelled as
such so a later reader does not mistake them for observed data.

**Fixed at the producer too.** `asxos/ingestion/financial_statements.py` had the identical
`a or b` idiom and is what writes the blanks in the first place — while `_sector_industry()`,
fourteen lines below it in the same file, already defused that exact trap with a trailing
`or None`. The producer line was simply missed when that fix was made. Note the scope
difference: the PIT table **self-heals** (every run re-derives the whole symbol space through
`_currency()`), whereas `rs_financial_statements` only stops *accruing* blanks — its 1,150
legacy rows are not backfilled, so `WHERE (currency IS NULL OR currency = '')` remains the
correct predicate on that table.

**Also case-folded, as prevention rather than repair.** `0044`'s `COMMENT ON COLUMN` mandates
that any aggregate `GROUP BY currency`, so `'AUD'` vs `'aud'` would silently split one bucket
into two — the same duplicate-bucket defect `segment_map` exists to prevent in the sector
dimension. Measured 2026-08-20: all 20 live values are already upper-case ISO-4217 (`AUD BRL
CAD CNY EUR GBP HKD IDR ILS INR JPY MXN MYR NOK NZD PGK SGD TWD USD ZAR`), zero non-uppercase
rows — so this is a no-op today and cheap insurance against a vendor change. A shape check
(`^[A-Z]{3}$` → drop) was considered and **rejected**: silently discarding an unrecognised
currency is exactly the graceful-degradation rule #10 forbids. An unexpected value surfacing
as its own visible bucket is the loud failure.

---

## F2 — the `universe.sector` fallback is dead code (0 of 4,418)

`resolve_segment_key()` prefers `gics_sector` and falls back to `universe.sector`. Replaying
the exact resolver logic in SQL against live data:

| outcome | symbols |
|---|---|
| resolved via `gics_sector` | 3,661 |
| resolved via `universe.sector` fallback | **0** |
| unresolved | 757 (17.1%) |
| **total** | 4,418 |

The fallback branch — with dedicated tests — never fires. Diagnosis: of the 757 symbols whose
`gics_sector` is unresolvable, 242 have no `universe` row at all and the other **515 have
`universe.sector = ''`**. Zero have a usable value.

This is not a bug — the resolver correctly declines to map blanks. It falsifies a **design
premise**: D3 treated the two columns as independent vocabularies to reconcile, but both are
propagated from the same EODHD `General.Sector` field, so they are blank *together*. There is
no second opinion to fall back to.

Cited to the code, not to the architecture doc — that doc describes the two columns as
Morningstar-vs-GICS and never states the shared origin, so it is not the authority here:
`asxos/ingestion/financial_statements.py:27-28` ("EODHD exposes the Morningstar-style `Sector`;
`GicSector` is NULL on the current plan — **same source as production `universe.sector`**") and
`:190` (`general.get("GicSector") or general.get("Sector")`), against
`asxos/ingestion/fundamentals.py:58-61` and `asxos/ingestion/universe.py:75`
(`r.get("Sector") or ""`) — that last `or ""` being the direct mechanical explanation for the
515 rows sitting at `universe.sector = ''`.

**Recommendation:** keep the branch (it is correct, cheap, and a real second source could
appear), but stop describing cross-column fallback as D3's mechanism. Its actual mechanism is
F3.

---

## F3 — what D3 actually buys: 233 symbols de-duplicated

Splitting the 3,661 GICS resolutions by whether the alias table changed anything:

| outcome | symbols |
|---|---|
| already canonical GICS (pass-through) | 3,428 |
| **repaired by the alias table** | **233** |

So the "Financials"/"Financial Services", "Materials"/"Basic Materials" duplication that D3
exists to kill is **233 symbols, 5.3% of the universe** — real and worth having, since a
duplicated segment key corrupts every aggregate built on it, but materially smaller than the
doc's framing implies. The repair happens *within* `gics_sector`, which carries Morningstar
leakage — not across the two columns.

---

## F4 — scope corrections for the deferred work

- **20 distinct reporting currencies** live (excluding NULL/blank), not the "~12" D1 estimated
  for widening `fx_rates`. The deferred FX slice is ~65% larger than scoped.
- **757 symbols (17.1%) are unclassifiable by any code path.** No resolver change reaches them;
  they need an upstream ingestion fix or an explicit `unclassified` bucket that downstream
  aggregates exclude by name rather than silently drop.

## D2 verified clean

The hybrid filter that ships in `sync_financial_statements.py` was replayed as live SQL:
**2,393 active → 2,350**, excluding 43 hybrids. Behaves exactly as designed.

---

## Patch 0 (JAMES) — fix `0044`'s comments BEFORE applying it

> **OVERTAKEN 2026-08-22 — the apply already happened, and Patch 0 half-landed.** `0044` was
> applied to production **2026-08-21** as `20260821080458` (ledger count **97**);
> `rs_fundamentals_pit.currency` is present. Per `product/james-inbox.md`'s 2026-08-21 row, the
> applying session corrected the `COMMENT ON COLUMN` text *at apply time*, so **Edit 2 is in the
> database**. What did **not** happen is the repo-side edit: `migrations/0044_*.sql` still
> carries the old `612 / 14 / 102` figures at `:9-10` and `:29` and still reads `DRAFT — NOT
> APPLIED`, so the file and the database now disagree about both status and comment text.
>
> **What is still actionable, and what is not.** Edit 2 must **not** be re-applied to the
> database — `COMMENT ON COLUMN` is already correct there, and a second migration to restate it
> would be churn. The remaining work is bringing the repo file into line with production as a
> documentation correction (`migrations/**` is Edit-denied to agents — James's action, listed in
> the 2026-08-22 docs-pass handoff). Edit 1 (`:9-10`, header prose only, never entered the DB)
> is still worth landing in the same pass. `0045_segment_map.sql` remains genuinely unapplied
> and still needs no change.

**Do this in the same sitting as the apply.** `migrations/0044_fundamentals_pit_currency.sql`
carries two figures from an unscoped 2026-08-18 count that this validation supersedes, and one
of them lands in `COMMENT ON COLUMN` — **permanent DB metadata**, much harder to correct after
the fact than before.

**All three** figures in that header come from one unscoped 2026-08-18 query, and all three are
wrong. Re-measured 2026-08-20 against `rs_financial_statements WHERE period_type='yearly'` —
the same population the PIT derivation actually reads:

| Line | Says | Actually | Gap |
|---|---|---|---|
| `:9` | "612 symbols report in a non-AUD currency" | **530** | −82 |
| `:9-10` | "14 distinct currencies observed live 2026-08-18" | **20** | +6 |
| `:29` | "was unrecorded (102 symbols observed 2026-08-18)" | **947** (861 NULL + 86 blank) | **9×** |

The 9× miss is the original query never looking for the blank-string state — the same blind
spot as the F1 defect itself. That is also why the count is worth re-stating *with its scope*
rather than just re-numbering.

**Edit 1** — replace lines 9-10 **in full** (the parenthetical spans both lines, so a
single-line find-and-replace will not match):

```sql
-- monetary column on rs_fundamentals_pit is a cross-currency ratio today —
-- 530 symbols report in a non-AUD currency (20 distinct currencies), and
-- nothing records which. Measured 2026-08-20 against rs_financial_statements
-- WHERE period_type='yearly' — the same population the PIT derivation reads;
-- supersedes an unscoped 2026-08-18 count (612 symbols / 14 currencies).
-- This column is the storage-
```

(keep the existing `-- layer half of the fix: ...` line that follows unchanged.)

**Edit 2** — replace **lines 25-31 in full** (the whole `COMMENT ON COLUMN` statement). A
fragment-level find-and-replace does not work here: the replacement text needs its own quoting,
and splicing it mid-literal either doubles a quote (invalid SQL) or orphans the
`. Any aggregate that '` connective that line 30 depends on.

```sql
COMMENT ON COLUMN rs_fundamentals_pit.currency IS
    'Reporting currency of the source statement, carried through from '
    'rs_financial_statements.currency, trimmed and upper-cased. NULL for '
    'pre-existing rows written before this column existed, and for any symbol '
    'whose income AND balance statements both lack a usable currency. Any '
    'aggregate that sums monetary columns across rows MUST group by this '
    'column (or filter to a single value) rather than assume AUD.';
```

**Deliberately no count in the COMMENT.** The previous text put one there, and a count is the
wrong thing to freeze into permanent schema metadata for two reasons. First it rots — that is
this whole patch. Second, and worse, the obvious count answers a *different question* than the
comment asks: `compute_pit_factors` falls back income→balance, so a symbol with *some* blank
statement rows can still land a non-NULL PIT currency. A "947 symbols" figure (symbols with any
unusable yearly statement row — a verified distinct count, not `861 + 86` summed) is therefore
**not** the count of symbols whose PIT currency ends up NULL. Describing the *condition* is
correct and durable; quantifying it in DDL is neither. Live figures stay in this document,
which states its scope.

Migration `0045_segment_map.sql` needs no change. The DDL in both is correct — this is comment
text only, so applying as-is is *functionally* safe; it just bakes three wrong numbers into the
schema's own documentation, one of them permanently via `COMMENT ON COLUMN`.

---

## Patch 1 (JAMES) — `detect_theme_stages` has no Actions home

**Severity: live gap, not tidiness.** James ruled this job KEEP (roadmap-state Amendment F).
It was a Render cron at 20:55 UTC Sun–Thu — the slot named in its own docstring — and was
missed in the 2026-08-08 Actions migration. No workflow references it, so theme stages have
gone **un-refreshed since Render was deleted 2026-08-12**.

Placement is not free: `asxos/domain/brief/collectors/theme_dashboard.py:38,65,71-72` reads
`themes.stage_suggested` and renders the "(AI suggests)" divergence row, so the job must run
**before** `compose_brief` or every brief shows yesterday's suggestion.

Its only price input is **`prices`** — so it must follow `Sync prices`, and that is the whole
upstream constraint. Do **not** describe it as depending on `underlying_prices` or
`news_sentiment`: `jobs/detect_theme_stages.py:46` explicitly says "Use prices table since
underlying_prices is only for tracked underlyings" and never queries that table, and `:127`
hardcodes `news_sentiment=None`. The job's own module docstring (`:8-9`) claims both and is
aspirational — the code is the authority, and the parent architecture doc already records this
correctly ("passes `news_sentiment=None` ... stage suggestions currently rest on price breadth
and momentum only"). Its other inputs are `themes` and `theme_holdings`, neither of which the
daily chain writes.

Needs no new secret or config field (`JobMonitor(_JOB, as_of)` passes no healthcheck URL).

Apply to `.github/workflows/daily-brief.yml`, between `Ingest sentiment` and
`Compose and send brief`:

```yaml
      - name: Ingest sentiment
        run: python jobs/ingest_sentiment.py

      # Placed HERE, not after the brief, because the brief consumes its output:
      # asxos/domain/brief/collectors/theme_dashboard.py reads themes.stage_suggested
      # and renders the "(AI suggests)" divergence row. Running it after the send
      # would make every brief show yesterday's suggestion.
      #
      # Upstream it needs only `Sync prices` -- the prices table is its sole price
      # input. It does NOT read underlying_prices (see the comment at
      # jobs/detect_theme_stages.py:46) and it passes news_sentiment=None (:127),
      # despite what that job's own module docstring claims.
      #
      # Never had an Actions home: it was a Render cron (20:55 UTC Sun-Thu, the slot
      # named in the job's docstring) and was missed in the 2026-08-08 migration, so
      # theme stages went un-refreshed from at latest the Render deletion
      # (2026-08-12) until this step landed. Writes stage_suggested/stage_metadata
      # only -- never themes.stage, which stays user-confirmed via `asx theme stage`.
      - name: Detect theme stages
        run: python jobs/detect_theme_stages.py

      - name: Compose and send brief
        run: python jobs/compose_brief.py
```

`schedule:` only fires from the default branch, so this is live once merged.

---

## Patch 2 (JAMES) — retire `thesis-coherence-guard` before the next `/pm-review`

**Severity: actively misleading, capital-adjacent.** Found by auditing `CLAUDE.md` against
post-#144 reality.

`.claude/agents/thesis-coherence-guard.md` works by running
`SELECT signal_label, prob_up, shap_factors FROM signals WHERE symbol = $1 AND model = 'model_a'
ORDER BY as_of DESC LIMIT 1`. PR #144 deleted every writer to `signals` and deleted the SHAP
producer (`asxos/domain/brief/shap.py`). The table survives, frozen.

The agent therefore still returns rows — **stale Model A SHAP evidence, presented as current**,
into the `/pm-review` synthesis that informs real holding decisions. That is a worse failure
mode than an error, and it sits adjacent to rule #11: the rule forbids *using Model A output as
a basis for real capital decisions*, and this path serves exactly that output without saying
it is frozen. The agent file was not touched by #144.

**Amputate, don't retire — the agent is half alive.** Only steps 1-2 are dead:

| Step | Source | State |
|---|---|---|
| 1-2 · signal-vs-thesis SHAP coherence | `signals` (`model='model_a'`) | **DEAD** — frozen, no writer |
| 4 · revision-cadence / thesis-fatigue check | `thesis_revisions` JOIN `theses` | **LIVE**, model-independent |

Step 4 detects a run of `reviewed_no_change` revisions with no `assumption_change` — thesis
fatigue rather than evidence-based holding. That is exactly the model-independent discipline
this product is now built around, and deleting the agent wholesale would throw it away. Prefer
cutting the SHAP steps and keeping the agent as a discipline check.

**Two containment notes, because the obvious control is insufficient:**

1. "Don't run `/pm-review`" does **not** cover every path. The agent's frontmatter description
   says "Use **PROACTIVELY** when a signal label changes on an active holding" — an instruction
   to the main loop to auto-invoke it outside the command.
2. The warning currently lives only in `james-inbox.md` and this doc. Nothing in
   `.claude/commands/pm-review.md` or `CLAUDE.md` warns a future session. For something
   capital-adjacent, relying on someone having read the inbox first is a weak control — the
   warning belongs in the agent file itself.

**Edit surface** (larger than "drop it from the fan-out" implies, so it is listed rather than
left to be found): `.claude/commands/pm-review.md:7,20,22,27,35,78` (each "five" → "four", the
table row, and the worked example at `:47-48`, which is built on a Model A signal line);
`.claude/agents/README.md:110,112,132`; `CLAUDE.md:228,234,240-242`.

A fuller `CLAUDE.md` staleness audit (17 items — obsolete "Known test environment gaps"
section, rule #11 framing, migration ceiling, `ml-conventions.md` description, four dead slash
commands, a subagent breakdown that sums to 23 of 25) is summarised in the session handoff;
none of the remaining items are correctness-critical the way this one is.

None of the three patches could be applied by arbi — each is blocked by a distinct Edit denial
in this session's permission settings: Patch 0 by `Edit(/migrations/**)`, Patch 1 by
`Edit(/.github/workflows/**)`, Patch 2 by `Edit(/.claude/agents/**)`,
`Edit(/.claude/commands/**)` and `Edit(/CLAUDE.md)`. Tool boundaries, not judgement calls —
but note Patches 1 and 2 could instead be routed as a **draft PR** for merge approval rather
than hand-pasted, which is the more normal shape for this repo. Patch 0 cannot: applying a
migration is James's either way.
