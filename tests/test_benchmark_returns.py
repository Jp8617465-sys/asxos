"""Tests for benchmark return primitives (asxos/domain/benchmark/returns.py).

Pure Decimal math: simple holding-period return and portfolio-minus-benchmark
alpha, plus the positive-base guard.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from asxos.domain.benchmark.returns import alpha, period_return


def test_period_return_positive() -> None:
    # 100 → 104.2 = +4.2%
    assert period_return(Decimal("100"), Decimal("104.2")) == Decimal("0.042")


def test_period_return_negative() -> None:
    assert period_return(Decimal("100"), Decimal("90")) == Decimal("-0.10")


def test_period_return_zero_change() -> None:
    assert period_return(Decimal("100"), Decimal("100")) == Decimal("0")


def test_period_return_rejects_zero_base() -> None:
    with pytest.raises(ValueError, match="must be positive"):
        period_return(Decimal("0"), Decimal("100"))


def test_period_return_rejects_negative_base() -> None:
    with pytest.raises(ValueError, match="must be positive"):
        period_return(Decimal("-5"), Decimal("100"))


def test_alpha_is_excess_return() -> None:
    # portfolio +4.2% vs benchmark +3.1% → +1.1% alpha
    assert alpha(Decimal("4.2"), Decimal("3.1")) == Decimal("1.1")


def test_alpha_negative_when_underperforming() -> None:
    assert alpha(Decimal("2.0"), Decimal("3.5")) == Decimal("-1.5")


def test_period_return_and_alpha_compose() -> None:
    # Realistic since-inception: portfolio 200k→210k (+5%), XJO-TR 7000→7140 (+2%)
    port = period_return(Decimal("200000"), Decimal("210000")) * 100
    bench = period_return(Decimal("7000"), Decimal("7140")) * 100
    assert port == Decimal("5")
    assert bench == Decimal("2")
    assert alpha(port, bench) == Decimal("3")
