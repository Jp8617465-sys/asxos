"""Secret redaction for strings that get persisted or logged.

httpx builds an ``HTTPStatusError`` message containing the full request URL, and
the EODHD/FRED clients pass their API key as a URL query param (``?api_token=…``
/ ``?api_key=…``). A routine upstream error (401 on a rotated key, 402 free-tier
quota) would otherwise write that key into ``job_runs.error_message`` — a
queryable table also readable by the agent MCP surface — the Render stdout log
stream, and ``ingestion_warnings`` JSONB (CWE-532 / CWE-209).

``sanitized_http_error`` fixes the leak at the SOURCE (each client's ``_get``),
so no downstream sink can leak the key. ``redact_secrets`` is the defense-in-depth
string scrub applied at the sinks (the shared ``JobMonitor`` DB write, raw-exception
logging). Together they generalise the single-job ``_safe_exc_detail`` guard in
``jobs/ingest_market_context.py``.

Top-level module (not under jobs/ or clients/) so every layer — clients,
ingestion, jobs — can import it without a dependency inversion.
"""
from __future__ import annotations

import re

import httpx

# Credential-bearing query-param names actually used in this codebase (EODHD
# api_token, FRED api_key) plus common variants. Value-only redaction keeps the
# surrounding diagnostic (exception class, HTTP status, host, path) visible.
_SECRET_QS_RE = re.compile(
    r"(?i)(api[_-]?token|api[_-]?key|apikey|access[_-]?token|secret|password)=([^&\s'\"]+)"
)


def redact_secrets(text: str) -> str:
    """Replace the value of any credential query param with ``***``.

    Behaviour-preserving for secret-free strings: with no match the input is
    returned unchanged. Only the secret value is removed, so the exception
    class, HTTP status, host and path survive for diagnostics.
    """
    return _SECRET_QS_RE.sub(r"\1=***", text)


def sanitized_http_error(exc: httpx.HTTPStatusError) -> httpx.HTTPStatusError:
    """Return a copy of ``exc`` with the API key stripped at the SOURCE.

    The EODHD/FRED clients carry the key as a URL query param, so httpx's
    ``HTTPStatusError`` message and ``request.url`` both embed it. Raising this
    sanitized copy from the client's ``_get`` means no downstream sink (job_runs,
    Render logs, ingestion_warnings JSONB) can leak the key — current or future.

    The class and ``response`` are preserved so the tenacity retry predicate
    (``_is_retryable`` checks ``isinstance(exc, HTTPStatusError)`` and
    ``exc.response.status_code``) still classifies it correctly.
    """
    base_url = str(exc.request.url).split("?", 1)[0]  # drop ?api_token=…/?api_key=…
    return httpx.HTTPStatusError(
        redact_secrets(str(exc)),
        request=httpx.Request(exc.request.method, base_url),
        response=exc.response,
    )
