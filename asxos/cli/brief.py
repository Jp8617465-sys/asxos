from __future__ import annotations

import asyncio
from datetime import date

import typer

from asxos.cli._common import _require_personal_use, console
from asxos.db import close_pool, init_pool


def brief(
    as_of: str = typer.Option(None, "--as-of", help="Brief date YYYY-MM-DD; defaults to today"),
    send: bool = typer.Option(False, "--send", help="Dispatch via Resend (default: stdout-only)"),
) -> None:
    """Render the morning brief; pass --send to dispatch via Resend."""
    _require_personal_use()
    target = date.fromisoformat(as_of) if as_of else date.today()
    asyncio.run(_run_brief(target, send=send))


async def _run_brief(target: date, *, send: bool) -> None:
    from asxos.brief.compose import collect, render_html

    await init_pool()
    try:
        data = await collect(target)
        html = render_html(data)
    finally:
        await close_pool()

    typer.echo(html)

    if send:
        from asxos.brief.email import send_brief

        result = send_brief(html, as_of=target)
        console.print(
            f"[green]Sent to {result.to}[/green] · subject='{result.subject}' · id={result.message_id}"
        )
