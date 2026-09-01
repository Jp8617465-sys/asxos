from __future__ import annotations

import asyncio
from datetime import date

import typer

from asxos import clock
from asxos.cli._common import _require_personal_use, console
from asxos.db import acquire, close_pool, init_pool


def brief(
    as_of: str = typer.Option(None, "--as-of", help="Brief date YYYY-MM-DD; defaults to today"),
    send: bool = typer.Option(False, "--send", help="Dispatch via Resend (default: stdout-only)"),
    detail: bool = typer.Option(
        False, "--detail", help="Print the full-tables detail page (email stays short)"
    ),
) -> None:
    """Render the morning brief from gold; pass --send to dispatch via Resend."""
    _require_personal_use()
    target = date.fromisoformat(as_of) if as_of else clock.today()
    asyncio.run(_run_brief(target, send=send, detail=detail))


async def _run_brief(target: date, *, send: bool, detail: bool) -> None:
    from asxos.brief.compose import render_detail_html, render_html
    from asxos.brief.gold import hydrate

    await init_pool()
    try:
        async with acquire() as conn:
            data = await hydrate(conn, target)
        short = render_html(data)
        html = render_detail_html(data) if detail else short
    finally:
        await close_pool()

    typer.echo(html)

    if send:
        from asxos.brief.email import send_brief

        result = send_brief(short, as_of=target)
        console.print(
            f"[green]Sent to {result.to}[/green] · subject='{result.subject}' · id={result.message_id}"
        )
