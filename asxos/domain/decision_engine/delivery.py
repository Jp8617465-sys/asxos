"""Stage 4 delivery — identical render, delivery receipt, disposition, paper intent.

`target-architecture.md` §15 Stage 4 chain, after the immutable
`DecisionPacket`: *identical CLI/email render → DeliveryReceipt → James
Disposition → paper intent*. This module is that tail:

- `render_decision_case()` is the ONE renderer. The CLI prints its output and
  the email sends the same string, so the two channels are identical by
  construction and the `DeliveryReceipt` carries one `render_sha256`. The
  renderer contains no financial logic: every figure is read from the
  packet; the only derivation is `renderer.presentation_for` (tone / label).
- `DeliveryReceipt` is content-addressed and records the packet identity,
  the packet hash, the render hash, the channel, the time and the exact
  rendered bytes, in its own append-only `delivery_receipts` table
  (migration 0052). It was briefly written into `brief_runs` instead, to
  avoid opening a migration; that was wrong. `asxos/brief/deltas.py`'s
  `_PRIOR_BRIEF_SQL` takes the most recent `brief_runs` row with
  `as_of < $1` and does not filter on row kind, so a receipt was returned
  as "the prior brief" and skewed the brief's since-last timestamp. Nothing
  in this module touches `brief_runs`; `load_receipts` re-hashes the stored
  bytes and refuses a row whose `render_sha256` no longer matches them.
- `Disposition` is James's recorded reading of the packet (accept / request
  revision / reject / defer), persisted append-only in
  `decision_dispositions` (migration 0052) and bound to the packet's
  content hash, so a disposition cannot silently follow a changed packet.
- `PaperIntent` exists only for an ACTION state with an accepting
  disposition — which no packet can reach until tax readiness is earned
  (G12) — so `paper_intent_for()` returns `None` for every packet this
  wave can produce. That is the honest Stage 4 end state, not a gap.

Rule #11: nothing here reads `signals` or imports `asxos.domain.models`.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final, Literal, Protocol, Self

import jinja2
from pydantic import Field, model_validator

from asxos.domain.decision_engine.renderer import presentation_for
from asxos.domain.decision_engine.types import (
    ACTION_STATES,
    ContentAddressedContract,
    DecisionCase,
    require_utc,
)

_TEMPLATE_DIR: Final = Path(__file__).parent.parent.parent / "brief" / "templates"
_TEMPLATE_NAME: Final[str] = "decision_case.html.j2"

Channel = Literal["cli", "email"]
DeliveryStatus = Literal["pending", "sent", "failed"]
DispositionVerdict = Literal["accept", "request_revision", "reject", "defer"]


class DeliveryReceipt(ContentAddressedContract):
    receipt_id: str = Field(min_length=1, max_length=200)
    decision_packet_id: str = Field(min_length=1, max_length=200)
    decision_content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    render_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    render_bytes: int = Field(gt=0)
    channel: Channel
    delivered_at: datetime
    delivery_status: DeliveryStatus = "sent"
    resend_message_id: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def _validate(self) -> Self:
        if self.channel == "cli" and self.resend_message_id is not None:
            raise ValueError("a CLI delivery has no provider message id")
        if self.channel == "cli" and self.delivery_status != "sent":
            raise ValueError("a CLI delivery is recorded only after it is shown")
        if self.channel == "email":
            if self.delivery_status == "sent" and self.resend_message_id is None:
                raise ValueError("a sent email delivery requires the provider message id")
            if self.delivery_status != "sent" and self.resend_message_id is not None:
                raise ValueError("a pending or failed email has no provider message id")
        return self


class Disposition(ContentAddressedContract):
    disposition_id: str = Field(min_length=1, max_length=200)
    decision_packet_id: str = Field(min_length=1, max_length=200)
    decision_content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    verdict: DispositionVerdict
    note: str = Field(min_length=1, max_length=10_000)
    recorded_by: Literal["james"] = "james"
    recorded_at: datetime


class PaperIntent(ContentAddressedContract):
    """A paper (never real) intent, constructable only for an action state."""

    intent_id: str = Field(min_length=1, max_length=200)
    decision_packet_id: str = Field(min_length=1, max_length=200)
    disposition_id: str = Field(min_length=1, max_length=200)
    recommendation_state: str = Field(min_length=1, max_length=40)
    paper_only: Literal[True] = True
    created_at: datetime

    @model_validator(mode="after")
    def _validate(self) -> Self:
        if self.recommendation_state not in ACTION_STATES:
            raise ValueError("a paper intent requires an action state")
        return self


def render_decision_case(case: DecisionCase, *, evaluated_at: datetime) -> str:
    """The one render. Revalidates the case, derives presentation only."""
    rendered_at = require_utc(evaluated_at, field_name="evaluated_at")
    admitted = DecisionCase.model_validate(case.model_dump(mode="python"))
    presentation = presentation_for(admitted.decision, evaluated_at=rendered_at)
    environment = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=jinja2.select_autoescape(enabled_extensions=("html", "html.j2", "xml"), default=True),
        undefined=jinja2.StrictUndefined,
    )
    return environment.get_template(_TEMPLATE_NAME).render(
        case=admitted, presentation=presentation, rendered_at=rendered_at
    )


def render_sha256(html: str) -> str:
    return hashlib.sha256(html.encode("utf-8")).hexdigest()


def receipt_for(
    case: DecisionCase,
    html: str,
    *,
    channel: Channel,
    delivered_at: datetime,
    delivery_status: DeliveryStatus = "sent",
    resend_message_id: str | None = None,
) -> DeliveryReceipt:
    digest = render_sha256(html)
    delivered_at = require_utc(delivered_at, field_name="delivered_at")
    return DeliveryReceipt(
        # The instant is part of the identity: two deliveries of the same bytes
        # on the same channel are two FACTS for a provability ledger, and an id
        # that omitted the time made the second one vanish into ON CONFLICT.
        receipt_id=(
            f"rcpt-{case.decision.decision_packet_id}-{channel}-"
            f"{delivery_status}-{delivered_at.strftime('%Y%m%dT%H%M%SZ')}-{digest[:12]}"
        ),
        decision_packet_id=case.decision.decision_packet_id,
        decision_content_hash=case.decision.content_hash,
        render_sha256=digest,
        render_bytes=len(html.encode("utf-8")),
        channel=channel,
        delivered_at=require_utc(delivered_at, field_name="delivered_at"),
        delivery_status=delivery_status,
        resend_message_id=resend_message_id,
    )


def disposition_for(
    case: DecisionCase, *, verdict: DispositionVerdict, note: str, recorded_at: datetime
) -> Disposition:
    recorded_at = require_utc(recorded_at, field_name="recorded_at")
    return Disposition(
        # Same reasoning as the receipt id: a second `defer` after new
        # information is a new decision, not a duplicate of the first.
        disposition_id=(
            f"disp-{case.decision.decision_packet_id}-{verdict}-"
            f"{recorded_at.strftime('%Y%m%dT%H%M%SZ')}"
        ),
        decision_packet_id=case.decision.decision_packet_id,
        decision_content_hash=case.decision.content_hash,
        verdict=verdict,
        note=note,
        recorded_at=require_utc(recorded_at, field_name="recorded_at"),
    )


def paper_intent_for(case: DecisionCase, disposition: Disposition, *, created_at: datetime) -> PaperIntent | None:
    """None unless the packet is in an action state AND James accepted it."""
    if disposition.decision_packet_id != case.decision.decision_packet_id:
        raise ValueError("disposition does not reference this packet")
    if disposition.decision_content_hash != case.decision.content_hash:
        raise ValueError("disposition was recorded against a different packet content")
    if disposition.verdict != "accept" or case.decision.recommendation_state not in ACTION_STATES:
        return None
    return PaperIntent(
        intent_id=f"intent-{case.decision.decision_packet_id}",
        decision_packet_id=case.decision.decision_packet_id,
        disposition_id=disposition.disposition_id,
        recommendation_state=case.decision.recommendation_state,
        created_at=require_utc(created_at, field_name="created_at"),
    )


class ReceiptConn(Protocol):
    async def execute(self, query: str, *args: object) -> str: ...
    async def fetch(self, query: str, *args: object) -> list[Any]: ...


SQL_INSERT_RECEIPT: Final[str] = (
    "INSERT INTO delivery_receipts (receipt_id, content_hash, decision_packet_id, "
    "decision_content_hash, render_sha256, render_bytes, channel, delivered_at, "
    "resend_message_id, rendered_html, payload) "
    "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11::jsonb) "
    "ON CONFLICT (receipt_id) DO NOTHING"
)
SQL_LOAD_RECEIPTS: Final[str] = (
    "SELECT payload, rendered_html FROM delivery_receipts "
    "WHERE decision_packet_id = $1 ORDER BY delivered_at, receipt_id"
)
SQL_INSERT_DISPOSITION: Final[str] = (
    "INSERT INTO decision_dispositions (disposition_id, content_hash, decision_packet_id, "
    "decision_content_hash, verdict, recorded_at, payload) "
    "VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb) "
    "ON CONFLICT (disposition_id) DO NOTHING"
)
SQL_LOAD_DISPOSITIONS: Final[str] = (
    "SELECT payload FROM decision_dispositions "
    "WHERE decision_packet_id = $1 ORDER BY recorded_at, disposition_id"
)


class ReceiptIntegrityError(RuntimeError):
    """A stored render no longer hashes to the digest its receipt claims."""


def _payload(row: Mapping[str, object]) -> dict[str, Any]:
    raw = row["payload"]
    if isinstance(raw, str):
        return dict(json.loads(raw))
    if isinstance(raw, Mapping):
        return dict(raw)
    raise TypeError(f"unexpected payload column type: {type(raw)!r}")


async def persist_receipt(conn: ReceiptConn, receipt: DeliveryReceipt, html: str) -> None:
    """One `delivery_receipts` row per delivery, carrying the exact bytes sent."""
    if render_sha256(html) != receipt.render_sha256:
        raise ReceiptIntegrityError(
            f"receipt {receipt.receipt_id} does not describe the supplied render"
        )
    await conn.execute(
        SQL_INSERT_RECEIPT,
        receipt.receipt_id, receipt.content_hash, receipt.decision_packet_id,
        receipt.decision_content_hash, receipt.render_sha256, receipt.render_bytes,
        receipt.channel, receipt.delivered_at, receipt.resend_message_id, html,
        json.dumps(receipt.model_dump(mode="json")),
    )


async def load_receipts(conn: ReceiptConn, decision_packet_id: str) -> tuple[DeliveryReceipt, ...]:
    """Every delivery of one packet. Re-hashes the stored bytes rather than
    trusting the recorded digest — a receipt whose render has drifted is a
    corrupted record of what James saw, and is refused loudly."""
    out: list[DeliveryReceipt] = []
    for row in await conn.fetch(SQL_LOAD_RECEIPTS, decision_packet_id):
        receipt = DeliveryReceipt.model_validate(_payload(row))
        stored = row["rendered_html"]
        if not isinstance(stored, str) or render_sha256(stored) != receipt.render_sha256:
            raise ReceiptIntegrityError(
                f"stored render for {receipt.receipt_id} does not match its recorded sha256"
            )
        out.append(receipt)
    return tuple(out)


async def persist_disposition(conn: ReceiptConn, disposition: Disposition) -> None:
    await conn.execute(
        SQL_INSERT_DISPOSITION,
        disposition.disposition_id, disposition.content_hash, disposition.decision_packet_id,
        disposition.decision_content_hash, disposition.verdict, disposition.recorded_at,
        json.dumps(disposition.model_dump(mode="json")),
    )


async def load_dispositions(conn: ReceiptConn, decision_packet_id: str) -> tuple[Disposition, ...]:
    rows = await conn.fetch(SQL_LOAD_DISPOSITIONS, decision_packet_id)
    return tuple(Disposition.model_validate(_payload(r)) for r in rows)


def send_decision_case(html: str, *, case: DecisionCase) -> str | None:
    """Email the SAME render through the brief's Resend path. Returns the provider id."""
    from asxos.brief.email import _EmailSettings, _send_via_resend

    settings = _EmailSettings()  # type: ignore[call-arg]
    if not (settings.brief_to_email and settings.brief_from_email and settings.resend_api_key):
        raise RuntimeError("decision send refused: BRIEF_TO_EMAIL / BRIEF_FROM_EMAIL / RESEND_API_KEY must all be set")
    return _send_via_resend(
        api_key=settings.resend_api_key,
        from_address=settings.brief_from_email,
        to_address=settings.brief_to_email,
        subject=f"asxos decision case — {case.thesis.security_id} — {case.evidence.as_of.isoformat()}",
        html=html,
    )


def now_utc() -> datetime:
    return datetime.now(UTC)
