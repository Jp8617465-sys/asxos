"""asx decision — Stage 4: one governed paper case, end to end.

`build` composes the chain for an approved thesis (optionally with a Stage 3
candidate for the same symbol), challenges it with the live book, renders
it ONCE, prints that render (the CLI delivery), optionally emails the same
string (the email delivery), and — with `--persist` — saves the case to the
0048 tables and one `delivery_receipts` row per channel (0052). `positive-control`
reports which candidate D-5 would pick. `dispose` prints James's Disposition
contract (persistence is the 0052 migration's item).

Personal-use firewall (s766B): every command that touches holdings, cash or
the profile calls `_require_personal_use()` first, and the loaders check
again. Never `signals`; never a Model A import.
"""
from __future__ import annotations

import asyncio
import json
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import typer

from asxos.cli._common import _require_personal_use, console
from asxos.db import acquire, close_pool, init_pool
from asxos.domain.decision_engine import repository
from asxos.domain.decision_engine.builder import ChallengeContext, build_decision_case
from asxos.domain.decision_engine.challenge import DispositionLog
from asxos.domain.decision_engine.challenge.rules import PortfolioState
from asxos.domain.decision_engine.delivery import (
    DeliveryReceipt,
    disposition_for,
    load_dispositions,
    now_utc,
    paper_intent_for,
    persist_disposition,
    persist_receipt,
    receipt_for,
    render_decision_case,
    render_sha256,
    send_decision_case,
)
from asxos.domain.decision_engine.outcomes import (
    ThesisOutcome,
    due_horizons,
    load_outcomes,
    materialise_t0,
    observe,
    save_outcome,
)
from asxos.domain.decision_engine.paper_book import load_paper_book_state
from asxos.domain.decision_engine.portfolio_state import (
    SQL_CLOSE,
    load_annualised_vol,
    load_peer_vols,
    load_portfolio_state,
    load_sizing_policy,
    select_positive_control,
)
from asxos.domain.decision_engine.renderer import render_broker_report
from asxos.domain.decision_engine.types import DecisionCase
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
    paper_book: str = typer.Option(
        "", "--paper-book", help="paper_book_snapshots.snapshot_id; challenge against the paper book (C1/D15) instead of the live book"
    ),
    context: bool = typer.Option(True, "--context/--no-context", help="Challenge against the live book (default)"),
    persist: bool = typer.Option(False, "--persist/--dry-run", help="Save the case (0048) and receipts (0052)"),
    send: bool = typer.Option(False, "--send", help="Email the identical render via Resend"),
) -> None:
    """Build, challenge, render and (optionally) deliver one governed case."""
    _require_personal_use()
    asyncio.run(_build(thesis_id, as_of, theme, context, persist, send, paper_book))


async def _book_state(conn: Any, day: date, paper_book: str) -> PortfolioState:
    """Load exactly one book.

    One or the other, never a blend: the paper book is a separate table with a
    separate loader precisely so a case cannot be challenged against paper cash
    and live positions at the same time.
    """
    if paper_book:
        return await load_paper_book_state(conn, paper_book)
    return await load_portfolio_state(conn, day)


async def _build(
    thesis_id: int, as_of: str, theme: str | None, with_context: bool, persist: bool,
    send: bool, paper_book: str = "",
) -> None:
    if send and not persist:
        raise typer.BadParameter("--send requires --persist so the attempt is recoverable")
    if paper_book and not with_context:
        raise typer.BadParameter("--paper-book needs --context; without it no book is read at all")
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
                state = await _book_state(conn, day, paper_book)
                policy = await load_sizing_policy(conn, day)
                vol = await load_annualised_vol(conn, thesis.symbol, day)
                peers = await load_peer_vols(conn, state, day)
                ctx = ChallengeContext(
                    portfolio_state=state, sizing=policy, proposed_annualised_vol=vol, peers=peers,
                    dispositions=DispositionLog(),
                )
            case = await build_decision_case(conn, cutoff=cutoff, thesis_id=thesis_id, candidate=candidate, context=ctx)
            delivery_at = now_utc()
            html = render_decision_case(case, evaluated_at=delivery_at)
            receipts = [receipt_for(case, html, channel="cli", delivered_at=delivery_at)]
            if persist:
                await repository.save(case, conn=conn)
                await persist_receipt(conn, receipts[0], html)
            if send:
                receipts.extend(await _send_with_receipts(conn, case, html))
    finally:
        await close_pool()
    typer.echo(html)
    console.print(
        f"[dim]case={case.case_id} packet={case.decision.decision_packet_id} state={case.decision.recommendation_state} "
        f"challenge={case.challenge.outcome} book={paper_book or 'live'} render_sha256={render_sha256(html)} "
        f"receipts={[f'{r.channel}:{r.delivery_status}' for r in receipts]} persisted={persist}[/dim]"
    )


