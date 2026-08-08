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

# Authorization-header form. Proven necessary by a live leak (2026-08-08): the
# Resend client raised `InvalidHeader: ... header value: 'Bearer re_<KEY>\n'`
# and JobMonitor persisted it into job_runs.error_message — the query-param
# regex above cannot see a `Bearer <token>` shape at all. This is the recorded
# G0-71B lesson (a denylist over exception text is never complete) claiming its
# predicted victim; the pattern below closes the *observed* form while the
# structural fix remains "sanitise at the source".
_SECRET_BEARER_RE = re.compile(r"(?i)\b(bearer)\s+[A-Za-z0-9._~+/=-]{8,}")

# Recognisable vendor key prefixes appearing NAKED in text (no param name, no
# Bearer). Deliberately conservative: each requires a long tail, and `re_`
# additionally requires a digit so ordinary snake_case words
# ("re_authenticate") survive. Over-matching redacts a word; under-matching
# leaks a credential — the asymmetry favours the former, narrowly.
# DSN userinfo: postgresql://user:PASSWORD@host — the highest-value secret
# that can plausibly reach job_runs.error_message, and invisible to all other
# passes (userinfo is neither name=value nor Bearer). Value-only: user + host
# survive for diagnostics.
_SECRET_DSN_RE = re.compile(r"(://[^/:@\s]+:)[^@\s]+(@)")

_SECRET_PREFIX_RE = re.compile(
    r"\b(?:"
    r"re_(?=[A-Za-z0-9_]*\d)[A-Za-z0-9_]{10,}"      # Resend (digit form)
    r"|re_[A-Za-z0-9]{6,}_[A-Za-z0-9]{16,}"          # Resend (two-segment form;
                                                     # no digit guarantee exists —
                                                     # a 16+-char second segment
                                                     # never occurs in prose)
    r"|sk-ant-[A-Za-z0-9_-]{10,}"                    # Anthropic
    r"|ghp_[A-Za-z0-9]{10,}"                         # GitHub classic PAT
    r"|github_pat_[A-Za-z0-9_]{10,}"                 # GitHub fine-grained PAT
    r"|rnd_[A-Za-z0-9]{10,}"                         # Render API key
    r")"
)


def redact_secrets(text: str) -> str:
    """Replace credential material with ``***`` wherever it is recognised.

    Three passes: query-param values (``?api_token=…``), Authorization-header
    values (``Bearer …``), and naked vendor-prefixed keys (``re_…``,
    ``sk-ant-…``, ``ghp_…``, ``github_pat_…``, ``rnd_…``).

    Behaviour-preserving for secret-free strings: with no match the input is
    returned unchanged. Only the secret value is removed, so the exception
    class, HTTP status, host and path survive for diagnostics.

    Still a denylist, and the module docstring's caveat stands: sanitising at
    the SOURCE is the real control; this is defence in depth over the shapes
    that have actually leaked.
    """
    text = _SECRET_QS_RE.sub(r"\1=***", text)
    text = _SECRET_DSN_RE.sub(r"\1***\2", text)
    text = _SECRET_BEARER_RE.sub(r"\1 ***", text)
    return _SECRET_PREFIX_RE.sub("***", text)


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
