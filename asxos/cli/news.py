from __future__ import annotations

import asyncio

import typer

from asxos.cli._common import _require_personal_use, console
from asxos.db import acquire, close_pool, init_pool

news_app = typer.Typer(
    help="News ingestion gates (M14). Requires ASXOS_PERSONAL_USE=1.",
    no_args_is_help=True,
    add_completion=False,
)


@news_app.command("signoff")
def news_signoff(
    note: str = typer.Option("", "--note", help="Optional free-text note to record"),
    force: bool = typer.Option(False, "--force", help="Skip the prerequisite check"),
) -> None:
    """Record M14a sign-off and print the Render command to flip ASXOS_NEWS_BRIEF_ENABLED=1.

    Requires ≥1 successful ingest_news job run within the last 7 days, unless
    --force is passed.  Inserts a decisions journal entry tagged [m14_news_signoff].
    """
    _require_personal_use()
    asyncio.run(_run_news_signoff(note=note, force=force))


async def _run_news_signoff(*, note: str, force: bool) -> None:
    from datetime import date as _date

    today = _date.today()

    await init_pool()
    try:
        async with acquire() as conn:
            if not force:
                rows = await conn.fetch(
                    """
                    SELECT 1 FROM job_runs
                    WHERE job_name = 'ingest_news'
                      AND status = 'success'
                      AND as_of >= $1 - INTERVAL '7 days'
                    LIMIT 1
                    """,
                    today,
                )
                if not rows:
                    console.print(
                        "[red]No successful ingest_news run in the last 7 days.[/red] "
                        "Run the job at least once first, or pass [bold]--force[/bold] to override."
                    )
                    raise typer.Exit(code=1)

            rationale = (
                "[m14_news_signoff] M14a news ingestion gate passed. "
                f"Signed off {today.isoformat()}."
            )
            if note:
                rationale += f" Note: {note}"

            row = await conn.fetchrow(
                """
                INSERT INTO decisions (symbol, decision_date, action, rationale)
                VALUES (NULL, $1, 'NOTE', $2)
                RETURNING id
                """,
                today,
                rationale,
            )
            decisions_id = row["id"]
    finally:
        await close_pool()

    console.print(f"[green]✓[/green] News sign-off recorded (decisions.id={decisions_id}).")
    console.print()
    console.print("[bold]Next step — flip the brief flag via the Render REST API:[/bold]")
    console.print(
        "  curl -X PUT -H \"Authorization: Bearer $RENDER_API_KEY\" \\\n"
        "       -H \"Content-Type: application/json\" -d '{\"value\":\"1\"}' \\\n"
        "       https://api.render.com/v1/services/crn-d883biq8qa3s73eud08g/env-vars/ASXOS_NEWS_BRIEF_ENABLED"
    )
    console.print()
    console.print(
        "[dim]The next brief will include the 'Market news on holdings' section "
        "(gated by a fresh ingest_news run within 24h).[/dim]"
    )