async def _send_with_receipts(
    conn: object, case: DecisionCase, html: str
) -> tuple[DeliveryReceipt, DeliveryReceipt]:
    """Persist the attempt before the provider call, then its terminal state."""
    pending = receipt_for(
        case,
        html,
        channel="email",
        delivered_at=now_utc(),
        delivery_status="pending",
    )
    await persist_receipt(conn, pending, html)  # type: ignore[arg-type]
    try:
        message_id = send_decision_case(html, case=case)
    except Exception:
        failed = receipt_for(
            case,
            html,
            channel="email",
            delivered_at=now_utc(),
            delivery_status="failed",
        )
        await persist_receipt(conn, failed, html)  # type: ignore[arg-type]
        raise
    sent = receipt_for(
        case,
        html,
        channel="email",
        delivered_at=now_utc(),
        delivery_status="sent",
        resend_message_id=message_id,
    )
    await persist_receipt(conn, sent, html)  # type: ignore[arg-type]
    return pending, sent


@decision_app.command("record-t0")
def decision_record_t0(
    packet_id: str = typer.Option(..., "--packet-id"),
    persist: bool = typer.Option(False, "--persist/--dry-run", help="Write thesis_outcomes rows (0052)"),
) -> None:
    """Record what was known and claimed at t0, and schedule the 21/63/126-session horizons."""
    _require_personal_use()
    asyncio.run(_record_t0(packet_id, persist))


async def _record_t0(packet_id: str, persist: bool) -> None:
    await init_pool()
    try:
        async with acquire() as conn:
            case = await repository.load_case(packet_id, conn=conn)
            rows = materialise_t0(case)
            if persist:
                for row in rows:
                    await save_outcome(conn, row)
            stored = len(await load_outcomes(conn, packet_id))
    finally:
        await close_pool()
    for row in rows:
        console.print(
            f"[dim]{row.outcome_id} horizon={row.horizon_trading_days}d due={row.due_at.isoformat()} "
            f"state={row.observation_state}[/dim]"
        )
    console.print(
        f"[dim]t0 claim: state={rows[0].claim.recommendation_state} challenge={rows[0].claim.challenge_outcome} "
        f"reference_price={rows[0].claim.reference_price} blocking={rows[0].claim.blocking_finding_count} "
        f"persisted={persist} rows_on_packet={stored}[/dim]"
    )
    console.print(
        "[yellow]One observation is not an alpha claim; the Stage 5 gate needs a complete "
        "episode (21/63/126 sessions).[/yellow]"
    )


@decision_app.command("observe")
def decision_observe(
    packet_id: str = typer.Option(..., "--packet-id"),
    as_of: str = typer.Option(..., "--as-of", help="Observation date YYYY-MM-DD"),
    persist: bool = typer.Option(False, "--persist/--dry-run"),
) -> None:
    """Observe every horizon whose trading session has arrived."""
    _require_personal_use()
    asyncio.run(_observe(packet_id, date.fromisoformat(as_of), persist))


async def _observe(packet_id: str, day: date, persist: bool) -> None:
    await init_pool()
    try:
        async with acquire() as conn:
            rows = await load_outcomes(conn, packet_id)
            if not rows:
                raise typer.BadParameter(f"no thesis_outcomes rows for {packet_id}; run record-t0 first")
            cutoff = _cutoff(day.isoformat())
            due = due_horizons(rows, cutoff)
            observed = []
            for row in due:
                filled = await _observe_due_row(conn, row)
                if persist:
                    await save_outcome(conn, filled)
                observed.append(filled)
    finally:
        await close_pool()
    if not observed:
        console.print(f"[dim]nothing due at {day.isoformat()}; {len(rows)} row(s) on this packet[/dim]")
        return
    for row in observed:
        console.print(
            f"[dim]{row.outcome_id} return={row.security_return_pct} ({row.return_state}) "
            f"benchmark={row.benchmark_return_pct} ({row.benchmark_state}) excess={row.excess_return_pct} "
            f"persisted={persist}[/dim]"
        )


async def _observe_due_row(conn: object, row: ThesisOutcome) -> ThesisOutcome:
    """Observe one promised horizon at its due session, never the catch-up date."""
    due_day = row.due_at.date()
    price_row = await conn.fetchrow(SQL_CLOSE, row.symbol, due_day)  # type: ignore[attr-defined]
    price = Decimal(str(price_row["close"])) if price_row and price_row["close"] is not None else None
    observed_at = (
        date.fromisoformat(str(price_row["dt"]))
        if price_row and price_row.get("dt") is not None
        else due_day
    )
    # Benchmark levels are deliberately not passed: AXJOA.INDX is absent
    # from `prices`, so the comparison reports unavailable (F1), not proxied.
    return observe(row, observed_at=observed_at, observed_price=price)


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
    persist: bool = typer.Option(False, "--persist/--dry-run", help="Record into decision_dispositions"),
) -> None:
    """Record James's disposition of a persisted packet."""
    _require_personal_use()
    asyncio.run(_dispose(packet_id, verdict, note, persist))


