"""
Resend dispatch for the morning brief.

Wraps the Resend Python SDK. Test seam: the SDK call is isolated in
`_send_via_resend` so tests can patch it.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from asxos.config import BriefSettings

settings = BriefSettings()  # type: ignore[call-arg]  # pydantic-settings reads from env vars; hard-fails if absent


@dataclass(frozen=True)
class SendResult:
    message_id: str | None
    to: str
    subject: str


def send_brief(html: str, *, as_of: date) -> SendResult:
    subject = f"asxos brief — {as_of.isoformat()}"
    to = settings.brief_to_email
    sender = settings.brief_from_email
    if not (to and sender and settings.resend_api_key):
        raise RuntimeError(
            "brief send refused: BRIEF_TO_EMAIL / BRIEF_FROM_EMAIL / RESEND_API_KEY must all be set"
        )

    message_id = _send_via_resend(
        api_key=settings.resend_api_key,
        from_address=sender,
        to_address=to,
        subject=subject,
        html=html,
    )
    return SendResult(message_id=message_id, to=to, subject=subject)


def _send_via_resend(
    *, api_key: str, from_address: str, to_address: str, subject: str, html: str
) -> str | None:
    """Thin wrapper around the Resend SDK. Returns the provider message id
    on success. Isolated so tests can monkeypatch this without touching
    real Resend infrastructure."""
    import resend

    resend.api_key = api_key
    resp = resend.Emails.send(
        {
            "from": from_address,
            "to": to_address,
            "subject": subject,
            "html": html,
        }
    )
    if isinstance(resp, dict):
        return resp.get("id")
    return None
