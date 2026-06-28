# Proposal — CGT discount break-even spec amendment + test plan (2026-06-28)

**Status: DRAFT for James's sign-off. No spec or code change applied.**

This proposal closes a non-negotiable-#8 deviation: `cgt_break_even_price()`
(`asxos/domain/tax/cgt.py:110-140`) computes a tax number with a citation
("spec §2 + §5.1") to sections that define no such formula. The conformance pass
(`tax-spec-conformance`) found that the function is **also numerically wrong for
SMSF** — so this is not merely an unhoused formula but a live tax-math bug. The
amendment below encodes the *correct* formula; the code fix must follow the
amendment per #8, not enshrine the current code.

It is **live in production** via `position_monitor/display.py:223`, so "just
delete it" is not free.

---

## 1. Citation-gap finding (confirmed)

- **§2 "Account types"** (`tax-alpha.md:13-29`) is a rate/discount table. It
  supplies only the discount fraction `d` (50% individual, exact `1/3` SMSF). It
  defines no break-even concept.
- **§5.1 "The 12-month rule"** (`tax-alpha.md:102-112`) governs *eligibility timing
  only* (calendar arithmetic). The code legitimately uses it for the
  `days_to_eligibility()` gate, but §5.1 says nothing about *pricing* a deferral.
- No other section (§5.2 net-gain computation, §5.3/§7 Medicare, §§1-13 reviewed)
  contemplates a forward-looking break-even price.

→ The formula has **no governing spec home**. Genuine #8 deviation.

Two secondary defects in the same function, independent of the housing gap:
- **`cost_usd` parameter / currency basis is unstated.** The production caller
  (`display.py:222-226`) passes ASX positions; there is no §8 Div 775 FX
  translation here. The currency contract must be pinned (recommend: caller
  translates per §8.2 before calling; function operates in a single currency).
- **`marginal_rate` default `0.45` with no §10 validation.** §10 (`tax-alpha.md:347`)
  rejects a rate above 0.5; this path applies no validation, and `r=1` is only
  caught by the `denominator <= 0` guard.

---

## 2. Formula-correctness verdict — algebra is WRONG for SMSF

Derivation (after-tax-now == after-tax-later, price held constant at `P` when the
discount lands):

- **Sell later** (discount `d` on full gain `P − cost`): `P − (P − cost)·d·r`
- **Sell now** at `P_sell` (no discount, full gain at `r`): `P_sell − (P_sell − cost)·r`

Equating and solving:
```
P_sell = [ P·(1 − r·d) − cost·r·(1 − d) ] / (1 − r)
```

**The code (`cgt.py:138`) computes** `[ P·(1 − r·d) − cost·r·d ] / (1 − r)` — the
cost coefficient is `d` where it should be `(1 − d)`. These coincide only when
`d = 1 − d`, i.e. `d = 0.5`.

| Account | `d` | code coeff `d` | correct coeff `1−d` | verdict |
|---|---|---|---|---|
| Individual | 0.5 | 0.5 | 0.5 | **correct by coincidence** |
| SMSF | 1/3 | 1/3 | 2/3 | **WRONG — overstates break-even** |

**Second SMSF bug:** the SMSF rate is 15% (§2), not a marginal rate, but the
function defaults `marginal_rate=0.45` and the caller doesn't override it. So the
SMSF branch uses both the wrong coefficient *and* the wrong rate.

Effect: for an SMSF the function tells the user to demand a *higher* sale price than
the true break-even → wrongly discourages selling now. Hand-verified round-trips
below confirm the corrected numbers net identical after-tax proceeds.

---

## 3. Proposed spec text — new §5.4

Add under §5 (CGT). Bump spec to v1.3 with a §13 change-log entry, and add TC-22 /
TC-23 to the §11 worked-example matrix.

