"""One predicate for "this field is missing". Never repeated inline.

Why a helper and not `is None`: `rs_financial_statements.currency` carries BOTH
NULL and empty string — 70,393 and 2,511 rows respectively as at 2026-09-08 — and
`ingestion/financial_statements.py:222-230` records that whitespace-only values
are uncaught as well.  A predicate that tests only for NULL therefore passes rows
that have no value.

That is not hypothetical.  The Phase 1 run reported CBA as carrying a currency
gap and valued it anyway, because the gap was collected and never raised; the
same class of error one layer down is a predicate that never sees the gap at all.
Both failure modes end with a number computed on absent data, so both are closed:
this module is the only absence test, and `builder.py` raises on what it returns.
"""
from __future__ import annotations


def is_missing(value: object) -> bool:
    """True when a field carries no usable value: None, empty, or whitespace-only."""
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    return False


def is_present(value: object) -> bool:
    return not is_missing(value)
