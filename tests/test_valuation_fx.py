"""The FX step — converting a foreign reporter into AUD at the cutoff's rate.

75 symbols were blocked on `currency_unconvertible` because `fx_rates` held
AUDUSD and nothing else. What these tests hold, in order of what would hurt most
if it broke:

1. **Point-in-time, never spot.** The rate used is the latest at or before the
   cutoff. Converting a 2025 book value at today's rate is a look-ahead leak —
   the valuation would know an exchange rate that did not exist when its
   fundamentals were published, and the sealed V/P replay runs at 2025 cutoffs.

2. **Convertibility is a fact about the data, not a list.** A currency with a
   rate converts; one without stays blocked and the gap names the missing pair.
   The static `frozenset({"AUD","USD"})` this replaced could disagree with the
   store in both directions.

3. **`fx_audusd` keeps its exact meaning.** `valuation_runs.payload` is
   content-addressed and append-only (0054), so a USD row's shape must not move
   and no reader of `fx_audusd` may start receiving an NZD rate under that name.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal as D

import pytest

from asxos.domain.valuation.contracts import ValuationInputs
from asxos.domain.valuation.universe import MarketInputs, currency_from_pair

CUTOFF = date(2026, 9, 19)


def _market(**pairs: tuple[str, str]) -> MarketInputs:
    """MarketInputs with AUDUSD at 0.7134 plus whatever pairs the test names."""
    return MarketInputs(
        risk_free=D("0.04831"),
        risk_free_as_of=CUTOFF,
        audusd=D("0.7134"),
        audusd_as_of=CUTOFF,
        fx={cur: (D(rate), date.fromisoformat(as_of)) for cur, (rate, as_of) in pairs.items()},
    )


# --- the pair vocabulary -----------------------------------------------------------


@pytest.mark.parametrize(
    ("pair", "expected"),
    [
        ("AUDUSD", "USD"),
        ("AUDNZD", "NZD"),
        ("audnzd", "NZD"),
        (" AUDPGK ", "PGK"),
        ("AUDAUD", None),  # degenerate; never a conversion
        ("USDJPY", None),  # not AUD-base
        ("AUD", None),
        ("AUDNZDX", None),
    ],
)
def test_currency_from_pair(pair: str, expected: str | None) -> None:
    assert currency_from_pair(pair) == expected


def test_a_malformed_pair_is_ignored_rather_than_raising() -> None:
    """`fx_rates` is an ingestion table. A future non-AUD-base pair must not
    crash a sweep of 1,836 names — it is simply not a conversion this reads."""
    assert currency_from_pair("") is None
    assert currency_from_pair("nonsense") is None


# --- convertibility is a property of the data --------------------------------------


def test_aud_and_usd_convert_with_no_pair_row() -> None:
    m = _market()
    assert m.is_convertible("AUD") and m.is_convertible("USD")
    # AUD needs no rate, so fx_for returns None — "already in AUD", not "cannot".
    assert m.fx_for("AUD") is None
    assert m.fx_for("USD") == (D("0.7134"), CUTOFF)


def test_a_currency_with_a_rate_converts_and_one_without_does_not() -> None:
    m = _market(NZD=("1.0850", "2026-09-18"))
    assert m.is_convertible("NZD")
    assert m.fx_for("NZD") == (D("1.0850"), date(2026, 9, 18))
    assert not m.is_convertible("PGK")
    assert m.fx_for("PGK") is None


def test_an_unknown_currency_is_not_convertible() -> None:
    m = _market()
    assert not m.is_convertible("ZWL")
    assert not m.is_convertible(None)


def test_dropping_a_pair_re_blocks_its_cohort() -> None:
    """The failure the static frozenset could not express: stop ingesting a pair
    and convertibility must go with it, rather than valuing on a stale rate."""
    with_nzd = _market(NZD=("1.0850", "2026-09-18"))
    without = _market()
    assert with_nzd.is_convertible("NZD")
    assert not without.is_convertible("NZD")


# --- the contract keeps its old meaning --------------------------------------------


def _inputs(**over: object) -> dict[str, object]:
    base: dict[str, object] = {
        "pit_as_of": date(2026, 6, 30),
        "pit_knowledge_date": date(2026, 8, 31),
        "currency_verified": True,
        "book_value_ps_native": D("2.00"),
        "book_value_ps_aud": D("2.00"),
        "roe_trailing": D("0.12"),
        "roe_periods": 3,
        "payout_ratio": D("0.5"),
        "payout_clipped": False,
        "franking_pct": D("100"),
        "last_close": D("3.00"),
        "last_close_dt": CUTOFF,
    }
    base.update(over)
    return base


def test_a_usd_row_carries_both_the_legacy_and_the_general_field() -> None:
    v = ValuationInputs(
        **_inputs(
            reporting_currency="USD",
            fx_audusd=D("0.7134"),
            fx_rate=D("0.7134"),
            fx_pair="AUDUSD",
            fx_as_of=CUTOFF,
        )
    )
    assert v.fx_audusd == v.fx_rate == D("0.7134")
    assert v.fx_pair == "AUDUSD"


def test_a_non_usd_row_leaves_the_legacy_field_null() -> None:
    """The point of keeping `fx_audusd`: a consumer reading it must never be
    handed an NZD rate under a name that says AUDUSD."""
    v = ValuationInputs(
        **_inputs(
            reporting_currency="NZD",
            fx_rate=D("1.0850"),
            fx_pair="AUDNZD",
            fx_as_of=CUTOFF,
        )
    )
    assert v.fx_audusd is None
    assert (v.fx_pair, v.fx_rate) == ("AUDNZD", D("1.0850"))


def test_an_aud_row_carries_no_fx_at_all() -> None:
    v = ValuationInputs(**_inputs(reporting_currency="AUD"))
    assert v.fx_audusd is None and v.fx_rate is None and v.fx_pair is None


@pytest.mark.parametrize(
    ("over", "match"),
    [
        ({"fx_rate": D("1.08"), "fx_pair": "AUDNZD"}, "fx_as_of"),
        ({"fx_rate": D("1.08"), "fx_as_of": CUTOFF}, "fx_pair"),
        (
            {"fx_audusd": D("0.71"), "fx_rate": D("1.08"), "fx_pair": "AUDNZD", "fx_as_of": CUTOFF},
            "only set for an AUDUSD conversion",
        ),
        (
            {"fx_audusd": D("0.70"), "fx_rate": D("0.7134"), "fx_pair": "AUDUSD", "fx_as_of": CUTOFF},
            "disagree",
        ),
    ],
)
def test_the_fx_fields_cannot_contradict_each_other(over: dict[str, object], match: str) -> None:
    with pytest.raises(ValueError, match=match):
        ValuationInputs(**_inputs(**over))


# --- the ingestion list ------------------------------------------------------------


def test_every_blocked_currency_has_a_pair_and_audusd_is_not_duplicated() -> None:
    """The nine currencies measured in the 75-symbol cohort on 2026-09-20.

    AUDUSD is deliberately absent — it is fetched by the US-holdings phase and
    is the one pair `load_market_inputs` hard-fails without, so listing it here
    would double-fetch it every day.
    """
    from asxos.ingestion.prices import VALUATION_FX_PAIRS

    blocked = {"NZD", "CAD", "EUR", "GBP", "PGK", "SGD", "MYR", "IDR", "HKD"}
    assert {currency_from_pair(p) for p in VALUATION_FX_PAIRS} == blocked
    assert "AUDUSD" not in VALUATION_FX_PAIRS
    assert len(set(VALUATION_FX_PAIRS)) == len(VALUATION_FX_PAIRS)


# --- end to end: the cohort actually unblocks --------------------------------------


def _sweep_row(**over: object):
    """A valuable row, borrowing the sweep suite's own shape."""
    from tests.test_valuation_sweep import _row

    return _row(**over)


