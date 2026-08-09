"""
Section 3: Active theses — M-Brief-V2-Sections (+ 0042 rules-integrity).

For each active thesis: format a thesis card, compute underlying score,
detect hidden risk. Severity based on revisit overdue / underlying divergence.

0042 (design §5, last row): each card also renders the attestation tag, the
disposal-lock badge, and a condition-state line from thesis_conditions;
unparseable (not_machine_checkable) conditions are a visible yellow line,
never absent (register #5).

SeverityItem levels:
  - red:    triggered hard_exit condition on an underwritten, unlocked thesis
            (capital-discipline priority) OR revisit overdue / timeline expired
  - yellow: any other triggered condition OR underlying diverging OR revisit
            due within 7d OR hidden risk OR not-machine-checked conditions
  - green:  all ok
"""
from __future__ import annotations

import time
from collections import defaultdict
from datetime import date, datetime
from typing import Any

from asxos.db import acquire
from asxos.domain.brief.severity import (
    earnings_risk,
    thesis_revisit_overdue,
    thesis_timeline_expired,
)
from asxos.domain.brief.shap import format_top_factors
from asxos.domain.brief.types import SectionResult, SectionStatus, SeverityItem, SeverityLevel
from asxos.domain.models.production_gate import resolve_production_model
from asxos.domain.portfolio.locks import get_disposal_locks
from asxos.domain.underlyings.attribution import score_thesis_underlying
from asxos.domain.underlyings.divergence import detect_hidden_risk
from asxos.domain.underlyings.service import bulk_list_thesis_underlyings, get_5d_moves

_SECTION = "active_theses"


