"""
Profile persistence + the risk-label → scalar mapping.

The validators in `types.py` enforce field bounds at construction time;
this module owns the DB I/O (load_active / save / activate) plus the
on-read normalisation of `score_weights_json` to exact `Decimal("1")` sum
(per plan I.3 — the DB CHECK tolerates ±0.001; in-memory math is exact).

CLI gating per plan Part 0 Q1: callers in `asxos/cli/main.py` check
`ASXOS_PERSONAL_USE=1` before invoking any function here. The profile
module itself is importable without the flag — tests don't need it set.
"""
from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

import asyncpg

from asxos import clock
from asxos.domain.portfolio.types import (
    DEFAULT_SCORE_WEIGHTS,
    RISK_TOLERANCE_SCALARS,
    Profile,
    RiskTolerance,
)


def risk_tolerance_scalar(label: str) -> Decimal:
    """Map a risk-tolerance label to its canonical scalar in [0, 1]."""
    if label not in RISK_TOLERANCE_SCALARS:
        raise ValueError(
            f"unknown risk_tolerance {label!r}; valid: {list(RISK_TOLERANCE_SCALARS)}"
        )
    return RISK_TOLERANCE_SCALARS[label]  # type: ignore[index]  # validated above


def _normalise_score_weights(raw: dict[str, Any]) -> dict[str, Decimal]:
    """Rescale to sum=Decimal('1') exactly. Storage tolerates ±0.001 via
    the CHECK constraint; this enforces the in-memory invariant."""
    p = Decimal(str(raw["prob_up"]))
    r = Decimal(str(raw["expected_return"]))
    total = p + r
    if total == Decimal("0"):
        # Pathological — DB CHECK prevents this, but be defensive
        raise ValueError("score_weights sum is zero")
    return {
        "prob_up": p / total,
        "expected_return": r / total,
    }


def _row_to_profile(row: asyncpg.Record) -> Profile:
    """Convert an asyncpg Record from `profiles` to a Profile dataclass."""
    raw_weights = row["score_weights_json"]
    if isinstance(raw_weights, str):
        raw_weights = json.loads(raw_weights)
    weights = _normalise_score_weights(raw_weights)

    return Profile(
        profile_id=row["profile_id"],
        name=row["name"],
        is_active=row["is_active"],
        account_type=row["account_type"],
        risk_tolerance=row["risk_tolerance"],
        risk_tolerance_scalar=Decimal(str(row["risk_tolerance_scalar"])),
        capital_aud=Decimal(str(row["capital_aud"])),
        cash_floor_pct=Decimal(str(row["cash_floor_pct"])),
        leverage_cap=Decimal(str(row["leverage_cap"])),
        per_name_cap_pct=Decimal(str(row["per_name_cap_pct"])),
        sector_cap_pct=Decimal(str(row["sector_cap_pct"])),
        excluded_sectors=tuple(row["excluded_sectors"]),
        excluded_symbols=tuple(row["excluded_symbols"]),
        min_position_aud=Decimal(str(row["min_position_aud"])),
        horizon_years=row["horizon_years"],
        defer_near_boundary_sells=row["defer_near_boundary_sells"],
        score_weights_json=weights,
        created_at=row["created_at"].date() if hasattr(row["created_at"], "date") else row["created_at"],
        updated_at=row["updated_at"].date() if hasattr(row["updated_at"], "date") else row["updated_at"],
    )


async def load_active(conn: asyncpg.Connection) -> Profile | None:
    """Return the row with is_active=TRUE, or None if no profile is active.
    Callers raise on None (CLI -> typer.BadParameter; job -> RuntimeError)."""
    row = await conn.fetchrow(
        """
        SELECT profile_id, name, is_active, account_type, risk_tolerance,
               risk_tolerance_scalar, capital_aud, cash_floor_pct, leverage_cap,
               per_name_cap_pct, sector_cap_pct, excluded_sectors, excluded_symbols,
               min_position_aud, horizon_years, defer_near_boundary_sells,
               score_weights_json, created_at, updated_at
        FROM profiles
        WHERE is_active = TRUE
        """
    )
    if row is None:
        return None
    return _row_to_profile(row)


async def load_by_name(conn: asyncpg.Connection, name: str) -> Profile | None:
    """Return a named profile or None."""
    row = await conn.fetchrow(
        """
        SELECT profile_id, name, is_active, account_type, risk_tolerance,
               risk_tolerance_scalar, capital_aud, cash_floor_pct, leverage_cap,
               per_name_cap_pct, sector_cap_pct, excluded_sectors, excluded_symbols,
               min_position_aud, horizon_years, defer_near_boundary_sells,
               score_weights_json, created_at, updated_at
        FROM profiles
        WHERE name = $1
        """,
        name,
    )
    if row is None:
        return None
    return _row_to_profile(row)


