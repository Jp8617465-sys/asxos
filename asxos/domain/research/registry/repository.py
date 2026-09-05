"""Append-only persistence for the research registry (migration 0050).

Mirrors `asxos.domain.decision_engine.repository`: `payload` is the only
authoritative column, reconstruction is exclusively `Model.model_validate`,
content-addressed rows are `ON CONFLICT DO NOTHING`, and mutation is refused
by the database trigger rather than by this module's good manners.
"""
from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any, Protocol

from asxos.domain.research.registry.promotion import PromotionState, advance
from asxos.domain.research.registry.types import ResearchHypothesis, ResearchRun, StrategyVersion


class RepositoryConn(Protocol):
    async def execute(self, query: str, *args: object) -> str: ...
    async def fetch(self, query: str, *args: object) -> list[Any]: ...
    async def fetchrow(self, query: str, *args: object) -> Mapping[str, object] | None: ...


def _dump(model: ResearchHypothesis | StrategyVersion | ResearchRun) -> str:
    return json.dumps(model.model_dump(mode="json"))


def _payload(row: Mapping[str, object]) -> dict[str, object]:
    raw = row["payload"]
    if isinstance(raw, str):
        return dict(json.loads(raw))
    if isinstance(raw, Mapping):
        return dict(raw)
    raise TypeError(f"unexpected payload column type: {type(raw)!r}")


async def save_hypothesis(conn: RepositoryConn, h: ResearchHypothesis) -> None:
    await conn.execute(
        "INSERT INTO research_hypotheses (hypothesis_id, content_hash, factor, created_at, payload) "
        "VALUES ($1, $2, $3, $4, $5::jsonb) ON CONFLICT (hypothesis_id) DO NOTHING",
        h.hypothesis_id, h.content_hash, h.factor, h.created_at, _dump(h),
    )


async def save_strategy_version(conn: RepositoryConn, s: StrategyVersion) -> None:
    await conn.execute(
        "INSERT INTO strategy_versions (strategy_version_id, content_hash, hypothesis_id, code_ref, created_at, payload) "
        "VALUES ($1, $2, $3, $4, $5, $6::jsonb) ON CONFLICT (strategy_version_id) DO NOTHING",
        s.strategy_version_id, s.content_hash, s.hypothesis_id, s.code_ref, s.created_at, _dump(s),
    )


async def save_run(conn: RepositoryConn, r: ResearchRun) -> None:
    """Every run is kept — `outcome = 'fail'` rows are the point, not noise."""
    await conn.execute(
        "INSERT INTO research_runs (run_id, content_hash, hypothesis_id, strategy_version_id, as_of, "
        "panel_hash, outcome, created_at, payload) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9::jsonb)",
        r.run_id, r.content_hash, r.hypothesis_id, r.strategy_version_id, r.as_of,
        r.panel_hash, r.outcome, r.created_at, _dump(r),
    )


async def list_runs(conn: RepositoryConn, *, hypothesis_id: str) -> list[ResearchRun]:
    """All runs for a hypothesis, failures included, oldest first."""
    rows = await conn.fetch(
        "SELECT payload FROM research_runs WHERE hypothesis_id = $1 ORDER BY created_at, run_id",
        hypothesis_id,
    )
    return [ResearchRun.model_validate(_payload(row)) for row in rows]


async def record_promotion(
    conn: RepositoryConn,
    *,
    strategy_version_id: str,
    current: PromotionState,
    to: PromotionState,
    evidence_run_id: str | None,
    reason: str,
    decided_by: str,
) -> PromotionState:
    """Validate the edge in code, then append the log row. The DB CHECKs backstop."""
    new_state = advance(current, to, evidence_run_id=evidence_run_id, reason=reason)
    await conn.execute(
        "INSERT INTO research_promotions (strategy_version_id, from_state, to_state, "
        "evidence_run_id, reason, decided_by, decided_at) "
        "VALUES ($1, $2, $3, $4, $5, $6, now())",
        strategy_version_id, current, new_state, evidence_run_id, reason, decided_by,
    )
    return new_state
