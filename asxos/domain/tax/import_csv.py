"""
CSV importer for holding_lots.

Format (header required):
  symbol, acquired_at, quantity, cost_base_normal, account_type[, cost_base_div296, broker_ref, notes]

- `symbol` must already exist in `universe` (FK).
- `acquired_at` is YYYY-MM-DD.
- `cost_base_div296` defaults to `cost_base_normal` when missing (spec §6.4).
- Any malformed row aborts the import — no partial writes.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

REQUIRED_COLUMNS = ("symbol", "acquired_at", "quantity", "cost_base_normal", "account_type")


@dataclass(frozen=True)
class LotRow:
    symbol: str
    acquired_at: date
    quantity: Decimal
    cost_base_normal: Decimal
    cost_base_div296: Decimal
    account_type: str
    broker_ref: str
    notes: str


def parse_csv(path: Path) -> list[LotRow]:
    with path.open(newline="") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None:
            raise ValueError(f"{path} has no header row")
        missing = [c for c in REQUIRED_COLUMNS if c not in reader.fieldnames]
        if missing:
            raise ValueError(f"{path} missing required columns: {missing}")

        rows: list[LotRow] = []
        for lineno, raw in enumerate(reader, start=2):
            try:
                symbol = raw["symbol"].strip()
                if not symbol:
                    raise ValueError("empty symbol")

                acquired = date.fromisoformat(raw["acquired_at"].strip())

                qty = Decimal(raw["quantity"].strip())
                if qty <= 0:
                    raise ValueError(f"non-positive quantity {qty}")

                cb_normal = Decimal(raw["cost_base_normal"].strip())
                if cb_normal < 0:
                    raise ValueError(f"negative cost_base_normal {cb_normal}")

                cb_div296_raw = raw.get("cost_base_div296", "").strip() if raw.get("cost_base_div296") else ""
                cb_div296 = Decimal(cb_div296_raw) if cb_div296_raw else cb_normal

                account_type = raw["account_type"].strip()
                if account_type not in ("individual", "smsf"):
                    raise ValueError(f"unknown account_type {account_type!r}")

                broker_ref = (raw.get("broker_ref") or "").strip()
                notes = (raw.get("notes") or "").strip()

                rows.append(
                    LotRow(
                        symbol=symbol,
                        acquired_at=acquired,
                        quantity=qty,
                        cost_base_normal=cb_normal,
                        cost_base_div296=cb_div296,
                        account_type=account_type,
                        broker_ref=broker_ref,
                        notes=notes,
                    )
                )
            except (KeyError, ValueError, InvalidOperation) as e:
                raise ValueError(f"{path}:{lineno}: {e}") from e

    return rows
