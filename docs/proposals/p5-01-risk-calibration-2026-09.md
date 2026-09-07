# P5-01 — Capital/risk calibration for Stage 4: a ruling-ready proposal (2026-09-07)

**Status:** **P5 draft — changes nothing until James merges an edit to `portfolio-policy.md`.**
P5 is "propose a change to `portfolio-policy.md`", draft-only, never standing
(`arbi-permission-model.md:171`). This document is not a memo, not advice, and not an order: it
names the numbers the governor deferred under **F4** ("James must complete the capital/risk
calibration before Stage 4", `target-architecture.md` F4; `portfolio-policy.md` Objectives) as
**options with one recommended default each**, every number traced to a constraint that already
exists in the repo or the active profile, and ends with the single ruling James is asked to make.
**Sprint:** `docs/proposals/production-sprint-r1-2026-09-07.md` slice **S2** (backlog C-13a → C-13;
inbox H-32). **Work-Item:** F-E2E/S2 · **Contract-Revision:** r1.
**Model independence:** nothing here reads `signals`, the allocator's Model A path, or any
`asxos.domain.models` import; every quantity is a policy constant, a profile field, or a live
portfolio/packet value read through the read-only role. Rule #11 is untouched.
**Every figure is measured** (2026-09-07 ~05:00 UTC, `supabase-ro`) unless marked *inferred*.

---

## 1. What F4 deferred, and what already binds

F4 deferred "James-specific numeric loss and drawdown limits" and made five universal gates
non-deferrable (no leverage, no Model A capital input, no action on unresolved tradeability, no
action on stale/missing evidence, no broker execution). Since then the ADR and Wave 5 fixed more of
the mandate than the policy file records:

| Constraint | Value today | Where it is enforced | Ruled by |
|---|---|---|---|
| Cash floor | **7.5 %** | `challenge/rules.py:40` `CASH_FLOOR_PCT`; `sizer.py` clamps the profile to ≥ 7.5 | ADR **D1** (2026-08-23) |
| Gross leverage | **0 %** | `rules.py:41`; `headroom_max_pct` returns 0 on any borrowing | ADR **D2** |
| Sector cap | **30 %** | `rules.py:42`; sizer headroom | ADR **D8** |
| Per-name cap | **10 %** (`per_name_cap_pct = 0.10`) | active `profiles` row → `SizingPolicy.position_cap_pct` | profile, 2026-07-04 |
| Minimum position | **1,000 AUD** | profile → `SizingPolicy.min_position_aud` | profile, 2026-07-04 |
| Position count | balanced ≈ 20 names (heuristic) | `portfolio-conventions.md` I.2 | profile `risk_tolerance = balanced`, scalar 0.5 |
| Price staleness | blocking > 10 d, material > 3 d | `rules.py:45-46` | Wave 5 register |
| `price_detached` | blocking ≥ 1.0, material ≥ 0.25 (band-midpoint ratio) | `rules.py:57-58` — **arbi's draft constants** | pending **D-8** |
| Expiry | 5 sessions (action), 21 (watch/avoid/abstain) | `types.py` F3 defaults | F3 |
| Loss limit per position | **none** | — | **F4, deferred** |
| Portfolio drawdown limit | **none** (reporting-only) | — | **F4, deferred** |

Two facts about *where* the gate lives, because the red-team asked for the mechanism to be named
honestly (2026-09-06): "every Stage 4 packet closes at `abstain` until the calibration lands" is a
**policy** gate — `portfolio-policy.md` says "arbi does not assume a number" — **not a code path**:
`grep -ri 'mandate\|calibrat' asxos/domain/decision_engine/` finds nothing, and the sizer already
carries the ratified constants. What the code *does* gate on is the challenge outcome and the
headroom arithmetic below.

## 2. What the live numbers say (measured)

| Quantity | Value | Source |
|---|---|---|
| Active profile `capital_aud` | **6,666.98** | `profiles WHERE is_active` (updated 2026-07-04) |
| Active profile `cash_floor_pct` | **0.0000** | same row — *below D1; the sizer clamps it to 7.5 (`portfolio_state.py:214`)* |
| Live book, 2026-09-04 | capital **8,249.90** · holdings **8,249.90** · cash **0.00** | `portfolio_daily_snapshots` |
| Open lots | **1** (HUBS.NYSE — the global sleeve, F2) | `holding_lots` |
| Latest packet | `dpk-cba-1-2026-09-01` · **abstain** · `size_range 0/0` · expires 2026-09-30 | `decision_packets` |

**Consequence 1 — on the live book no packet can ever leave zero size.** `headroom_max_pct`
(`sizer.py:96-118`) takes the minimum of the risk-parity reference, the per-name headroom, **`cash_pct
− cash_floor_pct` = 0 − 7.5 = −7.5**, and the gross headroom, then clamps at 0. With cash at 0.00,
`SizeRange(0, 0)` is the answer for *any* candidate after *any* challenge — the D1 clamp binds
absolutely and no calibration of loss limits changes it. The Stage 4 positive control therefore runs
on a **declared paper book**, not the live one — which the architecture already intends ("one
governed *paper* investment case") but no document states as a number.

**Consequence 2 — the minimum position and the per-name cap interact.** `minimum = min(maximum,
min_position_aud ÷ capital × 100)`. At 1,000 AUD on a 6,667 AUD book the minimum is 15 % — above the
10 % cap — so the range collapses to a point at the cap. The minimum is admissible as a *range* only
when `capital ≥ min_position ÷ per_name_cap` = **10,000 AUD**.

**Consequence 3 — the profile disagrees with D1.** `cash_floor_pct = 0.0` on the row; the code
clamps to 7.5. Correct, but a reader of the row is misled. Updating the row is a production write
(James's; I5-class through the CLI or a migration-free `UPDATE`), not arbi's.

## 3. The calibration — options, one recommended default each, every number traced

| # | Parameter | Options | **Recommended** | Traced to |
|---|---|---|---|---|
| **C1** | **Paper book for the positive control** — notional capital, 100 % cash at t0, a separate `portfolio_snapshot_id` so it never blends with the live/global sleeve (F2) | 10,000 · **25,000** · 50,000 AUD | **25,000 AUD** | ≥ 10,000 so the 1,000 AUD minimum fits under the 10 % cap (Consequence 2); ≥ 20 × 1,000 so the balanced heuristic (≈20 names) is representable; round |
| **C2** | **Capital at risk per position** = position size × distance to the thesis's own `stop_price` (every active/watching thesis already carries one — `theses missing stop/target = 0`, measured) | 1 % · **2 %** · 3 % of capital | **2 %** | 10 % per-name cap × a 20 % stop distance = 2 %; a thesis whose stop is wider must size smaller to stay inside |
| **C3** | **Stop distance sanity band** — a `stop_price` further than this from entry is a challenge finding (material), not silently accepted | 15 % · **25 %** · 35 % | **25 %** | the CBA packet's own scenario bear case is −12.6 % (`scenario_summary`); twice that as the material band |
| **C4** | **Per-position size band** | keep **10 %** cap · 5 % · 15 % | **keep 10 %** (already on the profile) | profile 2026-07-04; changing it is a profile edit, not a policy edit |
| **C5** | **Portfolio drawdown limit** | 10 % · 15 % · 20 % peak-to-trough on the paper book → **mandatory review**, never a forced sale | **defer to r2 — keep reporting-only** | no code path reads a drawdown limit today; the first consumer is Stage 5's outcome review, so ruling a number now would be a number nothing enforces (the F4 "reporting-only" clause stands) |
| **C6** | **`price_detached` thresholds** (D-8) | keep draft **1.0 / 0.25** · tighten 0.5 / 0.15 | **keep 1.0 / 0.25** | `rules.py:57-58`; one ruling closes D-8 and this item together |
| **C7** | **Cash floor on the profile row** | leave 0.0 (clamped) · **set 7.5** | **set 7.5** | ADR D1; removes the row/code disagreement (Consequence 3) |
| **C8** | **Evidence staleness** | keep 10 d blocking / 3 d material | **keep** | `rules.py:45-46` |

Universal gates (F4's five) are restated unchanged and are not on the table.

## 4. Worked application to `dpk-cba-1-2026-09-01` (the negative control)

Measured state: `recommendation_state = abstain`, `size_range = 0/0`, `model_independence = true`,
the packet's own `risk_summary` names the pre-Wave-5 blocker ("absence of an independent challenge
process"). Since Wave 5 the challenge layer exists and its `price_detached` rule applies: CBA's entry
band is ≈ **2.62×** detached from price (backlog C-6; the 2026-07-16 "3.5×" ruling note) — above the
1.0 blocking ratio under C6, so the challenge **blocks** and `size_from_challenge` returns
`ZERO_SIZE` before any calibration is consulted. **The negative control still closes `abstain` with
the calibration applied** — as the Stage 4 exit gate requires ("missing evidence forces abstention").

For contrast, the arithmetic a *positive* control would see on the recommended paper book (C1 =
25,000, cash 100 %), assuming its challenge passes and its sector is unheld: headroom = min(reference
weight, 10 − 0 [C4], 100 − 7.5 = 92.5 [D1], 100 − 0 [D2], 30 − 0 [D8]) ≤ **10 %** — the per-name cap
binds, not cash; minimum = min(10, 1,000 ÷ 25,000 × 100 = 4 %) = **4 %** → `SizeRange(4, 10)` =
1,000–2,500 AUD. C2 then requires size × stop-distance ≤ 2 % × 25,000 = 500 AUD of capital at risk:
at the 10 % cap the stop may be at most 20 % away; at 4 % it may be 50 % away (C3 flags anything
beyond 25 % anyway). *Inferred* (no positive control exists yet — C-5 is James's).

## 5. The edit James would merge — `portfolio-policy.md` (deny-listed; arbi drafts, James applies)

```diff
 - **Return / drawdown targets:** **DEFERRED (governor ruling F4, 2026-08-10)** with a named blocker:
-  **"James must complete the capital/risk calibration before Stage 4."** arbi does not assume a
-  number. Until the calibrated mandate exists, volatility, beta, correlation and drawdown are
-  **reporting-only**, and these hard universal gates apply and are not deferrable: …
+  **"James must complete the capital/risk calibration before Stage 4."** **Calibrated 2026-09-__
+  (governor ruling P5-01):** capital at risk per position **≤ 2 %** of the book (position size ×
+  distance to the thesis's own stop); stop distance beyond **25 %** of entry is a material
+  challenge finding; the Stage 4 positive control runs on a **declared paper book of 25,000 AUD,
+  100 % cash at t0, in its own portfolio snapshot** (never blended with the live or global sleeve);
+  a portfolio drawdown limit stays **reporting-only until Stage 5** consumes it. The five universal
+  gates below are unchanged and not deferrable: …
@@ Hard constraints table
-| Cash floor | **[governor to set / read from profile]** — a structural protection, one of only two in v1 | `portfolio-conventions.md` I.1 |
-| Leverage cap | **[governor to set / read from profile]** — the other v1 structural protection | `portfolio-conventions.md` I.1 |
+| Cash floor | **7.5 %** (ADR D1, 2026-08-23) — enforced as a clamp in `decision_engine/sizer.py`; the profile row is to carry the same value | ADR §1.1 |
+| Leverage cap | **0 % gross LVR** (ADR D2, 2026-08-23) — any borrowing sizes to zero | ADR §1.3 |
+| Capital at risk per position | **2 %** of the book (P5-01 C2) | this ruling |
+| Stop-distance sanity band | **25 %** (P5-01 C3) — beyond it, a material challenge finding | this ruling |
+| Paper book (Stage 4 positive control) | **25,000 AUD**, 100 % cash at t0, own snapshot id (P5-01 C1) | this ruling |
```

Companion actions the ruling implies (all James's): update the active `profiles` row
`cash_floor_pct` to 0.075 (C7); rule D-8 (C6) in the same sitting; nominate the positive-control
candidate (C-5). The code changes C2/C3 imply — a `capital_at_risk` clamp in `sizer.py` and a
`stop_distance` rule in `challenge/rules.py` — are **S3-class slices after the ruling**, not part of
this proposal; until they land, C2/C3 bind as policy the packet's `risk_summary` must cite.

## 6. The ruling

> **James, one of:** (a) **accept** C1–C8 as recommended — merge the diff above (dated) and do the
> three companion actions; (b) **amend** — reply with the option letter per row (e.g. "C1: 10,000;
> C2: 1 %; rest as recommended") and arbi re-issues the diff; (c) **reject** — F4 stays deferred and
> every Stage 4 packet keeps closing `abstain` by policy.

## 7. What this proposal does not do

It does not recommend a security, a size, a buy, a sell, or a time — the personal-advice firewall
(s766B) and P6 are untouched; James executes nothing on its basis. It does not edit
`portfolio-policy.md`, the profile row, `sizer.py` or `rules.py`. It does not read `signals` or any
Model A output. It does not flip a Stage cell. If rejected, nothing in the repo changes.
