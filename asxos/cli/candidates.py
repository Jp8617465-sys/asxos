"""asx candidates — Stage 3: build a ThemeVersion + CandidateSnapshot reproducibly.

Read-only against themes/theme_holdings/macro_theses/rs_factor_scores/
rs_security_master/prices; writes only the append-only 0051 tables when
`--persist`. Not personal-use gated: no holdings, no tax, no theses, never
`signals`. Output is evidence, not a recommendation — the contracts refuse to
carry one.
"""
from __future__ import annotations

import asyncio
import json
from datetime import date

import typer

from asxos.cli._common import console
from asxos.db import acquire, close_pool, init_pool
from asxos.domain.themes.candidates.builder import build_candidate_snapshot, build_theme_version
from asxos.domain.themes.candidates.repository import save_candidate_snapshot, save_theme_version

candidates_app = typer.Typer(
    help="Theme + candidate engine (Stage 3): reproducible evidence artifacts.",
    no_args_is_help=True,
    add_completion=False,
)


@candidates_app.command("build")
def candidates_build(
    theme: str = typer.Option(..., "--theme", help="themes.theme_code, e.g. big-4-banks"),
    symbol: str = typer.Option(..., "--symbol", help="A member of the theme, e.g. CBA.AU"),
    as_of: str = typer.Option(..., "--as-of", help="Knowledge cutoff YYYY-MM-DD"),
    twice: bool = typer.Option(True, "--twice/--once", help="Build twice; refuse if hashes differ."),
    persist: bool = typer.Option(False, "--persist/--dry-run", help="Write to theme_versions / candidate_snapshots."),
    fixture: bool = typer.Option(
        False,
        "--fixture/--no-fixture",
        help="Mark the rows as F-E2E fixture rows with an f-e2e- id prefix. "
        "data_mode stays 'real' — the data is live, only the purpose is fixture.",
    ),
) -> None:
    """Build one ThemeVersion and one CandidateSnapshot from exact evidence."""
    asyncio.run(_build(theme, symbol, date.fromisoformat(as_of), twice, persist, fixture))


FIXTURE_ID_PREFIX = "f-e2e-"


async def _build(
    theme_code: str, symbol: str, as_of: date, twice: bool, persist: bool, fixture: bool = False
) -> None:
    # The prefix is part of the id, and the id is inside the content hash, so a
    # fixture row is a different identity from a production row built the same
    # day — not the same row wearing a label.
    prefix = FIXTURE_ID_PREFIX if fixture else ""
    await init_pool()
    try:
        async with acquire() as conn:
            tv = await build_theme_version(conn, theme_code=theme_code, as_of=as_of, id_prefix=prefix)
            cand = await build_candidate_snapshot(conn, symbol=symbol, theme=tv, as_of=as_of, id_prefix=prefix)
            if twice:
                tv2 = await build_theme_version(conn, theme_code=theme_code, as_of=as_of, id_prefix=prefix)
                cand2 = await build_candidate_snapshot(conn, symbol=symbol, theme=tv2, as_of=as_of, id_prefix=prefix)
                if (tv2.content_hash, cand2.content_hash) != (tv.content_hash, cand.content_hash):
                    raise typer.Exit(code=2)
            if persist:
                await save_theme_version(conn, tv)
                await save_candidate_snapshot(conn, cand)
    finally:
        await close_pool()

    console.print(json.dumps(tv.model_dump(mode="json"), indent=2, sort_keys=True))
    console.print(json.dumps(cand.model_dump(mode="json"), indent=2, sort_keys=True))
    console.print(
        f"[dim]theme_version={tv.theme_version_id} sha256={tv.content_hash} "
        f"candidate={cand.candidate_id} sha256={cand.content_hash} "
        f"quality_passed={cand.quality_passed} reproducible={'yes' if twice else 'not checked'} "
        f"persisted={persist} fixture={fixture}[/dim]"
    )
