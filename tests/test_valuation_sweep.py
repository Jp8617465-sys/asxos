"""The universe sweep: REPORT B parity, the gates, the flags, the sensitivities.

The five golden values are the probability-weighted, franking-adjusted values the
baseline SQL produced on 2026-09-16 (`scripts/research/parity_check.py`,
`SQL_PW_FRANK`), with the same inputs. A persisted `valuation_runs` row for one of
these names on those inputs must carry exactly these numbers — that is what makes
REPORT B the S1 acceptance test rather than a memo.
"""
from __future__ import annotations

from collections import Counter
from datetime import UTC, date, datetime
from decimal import Decimal as D

import pytest

from asxos.domain.decision_engine.types import verify_content_hash
from asxos.domain.valuation import sweep
from asxos.domain.valuation.contracts import ValuationRun
from asxos.domain.valuation.preregistration import load_bundled_preregistration
from asxos.domain.valuation.universe import MarketInputs, UniverseRow

PREREG = load_bundled_preregistration()
MARKET = MarketInputs(
    risk_free=D("0.04831"),
    risk_free_as_of=date(2026, 9, 15),
    audusd=D("0.7134"),
    audusd_as_of=date(2026, 9, 14),
)
KE = sweep.ke_band_for(MARKET, PREREG)
CUTOFF = datetime(2026, 9, 16, 1, 0, tzinfo=UTC)

# symbol -> (book_value_ps native, roe, eps_ttm, dividend_ttm, currency)
INPUTS = {
    "CBA.AU": (D("47.015532"), D("0.138062"), D("6.491039"), D("4.950000"), "AUD"),
    "NAB.AU": (D("20.090038"), D("0.107419"), D("2.158046"), D("1.700000"), "AUD"),
    "WES.AU": (D("7.034392"), D("0.360286"), D("2.534392"), D("3.630000"), "AUD"),
    "BHP.AU": (D("9.711142"), D("0.198968"), D("1.932207"), D("1.957740"), "USD"),
    "WTC.AU": (D("8.347245"), D("0.094055"), D("0.785103"), D("0.212650"), "AUD"),
}
# REPORT B pw_zx_lo / pw_zx / pw_zx_hi, 2026-09-16.
GOLDEN = {
    "CBA.AU": (D("69.070035"), D("67.496381"), D("65.978315")),
    "NAB.AU": (D("26.552192"), D("25.962502"), D("25.393033")),
    "WES.AU": (D("18.107176"), D("17.696379"), D("17.300692")),
    "BHP.AU": (D("24.467223"), D("23.934733"), D("23.420555")),
    "WTC.AU": (D("9.517311"), D("9.249588"), D("8.992850")),
}
TOLERANCE = D("0.000001")


def _row(symbol: str = "T.AU", **overrides: object) -> UniverseRow:
    base: dict[str, object] = {
        "symbol": symbol,
        "pit_as_of": date(2026, 6, 30),
        "pit_knowledge_date": date(2026, 8, 30),
        "book_value_ps": D("10"),
        "roe": D("0.12"),
        "eps_ttm": D("1.2"),
        "dividend_ttm": D("0.6"),
        "franking_avg_pct": D("100"),
        "currency": "AUD",
        "roe_average": D("0.10"),
        "roe_periods": 3,
        "last_close_dt": date(2026, 9, 14),
        "last_close": D("8"),
    }
    base.update(overrides)
    return UniverseRow(**base)  # type: ignore[arg-type]


def _value(row: UniverseRow) -> ValuationRun:
    return sweep.value_row(row, market=MARKET, ke=KE, prereg=PREREG, cutoff=CUTOFF, created_at=CUTOFF)


# --- REPORT B parity ---------------------------------------------------------


def test_ke_band_matches_the_baseline() -> None:
    assert (KE.ke_low, KE.ke_mid, KE.ke_high) == (D("0.078560"), D("0.086810"), D("0.095060"))
    assert KE.beta_mid == D("0.70")


