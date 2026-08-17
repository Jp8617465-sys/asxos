"""Per-lot outcome vs benchmark — the pure Decimal layer.

These tests pin the three things that have historically gone wrong in this exact
arithmetic, and they pin them on the *pure* module so no DB fixture can hide a
regression:

1. **The currency error (R10).** `holding_lots.cost_base_normal` is the AUD CGT
   cost base, not `quantity × native_price`. Dividing it by `quantity` and
   comparing to a USD `prices.close` made the 2026-07-11 `/pm-review` report
   HUBS.NYSE at −29% and stop-violated when the lot was ≈ +9.8% in USD. The
   HUBS test below asserts the correct AUD-vs-AUD answer *and* asserts the
   −29% answer is not produced.
2. **The proxy label (governor ruling F1).** The synthetic yield overlay
   (`jobs/snapshot_portfolio.py:63-92`) is never reported as the accumulation
   benchmark — the measurement is `unavailable` and names the proxy.
3. **Sleeve separation (governor ruling F2).** HUBS.NYSE never appears in the
   ASX sleeve and never receives an ASX benchmark comparison.

Plus the standing rule for this whole surface: an unmeasurable leg is `None` with
a printed reason, never a zero. A rendered 0.0% is indistinguishable from a
measured flat return, which is the same class of lie as the −75.7%.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from asxos.domain.benchmark.outcome import (
    BenchmarkAnchor,
    BenchmarkState,
    LotInput,
    OutcomeSection,
    ReturnState,
    Sleeve,
    build_lot_outcome,
    build_outcome_section,
    sleeve_for,
)

AS_OF = date(2026, 8, 17)

# ---------------------------------------------------------------------------
# Fixtures — today's actual state plus one synthetic ASX lot.
#
# The live portfolio on 2026-08-17 is ONE open lot: HUBS.NYSE, 24 shares. Its
# cost base and acquisition FX are the values pinned in
# `.claude/rules/portfolio-conventions.md`: 6978.23 AUD = 24 × US$187.54 ÷ 0.6450.
# ---------------------------------------------------------------------------

HUBS_QUANTITY = Decimal("24")
HUBS_COST_BASE_AUD = Decimal("6978.23")
HUBS_ENTRY_USD = Decimal("187.54")
HUBS_ACQUISITION_FX = Decimal("0.6450")


def _hubs(**overrides: object) -> LotInput:
    defaults: dict[str, object] = {
        "lot_id": 1,
        "symbol": "HUBS.NYSE",
        "quantity": HUBS_QUANTITY,
        "acquired_at": date(2025, 6, 2),
        "cost_base_aud": HUBS_COST_BASE_AUD,
        "close_native": Decimal("205.92"),  # USD, ≈ +9.8% on the US$187.54 entry
        "fx_audusd": Decimal("0.6500"),
        "benchmark_start": None,
        "benchmark_end": None,
    }
    defaults.update(overrides)
    return LotInput(**defaults)  # type: ignore[arg-type]


def _real_anchor(day: date, level: str) -> BenchmarkAnchor:
    """A real S&P/ASX 200 Accumulation level (trailing_div_yield_pct was NULL)."""
    return BenchmarkAnchor(as_of=day, level=Decimal(level), is_proxy=False)


def _proxy_anchor(day: date, level: str) -> BenchmarkAnchor:
    """A synthetic yield-overlay level (trailing_div_yield_pct was non-NULL)."""
    return BenchmarkAnchor(as_of=day, level=Decimal(level), is_proxy=True)


def _cba(**overrides: object) -> LotInput:
    defaults: dict[str, object] = {
        "lot_id": 7,
        "symbol": "CBA.AU",
        "quantity": Decimal("100"),
        "acquired_at": date(2025, 8, 15),
        "cost_base_aud": Decimal("9000.00"),
        "close_native": Decimal("108.00"),  # AUD — no FX step for an ASX symbol
        "fx_audusd": Decimal("0.6500"),
        "benchmark_start": _real_anchor(date(2025, 8, 15), "80000"),
        "benchmark_end": _real_anchor(AS_OF, "84000"),
    }
    defaults.update(overrides)
    return LotInput(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 1. Currency correctness (R10) — the −29% defect, closed
# ---------------------------------------------------------------------------


def test_foreign_lot_converts_both_legs_to_aud() -> None:
    """24 × US$205.92 ÷ 0.6500 = A$7,603.20 against an A$6,978.23 cost base."""
    outcome = build_lot_outcome(_hubs(), AS_OF)

    assert outcome.return_state is ReturnState.measured
    assert outcome.market_value_aud == Decimal("7603.200000")
    assert outcome.lot_return == Decimal("0.089560")


def test_foreign_lot_return_is_not_the_cost_base_divided_by_quantity_error() -> None:
    """The exact 2026-07-11 defect, pinned as a negative assertion.

    `cost_base_normal / quantity` = 6978.23 / 24 = 290.76, which is an AUD figure
    wearing a USD label. Comparing it to a USD close yields −29.18%. The lot was
    up. Any future refactor that reintroduces that division fails here.
    """
    naive_entry = HUBS_COST_BASE_AUD / HUBS_QUANTITY
    close = Decimal("205.92")
    naive_return = ((close - naive_entry) / naive_entry).quantize(Decimal("0.000001"))
    assert naive_return == Decimal("-0.291786")  # the wrong answer, reproduced

    outcome = build_lot_outcome(_hubs(), AS_OF)
    assert outcome.lot_return is not None
    assert outcome.lot_return > 0
    assert outcome.lot_return != naive_return


def test_native_entry_reconstruction_agrees_with_the_aud_measurement() -> None:
    """Cross-check the AUD answer against the USD-vs-USD route (R10 offers both).

    Native: (205.92 − 187.54) / 187.54 = +9.80% USD. The AUD answer is +8.96%,
    lower because AUDUSD moved from 0.6450 to 0.6500 — the AUD strengthened, so
    the same USD gain buys fewer AUD. The two differing is the FX effect, not an
    error; this test pins that they differ in the direction FX implies.
    """
    usd_return = (Decimal("205.92") - HUBS_ENTRY_USD) / HUBS_ENTRY_USD
    aud_return = build_lot_outcome(_hubs(), AS_OF).lot_return
    assert aud_return is not None
    assert Decimal("0.097") < usd_return < Decimal("0.099")
    assert aud_return < usd_return  # AUD strengthened: 0.6450 → 0.6500
    assert HUBS_ACQUISITION_FX < Decimal("0.6500")


def test_asx_lot_needs_no_fx_step() -> None:
    outcome = build_lot_outcome(_cba(), AS_OF)
    assert outcome.market_value_aud == Decimal("10800.000000")
    assert outcome.lot_return == Decimal("0.200000")
    assert outcome.is_foreign is False


def test_foreign_lot_without_fx_is_unavailable_not_zero() -> None:
    outcome = build_lot_outcome(_hubs(fx_audusd=None), AS_OF)
    assert outcome.return_state is ReturnState.unavailable_no_fx
    assert outcome.lot_return is None
    assert outcome.market_value_aud is None
    assert "AUDUSD" in outcome.return_note


def test_missing_close_is_unavailable_not_zero() -> None:
    outcome = build_lot_outcome(_cba(close_native=None), AS_OF)
    assert outcome.return_state is ReturnState.unavailable_no_price
    assert outcome.lot_return is None
    assert "no close" in outcome.return_note


def test_non_positive_cost_base_is_reported_not_raised() -> None:
    """`period_return` raises on a non-positive base; the caller must not.

    A zero cost base is a data defect, and the brief has to keep rendering. The
    honest output is a named unavailable state with the offending value printed —
    loud on the page rather than a traceback that takes the whole brief down.
    """
    outcome = build_lot_outcome(_cba(cost_base_aud=Decimal("0")), AS_OF)
    assert outcome.return_state is ReturnState.unavailable_cost_base
    assert outcome.lot_return is None
    assert outcome.market_value_aud == Decimal("10800.000000")  # still stated
    assert "not positive" in outcome.return_note


# ---------------------------------------------------------------------------
# 2. Governor ruling F1 — the proxy is never a total-return measurement
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "start_proxy,end_proxy",
    [(True, True), (True, False), (False, True)],
)
def test_proxy_benchmark_is_unavailable_in_every_combination(
    start_proxy: bool, end_proxy: bool
) -> None:
    start = (_proxy_anchor if start_proxy else _real_anchor)(date(2025, 8, 15), "80000")
    end = (_proxy_anchor if end_proxy else _real_anchor)(AS_OF, "84000")
    outcome = build_lot_outcome(_cba(benchmark_start=start, benchmark_end=end), AS_OF)

    assert outcome.benchmark_state is BenchmarkState.unavailable_proxy
    assert outcome.benchmark_return is None
    assert outcome.alpha is None
    assert outcome.benchmark_window is None
    assert "F1" in outcome.benchmark_note


def test_proxy_note_never_claims_a_total_return_measurement() -> None:
    """F1: `AXJO.INDX` "must never carry a total-return label"."""
    outcome = build_lot_outcome(
        _cba(benchmark_start=_proxy_anchor(date(2025, 8, 15), "80000")), AS_OF
    )
    note = outcome.benchmark_note.lower()
    assert "approximation" in note
    assert "unavailable" in note
    # The label the ruling forbids on a proxy, in either spelling.
    assert "total-return" not in note
    assert "total return" not in note


def test_real_accumulation_levels_measure_benchmark_and_alpha() -> None:
    outcome = build_lot_outcome(_cba(), AS_OF)
    assert outcome.benchmark_state is BenchmarkState.measured
    assert outcome.benchmark_return == Decimal("0.050000")
    assert outcome.alpha == Decimal("0.150000")  # 20.0% − 5.0%
    assert outcome.benchmark_window == (date(2025, 8, 15), AS_OF)


def test_missing_benchmark_series_is_unavailable_with_a_reason() -> None:
    outcome = build_lot_outcome(_cba(benchmark_start=None), AS_OF)
    assert outcome.benchmark_state is BenchmarkState.unavailable_no_series
    assert outcome.benchmark_return is None
    assert outcome.alpha is None
    assert "does not cover this window" in outcome.benchmark_note


def test_benchmark_anchor_too_far_from_the_lot_window_is_rejected() -> None:
    """A 6-day-stale anchor is a different window, so it is not silently used."""
    stale = _real_anchor(date(2025, 8, 9), "80000")  # acquired 2025-08-15
    outcome = build_lot_outcome(_cba(benchmark_start=stale), AS_OF)
    assert outcome.benchmark_state is BenchmarkState.unavailable_window_mismatch
    assert outcome.benchmark_return is None
    assert outcome.alpha is None


def test_benchmark_anchor_within_tolerance_is_accepted() -> None:
    """A weekend/holiday gap is normal for a snapshot-derived series."""
    lagged = _real_anchor(date(2025, 8, 12), "80000")  # 3 days before acquisition
    outcome = build_lot_outcome(_cba(benchmark_start=lagged), AS_OF)
    assert outcome.benchmark_state is BenchmarkState.measured
    assert outcome.benchmark_window == (date(2025, 8, 12), AS_OF)


def test_alpha_is_absent_whenever_either_leg_is_absent() -> None:
    no_price = build_lot_outcome(_cba(close_native=None), AS_OF)
    assert no_price.benchmark_return is not None  # benchmark leg still measured
    assert no_price.alpha is None  # but alpha needs both

    no_bench = build_lot_outcome(_cba(benchmark_end=None), AS_OF)
    assert no_bench.lot_return is not None
    assert no_bench.alpha is None


# ---------------------------------------------------------------------------
# 3. Governor ruling F2 — sleeves separated, never blended
# ---------------------------------------------------------------------------


def _sleeve(section: OutcomeSection, sleeve: Sleeve):  # type: ignore[no-untyped-def]
    return next(s for s in section.sleeves if s.sleeve is sleeve)


def test_sleeve_for_routes_by_the_shared_foreign_suffix_test() -> None:
    assert sleeve_for("HUBS.NYSE") is Sleeve.global_
    assert sleeve_for("AAPL.US") is Sleeve.global_
    assert sleeve_for("MSFT.NASDAQ") is Sleeve.global_
    assert sleeve_for("CBA.AU") is Sleeve.asx
    assert sleeve_for("BHP.AU") is Sleeve.asx


def test_hubs_is_never_in_the_asx_sleeve_or_its_benchmark_comparison() -> None:
    """Governor ruling F2, asserted as an exclusion rather than an inclusion."""
    section = build_outcome_section([_hubs(), _cba()], AS_OF)

    asx = _sleeve(section, Sleeve.asx)
    assert [lot.symbol for lot in asx.lots] == ["CBA.AU"]
    assert all(lot.symbol != "HUBS.NYSE" for lot in asx.lots)

    glob = _sleeve(section, Sleeve.global_)
    assert [lot.symbol for lot in glob.lots] == ["HUBS.NYSE"]


def test_global_sleeve_carries_no_benchmark_even_when_levels_are_supplied() -> None:
    """Handing the global sleeve ASX levels must not produce a comparison.

    This is the adversarial form of F2: the blend is prevented by the sleeve
    check, not merely by the loader declining to fetch ASX levels for HUBS.
    """
    contaminated = _hubs(
        benchmark_start=_real_anchor(date(2025, 6, 2), "80000"),
        benchmark_end=_real_anchor(AS_OF, "84000"),
    )
    outcome = build_lot_outcome(contaminated, AS_OF)
    assert outcome.benchmark_state is BenchmarkState.not_applicable_sleeve
    assert outcome.benchmark_return is None
    assert outcome.alpha is None
    assert outcome.lot_return is not None  # its own return is still reported


def test_both_sleeves_are_always_present_even_when_empty() -> None:
    """Today's real shape: one global lot, zero ASX lots."""
    section = build_outcome_section([_hubs()], AS_OF)
    assert {s.sleeve for s in section.sleeves} == {Sleeve.asx, Sleeve.global_}

    asx = _sleeve(section, Sleeve.asx)
    assert asx.lots == ()
    assert asx.empty_note  # stated, not blank
    assert "No open ASX lots" in asx.empty_note

    glob = _sleeve(section, Sleeve.global_)
    assert len(glob.lots) == 1
    assert glob.empty_note == ""


