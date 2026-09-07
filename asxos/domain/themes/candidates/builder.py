"""Assemble a ThemeVersion and a CandidateSnapshot from a governed theme.

Everything numeric comes from `measures.py`; every evidence item cites the
row it came from; the same inputs produce the same content hash. No LLM is
consulted here — agent evidence enters only through `extraction_boundary`.
"""
from __future__ import annotations

from datetime import UTC, date, datetime, time
from decimal import Decimal
from typing import Any

from asxos.domain.decision_engine.types import DataMode, EvidenceItem
from asxos.domain.themes.candidates.measures import (
    SQL_MACRO,
    SQL_MEMBERS,
    SQL_THEME,
    FetchConn,
    MeasureError,
    candidate_measures,
    theme_breadth,
)
from asxos.domain.themes.candidates.types import (
    CANDIDATE_EXPIRY_DAYS,
    THEME_EXPIRY_DAYS,
    CandidateSnapshot,
    ThemeVersion,
    default_expiry,
)

MIN_MEDIAN_DOLLAR_VOLUME_AUD = Decimal("100000")
MAX_PRICE_STALENESS_DAYS = 7
MAX_FACTOR_STALENESS_DAYS = 60


def cutoff_instant(as_of: date) -> datetime:
    return datetime.combine(as_of, time(23, 59, 59), tzinfo=UTC)


def _fact(
    evidence_id: str,
    *,
    evidence_type: str,
    title: str,
    claim: str,
    source_uri: str,
    as_of: date,
    known_at: datetime,
    data_mode: DataMode,
) -> EvidenceItem:
    return EvidenceItem(
        evidence_id=evidence_id,
        evidence_type=evidence_type,  # type: ignore[arg-type]
        title=title[:500],
        claim=claim,
        source_uri=source_uri,
        observed_at=as_of,
        known_at=known_at,
        evidence_tier="verified",
        data_mode=data_mode,
    )


async def build_theme_version(
    conn: FetchConn,
    *,
    theme_code: str,
    as_of: date,
    created_at: datetime | None = None,
    data_mode: DataMode = "real",
    extra_evidence: tuple[EvidenceItem, ...] = (),
    id_prefix: str = "",
) -> ThemeVersion:
    theme = await conn.fetchrow(SQL_THEME, theme_code)
    if theme is None:
        raise MeasureError(f"theme {theme_code!r} does not exist")
    if theme["governance_status"] != "approved":
        raise MeasureError(f"theme {theme_code!r} is {theme['governance_status']}, not approved")
    if theme["retired_at"] is not None and theme["retired_at"] <= as_of:
        raise MeasureError(f"theme {theme_code!r} was retired on {theme['retired_at']}")
    members_rows = await conn.fetch(SQL_MEMBERS, theme["theme_id"])
    if not members_rows:
        raise MeasureError(f"theme {theme_code!r} has no members")
    members = tuple(str(r["symbol"]) for r in members_rows)
    cutoff = cutoff_instant(as_of)
    created = created_at or cutoff

    regime: str | None = None
    macro_id = theme["macro_thesis_id"]
    evidence: list[EvidenceItem] = [
        _fact(
            "theme:row",
            evidence_type="theme_fact",
            title=f"themes.{theme_code} is governed and approved",
            claim=(
                f"themes row theme_code={theme_code} name={theme['name']!r} conviction_band="
                f"{theme['conviction_band']} stage={theme['stage']} governance_status=approved"
            ),
            source_uri=f"db://themes/{theme_code}",
            as_of=as_of, known_at=cutoff, data_mode=data_mode,
        ),
    ]
    for r in members_rows:
        evidence.append(
            _fact(
                f"theme:member:{r['symbol']}",
                evidence_type="theme_fact",
                title=f"{r['symbol']} is a {r['direction']} member of {theme_code}",
                claim=(
                    f"theme_holdings row symbol={r['symbol']} exposure_strength={r['exposure_strength']} "
                    f"direction={r['direction']} mechanism={str(r['mechanism_text'])[:300]!r}"
                ),
                source_uri=f"db://theme_holdings/{theme_code}/{r['symbol']}",
                as_of=as_of, known_at=cutoff, data_mode=data_mode,
            )
        )
    if macro_id is not None:
        macro = await conn.fetchrow(SQL_MACRO, macro_id)
        if macro is not None:
            regime = macro["regime_quadrant"]
            evidence.append(
                _fact(
                    f"theme:macro:{macro_id}",
                    evidence_type="theme_fact",
                    title=f"conditioned by macro thesis #{macro_id}",
                    claim=(
                        f"macro_theses row id={macro_id} title={macro['title']!r} regime_quadrant="
                        f"{macro['regime_quadrant']} governance_status={macro['governance_status']}"
                    ),
                    source_uri=f"db://macro_theses/{macro_id}",
                    as_of=as_of, known_at=cutoff, data_mode=data_mode,
                )
            )

    breadth = await theme_breadth(conn, list(members), as_of)
    measures: dict[str, Any] = {**breadth, "macro_thesis_id": macro_id}
    return ThemeVersion(
        theme_version_id=f"{id_prefix}tv-{theme_code}-{as_of.isoformat()}",
        theme_code=theme_code,
        name=theme["name"],
        description=theme["description"],
        conviction_band=theme["conviction_band"],
        stage=theme["stage"],
        macro_thesis_id=macro_id,
        regime_quadrant=regime,
        members=members,
        measures=measures,
        as_of=as_of,
        knowledge_cutoff=cutoff,
        expires_at=default_expiry(cutoff, days=THEME_EXPIRY_DAYS),
        evidence=tuple(evidence) + tuple(extra_evidence),
        data_mode=data_mode,
        created_at=created,
    )