def test_an_nzd_reporter_blocks_without_a_rate_and_values_with_one() -> None:
    """The 43-symbol NZD cohort, end to end. This is the whole point of Block 0:
    the same row, the same engine, and the only thing that changed is whether
    `fx_rates` carries the pair."""
    from asxos.domain.valuation import sweep
    from asxos.domain.valuation.preregistration import load_bundled_preregistration
    from tests.test_valuation_sweep import CUTOFF, MARKET

    prereg = load_bundled_preregistration()
    row = _sweep_row(currency="NZD")

    blocked = sweep.value_row(
        row,
        market=MARKET,
        ke=sweep.ke_band_for(MARKET, prereg),
        prereg=prereg,
        cutoff=CUTOFF,
        created_at=CUTOFF,
    )
    assert blocked.outcome == "blocked"
    assert [g.name for g in blocked.gaps] == ["currency_unconvertible"]
    # The gap names the pair that would unblock it, not a fixed "AUD or USD".
    assert "AUDNZD" in (blocked.gaps[0].required or "")

    with_rate = MarketInputs(
        risk_free=MARKET.risk_free,
        risk_free_as_of=MARKET.risk_free_as_of,
        audusd=MARKET.audusd,
        audusd_as_of=MARKET.audusd_as_of,
        fx={"NZD": (D("1.0850"), date(2026, 9, 18))},
    )
    valued = sweep.value_row(
        row,
        market=with_rate,
        ke=sweep.ke_band_for(with_rate, prereg),
        prereg=prereg,
        cutoff=CUTOFF,
        created_at=CUTOFF,
    )
    assert valued.outcome == "valued"
    assert valued.inputs is not None
    assert valued.inputs.fx_pair == "AUDNZD"
    assert valued.inputs.fx_rate == D("1.0850")
    assert valued.inputs.fx_as_of == date(2026, 9, 18)
    # Converted at the rate, not left native, and NOT written to the USD field.
    assert valued.inputs.fx_audusd is None
    assert valued.inputs.book_value_ps_aud < valued.inputs.book_value_ps_native


def test_the_rate_used_is_the_cutoffs_rate_not_the_newest() -> None:
    """Point-in-time: `fx_as_of` travels on the run, so a replay at a historical
    cutoff records which rate it actually used rather than implying today's."""
    from asxos.domain.valuation import sweep
    from asxos.domain.valuation.preregistration import load_bundled_preregistration
    from tests.test_valuation_sweep import CUTOFF, MARKET

    prereg = load_bundled_preregistration()
    stale = MarketInputs(
        risk_free=MARKET.risk_free,
        risk_free_as_of=MARKET.risk_free_as_of,
        audusd=MARKET.audusd,
        audusd_as_of=MARKET.audusd_as_of,
        fx={"CAD": (D("0.9100"), date(2025, 7, 1))},
    )
    run = sweep.value_row(
        _sweep_row(currency="CAD"),
        market=stale,
        ke=sweep.ke_band_for(stale, prereg),
        prereg=prereg,
        cutoff=CUTOFF,
        created_at=CUTOFF,
    )
    assert run.outcome == "valued"
    assert run.inputs is not None
    assert run.inputs.fx_as_of == date(2025, 7, 1)
    assert run.inputs.fx_rate == D("0.9100")
