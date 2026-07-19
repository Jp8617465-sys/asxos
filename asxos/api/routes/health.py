import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from asxos.db import acquire

router = APIRouter()
log = logging.getLogger(__name__)


@router.get("/health")
async def health() -> JSONResponse:
    """Public, unauthenticated (Render's load balancer needs to hit it).

    The 503 body must stay generic -- the real exception is logged server-side
    for debugging, never returned to the caller. A leaked exception string on
    a public endpoint can expose internal details (DB host/schema fragments,
    stack-trace internals) to anyone probing the API during an outage.
    """
    try:
        async with acquire() as conn:
            await conn.fetchval("SELECT 1")
    except Exception:
        log.exception("Health check failed")
        return JSONResponse(status_code=503, content={"status": "unhealthy"})
    return JSONResponse(status_code=200, content={"status": "ok"})
