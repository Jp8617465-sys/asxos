# Session handoff — 2026-09-08 (F-VAL/r0 + F-THESIS/r0, out-of-fence)

**Branch:** `claude/f-e2e-broker-report-2026-09-07` @ `9f79ce9` — clean, 0 behind / 25 ahead
of `origin/main`, pushed. **PR #229, draft, 24 commits.** Supersedes #226.

## STOP — read this first

**This session ran out-of-fence.** The hook fence at `.claude/hooks/` never loaded, so
`push-guard.sh` and `unattended-guard.sh` did not fire on any action. James authorised each
step explicitly and the draft-PR ceiling held by convention, not by mechanism. He ended the
session deliberately to restart rooted where the fence loads. **Do not run an unattended
window from an unfenced session.**

**Second: `/Users/jpcino/Desktop/asxos` (the main checkout) is on a broken branch.** It sits
on `claude/arbi-close-2026-08-25`, **41 commits behind `origin/main`**, with **8 dirty files
and 3 unmerged paths** (`decision_engine/staging.py`, `test_decision_builder_wave5.py`,
`test_decision_staging.py`). No merge is in progress — it is a stale index from an aborted
`git reset --hard` in an earlier session. That branch is an August close record predating
25+ merged PRs; it wants abandoning, not merging. **A restart "rooted in the asxos repo"
lands there.** Either `git checkout main && git pull` first, or root in `asxos-wt-aw01`.

None of it blocks anything. It is not a prerequisite to the mission and not a task in it.

## What this session was

Two corrections from James reframed the work:

1. **No thesis has ever been accepted.** Measured: 13 theses, 13 `governance_status='approved'`,
   but **0** `governance_events` for `object_type='thesis'`, **0** `source_run_id`, **0**
   `thesis_evidence`, **0** `conviction_level`. All 13 carry the migration-0033 column
   DEFAULT, never a decision. Eleven are identical 201-character boilerplate with zero-width
   entry bands; the one `active` row (HUBS) has a stop *above* its entry band.
2. **Arbi generates the numbers**, from an institutional valuation process, run reproducibly.
   The prior plan reserved entry/stop/target/conviction to James on a firewall reading; that
   is superseded within the paper-book scope.

## What shipped

**#226 finished** (`7dae5a5` → `e79d804`): `asx decision report` gives the renderer its only
entry point; delivery receipt; content-addressed artifact; `--evaluated-at` byte-reproducible
render; `source_uri` scheme allowlist (26 adversarial tests); VAS/WES brief labelled
hand-authored.

**C1 paper book** (`14894d2`, `0a98590`, `1b625f4`): migration 0053, a **separate table** not
a `book` flag — invisibility is structural, not a `WHERE` clause every future reader must
remember. `asx decision build --paper-book`. ADR **D15**.

**ADR D16** (`31e0a4b`): arbi may author, evidence, price, challenge **and approve** a
thesis, **paper book only**. All three transitions `actor='agent'`. Records what it does not
change: P6 untouched, the charter's hard line unamended for live capital, P3 sizing still
ungranted. Reconciles with §3.6 ("tighten, not relax") **only** by the scope limit.

**F-VAL/r0 Phase 1** (`1d05c70` → `9f79ce9`): residual income on tangible common equity,
Decimal-only, deterministic under a local Decimal context. Scenario probabilities
**pre-registered and sealed before any model ran** —
`a6912403cd2505fe179e63097e57377a1d2b368c53208d88b9ea3516d45165d0`. Ke as a stated band.
Bound read surface with a forbidden-token screen. Migration 0054 with the
`terminal_convention` discriminator. Second convention (Ohlson persistence) with its
degeneracy to `zero_excess` proven by test.

## State at close — all measured

- `make check` green: ruff, mypy (218 files), **4,541 passed / 1 skipped**.
- **Migrations 0053 and 0054 are DRAFTED, NOT APPLIED.** Both in
  `schema_drift.EXPECTED_UNAPPLIED`. Applying is a production write; this session held no
  `apply_migration` tool. Typed procedure for 0053 was delivered in-conversation.
- **Live writes made, under explicit grant:** `theme_holdings` WBC.AU (holding_id 5) via the
  audited path — 3 `governance_events` rows, two `actor='agent'`, one `actor='human'`; and
  the F-E2E fixture rows `f-e2e-tv-big-4-banks-2026-09-04` /
  `f-e2e-cand-big-4-banks-WBC.AU-2026-09-04`, `data_mode='real'`, listable, **retained not
  removable** (append-only, ruled).
- `asx decision positive-control --as-of 2026-09-04` now returns the fixture candidate — the
  first time that command has had an eligible answer.

### The valuation result

