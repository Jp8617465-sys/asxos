"""asx thesis — trade thesis management CLI.

Commands:
  asx thesis open SYMBOL   — open a new thesis (research or watching)
  asx thesis open SYMBOL --from-agent-run ID — create a draft from an agent
                             proposal (Phase 1: always fails, no ThesisProposal
                             schema exists yet — see domain/theses/schemas.py)
  asx thesis show SYMBOL   — detailed view of the most recent thesis for a symbol
  asx thesis list          — summary table of all (or filtered) theses
  asx thesis enter SYMBOL  — transition to active (capital deployed)
  asx thesis approve ID    — governance_status pending_review -> approved
  asx thesis reject ID     — governance_status draft/evidence_complete/
                             pending_review -> rejected
  asx thesis attest ID     — attestation placeholder <-> underwritten (0042)
  asx thesis condition add|resolve|list — invalidation condition management (0042)
  asx thesis revise SYMBOL — revise one field with an audit event
  asx thesis review SYMBOL — discipline event: reviewed, no change
  asx thesis hold SYMBOL   — alias for review
  asx thesis exit SYMBOL   — close the position
  asx thesis history SYMBOL — full revision log
  asx thesis add-section SYMBOL — add/replace a broker-report section (Phase C)
  asx thesis show SYMBOL --full-report — render the broker-report sections
"""
from __future__ import annotations

import asyncio
import re
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, cast

import typer
from pydantic import ValidationError as PydanticValidationError
from rich.markup import escape
from rich.table import Table

from asxos.cli._common import _require_personal_use, console
from asxos.db import acquire, close_pool, init_pool
from asxos.domain.theses import conditions as conditions_svc
from asxos.domain.theses import lint
from asxos.domain.theses import service as svc
from asxos.domain.theses.condition_parser import lint_echo
from asxos.domain.theses.schemas import REPORT_SECTION_KINDS, ReportFigure, ReportSectionKind
from asxos.domain.theses.types import REVISABLE_FIELDS, Thesis
from asxos.domain.underlyings import service as underlying_svc

thesis_app = typer.Typer(
    help="Trade thesis management.",
    no_args_is_help=True,
    add_completion=False,
)

# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

_TIMELINE_RE = re.compile(r"^(\d+)(m|d)$", re.IGNORECASE)


def _parse_timeline(value: str) -> int:
    """Parse '18m' → 540 days, '90d' → 90 days."""
    m = _TIMELINE_RE.match(value.strip())
    if not m:
        raise typer.BadParameter(
            f"Invalid timeline {value!r}. Use Nm (months) or Nd (days), e.g. '18m' or '90d'."
        )
    n = int(m.group(1))
    unit = m.group(2).lower()
    return n * 30 if unit == "m" else n


def _parse_entry(value: str) -> tuple[Decimal, Decimal]:
    """Parse '60-65' → (60, 65) or '62' → (62, 62)."""
    value = value.strip()
    if "-" in value:
        parts = value.split("-", 1)
        try:
            lo, hi = Decimal(parts[0].strip()), Decimal(parts[1].strip())
        except InvalidOperation as exc:
            raise typer.BadParameter(f"Invalid entry band {value!r}. Use 'lo-hi' or single price.") from exc
        if lo > hi:
            raise typer.BadParameter(f"entry_band_lower ({lo}) must be ≤ entry_band_upper ({hi})")
        return lo, hi
    try:
        p = Decimal(value)
        return p, p
    except InvalidOperation as exc:
        raise typer.BadParameter(f"Invalid entry price {value!r}.") from exc


def _parse_decimal(value: str, label: str) -> Decimal:
    try:
        return Decimal(value)
    except InvalidOperation as exc:
        raise typer.BadParameter(f"Invalid {label}: {value!r}") from exc


def _parse_condition_option(raw: str) -> dict[str, str]:
    """Parse a repeatable ``--condition`` value into the service's
    {"text", "trigger_semantics"} shape.

    Format: 'TEXT' (defaults to alert_review — the conservative authored
    intent) or an explicit 'hard_exit::TEXT' / 'alert_review::TEXT' prefix.
    """
    semantics = "alert_review"
    text = raw
    if "::" in raw:
        prefix, _, rest = raw.partition("::")
        prefix = prefix.strip()
        if prefix not in ("hard_exit", "alert_review"):
            raise typer.BadParameter(
                f"Invalid --condition prefix {prefix!r}. Use 'hard_exit::TEXT' "
                "or 'alert_review::TEXT' (or plain TEXT for alert_review)."
            )
        semantics = prefix
        text = rest
    text = text.strip()
    if not text:
        raise typer.BadParameter(f"Invalid --condition {raw!r}: text is empty")
    return {"text": text, "trigger_semantics": semantics}


def _print_ladder_lint(t: Thesis) -> None:
    """Echo ladder lint findings for a PLACEHOLDER thesis — visibly wrong, not
    blocked (0042 D4: the service hard-fails only for underwritten rows)."""
    if t.attestation == "underwritten":
        return
    findings = lint.lint_ladder(
        stop_price=t.stop_price,
        entry_band_lower=t.entry_band_lower,
        entry_band_upper=t.entry_band_upper,
        target_price=t.target_price,
    )
    for f in findings:
        console.print(f"[yellow]placeholder lint [{f.code}]:[/yellow] {escape(f.message)}")


def _parse_figure(raw: str) -> ReportFigure:
    """Parse a repeatable '--figure Label=Value' into a james_input ReportFigure.

    Phase C's first cut is human-authored only, so every figure this parser
    produces is provenance='james_input' — no evidence_citation_ids needed
    (James is the source). Value is a raw decimal (e.g. '0.99' for 99%, not
    '99%') — ReportFigure carries no unit, the Label should say what it means.
    """
    if "=" not in raw:
        raise typer.BadParameter(f"Invalid --figure {raw!r}. Use 'Label=Value'.")
    label, _, value_str = raw.partition("=")
    label = label.strip()
    if not label:
        raise typer.BadParameter(f"Invalid --figure {raw!r}: label is empty")
    try:
        value = Decimal(value_str.strip())
    except InvalidOperation as exc:
        raise typer.BadParameter(f"Invalid --figure {raw!r}: {value_str!r} is not a decimal") from exc
    try:
        return ReportFigure(label=label, value=value, provenance="james_input")
    except PydanticValidationError as exc:
        raise typer.BadParameter(f"Invalid --figure {raw!r}: {exc}") from exc


