"""The one Resend alert path for jobs. Never raises; never loses the outcome.

Six jobs each carried their own `_send_alert` — `check_au_positions`,
`check_us_positions`, `check_thesis_invalidations`, `check_cron_health`,
`score_macro_theses`, `validate_price_data` — and they had drifted into three
different contracts, which is the reason this module exists rather than pure
tidiness:

* two returned a failure note so a dead alerter left a trace in
  `job_runs.error_message`, redacted to the exception CLASS NAME;
* three swallowed the failure entirely, leaving a run that looked identical to
  one with nothing to report;
* one additionally `html.escape`d the body before it entered `<pre>`.

`tests/test_alert_send_observability.py` already stated the contract and fixed
the first two. This module is that contract in one place, applied to all of
them. Its rules, in the order they matter:

1. **Never raise.** A dead notification channel must not take down the check
   that found the problem.
2. **Never discard the outcome.** Silence from an alerting system being
   indistinguishable from good news is the one failure mode it cannot afford, so
   a failure is RETURNED for the caller to record on `JobMonitor.note`.
3. **Never return `str(exc)`.** A Resend/httpx error embeds the request URL and
   the API key travels with it; `job_runs` is queryable and agent-readable
   (CWE-532). Only the exception class name leaves this function.
4. **Escape the body.** It enters a `<pre>`, and some of these bodies carry
   external text — `job_runs.error_message` reaches `check_cron_health`'s alert,
   which is why that job escaped before this module existed.

The SDK call itself is delegated to `asxos.brief.email._send_via_resend`, the
repo's single Resend seam, so tests that stub `sys.modules["resend"]` keep
working and there is one place where the provider is actually touched.
"""
from __future__ import annotations

import html
import os

#: Returned when the channel is not configured at all. Deliberately distinct
#: from a send FAILURE: nothing was attempted, and on a runner without the
#: secrets this is expected rather than broken.
NOT_CONFIGURED = (
    "alert not sent: RESEND_API_KEY/BRIEF_TO_EMAIL/BRIEF_FROM_EMAIL not all set"
)


def send_alert(subject: str, body: str) -> str | None:
    """Send a plain-text alert body as an escaped `<pre>` email.

    Returns None on success, or a short note describing why it did not send.
    Never raises. The note is safe to store: it carries no secret and no
    external text, only `NOT_CONFIGURED` or an exception class name.
    """
    api_key = os.environ.get("RESEND_API_KEY", "")
    to = os.environ.get("BRIEF_TO_EMAIL", "")
    sender = os.environ.get("BRIEF_FROM_EMAIL", "")
    if not (api_key and to and sender):
        return NOT_CONFIGURED

    try:
        # Imported here, not at module scope: `asxos.brief.email` pulls
        # pydantic-settings, and this module is imported by jobs that run
        # without the BRIEF_* env vars set.
        from asxos.brief.email import _send_via_resend

        _send_via_resend(
            api_key=api_key,
            from_address=sender,
            to_address=to,
            subject=subject,
            html=f"<pre>{html.escape(body)}</pre>",
        )
    except Exception as exc:
        return f"alert send failed: {type(exc).__name__}"
    return None
