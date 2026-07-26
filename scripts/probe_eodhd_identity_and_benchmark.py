#!/usr/bin/env python3
"""Probe EODHD for the two data sources the investment-engine programme needs.

Answers two questions that gate roughly 80% of the S07 identity build and the
S10/S11 benchmark, at zero marginal cost on the existing subscription:

1. Does EODHD return an LEI (and FIGI/ISIN) for ``.AU`` symbols? If yes, issuer
   identity comes from a feed already paid for, and GLEIF Level 2 supplies the
   corporate-group edges. If no, the fallback is matching existing ISINs against
   GLEIF's ISIN-to-LEI file, which depends on ASX being a participating NNA.

2. Does EODHD carry the genuine S&P/ASX 200 total-return indices (AXJT gross,
   AXNT net, XJOA accumulation)? If yes, ``benchmark-policy-v1``'s "genuine
   XJO-TR" requirement is satisfiable under a licence already held, and S11's
   strategy gate becomes reachable. If no, the benchmark must be an explicitly
   labelled proxy and the policy needs amending.

Read-only. Performs GET requests only; writes nothing and touches no database.

Usage:
    EODHD_API_KEY=... python3 scripts/probe_eodhd_identity_and_benchmark.py
"""

from __future__ import annotations

import http.client
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

# Deliberately standalone: this probe must run in a bare shell (e.g. a one-off
# Render job) where asxos and its dependencies may not be importable, so the
# credential scrub is inlined rather than imported from asxos.redaction.
_SECRET_PARAM = re.compile(r"((?:api_token|api_key|apikey|token)=)[^&\s'\"]+", re.IGNORECASE)


def redact_secrets(text: str) -> str:
    """Replace the value of any credential query parameter with ``***``."""
    return _SECRET_PARAM.sub(r"\1***", text)


BASE = "https://eodhd.com/api"
TIMEOUT = 30

# Names worth checking for the ASX total-return series. XJOA is the
# end-of-day accumulation index; XJT/AXJT is the gross total return
# (calculated intraday, formerly named the accumulation index); XNT/AXNT is
# the net total return. XJOAI is deliberately absent -- it is the Buy-Write
# index, not an accumulation series.
BENCHMARK_HINTS = ("AXJT", "AXNT", "XJOA", "AXJOA", "XJT", "XNT")
IDENTITY_SYMBOLS = ("BHP.AU", "GMG.AU", "RIO.AU", "NWS.AU")


def _clean(value: object, limit: int = 80) -> str:
    """Truncate and strip control characters from a vendor-supplied string."""
    return "".join(char for char in str(value)[:limit] if char.isprintable())


def _get(path: str, params: dict[str, str], token: str) -> object:
    query = urllib.parse.urlencode({**params, "api_token": token, "fmt": "json"})
    url = f"{BASE}/{urllib.parse.quote(path, safe='/')}?{query}"
    request = urllib.request.Request(url, headers={"User-Agent": "asxos-probe/1.0"})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return json.loads(response.read().decode("utf-8"))


def _safe_get(label: str, path: str, params: dict[str, str], token: str) -> object | None:
    """Return the parsed body, or None when the request itself failed.

    None means "no answer", never "the answer is no" -- the caller must keep the
    two apart so a bad key cannot manufacture a negative result.
    """
    try:
        return _get(path, params, token)
    except urllib.error.HTTPError as exc:
        hint = " -- auth/subscription, NOT evidence of absence" if exc.code in (401, 403) else ""
        if exc.code == 429:
            hint = " -- rate limited, NOT evidence of absence"
        print(f"  {label}: HTTP {exc.code} ({redact_secrets(str(exc.reason))}){hint}")
    except (
        urllib.error.URLError,
        TimeoutError,
        json.JSONDecodeError,
        http.client.HTTPException,
        ValueError,
    ) as exc:
        print(f"  {label}: unavailable ({redact_secrets(str(exc))})")
    return None


