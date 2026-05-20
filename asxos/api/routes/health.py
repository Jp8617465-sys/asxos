from fastapi import APIRouter
from fastapi.responses import JSONResponse

from asxos.db import acquire

router = APIRouter()


@router.get("/health")
async def health() -> JSONResponse:
    try:
        async with acquire() as conn:
            await conn.fetchval("SELECT 1")
    except Exception as exc:
        return JSONResponse(status_code=503, content={"status": "unhealthy", "detail": str(exc)})
    return JSONResponse(status_code=200, content={"status": "ok"})
