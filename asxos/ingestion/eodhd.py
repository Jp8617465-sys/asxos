"""
EODHD async client. One instance per process via get_client().
Rate-limited via semaphore. Retries on transient errors.
"""
from __future__ import annotations

import asyncio
from functools import lru_cache
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from asxos.config import settings
from asxos.redaction import sanitized_http_error

_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in _RETRYABLE_STATUS
    return isinstance(exc, httpx.RequestError)


class EODHDClient:
    BASE = "https://eodhd.com/api"

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._sem = asyncio.Semaphore(10)  # max 10 concurrent requests
        self._client = httpx.AsyncClient(timeout=60.0)

    async def close(self) -> None:
        await self._client.aclose()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=1, max=10),
        retry=retry_if_exception(_is_retryable),
        reraise=True,
    )
    async def _get(self, path: str, **params: Any) -> Any:
        async with self._sem:
            r = await self._client.get(
                f"{self.BASE}{path}",
                params={"api_token": self._api_key, "fmt": "json", **params},
            )
            try:
                r.raise_for_status()
            except httpx.HTTPStatusError as exc:
                # Strip the api_token before the error can reach any log or
                # job_runs (CWE-532). `from None` suppresses the original in
                # tracebacks; type + response are preserved so the tenacity
                # retry predicate still classifies the status.
                raise sanitized_http_error(exc) from None
            return r.json()

    async def exchange_symbols(self, exchange: str = "AU") -> list[dict[str, Any]]:
        return await self._get(f"/exchange-symbol-list/{exchange}")  # type: ignore[no-any-return]

    async def exchange_symbols_delisted(self, exchange: str = "AU") -> list[dict[str, Any]]:
        # `delisted=1` returns securities no longer trading (survivorship-free
        # research store). Probe 2026-06-24: AU returns 1,986 rows. The payload
        # carries no delisted-date field — callers must set delisted_date = NULL.
        return await self._get(f"/exchange-symbol-list/{exchange}", delisted=1)  # type: ignore[no-any-return]

    async def daily_prices(self, symbol: str, *, from_date: str | None = None) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}
        if from_date:
            params["from"] = from_date
        result = await self._get(f"/eod/{symbol}", **params)
        # Same list guard as news_for_symbol/sentiments_for_symbol: a no-data or
        # error response can come back as {} — coerce to [] so the per-symbol
        # parsers (to_us_price_rows / to_fx_rows) never see a non-list.
        return result if isinstance(result, list) else []

    async def daily_prices_bulk(self, exchange: str = "AU", *, date: str | None = None) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}
        if date:
            params["date"] = date
        return await self._get(f"/eod-bulk-last-day/{exchange}", **params)  # type: ignore[no-any-return]

    async def fundamentals(self, symbol: str) -> dict[str, Any]:
        return await self._get(f"/fundamentals/{symbol}")  # type: ignore[no-any-return]

    async def dividends(self, symbol: str) -> list[dict[str, Any]]:
        # Per-share dividend history. Each object: date (ex-date), value,
        # unadjustedValue, paymentDate, recordDate, period, currency, and (AU only)
        # franking as a "<float>%" string. No-dividend names return []. Probe 2026-06-24.
        return await self._get(f"/div/{symbol}")  # type: ignore[no-any-return]

    async def splits(self, symbol: str) -> list[dict[str, Any]]:
        # Split history. Each object: date (ex-date), split = "new/old" string
        # (e.g. "4.000000/1.000000" = 4:1). No-split names return []. Probe 2026-06-24.
        return await self._get(f"/splits/{symbol}")  # type: ignore[no-any-return]

    async def news_for_symbol(
        self,
        symbol: str,
        *,
        limit: int = 10,
        from_date: str | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch recent news headlines for a single symbol from EODHD /news.

        EODHD returns a list directly (unlike most endpoints that return a dict).
        The isinstance guard converts a no-data ``{}`` response to ``[]``.
        """
        params: dict[str, Any] = {"s": symbol, "limit": limit}
        if from_date:
            params["from"] = from_date
        result = await self._get("/news", **params)
        return result if isinstance(result, list) else []

    async def sentiments_for_symbol(
        self,
        symbol: str,
        *,
        from_date: str,
        to_date: str,
    ) -> list[dict[str, Any]]:
        """Fetch daily aggregated sentiment from EODHD /sentiments (M14b).

        Returns list of {date, count, normalized} dicts.
        ``normalized`` ∈ [−1, +1] is the daily-aggregated sentiment score.
        ``count`` is the number of news mentions that day (a volume signal).

        Ref: https://eodhd.com/lp/fundamental-data-api
        Same isinstance list guard as news_for_symbol().
        """
        params: dict[str, Any] = {"s": symbol, "from": from_date, "to": to_date}
        result = await self._get("/sentiments", **params)
        return result if isinstance(result, list) else []


@lru_cache(maxsize=1)
def get_client() -> EODHDClient:
    if not settings.eodhd_api_key:
        raise RuntimeError(
            "EODHD_API_KEY is not set — this job requires it. "
            "Set it on the Render service (Environment tab) or via fromService "
            "reference from asxos-api."
        )
    return EODHDClient(api_key=settings.eodhd_api_key)