async def collect_active_theses(as_of: date) -> SectionResult:
    start_ms = int(time.monotonic() * 1000)
    items: list[SeverityItem] = []

    async with acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT thesis_id, symbol, status, opened_at, stop_price, target_price,
                   timeline_days, entry_band_lower, entry_band_upper, revisit_due_at,
                   analyst_buy_count, analyst_neutral_count, analyst_sell_count,
                   analyst_consensus_target, next_earnings_date, earnings_notes,
                   attestation
            FROM theses
            WHERE status = 'active'
              AND governance_status = 'approved'
            ORDER BY opened_at DESC
            """
        )

        if not rows:
            elapsed_ms = int(time.monotonic() * 1000) - start_ms
            return SectionResult(
                name=_SECTION, status=SectionStatus.no_data,
                items=(), elapsed_ms=elapsed_ms,
                error="no active theses",
            )

        # Batch-load all underlyings and moves in two queries (avoids N+1)
        all_thesis_ids = [r["thesis_id"] for r in rows]

        # 0042: condition states (one aggregate query) + disposal locks. The
        # unresolved conditions drive the condition-state line and the
        # triggered/unparseable severities below.
        cond_rows = await conn.fetch(
            """
            SELECT thesis_id, status, trigger_semantics, enforcement_kind
            FROM thesis_conditions
            WHERE thesis_id = ANY($1) AND status <> 'resolved'
            """,
            all_thesis_ids,
        )
        conds_by_thesis: dict[int, list[Any]] = defaultdict(list)
        for c in cond_rows:
            conds_by_thesis[c["thesis_id"]].append(c)
        locks = await get_disposal_locks(conn, [r["symbol"] for r in rows], as_of)

        tu_by_thesis = await bulk_list_thesis_underlyings(conn, all_thesis_ids)
        all_underlying_ids = list({
            tu.underlying_id
            for tus in tu_by_thesis.values()
            for tu in tus
        })
        all_moves = await get_5d_moves(conn, all_underlying_ids, as_of) if all_underlying_ids else {}

        # Governance Section 4.4 Step B / portfolio-conventions.md: resolve the
        # single active+approved_for_allocation production model before
        # reading signals, so an unapproved model can't surface on a thesis
        # card any more than it can reach the allocator or the V1 brief.
        model_rows = await conn.fetch(
            "SELECT model FROM model_versions "
            "WHERE is_active = TRUE AND approved_for_allocation = TRUE"
        )
        # Display-only: under a deliberate Model A quarantine (rule #11 → 0
        # approved models) resolve returns None; skip the signal fetch so every
        # thesis card still renders with full discipline severity, just without
        # the cosmetic "Model A:" driver line. The allocator keeps its own
        # hard-fail (build.py) — that is rule #11's real enforcement. See R9.
        production_model = resolve_production_model(model_rows, required=False)

        # Steady-state ML explainability: latest Model A signal per thesis symbol.
        # One batch query (DISTINCT ON, latest as_of) — same pattern as the V1
        # signal-change line. Missing signal → no drivers line on that card.
        all_symbols = [r["symbol"] for r in rows]
        if production_model is not None:
            sig_rows = await conn.fetch(
                """
                SELECT DISTINCT ON (symbol) symbol, signal_label, shap_factors
                FROM signals
                WHERE symbol = ANY($1) AND model = $2
                ORDER BY symbol, as_of DESC
                """,
                all_symbols,
                production_model,
            )
            sig_by_symbol = {r["symbol"]: r for r in sig_rows}
        else:
            sig_by_symbol = {}

        for row in rows:
            thesis_id = row["thesis_id"]
            symbol = row["symbol"]
            revisit_due = row["revisit_due_at"]
            opened = row["opened_at"]

            # Underlying score (uses pre-fetched data)
            thesis_underlyings = tu_by_thesis.get(thesis_id, [])
            moves = {tu.underlying_id: all_moves.get(tu.underlying_id) for tu in thesis_underlyings}
            score = score_thesis_underlying(thesis_underlyings, moves)

            # Overdue check
            overdue_item = thesis_revisit_overdue(
                symbol, revisit_due.date(), as_of, section=_SECTION
            )

            # Timeline expiry check
            expiry_item = thesis_timeline_expired(
                symbol, opened.date(), row["timeline_days"], as_of, section=_SECTION
            )

            days_since = (as_of - opened.date()).days
            days_to_revisit = (revisit_due.date() - as_of).days

            entry_str = ""
            if row["entry_band_lower"] and row["entry_band_upper"]:
                entry_str = f"Entry: {row['entry_band_lower']}–{row['entry_band_upper']} | "

            timeline_mo = f"{row['timeline_days'] // 30}mo" if row["timeline_days"] else "—"

            # Steady-state ML driver line — why Model A rates this symbol today.
            sig = sig_by_symbol.get(symbol)
            signal_line = ""
            if sig is not None:
                drivers = format_top_factors(sig["shap_factors"], n=3)
                drivers_str = f" | Top drivers: {drivers}" if drivers else ""
                signal_line = f"\nModel A: {sig['signal_label']}{drivers_str}"

            # 0042: attestation tag + lock badge + condition-state line.
            attestation = row["attestation"]
            att_tag = (
                "underwritten" if attestation == "underwritten"
                else "PLACEHOLDER — not underwritten"
            )
            lock = locks.get(symbol)
            lock_badge = ""
            if lock is not None:
                lock_badge = (
                    f" | LOCKED ({'until ' + str(lock.lock_end) if lock.lock_end else 'end unknown'})"
                )

            conds = conds_by_thesis.get(thesis_id, [])
            n_triggered = sum(1 for c in conds if c["status"] == "triggered")
            n_unparseable = sum(
                1 for c in conds
                if c["enforcement_kind"] == "not_machine_checkable"
                and c["status"] != "triggered"
            )
            n_re_armed = sum(
                1 for c in conds
                if c["status"] == "re_armed"
                and c["enforcement_kind"] != "not_machine_checkable"
            )
            n_active = sum(
                1 for c in conds
                if c["status"] == "active"
                and c["enforcement_kind"] != "not_machine_checkable"
            )
            cond_parts = []
            if n_triggered:
                cond_parts.append(f"{n_triggered} triggered")
            if n_re_armed:
                cond_parts.append(f"{n_re_armed} re-armed")
            if n_unparseable:
                cond_parts.append(f"{n_unparseable} not machine-checked")
            if n_active:
                cond_parts.append(f"{n_active} active")
            cond_line = "conditions: " + (" · ".join(cond_parts) if cond_parts else "none")

            msg = (
                f"{symbol} | Active | {days_since}d | {att_tag}{lock_badge}\n"
                f"{entry_str}"
                f"Stop: {row['stop_price'] or '—'} | Target: {row['target_price'] or '—'} | {timeline_mo}\n"
                f"Underlying: {score.label} (weighted {score.weighted_movement:+.2f}%)\n"
                f"{cond_line}\n"
                f"Revisit: {'overdue' if days_to_revisit < 0 else f'due in {days_to_revisit}d'}"
                f"{signal_line}"
            )

            # Red iff a triggered hard_exit condition sits on an underwritten,
            # unlocked thesis (design §5) — the full action-eligible combination;
            # any demoted trigger (placeholder / locked / alert_review) is yellow.
            hard_trigger_red = (
                attestation == "underwritten"
                and lock is None
                and any(
                    c["status"] == "triggered" and c["trigger_semantics"] == "hard_exit"
                    for c in conds
                )
            )

            # Determine severity — hard trigger first (capital discipline),
            # then expiry and overdue both red; expiry takes priority.
            if hard_trigger_red:
                items.append(SeverityItem(
                    level=SeverityLevel.red, message=msg, section=_SECTION
                ))
            elif expiry_item and expiry_item.level == SeverityLevel.red:
                items.append(expiry_item)
            elif overdue_item:
                items.append(overdue_item)
            elif expiry_item:
                items.append(expiry_item)
            elif n_triggered or score.label == "diverging" or days_to_revisit <= 7:
                items.append(SeverityItem(
                    level=SeverityLevel.yellow, message=msg, section=_SECTION
                ))
            else:
                items.append(SeverityItem(
                    level=SeverityLevel.green, message=msg, section=_SECTION
                ))

            # Unparseable conditions: a visible yellow line, never absent
            # (register #5 — a skipped condition must be seen to be skipped).
            if n_unparseable:
                items.append(SeverityItem(
                    level=SeverityLevel.yellow,
                    message=(
                        f"{symbol}: {n_unparseable} invalidation condition(s) NOT "
                        "MACHINE-CHECKED — manual review only"
                    ),
                    section=_SECTION,
                ))

            # Earnings risk
            next_ed = row.get("next_earnings_date")
            earnings_date = next_ed.date() if isinstance(next_ed, datetime) else next_ed
            earnings_item = earnings_risk(
                symbol,
                earnings_date,
                cgt_date=None,
                as_of=as_of,
                section=_SECTION,
            )
            if earnings_item:
                items.append(earnings_item)

            # Hidden risk alert
            hidden = detect_hidden_risk(row["status"], score)
            if hidden:
                items.append(SeverityItem(
                    level=SeverityLevel.yellow, message=hidden, section=_SECTION
                ))

    elapsed_ms = int(time.monotonic() * 1000) - start_ms
    return SectionResult(
        name=_SECTION, status=SectionStatus.ok,
        items=tuple(items), elapsed_ms=elapsed_ms,
    )
