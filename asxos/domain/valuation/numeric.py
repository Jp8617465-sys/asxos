"""Determinism substrate for the valuation package.

`Decimal` division and exponentiation read the PROCESS-GLOBAL context, which any
other module can mutate.  Decimal types alone therefore do not give
"same inputs, same value" — an explicit local context does.  Every computation in
this package runs inside `valuation_context()`, and every stored figure is
quantised by `q6()`.  Intermediates keep full precision; only stored figures
quantise.
"""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from decimal import Context, Decimal, DivisionByZero, InvalidOperation, localcontext
from typing import Final

#: 34 significant digits — far beyond NUMERIC(18,6), so quantisation is the only
#: place precision is ever lost, and it happens once, at the boundary.
PRECISION: Final[int] = 34

Q6: Final[Decimal] = Decimal("0.000001")

_CONTEXT: Final[Context] = Context(
    prec=PRECISION,
    traps=[InvalidOperation, DivisionByZero],
)


@contextmanager
def valuation_context() -> Iterator[None]:
    """Run a block under the package's own Decimal context.

    Traps rather than returning NaN: a division by zero in a valuation is a
    defect to surface, never a value to carry forward.
    """
    with localcontext(_CONTEXT):
        yield


def q6(value: Decimal) -> Decimal:
    """Quantise a stored figure to 6dp, banker's rounding — the NUMERIC(18,6) shape."""
    if isinstance(value, float):
        raise TypeError("float reached the valuation quantiser")
    return value.quantize(Q6)


def dec(value: object) -> Decimal:
    """Coerce a DB value to Decimal, refusing float outright (CLAUDE.md #5)."""
    if isinstance(value, float):
        raise TypeError("float reached the valuation loader")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def compound(base: Decimal, exponent: int) -> Decimal:
    """`base ** exponent` by repeated multiplication.

    `Decimal.__pow__` with a non-integral result routes through the context's
    inexact power, whose last digits depend on the ambient precision.  Repeated
    multiplication is exact for an integer exponent and therefore reproducible.
    """
    if exponent < 0:
        raise ValueError("compound() takes a non-negative exponent")
    result = Decimal(1)
    for _ in range(exponent):
        result *= base
    return result
