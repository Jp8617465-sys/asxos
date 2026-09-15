"""Parity check: the SQL residual-income sweep vs the repo's own ``value_per_share``.

The baseline inquiry (``scripts/research/baseline_inquiry.sql``) re-expresses
``asxos.domain.valuation.residual_income.value_per_share`` as a recursive CTE so it can
run through the read-only ``supabase-ro`` connector. This script proves the two agree:
it evaluates the Python model on the same five names with the same inputs (fetched
2026-09-16 through supabase-ro and embedded below) and prints the probability-weighted
values the SQL produced next to them.

Run: ``.venv/bin/python scripts/research/parity_check.py``  (no database needed)

Result 2026-09-16: every pair reconciles to <= 0.000001 (a sixth-decimal rounding
artefact of ``round(..., 6)`` in SQL vs ``q6`` in Python) — see the memo,
``docs/proposals/baseline-inquiry-2026-09-16.md``.

Conventions (identical on both sides): reported-book base, 10-year linear fade to Ke,
terminal value = book (``persistence=0``), franking grossed up at 30/70 for an Australian
resident, payout = dividend_ttm / eps_ttm clipped to [0, 1] (0 when EPS <= 0 or no
dividend), scenarios 0.70/1.00/1.20 x own ROE at 25/50/25, Ke = rf + beta * ERP with the
cited 0.55/0.70/0.85 beta band. USD reporters (BHP) converted at AUDUSD 0.7134.
"""

from __future__ import annotations

import sys
from decimal import Decimal as D
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from asxos.domain.valuation.residual_income import value_per_share

RF = D("0.04831")  # market_context.aus_10y_yield, as_of 2026-09-15
ERP = D("0.055")
AUDUSD = D("0.7134")  # portfolio_daily_snapshots.fx_rate_audusd, 2026-09-14
KE = {"lo": RF + D("0.55") * ERP, "mid": RF + D("0.70") * ERP, "hi": RF + D("0.85") * ERP}
SCENARIOS = ((D("0.70"), D("0.25")), (D("1.00"), D("0.50")), (D("1.20"), D("0.25")))

# symbol -> (book_value_ps in AUD, roe, payout, franking_pct), from rs_fundamentals_pit,
# latest usable row at 2026-09-16 (knowledge_date <= today).
INPUTS: dict[str, tuple[D, D, D, D]] = {
    "CBA.AU": (D("47.015532"), D("0.138062"), D("4.950000") / D("6.491039"), D("100")),
    "NAB.AU": (D("20.090038"), D("0.107419"), D("1.700000") / D("2.158046"), D("100")),
    "WES.AU": (D("7.034392"), D("0.360286"), min(D(1), D("3.630000") / D("2.534392")), D("100")),
    "BHP.AU": (
        D("9.711142") / AUDUSD,
        D("0.198968"),
        min(D(1), D("1.957740") / D("1.932207")),
        D("100"),
    ),
    "WTC.AU": (D("8.347245"), D("0.094055"), D("0.212650") / D("0.785103"), D("100")),
}

# Probability-weighted, franking-adjusted values the SQL sweep produced on 2026-09-16
# (REPORT B columns pw_zx_lo / pw_zx / pw_zx_hi, run on the five names).
SQL_PW_FRANK: dict[str, dict[str, D]] = {
    "CBA.AU": {"lo": D("69.070035"), "mid": D("67.496381"), "hi": D("65.978315")},
    "NAB.AU": {"lo": D("26.552192"), "mid": D("25.962502"), "hi": D("25.393033")},
    "WES.AU": {"lo": D("18.107176"), "mid": D("17.696379"), "hi": D("17.300692")},
    "BHP.AU": {"lo": D("24.467223"), "mid": D("23.934733"), "hi": D("23.420555")},
    "WTC.AU": {"lo": D("9.517311"), "mid": D("9.249588"), "hi": D("8.992850")},
}

TOLERANCE = D("0.000001")


def python_value(book: D, roe: D, payout: D, franking: D, ke: D) -> D:
    total = D(0)
    for factor, prob in SCENARIOS:
        value, _, _ = value_per_share(
            book_start=book,
            roe_start=roe * factor,
            ke=ke,
            payout_ratio=payout,
            franking_pct=franking,
        )
        total += prob * value
    return total


def main() -> int:
    worst = D(0)
    print(f"{'symbol':8} {'ke':4} {'python':>12} {'sql':>12} {'diff':>10}")
    for symbol, (book, roe, payout, franking) in INPUTS.items():
        for name, ke in KE.items():
            py = python_value(book, roe, payout, franking, ke)
            sql = SQL_PW_FRANK[symbol][name]
            diff = abs(py - sql)
            worst = max(worst, diff)
            print(f"{symbol:8} {name:4} {py:12.6f} {sql:12.6f} {diff:10.6f}")
    print(f"max |python - sql| = {worst}  (tolerance {TOLERANCE})")
    return 0 if worst <= TOLERANCE else 1


if __name__ == "__main__":
    raise SystemExit(main())