Ke band `0.078560` / `0.086810` / `0.095060` (rf `0.048310` FRED `IRLTLT01AUM156N`, a
**monthly** series; ERP 0.055; beta **0.55–0.85 third-party, cited, not measured**).

| sym | close | TBVPS | ROTE | w=0 ÷price | w=0.8 ÷price |
|---|---|---|---|---|---|
| CBA | 160.42 | — | — | **BLOCKED** `currency_null` | — |
| NAB | 39.25 | 18.295 | 0.1191 | 0.628 (1.35×) | 0.699 (1.50×) |
| ANZ | 37.95 | 20.555 | 0.0908 | 0.631 (1.17×) | 0.636 (1.17×) |
| WBC | 34.96 | 16.884 | 0.1121 | 0.637 (1.32×) | 0.693 (1.43×) |

**All three valued names read expensive under both conventions.** No name crosses market at
any beta down to zero. Metric: **0 of 3 valued, 1 blocked** — and it is **not yet a
calibration metric**: 0-of-3 is equally consistent with the market being wrong and the method
being harsh, and nothing yet separates those.

## Pending, requiring James

1. **Ohlson persistence vs a growing-perpetuity third convention.** *Open, and it gates the
   second convention's usefulness.* Measured: convention is worth **0.5–7.1 points of price**
   across w=0→0.8 — roughly 2–3× beta's 1.8–2.8, **not** the 6–12× estimated. The divergence
   is a formulation choice made without asking: at Ke 0.0868 a growing perpetuity at g=3.5%
   capitalises residual income **19.3×** against Ohlson-at-w=0.8's **2.79×**. If the point is
   to size the claim against mainstream practice, Ohlson at any defensible `w` does not get
   near it.
2. **Apply migrations 0053 and 0054.**
3. **The operative persistence value needs pre-registering** before use in a thesis rather
   than a comparison — a grid was reported, no number picked.
4. **C-22 ruling**: currency-changepoint comparability — translate at a stated rate, or refuse
   with a named gap.
5. **Phase 3 blocker to verify**: `theses/service.py:803-828` does not forward an `actor`.
   If `asx thesis approve` cannot record `actor='agent'` after Phase 3, **stop and report —
   do not route approval to James.** His datapoint is the Phase 5 disposition.
6. **Model for the fenced window.** `.claude/settings.json` has **no model key** — the only
   `model` hit is an unrelated `Edit(...)` permission. The Opus pin could not be confirmed.

## Tickets filed, not fixed

`C-16` legacy-marker the 13 theses · `C-17` `stop < entry < target` CHECK (blocked on ruling
the HUBS row) · `C-18` five `fundamentals` columns with no writer across 143,715 rows ·
`C-19` sector-inapplicable metrics in Screen #1 · `C-20` currency missing on 72,904 rows /
1,177 symbols · `C-21` beta provenance · `C-22` currency-changepoint comparability ·
`E-19` AXJO.INDX backfill. All `attended` or james-owned so the standing lane cannot start
what was filed not fixed.

## Lessons — three of mine, all caught by James

**1. A gap collected is not a gate.** The Phase 1 run reported CBA as carrying a currency gap
**and valued it anyway**: gaps were appended to a list and printed beside the numbers, with
no `raise`, while `ValuationBlocked` sat defined and called by nothing. The writeup then
claimed "the valuation gates on currency" — describing intent as implementation. Re-running
with the gate firing withdrew CBA and left NAB/ANZ/WBC byte-identical. *A gate that was
silently passable is worth recording even where the output survives it.*

**2. `IS NULL` is not absence.** C-20 was first filed at 70,393 rows because the query tested
`currency IS NULL`; 2,511 further rows carry an empty string. The loader's own comment at
`financial_statements.py:222-230` had already said so. There is now **one** absence predicate
(`valuation/absence.py`), never repeated inline.

**3. Constants that disagree with shipped output.** The beta band shipped at 0.90–1.20 while
the reviewed figure was 0.55–0.85, and no output would have shown the disagreement. Corrected
in `36a3643`; C-21 files the structural fix — a dated third-party band belongs on the
artifact alongside rf and ERP, not in a module constant.

**Also worth keeping:** two backlog tickets I first filed as arbi-owned build routes with
`migrations/` paths were rejected by the repo's own `test_seed_parses`, and a third became
lane-eligible and would have had the standing `backlog-roll` lane start building something
explicitly filed *not fixed*. The tests were right; nothing was re-pinned.

## Not started

Phase 2's builder with the gate firing, cutoff enforcement plus its test (the
`knowledge_cutoff::date = as_of` CHECK proves two columns agree and nothing about what the
run consumed — **constraint plus test, or it is a comment**), the CLI, persistence to 0054.
Then Phases 3–5: the authoring path's five blockers, the first accepted thesis, the E2E onto
the paper book.
