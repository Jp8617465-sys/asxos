"""Deterministic canonical encoding of domain objects to JSON-safe values.

Extracted verbatim from ``asxos/brief/gold.py::jsonable`` (2026-09-02). It was
never brief-specific — it is a general canonical serialiser that happened to
live next to its first caller. Splitting it out makes characterization
snapshots available to every module rather than only the brief render path.

**Why this is snapshot-safe, and why that property is load-bearing:** unknown
types raise ``TypeError`` rather than falling back to ``repr()``. A ``repr()``
fallback would silently embed memory addresses and other run-varying detail
into a stored payload, so two runs over identical data would differ and the
snapshot would be worthless as an equivalence check. Do not add a permissive
fallback here.

Decimal encodes as ``str``, never ``float`` — the repo is Decimal-only for
monetary and statistical values (CLAUDE.md non-negotiable #5) and a float round
trip loses exactness.

Leaf module: stdlib imports only.
"""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum

DEFAULT_CONTEXT = "payload"


def to_canonical(value: object, *, context: str = DEFAULT_CONTEXT) -> object:
    """Dates ISO, Decimal as strings, dataclasses via field recursion. No secrets.

    ``context`` names the caller in the ``TypeError`` raised for an
    unencodable type, so a failure says which payload rejected the value.
    """
    if value is None or isinstance(value, bool | int | str):
        return value
    if isinstance(value, float):
        return value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        return {
            f.name: to_canonical(getattr(value, f.name), context=context)
            for f in fields(value)
        }
    if isinstance(value, dict):
        return {str(k): to_canonical(v, context=context) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [to_canonical(v, context=context) for v in value]
    raise TypeError(f"cannot encode {type(value).__name__} for {context}")
