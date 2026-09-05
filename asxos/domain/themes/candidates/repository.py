"""Append-only persistence for ThemeVersion / CandidateSnapshot (migration 0051)."""
from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any, Protocol

from asxos.domain.themes.candidates.types import CandidateSnapshot, ThemeVersion


class RepositoryConn(Protocol):
    async def execute(self, query: str, *args: object) -> str: ...
    async def fetchrow(self, query: str, *args: object) -> Mapping[str, object] | None: ...
    async def fetch(self, query: str, *args: object) -> list[Any]: ...


def _payload(row: Mapping[str, object]) -> dict[str, object]:
    raw = row["payload"]
    if isinstance(raw, str):
        return dict(json.loads(raw))
    if isinstance(raw, Mapping):
        return dict(raw)
    raise TypeError(f"unexpected payload column type: {type(raw)!r}")


async def save_theme_version(conn: RepositoryConn, tv: ThemeVersion) -> None:
    await conn.execute(
        "INSERT INTO theme_versions (theme_version_id, content_hash, theme_code, as_of, knowledge_cutoff, "
        "expires_at, macro_thesis_id, data_mode, created_at, payload) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10::jsonb) ON CONFLICT (theme_version_id) DO NOTHING",
        tv.theme_version_id, tv.content_hash, tv.theme_code, tv.as_of, tv.knowledge_cutoff,
        tv.expires_at, tv.macro_thesis_id, tv.data_mode, tv.created_at, json.dumps(tv.model_dump(mode="json")),
    )


async def save_candidate_snapshot(conn: RepositoryConn, c: CandidateSnapshot) -> None:
    await conn.execute(
        "INSERT INTO candidate_snapshots (candidate_id, content_hash, symbol, theme_version_id, as_of, "
        "knowledge_cutoff, expires_at, quality_passed, data_mode, created_at, payload) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11::jsonb) ON CONFLICT (candidate_id) DO NOTHING",
        c.candidate_id, c.content_hash, c.symbol, c.theme_version_id, c.as_of, c.knowledge_cutoff,
        c.expires_at, c.quality_passed, c.data_mode, c.created_at, json.dumps(c.model_dump(mode="json")),
    )


async def load_theme_version(conn: RepositoryConn, theme_version_id: str) -> ThemeVersion:
    row = await conn.fetchrow("SELECT payload FROM theme_versions WHERE theme_version_id = $1", theme_version_id)
    if row is None:
        raise LookupError(theme_version_id)
    return ThemeVersion.model_validate(_payload(row))


async def load_candidate_snapshot(conn: RepositoryConn, candidate_id: str) -> CandidateSnapshot:
    row = await conn.fetchrow("SELECT payload FROM candidate_snapshots WHERE candidate_id = $1", candidate_id)
    if row is None:
        raise LookupError(candidate_id)
    return CandidateSnapshot.model_validate(_payload(row))
