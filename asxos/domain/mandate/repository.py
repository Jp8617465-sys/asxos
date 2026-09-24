"""Persistence and governance for the mandate layer (0062).

Mirrors `research/registry/repository.py`: `payload` is the source of truth,
content-addressed rows are `ON CONFLICT DO NOTHING`, mutation is refused by
the table's own triggers. `RepositoryConn` is a Protocol, not
`asyncpg.Connection`, so this module stays driver-free
(`tests/test_domain_purity.py`) and tests pass a mock with an ordered call
log — the Phase 2a lesson: the governance_events INSERT must precede the
UPDATE, and only the *emitted statement order* proves it.

Every public function checks the personal-use firewall: goals are income and
net worth (AGENTS.md §2), and the derived caps are personal investment
content.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Final, Protocol, cast

from asxos.domain.decision_engine.portfolio_state import require_personal_use
from asxos.domain.decision_engine.sizer import SizingPolicy
from asxos.domain.governance.transitions import apply_governance_transition
from asxos.domain.mandate.types import Goals, Mandate, MandateStatus


class RepositoryConn(Protocol):
    async def execute(self, query: str, *args: object) -> str: ...
    async def fetchrow(self, query: str, *args: object) -> Any: ...
    async def fetch(self, query: str, *args: object) -> list[Any]: ...
    async def fetchval(self, query: str, *args: object) -> Any: ...


@dataclass(frozen=True)
class StoredMandate:
    mandate_id: int
    goal_version_id: int
    governance_status: MandateStatus
    derivation_version: str
    mandate: Mandate
    memo_html: str


def _dump(model: Goals | Mandate) -> str:
    return json.dumps(model.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))


def _payload(raw: object) -> dict[str, object]:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str | bytes | bytearray):
        loaded = json.loads(raw)
        if isinstance(loaded, dict):
            return loaded
    raise TypeError(f"unexpected payload column type: {type(raw)!r}")


SQL_INSERT_GOALS: Final[str] = (
    "INSERT INTO financial_goals (as_of, investable_assets_aud, income_aud_pa, savings_aud_pa, "
    "target_wealth_aud, horizon_years, drawdown_tolerance_pct, liquidity_needs, emergency_months, "
    "account_type, marginal_rate_pct, brokerage_aud_per_side, stated_by, content_hash, payload) "
    "VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb, $9, $10, $11, $12, $13, $14, $15::jsonb) "
    "ON CONFLICT (content_hash) DO NOTHING RETURNING goal_version_id"
)
SQL_GOALS_ID_BY_HASH: Final[str] = "SELECT goal_version_id FROM financial_goals WHERE content_hash = $1"
SQL_LOAD_GOALS: Final[str] = "SELECT goal_version_id, payload FROM financial_goals WHERE goal_version_id = $1"
SQL_INSERT_MANDATE: Final[str] = (
    "INSERT INTO mandates (goal_version_id, as_of, derivation_version, goals_content_hash, content_hash, "
    "outputs, memo_html, governance_status) "
    "VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7, 'pending_review') "
    "ON CONFLICT (content_hash) DO NOTHING RETURNING mandate_id"
)
SQL_MANDATE_ID_BY_HASH: Final[str] = "SELECT mandate_id FROM mandates WHERE content_hash = $1"
SQL_LOAD_MANDATE: Final[str] = (
    "SELECT mandate_id, goal_version_id, governance_status, derivation_version, outputs, memo_html "
    "FROM mandates WHERE mandate_id = $1"
)
SQL_LATEST_APPROVED: Final[str] = (
    "SELECT mandate_id, goal_version_id, governance_status, derivation_version, outputs, memo_html "
    "FROM mandates WHERE governance_status = 'approved' ORDER BY as_of DESC, mandate_id DESC LIMIT 1"
)
SQL_LIST: Final[str] = (
    "SELECT mandate_id, goal_version_id, governance_status, derivation_version, as_of, created_at "
    "FROM mandates ORDER BY mandate_id DESC LIMIT $1"
)


async def save_goals(conn: RepositoryConn, goals: Goals) -> int:
    """Append a goals row; a re-statement with identical content returns the existing id."""
    require_personal_use()
    needs = json.dumps([n.model_dump(mode="json") for n in goals.liquidity_needs])
    new_id = await conn.fetchval(
        SQL_INSERT_GOALS,
        goals.as_of, goals.investable_assets_aud, goals.income_aud_pa, goals.savings_aud_pa,
        goals.target_wealth_aud, goals.horizon_years, goals.drawdown_tolerance_pct, needs,
        goals.emergency_months, goals.account_type, goals.marginal_rate_pct,
        goals.brokerage_aud_per_side, goals.stated_by, goals.content_hash, _dump(goals),
    )
    if new_id is not None:
        return int(new_id)
    existing = await conn.fetchval(SQL_GOALS_ID_BY_HASH, goals.content_hash)
    if existing is None:
        raise RuntimeError("financial_goals insert returned no id and no row carries this content_hash")
    return int(existing)


async def load_goals(conn: RepositoryConn, goal_version_id: int) -> Goals:
    require_personal_use()
    row = await conn.fetchrow(SQL_LOAD_GOALS, goal_version_id)
    if row is None:
        raise ValueError(f"financial_goals {goal_version_id} not found")
    return Goals.model_validate(_payload(row["payload"]))


async def save_mandate(conn: RepositoryConn, mandate: Mandate, *, goal_version_id: int, memo_html: str) -> int:
    """Append a mandate at pending_review (status stated explicitly — 0059's lesson)."""
    require_personal_use()
    if not memo_html:
        raise ValueError("a mandate is stored with its memo; memo_html is empty")
    new_id = await conn.fetchval(
        SQL_INSERT_MANDATE,
        goal_version_id, mandate.as_of, mandate.derivation_version, mandate.goals_content_hash,
        mandate.content_hash, _dump(mandate), memo_html,
    )
    if new_id is not None:
        return int(new_id)
    existing = await conn.fetchval(SQL_MANDATE_ID_BY_HASH, mandate.content_hash)
    if existing is None:
        raise RuntimeError("mandates insert returned no id and no row carries this content_hash")
    return int(existing)


def _stored(row: Any) -> StoredMandate:
    return StoredMandate(
        mandate_id=int(row["mandate_id"]),
        goal_version_id=int(row["goal_version_id"]),
        governance_status=row["governance_status"],
        derivation_version=row["derivation_version"],
        mandate=Mandate.model_validate(_payload(row["outputs"])),
        memo_html=row["memo_html"],
    )


async def load_mandate(conn: RepositoryConn, mandate_id: int) -> StoredMandate:
    require_personal_use()
    row = await conn.fetchrow(SQL_LOAD_MANDATE, mandate_id)
    if row is None:
        raise ValueError(f"mandate {mandate_id} not found")
    return _stored(row)


async def latest_approved_mandate(conn: RepositoryConn) -> StoredMandate | None:
    require_personal_use()
    row = await conn.fetchrow(SQL_LATEST_APPROVED)
    return _stored(row) if row is not None else None


async def list_mandates(conn: RepositoryConn, *, limit: int = 20) -> list[Any]:
    require_personal_use()
    return await conn.fetch(SQL_LIST, limit)


async def _transition(conn: RepositoryConn, mandate_id: int, *, to_status: MandateStatus, reasoning: str) -> StoredMandate:
    if not reasoning or not reasoning.strip():
        raise ValueError(f"reasoning is required to {to_status.replace('_', ' ')} a mandate")
    current = await load_mandate(conn, mandate_id)
    if current.governance_status != "pending_review":
        raise ValueError(
            f"Cannot move mandate {mandate_id} to {to_status!r} — governance_status is "
            f"{current.governance_status!r}, expected 'pending_review'."
        )
    # INSERT governance_events THEN UPDATE mandates — the shared helper owns that order.
    # The helper is typed against asyncpg.Connection; this module stays driver-free.
    await apply_governance_transition(
        cast(Any, conn),
        table_name="mandates",
        id_column="mandate_id",
        object_type="mandate",
        object_id=mandate_id,
        from_status="pending_review",
        to_status=to_status,
        reasoning=reasoning.strip(),
        actor="human",
    )
    return await load_mandate(conn, mandate_id)


async def approve_mandate(conn: RepositoryConn, mandate_id: int, *, reasoning: str) -> StoredMandate:
    """James's ratification (`MANDATE approve <id> <reason>`): pending_review → approved."""
    require_personal_use()
    return await _transition(conn, mandate_id, to_status="approved", reasoning=reasoning)


async def reject_mandate(conn: RepositoryConn, mandate_id: int, *, reasoning: str) -> StoredMandate:
    require_personal_use()
    return await _transition(conn, mandate_id, to_status="rejected", reasoning=reasoning)


def sizing_policy_from(mandate: Mandate, *, capital_aud: Decimal | None = None) -> SizingPolicy:
    """The SizingPolicy the paper packet builder reads instead of the live profile.

    `capital_aud` defaults to the mandate's deployable capital; the paper book's
    measured NAV may be passed once positions exist. The register floors/caps
    still bind inside SizingPolicy (cash ≥ 7.5, sector ≤ 30).
    """
    o = mandate.outputs
    return SizingPolicy(
        capital_aud=capital_aud if capital_aud is not None else o.deployable_capital_aud.value,
        position_cap_pct=o.position_cap_pct.value,
        min_position_aud=o.min_position_aud.value,
        cash_floor_pct=o.cash_floor_pct.value,
    )


__all__ = [
    "RepositoryConn",
    "StoredMandate",
    "approve_mandate",
    "latest_approved_mandate",
    "list_mandates",
    "load_goals",
    "load_mandate",
    "reject_mandate",
    "save_goals",
    "save_mandate",
    "sizing_policy_from",
]