def _thesis_summary_row(t: Thesis) -> tuple[str, ...]:
    """Return (symbol, status, thesis_id, entry_band, stop, target, days_since, overdue)."""
    days_since = (date.today() - t.opened_at.date()).days
    overdue = date.today() > t.revisit_due_at.date()
    entry = (
        f"{t.entry_band_lower}–{t.entry_band_upper}"
        if t.entry_band_lower and t.entry_band_upper
        else "—"
    )
    return (
        t.symbol,
        t.status,
        str(t.thesis_id),
        entry,
        str(t.stop_price or "—"),
        str(t.target_price or "—"),
        f"{days_since}d",
        "[red]YES[/red]" if overdue else "[green]no[/green]",
    )


# ---------------------------------------------------------------------------
# Async runners
# ---------------------------------------------------------------------------

async def _run(coro):  # type: ignore[no-untyped-def]
    """Boot pool, run coro, close pool."""
    await init_pool()
    try:
        return await coro
    finally:
        await close_pool()



# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

@thesis_app.command("open")
def thesis_open(
    symbol: str = typer.Argument(..., help="Symbol, e.g. CBA.AU"),
    status: str = typer.Option("watching", "--status", help="research|watching"),
    thesis: str = typer.Option("", "--thesis", help="Thesis text (the 'why')"),
    entry: str = typer.Option("", "--entry", help="Entry band: '60-65' or single price"),
    stop: str = typer.Option("", "--stop", help="Stop price"),
    target: str = typer.Option("", "--target", help="Target price"),
    timeline: str = typer.Option("", "--timeline", help="Timeline: 18m or 90d"),
    themes: str = typer.Option("", "--themes", help="Comma-separated theme codes"),
    conviction: int = typer.Option(0, "--conviction", help="PM conviction 1-5 (0 = unset)"),
    tax_notes: str = typer.Option("", "--tax-notes", help="CGT / franking / holding-period notes"),
    # Typer's repeatable-option pattern; default None (not a mutable []) —
    # same shape/noqa rationale as add-section's --figure below.
    condition: list[str] | None = typer.Option(  # noqa: B008
        None, "--condition",
        help="Repeatable invalidation condition: 'TEXT' (alert_review) or "
             "'hard_exit::TEXT'. The parser echo prints what will be enforced.",
    ),
    reason: str = typer.Option("Initial thesis", "--reason", help="Opening rationale"),
    from_agent_run: int = typer.Option(
        0, "--from-agent-run",
        help="agent_runs.run_id to create a draft thesis from (governance_status='draft', "
             "not 'approved'). All other options are ignored in this mode.",
    ),
) -> None:
    """Open a new investment thesis (research or watching status).

    --from-agent-run <run_id> creates the thesis via
    create_thesis_from_agent_run() instead of the normal human-authored
    path. As of Phase 1, this always fails with a clear error (no
    ThesisProposal schema exists yet — see
    asxos/domain/theses/schemas.py) — the flag is wired end-to-end ahead of
    that schema landing.
    """
    _require_personal_use()
    if from_agent_run:
        asyncio.run(_open_thesis_from_agent_run(symbol, from_agent_run))
        return

    if status not in ("research", "watching"):
        raise typer.BadParameter("--status must be 'research' or 'watching'")
    if conviction and not (1 <= conviction <= 5):
        raise typer.BadParameter("--conviction must be between 1 and 5")

    entry_lo: Decimal | None = None
    entry_hi: Decimal | None = None
    if entry:
        entry_lo, entry_hi = _parse_entry(entry)

    stop_d: Decimal | None = _parse_decimal(stop, "stop") if stop else None
    target_d: Decimal | None = _parse_decimal(target, "target") if target else None
    timeline_days: int | None = _parse_timeline(timeline) if timeline else None
    theme_list = [c.strip() for c in themes.split(",") if c.strip()] if themes else []
    thesis_text: str | None = thesis.strip() or None
    condition_list = [_parse_condition_option(c) for c in (condition or [])]

    asyncio.run(_open_thesis(
        symbol, status, thesis_text, entry_lo, entry_hi,
        stop_d, target_d, timeline_days, theme_list, condition_list,
        (conviction or None), (tax_notes.strip() or None), reason,
    ))


async def _open_thesis(
    symbol: str, status: str, thesis_text: str | None,
    entry_lo: Decimal | None, entry_hi: Decimal | None,
    stop_d: Decimal | None, target_d: Decimal | None,
    timeline_days: int | None, theme_list: list[str],
    condition_list: list[dict[str, str]],
    conviction: int | None, tax_notes: str | None, reason: str,
) -> None:
    await init_pool()
    try:
        async with acquire() as conn:
            t = await svc.open_thesis(
                conn, symbol,
                status=status,
                thesis_text=thesis_text,
                entry_band_lower=entry_lo,
                entry_band_upper=entry_hi,
                stop_price=stop_d,
                target_price=target_d,
                timeline_days=timeline_days,
                themes=theme_list,
                conditions=condition_list,
                conviction_level=conviction,
                tax_notes=tax_notes,
                reasoning=reason,
            )
        console.print(f"[green]✓[/green] Opened thesis #{t.thesis_id} for {t.symbol} ({t.status})")
        _print_thesis_detail(t)
        # 0042: the authoring echo — what the machine will (and will NOT)
        # enforce, plus placeholder ladder lint. A narrowing is never silent.
        if condition_list:
            console.print(lint_echo([c["text"] for c in condition_list]), markup=False)
        _print_ladder_lint(t)
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc
    finally:
        await close_pool()


