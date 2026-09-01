"""
Regulatory event ingestion.

One live source: RBA (RSS 1.0/RDF — the "RSS-CB" central-bank profile).
Treasury (RSS 2.0) was removed 2026-07-18 — gov.au's WAF returned a
deterministic 403 to every fetch regardless of client headers, confirmed
across 13+ consecutive days of live production runs (see the SOURCES
comment in jobs/ingest_regulatory.py for the full diagnosis). ATO was
removed earlier — its site redesign killed the Newsroom feed and there is
no stable public replacement. ASIC was never wired. ASX market
announcements (JSON) is a stretch goal once an authenticated endpoint
exists; `parse_json_announcements` is kept for that path.

Each source has a parser that turns the upstream payload (RSS XML, JSON)
into a list of `RegulatoryEvent` records, which the job UPSERTs.

Network I/O is pushed to fetchers in the job script — parsers are pure
functions over bytes/strings so they're easy to unit-test against fixtures.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any
from xml.etree import ElementTree as ET  # Element types only — parsing goes through defusedxml

import asyncpg
from defusedxml.ElementTree import (  # type: ignore[import-untyped]  # no stubs shipped
    fromstring as _safe_fromstring,
)

from asxos import clock

# Symbol regex — ASX tickers are 3 to 5 uppercase letters. `.AU` suffix
# is the asxos convention; events may carry the bare ticker so we capture
# the bare form and normalise downstream.
_SYMBOL_RE = re.compile(r"\b([A-Z]{3,5})(?:\.AX|\.AU)?\b")
_RSS_DATE_FORMATS = (
    "%a, %d %b %Y %H:%M:%S %z",
    "%a, %d %b %Y %H:%M:%S GMT",
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%dT%H:%M:%SZ",
)
_ATOM_NS = "{http://www.w3.org/2005/Atom}"
_RSS1_NS = "{http://purl.org/rss/1.0/}"
_DC_NS = "{http://purl.org/dc/elements/1.1/}"


@dataclass(frozen=True)
class RegulatoryEvent:
    source: str
    title: str
    url: str
    published_at: date
    summary: str
    symbols: list[str]
    kind: str  # 'disclosure' | 'monetary_policy' | 'tax' | 'enforcement' | 'other'


def parse_rss(xml_bytes: bytes, *, source: str, default_kind: str = "other") -> list[RegulatoryEvent]:
    """Parse an RSS 2.0 / RSS 1.0 (RDF) / Atom-ish feed into RegulatoryEvent rows.

    Parsing uses defusedxml (entity-expansion / external-entity attacks
    disabled) — the feed bytes are untrusted external input (07-18 audit).
    """
    root = _safe_fromstring(xml_bytes)
    items = root.findall(".//item") or root.findall(f"./{_ATOM_NS}entry")
    ns = ""
    if not items:
        # RSS 1.0/RDF fallback (e.g. RBA's RSS-CB feeds): rdf:RDF root, items
        # in the RSS 1.0 default namespace, dates in Dublin Core <dc:date>
        # (ISO 8601) rather than RSS 2.0 <pubDate>.
        items = root.findall(f".//{_RSS1_NS}item")
        ns = _RSS1_NS
    out: list[RegulatoryEvent] = []
    for item in items:
        title = _text(item, f"{ns}title")
        link = _text(item, f"{ns}link") or _attr(item, f"{ns}link", "href")
        if ns:
            pub_str = _text(item, f"{_DC_NS}date")
            summary = _text(item, f"{ns}description")
        else:
            pub_str = _text(item, "pubDate") or _text(item, f"{_ATOM_NS}published")
            summary = _text(item, "description") or _text(item, f"{_ATOM_NS}summary")

        if not title or not link:
            continue

        out.append(
            RegulatoryEvent(
                source=source,
                # Cap like summary below — titles are untrusted feed text and
                # flow into the brief/alert render paths (07-18 audit).
                title=title[:500],
                url=link,
                published_at=_parse_date(pub_str) or clock.today(),
                summary=summary[:2000],
                symbols=extract_symbols(f"{title} {summary}"),
                kind=classify_kind(title, summary, default_kind),
            )
        )
    return out


def parse_json_announcements(payload: list[dict[str, Any]], *, source: str = "ASX") -> list[RegulatoryEvent]:
    """ASX announcements JSON — one object per announcement.

    Each item is expected to carry: symbol, headline, url, pdfUrl, releasedOn.
    Unknown fields are tolerated.
    """
    out: list[RegulatoryEvent] = []
    for item in payload:
        symbol = (item.get("symbol") or "").strip().upper()
        title = (item.get("headline") or item.get("title") or "").strip()
        url = (item.get("url") or item.get("pdfUrl") or "").strip()
        released = item.get("releasedOn") or item.get("publishedAt") or ""

        if not title or not url:
            continue

        symbols = [symbol] if symbol else extract_symbols(title)
        if symbols and "." not in symbols[0]:
            symbols = [f"{s}.AU" for s in symbols]

        out.append(
            RegulatoryEvent(
                source=source,
                title=title[:500],
                url=url,
                published_at=_parse_date(released) or clock.today(),
                summary=(item.get("description") or "")[:2000],
                symbols=symbols,
                kind=classify_kind(title, "", "disclosure"),
            )
        )
    return out


def extract_symbols(text: str) -> list[str]:
    """Find ASX-like tickers in `text`. Returns `.AU`-suffixed symbols, de-duped."""
    found = []
    seen = set()
    for m in _SYMBOL_RE.finditer(text):
        tok = m.group(1)
        if tok in {"ASX", "ASIC", "RBA", "ATO", "AUD", "GMT", "UTC", "PDF", "RSS", "API"}:
            continue
        sym = f"{tok}.AU"
        if sym not in seen:
            seen.add(sym)
            found.append(sym)
    return found


_KIND_KEYWORDS: dict[str, tuple[str, ...]] = {
    "monetary_policy": ("cash rate", "monetary policy", "interest rate decision", "RBA board"),
    "tax": ("tax determination", "ruling", "ATO", "GST", "stamp duty", "franking", "Division 296"),
    "enforcement": ("infringement", "penalty", "enforcement action", "court action", "investigation"),
    "disclosure": ("announcement", "results", "guidance", "dividend", "trading update", "appendix"),
}


def classify_kind(title: str, body: str, default: str = "other") -> str:
    """20-line keyword heuristic. Order matters — first hit wins."""
    blob = f"{title} {body}".lower()
    for kind, keywords in _KIND_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in blob:
                return kind
    return default


def _text(el: ET.Element, tag: str) -> str:
    found = el.find(tag)
    if found is None or found.text is None:
        return ""
    return found.text.strip()


def _attr(el: ET.Element, tag: str, attr: str) -> str:
    found = el.find(tag)
    if found is None:
        return ""
    return (found.get(attr) or "").strip()


def _parse_date(s: str | None) -> date | None:
    if not s:
        return None
    s = s.strip()
    for fmt in _RSS_DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    # last-ditch ISO date
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        return None


async def upsert_events(
    conn: asyncpg.Connection, events: list[RegulatoryEvent]
) -> int:
    """Idempotent UPSERT on (source, url). Returns rows affected."""
    if not events:
        return 0
    # Single comprehension straight to bind-tuples (07-18 audit: the old
    # two-step intermediate list re-mapped every row a second time).
    rows = [
        (
            e.source,
            e.published_at,
            e.title,
            e.url,
            e.summary,
            # relevance_tags JSONB — store symbols + kind
            json.dumps({"symbols": e.symbols, "kind": e.kind}),
        )
        for e in events
    ]
    await conn.executemany(
        """
        INSERT INTO regulatory_events (source, published_at, title, url, summary, relevance_tags)
        VALUES ($1, $2, $3, $4, $5, $6::jsonb)
        ON CONFLICT (source, url) DO UPDATE SET
            published_at   = EXCLUDED.published_at,
            title          = EXCLUDED.title,
            summary        = EXCLUDED.summary,
            relevance_tags = EXCLUDED.relevance_tags
        """,
        rows,
    )
    return len(rows)
