"""Stage 2 gold artefacts for the live daily brief.

Encode / decode / persist / hydrate ``BriefData`` through ``brief_section_gold``.
This module never calls ``collect()``. Hydrate reconstructs renderable
``BriefData`` from stored rows; a missing table is a MISSING section set, not
an exception (the send path still renders). The materialiser lets
``UndefinedTableError`` propagate so GHA compose cannot run against an
unapplied 0047.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import fields, is_dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Protocol

from asxos.brief.compose import (
    NEWS_UNVERIFIED,
    BriefData,
    JobFailure,
    JobProblemKind,
    NewsItem,
    NewsStatus,
    PortfolioSection,
    PortfolioTradeSummary,
    RegulatoryHit,
)
from asxos.brief.deltas import BookDelta, SnapshotLevels
from asxos.brief.section import SECTION_ORDER, SectionResult, SectionStatus
from asxos.domain.benchmark.outcome import (
    BenchmarkState,
    LotOutcome,
    OutcomeSection,
    ReturnState,
    Sleeve,
    SleeveOutcome,
)
from asxos.domain.theses.discipline import DisciplineFinding, DisciplineLevel

GOLD_TABLE = "brief_section_gold"
HEADER_NAME = "header"
DELTAS_NAME = "deltas"
GOLD_NAMES: tuple[str, ...] = (*SECTION_ORDER, HEADER_NAME, DELTAS_NAME)

_UPSERT_SQL = f"""
INSERT INTO {GOLD_TABLE} (
    as_of, section_name, status, computed_at, source, error, payload
) VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb)
ON CONFLICT (as_of, section_name) DO UPDATE SET
    status = EXCLUDED.status,
    computed_at = EXCLUDED.computed_at,
    source = EXCLUDED.source,
    error = EXCLUDED.error,
    payload = EXCLUDED.payload