async def _open_thesis_from_agent_run(symbol: str, run_id: int) -> None:
    await init_pool()
    try:
        async with acquire() as conn:
            t = await svc.create_thesis_from_agent_run(conn, run_id, symbol)
        console.print(
            f"[green]✓[/green] Opened draft thesis #{t.thesis_id} for {t.symbol} "
            f"from agent run #{run_id} (governance_status={t.governance_status})"
        )
        _print_thesis_detail(t)
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc
    finally:
        await close_pool()


@thesis_app.command("show")
def thesis_show(
    symbol: str = typer.Argument(..., help="Symbol, e.g. CBA.AU"),
    full_report: bool = typer.Option(
        False, "--full-report", help="Also render broker-report sections (Phase C)"
    ),
) -> None:
    """Show the most recent thesis for a symbol (all fields)."""
    _require_personal_use()
    asyncio.run(_show_thesis(symbol, full_report))


async def _show_thesis(symbol: str, full_report: bool = False) -> None:
    await init_pool()
    try:
        async with acquire() as conn:
            t = await svc.get_thesis_by_symbol(conn, symbol)
            if t is None:
                console.print(f"[yellow]No thesis found for {symbol}[/yellow]")
                raise typer.Exit(1)
            _print_thesis_detail(t)
            # 0042: conditions + events live in their own tables now.
            await _print_conditions(conn, t.thesis_id, symbol)
        if full_report:
            _print_report_sections(t)
    finally:
        await close_pool()


@thesis_app.command("list")
def thesis_list(
    status: str = typer.Option("", "--status", help="Filter: research|watching|active|exited|expired"),
) -> None:
    """List all theses (or filter by status)."""
    _require_personal_use()
    asyncio.run(_list_theses(status.strip() or None))


async def _list_theses(status: str | None) -> None:
    await init_pool()
    try:
        async with acquire() as conn:
            theses = await svc.list_theses(conn, status=status)
        if not theses:
            console.print("[yellow]No theses found.[/yellow]")
            return
        table = Table(title="Theses", show_header=True)
        for col in ("Symbol", "Status", "ID", "Entry band", "Stop", "Target", "Age", "Overdue"):
            table.add_column(col)
        for t in theses:
            table.add_row(*_thesis_summary_row(t))
        console.print(table)
    finally:
        await close_pool()


@thesis_app.command("enter")
def thesis_enter(
    symbol: str = typer.Argument(..., help="Symbol, e.g. CBA.AU"),
    at: str = typer.Option(..., "--at", help="Actual entry price"),
    qty: int = typer.Option(0, "--qty", help="Number of shares (informational)"),
) -> None:
    """Transition thesis to active — capital deployed."""
    _require_personal_use()
    price = _parse_decimal(at, "entry price")
    asyncio.run(_enter_thesis(symbol, price, qty or None))


async def _enter_thesis(symbol: str, price: Decimal, qty: int | None) -> None:
    await init_pool()
    try:
        async with acquire() as conn:
            t = await svc.get_thesis_by_symbol(conn, symbol)
            if t is None:
                console.print(f"[red]No thesis found for {symbol}[/red]")
                raise typer.Exit(1)
            t = await svc.enter_thesis(conn, t.thesis_id, price, qty)
        console.print(f"[green]✓[/green] Thesis #{t.thesis_id} {symbol} entered at {price}")
        _print_thesis_detail(t)
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc
    finally:
        await close_pool()


# ---------------------------------------------------------------------------
# approve / reject — governance_status transitions (Phase 1)
# ---------------------------------------------------------------------------

@thesis_app.command("approve")
def thesis_approve(
    thesis_id: int = typer.Argument(..., help="Thesis ID (numeric), not symbol"),
    reason: str = typer.Option(..., "--reason", help="Why you are approving this"),
    accept_stale_evidence: str = typer.Option(
        "", "--accept-stale-evidence",
        help="Override the 14-day evidence staleness check (reason required, logged separately)",
    ),
) -> None:
    """Approve a thesis pending review — governance_status -> 'approved'.

    Hard-fails if governance_status is not 'pending_review', if evidence is
    100% speculative (no override available), or if non-speculative
    evidence is older than 14 days (override with --accept-stale-evidence).
    """
    _require_personal_use()
    asyncio.run(_approve_thesis(thesis_id, reason, accept_stale_evidence.strip() or None))


async def _approve_thesis(
    thesis_id: int, reason: str, accept_stale_evidence: str | None
) -> None:
    await init_pool()
    try:
        async with acquire() as conn:
            t = await svc.approve_object(
                conn, thesis_id,
                reasoning=reason,
                accept_stale_evidence=accept_stale_evidence,
            )
        console.print(f"[green]✓[/green] Approved thesis #{t.thesis_id} ({t.symbol})")
        _print_thesis_detail(t)
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc
    finally:
        await close_pool()


@thesis_app.command("reject")
def thesis_reject(
    thesis_id: int = typer.Argument(..., help="Thesis ID (numeric), not symbol"),
    reason: str = typer.Option(..., "--reason", help="Why you are rejecting this"),
) -> None:
    """Reject a thesis pending review — governance_status -> 'rejected'.

    Only valid from 'draft', 'evidence_complete', or 'pending_review' —
    cannot reject an already-approved/rejected/retired thesis.
    """
    _require_personal_use()
    asyncio.run(_reject_thesis(thesis_id, reason))


async def _reject_thesis(thesis_id: int, reason: str) -> None:
    await init_pool()
    try:
        async with acquire() as conn:
            t = await svc.reject_object(conn, thesis_id, reasoning=reason)
        console.print(f"[yellow]✗[/yellow] Rejected thesis #{t.thesis_id} ({t.symbol})")
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc
    finally:
        await close_pool()


# ---------------------------------------------------------------------------
# attest — attestation transitions (0042, D4/R9)
# ---------------------------------------------------------------------------