@pytest.mark.parametrize("symbol", sorted(INPUTS))
def test_persisted_values_reproduce_report_b(symbol: str) -> None:
    book, roe, eps, div, ccy = INPUTS[symbol]
    run = _value(_row(symbol, book_value_ps=book, roe=roe, eps_ttm=eps, dividend_ttm=div, currency=ccy))
    assert run.outcome == "valued"
    low, mid, high = GOLDEN[symbol]
    assert run.value_per_share is not None and abs(run.value_per_share - mid) <= TOLERANCE
    assert run.value_ke_low is not None and abs(run.value_ke_low - low) <= TOLERANCE
    assert run.value_ke_high is not None and abs(run.value_ke_high - high) <= TOLERANCE
    assert verify_content_hash(run)
    assert ValuationRun.model_validate(run.model_dump(mode="json")) == run


def test_usd_reporter_is_converted_at_the_audusd_rate() -> None:
    run = _value(_row("BHP.AU", book_value_ps=D("9.711142"), currency="USD", dividend_ttm=D("1.0")))
    assert run.inputs is not None
    assert run.inputs.fx_audusd == D("0.7134") and run.inputs.fx_as_of == date(2026, 9, 14)
    assert run.inputs.book_value_ps_aud == (D("9.711142") / D("0.7134")).quantize(D("0.000001"))
    assert run.inputs.dividend_ttm_aud == (D("1.0") / D("0.7134")).quantize(D("0.000001"))
    assert run.inputs.reporting_currency == "USD" and run.inputs.currency_verified


def test_aud_reporter_carries_no_fx() -> None:
    run = _value(_row())
    assert run.inputs is not None
    assert run.inputs.fx_audusd is None and run.inputs.fx_as_of is None
    assert run.inputs.book_value_ps_aud == D("10.000000")


# --- gates: blocked rows name every gap ---------------------------------------


def test_missing_pit_row_and_price_block_with_both_gaps() -> None:
    run = _value(
        _row(
            pit_as_of=None, pit_knowledge_date=None, book_value_ps=None, roe=None,
            eps_ttm=None, dividend_ttm=None, franking_avg_pct=None, currency=None,
            roe_average=None, roe_periods=0, last_close_dt=None, last_close=None,
        )
    )
    assert run.outcome == "blocked"
    assert [g.name for g in run.gaps] == ["pit_row_absent", "price_absent"]
    assert run.value_per_share is None and run.inputs is None and run.scenarios == ()
    assert verify_content_hash(run)


@pytest.mark.parametrize(
    ("overrides", "gap"),
    [
        ({"book_value_ps": D("0")}, "book_value_non_positive"),
        ({"book_value_ps": D("-1")}, "book_value_non_positive"),
        ({"book_value_ps": None}, "book_value_non_positive"),
        ({"roe": None}, "roe_null"),
        ({"roe": D("0")}, "roe_non_positive"),
        ({"roe": D("-0.05")}, "roe_non_positive"),
        ({"currency": "NZD"}, "currency_unconvertible"),
        ({"currency": "gbp"}, "currency_unconvertible"),
        ({"last_close": None, "last_close_dt": None}, "price_absent"),
        ({"last_close": D("0")}, "price_absent"),
    ],
)
def test_each_gate_blocks_with_its_named_gap(overrides: dict[str, object], gap: str) -> None:
    run = _value(_row(**overrides))
    assert run.outcome == "blocked"
    assert [g.name for g in run.gaps] == [gap]
    assert run.gaps[0].detail


def test_loss_maker_gap_records_the_observed_value() -> None:
    run = _value(_row(roe=D("-0.031")))
    gap = run.gaps[0]
    assert (gap.table, gap.column, gap.observed, gap.required) == (
        "rs_fundamentals_pit", "roe", "-0.031", "> 0",
    )


# --- flags: valued but said so -----------------------------------------------


@pytest.mark.parametrize("currency", [None, "", "   "])
def test_currency_unverified_is_valued_and_flagged(currency: str | None) -> None:
    """The baseline's ruling: a NULL/blank currency is valued as AUD and FLAGGED, not hidden."""
    run = _value(_row(currency=currency))
    assert run.outcome == "valued"
    assert run.flags == (sweep.FLAG_CURRENCY_UNVERIFIED,)
    assert run.inputs is not None and run.inputs.currency_verified is False
    assert run.inputs.reporting_currency is None


