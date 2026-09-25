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
import logging
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

log = logging.getLogger(__name__)

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
            # E-20's other half: "does parse_rss filter too narrowly?" is
            # unanswerable from a synthetic fixture and the live feed is not
            # reachable from an agent session (egress policy denies
            # www.rba.gov.au). This makes the next PRODUCTION run answer it —
            # every item dropped here says so, with which leg was missing.
            # Silent skipping is what made the question unanswerable.
            log.warning(
                "%s: skipped a feed item with no %s",
                source,
                "title" if not title else "link",
            )
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


@dataclass(frozen=True)
class UpsertCounts:
    """How an UPSERT batch actually landed — new rows vs rows already present.

    The distinction is the whole point (E-20). ``upsert_events`` used to return
    ``len(rows)``, i.e. how many events were *presented* to the statement, and
    ``jobs/ingest_regulatory.py`` assigned that to ``monitor.rows_written``. So a
    feed re-serving the same single item every night reported ``rows_written=1``
    every night while ``regulatory_events`` did not grow — measured 2026-09-15:
    7 rows total, ``max(ingested_at)`` 2026-09-03, yet a ``rows_written=1``
    success row on every night from 09-07 to 09-14.

    Nothing was broken; the number meant "touched", and every reader — the
    digest, a human scanning ``job_runs`` — reads ``rows_written`` as "work
    done". That is the same defect class as routing a steady-state fact into
    ``monitor.note``: a channel with an established meaning carrying something
    else.
    """

    inserted: int
    updated: int

    @property
    def presented(self) -> int:
        """Events handed to the statement — the old return value, kept nameable."""
        return self.inserted + self.updated


async def upsert_events(
    conn: asyncpg.Connection, events: list[RegulatoryEvent]
) -> UpsertCounts:
    """Idempotent UPSERT on (source, url). Returns new vs already-present counts.

    ``RETURNING (xmax = 0)`` is the standard Postgres idiom for "did this row
    INSERT or UPDATE": on a row the statement inserted, the system column
    ``xmax`` is 0, while a row it updated carries the updating transaction's id.
    It is a system-column detail rather than standard SQL, and it is used here
    instead of a count-before/count-after pair because it is exact in one round
    trip and cannot race a concurrent writer.

    **Deduped by (source, url) before binding, which ``executemany`` did not need
    to be.** One statement over an array cannot touch the same conflict target
    twice — Postgres raises *"ON CONFLICT DO UPDATE command cannot affect row a
    second time"* — whereas the previous per-row ``executemany`` would quietly
    apply both. A feed that lists one release under two entries is a feed bug,
    not a reason to fail the run, so the last occurrence wins and the count
    reflects what was actually written.
    """
    if not events:
        return UpsertCounts(inserted=0, updated=0)
    # Last occurrence wins, insertion order preserved (dict, not a set).
    deduped = {(e.source, e.url): e for e in events}
    cols = list(
        zip(
            *[
                (
                    e.source,
                    e.published_at,
                    e.title,
                    e.url,
                    e.summary,
                    # relevance_tags JSONB — store symbols + kind
                    json.dumps({"symbols": e.symbols, "kind": e.kind}),
                )
                for e in deduped.values()
            ],
            strict=True,
        )
    )
    landed = await conn.fetch(
        """
        INSERT INTO regulatory_events (source, published_at, title, url, summary, relevance_tags)
        SELECT s, p, t, u, sm, rt::jsonb
        FROM unnest($1::text[], $2::date[], $3::text[], $4::text[], $5::text[], $6::text[])
             AS v(s, p, t, u, sm, rt)
        ON CONFLICT (source, url) DO UPDATE SET
            published_at   = EXCLUDED.published_at,
            title          = EXCLUDED.title,
            summary        = EXCLUDED.summary,
            relevance_tags = EXCLUDED.relevance_tags
        RETURNING (xmax = 0) AS inserted
        """,
        *[list(c) for c in cols],
    )
    inserted = sum(1 for r in landed if r["inserted"])
    return UpsertCounts(inserted=inserted, updated=len(landed) - inserted)