@thesis_app.command("attest")
def thesis_attest(
    thesis_id: int = typer.Argument(..., help="Thesis ID (numeric), not symbol"),
    to: str = typer.Option("underwritten", "--to", help="underwritten|placeholder"),
    basis: str = typer.Option("", "--basis", help="The underwriting basis (required for underwritten)"),
    reason: str = typer.Option("", "--reason", help="Reasoning (required for demotion; defaults to basis for underwritten)"),
) -> None:
    """Attest a thesis' rule set — attestation placeholder <-> underwritten.

    To 'underwritten' the full gate runs: basis required, ladder coherent,
    stop not currently breached vs the latest close, condition baselines
    current. Demotion to 'placeholder' is always allowed with --reason.
    """
    _require_personal_use()
    if to not in ("underwritten", "placeholder"):
        raise typer.BadParameter("--to must be 'underwritten' or 'placeholder'")
    basis = basis.strip()
    reason = reason.strip()
    if to == "placeholder" and not reason:
        raise typer.BadParameter("--reason is required when demoting to placeholder")
    if not reason:
        reason = f"Underwritten: {basis}" if basis else "Attestation change"
    asyncio.run(_attest_thesis(thesis_id, to, basis or None, reason))


async def _attest_thesis(thesis_id: int, to: str, basis: str | None, reason: str) -> None:
    await init_pool()
    try:
        async with acquire() as conn:
            t = await svc.attest_thesis(conn, thesis_id, to=to, basis=basis, reasoning=reason)
        console.print(
            f"[green]✓[/green] Thesis #{t.thesis_id} ({t.symbol}) attestation → {t.attestation}"
        )
        _print_thesis_detail(t)
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc
    finally:
        await close_pool()


# ---------------------------------------------------------------------------
# condition add|resolve|list — thesis_conditions management (0042, D1/R2)
# ---------------------------------------------------------------------------

condition_app = typer.Typer(
    help="Invalidation condition management (0042).",
    no_args_is_help=True,
    add_completion=False,
)
thesis_app.add_typer(condition_app, name="condition")


@condition_app.command("add")
def condition_add(
    symbol: str = typer.Argument(..., help="Symbol, e.g. HUBS.NYSE"),
    text: str = typer.Option(..., "--text", help="The condition text"),
    semantics: str = typer.Option(
        "alert_review", "--semantics", help="hard_exit|alert_review (authored intent)"
    ),
    reason: str = typer.Option(..., "--reason", help="Why this condition exists"),
) -> None:
    """Add one invalidation condition — the parser echo prints exactly what
    will (and will NOT) be machine-enforced."""
    _require_personal_use()
    if semantics not in ("hard_exit", "alert_review"):
        raise typer.BadParameter("--semantics must be 'hard_exit' or 'alert_review'")
    asyncio.run(_condition_add(symbol, text, semantics, reason))


async def _condition_add(symbol: str, text: str, semantics: str, reason: str) -> None:
    await init_pool()
    try:
        async with acquire() as conn:
            t = await svc.get_thesis_by_symbol(conn, symbol)
            if t is None:
                console.print(f"[red]No thesis found for {symbol}[/red]")
                raise typer.Exit(1)
            c = await conditions_svc.add_condition(
                conn, t.thesis_id, text=text, trigger_semantics=semantics, reasoning=reason
            )
        console.print(
            f"[green]✓[/green] Condition {c.ordinal} added to thesis #{c.thesis_id} "
            f"({symbol}, {c.trigger_semantics})"
        )
        console.print(c.enforcement_note, markup=False)
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc
    finally:
        await close_pool()


@condition_app.command("resolve")
def condition_resolve(
    condition_id: int = typer.Argument(..., help="Condition ID (see: asx thesis condition list)"),
    reason: str = typer.Option(..., "--reason", help="Why this condition no longer applies"),
) -> None:
    """Resolve a condition (terminal, human-only). Re-opening = a new
    condition with a fresh baseline."""
    _require_personal_use()
    asyncio.run(_condition_resolve(condition_id, reason))


async def _condition_resolve(condition_id: int, reason: str) -> None:
    await init_pool()
    try:
        async with acquire() as conn:
            c = await conditions_svc.resolve_condition(conn, condition_id, reasoning=reason)
        console.print(
            f"[green]✓[/green] Condition {c.ordinal} on thesis #{c.thesis_id} resolved"
        )
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc
    finally:
        await close_pool()


@condition_app.command("list")
def condition_list(
    symbol: str = typer.Argument(..., help="Symbol, e.g. HUBS.NYSE"),
) -> None:
    """List a thesis' conditions with their machine baselines and events."""
    _require_personal_use()
    asyncio.run(_condition_list(symbol))


async def _condition_list(symbol: str) -> None:
    await init_pool()
    try:
        async with acquire() as conn:
            t = await svc.get_thesis_by_symbol(conn, symbol)
            if t is None:
                console.print(f"[red]No thesis found for {symbol}[/red]")
                raise typer.Exit(1)
            await _print_conditions(conn, t.thesis_id, symbol)
    finally:
        await close_pool()


async def _print_conditions(conn: Any, thesis_id: int, symbol: str) -> None:
    """Render conditions + their event history (0042 tables)."""
    conds = await conditions_svc.list_conditions(conn, thesis_id)
    if not conds:
        console.print(f"[dim]No conditions on thesis #{thesis_id} ({symbol}).[/dim]")
        return
    console.print(f"\n[bold]Conditions — thesis #{thesis_id} ({symbol}):[/bold]")
    colour_for = {"active": "yellow", "triggered": "red", "re_armed": "cyan", "resolved": "green"}
    for c in conds:
        colour = colour_for.get(c.status, "white")
        console.print(
            f"  [{colour}][{c.status}][/{colour}] "
            f"[{c.ordinal}] {escape(c.condition_text)} ({c.trigger_semantics}, id={c.condition_id})"
        )
        console.print(f"      {escape(c.enforcement_note)}")
        events = await conditions_svc.get_events(conn, c.condition_id)
        for e in events:
            close_str = f" close={e.observed_close}" if e.observed_close is not None else ""
            console.print(
                f"      [dim]{e.price_date} {e.event_type}{close_str} [{e.source}][/dim]"
            )


