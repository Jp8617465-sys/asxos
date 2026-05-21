"""
Morning-brief composer.

Pulls five sections from Postgres and renders them through a Jinja
template. Keep the prose under 200 words — this brief is consumed daily,
so density matters.

Sections (in order):
  1. Job failures banner (if any in the last 24h)
  2. Market regime
  3. Signal label changes on current holdings (today vs yesterday)
  4. Tax actions: lots crossing the 12-month CGT boundary in next 30 days
  5. Regulatory hits on holdings in the last 24h
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

import jinja2

from asxos.db import acquire
from asxos.domain.tax.cgt import days_to_eligibility

if TYPE_CHECKING:
    import asyncpg


@dataclass(frozen=True)
class SignalChange:
    symbol: str
    old_label: str
    new_label: str
    top_factor: str  # e.g. "mom_12_1+0.953"


@dataclass(frozen=True)
class TaxAction:
    symbol: str
    lot_id: int
    eligible_at: date
    days: int


@dataclass(frozen=True)
class RegulatoryHit:
    symbol: str
    source: str
    title: str
    published_at: date
    kind: str


@dataclass(frozen=True)
class JobFailure:
    job_name: str
    as_of: date
    error_message: str


@dataclass(frozen=True)
class BriefData:
    as_of: date
    regime: str
    holdings_count: int
    signal_changes: list[SignalChange] = field(default_factory=list)
    tax_actions: list[TaxAction] = field(default_factory=list)
    regulatory_hits: list[RegulatoryHit] = field(default_factory=list)
    job_failures: list[JobFailure] = field(default_factory=list)

    @property
    def has_failures(self) -> bool:
        return bool(self.job_failures)


async def collect(as_of: date) -> BriefData:
    """Single async DB session, five queries."""
    async with acquire() as conn:
        regime_row = await conn.fetchrow(
            "SELECT regime FROM signals WHERE as_of = $1 LIMIT 1",
            as_of,
        )
        regime = regime_row["regime"] if regime_row else "neutral"

        holdings_count = await conn.fetchval(
            "SELECT COUNT(*) FROM current_holdings"
        ) or 0

        signal_changes = await _signal_changes(conn, as_of)
        tax_actions = await _tax_actions(conn, as_of)
        regulatory_hits = await _regulatory_hits(conn, as_of)
        job_failures = await _job_failures(conn, as_of)

    return BriefData(
        as_of=as_of,
        regime=regime,
        holdings_count=int(holdings_count),
        signal_changes=signal_changes,
        tax_actions=tax_actions,
        regulatory_hits=regulatory_hits,
        job_failures=job_failures,
    )


async def _signal_changes(conn: asyncpg.Connection, as_of: date) -> list[SignalChange]:
    rows = await conn.fetch(
        """
        WITH today AS (
            SELECT DISTINCT ON (s.symbol)
                s.symbol, s.signal_label, s.shap_factors
            FROM signals s
            JOIN current_holdings h ON h.symbol = s.symbol
            WHERE s.as_of = $1
            ORDER BY s.symbol, s.as_of DESC
        ),
        yesterday AS (
            SELECT DISTINCT ON (s.symbol)
                s.symbol, s.signal_label
            FROM signals s
            JOIN current_holdings h ON h.symbol = s.symbol
            WHERE s.as_of < $1
            ORDER BY s.symbol, s.as_of DESC
        )
        SELECT
            t.symbol,
            COALESCE(y.signal_label, '(new)') AS old_label,
            t.signal_label AS new_label,
            t.shap_factors
        FROM today t
        LEFT JOIN yesterday y ON y.symbol = t.symbol
        WHERE COALESCE(y.signal_label, '') <> t.signal_label
        ORDER BY t.symbol
        """,
        as_of,
    )
    out: list[SignalChange] = []
    for r in rows:
        shap = r["shap_factors"] or {}
        if isinstance(shap, str):
            import json
            shap = json.loads(shap)
        top = ""
        if shap:
            ordered = sorted(
                ((k, v) for k, v in shap.items() if k != "bias" and v is not None),
                key=lambda kv: abs(float(kv[1])),
                reverse=True,
            )
            if ordered:
                k, v = ordered[0]
                top = f"{k}{float(v):+.3f}"
        out.append(
            SignalChange(
                symbol=r["symbol"],
                old_label=r["old_label"],
                new_label=r["new_label"],
                top_factor=top,
            )
        )
    return out


async def _tax_actions(
    conn: asyncpg.Connection, as_of: date, window_days: int = 30
) -> list[TaxAction]:
    rows = await conn.fetch(
        """
        SELECT id, symbol, acquired_at
        FROM current_holdings
        ORDER BY acquired_at
        """
    )
    out: list[TaxAction] = []
    for r in rows:
        days = days_to_eligibility(r["acquired_at"], as_of)
        if 0 < days <= window_days:
            out.append(
                TaxAction(
                    symbol=r["symbol"],
                    lot_id=r["id"],
                    eligible_at=r["acquired_at"] + timedelta(days=366),
                    days=days,
                )
            )
    return out


async def _regulatory_hits(
    conn: asyncpg.Connection, as_of: date, lookback_hours: int = 24
) -> list[RegulatoryHit]:
    rows = await conn.fetch(
        """
        SELECT r.source, r.title, r.published_at, r.relevance_tags
        FROM regulatory_events r
        WHERE r.published_at >= $1::date - INTERVAL '2 day'
          AND r.ingested_at >= $1::date - make_interval(hours => $2)
        ORDER BY r.published_at DESC
        """,
        as_of,
        lookback_hours,
    )
    holdings_rows = await conn.fetch("SELECT symbol FROM current_holdings")
    holdings = {r["symbol"] for r in holdings_rows}

    out: list[RegulatoryHit] = []
    for r in rows:
        tags = r["relevance_tags"] or {}
        if isinstance(tags, str):
            import json
            tags = json.loads(tags)
        symbols = tags.get("symbols") if isinstance(tags, dict) else []
        kind = tags.get("kind", "other") if isinstance(tags, dict) else "other"
        # Match on any holding symbol
        for s in symbols or []:
            if s in holdings:
                out.append(
                    RegulatoryHit(
                        symbol=s,
                        source=r["source"],
                        title=r["title"],
                        published_at=r["published_at"],
                        kind=kind,
                    )
                )
                break
    return out


async def _job_failures(
    conn: asyncpg.Connection, as_of: date
) -> list[JobFailure]:
    rows = await conn.fetch(
        """
        SELECT job_name, as_of, error_message
        FROM job_runs
        WHERE as_of = $1 AND status = 'failure'
        ORDER BY job_name
        """,
        as_of,
    )
    return [
        JobFailure(
            job_name=r["job_name"],
            as_of=r["as_of"],
            error_message=(r["error_message"] or "")[:200],
        )
        for r in rows
    ]


def render_html(data: BriefData) -> str:
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(Path(__file__).parent / "templates"),
        autoescape=True,
    )
    return env.get_template("brief.html.j2").render(d=data)
