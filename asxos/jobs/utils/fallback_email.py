"""
Fallback email helper — last-resort failure notification.

Used by compose_brief when the main brief pipeline raises. Designed to be
reusable by future jobs (e.g. P1-4 cron staleness alert).

Design constraints:
  - Synchronous (matches the sync Resend SDK in asxos/brief/email.py).
  - Bypasses jinja templates, BriefData, collect(), send_brief() — must not
    depend on whatever broke.
  - Lazy imports — keeps this module importable in test environments without
    BRIEF_* env vars set.
  - Never raises. On Resend / settings failure, attempts to write a synthetic
    job_runs row so the next morning's brief surfaces the dispatch failure.
    If even that fails, prints to stderr — there is nothing more to fall
    back to.
"""
from __future__ import annotations

import asyncio
import html
import logging
import sys
from datetime import date, datetime

log = logging.getLogger(__name__)


def send_fallback_email(*, subject: str, body_text: str) -> None:
    """Send a minimal HTML-wrapped-plaintext email via Resend.

    Args:
        subject: Full subject line (caller supplies decoration like "[asxos]").
        body_text: Plain text body. Wrapped in <pre> for monospace rendering
            and html.escape()'d to neutralise any injection in error messages.

    Never raises. On any failure, attempts an in-band signal via job_runs.
    """
    try:
        # Lazy imports — keeps this module importable in test envs without
        # BRIEF_* env vars set (BriefSettings() raises at import otherwise).
        from asxos.brief.email import _send_via_resend
        from asxos.config import BriefSettings

        settings = BriefSettings()  # type: ignore[call-arg]  # pydantic-settings reads from env vars
        body_html = (
            "<html><body>"
            '<pre style="font-family: monospace; white-space: pre-wrap;">'
            f"{html.escape(body_text)}"
            "</pre></body></html>"
        )
        _send_via_resend(
            api_key=settings.resend_api_key,
            from_address=settings.brief_from_email,
            to_address=settings.brief_to_email,
            subject=subject,
            html=body_html,
        )
        log.info("fallback email sent: subject=%r", subject)
    except Exception as exc:
        log.exception("fallback email failed: %s", exc)
        try:
            asyncio.run(_record_fallback_failure(subject=subject, error=repr(exc)))
        except Exception as inner:
            print(
                f"FATAL: fallback email AND job_runs record both failed: "
                f"primary={exc!r} secondary={inner!r}",
                file=sys.stderr,
            )


async def _record_fallback_failure(*, subject: str, error: str) -> None:
    """Write a synthetic job_runs row so the failure surfaces in-band.

    Uses ``job_name='fallback_email_dispatch'`` and today's date so the
    next morning's brief / health query picks it up. Truncates the error
    message to 1000 chars to avoid degenerate inputs swamping job_runs.
    """
    from asxos.db import acquire, close_pool, init_pool

    await init_pool()
    try:
        async with acquire() as conn:
            now = datetime.utcnow()
            err_message = (
                f"fallback_email dispatch failed: subject={subject!r} "
                f"error={error}"
            )[:1000]
            await conn.execute(
                """
                INSERT INTO job_runs
                    (job_name, as_of, status, started_at, finished_at,
                     error_message, rows_written, duration_ms)
                VALUES ($1, $2, 'failure', $3, $3, $4, 0, 0)
                ON CONFLICT (job_name, as_of) DO UPDATE SET
                    status        = 'failure',
                    error_message = EXCLUDED.error_message,
                    finished_at   = EXCLUDED.finished_at
                """,
                "fallback_email_dispatch",
                date.today(),
                now,
                err_message,
            )
    finally:
        await close_pool()
