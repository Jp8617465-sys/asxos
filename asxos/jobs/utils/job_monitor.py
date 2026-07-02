from datetime import date, datetime

import httpx

from asxos.db import acquire


class JobMonitor:
    """
    Async context manager — records job lifecycle to job_runs, pings Healthchecks.
    Never suppresses exceptions. Failure is recorded then re-raised.

    Status mapping (set in __aexit__):
      - no exception              → 'success' (pings the Healthchecks URL)
      - UpstreamBlocked raised    → 'blocked' (distinct from failure;
                                    upstream not ready, retry later;
                                    Healthchecks NOT pinged)
      - any other exception       → 'failure' (pings healthcheck_url + '/fail'
                                    — Healthchecks' explicit-failure signal;
                                    also marks the check for deadman purposes)

    The 'blocked' distinction prevents alert fatigue: the P0-1/P0-2 guards
    will generate many runs where the right operator response is "wait for
    the upstream to retry" rather than "page me, something is broken."

    The override_reason kwarg captures the audit trail when an operator
    bypasses a guard (e.g. --allow-stale-upstream). NULL on normal runs.
    """

    def __init__(
        self,
        job_name: str,
        as_of: date,
        healthcheck_url: str = "",
        override_reason: str | None = None,
    ) -> None:
        self.job_name = job_name
        self.as_of = as_of
        self.healthcheck_url = healthcheck_url
        self.override_reason = override_reason
        self.rows_written: int = 0
        self._started_at: datetime | None = None

    async def __aenter__(self) -> "JobMonitor":
        self._started_at = datetime.utcnow()
        async with acquire() as conn:
            # Stale-row reset + fresh INSERT are one atomic transaction so no
            # concurrent job instance can see a partially-updated state.
            async with conn.transaction():
                # Mark any prior crashed run failed before starting fresh.
                # Deliberately NOT scoped to as_of: a sync_financial_statements
                # run that crashed on 2026-06-27 sat at status='running' forever
                # because every later run's heal was scoped to its own as_of
                # (date.today()) and so could never touch the prior day's row.
                # Any 'running' row for this job older than 2 hours is stale.
                await conn.execute(
                    """
                    UPDATE job_runs SET
                        status        = 'failure',
                        finished_at   = NOW(),
                        error_message = 'prior run crashed (process never exited cleanly)'
                    WHERE job_name = $1
                      AND status   = 'running'
                      AND started_at < NOW() - INTERVAL '2 hours'
                    """,
                    self.job_name,
                )
                await conn.execute(
                    """
                    INSERT INTO job_runs
                        (job_name, as_of, status, started_at, override_reason)
                    VALUES ($1, $2, 'running', $3, $4)
                    ON CONFLICT (job_name, as_of) DO UPDATE SET
                        status          = 'running',
                        started_at      = EXCLUDED.started_at,
                        error_message   = NULL,
                        finished_at     = NULL,
                        rows_written    = NULL,
                        override_reason = EXCLUDED.override_reason
                    """,
                    self.job_name,
                    self.as_of,
                    self._started_at,
                    self.override_reason,
                )
        return self

    async def __aexit__(
        self,
        exc_type: type | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> bool:
        assert self._started_at is not None
        finished_at = datetime.utcnow()
        duration_ms = int((finished_at - self._started_at).total_seconds() * 1000)

        # Status mapping: UpstreamBlocked → 'blocked' (distinct from 'failure').
        # Check by __name__ to avoid importing job-specific exception types
        # into the shared monitor (would create a circular dep risk).
        if exc_type is None:
            status = "success"
        elif exc_type.__name__ == "UpstreamBlocked":
            status = "blocked"
        else:
            status = "failure"

        error_message = f"{exc_type.__name__}: {exc_val}" if exc_type else None

        async with acquire() as conn:
            await conn.execute(
                """
                UPDATE job_runs SET
                    status          = $1,
                    duration_ms     = $2,
                    rows_written    = $3,
                    error_message   = $4,
                    finished_at     = $5,
                    override_reason = $6
                WHERE job_name = $7 AND as_of = $8
                """,
                status,
                duration_ms,
                self.rows_written,
                error_message,
                finished_at,
                self.override_reason,
                self.job_name,
                self.as_of,
            )

        # Success pings the base URL. Blocked runs do NOT ping — the deadman
        # should miss so the "upstream stuck" pattern surfaces in monitoring.
        # Failures ping healthcheck_url + '/fail': ingest_regulatory failed 33
        # consecutive days in total silence because failures used to send no
        # signal at all and the deadman was never armed. '/fail' gives
        # Healthchecks an immediate explicit-failure signal AND still marks
        # the check for deadman purposes.
        if status == "success" and self.healthcheck_url:
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    await client.get(self.healthcheck_url)
            except Exception:
                pass  # ping failure never fails a successful job
        elif status == "failure" and self.healthcheck_url:
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    await client.get(self.healthcheck_url + "/fail")
            except Exception:
                pass  # ping failure must never mask the original job exception

        return False  # never suppress exceptions
