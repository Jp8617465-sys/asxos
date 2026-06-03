"""
Regulatory event ingestion.

Three sources (ASIC, RBA, ATO; ASX market announcements is a stretch goal
once an authenticated endpoint is wired). Each source has a parser that
turns the upstream payload (RSS XML for ATO / RBA, JSON for ASX) into a
list of `RegulatoryEvent` records, which the job UPSERTs.

Network I/O is pushed to fetchers in the job script — parsers are pure
functions over bytes/strings so they're easy to unit-test against fixtures.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any
from xml.etree import ElementTree as ET

import asyncpg

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
    """Parse an RSS 2.0 / Atom-ish feed into RegulatoryEvent rows."""
    root = ET.fromstring(xml_bytes)
    items = root.findall(".//item") or root.findall("./{http://www.w3.org/2005/Atom}entry")
    out: list[RegulatoryEvent] = []
    for item in items:
        title = _text(item, "title")
        link = _text(item, "link") or _attr(item, "link", "href")
        pub_str = _text(item, "pubDate") or _text(item, "{http://www.w3.org/2005/Atom}published")
        summary = _text(item, "description") or _text(item, "{http://www.w3.org/2005/Atom}summary") or ""

        if not title or not link:
            continue

        out.append(
            RegulatoryEvent(
                source=source,
                title=title,
                url=link,
                published_at=_parse_date(pub_str) or date.today(),
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
                title=title,
                url=url,
                published_at=_parse_date(released) or date.today(),
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
    payload = []
    for e in events:
        payload.append(
            (
                e.source,
                e.published_at,
                e.title,
                e.url,
                e.summary,
                # relevance_tags JSONB — store symbols + kind
                {"symbols": e.symbols, "kind": e.kind},
            )
        )
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
        [(p[0], p[1], p[2], p[3], p[4], _json(p[5])) for p in payload],
    )
    return len(payload)


def _json(obj: object) -> str:
    import json
    return json.dumps(obj)