> ### 5.4 CGT discount break-even price (decision-support heuristic)
>
> Governs `cgt_break_even_price()` in `asxos/domain/tax/cgt.py`, surfaced by the
> position monitor. This is a **decision-support hint, not a tax computation**: it
> estimates the minimum sale price today that nets the same after-tax proceeds as
> deferring the sale until the s 115-100 discount is available, holding price
> constant.
>
> **Scope and assumptions (all disclosed to the user):**
> - Price assumed unchanged at the current price `P` on the date the discount
>   becomes available. A heuristic, not a forecast.
> - Ignores time value of money, dividends/franking received during the deferral,
>   and transaction costs.
> - **Individual:** `r` = the user's marginal rate. The 2% Medicare levy (§7) is
>   **[DECISION: include for consistency with §5.3, or exclude and disclose]**.
> - **SMSF:** `r = 0.15` (§2 headline rate), **not** a marginal rate; `d = 1/3`
>   (exact, §2).
> - **Currency:** `P` and `cost` must be in the same currency. For US lots,
>   translate per §8.2 before calling; the function performs no Div 775 translation.
>
> **Formula.** With `P` = current price, `cost` = cost base (same currency), `r` =
> applicable rate, `d` = discount fraction (0.5 individual, exact 1/3 SMSF, both §2):
>
> > P_sell = [ P·(1 − r·d) − cost·r·(1 − d) ] / (1 − r)
>
> Derived by equating sell-now after-tax `P_sell − (P_sell − cost)·r` with sell-later
> after-tax `P − (P − cost)·d·r`. **The cost coefficient is `(1 − d)`, not `d`** — the
> two coincide only for individuals (d = 0.5).
>
> **Degenerate / None branches:**
> - Already discount-eligible (`days_to_eligibility == 0`) → None.
> - No unrealised gain (`P ≤ cost`) → None.
> - `r ≥ 1` (degenerate) → None (also subject to §10 "rate above 0.5 rejected").
> - Computed `P_sell ≤ cost` → None.
>
> **TC-22 (individual).** P=100, cost=40, r=0.45, d=0.5, not yet eligible.
> numerator = 100·(1 − 0.225) − 40·0.45·0.5 = 77.5 − 9 = 68.5; /0.55 = **124.55**.
> Check: sell-later nets 100 − 60·0.5·0.45 = 86.50; sell-now @124.55 nets
> 124.55 − 84.55·0.45 = 86.50. ✓
>
> **TC-23 (SMSF).** P=100, cost=40, r=0.15, d=1/3, not yet eligible.
> numerator = 100·(1 − 0.05) − 40·0.15·(2/3) = 95 − 4 = 91; /0.85 = **107.06**.
> Check: sell-later nets 100 − 60·(1/3)·0.15 = 97.00; sell-now @107.06 nets
> 107.06 − 67.06·0.15 = 97.00. ✓

(TC-22/23 numbers hand-computed and independently verified; round to cents
ROUND_HALF_UP per the existing cents-quantization convention.)

---

## 4. Test plan

Target `tests/test_tax_cgt.py` (or a new `tests/test_tax_break_even.py`). Every test
cites §5.4 / TC-22 / TC-23.

**Correctness (the fix):**
1. **TC-22 individual** → `Decimal("124.55")`. *(Passes against current code — the
   individual path is correct by coincidence.)*
2. **TC-23 SMSF** → `Decimal("107.06")`, with the corrected SMSF rate `r=0.15` and
   `d=1/3`. **Fails against current code** (wrong coefficient + wrong default rate) —
   this is the regression lock proving the fix.
3. **Round-trip invariant (property test)** — for both account types, assert
   sell-now-at-`P_sell` after-tax == sell-later-at-`P` after-tax to the cent. This is
   the generic guard that would have caught the `(1 − d)` error.

**Boundary / None branches:**
4. Already eligible (`days_to_eligibility == 0`) → None.
5. `current_price == cost` and `current_price < cost` → None.
6. Result `≤ cost` (tiny gain, high rate, e.g. P=41, cost=40, r=0.45) → None.
7. `r = 1` (denominator ≤ 0) → None. Add `r > 0.5` rejection once §10 validation is
   wired (currently absent — tracked as a follow-up, not a pass).

**Decimal-exactness (SMSF 1/3 trap):**
8. SMSF path uses the exact `Fraction(1,3)` via `cgt_discount_rate("smsf")`
   (`cgt.py:45-48`) → `Decimal(1)/Decimal(3)` truncated at context precision (NOT a
   float `0.3333`). Assert an exact `Decimal` literal (not `pytest.approx`), and pin
   TC-23 to the value the truncated fraction actually yields, ROUND_HALF_UP at cents.

**Currency guard (from the `cost_usd` defect):**
9. Once the amendment pins currency, assert the contract (callers translate US lots
   per §8.2, or the parameter is renamed). Until pinned, mark `xfail` referencing the
   §5.4 amendment rather than asserting current behaviour.

---

## 5. Follow-on code change (after sign-off; spec-governed per #8)

Not part of this proposal — listed so the path is clear:
1. Correct the cost coefficient to `(1 − d)`.
2. Give the SMSF branch `r = 0.15` (don't rely on the 0.45 default).
3. Pin / rename the currency basis (`cost_usd`).
4. Wire §10 rate validation.
5. Decide the Medicare-2% inclusion for the individual branch.
Route through `backend-architect` (touches a live job output) then the review-gate
loop.

---

## Decisions needed from James
1. **Approve §5.4** as drafted (formula with `(1 − d)`, TC-22/TC-23, None branches)?
2. **Medicare on the individual branch:** include the 2% (consistent with §5.3) or
   exclude-and-disclose?
3. **Currency contract:** caller-translates-per-§8.2 (recommended) — confirm?
4. **Then** authorise the follow-on code fix (steps in §5) under the approved spec.
