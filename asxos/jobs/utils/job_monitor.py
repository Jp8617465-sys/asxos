from datetime import date, datetime

import httpx

from asxos.db import acquire


class JobMonitor:
    """
    Async context manager — records job lifecycle to job_runs, pings Healthchecks.
    Never suppresses exceptions. Failure is recorded then re-raised.

    Status mapping (set in __aexit__):
      - no exception              → 'success'
      - UpstreamBlocked raised    → 'blocked' (distinct from failure;
                                    upstream not ready, retry later;
                                    Healthchecks NOT pinged)
      - any other exception       → 'failure'

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
            # If a prior run of (job_name, as_of) is still 'running' after 2 hours
            # the process crashed without executing __aexit__. Mark it failed so
            # the dead row doesn't mask the fresh run.
            await conn.execute(
                """
                UPDATE job_runs SET
                    status        = 'failure',
                    finished_at   = NOW(),
                    error_message = 'prior run crashed (process never exited cleanly)'
                WHERE job_name = $1
                  AND as_of    = $2
                  AND status   = 'running'
                  AND started_at < NOW() - INTERVAL '2 hours'
                """,
                self.job_name,
                self.as_of,
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

        # Ping Healthchecks ONLY on full success. Blocked runs do NOT ping —
        # the deadman should miss so the "upstream stuck" pattern surfaces
        # in monitoring. Failures also don't ping (same as before).
        if status == "success" and self.healthcheck_url:
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    await client.get(self.healthcheck_url)
            except Exception:
                pass  # ping failure never fails a successful job

        return False  # never suppress exceptions