@thesis_app.command("revise")
def thesis_revise(
    symbol: str = typer.Argument(..., help="Symbol, e.g. CBA.AU"),
    reason: str = typer.Option(..., "--reason", help="Why you are revising this field"),
    thesis: str = typer.Option("", "--thesis", help="New thesis text"),
    stop: str = typer.Option("", "--stop", help="New stop price"),
    target: str = typer.Option("", "--target", help="New target price"),
    entry: str = typer.Option("", "--entry", help="New entry band: '60-65'"),
    timeline: str = typer.Option("", "--timeline", help="New timeline: 18m or 90d"),
    new_status: str = typer.Option("", "--status", help="New status"),
    conviction: int = typer.Option(0, "--conviction", help="New PM conviction 1-5"),
    tax_notes: str = typer.Option("", "--tax-notes", help="New CGT / franking notes"),
) -> None:
    """Revise one field on the most recent thesis for a symbol.

    One field per invocation. --reason is required.
    """
    _require_personal_use()
    changes: dict[str, object] = {}
    if thesis:
        changes["thesis_text"] = thesis.strip()
    if conviction:
        if not (1 <= conviction <= 5):
            raise typer.BadParameter("--conviction must be between 1 and 5")
        changes["conviction_level"] = conviction
    if tax_notes:
        changes["tax_notes"] = tax_notes.strip()
    if stop:
        changes["stop_price"] = _parse_decimal(stop, "stop")
    if target:
        changes["target_price"] = _parse_decimal(target, "target")
    if timeline:
        changes["timeline_days"] = _parse_timeline(timeline)
    if new_status:
        changes["status"] = new_status.strip()
    if entry:
        lo, hi = _parse_entry(entry)
        changes["entry_band_lower"] = lo
        changes["entry_band_upper"] = hi

    if not changes:
        console.print("[red]Specify at least one field to revise (--thesis, --stop, --target, --entry, --timeline, --status, --conviction, --tax-notes)[/red]")
        raise typer.Exit(1)

    asyncio.run(_revise_thesis(symbol, changes, reason))


async def _revise_thesis(symbol: str, changes: dict[str, Any], reason: str) -> None:
    await init_pool()
    try:
        async with acquire() as conn:
            t = await svc.get_thesis_by_symbol(conn, symbol)
            if t is None:
                console.print(f"[red]No thesis found for {symbol}[/red]")
                raise typer.Exit(1)

            for field, value in changes.items():
                if field not in REVISABLE_FIELDS:
                    console.print(f"[red]Field {field!r} is not revisable[/red]")
                    raise typer.Exit(1)
                t = await svc.revise_thesis(conn, t.thesis_id, field, value, reason)

        console.print(f"[green]✓[/green] Revised thesis #{t.thesis_id} for {symbol}")
        _print_thesis_detail(t)
        # 0042: placeholder ladders are not blocked, but never silent either.
        _print_ladder_lint(t)
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc
    finally:
        await close_pool()


# ---------------------------------------------------------------------------
# add-section — Phase C broker-report thesis (migration 0040)
# ---------------------------------------------------------------------------

@thesis_app.command("add-section")
def thesis_add_section(
    symbol: str = typer.Argument(..., help="Symbol, e.g. CBA.AU"),
    kind: str = typer.Option(..., "--kind", help=f"One of: {', '.join(REPORT_SECTION_KINDS)}"),
    body: str = typer.Option("", "--body", help="Section prose — no inline $/%/x numbers, use --figure"),
    body_file: str = typer.Option("", "--body-file", help="Read body from a file instead of --body"),
    # Typer's repeatable-option pattern; default is None (not a mutable []),
    # and Typer's OptionInfo is a descriptor, not the classic shared-mutable-
    # default bug bugbear's B008 exists to catch — suppressed below.
    figure: list[str] | None = typer.Option(  # noqa: B008
        None, "--figure",
        help="Repeatable: 'Label=Value' (Value is a raw decimal, e.g. '0.99' for 99%, not '99%')",
    ),
    reason: str = typer.Option("", "--reason", help="Why this section/figures (optional)"),
) -> None:
    """Add or replace one broker-report section (by --kind) on the most recent thesis for SYMBOL.

    Every figure is recorded with provenance='james_input' — Phase C's first
    cut has no cited/derived recompute engine; this is your own conviction,
    not a computed or agent-sourced number. Replaces any existing section of
    the same --kind wholesale — the prior content is never silently
    discarded, it survives in `asx thesis history`.
    """
    _require_personal_use()
    if kind not in REPORT_SECTION_KINDS:
        raise typer.BadParameter(f"--kind must be one of: {', '.join(REPORT_SECTION_KINDS)}")
    # Strip before the exactly-one check (matches --thesis/--tax-notes elsewhere
    # in this file) so a whitespace-only --body ("   ") is treated as absent,
    # not silently persisted as an invisible section body.
    body = body.strip()
    if bool(body) == bool(body_file):
        raise typer.BadParameter("Specify exactly one of --body or --body-file")
    if body_file:
        try:
            body = Path(body_file).read_text().strip()
        except (OSError, UnicodeDecodeError) as exc:
            raise typer.BadParameter(f"Could not read --body-file {body_file!r}: {exc}") from exc
    figures = [_parse_figure(f) for f in (figure or [])]
    asyncio.run(_add_report_section(symbol, kind, body, figures, reason.strip()))


async def _add_report_section(
    symbol: str, kind: str, body: str, figures: list[ReportFigure], reason: str
) -> None:
    await init_pool()
    try:
        async with acquire() as conn:
            t = await svc.get_thesis_by_symbol(conn, symbol)
            if t is None:
                console.print(f"[red]No thesis found for {symbol}[/red]")
                raise typer.Exit(1)
            t = await svc.add_report_section(
                conn, t.thesis_id, kind, body, figures, reasoning=reason
            )
        console.print(
            f"[green]✓[/green] Section '{kind}' recorded on thesis #{t.thesis_id} "
            f"({symbol}) — {len(t.report_sections)}/{len(REPORT_SECTION_KINDS)} sections. "
            f"View with: asx thesis show {symbol} --full-report"
        )
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc
    finally:
        await close_pool()