def test_empty_input_reports_two_empty_sleeves_and_zero_measurements() -> None:
    section = build_outcome_section([], AS_OF)
    assert len(section.sleeves) == 2
    assert all(s.lots == () and s.empty_note for s in section.sleeves)
    assert section.measured_lot_count == 0


def test_lots_are_ordered_deterministically_within_a_sleeve() -> None:
    older = _cba(lot_id=2, symbol="BHP.AU", acquired_at=date(2024, 1, 5))
    newer = _cba(lot_id=3, symbol="ANZ.AU", acquired_at=date(2026, 1, 5))
    section = build_outcome_section([newer, older, _cba()], AS_OF)
    asx = _sleeve(section, Sleeve.asx)
    assert [lot.symbol for lot in asx.lots] == ["BHP.AU", "CBA.AU", "ANZ.AU"]


def test_measured_lot_count_counts_only_measured_returns() -> None:
    section = build_outcome_section([_cba(), _hubs(fx_audusd=None)], AS_OF)
    assert section.measured_lot_count == 1


# ---------------------------------------------------------------------------
# 4. Purity — no DB, no numpy, no float
# ---------------------------------------------------------------------------


def test_module_imports_no_db_or_numpy() -> None:
    """The Decimal-only invariant, asserted on the source rather than by faith.

    `.claude/rules/portfolio-conventions.md` §"Decimal-only arithmetic" bans numpy
    from this arithmetic, and this module must stay renderable without a database
    handle so its maths can be tested in isolation from any fixture.
    """
    import ast
    from pathlib import Path

    import asxos.domain.benchmark.outcome as mod

    tree = ast.parse(Path(mod.__file__).read_text())

    # Parsed, not grepped. The previous version matched the literal string
    # "import numpy", which missed `from numpy import ...` — the spelling a
    # future edit is most likely to reach for. Widening it to a bare "numpy"
    # substring then matched this module's own docstring ("no DB, no numpy"),
    # i.e. the prose describing the invariant tripped the check on the
    # invariant. The import graph is the thing under test, so read the import
    # graph.
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)

    for banned in ("numpy", "pandas", "asyncpg", "asxos.db"):
        offenders = [m for m in modules if m == banned or m.startswith(f"{banned}.")]
        assert not offenders, f"outcome.py imports {offenders} — {banned} is banned here"

    # `float(...)` anywhere in the arithmetic would silently leave Decimal.
    # A call-node walk, so the word appearing in a docstring cannot trip it.
    float_calls = [
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Name)
        and n.func.id == "float"
    ]
    assert not float_calls, "outcome.py calls float() — Decimal-only invariant"


def test_every_measured_number_is_a_decimal() -> None:
    outcome = build_lot_outcome(_cba(), AS_OF)
    for value in (
        outcome.market_value_aud,
        outcome.lot_return,
        outcome.benchmark_return,
        outcome.alpha,
    ):
        assert isinstance(value, Decimal)