def test_payout_clipping_is_flagged() -> None:
    run = _value(_row(eps_ttm=D("1"), dividend_ttm=D("1.5")))
    assert run.inputs is not None
    assert run.inputs.payout_ratio == D("1.000000") and run.inputs.payout_clipped
    assert sweep.FLAG_PAYOUT_CLIPPED in run.flags


@pytest.mark.parametrize("eps,div", [(D("0"), D("1")), (D("-2"), D("1")), (D("1"), None), (None, D("1"))])
def test_payout_is_zero_without_positive_eps_and_a_dividend(eps: D | None, div: D | None) -> None:
    run = _value(_row(eps_ttm=eps, dividend_ttm=div))
    assert run.inputs is not None
    assert run.inputs.payout_ratio == D("0.000000") and not run.inputs.payout_clipped
    assert sweep.FLAG_PAYOUT_CLIPPED not in run.flags


def test_short_roe_history_is_flagged() -> None:
    run = _value(_row(roe_periods=1))
    assert sweep.FLAG_ROE_AVERAGE_SHORT in run.flags
    assert sweep.FLAG_ROE_AVERAGE_SHORT not in _value(_row(roe_periods=3)).flags


# --- sensitivities travel with the row --------------------------------------


def test_fading_excess_exceeds_zero_excess_when_roe_exceeds_ke() -> None:
    run = _value(_row(roe=D("0.20")))
    assert run.sensitivities is not None and run.value_per_share is not None
    assert run.sensitivities.fading_excess_w050_ke_mid > run.value_per_share


def test_average_roe_sensitivity_uses_the_average_and_is_none_when_absent() -> None:
    run = _value(_row(roe=D("0.30"), roe_average=D("0.10")))
    assert run.sensitivities is not None and run.value_per_share is not None
    assert run.sensitivities.average_roe_start == D("0.100000")
    assert run.sensitivities.average_roe_ke_mid is not None
    assert run.sensitivities.average_roe_ke_mid < run.value_per_share
    absent = _value(_row(roe_average=None, roe_periods=0))
    assert absent.sensitivities is not None
    assert absent.sensitivities.average_roe_ke_mid is None
    assert absent.sensitivities.average_roe_start is None
    assert absent.inputs is not None and absent.inputs.roe_periods == 1


def test_unadjusted_franking_is_below_the_grossed_up_value() -> None:
    run = _value(_row())
    assert run.sensitivities is not None and run.value_per_share is not None
    assert run.sensitivities.unadjusted_franking_ke_mid < run.value_per_share
    unfranked = _value(_row(franking_avg_pct=D("0")))
    assert unfranked.sensitivities is not None
    assert unfranked.sensitivities.unadjusted_franking_ke_mid == unfranked.value_per_share


def test_scenarios_carry_the_registered_levers_and_ke_ordering() -> None:
    run = _value(_row())
    assert [s.label for s in run.scenarios] == ["bear", "base", "bull"]
    assert [s.probability for s in run.scenarios] == [D("0.25"), D("0.5"), D("0.25")]
    for s in run.scenarios:
        assert s.value_ke_low >= s.value_ke_mid >= s.value_ke_high
    assert run.value_to_price == D("1.500000") or run.value_to_price is not None


def test_run_identity_and_provenance() -> None:
    run = _value(_row("CBA.AU"))
    assert run.run_id == "vr-CBA.AU-2026-09-16-zero_excess"
    assert run.as_of == date(2026, 9, 16) and run.knowledge_cutoff == CUTOFF
    assert run.preregistration_id == PREREG.preregistration_id
    assert run.terminal_convention == "zero_excess"
    assert run.ke.risk_free_as_of == date(2026, 9, 15)
    assert run.value_to_price is not None and run.value_per_share is not None
    assert run.value_to_price == (run.value_per_share / D("8")).quantize(D("0.000001"))


def test_histogram_buckets_by_first_gap() -> None:
    from jobs.run_valuation import histogram

    runs = [_value(_row()), _value(_row(roe=D("-1"))), _value(_row(roe=None, last_close=None, last_close_dt=None))]
    assert histogram(runs) == Counter({"valued": 1, "roe_non_positive": 1, "roe_null": 1})
