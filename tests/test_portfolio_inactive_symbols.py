"""Tests for the build.py rebalance-input helpers.

Guards the Option-B invariant: a held US holding (is_active=FALSE by design) is
NOT auto-liquidated. Two layers: it's excluded from the rebalance snapshot
entirely (so it never reaches compute_deltas), and excluded from the
universe_inactive forced-sell set. A genuinely delisted AU equity still is sold.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from asxos.domain.portfolio.build import (
    forced_sell_inactive_symbols,
    rebalance_holding_snapshots,
)


def _row(symbol: str, is_active: bool, security_kind: str = "au_equity") -> dict:
    return {"symbol": symbol, "is_active": is_active, "security_kind": security_kind}


def _hrow(symbol: str, lot_id: int = 1) -> dict:
    return {
        "lot_id": lot_id,
        "symbol": symbol,
        "acquired_at": date(2026, 1, 1),
        "quantity": Decimal("10"),
        "cost_base_normal": Decimal("1000"),
        "cost_base_div296": Decimal("1000"),
    }


def test_au_delisting_is_force_sold() -> None:
    # An AU equity flipped is_active=FALSE (a real delisting) stays eligible.
    out = forced_sell_inactive_symbols([_row("BHP.AU", False)])
    assert out == frozenset({"BHP.AU"})


def test_active_au_not_force_sold() -> None:
    out = forced_sell_inactive_symbols([_row("CBA.AU", True)])
    assert out == frozenset()


def test_held_us_holding_not_force_sold() -> None:
    # HUBS.NYSE is is_active=FALSE by design (not an ASX-equity-universe member),
    # NOT delisted — it must NOT be auto-liquidated.
    out = forced_sell_inactive_symbols([_row("HUBS.NYSE", False, "us_equity")])
    assert out == frozenset()


def test_all_foreign_exchanges_excluded() -> None:
    rows = [_row(s, False, "us_equity") for s in ("X.US", "Y.NYSE", "Z.NASDAQ", "W.AMEX")]
    assert forced_sell_inactive_symbols(rows) == frozenset()


def test_index_row_excluded() -> None:
    # Post-0037: an index row (security_kind='index') is excluded outright. The kind
    # filter is stricter than the old is_foreign_symbol check — .INDX is not a
    # FOREIGN_SUFFIX, so it used to be INCLUDED-but-inert (never held); now it's cleanly
    # excluded, which is the correct behaviour.
    out = forced_sell_inactive_symbols([_row("AXJO.INDX", False, "index")])
    assert out == frozenset()


def test_au_etf_not_force_sold() -> None:
    # VGS.AU is an ETF (security_kind='etf') with the SAME .AU suffix as an equity.
    # The old is_foreign_symbol check could not tell them apart and would have
    # force-sold a held ETF on a delisting sweep; the kind filter excludes it.
    out = forced_sell_inactive_symbols([_row("VGS.AU", False, "etf")])
    assert out == frozenset()


def test_bare_code_au_is_force_sold() -> None:
    # Production AU symbols can be bare codes (no .AU suffix). is_foreign_symbol
    # returns False for them, so an inactive bare code is still force-sold.
    out = forced_sell_inactive_symbols([_row("BHP", False)])
    assert out == frozenset({"BHP"})


def test_mixed_set() -> None:
    rows = [
        _row("BHP.AU", False),                  # delisted au_equity → included
        _row("CBA.AU", True),                   # active au_equity → excluded
        _row("HUBS.NYSE", False, "us_equity"),  # held US → excluded
        _row("AAPL.US", False, "us_equity"),    # held US → excluded
        _row("VGS.AU", False, "etf"),           # ETF (even .AU-suffixed) → excluded
    ]
    assert forced_sell_inactive_symbols(rows) == frozenset({"BHP.AU"})


# --- rebalance_holding_snapshots — the primary "don't liquidate HUBS" guard ----

def test_snapshot_excludes_foreign_holding_even_with_price() -> None:
    # HUBS.NYSE WITH a price is still excluded from the rebalance snapshot — so it
    # never reaches compute_deltas and is never proposed for sale.
    rows = [_hrow("BHP.AU", 1), _hrow("HUBS.NYSE", 2)]
    prices = {"BHP.AU": Decimal("45.20"), "HUBS.NYSE": Decimal("150.00")}
    out = rebalance_holding_snapshots(rows, prices, "individual", date(2026, 6, 1))
    assert {h.symbol for h in out} == {"BHP.AU"}


def test_snapshot_excludes_held_etf() -> None:
    # A held ETF (security_kind != au_equity, passed via non_equity_symbols) is excluded from
    # the rebalance snapshot — so it never reaches compute_deltas and is never proposed for an
    # 'exited_universe' full-sell. Mirror of the foreign-holding guard; this is the path that
    # catches a .AU-suffixed ETF (VGS.AU), which is_foreign_symbol cannot.
    rows = [_hrow("BHP.AU", 1), _hrow("VGS.AU", 2)]
    prices = {"BHP.AU": Decimal("45.20"), "VGS.AU": Decimal("110.00")}
    out = rebalance_holding_snapshots(
        rows, prices, "individual", date(2026, 6, 1),
        non_equity_symbols=frozenset({"VGS.AU"}),
    )
    assert {h.symbol for h in out} == {"BHP.AU"}


def test_snapshot_omits_symbol_without_price() -> None:
    out = rebalance_holding_snapshots([_hrow("CBA.AU")], {}, "individual", date(2026, 6, 1))
    assert out == []


def test_snapshot_includes_priced_au_holding() -> None:
    out = rebalance_holding_snapshots(
        [_hrow("CBA.AU")], {"CBA.AU": Decimal("100")}, "individual", date(2026, 6, 1)
    )
    assert len(out) == 1
    assert out[0].symbol == "CBA.AU"
    assert out[0].current_price_aud == Decimal("100")
