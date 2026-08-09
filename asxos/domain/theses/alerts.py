"""Invalidation alert builder — attestation / semantics / lock aware (0042, §5).

Wording rules (binding, design §5):
  Action verbs ("Run: asx thesis exit …") appear IFF
      attestation == 'underwritten'
      AND trigger_semantics == 'hard_exit'
      AND the instrument is not disposal-locked.
  Otherwise the alert is REVIEW-framed, with the demotion reason printed on
  the face:
      "PLACEHOLDER — not underwritten"                     (D4/R9)
      "INSTRUMENT LOCKED (…) — review only"                (KD-2/KD-3)

The body is html.escape()d here (closes the synthesis §7 <pre>{body}</pre>
injection note) — the job may interpolate Alert.body straight into
``<pre>…</pre>`` without further escaping. The subject line is a plain
email header, not HTML, and is left raw.

Pure module: no DB, no I/O — the caller passes row mappings + a LockState.
"""
from __future__ import annotations

import html
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from asxos.domain.portfolio.locks import LockState


@dataclass(frozen=True)
class Alert:
    subject: str
    body: str  # HTML-escaped — safe inside <pre>…</pre>
    action_framed: bool


def build_invalidation_alert(
    thesis: Mapping[str, Any],
    condition: Mapping[str, Any],
    event: Mapping[str, Any],
    lock: LockState | None,
) -> Alert:
    """Build the invalidation email for one triggered condition.

    Args:
        thesis:    mapping with symbol, thesis_id, attestation.
        condition: mapping with condition_text, trigger_semantics.
        event:     mapping with price_date (the CLOSE's dt, never the run
                   date — register #21), observed_close, threshold.
        lock:      LockState if the symbol is disposal-locked as of the run
                   date, else None (see portfolio.locks.get_disposal_locks).
    """
    symbol = thesis["symbol"]
    thesis_id = thesis["thesis_id"]
    attestation = thesis["attestation"]
    semantics = condition["trigger_semantics"]
    locked = lock is not None

    action_framed = attestation == "underwritten" and semantics == "hard_exit" and not locked

    lines = [
        f"{symbol} invalidation condition triggered:",
        "",
        f"  • {condition['condition_text']}",
        f"    close={event['observed_close']} on {event['price_date']} "
        f"(threshold {event['threshold']})",
        "",
    ]

    if action_framed:
        lines.append("Review thesis and consider exit.")
        lines.append(f"Run: asx thesis exit {symbol}")
    else:
        # Demotion reasons on the face — never a silently softened alert.
        if attestation != "underwritten":
            lines.append("PLACEHOLDER — not underwritten")
        if locked and lock is not None:
            end_phrase = f"until {lock.lock_end}" if lock.lock_end else "end unknown"
            lines.append(f"INSTRUMENT LOCKED ({end_phrase}) — review only")
            if lock.lock_note:
                lines.append(f"  lock note: {lock.lock_note}")
        if attestation == "underwritten" and not locked and semantics != "hard_exit":
            lines.append("alert_review semantics — review only")
        lines.append("")
        lines.append(f"Review thesis #{thesis_id}: asx thesis show {symbol}")

    subject = f"asxos [INVALIDATION] {symbol} — {event['price_date']}"
    return Alert(
        subject=subject,
        body=html.escape("\n".join(lines)),
        action_framed=action_framed,
    )
