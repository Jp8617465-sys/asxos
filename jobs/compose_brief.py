#!/usr/bin/env python
"""
Daily morning-brief composer.

Collects, renders, sends, and prints. Wrapped in JobMonitor so failures
are recorded in job_runs and surface on the next day's brief.

Usage:
    python jobs/compose_brief.py                # send today's brief
    python jobs/compose_brief.py --as-of 2026-05-22
    python jobs/compose_brief.py --no-send      # render + stdout only

M-Brief-Skeleton refactor: uses domain.brief.composer.compose() which
orchestrates V2 collectors and persists to brief_runs. V1 rendering
path is preserved — email HTML is identical to pre-refactor output.
"""

import argparse
import asyncio
import logging
import traceback
from datetime import date

from asxos import clock

# Stage 2 send path: hydrate gold artefacts and render the live brief.
# Never calls collect() here — materialise_brief_sections owns collect/persist.
from asxos.brief.compose import render_html
from asxos.brief.gold import hydrate, is_undefined_table

# Module-level stubs — tests patch these at the jobs.compose_brief namespace.
# Production main() lazy-imports the real implementations on first use.
# This mirrors jobs/ingest_news.py and keeps the module importable in test
# environments that lack the full prod dep tree (pydantic_settings, resend).
init_pool = None  # type: ignore[assignment]
close_pool = None  # type: ignore[assignment]
JobMonitor = None  # type: ignore[assignment]
send_brief = None  # type: ignore[assignment]
send_fallback_email = None  # type: ignore[assignment]
settings = None  # type: ignore[assignment]
acquire = None  # type: ignore[assignment]

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


async def _persist_brief_run(conn: object, as_of: date, html: str) -> None:
    """Best-effort INSERT of as_of + rendered_html. Never writes V2 snapshot_json.

    Undefined table (or any insert error) is logged and skipped so a missing
    brief_runs row cannot take down a successful send.
    """
    try:
        await conn.execute(  # type: ignore[union-attr]
            "INSERT INTO brief_runs (as_of, rendered_html) VALUES ($1, $2)",
            as_of,
            html,
        )
    except Exception as exc:
        if is_undefined_table(exc):
            log.warning("brief_runs is absent; skipping persist")
            return
        log.warning("brief_runs persist skipped: %s", exc)


async def main(as_of: date, send: bool) -> None:
    # Personal-use firewall, top-level (Part 0 Q1 / CLAUDE.md #10). The brief's
    # sections already self-gate at the data layer (compose.py checks
    # ASXOS_PERSONAL_USE per section), so this is defense-in-depth — one loud
    # gate ahead of any collection rather than N quiet per-section skips
    # (07-18 audit P1 #2). Lazy import keeps the module importable in test
    # envs lacking the prod dep tree, same as the stubs below.
    from asxos.jobs._helpers import require_personal_use_job

    require_personal_use_job()

    # Resolve module-level stubs: tests inject mocks (non-None); production
    # lazy-imports the real implementations here.
    _init_pool = globals()["init_pool"]
    _close_pool = globals()["close_pool"]
    _JobMonitor = globals()["JobMonitor"]
    _send_brief = globals()["send_brief"]
    _send_fallback_email = globals()["send_fallback_email"]
    _settings = globals()["settings"]
    _acquire = globals()["acquire"]

    if _init_pool is None:
        from asxos.db import close_pool as _close_pool  # type: ignore[assignment]
        from asxos.db import init_pool as _init_pool  # type: ignore[assignment]
    if _JobMonitor is None:
        from asxos.jobs.utils.job_monitor import (
            JobMonitor as _JobMonitor,  # type: ignore[assignment]
        )
    if _send_brief is None:
        from asxos.brief.email import send_brief as _send_brief  # type: ignore[assignment]
    if _send_fallback_email is None:
        from asxos.jobs.utils.fallback_email import (  # type: ignore[assignment]
            send_fallback_email as _send_fallback_email,
        )
    if _settings is None:
        from asxos.config import settings as _settings  # type: ignore[assignment]
    if _acquire is None:
        from asxos.db import acquire as _acquire  # type: ignore[assignment]

    await _init_pool()
    try:
        primary_delivered = False
        # Outer try wraps the entire JobMonitor block. Failures before primary
        # delivery produce a fallback; failures after a confirmed primary send
        # still make the job red without sending a duplicate email.
        try:
            async with _JobMonitor(
                job_name="compose_brief",
                as_of=as_of,
                healthcheck_url=_settings.healthcheck_url_compose_brief,
            ) as monitor:
                async with _acquire() as conn:
                    data = await hydrate(conn, as_of)
                    html = render_html(data)
                    print(html)

                    if send:
                        result = _send_brief(html, as_of=as_of)
                        primary_delivered = True
                        log.info(
                            f"sent to {result.to}: subject={result.subject} id={result.message_id}"
                        )
                    else:
                        log.info("--no-send: skipped Resend dispatch")

                    await _persist_brief_run(conn, as_of, html)
                    monitor.rows_written = len(data.sections)
        # asyncio.CancelledError is a BaseException in Py3.12; asyncpg pool
        # timeouts in collect() propagate as CancelledError and would slip
        # past a bare `except Exception:`.
        except (Exception, asyncio.CancelledError) as exc:
            log.exception("compose_brief failed")
            if send and not primary_delivered:
                # Tail of traceback — Render log retention is finite, so the
                # email is the durable record. ~3.5KB keeps the total body
                # under ~4KB once HTML-escaped + wrapped.
                tb = traceback.format_exc()[-3500:]
                _send_fallback_email(
                    subject=f"[asxos] Brief composition FAILED — {as_of.isoformat()}",
                    body_text=(
                        f"The morning brief failed to compose for {as_of.isoformat()}.\n\n"
                        f"Exception: {type(exc).__name__}: {exc}\n\n"
                        f"Traceback (tail):\n{tb}\n\n"
                        "Render log retention is finite; the traceback above is the full record."
                    ),
                )
            elif send:
                log.error(
                    "failure occurred after confirmed primary delivery; duplicate fallback "
                    "suppressed"
                )
            raise  # JobMonitor (if it survived) records failure; cron exits non-zero
    finally:
        await _close_pool()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--as-of",
        type=date.fromisoformat,
        default=None,
        help="Brief date (YYYY-MM-DD). Defaults to today.",
    )
    parser.add_argument("--no-send", action="store_true", help="Render + stdout only; skip Resend")
    args = parser.parse_args()
    asyncio.run(main(args.as_of or clock.today(), send=not args.no_send))
