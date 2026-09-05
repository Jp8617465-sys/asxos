"""Replay one symbol at one cutoff using only facts knowable by then.

Two rules make this a replay rather than a lookup:

* **Provenance, not just date.** A `rs_fundamentals_pit` row is admitted only
  when `knowledge_date <= cutoff` AND `knowledge_tier = 'filed'`. `estimated`
  rows carry `period_end + lag_days`, a convention rather than an event, and
  `NULL` rows were written before migration 0049 and are "not yet classified".
  Neither is evidence that anyone knew the figures by the cutoff, so both are
  excluded by default and the exclusion is reported, not hidden. `require_filed=
  False` opts back in for exploratory use and is recorded in the snapshot so the
  hash of an opted-in replay can never masquerade as a strict one.

* **The price as it was known, not as it is now.** `prices` is a serving
  projection that migration 0043 allows to be corrected in place; every such
  correction is written to the append-only `price_revisions` ledger in the
  same transaction. A revision recorded AFTER the cutoff means the row visible
  today is not the row that was visible then. The replay therefore reads the
  ledger and reports `prior_close` of the earliest post-cutoff revision as the
  as-known value. With zero revisions (the live state on 2026-09-02) the two
  agree; the machinery exists so that the first revision does not silently
  rewrite history under a replay that claims to be point-in-time.

All identifiers are constants; all values are bound. Every figure is emitted as
a decimal string so the snapshot is JSON-native and hashes deterministically.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from decimal import Decimal
from typing import Final, Literal, Protocol

from asxos.domain.results_review.contracts import hash_document_payload
from asxos.domain.results_review.pit_db import validate_symbol

REPLAY_VERSION: Final[str] = "1"

# Same discipline as results_review.pit_db: a SELECT list that names a column
# from the forbidden families cannot be admitted, however it got there. Tokens
# are matched as substrings. `price_revisions` is admissible here and not in
# pit_db because the ledger IS the point-in-time correction record.
_FORBIDDEN: Final[tuple[str, ...]] = (
    "shap_factors", "prob_up", "signal_label", "model_a", "holding_lots",
    "theses", "thesis_", "screening_rules", "screening_runs", "line_items",
    "job_runs", "tax_",
)
_ADMISSIBLE_TABLES: Final[frozenset[str]] = frozenset(
    {"rs_security_master", "rs_fundamentals_pit", "prices", "price_revisions"}
)

SQL_SECURITY: Final[str] = "SELECT symbol FROM rs_security_master WHERE symbol = $1"

# The most recent PIT row knowable at the cutoff, whatever its tier. Tier
# filtering happens in Python so the snapshot can SAY why a row was excluded —
# a WHERE clause would just make it vanish.
SQL_PIT_LATEST: Final[str] = (
    "SELECT symbol, as_of, knowledge_date, knowledge_tier, revenue_ttm, "
    "net_income_ttm, eps_ttm, book_value_ps, roe, net_debt, currency "
    "FROM rs_fundamentals_pit "
    "WHERE symbol = $1 AND knowledge_date <= $2 "
    "ORDER BY knowledge_date DESC LIMIT 1"
)
# The most recent FILED row knowable at the cutoff — used when the latest row
# by date is not admissible, so a strict replay still finds the best evidence
# that WAS admissible rather than reporting "absent".
SQL_PIT_LATEST_FILED: Final[str] = (
    "SELECT symbol, as_of, knowledge_date, knowledge_tier, revenue_ttm, "
    "net_income_ttm, eps_ttm, book_value_ps, roe, net_debt, currency "
    "FROM rs_fundamentals_pit "
    "WHERE symbol = $1 AND knowledge_date <= $2 AND knowledge_tier = 'filed' "
    "ORDER BY knowledge_date DESC LIMIT 1"
)
SQL_PRICE_LATEST: Final[str] = (
    "SELECT symbol, dt, close, adj_close FROM prices "
    "WHERE symbol = $1 AND dt <= $2 ORDER BY dt DESC LIMIT 1"
)
SQL_PRICE_REVISIONS: Final[str] = (
    "SELECT revision_id, operation, prior_close, replacement_close, recorded_at "
    "FROM price_revisions "
    "WHERE prior_symbol = $1 AND prior_dt = $2 "
    "ORDER BY recorded_at ASC, revision_id ASC"
)

FundamentalsStatus = Literal[
    "included", "excluded_untiered", "excluded_estimated", "absent"
]
PriceStatus = Literal["included", "absent"]


class FetchConn(Protocol):
    async def fetchrow(self, sql: str, *args: object) -> object: ...
    async def fetch(self, sql: str, *args: object) -> list[object]: ...


class ReplayError(RuntimeError):
    """A replay could not be assembled honestly. Never silently degraded."""


def assert_replay_sql_admissible(sql: str) -> None:
    lowered = sql.lower()
    for token in _FORBIDDEN:
        if token in lowered:
            raise ReplayError(f"forbidden token {token!r} in replay SQL")
    tables = {
        word.strip(",;")
        for prev, word in zip(lowered.split(), lowered.split()[1:], strict=False)
        if prev in {"from", "join"}
    }
    if not tables or not tables <= _ADMISSIBLE_TABLES:
        raise ReplayError(f"replay SQL touches non-admissible table(s): {sorted(tables)}")


for _sql in (SQL_SECURITY, SQL_PIT_LATEST, SQL_PIT_LATEST_FILED, SQL_PRICE_LATEST, SQL_PRICE_REVISIONS):
    assert_replay_sql_admissible(_sql)


def _dec_str(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, float):
        raise ReplayError("float reached the replay — every figure must be Decimal")
    if isinstance(value, Decimal):
        return format(value, "f")
    return str(value)


def _date_str(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)[:10]


def cutoff_instant(cutoff: date) -> datetime:
    """End of the cutoff day, UTC — the same convention results_review uses."""
    return datetime.combine(cutoff, time(23, 59, 59), tzinfo=UTC)


@dataclass(frozen=True)
class ReplaySnapshot:
    """JSON-native. `payload` is what gets hashed; the fields beside it are views."""

    payload: dict[str, object]
    fundamentals_status: FundamentalsStatus
    price_status: PriceStatus

    @property
    def hash(self) -> str:
        return snapshot_hash(self)


def snapshot_hash(snapshot: ReplaySnapshot) -> str:
    return hash_document_payload(snapshot.payload)


async def replay_snapshot(
    conn: FetchConn,
    *,
    symbol: str,
    cutoff: date,
    require_filed: bool = True,
) -> ReplaySnapshot:
    """Assemble the facts knowable for `symbol` at end-of-day `cutoff` (UTC)."""
    symbol = validate_symbol(symbol)
    if await conn.fetchrow(SQL_SECURITY, symbol) is None:
        raise ReplayError(f"{symbol} is absent from rs_security_master")

    # --- fundamentals -----------------------------------------------------
    latest = await conn.fetchrow(SQL_PIT_LATEST, symbol, cutoff)
    fundamentals: dict[str, object]
    f_status: FundamentalsStatus
    if latest is None:
        f_status, chosen, excluded = "absent", None, None
    else:
        tier = latest["knowledge_tier"]  # type: ignore[index]
        if tier == "filed" or not require_filed:
            f_status, chosen, excluded = "included", latest, None
        else:
            excluded = latest
            f_status = "excluded_untiered" if tier is None else "excluded_estimated"
            # Strict mode still wants the best ADMISSIBLE evidence, if any.
            chosen = await conn.fetchrow(SQL_PIT_LATEST_FILED, symbol, cutoff)
            if chosen is not None:
                f_status = "included"

    def _pit_row(row: object) -> dict[str, object] | None:
        if row is None:
            return None
        r = row
        return {
            "as_of": _date_str(r["as_of"]),  # type: ignore[index]
            "knowledge_date": _date_str(r["knowledge_date"]),  # type: ignore[index]
            "knowledge_tier": r["knowledge_tier"],  # type: ignore[index]
            "revenue_ttm": _dec_str(r["revenue_ttm"]),  # type: ignore[index]
            "net_income_ttm": _dec_str(r["net_income_ttm"]),  # type: ignore[index]
            "eps_ttm": _dec_str(r["eps_ttm"]),  # type: ignore[index]
            "book_value_ps": _dec_str(r["book_value_ps"]),  # type: ignore[index]
            "roe": _dec_str(r["roe"]),  # type: ignore[index]
            "net_debt": _dec_str(r["net_debt"]),  # type: ignore[index]
            "currency": r["currency"],  # type: ignore[index]
        }

    fundamentals = {
        "status": f_status,
        "row": _pit_row(chosen),
        # What a date-only replay WOULD have used, so the exclusion is auditable.
        "latest_by_date_excluded": _pit_row(excluded),
    }

    # --- price, as known at the cutoff ------------------------------------
    price_row = await conn.fetchrow(SQL_PRICE_LATEST, symbol, cutoff)
    p_status: PriceStatus
    if price_row is None:
        p_status = "absent"
        price: dict[str, object] = {"status": p_status, "row": None}
    else:
        p_status = "included"
        pr = price_row
        dt = pr["dt"]  # type: ignore[index]
        revisions = await conn.fetch(SQL_PRICE_REVISIONS, symbol, dt)
        instant = cutoff_instant(cutoff)
        post_cutoff = [
            rv for rv in revisions
            if rv["recorded_at"] > instant  # type: ignore[index]
        ]
        current_close = _dec_str(pr["close"])  # type: ignore[index]
        if post_cutoff:
            first = post_cutoff[0]
            as_known = _dec_str(first["prior_close"])  # type: ignore[index]
            as_known_source = f"price_revisions.revision_id={first['revision_id']}.prior_close"  # type: ignore[index]
        else:
            as_known = current_close
            as_known_source = "prices.close (no post-cutoff revision)"
        price = {
            "status": p_status,
            "row": {
                "dt": _date_str(dt),
                "close_now": current_close,
                "adj_close_now": _dec_str(pr["adj_close"]),  # type: ignore[index]
                "close_as_known_at_cutoff": as_known,
                "as_known_source": as_known_source,
                "revisions_total": len(revisions),
                "revisions_after_cutoff": len(post_cutoff),
            },
        }

    payload: dict[str, object] = {
        "replay_version": REPLAY_VERSION,
        "symbol": symbol,
        "cutoff": cutoff.isoformat(),
        "cutoff_instant_utc": cutoff_instant(cutoff).isoformat(),
        "require_filed": require_filed,
        "fundamentals": fundamentals,
        "price": price,
        "not_included": [
            "signals (rule #11 — frozen Model A output is never replay evidence)",
            "holdings, theses, tax (capital-facing; a replay is evidence, not a decision)",
        ],
    }
    return ReplaySnapshot(payload=payload, fundamentals_status=f_status, price_status=p_status)
