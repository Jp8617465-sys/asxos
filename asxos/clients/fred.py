"""
FRED (Federal Reserve Economic Data) async client.
One instance per process via get_client().
Mirrors EODHDClient structure: semaphore, tenacity retry, lru_cache factory.

Key series used by this project:
  BAMLH0A0HYM2  — US High-Yield Corporate OAS (basis points)
  T10Y2Y        — 10Y-2Y Treasury spread (percentage points)
  IRLTLT01AUM156N — Australia long-term government bond yield (%, monthly)
  AUCBCNTO      — Australia overnight call money rate (%, monthly)
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from functools import lru_cache

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


@dataclass(frozen=True)
class FREDObservation:
    date: date
    value: Decimal | None  # None when FRED returns "." (missing)


class FREDClient:
    BASE = "https://api.stlouisfed.org/fred"

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._sem = asyncio.Semaphore(5)  # FRED is slower than EODHD; conservative limit
        self._client = httpx.AsyncClient(timeout=30.0)

    async def close(self) -> None:
        await self._client.aclose()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=2, max=15),
        retry=retry_if_exception(_is_retryable),
        reraise=True,
    )
    async def _get(self, path: str, **params: str | int) -> dict:
        async with self._sem:
            r = await self._client.get(
                f"{self.BASE}{path}",
                params={"api_key": self._api_key, "file_type": "json", **params},
            )
            r.raise_for_status()
            return r.json()  # type: ignore[no-any-return]

    async def get_series(
        self,
        series_id: str,
        *,
        observation_start: str | None = None,
        limit: int = 10,
        sort_order: str = "desc",
    ) -> list[FREDObservation]:
        """Fetch observations for a FRED series.

        Returns observations newest-first by default (sort_order='desc').
        Values of '.' are returned as None (FRED convention for missing data).
        """
        params: dict[str, str | int] = {
            "series_id": series_id,
            "limit": limit,
            "sort_order": sort_order,
        }
        if observation_start:
            params["observation_start"] = observation_start

        data = await self._get("/series/observations", **params)
        result = []
        for obs in data.get("observations", []):
            raw = obs.get("value", ".")
            value = None if raw == "." else Decimal(raw)
            result.append(FREDObservation(
                date=date.fromisoformat(obs["date"]),
                value=value,
            ))
        return result

    async def latest_value(self, series_id: str) -> Decimal | None:
        """Return the most recent non-missing value for a series, or None."""
        obs_list = await self.get_series(series_id, limit=5, sort_order="desc")
        for obs in obs_list:
            if obs.value is not None:
                return obs.value
        return None


@lru_cache(maxsize=1)
def get_client() -> FREDClient:
    if not settings.fred_api_key:
        raise RuntimeError(
            "FRED_API_KEY is not set — this job requires it. "
            "Set it on the Render service (Environment tab) or via fromService "
            "reference from asxos-api."
        )
    return FREDClient(api_key=settings.fred_api_key)