async def build_candidate_snapshot(
    conn: FetchConn,
    *,
    symbol: str,
    theme: ThemeVersion,
    as_of: date,
    created_at: datetime | None = None,
    extra_evidence: tuple[EvidenceItem, ...] = (),
    id_prefix: str = "",
) -> CandidateSnapshot:
    if symbol not in theme.members:
        raise MeasureError(f"{symbol} is not a member of {theme.theme_code}")
    if as_of != theme.as_of:
        raise MeasureError("candidate as_of must equal its theme version's as_of")
    cutoff = cutoff_instant(as_of)
    created = created_at or cutoff
    m = await candidate_measures(conn, symbol, as_of)

    def _age(iso: object) -> int | None:
        return (as_of - date.fromisoformat(str(iso))).days if iso else None

    price_age = _age(m["last_price_dt"])
    factor_age = _age(m["factor_as_of"])
    median = Decimal(str(m["median_dollar_volume_60d"])) if m["median_dollar_volume_60d"] else None
    checks = {
        "has_sector": "pass" if (m["gics_sector"] or m["factor_sector"]) else "fail",
        "has_factor_scores": "pass" if m["factor_as_of"] and int(m["n_factors_present"] or 0) >= 3 else "fail",
        "factor_scores_fresh": (
            "unknown" if factor_age is None else ("pass" if factor_age <= MAX_FACTOR_STALENESS_DAYS else "fail")
        ),
        "price_fresh": (
            "unknown" if price_age is None else ("pass" if price_age <= MAX_PRICE_STALENESS_DAYS else "fail")
        ),
        "liquid_enough": (
            "unknown" if median is None else ("pass" if median >= MIN_MEDIAN_DOLLAR_VOLUME_AUD else "fail")
        ),
    }
    direction = "positive"
    for e in theme.evidence:
        if e.evidence_id == f"theme:member:{symbol}" and "direction=negative" in e.claim:
            direction = "negative"

    evidence: list[EvidenceItem] = [
        e for e in theme.evidence if e.evidence_id in {"theme:row", f"theme:member:{symbol}"}
    ]
    if m["factor_as_of"]:
        evidence.append(
            _fact(
                f"candidate:factors:{symbol}",
                evidence_type="fundamental_fact",
                title=f"rs_factor_scores for {symbol} at {m['factor_as_of']}",
                claim=(
                    f"rs_factor_scores symbol={symbol} as_of={m['factor_as_of']} sector={m['factor_sector']} "
                    f"value={m['factor_value_score']} quality={m['factor_quality_score']} "
                    f"momentum={m['factor_momentum_score']} low_vol={m['factor_low_vol_score']} "
                    f"yield={m['factor_yield_score']} composite={m['factor_composite_score']} "
                    f"n_factors_present={m['n_factors_present']}"
                ),
                source_uri=f"db://rs_factor_scores/{symbol}/{m['factor_as_of']}",
                as_of=as_of, known_at=cutoff, data_mode=theme.data_mode,
            )
        )
    if m["last_price_dt"]:
        evidence.append(
            _fact(
                f"candidate:price:{symbol}",
                evidence_type="market_fact",
                title=f"{symbol} last close {m['last_close']} on {m['last_price_dt']}",
                claim=(
                    f"prices symbol={symbol} dt={m['last_price_dt']} close={m['last_close']} "
                    f"median_dollar_volume_60d={m['median_dollar_volume_60d']} sessions={m['price_sessions_in_window']}"
                ),
                source_uri=f"db://prices/{symbol}/{m['last_price_dt']}",
                as_of=as_of, known_at=cutoff, data_mode=theme.data_mode,
            )
        )
    return CandidateSnapshot(
        candidate_id=f"{id_prefix}cand-{theme.theme_code}-{symbol}-{as_of.isoformat()}",
        symbol=symbol,
        theme_version_id=theme.theme_version_id,
        theme_code=theme.theme_code,
        exposure_direction=direction,  # type: ignore[arg-type]
        measures=m,
        quality_checks=checks,  # type: ignore[arg-type]
        as_of=as_of,
        knowledge_cutoff=cutoff,
        expires_at=default_expiry(cutoff, days=CANDIDATE_EXPIRY_DAYS),
        evidence=tuple(evidence) + tuple(extra_evidence),
        data_mode=theme.data_mode,
        created_at=created,
    )
