"""
CSV import parser tests for asxos.domain.tax.import_csv.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from asxos.domain.tax.import_csv import parse_csv


def _write_csv(path: Path, header: list[str], rows: list[list[str]]) -> Path:
    body = ",".join(header) + "\n"
    for r in rows:
        body += ",".join(r) + "\n"
    path.write_text(body)
    return path


def test_parses_minimal_row(tmp_path: Path) -> None:
    csv_path = _write_csv(
        tmp_path / "h.csv",
        ["symbol", "acquired_at", "quantity", "cost_base_normal", "account_type"],
        [["BHP.AU", "2024-06-15", "100", "4500.00", "individual"]],
    )
    rows = parse_csv(csv_path)
    assert len(rows) == 1
    r = rows[0]
    assert r.symbol == "BHP.AU"
    assert r.acquired_at == date(2024, 6, 15)
    assert r.quantity == Decimal("100")
    assert r.cost_base_normal == Decimal("4500.00")
    assert r.cost_base_div296 == Decimal("4500.00")  # defaulted from normal
    assert r.account_type == "individual"


def test_cost_base_div296_override(tmp_path: Path) -> None:
    csv_path = _write_csv(
        tmp_path / "h.csv",
        [
            "symbol",
            "acquired_at",
            "quantity",
            "cost_base_normal",
            "cost_base_div296",
            "account_type",
        ],
        [["BHP.AU", "2024-06-15", "100", "4500", "5500", "smsf"]],
    )
    rows = parse_csv(csv_path)
    assert rows[0].cost_base_div296 == Decimal("5500")


def test_missing_required_column_raises(tmp_path: Path) -> None:
    csv_path = _write_csv(
        tmp_path / "h.csv",
        ["symbol", "acquired_at", "quantity"],
        [["BHP.AU", "2024-06-15", "100"]],
    )
    with pytest.raises(ValueError, match="missing required columns"):
        parse_csv(csv_path)


def test_invalid_date_raises_with_line_number(tmp_path: Path) -> None:
    csv_path = _write_csv(
        tmp_path / "h.csv",
        ["symbol", "acquired_at", "quantity", "cost_base_normal", "account_type"],
        [["BHP.AU", "not-a-date", "100", "4500", "individual"]],
    )
    with pytest.raises(ValueError, match="h.csv:2"):
        parse_csv(csv_path)


def test_unknown_account_type_raises(tmp_path: Path) -> None:
    csv_path = _write_csv(
        tmp_path / "h.csv",
        ["symbol", "acquired_at", "quantity", "cost_base_normal", "account_type"],
        [["BHP.AU", "2024-06-15", "100", "4500", "trust"]],
    )
    with pytest.raises(ValueError, match="account_type"):
        parse_csv(csv_path)


def test_non_positive_quantity_raises(tmp_path: Path) -> None:
    csv_path = _write_csv(
        tmp_path / "h.csv",
        ["symbol", "acquired_at", "quantity", "cost_base_normal", "account_type"],
        [["BHP.AU", "2024-06-15", "0", "4500", "individual"]],
    )
    with pytest.raises(ValueError, match="non-positive quantity"):
        parse_csv(csv_path)
