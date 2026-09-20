"""asx evidence — record and read citations against an existing thesis.

Commands:
  asx evidence log SYMBOL   — record one citation, optionally with a stance
  asx evidence list SYMBOL  — show the citations recorded against a thesis

WHY THIS COMMAND EXISTS. Before it, the only writer of `thesis_evidence` was a
helper reachable solely from `asx thesis open` — a citation could be recorded at
the moment a thesis was created and never again. Measured 2026-09-20 that showed:
all 26 rows in the corpus were `system_screen` output, two per thesis, and not one
recorded a judgement James made. Human research had nowhere to land, so the
evidence chain recorded what the screen noticed rather than what anyone concluded.

WHAT IT IS NOT. Logging a citation is not revising a thesis and not revisiting
one. No `thesis_revisions` row is written and no clock moves — `revisit_due_at`
stays where it was. Use `asx thesis review` to record that you actually revisited.
"""
from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import typer
from rich.markup import escape
from rich.table import Table

from asxos.cli._common import _require_personal_use, console
from asxos.db import acquire, close_pool, init_pool
from asxos.domain.theses import service as svc

evidence_app = typer.Typer(
    help="Record and read thesis evidence citations.",
    no_args_is_help=True,
    add_completion=False,
)


def _parse_as_of(value: str | None) -> datetime | None:
    """Parse --as-of into an aware UTC datetime, or None.

    A date alone means midnight UTC on that date. A naive timestamp is REFUSED
    rather than assumed to be UTC: `source_as_of` is the point in time the cited
    source speaks for, and silently inventing a timezone for it would make the
    citation claim precision nobody supplied.
    """
    if value is None:
        return None
    raw = value.strip()
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise typer.BadParameter(
            f"Invalid --as-of {value!r}. Use YYYY-MM-DD or an ISO-8601 timestamp "
            "with an offset, e.g. 2026-09-20T04:00:00+00:00."
        ) from exc
    if parsed.tzinfo is None:
        if len(raw) == 10:  # a bare YYYY-MM-DD
            return parsed.replace(tzinfo=UTC)
        raise typer.BadParameter(
            f"--as-of {value!r} has no timezone. Give an offset (…+00:00) or a bare date; "
            "a naive timestamp would have this citation claim a precision you did not supply."
        )
    return parsed


def _load_snapshot(
    snapshot: str | None, snapshot_file: str | None, quote: str | None
) -> dict[str, Any] | None:
    """Build `snapshot_data` from exactly one of --snapshot / --snapshot-file / --quote.

    The snapshot is what the `snapshot_hash` is taken over, so it is the part of
    the citation that is tamper-evident. `--quote` is the human path: the passage
    you actually read, stored verbatim under one key.
    """
    given = [x for x in (snapshot, snapshot_file, quote) if x is not None]
    if not given:
        return None
    if len(given) > 1:
        raise typer.BadParameter(
            "Give at most one of --snapshot, --snapshot-file or --quote — they all "
            "fill the same field, and two would silently discard one."
        )
    if quote is not None:
        if not quote.strip():
            raise typer.BadParameter("--quote is empty")
        return {"quote": quote}
    raw = Path(snapshot_file).read_text(encoding="utf-8") if snapshot_file else snapshot
    assert raw is not None  # one of the three was given, and quote was handled above
    try:
        loaded = json.loads(raw)
    except json.JSONDecodeError as exc:
        where = f"--snapshot-file {snapshot_file}" if snapshot_file else "--snapshot"
        raise typer.BadParameter(f"{where} is not valid JSON: {exc}") from exc
    if not isinstance(loaded, dict):
        raise typer.BadParameter(
            f"snapshot must be a JSON object, got {type(loaded).__name__} — the hash is "
            "taken over an object's sorted keys."
        )
    return loaded


async def _run(coro: Any) -> Any:
    await init_pool()
    try:
        return await coro()
    finally:
        await close_pool()


@evidence_app.command("log")
def evidence_log(
    symbol: str = typer.Argument(..., help="Symbol, e.g. CBA.AU (most recent thesis)"),
    claim: str = typer.Option(..., "--claim", help="What this citation asserts, in one sentence"),
    tier: str = typer.Option(
        "verified", "--tier", help="verified | inferred | speculative"
    ),
    stance: str | None = typer.Option(
        None,
        "--stance",
        help=(
            "supports | contradicts | neutral. OMIT it if you did not judge — "
            "omitted means nobody judged, which is not the same as 'neutral'."
        ),
    ),
    source_table: str | None = typer.Option(
        None, "--source-table", help="The table this was read from (db_query citations)"
    ),
    source_url: str | None = typer.Option(
        None, "--source-url", help="The page this was read from (external_url citations)"
    ),
    as_of: str | None = typer.Option(
        None, "--as-of", help="The point in time the source speaks for (YYYY-MM-DD or ISO-8601)"
    ),
    snapshot: str | None = typer.Option(
        None, "--snapshot", help="Snapshot as inline JSON (the hashed payload)"
    ),
    snapshot_file: str | None = typer.Option(
        None, "--snapshot-file", help="Snapshot as a path to a JSON file"
    ),
    quote: str | None = typer.Option(
        None, "--quote", help="The passage you read, stored verbatim as the snapshot"
    ),
    source_agent: str = typer.Option(
        "human", "--source-agent", help="Who recorded this (default: human)"
    ),
    thesis_id: int | None = typer.Option(
        None, "--thesis-id", help="Target this exact thesis instead of the symbol's most recent"
    ),
) -> None:
    """Record one citation against an existing thesis, without re-opening it.

    A non-speculative citation must carry a snapshot (one of --snapshot,
    --snapshot-file or --quote); only a speculative one may omit it. The snapshot
    is hashed with sha256 over its canonical JSON, so the row is tamper-evident.

    This writes no revision and moves no clock: `revisit_due_at` is untouched.
    """
    _require_personal_use()
    if source_url is not None and source_table is not None:
        raise typer.BadParameter(
            "Give --source-url or --source-table, not both — a citation is read from one place."
        )
    source_type = "external_url" if source_url is not None else "db_query"
    snapshot_data = _load_snapshot(snapshot, snapshot_file, quote)
    asyncio.run(
        _run(
            lambda: _log_evidence(
                symbol=symbol,
                thesis_id=thesis_id,
                claim=claim,
                tier=tier,
                stance=stance,
                source_type=source_type,
                source_table=source_table,
                source_url=source_url,
                source_as_of=_parse_as_of(as_of),
                snapshot_data=snapshot_data,
                source_agent=source_agent,
            )
        )
    )


