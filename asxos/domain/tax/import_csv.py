"""
CSV importer for holding_lots.

Format (header required):
  symbol, acquired_at, quantity, cost_base_normal, account_type
  [, cost_base_div296, broker_ref, notes, cost_base_usd]

- `symbol` is auto-inserted into `universe` if absent (demand-driven; see cli/main.py).
- `acquired_at` is YYYY-MM-DD.
- `cost_base_div296` defaults to `cost_base_normal` when missing (spec §6.4).
- `cost_base_usd`: optional — for US ESPP/stock lots whose grant price is in USD.
  When present, `acquisition_fx_rate` is resolved from fx_rates table in cli/main.py
  and `cost_base_normal` is computed as cost_base_usd / acquisition_fx_rate (AUD).
  Both cost_base_normal and cost_base_usd are stored for Div 775 FX gain/loss (M15-7).
- Any malformed row aborts the import — no partial writes.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

REQUIRED_COLUMNS = ("symbol", "acquired_at", "quantity", "account_type")


@dataclass(frozen=True)
class LotRow:
    symbol: str
    acquired_at: date
    quantity: Decimal
    cost_base_normal: Decimal    # AUD — always present; computed from cost_base_usd if provided
    cost_base_div296: Decimal
    account_type: str
    broker_ref: str
    notes: str
    cost_base_usd: Decimal | None = None   # USD — for US lots only; None for ASX lots


def parse_csv(path: Path) -> list[LotRow]:
    with path.open(newline="") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None:
            raise ValueError(f"{path} has no header row")
        missing = [c for c in REQUIRED_COLUMNS if c not in reader.fieldnames]
        if missing:
            raise ValueError(f"{path} missing required columns: {missing}")

        has_usd = "cost_base_usd" in (reader.fieldnames or [])
        has_normal = "cost_base_normal" in (reader.fieldnames or [])

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

                # cost_base_usd — optional, for US lots
                cb_usd: Decimal | None = None
                if has_usd:
                    raw_usd = (raw.get("cost_base_usd") or "").strip()
                    if raw_usd:
                        cb_usd = Decimal(raw_usd)
                        if cb_usd < 0:
                            raise ValueError(f"negative cost_base_usd {cb_usd}")

                # cost_base_normal — required unless cost_base_usd present (resolved via FX in CLI)
                cb_normal: Decimal | None = None
                if has_normal:
                    raw_normal = (raw.get("cost_base_normal") or "").strip()
                    if raw_normal:
                        cb_normal = Decimal(raw_normal)
                        if cb_normal < 0:
                            raise ValueError(f"negative cost_base_normal {cb_normal}")

                if cb_normal is None and cb_usd is None:
                    raise ValueError("one of cost_base_normal or cost_base_usd must be provided")

                # Placeholder: if only USD provided, cost_base_normal will be resolved
                # in cli/main.py using the fx_rates table.  Store 0 as sentinel here.
                cb_normal_final = cb_normal if cb_normal is not None else Decimal("0")

                cb_div296_raw = raw.get("cost_base_div296", "").strip() if raw.get("cost_base_div296") else ""
                cb_div296 = Decimal(cb_div296_raw) if cb_div296_raw else cb_normal_final

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
                        cost_base_normal=cb_normal_final,
                        cost_base_div296=cb_div296,
                        account_type=account_type,
                        broker_ref=broker_ref,
                        notes=notes,
                        cost_base_usd=cb_usd,
                    )
                )
            except (KeyError, ValueError, InvalidOperation) as e:
                raise ValueError(f"{path}:{lineno}: {e}") from e

    return rows
