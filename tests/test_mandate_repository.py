"""The repository emits INSERT governance_events BEFORE UPDATE mandates
(the Phase 2a lesson: only the emitted statement order proves it), refuses
transitions from any state but pending_review, and maps a mandate onto the
sizer's policy inside the register floors."""
from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from asxos.domain.decision_engine.sizer import SizingPolicy
from asxos.domain.mandate import Goals, derive
from asxos.domain.mandate import repository as repo


class FakeConn:
    """Ordered call log across execute/fetchrow/fetchval; a mandates row that
    reflects the last UPDATE so load-after-transition sees the new status."""

    def __init__(self, status: str = "pending_review") -> None:
        g = Goals(
            as_of=date(2026, 9, 19), investable_assets_aud=Decimal("25000"), income_aud_pa=Decimal("120000"),
            savings_aud_pa=Decimal("30000"), target_wealth_aud=Decimal("1000000"), horizon_years=10,
            drawdown_tolerance_pct=Decimal("25"), emergency_months=0, account_type="individual",
            marginal_rate_pct=Decimal("37"), brokerage_aud_per_side=Decimal("5"),
        )
        self.mandate = derive(g)
        self.status = status
        self.log: list[tuple[str, str]] = []

    def _row(self) -> dict[str, Any]:
        return {
            "mandate_id": 7, "goal_version_id": 3, "governance_status": self.status,
            "derivation_version": "v1", "outputs": json.dumps(self.mandate.model_dump(mode="json")),
            "memo_html": "<section/>",
        }

    async def execute(self, query: str, *args: object) -> str:
        self.log.append(("execute", query.split()[0].upper() + " " + " ".join(query.split()[1:3])))
        if query.lstrip().upper().startswith("UPDATE MANDATES"):
            self.status = str(args[0])
        return "OK"

    async def fetchrow(self, query: str, *args: object) -> Any:
        self.log.append(("fetchrow", " ".join(query.split()[:3])))
        if "UPDATE mandates" in query:
            self.status = str(args[0])
            return self._row()
        return self._row()

    async def fetch(self, query: str, *args: object) -> list[Any]:
        return []

    async def fetchval(self, query: str, *args: object) -> Any:
        self.log.append(("fetchval", " ".join(query.split()[:3])))
        return 7

    def transaction(self) -> Any:  # pragma: no cover - not exercised here
        raise NotImplementedError


@pytest.fixture(autouse=True)
def _personal_use(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")


async def test_approve_emits_the_audit_insert_before_the_update() -> None:
    conn = FakeConn()
    stored = await repo.approve_mandate(conn, 7, reasoning="ratified in the 2026-09-19 session")
    statements = [s for kind, s in conn.log if kind in {"execute", "fetchrow"}]
    insert_ix = next(i for i, s in enumerate(statements) if s.startswith("INSERT INTO governance_events"))
    update_ix = next(i for i, s in enumerate(statements) if s.startswith("UPDATE mandates"))
    assert insert_ix < update_ix, statements
    assert stored.governance_status == "approved"


async def test_reject_and_approve_refuse_a_non_pending_mandate() -> None:
    conn = FakeConn(status="approved")
    with pytest.raises(ValueError, match="expected 'pending_review'"):
        await repo.reject_mandate(conn, 7, reasoning="no")
    with pytest.raises(ValueError, match="expected 'pending_review'"):
        await repo.approve_mandate(conn, 7, reasoning="again")


async def test_a_reason_is_required() -> None:
    with pytest.raises(ValueError, match="reasoning is required"):
        await repo.approve_mandate(FakeConn(), 7, reasoning="   ")


async def test_save_mandate_states_pending_review_explicitly_and_needs_a_memo() -> None:
    conn = FakeConn()
    with pytest.raises(ValueError, match="memo_html"):
        await repo.save_mandate(conn, conn.mandate, goal_version_id=3, memo_html="")
    await repo.save_mandate(conn, conn.mandate, goal_version_id=3, memo_html="<section/>")
    assert any("INSERT INTO mandates" in s for _, s in conn.log)
    assert "'pending_review'" in repo.SQL_INSERT_MANDATE  # 0059: never a column DEFAULT


def test_sizing_policy_from_mandate_binds_inside_the_register() -> None:
    m = FakeConn().mandate
    p = repo.sizing_policy_from(m)
    assert isinstance(p, SizingPolicy)
    assert p.capital_aud == Decimal("25000")
    assert p.position_cap_pct == Decimal("10")
    assert p.min_position_aud == Decimal("1000")
    assert p.cash_floor_pct == Decimal("7.5")
    assert repo.sizing_policy_from(m, capital_aud=Decimal("24000")).capital_aud == Decimal("24000")


def test_personal_use_gate_holds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ASXOS_PERSONAL_USE", raising=False)
    import asyncio

    with pytest.raises(RuntimeError):
        asyncio.run(repo.load_mandate(FakeConn(), 7))
