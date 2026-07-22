import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from asxos.db import acquire

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health")
async def health() -> JSONResponse:
    try:
        async with acquire() as conn:
            await conn.fetchval("SELECT 1")
    except Exception:
        # Generic body only — /health is the one unauthenticated route, and
        # str(exc) can leak connection-string/host internals (CWE-209,
        # 07-18 audit). The traceback goes to server logs, not the response.
        logger.exception("health check failed")
        return JSONResponse(status_code=503, content={"status": "unhealthy"})
    return JSONResponse(status_code=200, content={"status": "ok"})
