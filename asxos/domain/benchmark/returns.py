"""Benchmark return primitives — pure Decimal, no DB, no numpy.

`period_return` is the simple holding-period return between two levels; `alpha`
is the portfolio-minus-benchmark excess. Both operate on *levels* (capital_aud,
benchmark_tr_level, an index close) and return a fraction (0.042 = +4.2%), so the
caller controls percent formatting. Used by the wealth-state collector (Stage 1d)
and the benchmark-performance-analyst agent.
"""
from __future__ import annotations

from decimal import Decimal


def period_return(start: Decimal, end: Decimal) -> Decimal:
    """Simple return ``(end - start) / start`` as a Decimal fraction.

    Raises ``ValueError`` when ``start <= 0`` — a zero/negative base has no
    meaningful return, and silently returning 0 would hide a data bug. Callers
    gate on a positive inception level before calling.
    """
    if start <= 0:
        raise ValueError(f"period_return start must be positive, got {start}")
    return (end - start) / start


def alpha(portfolio_return: Decimal, benchmark_return: Decimal) -> Decimal:
    """Excess return: portfolio minus benchmark, in the same units as the inputs.

    Both arguments must already be on the same basis (both fractions or both
    percentages); the function does not convert.
    """
    return portfolio_return - benchmark_return
