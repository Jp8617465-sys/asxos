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
            r.raise_for_status()
            return r.json()

    async def exchange_symbols(self, exchange: str = "AU") -> list[dict]:
        return await self._get(f"/exchange-symbol-list/{exchange}")

    async def daily_prices(self, symbol: str, *, from_date: str | None = None) -> list[dict]:
        params: dict[str, Any] = {}
        if from_date:
            params["from"] = from_date
        return await self._get(f"/eod/{symbol}", **params)

    async def daily_prices_bulk(self, exchange: str = "AU", *, date: str | None = None) -> list[dict]:
        params: dict[str, Any] = {}
        if date:
            params["date"] = date
        return await self._get(f"/eod-bulk-last-day/{exchange}", **params)

    async def fundamentals(self, symbol: str) -> dict:
        return await self._get(f"/fundamentals/{symbol}")


@lru_cache(maxsize=1)
def get_client() -> EODHDClient:
    return EODHDClient(api_key=settings.eodhd_api_key)
