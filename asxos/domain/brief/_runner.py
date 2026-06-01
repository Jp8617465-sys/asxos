"""
safe_collect — timeout-bounded collector runner — M-Brief-Skeleton.

safe_collect(coro, section_name, timeout) → SectionResult

Never raises. Timeout or exception → SectionResult with status=timeout/failed.
Callers always get a SectionResult, never an exception.
"""
from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from datetime import datetime
from typing import Any

from asxos.domain.brief.types import SectionResult, SectionStatus


async def safe_collect(
    coro: Coroutine[Any, Any, SectionResult],
    section_name: str,
    timeout: float,
) -> SectionResult:
    """Run coro with a timeout. Returns SectionResult regardless of outcome."""
    start = datetime.utcnow()
    try:
        result = await asyncio.wait_for(coro, timeout=timeout)
        return result
    except TimeoutError:
        elapsed_ms = int((datetime.utcnow() - start).total_seconds() * 1000)
        return SectionResult(
            name=section_name,
            status=SectionStatus.timeout,
            items=(),
            elapsed_ms=elapsed_ms,
            error=f"timed out after {timeout:.0f}s",
        )
    except Exception as exc:
        elapsed_ms = int((datetime.utcnow() - start).total_seconds() * 1000)
        return SectionResult(
            name=section_name,
            status=SectionStatus.failed,
            items=(),
            elapsed_ms=elapsed_ms,
            error=f"{type(exc).__name__}: {exc}",
        )