def _thesis_review_cmd(
    symbol: str = typer.Argument(..., help="Symbol, e.g. CBA.AU"),
    reason: str = typer.Option(..., "--reason", help="Why you are still holding (required)"),
) -> None:
    """Record a deliberate 'reviewed, no change' discipline event.

    This is the core discipline scaffold. You must state why you are still
    holding. No field is changed. The event is recorded in thesis_revisions.
    """
    _require_personal_use()
    asyncio.run(_review_thesis(symbol, reason))


# Register as both 'review' and 'hold' (alias)
thesis_app.command("review")(_thesis_review_cmd)
thesis_app.command("hold", help="Alias for 'review' — deliberate hold discipline event.")(_thesis_review_cmd)


async def _review_thesis(symbol: str, reason: str) -> None:
    await init_pool()
    try:
        async with acquire() as conn:
            t = await svc.get_thesis_by_symbol(conn, symbol)
            if t is None:
                console.print(f"[red]No thesis found for {symbol}[/red]")
                raise typer.Exit(1)
            t = await svc.review_thesis(conn, t.thesis_id, reason)
        console.print(
            f"[green]✓[/green] Reviewed thesis #{t.thesis_id} for {symbol} — "
            f"next review due {t.revisit_due_at.date()}"
        )
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc
    finally:
        await close_pool()


@thesis_app.command("exit")
def thesis_exit(
    symbol: str = typer.Argument(..., help="Symbol, e.g. CBA.AU"),
    at: str = typer.Option(..., "--at", help="Exit price"),
    stop: bool = typer.Option(False, "--stop", help="Stopped out"),
    hit_target: bool = typer.Option(False, "--target", help="Target hit"),
    reason: str = typer.Option("", "--reason", help="Exit reasoning"),
    redeploy: bool = typer.Option(False, "--redeploy", help="Show CGT-adjusted redeployment candidates after exit"),
) -> None:
    """Close a thesis position. Use --redeploy to see CGT-adjusted redeployment ranking."""
    _require_personal_use()
    price = _parse_decimal(at, "exit price")
    if stop and hit_target:
        raise typer.BadParameter("Cannot use both --stop and --target")
    rev_type = "exited_by_stop" if stop else ("exited_by_target" if hit_target else "exited")
    asyncio.run(_exit_thesis(symbol, price, rev_type, reason, show_redeploy=redeploy))


async def _exit_thesis(
    symbol: str, price: Decimal, rev_type: str, reason: str, show_redeploy: bool = False
) -> None:
    await init_pool()
    try:
        async with acquire() as conn:
            t = await svc.get_thesis_by_symbol(conn, symbol)
            if t is None:
                console.print(f"[red]No thesis found for {symbol}[/red]")
                raise typer.Exit(1)
            t = await svc.exit_thesis(conn, t.thesis_id, price, revision_type=rev_type, reasoning=reason)

        console.print(
            f"[green]✓[/green] Exited thesis #{t.thesis_id} for {symbol} at {price} ({rev_type})"
        )

        if show_redeploy:
            await _show_redeploy_candidates(symbol)
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc
    finally:
        await close_pool()


async def _show_redeploy_candidates(symbol: str) -> None:
    """Print CGT-adjusted redeployment candidates from opportunity_cost_scenarios.

    (exit_price param removed 2026-07-21 — dead since the scenarios moved to
    the pre-computed weekly job; the query keys on symbol alone. 07-18 audit.)
    """
    try:
        async with acquire() as conn:
            # Prefer pre-computed scenarios from the weekly job
            rows = await conn.fetch(
                """
                SELECT oc.alternative_symbol, oc.alternative_source,
                       oc.gross_expected_return, oc.estimated_cgt_friction,
                       oc.net_expected_return
                FROM opportunity_cost_scenarios oc
                JOIN theses t ON t.thesis_id = oc.thesis_id
                WHERE t.symbol = $1
                ORDER BY oc.net_expected_return DESC
                LIMIT 10
                """,
                symbol,
            )

        if not rows:
            console.print("[yellow]No pre-computed redeployment scenarios found.[/yellow]")
            console.print("[dim]Run compute_opportunity_cost.py (weekly Sat job) to populate.[/dim]")
            return

        console.print(f"\n[bold]Redeployment candidates (CGT-adjusted) for {symbol}:[/bold]")
        tbl = Table(show_header=True, header_style="bold")
        tbl.add_column("Candidate", style="cyan")
        tbl.add_column("Source")
        tbl.add_column("Gross return", justify="right")
        tbl.add_column("CGT friction", justify="right")
        tbl.add_column("Net return", justify="right")
        for row in rows:
            gross = f"{Decimal(str(row['gross_expected_return'])):+.1%}" if row["gross_expected_return"] else "—"
            friction = f"{Decimal(str(row['estimated_cgt_friction'])):.1%}" if row["estimated_cgt_friction"] else "—"
            net = f"{Decimal(str(row['net_expected_return'])):+.1%}" if row["net_expected_return"] else "—"
            tbl.add_row(row["alternative_symbol"], row["alternative_source"], gross, friction, net)
        console.print(tbl)
        console.print("[dim]CGT friction is a flat 45% marginal rate approximation. See docs/foundation/spec/tax-alpha.md.[/dim]")
    except Exception as exc:
        console.print(f"[yellow]Could not load redeployment candidates: {exc}[/yellow]")


@thesis_app.command("attach-underlying")
def thesis_attach_underlying(
    symbol: str = typer.Argument(..., help="Symbol, e.g. MIN.AU"),
    underlying: str = typer.Option(..., "--underlying", help="Underlying code, e.g. iron_ore_62fe"),
    exposure: str = typer.Option(..., "--exposure", help="Exposure weight [0, 1], e.g. 0.65"),
    direction: str = typer.Option(..., "--direction", help="positive|negative"),
) -> None:
    """Attach or update an underlying commodity/rate on a thesis.

    The sum of all exposure weights per thesis must not exceed 1.0.
    Run `asx underlying list` to see available underlying codes.
    """
    _require_personal_use()
    exposure_d = _parse_decimal(exposure, "exposure")
    if direction not in ("positive", "negative"):
        raise typer.BadParameter("--direction must be 'positive' or 'negative'")
    asyncio.run(_attach_underlying(symbol, underlying, exposure_d, direction))


