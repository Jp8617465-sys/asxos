#!/usr/bin/env python3
"""CLI shim over ``asxos.schema_drift`` — run the drift check from CI or by hand.

The logic lives in ``asxos/schema_drift.py``, not here, for one reason:
``asxos/api/main.py`` calls it during lifespan startup, and ``scripts/`` is not
an installed package (no ``__init__.py``, not in ``[tool.setuptools.packages]``).
Importing it from the app would work when run out of a checkout and fail once
installed — a boot failure, which CLAUDE.md #1 says must never be a surprise.

Exit codes: 0 agree · 1 drift · 2 DATABASE_URL missing.
"""
from __future__ import annotations

import asyncio
import os
import sys

from asxos.schema_drift import MigrationDrift, check


async def _main() -> int:
    import asyncpg

    url = os.environ.get("DATABASE_URL")
    if not url:
        print("DATABASE_URL is not set", file=sys.stderr)
        return 2

    # Read-only session, declared to the server rather than left implicit.
    # `default_transaction_read_only` and not `SET TRANSACTION READ ONLY`: the
    # latter outside an explicit transaction block is a no-op that only emits a
    # warning, so it would look like a control and be none.
    conn = await asyncpg.connect(
        url,
        server_settings={"timezone": "UTC", "default_transaction_read_only": "on"},
    )
    try:
        await check(conn)
    except MigrationDrift as exc:
        print(str(exc), file=sys.stderr)
        return 1
    finally:
        await conn.close()

    print("migration drift check: applied migrations and migrations/ agree")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
