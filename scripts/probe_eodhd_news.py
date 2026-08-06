#!/usr/bin/env python3
"""Probe EODHD /news — the one call that settles why `holding_news` is empty.

`holding_news` has held zero rows since at least 2026-07-06 while `ingest_news`
recorded status='success' on every run. Two independent defects could each produce
that artefact, and both were fixed on 2026-08-05 (commits deea76a, 002b6c9):

  A. the request asked EODHD for the project symbol (``HUBS.NYSE``), a namespace it
     does not serve — it addresses NYSE/NASDAQ listings as ``.US``
  B. the response filter guessed ``.AU`` for any bare vendor tag, so EODHD's
     ``HUBS`` became ``HUBS.AU`` and never matched the held ``HUBS.NYSE``

Neither can be ranked from the logs — they produce an identical green zero-row run,
and A sits upstream of B. There is a third possibility nothing has tested: that
``/news`` simply has no coverage on this plan tier, the way ``/sentiments`` does not
(the REV-K pivot, 2026-05-24). If that is the answer, the honest outcome is to
retire the feed the way Treasury and ATO were retired, not to keep patching it.

This script answers all three, read-only, in one run.

Usage:
    EODHD_API_KEY=... python3 scripts/probe_eodhd_news.py
    EODHD_API_KEY=... python3 scripts/probe_eodhd_news.py BHP.AU CBA.AU

Read-only: performs GET requests only. Writes nothing, touches no database.
Deliberately standalone — stdlib only — so it runs in a bare shell (a one-off
Render job) where asxos and its dependencies may not be importable. The credential
scrub is inlined for the same reason. Prior art:
docs/research/probes/2026-06-24-eodhd-gate-closure.md.

Operational: /news is metered. Five calls is trivial, but repeated runs against a
quota-limited plan can push the account to 402 and take the real ingest_news cron
down with it. Run this in a Render shell rather than an agent sandbox — the token
rides in the query string, so any TLS-terminating proxy in between can see it.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://eodhd.com/api"
TIMEOUT = 30

# The live holding, plus an ASX control. The US name is the whole question: if the
# .AU control returns articles and the .US one does not, coverage is the answer.
DEFAULT_SYMBOLS = ("HUBS.NYSE", "HUBS.US", "HUBS", "BHP.AU", "CBA.AU")

_SECRET = re.compile(r"((?:api_token|api_key|apikey|token)=)[^&\s'\"]+", re.IGNORECASE)


def redact(text: str) -> str:
    """Strip credential values AND control characters. The only print-safe path.

    Control-character scrubbing is not decoration: both callers pass an
    externally-controlled HTTP body, and the realistic trigger is not a hostile
    vendor but a proxy or captive-portal HTML error page, which is multi-line by
    construction and would scramble the very table this probe exists to read
    (CWE-117). Same class as the fix applied to asxos/ingestion/news.py.

    Known residual, shared with asxos/redaction.py: the pattern is anchored on
    `name=`, so a body echoing a token as bare JSON or prose is NOT redacted.
    """
    scrubbed = "".join(c if c.isprintable() or c == " " else " " for c in str(text))
    return _SECRET.sub(r"\1***", scrubbed)


def _get(path: str, key: str, **params: object) -> tuple[int, object, str]:
    """GET and return (status, parsed_or_None, note). Never raises on HTTP error."""
    qs = urllib.parse.urlencode({"api_token": key, "fmt": "json", **params})
    url = f"{BASE}{path}?{qs}"
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT) as r:
            raw = r.read().decode("utf-8", "replace")
            try:
                return r.status, json.loads(raw), ""
            except json.JSONDecodeError:
                return r.status, None, f"non-JSON body, first 120 chars: {redact(raw[:120])}"
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8", "replace")[:200]
        except Exception:  # a body read can itself time out; never abort the run
            body = "(error body unreadable)"
        return e.code, None, redact(body)
    except Exception as e:  # a probe must not abort the run on one bad symbol
        return 0, None, f"{type(e).__name__}: {redact(e)}"


def describe(payload: object) -> str:
    """Say what came back WITHOUT echoing vendor strings verbatim."""
    if payload is None:
        return "no parseable payload"
    if isinstance(payload, list):
        return f"list[{len(payload)}]"
    if isinstance(payload, dict):
        # Keys are vendor-controlled. repr() escapes control chars, but [:6]
        # bounds the COUNT not the SIZE, and the field width below is a minimum
        # rather than a truncation — so cap each key explicitly.
        keys = [str(k)[:20] for k in sorted(payload, key=str)[:6]]
        return f"dict keys={keys}"[:64]
    return type(payload).__name__


def main() -> int:
    key = os.environ.get("EODHD_API_KEY", "")
    if not key:
        print("EODHD_API_KEY is not set. This probe needs it; it never prints the")
        print("key, its length, or any URL containing it.")
        return 2

    symbols = tuple(sys.argv[1:]) or DEFAULT_SYMBOLS
    print(f"EODHD /news probe — key present, {len(symbols)} symbols\n")
    print(f"{'symbol':<12} {'HTTP':>5}  {'shape':<28} {'articles':>8}  tags seen")
    print("-" * 92)

    verdicts: dict[str, int] = {}
    for sym in symbols:
        status, payload, note = _get("/news", key, s=sym, limit=5)
        n = len(payload) if isinstance(payload, list) else 0
        verdicts[sym] = n

        tags: list[str] = []
        if isinstance(payload, list):
            for item in payload[:5]:
                if not isinstance(item, dict):
                    continue
                raw_syms = item.get("symbols") or []
                # EODHD sometimes returns `symbols` as a JSON-ENCODED STRING
                # ('["HUBS"]'), which asxos/ingestion/news.py decodes. Without
                # this branch the slice below iterates CHARACTERS and prints
                # ['[', '"', 'H', 'U'] — making the single most load-bearing
                # column of this probe answer its own question wrongly.
                if isinstance(raw_syms, str):
                    try:
                        raw_syms = json.loads(raw_syms)
                    except (json.JSONDecodeError, ValueError):
                        raw_syms = [raw_syms] if raw_syms else []
                if not isinstance(raw_syms, list):
                    raw_syms = [raw_syms]
                for t in raw_syms[:4]:
                    # Same scrub the ingest path applies before logging.
                    clean = "".join(c for c in str(t).upper() if c.isprintable())[:24]
                    if clean and clean not in tags:
                        tags.append(clean)

        print(f"{sym:<12} {status:>5}  {describe(payload):<28} {n:>8}  {', '.join(tags[:6]) or '-'}")
        if note:
            print(f"{'':<12} note: {note[:150]}")

    print("\n" + "=" * 92)
    print("READING THE RESULT")
    print("=" * 92)
    us_ok = any(verdicts.get(s, 0) > 0 for s in ("HUBS.US", "HUBS", "HUBS.NYSE"))
    au_ok = any(verdicts.get(s, 0) > 0 for s in ("BHP.AU", "CBA.AU"))

    if not us_ok and not au_ok:
        print("  NO coverage on either namespace -> the plan tier does not serve /news.")
        print("  Honest outcome: RETIRE the feed (as Treasury and ATO were), do not patch.")
    elif au_ok and not us_ok:
        print("  ASX works, US does not -> coverage is ASX-only on this tier.")
        print("  The symbol fix is still correct but cannot help the current US-only holding.")
    elif us_ok:
        print("  US coverage EXISTS -> the feed works and the fix should populate the table.")
        print("  Compare which US form returned articles against what the job now requests")
        print("  (jobs/ingest_news.py sends eodhd_symbol(symbol), i.e. HUBS.NYSE -> HUBS.US).")
        print("  The 'tags seen' column shows the form the vendor labels articles with —")
        print("  build_symbol_alias must map that form to the HELD symbol.")

    print("\n  Whatever the outcome, record it in docs/market-trends-report-2026-08-05.md")
    print("  section 11 fix #1, which is currently the only open way to rank the two causes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