async def _dispose(packet_id: str, verdict: str, note: str, persist: bool) -> None:
    await init_pool()
    try:
        async with acquire() as conn:
            case = await repository.load_case(packet_id, conn=conn)
            disposition = disposition_for(case, verdict=verdict, note=note, recorded_at=now_utc())  # type: ignore[arg-type]
            intent = paper_intent_for(case, disposition, created_at=now_utc())
            if persist:
                await persist_disposition(conn, disposition)
            recorded = len(await load_dispositions(conn, packet_id))
    finally:
        await close_pool()
    console.print(json.dumps(disposition.model_dump(mode="json"), indent=2, sort_keys=True))
    console.print(
        f"[dim]paper_intent={'none (non-action state)' if intent is None else intent.intent_id} "
        f"persisted={persist} dispositions_on_packet={recorded}[/dim]"
    )


def _evaluated_at(raw: str) -> datetime | None:
    """Parse the optional --evaluated-at, insisting it is explicit UTC.

    A naive or offset instant would silently change what the report says about
    expiry, so it is refused rather than coerced.
    """
    if not raw:
        return None
    parsed = datetime.fromisoformat(raw)
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise typer.BadParameter("--evaluated-at must be an explicit UTC instant, e.g. 2026-09-07T00:00:00+00:00")
    return parsed


def _artifact_path(out_dir: Path, packet_id: str, render_sha256: str) -> Path:
    """Content-addressed location for one rendered report.

    The digest is in the name, so the artifact is addressed by what it says
    rather than by when it was written: the same bytes always land on the same
    path, and a render that differs by one character cannot overwrite an
    earlier one.
    """
    return out_dir / packet_id / f"{render_sha256}.md"


@decision_app.command("report")
def decision_report(
    packet_id: str = typer.Option(..., "--packet-id", help="decision_packets.decision_packet_id"),
    out: str = typer.Option(
        ..., "--out", help="Directory for the content-addressed broker-report artifact"
    ),
    persist: bool = typer.Option(
        False, "--persist/--dry-run", help="Record one delivery_receipts row for the rendered bytes"
    ),
    evaluated_at: str = typer.Option(
        "",
        "--evaluated-at",
        help="ISO-8601 UTC instant to evaluate expiry against; omit for now. "
        "Supplying it makes the render byte-reproducible.",
    ),
) -> None:
    """Render a persisted decision packet as the canonical broker report.

    Reads only what was persisted: `load_case` reconstructs the five contracts
    from their `payload` columns and every one is re-validated on the way out,
    so a report can never show a number the stored chain does not carry.
    """
    _require_personal_use()
    asyncio.run(_report(packet_id, Path(out), persist, _evaluated_at(evaluated_at)))


async def _report(
    packet_id: str, out: Path, persist: bool, evaluated_at: datetime | None
) -> None:
    # Two instants with different jobs. `evaluated_at` decides what the report
    # SAYS (expiry, actionability) and is therefore what the bytes are a
    # function of; `delivered_at` records WHEN those bytes were handed over.
    # With no --evaluated-at they are the same instant, which is the behaviour
    # a receipt-only render had.
    delivered_at = now_utc()
    evaluated_at = evaluated_at or delivered_at
    await init_pool()
    try:
        async with acquire() as conn:
            case = await repository.load_case(packet_id, conn=conn)
            report = render_broker_report(case, evaluated_at=evaluated_at)
            receipt = receipt_for(case, report, channel="cli", delivered_at=delivered_at)
            if persist:
                await persist_receipt(conn, receipt, report)
    finally:
        await close_pool()
    artifact = _artifact_path(out, case.decision.decision_packet_id, receipt.render_sha256)
    artifact.parent.mkdir(parents=True, exist_ok=True)
    # Write-once by construction: the name IS the digest, so re-rendering the
    # same bytes rewrites the same path and differing bytes can never clobber.
    artifact.write_text(report, encoding="utf-8")
    console.print(
        f"[dim]packet={case.decision.decision_packet_id} "
        f"state={case.decision.recommendation_state} "
        f"written={artifact} bytes={receipt.render_bytes} "
        f"render_sha256={receipt.render_sha256} "
        f"receipt={receipt.receipt_id if persist else 'not persisted (--dry-run)'}[/dim]"
    )
