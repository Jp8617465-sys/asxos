"""Unit tests for asxos/jobs/utils/redaction.py.

Pins that credential query params (EODHD api_token, FRED api_key) are stripped
from any string before it is persisted or logged, while non-secret diagnostic
detail is preserved. Backs the 2026-07-18 audit P1 (CWE-532 key leak).
"""
import httpx

from asxos.redaction import redact_secrets, sanitized_http_error


def test_redacts_eodhd_api_token() -> None:
    s = "HTTPStatusError: ... for url 'https://eodhd.com/api/eod/BHP.AU?api_token=SECRETKEY&fmt=json'"
    out = redact_secrets(s)
    assert "SECRETKEY" not in out
    assert "api_token=***" in out
    assert "fmt=json" in out  # non-secret param preserved


def test_redacts_fred_api_key() -> None:
    s = "for url 'https://api.stlouisfed.org/fred/series/observations?api_key=DEADBEEF&file_type=json'"
    out = redact_secrets(s)
    assert "DEADBEEF" not in out
    assert "api_key=***" in out
    assert "file_type=json" in out


def test_preserves_secret_free_text() -> None:
    # No credential param → returned unchanged (behaviour-preserving).
    s = "RuntimeError: No active profile found."
    assert redact_secrets(s) == s


def test_preserves_diagnostic_status_and_path() -> None:
    s = "Client error '402 Payment Required' for url 'https://eodhd.com/api/eod/X?api_token=SECRETKEY&fmt=json'"
    out = redact_secrets(s)
    assert "402 Payment Required" in out  # HTTP status kept for diagnosis
    assert "eodhd.com/api/eod/X" in out    # host + path kept
    assert "api_token=SECRETKEY" not in out
    assert "api_token=***" in out


def test_redacts_case_insensitively() -> None:
    assert "***" in redact_secrets("?API_TOKEN=SECRETKEY")
    assert "SECRETKEY" not in redact_secrets("?API_TOKEN=SECRETKEY")


# ── sanitized_http_error — the SOURCE fix in the EODHD/FRED clients ─────────────

def _leaking_error(query_param: str) -> httpx.HTTPStatusError:
    url = f"https://eodhd.com/api/eod/BHP.AU?{query_param}=SECRETKEY&fmt=json"
    req = httpx.Request("GET", url)
    resp = httpx.Response(402, request=req)
    return httpx.HTTPStatusError(f"Client error '402' for url '{url}'", request=req, response=resp)


def test_sanitized_http_error_strips_key_from_message_and_url() -> None:
    safe = sanitized_http_error(_leaking_error("api_token"))
    assert "SECRETKEY" not in str(safe)               # message scrubbed
    assert "SECRETKEY" not in str(safe.request.url)   # request URL stripped
    assert "api_token" not in str(safe.request.url)   # whole query dropped


def test_sanitized_http_error_preserves_retry_classification() -> None:
    # The tenacity _is_retryable predicate keys on isinstance + response.status_code;
    # both must survive so retries still work after sanitization.
    safe = sanitized_http_error(_leaking_error("api_key"))
    assert isinstance(safe, httpx.HTTPStatusError)
    assert safe.response.status_code == 402
    assert "402" in str(safe)  # status kept for diagnostics


def test_sanitized_http_error_suppresses_original_context() -> None:
    # `raise ... from None` at the call site relies on the traceback machinery not
    # re-exposing the original; the sanitized copy itself must carry no key.
    safe = sanitized_http_error(_leaking_error("api_token"))
    assert "SECRETKEY" not in repr(safe)


# ---------------------------------------------------------------------------
# Bearer-header and naked-prefix forms (2026-08-08)
#
# Live instance: the Resend client raised
#   InvalidHeader: ... header value: 'Bearer re_<KEY>\n'
# and JobMonitor persisted it to job_runs.error_message — the query-param
# regex cannot see that shape. These pin the observed leak form and the
# conservative naked-prefix pass.
# ---------------------------------------------------------------------------


def test_bearer_header_value_is_redacted() -> None:
    msg = (
        "InvalidHeader: Invalid leading whitespace, reserved character(s), or "
        "return character(s) in header value: 'Bearer re_CwbxTESTKEY12345abc\\n'"
    )
    out = redact_secrets(msg)
    assert "re_CwbxTESTKEY12345abc" not in out
    assert "Bearer ***" in out
    assert "InvalidHeader" in out, "diagnostic context must survive"


def test_naked_vendor_keys_are_redacted() -> None:
    for raw in (
        "sent with key re_9abcDEF12345xyz",
        "anthropic sk-ant-abc123def456ghi",
        "token ghp_AbCd1234EfGh5678",
        "pat github_pat_11ABCDEF0123456789",
        "render rnd_7QNvTESTKEY123456",
    ):
        out = redact_secrets(raw)
        assert "***" in out, raw
        for frag in ("re_9abc", "sk-ant-abc", "ghp_AbCd", "github_pat_11", "rnd_7QNv"):
            assert frag not in out, f"{frag} survived in {out!r}"


def test_ordinary_snake_case_words_survive() -> None:
    """`re_` needs a digit + length — prose must not be eaten."""
    msg = "please re_authenticate and re_run the re_ingestion step"
    assert redact_secrets(msg) == msg


def test_bearer_in_prose_without_token_survives() -> None:
    assert redact_secrets("the bearer of this message") == (
        "the bearer of this message"
    )