async def list_profiles(conn: asyncpg.Connection) -> list[Profile]:
    """All profiles, ordered by created_at desc."""
    rows = await conn.fetch(
        """
        SELECT profile_id, name, is_active, account_type, risk_tolerance,
               risk_tolerance_scalar, capital_aud, cash_floor_pct, leverage_cap,
               per_name_cap_pct, sector_cap_pct, excluded_sectors, excluded_symbols,
               min_position_aud, horizon_years, defer_near_boundary_sells,
               score_weights_json, created_at, updated_at
        FROM profiles
        ORDER BY created_at DESC
        """
    )
    return [_row_to_profile(r) for r in rows]


async def save(
    conn: asyncpg.Connection,
    *,
    name: str,
    account_type: str,
    risk_tolerance: RiskTolerance,
    capital_aud: Decimal,
    cash_floor_pct: Decimal = Decimal("0.05"),
    leverage_cap: Decimal = Decimal("1.0"),
    per_name_cap_pct: Decimal = Decimal("0.10"),
    sector_cap_pct: Decimal = Decimal("0.30"),
    excluded_sectors: tuple[str, ...] = (),
    excluded_symbols: tuple[str, ...] = (),
    min_position_aud: Decimal = Decimal("1000"),
    horizon_years: int = 10,
    defer_near_boundary_sells: bool = True,
    score_weights_json: dict[str, Decimal] | None = None,
) -> int:
    """Insert a new profile row. Returns the profile_id.

    The dataclass validators run on a Profile constructed before INSERT so
    bad inputs raise before any DB roundtrip. Activation is a separate
    call (`activate(conn, name)`) — `save()` always inserts with
    `is_active=FALSE`.
    """
    weights = score_weights_json or dict(DEFAULT_SCORE_WEIGHTS)
    today = clock.today()

    # Construct and validate via the dataclass before hitting the DB.
    Profile(
        profile_id=None,
        name=name,
        is_active=False,
        account_type=account_type,  # type: ignore[arg-type]
        risk_tolerance=risk_tolerance,
        risk_tolerance_scalar=risk_tolerance_scalar(risk_tolerance),
        capital_aud=capital_aud,
        cash_floor_pct=cash_floor_pct,
        leverage_cap=leverage_cap,
        per_name_cap_pct=per_name_cap_pct,
        sector_cap_pct=sector_cap_pct,
        excluded_sectors=excluded_sectors,
        excluded_symbols=excluded_symbols,
        min_position_aud=min_position_aud,
        horizon_years=horizon_years,
        defer_near_boundary_sells=defer_near_boundary_sells,
        score_weights_json=weights,
        created_at=today,
        updated_at=today,
    )

    profile_id = await conn.fetchval(
        """
        INSERT INTO profiles (
            name, account_type, risk_tolerance, risk_tolerance_scalar,
            capital_aud, cash_floor_pct, leverage_cap,
            per_name_cap_pct, sector_cap_pct,
            excluded_sectors, excluded_symbols,
            min_position_aud, horizon_years,
            defer_near_boundary_sells, score_weights_json
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10::text[], $11::text[],
            $12, $13, $14, $15::jsonb
        )
        RETURNING profile_id
        """,
        name,
        account_type,
        risk_tolerance,
        risk_tolerance_scalar(risk_tolerance),
        capital_aud,
        cash_floor_pct,
        leverage_cap,
        per_name_cap_pct,
        sector_cap_pct,
        list(excluded_sectors),
        list(excluded_symbols),
        min_position_aud,
        horizon_years,
        defer_near_boundary_sells,
        json.dumps({k: str(v) for k, v in weights.items()}),
    )
    return int(profile_id)  # asyncpg fetchval returns Any


async def activate(conn: asyncpg.Connection, name: str) -> int:
    """Atomically flip is_active=TRUE on `name`, FALSE on every other row.

    Uses the `set_active_profile()` PL/pgSQL function (migration 0005) which
    asserts the at-most-one-active invariant by raising on violation. The
    partial unique index would catch it too; this is belt-and-braces.
    """
    profile_id = await conn.fetchval("SELECT set_active_profile($1)", name)
    return int(profile_id)  # asyncpg fetchval returns Any
