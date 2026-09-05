"""Pin ``asxos.serde.canonical.to_canonical`` — extracted from ``gold.py::jsonable``.

The extraction (2026-09-02) claimed to be behaviour-preserving. These tests are what
makes that claim checkable rather than asserted: every branch of the original
function, plus the two properties the snapshot machinery depends on (no ``repr()``
fallback, Decimal as exact string).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum

import pytest

from asxos.brief.gold import jsonable
from asxos.serde.canonical import to_canonical


class Colour(Enum):
    RED = "red"
    TWO = 2


@dataclass
class Inner:
    amount: Decimal
    when: date


@dataclass
class Outer:
    name: str
    inner: Inner
    tags: list[str]


def test_passthrough_scalars() -> None:
    assert to_canonical(None) is None
    assert to_canonical(True) is True
    assert to_canonical(7) == 7
    assert to_canonical("x") == "x"
    assert to_canonical(1.5) == 1.5


def test_decimal_encodes_as_exact_string_not_float() -> None:
    """Decimal-only is CLAUDE.md non-negotiable #5; a float round trip loses exactness."""
    value = Decimal("0.1234567890123456789")
    encoded = to_canonical(value)
    assert encoded == "0.1234567890123456789"
    assert isinstance(encoded, str)
    assert Decimal(encoded) == value


def test_dates_and_datetimes_iso() -> None:
    assert to_canonical(date(2026, 9, 2)) == "2026-09-02"
    assert to_canonical(datetime(2026, 9, 2, 15, 17, tzinfo=UTC)) == "2026-09-02T15:17:00+00:00"


def test_datetime_checked_before_date() -> None:
    """``datetime`` subclasses ``date``; the wrong branch order silently truncates time."""
    moment = datetime(2026, 9, 2, 15, 17, tzinfo=UTC)
    assert to_canonical(moment) == moment.isoformat()
    assert "T" in str(to_canonical(moment))


def test_enum_uses_value() -> None:
    assert to_canonical(Colour.RED) == "red"
    assert to_canonical(Colour.TWO) == 2


def test_dataclass_recurses_by_field() -> None:
    got = to_canonical(
        Outer(name="a", inner=Inner(amount=Decimal("2.50"), when=date(2026, 1, 1)), tags=["x", "y"])
    )
    assert got == {
        "name": "a",
        "inner": {"amount": "2.50", "when": "2026-01-01"},
        "tags": ["x", "y"],
    }


def test_dataclass_type_is_not_an_instance() -> None:
    """A dataclass *class* is not encodable — only instances are."""
    with pytest.raises(TypeError):
        to_canonical(Outer)


def test_dict_keys_stringified_and_values_recursed() -> None:
    assert to_canonical({1: Decimal("3"), "b": date(2026, 1, 1)}) == {"1": "3", "b": "2026-01-01"}


def test_sequences_become_lists() -> None:
    assert to_canonical((Decimal("1"), Decimal("2"))) == ["1", "2"]
    assert to_canonical([Colour.RED]) == ["red"]


def test_unknown_type_raises_rather_than_repr_fallback() -> None:
    """The property the whole snapshot layer rests on.

    A ``repr()`` fallback would embed a memory address, so two runs over identical
    data would differ and a characterization snapshot would be worthless.
    """

    class Opaque:
        pass

    with pytest.raises(TypeError, match="cannot encode Opaque"):
        to_canonical(Opaque())


def test_context_names_the_caller_in_the_error() -> None:
    class Opaque:
        pass

    with pytest.raises(TypeError, match="for widget payload"):
        to_canonical(Opaque(), context="widget payload")


def test_gold_jsonable_message_unchanged_by_the_extraction() -> None:
    """Regression pin: gold.py's error text must survive the split byte-identical."""

    class Opaque:
        pass

    with pytest.raises(TypeError, match=r"^cannot encode Opaque for gold payload$"):
        jsonable(Opaque())


def test_gold_jsonable_still_delegates() -> None:
    payload = Outer(name="a", inner=Inner(Decimal("1.5"), date(2026, 3, 4)), tags=[])
    assert jsonable(payload) == to_canonical(payload, context="gold payload")