async def _attach_underlying(
    symbol: str,
    underlying_code: str,
    exposure: Decimal,
    direction: str,
) -> None:
    await init_pool()
    try:
        async with acquire() as conn:
            t = await svc.get_thesis_by_symbol(conn, symbol)
            if t is None:
                console.print(f"[red]No thesis found for {symbol}[/red]")
                raise typer.Exit(1)
            await underlying_svc.attach_underlying(
                conn, t.thesis_id, underlying_code, exposure, direction
            )
        console.print(
            f"[green]✓[/green] Attached {underlying_code} to thesis #{t.thesis_id} "
            f"({symbol}) — exposure {exposure} {direction}"
        )
    except (ValueError, RuntimeError) as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc
    finally:
        await close_pool()


@thesis_app.command("history")
def thesis_history(
    symbol: str = typer.Argument(..., help="Symbol, e.g. CBA.AU"),
) -> None:
    """Show the full revision history for a symbol's most recent thesis."""
    _require_personal_use()
    asyncio.run(_thesis_history(symbol))


async def _thesis_history(symbol: str) -> None:
    await init_pool()
    try:
        async with acquire() as conn:
            t = await svc.get_thesis_by_symbol(conn, symbol)
            if t is None:
                console.print(f"[red]No thesis found for {symbol}[/red]")
                raise typer.Exit(1)
            history = await svc.get_history(conn, t.thesis_id)

        table = Table(title=f"Thesis #{t.thesis_id} — {symbol} history", show_header=True)
        for col in ("Date", "Type", "Fields changed", "Reasoning"):
            table.add_column(col)
        for rev in history:
            fields = ", ".join(rev.diff.keys()) or "—"
            table.add_row(
                str(rev.revised_at.date()),
                rev.revision_type,
                fields,
                rev.reasoning[:80] + ("…" if len(rev.reasoning) > 80 else ""),
            )
        console.print(table)
    finally:
        await close_pool()


# ---------------------------------------------------------------------------
# update-consensus
# ---------------------------------------------------------------------------

@thesis_app.command("update-consensus")
def thesis_update_consensus(
    symbol: str = typer.Argument(..., help="Symbol, e.g. HUBS.NYSE"),
    buy: int = typer.Option(..., "--buy", help="Number of buy ratings"),
    neutral: int = typer.Option(0, "--neutral", help="Number of neutral ratings"),
    sell: int = typer.Option(0, "--sell", help="Number of sell ratings"),
    target: str = typer.Option("", "--target", help="Consensus price target"),
) -> None:
    """Record analyst consensus snapshot for a thesis."""
    _require_personal_use()
    target_d = _parse_decimal(target, "target") if target else None
    asyncio.run(_update_consensus(symbol, buy, neutral, sell, target_d))


async def _update_consensus(
    symbol: str, buy: int, neutral: int, sell: int, target: Decimal | None
) -> None:
    await init_pool()
    try:
        async with acquire() as conn:
            t = await svc.get_thesis_by_symbol(conn, symbol)
            if t is None:
                console.print(f"[red]No thesis found for {symbol}[/red]")
                raise typer.Exit(1)
            await svc.update_analyst_consensus(
                conn, t.thesis_id,
                buy=buy, neutral=neutral, sell=sell,
                target=target, updated_at=date.today(),
            )
        console.print(
            f"[green]✓[/green] Updated consensus for {symbol}: "
            f"{buy}B/{neutral}N/{sell}S"
            + (f"  target ${target}" if target else "")
        )
    finally:
        await close_pool()


# ---------------------------------------------------------------------------
# log-analyst
# ---------------------------------------------------------------------------

@thesis_app.command("log-analyst")
def thesis_log_analyst(
    symbol: str = typer.Argument(..., help="Symbol, e.g. HUBS.NYSE"),
    analyst: str = typer.Option(..., "--analyst", help="Analyst firm or name"),
    action: str = typer.Option(..., "--action", help="upgrade|downgrade|initiate|reiterate"),
    from_rating: str = typer.Option("", "--from-rating", help="Previous rating"),
    to_rating: str = typer.Option(..., "--to-rating", help="New rating"),
    from_target: str = typer.Option("", "--from-target", help="Previous price target"),
    to_target: str = typer.Option("", "--to-target", help="New price target"),
    event_date: str = typer.Option("", "--date", help="YYYY-MM-DD (default: today)"),
) -> None:
    """Log an analyst rating change as a thesis revision event."""
    _require_personal_use()
    if action not in ("upgrade", "downgrade", "initiate", "reiterate"):
        raise typer.BadParameter("--action must be upgrade|downgrade|initiate|reiterate")
    ft = _parse_decimal(from_target, "from-target") if from_target else None
    tt = _parse_decimal(to_target, "to-target") if to_target else None
    ed = date.fromisoformat(event_date) if event_date else date.today()
    asyncio.run(_log_analyst(symbol, analyst, action, from_rating, to_rating, ft, tt, ed))


async def _log_analyst(
    symbol: str,
    analyst: str,
    action: str,
    from_rating: str,
    to_rating: str,
    from_target: Decimal | None,
    to_target: Decimal | None,
    event_date: date,
) -> None:
    await init_pool()
    try:
        async with acquire() as conn:
            t = await svc.get_thesis_by_symbol(conn, symbol)
            if t is None:
                console.print(f"[red]No thesis found for {symbol}[/red]")
                raise typer.Exit(1)
            await svc.log_analyst_action(
                conn, t.thesis_id,
                analyst=analyst, action=action,
                from_rating=from_rating, to_rating=to_rating,
                from_target=from_target, to_target=to_target,
                event_date=event_date,
            )
        console.print(
            f"[green]✓[/green] Logged analyst action for {symbol}: "
            f"{analyst} {action} → {to_rating}"
        )
    finally:
        await close_pool()


# ---------------------------------------------------------------------------
# set-earnings
# ---------------------------------------------------------------------------