"""

_SELECT_SQL = f"""
SELECT as_of, section_name, status, computed_at, source, error, payload
FROM {GOLD_TABLE}
WHERE as_of = $1
"""


class GoldConn(Protocol):
    async def execute(self, query: str, *args: object) -> object: ...
    async def fetch(self, query: str, *args: object) -> Sequence[Mapping[str, Any]]: ...


def is_undefined_table(exc: BaseException) -> bool:
    """True when Postgres reports SQLSTATE 42P01 (undefined_table)."""
    if getattr(exc, "sqlstate", None) == "42P01":
        return True
    return type(exc).__name__ in {"UndefinedTableError", "UndefinedTable"}


def _table_from_exc(exc: BaseException) -> str:
    text = str(exc)
    marker = 'relation "'
    if marker in text:
        start = text.index(marker) + len(marker)
        end = text.find('"', start)
        if end > start:
            return text[start:end]
    return GOLD_TABLE


# ---------------------------------------------------------------------------
# JSON codec
# ---------------------------------------------------------------------------


def jsonable(value: object) -> object:
    """Dates ISO, Decimal as strings, dataclasses via field recursion. No secrets."""
    if value is None or isinstance(value, bool | int | str):
        return value
    if isinstance(value, float):
        return value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        return {f.name: jsonable(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [jsonable(v) for v in value]
    raise TypeError(f"cannot encode {type(value).__name__} for gold payload")


def _as_date(value: object) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value[:10])
    raise TypeError(f"not a date: {value!r}")


def _as_dt(value: object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    raise TypeError(f"not a datetime: {value!r}")


def _as_dec(value: object) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _as_enum(enum_cls: type[Any], value: object) -> Any:
    if isinstance(value, enum_cls):
        return value
    return enum_cls(value)


def _payload(value: object) -> object:
    if value is None:
        return None
    if isinstance(value, bytes | bytearray):
        return json.loads(value.decode())
    if isinstance(value, str):
        return json.loads(value)
    return value


# ---------------------------------------------------------------------------
# Encode
# ---------------------------------------------------------------------------


def encode_brief(
    data: BriefData,
) -> list[tuple[date, str, str, datetime | None, str, str | None, object]]:
    """Return gold rows: SECTION_ORDER + header + deltas."""
    sections = data.sections or data.resolved_sections
    rows: list[tuple[date, str, str, datetime | None, str, str | None, object]] = []
    for name in SECTION_ORDER:
        section = sections.get(name)
        if section is None:
            rows.append(
                (
                    data.as_of,
                    name,
                    SectionStatus.MISSING.value,
                    None,
                    "gold.encode",
                    f"gold row absent: {name} as_of={data.as_of}",
                    None,
                )
            )
            continue
        payload = None if section.status is SectionStatus.MISSING else jsonable(section.data)
        rows.append(
            (
                data.as_of,
                name,
                section.status.value,
                section.computed_at,
                section.source,
                section.error,
                payload,
            )
        )
    header_payload = {
        "holdings_count": data.holdings_count,
        "latest_price_date": jsonable(data.latest_price_date),
        "data_as_of": jsonable(data.data_as_of),
        "news_status": str(data.news_status),
        "outcome_error": data.outcome_error,
    }
    computed = next((s.computed_at for s in sections.values() if s.computed_at is not None), None)
    rows.append(
        (
            data.as_of,
            HEADER_NAME,
            SectionStatus.FRESH.value,
            computed or datetime.now(UTC),
            "gold.encode",
            None,
            header_payload,
        )
    )
    if data.deltas is None:
        deltas_status = SectionStatus.EMPTY.value
        deltas_payload: object = None
    else:
        deltas_status = SectionStatus.FRESH.value
        deltas_payload = jsonable(data.deltas)
    rows.append(
        (
            data.as_of,
            DELTAS_NAME,
            deltas_status,
            computed or datetime.now(UTC),
            "gold.encode",
            None,
            deltas_payload,
        )
    )
    return rows


# ---------------------------------------------------------------------------
# Decode — reconstruct types so render_html works
# ---------------------------------------------------------------------------


def _decode_finding(item: object) -> DisciplineFinding:
    raw = item if isinstance(item, Mapping) else {}
    symbol = raw.get("symbol")
    return DisciplineFinding(
        check=str(raw.get("check", "")),
        level=_as_enum(DisciplineLevel, raw.get("level", DisciplineLevel.info)),
        message=str(raw.get("message", "")),
        symbol=str(symbol) if symbol is not None else None,
        watchlist_only=bool(raw.get("watchlist_only", False)),
    )


def _decode_job(item: object) -> JobFailure:
    raw = item if isinstance(item, Mapping) else {}
    as_of = _as_date(raw.get("as_of")) or date.min
    return JobFailure(
        job_name=str(raw.get("job_name", "")),
        as_of=as_of,
        error_message=str(raw.get("error_message", "")),
        kind=_as_enum(JobProblemKind, raw.get("kind", JobProblemKind.FAILURE)),
    )


def _decode_news(item: object) -> NewsItem:
    raw = item if isinstance(item, Mapping) else {}
    symbols = raw.get("symbols") or []
    published = _as_date(raw.get("published_at")) or date.min
    return NewsItem(
        symbols=[str(s) for s in symbols],
        title=str(raw.get("title", "")),
        url=str(raw.get("url", "")),
        published_at=published,
        sentiment=str(raw.get("sentiment", "")),
    )


def _decode_reg(item: object) -> RegulatoryHit:
    raw = item if isinstance(item, Mapping) else {}
    published = _as_date(raw.get("published_at")) or date.min
    return RegulatoryHit(
        symbol=str(raw.get("symbol", "")),
        source=str(raw.get("source", "")),
        title=str(raw.get("title", "")),
        published_at=published,
        kind=str(raw.get("kind", "")),
    )


def _decode_trade(item: object) -> PortfolioTradeSummary:
    raw = item if isinstance(item, Mapping) else {}
    delta = _as_dec(raw.get("delta_aud")) or Decimal("0")
    return PortfolioTradeSummary(
        symbol=str(raw.get("symbol", "")),
        side=str(raw.get("side", "")),
        delta_aud=delta,
    )


def _decode_portfolio(payload: object) -> PortfolioSection | None:
    if not isinstance(payload, Mapping):
        return None
    run_as_of = _as_date(payload.get("run_as_of"))
    if run_as_of is None:
        return None
    return PortfolioSection(
        run_id=int(payload.get("run_id") or 0),
        run_as_of=run_as_of,
        top_buys=[_decode_trade(t) for t in (payload.get("top_buys") or [])],
        top_sells=[_decode_trade(t) for t in (payload.get("top_sells") or [])],
        total_buy_aud=_as_dec(payload.get("total_buy_aud")) or Decimal("0"),
        total_sell_aud=_as_dec(payload.get("total_sell_aud")) or Decimal("0"),
        turnover_aud=_as_dec(payload.get("turnover_aud")) or Decimal("0"),
    )


def _decode_window(value: object) -> tuple[date, date] | None:
    if not isinstance(value, list | tuple) or len(value) != 2:
        return None
    start, end = _as_date(value[0]), _as_date(value[1])
    if start is None or end is None:
        return None
    return start, end


def _decode_lot(item: object) -> LotOutcome:
    raw = item if isinstance(item, Mapping) else {}
    acquired = _as_date(raw.get("acquired_at")) or date.min
    return LotOutcome(
        lot_id=int(raw.get("lot_id") or 0),
        symbol=str(raw.get("symbol", "")),
        sleeve=_as_enum(Sleeve, raw.get("sleeve", Sleeve.asx)),
        quantity=_as_dec(raw.get("quantity")) or Decimal("0"),
        acquired_at=acquired,
        cost_base_aud=_as_dec(raw.get("cost_base_aud")) or Decimal("0"),
        market_value_aud=_as_dec(raw.get("market_value_aud")),
        lot_return=_as_dec(raw.get("lot_return")),
        return_state=_as_enum(ReturnState, raw.get("return_state", ReturnState.measured)),
        return_note=str(raw.get("return_note", "")),
        priced_at=_as_date(raw.get("priced_at")),
        benchmark_return=_as_dec(raw.get("benchmark_return")),
        benchmark_state=_as_enum(
            BenchmarkState, raw.get("benchmark_state", BenchmarkState.measured)
        ),
        benchmark_note=str(raw.get("benchmark_note", "")),
        benchmark_window=_decode_window(raw.get("benchmark_window")),
        alpha=_as_dec(raw.get("alpha")),
    )


def _decode_sleeve(item: object) -> SleeveOutcome:
    raw = item if isinstance(item, Mapping) else {}
    lots = tuple(_decode_lot(x) for x in (raw.get("lots") or []))
    return SleeveOutcome(
        sleeve=_as_enum(Sleeve, raw.get("sleeve", Sleeve.asx)),
        label=str(raw.get("label", "")),
        benchmark_label=str(raw.get("benchmark_label", "")),
        lots=lots,
        empty_note=str(raw.get("empty_note", "")),
    )


def _decode_outcome(payload: object) -> OutcomeSection | None:
    if not isinstance(payload, Mapping):
        return None
    as_of = _as_date(payload.get("as_of"))
    if as_of is None:
        return None
    sleeves = tuple(_decode_sleeve(s) for s in (payload.get("sleeves") or []))
    return OutcomeSection(as_of=as_of, sleeves=sleeves)


def _decode_levels(payload: object) -> SnapshotLevels | None:
    if not isinstance(payload, Mapping):
        return None
    as_of = _as_date(payload.get("as_of"))
    if as_of is None:
        return None
    return SnapshotLevels(
        as_of=as_of,
        capital_aud=_as_dec(payload.get("capital_aud")) or Decimal("0"),
        holdings_mv_aud=_as_dec(payload.get("holdings_mv_aud")) or Decimal("0"),
        cash_aud=_as_dec(payload.get("cash_aud")) or Decimal("0"),
        holdings_count=int(payload.get("holdings_count") or 0),
    )


def _decode_deltas(payload: object) -> BookDelta | None:
    if not isinstance(payload, Mapping):
        return None
    return BookDelta(
        current=_decode_levels(payload.get("current")),
        prior=_decode_levels(payload.get("prior")),
        prior_job_finished_at=_as_dt(payload.get("prior_job_finished_at")),
        prior_brief_composed_at=_as_dt(payload.get("prior_brief_composed_at")),
    )


def _seq(value: object) -> list[object]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


def _decode_prices_data(payload: object) -> dict[str, date | None] | None:
    if not isinstance(payload, Mapping):
        return None
    return {
        "latest_price_date": _as_date(payload.get("latest_price_date")),
        "data_as_of": _as_date(payload.get("data_as_of")),
    }


def _decode_section_data(name: str, status: SectionStatus, payload: object) -> object | None:
    if status is SectionStatus.MISSING:
        return None
    if name == "prices":
        return _decode_prices_data(payload)
    if name == "jobs":
        return [_decode_job(x) for x in _seq(payload)]
    if name == "discipline":
        return [_decode_finding(x) for x in _seq(payload)]
    if name == "outcome":
        return _decode_outcome(payload)
    if name == "regulatory":
        return [_decode_reg(x) for x in _seq(payload)]
    if name == "news":
        return [_decode_news(x) for x in _seq(payload)]
    if name == "portfolio":
        return _decode_portfolio(payload)
    return payload


def _section_from_row(name: str, row: Mapping[str, Any]) -> SectionResult:
    status = _as_enum(SectionStatus, row["status"])
    error = row.get("error")
    error_s = str(error) if error is not None else None
    if status is SectionStatus.MISSING and not error_s:
        as_of = _as_date(row.get("as_of"))
        error_s = f"gold row absent: {name} as_of={as_of}"
    data = _decode_section_data(name, status, _payload(row.get("payload")))
    return SectionResult(
        name=name,
        status=status,
        data=data,
        computed_at=_as_dt(row.get("computed_at")),
        source=str(row.get("source") or ""),
        error=error_s,
    )


def _missing_section(name: str, as_of: date, error: str) -> SectionResult:
    return SectionResult(
        name=name,
        status=SectionStatus.MISSING,
        data=None,
        computed_at=None,
        source="gold.hydrate",
        error=error,
    )


def decode_brief(as_of: date, rows: Sequence[Mapping[str, Any]]) -> BriefData:
    """Rebuild BriefData from gold rows. Absent names become MISSING, not EMPTY."""
    by_name: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        name = str(row["section_name"])
        by_name[name] = row

    sections: dict[str, SectionResult] = {}
    for name in SECTION_ORDER:
        stored = by_name.get(name)
        if stored is None:
            sections[name] = _missing_section(name, as_of, f"gold row absent: {name} as_of={as_of}")
        else:
            sections[name] = _section_from_row(name, stored)

    header_row = by_name.get(HEADER_NAME)
    header = _payload(header_row["payload"]) if header_row is not None else None
    header_map = header if isinstance(header, Mapping) else {}

    holdings_count = int(header_map.get("holdings_count") or 0)
    latest_price_date = _as_date(header_map.get("latest_price_date"))
    data_as_of = _as_date(header_map.get("data_as_of"))
    outcome_error = header_map.get("outcome_error")
    outcome_error_s = str(outcome_error) if outcome_error is not None else None
    try:
        news_status = _as_enum(NewsStatus, header_map.get("news_status", NEWS_UNVERIFIED))
    except (TypeError, ValueError):
        news_status = NEWS_UNVERIFIED

    news_section = sections["news"]
    if news_section.status is SectionStatus.MISSING:
        news_status = NEWS_UNVERIFIED

    prices_data = sections["prices"].data
    if isinstance(prices_data, Mapping):
        if latest_price_date is None:
            latest_price_date = _as_date(prices_data.get("latest_price_date"))
        if data_as_of is None:
            data_as_of = _as_date(prices_data.get("data_as_of"))

    def _list(name: str) -> list[Any]:
        payload = sections[name].data
        return list(payload) if isinstance(payload, list) else []

    job_failures = _list("jobs")
    discipline_findings = _list("discipline")
    regulatory_hits = _list("regulatory")
    news_items = _list("news")

    outcome_section: OutcomeSection | None = None
    if sections["outcome"].status is not SectionStatus.MISSING:
        raw_out = sections["outcome"].data
        outcome_section = raw_out if isinstance(raw_out, OutcomeSection) else None

    portfolio_section: PortfolioSection | None = None
    if sections["portfolio"].status is not SectionStatus.MISSING:
        raw_port = sections["portfolio"].data
        portfolio_section = raw_port if isinstance(raw_port, PortfolioSection) else None

    deltas: BookDelta | None = None
    deltas_row = by_name.get(DELTAS_NAME)
    if deltas_row is not None:
        deltas_status = _as_enum(SectionStatus, deltas_row["status"])
        if deltas_status is not SectionStatus.MISSING:
            deltas = _decode_deltas(_payload(deltas_row.get("payload")))

    return BriefData(
        as_of=as_of,
        holdings_count=holdings_count,
        regulatory_hits=regulatory_hits,
        job_failures=job_failures,
        news_items=news_items,
        news_status=news_status,
        portfolio_section=portfolio_section,
        discipline_findings=discipline_findings,
        outcome_section=outcome_section,
        outcome_error=outcome_error_s,
        latest_price_date=latest_price_date,
        data_as_of=data_as_of,
        sections=sections,
        deltas=deltas,
    )


def _missing_table_brief(as_of: date, exc: BaseException) -> BriefData:
    table = _table_from_exc(exc)
    error = f"gold table missing: {table} ({exc})"
    sections = {name: _missing_section(name, as_of, error) for name in SECTION_ORDER}
    return BriefData(
        as_of=as_of,
        holdings_count=0,
        news_status=NEWS_UNVERIFIED,
        sections=sections,
        deltas=None,
    )


# ---------------------------------------------------------------------------
# Persist / hydrate
# ---------------------------------------------------------------------------


async def persist(conn: GoldConn, data: BriefData) -> None:
    """Sequential upserts. Does not catch UndefinedTableError — fail loud."""
    for as_of, name, status, computed_at, source, error, payload in encode_brief(data):
        payload_json = json.dumps(payload) if payload is not None else None
        await conn.execute(
            _UPSERT_SQL,
            as_of,
            name,
            status,
            computed_at,
            source,
            error,
            payload_json,
        )


async def hydrate(conn: GoldConn, as_of: date) -> BriefData:
    """Read gold rows. Never calls collect(). Missing table → all MISSING."""
    try:
        rows = await conn.fetch(_SELECT_SQL, as_of)
    except Exception as exc:
        if is_undefined_table(exc):
            return _missing_table_brief(as_of, exc)
        raise
    return decode_brief(as_of, list(rows))
