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
  the packet hash, the render hash, the channel and the time. It is
  persisted into `brief_runs` (migration 0015) — the delivery ledger the
  brief already uses — under `snapshot_json.decision_delivery`, so no new
  table is needed this wave.
- `Disposition` is James's recorded reading of the packet (accept / request
  revision / reject / defer). It is a contract this wave; its append-only
  persistence is the 0052 migration's item (Wave 7), stated rather than
  smuggled in.
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
from datetime import UTC, date, datetime
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
DELIVERY_KEY: Final[str] = "decision_delivery"

Channel = Literal["cli", "email"]
DispositionVerdict = Literal["accept", "request_revision", "reject", "defer"]


class DeliveryReceipt(ContentAddressedContract):
    receipt_id: str = Field(min_length=1, max_length=200)
    decision_packet_id: str = Field(min_length=1, max_length=200)
    decision_content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    render_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    render_bytes: int = Field(gt=0)
    channel: Channel
    delivered_at: datetime
    resend_message_id: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def _validate(self) -> Self:
        if self.channel == "cli" and self.resend_message_id is not None:
            raise ValueError("a CLI delivery has no provider message id")
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
    resend_message_id: str | None = None,
) -> DeliveryReceipt:
    digest = render_sha256(html)
    return DeliveryReceipt(
        receipt_id=f"rcpt-{case.decision.decision_packet_id}-{channel}-{digest[:12]}",
        decision_packet_id=case.decision.decision_packet_id,
        decision_content_hash=case.decision.content_hash,
        render_sha256=digest,
        render_bytes=len(html.encode("utf-8")),
        channel=channel,
        delivered_at=require_utc(delivered_at, field_name="delivered_at"),
        resend_message_id=resend_message_id,
    )


def disposition_for(
    case: DecisionCase, *, verdict: DispositionVerdict, note: str, recorded_at: datetime
) -> Disposition:
    return Disposition(
        disposition_id=f"disp-{case.decision.decision_packet_id}-{verdict}",
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
    "INSERT INTO brief_runs (as_of, rendered_html, snapshot_json, section_runs, resend_message_id) "
    "VALUES ($1, $2, $3::jsonb, $4::jsonb, $5)"
)
SQL_LOAD_RECEIPTS: Final[str] = (
    "SELECT snapshot_json FROM brief_runs "
    f"WHERE snapshot_json->'{DELIVERY_KEY}'->>'decision_packet_id' = $1 ORDER BY composed_at"
)


async def persist_receipt(conn: ReceiptConn, receipt: DeliveryReceipt, html: str, *, as_of: date) -> None:
    """One `brief_runs` row per delivery, carrying the receipt and the exact render."""
    await conn.execute(
        SQL_INSERT_RECEIPT,
        as_of,
        html,
        json.dumps({DELIVERY_KEY: receipt.model_dump(mode="json")}),
        json.dumps({"decision_case": {"packet": receipt.decision_packet_id, "channel": receipt.channel}}),
        receipt.resend_message_id,
    )


def _snapshot(row: Mapping[str, object]) -> dict[str, Any]:
    raw = row["snapshot_json"]
    if isinstance(raw, str):
        return dict(json.loads(raw))
    if isinstance(raw, Mapping):
        return dict(raw)
    raise TypeError(f"unexpected snapshot_json column type: {type(raw)!r}")


async def load_receipts(conn: ReceiptConn, decision_packet_id: str) -> tuple[DeliveryReceipt, ...]:
    rows = await conn.fetch(SQL_LOAD_RECEIPTS, decision_packet_id)
    return tuple(DeliveryReceipt.model_validate(_snapshot(r)[DELIVERY_KEY]) for r in rows)


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