@thesis_app.command("set-earnings")
def thesis_set_earnings(
    symbol: str = typer.Argument(..., help="Symbol, e.g. HUBS.NYSE"),
    date_str: str = typer.Option(..., "--date", help="YYYY-MM-DD next earnings date"),
    notes: str = typer.Option("", "--notes", help="Earnings notes"),
) -> None:
    """Record the next earnings date for a thesis position."""
    _require_personal_use()
    try:
        ed = date.fromisoformat(date_str)
    except ValueError as exc:
        raise typer.BadParameter(f"Invalid date {date_str!r}: use YYYY-MM-DD") from exc
    asyncio.run(_set_earnings(symbol, ed, notes))


async def _set_earnings(symbol: str, next_earnings_date: date, notes: str) -> None:
    await init_pool()
    try:
        async with acquire() as conn:
            t = await svc.get_thesis_by_symbol(conn, symbol)
            if t is None:
                console.print(f"[red]No thesis found for {symbol}[/red]")
                raise typer.Exit(1)
            await svc.set_earnings(conn, t.thesis_id, next_earnings_date, notes)
        console.print(
            f"[green]✓[/green] Set next earnings date for {symbol}: {next_earnings_date}"
            + (f" — {notes}" if notes else "")
        )
    finally:
        await close_pool()


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def _print_thesis_detail(t: Thesis) -> None:
    """Print a thesis in a key-value Rich panel."""
    deadline_str = "—"
    if t.timeline_days and t.opened_at:
        deadline = t.opened_at.date() + timedelta(days=t.timeline_days)
        days_elapsed = (date.today() - t.opened_at.date()).days
        deadline_str = f"{deadline} ({days_elapsed}/{t.timeline_days}d elapsed)"

    overdue = date.today() > t.revisit_due_at.date()
    revisit_str = str(t.revisit_due_at.date())
    if overdue:
        revisit_str = f"[red]{revisit_str} OVERDUE[/red]"

    attest_str = (
        f"underwritten — {t.attestation_basis}"
        if t.attestation == "underwritten"
        else "[yellow]PLACEHOLDER — not underwritten[/yellow]"
    )

    rows = [
        ("ID", str(t.thesis_id)),
        ("Symbol", t.symbol),
        ("Status", t.status),
        ("Governance", t.governance_status),  # migration 0033
        ("Attestation", attest_str),  # migration 0042 (D4/R9)
        ("Thesis", t.thesis_text or "[dim]not articulated[/dim]"),
        ("Entry band", f"{t.entry_band_lower}–{t.entry_band_upper}" if t.entry_band_lower else "—"),
        ("Stop", str(t.stop_price or "—")),
        ("Target", str(t.target_price or "—")),
        ("Timeline", deadline_str),
        ("Conviction", f"{t.conviction_level}/5" if t.conviction_level else "—"),
        ("Tax notes", t.tax_notes or "—"),
        ("Themes", ", ".join(t.themes) or "—"),
        ("Actual entry", f"{t.actual_entry_price} on {t.actual_entry_at.date()}" if t.actual_entry_price and t.actual_entry_at else "—"),
        ("Actual exit", f"{t.actual_exit_price} on {t.actual_exit_at.date()}" if t.actual_exit_price and t.actual_exit_at else "—"),
        ("Opened", str(t.opened_at.date())),
        ("Last revisited", str(t.last_revisited_at.date())),
        ("Next revisit due", revisit_str),
    ]

    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("Field", style="dim")
    table.add_column("Value")
    for key, val in rows:
        table.add_row(key, val)

    console.print(table)

    # Invalidation conditions moved to thesis_conditions (0042) — rendered by
    # _print_conditions() where a connection is available (show / condition list).

    if t.report_sections:
        console.print(
            f"\n[dim]Full report: {len({s.kind for s in t.report_sections})}/"
            f"{len(REPORT_SECTION_KINDS)} sections — use --full-report to view[/dim]"
        )


# ---------------------------------------------------------------------------
# Broker-report section rendering — Phase C (migration 0040)
# ---------------------------------------------------------------------------

_SECTION_TITLES: dict[str, str] = {
    "identity_classification": "Identity & Classification",
    "business": "Business",
    "moat": "Moat",
    "capital_allocation": "Capital Allocation",
    "strategy_catalysts": "Strategy & Catalysts",
    "risks_bear": "Risks / Bear Case",
    "valuation": "Valuation",
    "position_plan": "Position Plan",
    "verdict_conviction": "Verdict & Conviction",
    "evidence_ledger": "Evidence Ledger",
}


def _print_report_sections(t: Thesis) -> None:
    """Render report_sections in the fixed REPORT_SECTION_KINDS order (not
    insertion order) — freeform per-thesis, absent kinds are skipped.

    section.body and fig.label are free text from --body/--body-file/
    --figure — Pydantic validates them for the numeric-literal/monitor-only
    rules only, nothing excludes Rich markup syntax ('[...]'). Console.print
    interprets '[...]' as style/link markup by default, so unescaped user
    text can silently drop content (an unrecognised '[...]' span swallows
    everything until end-of-string), crash on a mismatched closing tag
    (rich.errors.MarkupError — and since the bad text is already durably
    persisted, every future --full-report view of that thesis crashes the
    same way until overwritten), or spoof a clickable terminal hyperlink via
    '[link=URL]'. body renders with markup=False (verbatim, no styling
    needed); fig.label is escaped since it sits inside a real markup
    template (security-engineer review, 2026-07-19).
    """
    if not t.report_sections:
        console.print(
            "\n[dim]No report sections yet. "
            f"asx thesis add-section {t.symbol} --kind ... --body ...[/dim]"
        )
        return
    by_kind = {s.kind: s for s in t.report_sections}
    console.print(f"\n[bold]Full report — {t.symbol}[/bold]")
    for kind in REPORT_SECTION_KINDS:
        section = by_kind.get(cast(ReportSectionKind, kind))
        if section is None:
            continue
        console.print(f"\n[bold underline]{_SECTION_TITLES[kind]}[/bold underline]")
        console.print(section.body, markup=False)
        for fig in section.figures:
            tag = "monitor only, " if fig.monitor_only else ""
            console.print(f"  • {escape(fig.label)}: {fig.value}  [dim]({tag}{fig.provenance})[/dim]")