def probe_identity(token: str) -> bool | None:
    """True if an LEI was returned, False if genuinely absent, None if unanswered."""
    print("\n== PROBE 1: issuer identity (LEI / FIGI / ISIN) for .AU symbols ==")
    found_any = False
    answered = 0

    mapping = _safe_get(
        "id-mapping", "mp/eodhd/id-mapping", {"filter[ex]": "AU", "limit": "25"}, token
    )
    if mapping is not None:
        answered += 1
    if isinstance(mapping, list) and mapping:
        populated = [row for row in mapping if isinstance(row, dict) and row.get("lei")]
        print(f"  id-mapping API: {len(mapping)} row(s), {len(populated)} with a non-empty lei")
        for row in mapping[:5]:
            if isinstance(row, dict):
                print(
                    f"    {_clean(row.get('symbol'), 12):<12} "
                    f"isin={_clean(row.get('isin'), 14):<14} "
                    f"lei={_clean(row.get('lei'), 22):<22} figi={_clean(row.get('figi'), 14)}"
                )
        found_any = found_any or bool(populated)
    elif mapping is not None:
        print("  id-mapping API: reachable but returned no rows for filter[ex]=AU")

    for symbol in IDENTITY_SYMBOLS:
        general = _safe_get(f"fundamentals {symbol}", f"fundamentals/{symbol}", {}, token)
        if general is not None:
            answered += 1
        if isinstance(general, dict):
            block = general.get("General")
            if isinstance(block, dict):
                lei = block.get("LEI")
                print(
                    f"  {symbol:<9} LEI={_clean(lei, 22):<22} "
                    f"ISIN={_clean(block.get('ISIN'), 14):<14} "
                    f"OpenFigi={_clean(block.get('OpenFigi'), 14):<14} "
                    f"Primary={_clean(block.get('PrimaryTicker'), 14)}"
                )
                found_any = found_any or bool(lei)

    if answered == 0:
        return None
    return found_any


def probe_benchmark(token: str) -> bool | None:
    """True if a TR index is listed, False if genuinely absent, None if unanswered."""
    print("\n== PROBE 2: genuine S&P/ASX 200 total-return index availability ==")
    listing = _safe_get("exchange-symbol-list/INDX", "exchange-symbol-list/INDX", {}, token)
    if not isinstance(listing, list):
        print("  index listing unavailable -- cannot conclude")
        return None

    print(f"  index listing: {len(listing)} symbol(s)")
    hits = [
        row
        for row in listing
        if isinstance(row, dict)
        and any(hint in str(row.get("Code", "")).upper() for hint in BENCHMARK_HINTS)
    ]
    asx_like = [
        row
        for row in listing
        if isinstance(row, dict) and "ASX" in str(row.get("Name", "")).upper()
    ]
    for row in (hits + [row for row in asx_like if row not in hits])[:20]:
        print(f"    {_clean(row.get('Code'), 14):<14} {_clean(row.get('Name'))}")
    if not hits and not asx_like:
        print("    no ASX or total-return index codes matched")
    return bool(hits)


def main() -> int:
    token = os.environ.get("EODHD_API_KEY")
    if not token:
        print("EODHD_API_KEY is not set. Run where the key is provisioned (e.g. Render).")
        return 2

    identity_ok = probe_identity(token)
    benchmark_ok = probe_benchmark(token)

    if identity_ok is None:
        identity_verdict = (
            "INCONCLUSIVE -- no request succeeded. This is NOT evidence that EODHD lacks "
            "LEI; re-run where the key is valid before deciding anything"
        )
    elif identity_ok:
        identity_verdict = (
            "LEI available from EODHD -- build S07 identity on the feed already paid for"
        )
    else:
        identity_verdict = (
            "no LEI returned -- fall back to GLEIF ISIN-to-LEI (ASX NNA participation "
            "UNRESOLVED) or curate ~50 issuers by hand"
        )

    if benchmark_ok is None:
        benchmark_verdict = (
            "INCONCLUSIVE -- the index listing did not answer. This is NOT evidence that the "
            "series is unavailable; re-run before amending benchmark-policy-v1"
        )
    elif benchmark_ok:
        benchmark_verdict = (
            "an ASX total-return index is listed -- benchmark-policy-v1 is satisfiable "
            "under the existing licence"
        )
    else:
        benchmark_verdict = (
            "no ASX total-return index found -- use RBA Table F7 (CC BY 4.0, monthly) plus a "
            "labelled ETF-NAV proxy, and amend benchmark-policy-v1 accordingly"
        )

    print("\n== VERDICT ==")
    print(f"  identity : {identity_verdict}")
    print(f"  benchmark: {benchmark_verdict}")
    print("\nNeither answer changes a policy on its own; both are James decisions.")
    inconclusive = identity_ok is None or benchmark_ok is None
    return 3 if inconclusive else 0


if __name__ == "__main__":
    sys.exit(main())
