"""asx agent-run — logging agent proposals into agent_runs/agent_evidence.

Commands:
  asx agent-run log AGENT_NAME — validate + persist an agent's evidence and
                                  proposal (Phase 2b's new mechanism — the
                                  write side of agent_runs that Phase 1 never
                                  built). Prints the new run_id.

Not intended for interactive hand-typing of large --proposal-json/
--evidence-json blobs — this is the target of /discover-macro's own
shell-out after parsing an agent's structured output block.
"""
from __future__ import annotations

import asyncio

import typer

from asxos.cli._common import _require_personal_use, console
from asxos.db import acquire, close_pool, init_pool
from asxos.domain.governance import agent_run_service as svc

agent_run_app = typer.Typer(
    help="Agent-run logging.",
    no_args_is_help=True,
    add_completion=False,
)


@agent_run_app.command("log")
def agent_run_log(
    agent_name: str = typer.Argument(..., help="Agent slug, e.g. macro-economist"),
    object_type: str = typer.Option(
        "", "--object-type", help="macro_thesis|theme|theme_holding (omit for an evidence-only run)"
    ),
    subject: str = typer.Option("", "--subject", help="Symbol/theme_code this run concerns, if any"),
    summary: str = typer.Option(..., "--summary", help="One-line summary of what the agent found"),
    proposal_json: str = typer.Option(
        "", "--proposal-json", help="Raw proposal JSON (required iff --object-type is given)"
    ),
    evidence_json: str = typer.Option(
        "", "--evidence-json", help="Raw JSON array of evidence claims"
    ),
) -> None:
    """Validate an agent's proposal + evidence and persist as agent_runs/
    agent_evidence rows. Prints the new run_id on success."""
    _require_personal_use()
    asyncio.run(
        _log_agent_run(
            agent_name,
            object_type=object_type.strip() or None,
            subject=subject.strip() or None,
            summary=summary,
            proposal_json=proposal_json.strip() or None,
            evidence_json=evidence_json.strip() or None,
        )
    )


async def _log_agent_run(
    agent_name: str,
    *,
    object_type: str | None,
    subject: str | None,
    summary: str,
    proposal_json: str | None,
    evidence_json: str | None,
) -> None:
    await init_pool()
    try:
        async with acquire() as conn:
            run_id = await svc.log_agent_run(
                conn,
                agent_name,
                subject=subject,
                summary=summary,
                object_type=object_type,
                proposal_raw=proposal_json,
                evidence_raw=evidence_json,
            )
        console.print(f"[green]✓[/green] Logged agent run #{run_id} ({agent_name})")
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc
    finally:
        await close_pool()