async def _resolve_thesis_id(conn: Any, symbol: str, thesis_id: int | None) -> tuple[int, str]:
    if thesis_id is not None:
        t = await svc.get_thesis(conn, thesis_id)
        if t is None:
            raise ValueError(f"Thesis {thesis_id} not found")
        return t.thesis_id, t.symbol
    t = await svc.get_thesis_by_symbol(conn, symbol.upper())
    if t is None:
        raise ValueError(
            f"No thesis found for {symbol.upper()}. Open one with `asx thesis open` first — "
            "evidence is cited against a thesis, not against a symbol."
        )
    return t.thesis_id, t.symbol


async def _log_evidence(
    *,
    symbol: str,
    thesis_id: int | None,
    claim: str,
    tier: str,
    stance: str | None,
    source_type: str,
    source_table: str | None,
    source_url: str | None,
    source_as_of: datetime | None,
    snapshot_data: dict[str, Any] | None,
    source_agent: str,
) -> None:
    try:
        async with acquire() as conn:
            resolved_id, resolved_symbol = await _resolve_thesis_id(conn, symbol, thesis_id)
            evidence_id = await svc.log_evidence(
                conn,
                thesis_id=resolved_id,
                claim_text=claim,
                tier=tier,
                stance=stance,
                snapshot_data=snapshot_data,
                source_agent=source_agent,
                source_type=source_type,
                source_table=source_table,
                source_url=source_url,
                source_as_of=source_as_of,
            )
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {escape(str(exc))}")
        raise typer.Exit(1) from exc
    mark = stance if stance else "no stance recorded"
    console.print(
        f"[green]✓[/green] Evidence #{evidence_id} cited against "
        f"#{resolved_id} ({escape(resolved_symbol)}) — {escape(tier)}, {escape(mark)}"
    )
    console.print("[dim]No revision written; revisit_due_at unchanged.[/dim]")


@evidence_app.command("list")
def evidence_list(
    symbol: str = typer.Argument(..., help="Symbol, e.g. CBA.AU (most recent thesis)"),
    thesis_id: int | None = typer.Option(
        None, "--thesis-id", help="Target this exact thesis instead of the symbol's most recent"
    ),
    include_superseded: bool = typer.Option(
        False, "--include-superseded", help="Also show citations that have been superseded"
    ),
) -> None:
    """Show the citations recorded against a thesis, newest first."""
    _require_personal_use()
    asyncio.run(
        _run(
            lambda: _list_evidence(
                symbol=symbol, thesis_id=thesis_id, include_superseded=include_superseded
            )
        )
    )


async def _list_evidence(
    *, symbol: str, thesis_id: int | None, include_superseded: bool
) -> None:
    try:
        async with acquire() as conn:
            resolved_id, resolved_symbol = await _resolve_thesis_id(conn, symbol, thesis_id)
            rows = await svc.list_thesis_evidence(
                conn, resolved_id, include_superseded=include_superseded
            )
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {escape(str(exc))}")
        raise typer.Exit(1) from exc

    if not rows:
        console.print(f"No evidence cited against #{resolved_id} ({escape(resolved_symbol)}).")
        return

    table = Table(title=f"Evidence — #{resolved_id} {resolved_symbol}")
    for col in ("id", "cited", "author", "tier", "stance", "claim", "source"):
        table.add_column(col)
    for r in rows:
        # "—" and not "neutral": an unmarked row is one nobody judged, and
        # rendering it as a judgement would misreport the corpus on sight.
        stance = r["stance"] or "—"
        source = r["source_url"] or r["source_table"] or r["source_type"]
        table.add_row(
            str(r["evidence_id"]),
            r["cited_at"].date().isoformat(),
            r["source_agent"],
            r["tier"],
            stance,
            r["claim_text"][:60],
            str(source),
        )
    console.print(table)

    marked = sum(1 for r in rows if r["stance"])
    against = sum(1 for r in rows if r["stance"] == "contradicts")
    console.print(
        f"[dim]{len(rows)} citation(s); {marked} carry a stance, {against} contradict. "
        f"An unmarked row means nobody judged it.[/dim]"
    )
