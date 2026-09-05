"""asx decision — Stage 4: one governed paper case, end to end.

`build` composes the chain for an approved thesis (optionally with a Stage 3
candidate for the same symbol), challenges it with the live book, renders
it ONCE, prints that render (the CLI delivery), optionally emails the same
string (the email delivery), and — with `--persist` — saves the case to the
0048 tables and one `brief_runs` receipt row per channel. `positive-control`
reports which candidate D-5 would pick. `dispose` prints James's Disposition
contract (persistence is the 0052 migration's item).

Personal-use firewall (s766B): every command that touches holdings, cash or
the profile calls `_require_personal_use()` first, and the loaders check
again. Never `signals`; never a Model A import.
"""
from __future__ import annotations

import asyncio
import json
from datetime import date, datetime

import typer

from asxos.cli._common import _require_personal_use, console
from asxos.db import acquire, close_pool, init_pool
from asxos.domain.decision_engine import repository
from asxos.domain.decision_engine.builder import ChallengeContext, build_decision_case
from asxos.domain.decision_engine.challenge import DispositionLog
from asxos.domain.decision_engine.delivery import (
    disposition_for,
    now_utc,
    paper_intent_for,
    persist_receipt,
    receipt_for,
    render_decision_case,
    render_sha256,
    send_decision_case,
)
from asxos.domain.decision_engine.portfolio_state import (
    load_annualised_vol,
    load_peer_vols,
    load_portfolio_state,
    load_sizing_policy,
    select_positive_control,
)
from asxos.domain.themes.candidates.builder import build_candidate_snapshot, build_theme_version

decision_app = typer.Typer(help="Governed decision cases (Stage 4).", no_args_is_help=True, add_completion=False)


def _cutoff(as_of: str) -> datetime:
    from datetime import UTC, time

    return datetime.combine(date.fromisoformat(as_of), time(23, 59, 59), tzinfo=UTC)


@decision_app.command("build")
def decision_build(
    thesis_id: int = typer.Option(..., "--thesis-id"),
    as_of: str = typer.Option(..., "--as-of", help="Knowledge cutoff YYYY-MM-DD"),
    theme: str | None = typer.Option(None, "--theme", help="theme_code; builds a CandidateSnapshot for the thesis symbol"),
    context: bool = typer.Option(True, "--context/--no-context", help="Challenge against the live book (default)"),
    persist: bool = typer.Option(False, "--persist/--dry-run", help="Save the case (0048) and receipts (brief_runs)"),
    send: bool = typer.Option(False, "--send", help="Email the identical render via Resend"),
) -> None:
    """Build, challenge, render and (optionally) deliver one governed case."""
    _require_personal_use()
    asyncio.run(_build(thesis_id, as_of, theme, context, persist, send))


async def _build(thesis_id: int, as_of: str, theme: str | None, with_context: bool, persist: bool, send: bool) -> None:
    cutoff = _cutoff(as_of)
    day = cutoff.date()
    await init_pool()
    try:
        async with acquire() as conn:
            from asxos.domain.theses.service import get_thesis

            thesis = await get_thesis(conn, thesis_id)
            if thesis is None:
                raise typer.BadParameter(f"no thesis {thesis_id}")
            candidate = None
            if theme:
                tv = await build_theme_version(conn, theme_code=theme, as_of=day)
                candidate = await build_candidate_snapshot(conn, symbol=thesis.symbol, theme=tv, as_of=day)
            ctx = None
            if with_context:
                state = await load_portfolio_state(conn, day)
                policy = await load_sizing_policy(conn)
                vol = await load_annualised_vol(conn, thesis.symbol, day)
                peers = await load_peer_vols(conn, state, day)
                ctx = ChallengeContext(
                    portfolio_state=state, sizing=policy, proposed_annualised_vol=vol, peers=peers,
                    dispositions=DispositionLog(),
                )
            case = await build_decision_case(conn, cutoff=cutoff, thesis_id=thesis_id, candidate=candidate, context=ctx)
            html = render_decision_case(case, evaluated_at=cutoff)
            receipts = [receipt_for(case, html, channel="cli", delivered_at=now_utc())]
            if send:
                message_id = send_decision_case(html, case=case)
                receipts.append(receipt_for(case, html, channel="email", delivered_at=now_utc(), resend_message_id=message_id))
            if persist:
                await repository.save(case, conn=conn)
                for r in receipts:
                    await persist_receipt(conn, r, html, as_of=day)
    finally:
        await close_pool()
    typer.echo(html)
    console.print(
        f"[dim]case={case.case_id} packet={case.decision.decision_packet_id} state={case.decision.recommendation_state} "
        f"challenge={case.challenge.outcome} render_sha256={render_sha256(html)} "
        f"receipts={[r.channel for r in receipts]} persisted={persist}[/dim]"
    )


@decision_app.command("positive-control")
def decision_positive_control(as_of: str = typer.Option(..., "--as-of")) -> None:
    """Which CandidateSnapshot D-5 would pick as the Stage 4 positive control."""
    _require_personal_use()
    asyncio.run(_positive_control(date.fromisoformat(as_of)))


async def _positive_control(day: date) -> None:
    await init_pool()
    try:
        async with acquire() as conn:
            pick = await select_positive_control(conn, day, now=day)
    finally:
        await close_pool()
    if pick is None:
        console.print(
            "[yellow]No eligible positive control: no quality-passed CandidateSnapshot for an ordinary ASX equity "
            "outside the negative controls (CBA/HUBS/ESS). A second governed theme member is needed.[/yellow]"
        )
        raise typer.Exit(code=3)
    console.print(json.dumps(pick.model_dump(mode="json"), indent=2, sort_keys=True))


@decision_app.command("dispose")
def decision_dispose(
    packet_id: str = typer.Option(..., "--packet-id"),
    verdict: str = typer.Option(..., "--verdict", help="accept | request_revision | reject | defer"),
    note: str = typer.Option(..., "--note"),
) -> None:
    """Print James's Disposition contract for a persisted packet (dry-run until 0052 persists it)."""
    _require_personal_use()
    asyncio.run(_dispose(packet_id, verdict, note))


async def _dispose(packet_id: str, verdict: str, note: str) -> None:
    await init_pool()
    try:
        async with acquire() as conn:
            case = await repository.load_case(packet_id, conn=conn)
    finally:
        await close_pool()
    disposition = disposition_for(case, verdict=verdict, note=note, recorded_at=now_utc())  # type: ignore[arg-type]
    intent = paper_intent_for(case, disposition, created_at=now_utc())
    console.print(json.dumps(disposition.model_dump(mode="json"), indent=2, sort_keys=True))
    console.print(f"[dim]paper_intent={'none (non-action state)' if intent is None else intent.intent_id} persisted=False (0052)[/dim]")
