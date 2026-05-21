#!/usr/bin/env python
"""
Daily morning-brief composer.

Collects, renders, sends, and prints. Wrapped in JobMonitor so failures
are recorded in job_runs and surface on the next day's brief.

Usage:
    python jobs/compose_brief.py                # send today's brief
    python jobs/compose_brief.py --as-of 2026-05-22
    python jobs/compose_brief.py --no-send      # render + stdout only
"""
import argparse
import asyncio
import logging
from datetime import date

from asxos.brief.compose import collect, render_html
from asxos.brief.email import send_brief
from asxos.config import settings
from asxos.db import close_pool, init_pool
from asxos.jobs.utils.job_monitor import JobMonitor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


async def main(as_of: date, send: bool) -> None:
    await init_pool()
    try:
        async with JobMonitor(
            job_name="compose_brief",
            as_of=as_of,
            healthcheck_url=settings.healthcheck_url_compose_brief,
        ) as monitor:
            data = await collect(as_of)
            html = render_html(data)
            print(html)

            if send:
                result = send_brief(html, as_of=as_of)
                log.info(f"sent to {result.to}: subject={result.subject} id={result.message_id}")
            else:
                log.info("--no-send: skipped Resend dispatch")

            monitor.rows_written = (
                len(data.signal_changes)
                + len(data.tax_actions)
                + len(data.regulatory_hits)
            )
    finally:
        await close_pool()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--as-of",
        type=date.fromisoformat,
        default=None,
        help="Brief date (YYYY-MM-DD). Defaults to today.",
    )
    parser.add_argument(
        "--no-send", action="store_true", help="Render + stdout only; skip Resend"
    )
    args = parser.parse_args()
    asyncio.run(main(args.as_of or date.today(), send=not args.no_send))
