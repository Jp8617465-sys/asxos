from datetime import date, datetime

import httpx

from asxos.db import acquire


class JobMonitor:
    """
    Async context manager — records job lifecycle to job_runs, pings Healthchecks.
    Never suppresses exceptions. Failure is recorded then re-raised.
    """

    def __init__(self, job_name: str, as_of: date, healthcheck_url: str = "") -> None:
        self.job_name = job_name
        self.as_of = as_of
        self.healthcheck_url = healthcheck_url
        self.rows_written: int = 0
        self._started_at: datetime | None = None

    async def __aenter__(self) -> "JobMonitor":
        self._started_at = datetime.utcnow()
        async with acquire() as conn:
            await conn.execute(
                """
                INSERT INTO job_runs (job_name, as_of, status, started_at)
                VALUES ($1, $2, 'running', $3)
                ON CONFLICT (job_name, as_of) DO UPDATE SET
                    status        = 'running',
                    started_at    = EXCLUDED.started_at,
                    error_message = NULL,
                    finished_at   = NULL,
                    rows_written  = NULL
                """,
                self.job_name,
                self.as_of,
                self._started_at,
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

        status = "success" if exc_type is None else "failure"
        error_message = f"{exc_type.__name__}: {exc_val}" if exc_type else None

        async with acquire() as conn:
            await conn.execute(
                """
                UPDATE job_runs SET
                    status        = $1,
                    duration_ms   = $2,
                    rows_written  = $3,
                    error_message = $4,
                    finished_at   = $5
                WHERE job_name = $6 AND as_of = $7
                """,
                status,
                duration_ms,
                self.rows_written,
                error_message,
                finished_at,
                self.job_name,
                self.as_of,
            )

        if exc_type is None and self.healthcheck_url:
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    await client.get(self.healthcheck_url)
            except Exception:
                pass  # ping failure never fails a successful job

        return False  # never suppress exceptions
