"""Measured inputs for the challenge and sizer, read from the live book.

Every figure the Layer-1 rules consume is MEASURED here from the same tables
the daily snapshot job reads (`portfolio_daily_snapshots`, `current_holdings`,
`prices`, `fx_rates`, `universe`, `profiles`) — never inferred. Foreign
holdings are converted with the same AUDUSD convention as
`jobs/snapshot_portfolio.py` (USD → AUD = close / rate).

**Personal-use firewall.** These loaders read holdings, cash and the active
profile — personal financial data under s766B. Every public function here
checks `ASXOS_PERSONAL_USE == "1"` itself — including the price and candidate
readers, which touch no holdings today but sit one edit away from a caller
that does — and the `asx decision` CLI checks it again before calling. A
`security-engineer` pass (2026-09-03) found this sentence true of only two of
the five; the gates were added rather than the sentence weakened. A future brief surface carrying a
non-zero `SizeRange` must additionally honour `ASXOS_PORTFOLIO_BRIEF_ENABLED`
(the portfolio conventions rule file, §Regulatory firewall).

**Borrowing.** asxos has no borrowing ledger and D2 pins gross leverage at
0%, so `borrowing_aud` is reported as 0 with that reason recorded here —
it is an asserted invariant of the system, not a measurement.

Positive-control selection (arbi decision D-5, Stage 4): the top
`CandidateSnapshot` by quality among ordinary ASX equities, excluding the
negative-control names (HUBS, CBA, ESS). With one governed theme member
today (CBA.AU), this returns `None` until a second member is approved —
reported, not worked around.
"""
from __future__ import annotations

import json
import os
from collections.abc import Mapping
from datetime import date
from decimal import ROUND_HALF_EVEN, Decimal
from typing import Any, Final, Protocol

from asxos.domain.decision_engine.challenge.rules import (
    CASH_FLOOR_PCT,
    SECTOR_CAP_PCT,
    PortfolioState,
)
from asxos.domain.decision_engine.sizer import SizingPolicy, VolInput
from asxos.domain.portfolio.volatility import annualised_vol_from_prices
from asxos.domain.prices.fx import is_foreign_symbol
from asxos.domain.themes.candidates.types import CandidateSnapshot

_Q6: Final = Decimal("0.000001")
_HUNDRED: Final = Decimal("100")
NEGATIVE_CONTROLS: Final[frozenset[str]] = frozenset({"CBA.AU", "HUBS.NYSE", "HUBS.US", "ESS.AU"})

SQL_SNAPSHOT: Final[str] = (
    "SELECT as_of, capital_aud, holdings_mv_aud, cash_aud FROM portfolio_daily_snapshots "
    "WHERE as_of <= $1 ORDER BY as_of DESC LIMIT 1"
)
SQL_HOLDINGS: Final[str] = (
    "SELECT ch.symbol, SUM(ch.quantity) AS quantity, MAX(u.sector) AS sector "
    "FROM current_holdings ch LEFT JOIN universe u ON u.symbol = ch.symbol "
    "GROUP BY ch.symbol ORDER BY ch.symbol"
)
SQL_CLOSE: Final[str] = "SELECT dt, close FROM prices WHERE symbol = $1 AND dt <= $2 ORDER BY dt DESC LIMIT 1"
SQL_CLOSES: Final[str] = "SELECT close FROM prices WHERE symbol = $1 AND dt <= $2 ORDER BY dt DESC LIMIT $3"
SQL_FX: Final[str] = "SELECT rate FROM fx_rates WHERE pair = 'AUDUSD' AND dt <= $1 ORDER BY dt DESC LIMIT 1"
SQL_PROFILE: Final[str] = (
    "SELECT capital_aud, cash_floor_pct, per_name_cap_pct, sector_cap_pct, min_position_aud "
    "FROM profiles WHERE is_active = TRUE LIMIT 1"
)
SQL_CANDIDATES: Final[str] = (
    "SELECT payload FROM candidate_snapshots WHERE as_of <= $1 AND expires_at > $2 ORDER BY as_of DESC, symbol"
)


class StateConn(Protocol):
    async def fetchrow(self, query: str, *args: object) -> Any: ...
    async def fetch(self, query: str, *args: object) -> list[Any]: ...


class PersonalUseRequired(RuntimeError):
    """The s766B firewall flag is not set."""


def require_personal_use() -> None:
    if os.environ.get("ASXOS_PERSONAL_USE") != "1":
        raise PersonalUseRequired(
            "portfolio-state loaders require ASXOS_PERSONAL_USE=1 (s766B personal-advice firewall)"
        )


def _q(value: Decimal) -> Decimal:
    return value.quantize(_Q6, rounding=ROUND_HALF_EVEN)


def _dec(value: object) -> Decimal:
    if isinstance(value, float):
        raise TypeError("float reached the portfolio-state loader")
    return Decimal(str(value))


async def load_portfolio_state(conn: StateConn, as_of: date) -> PortfolioState:
    require_personal_use()
    snap = await conn.fetchrow(SQL_SNAPSHOT, as_of)
    if snap is None:
        raise RuntimeError(f"no portfolio_daily_snapshots row on or before {as_of}")
    capital = _dec(snap["capital_aud"])
    cash = _dec(snap["cash_aud"])
    if capital <= 0:
        raise RuntimeError("snapshot capital_aud must be positive")
    fx_row = await conn.fetchrow(SQL_FX, as_of)
    audusd = _dec(fx_row["rate"]) if fx_row else None

    sector_weights: dict[str, Decimal] = {}
    position_weights: dict[str, Decimal] = {}
    gross = Decimal("0")
    for row in await conn.fetch(SQL_HOLDINGS):
        symbol = str(row["symbol"])
        price_row = await conn.fetchrow(SQL_CLOSE, symbol, as_of)
        if price_row is None:
            raise RuntimeError(f"no price on or before {as_of} for held symbol {symbol}")
        close = _dec(price_row["close"])
        if is_foreign_symbol(symbol):
            if audusd is None:
                raise RuntimeError(f"no AUDUSD rate on or before {as_of}; cannot value {symbol}")
            close = close / audusd
        mv = _dec(row["quantity"]) * close
        weight = _q(mv / capital * _HUNDRED)
        gross += weight
        position_weights[symbol] = weight
        sector = str(row["sector"]) if row["sector"] else "UNKNOWN"
        sector_weights[sector] = _q(sector_weights.get(sector, Decimal("0")) + weight)
    return PortfolioState(
        capital_aud=_q(capital),
        cash_pct=_q(cash / capital * _HUNDRED),
        gross_exposure_pct=_q(gross),
        borrowing_aud=Decimal("0"),  # no borrowing ledger exists; D2 pins LVR at 0 — asserted, see module docstring
        sector_weights_pct=sector_weights,
        position_weights_pct=position_weights,
        evidence_id=f"portfolio-state-{snap['as_of'].isoformat()}",
    )


async def load_sizing_policy(conn: StateConn) -> SizingPolicy:
    """The active profile's caps, never looser than the register."""
    require_personal_use()
    row = await conn.fetchrow(SQL_PROFILE)
    if row is None:
        raise RuntimeError("no active profile")
    return SizingPolicy(
        capital_aud=_dec(row["capital_aud"]),
        position_cap_pct=_q(_dec(row["per_name_cap_pct"]) * _HUNDRED),
        min_position_aud=_dec(row["min_position_aud"]),
        cash_floor_pct=max(CASH_FLOOR_PCT, _q(_dec(row["cash_floor_pct"]) * _HUNDRED)),
        sector_cap_pct=min(SECTOR_CAP_PCT, _q(_dec(row["sector_cap_pct"]) * _HUNDRED)),
    )


async def load_annualised_vol(conn: StateConn, symbol: str, as_of: date, *, window_days: int = 60) -> Decimal | None:
    """Annualised vol from the last `window_days + 1` closes, or None if history is short."""
    require_personal_use()
    rows = await conn.fetch(SQL_CLOSES, symbol, as_of, window_days + 1)
    closes = [_dec(r["close"]) for r in reversed(rows)]
    if len(closes) < window_days + 1:
        return None
    return _q(annualised_vol_from_prices(closes, window_days=window_days))


async def load_peer_vols(conn: StateConn, state: PortfolioState, as_of: date) -> tuple[VolInput, ...]:
    require_personal_use()
    out: list[VolInput] = []
    for symbol in sorted(state.position_weights_pct):
        vol = await load_annualised_vol(conn, symbol, as_of)
        if vol is not None and vol > 0:
            out.append(VolInput(symbol=symbol, annualised_vol=vol))
    return tuple(out)


def _payload(row: Mapping[str, object]) -> dict[str, Any]:
    raw = row["payload"]
    if isinstance(raw, str):
        return dict(json.loads(raw))
    if isinstance(raw, Mapping):
        return dict(raw)
    raise TypeError(f"unexpected payload column type: {type(raw)!r}")


def rank_positive_controls(candidates: tuple[CandidateSnapshot, ...]) -> tuple[CandidateSnapshot, ...]:
    """Ordinary ASX equities only, negative controls excluded, best quality first
    (passed checks desc, median dollar volume desc, symbol asc)."""
    eligible = [
        c for c in candidates
        if c.symbol.endswith(".AU") and c.symbol not in NEGATIVE_CONTROLS and c.quality_passed
    ]

    def key(c: CandidateSnapshot) -> tuple[int, Decimal, str]:
        passed = sum(1 for v in c.quality_checks.values() if v == "pass")
        adv = c.measures.get("median_dollar_volume_60d")
        return (-passed, -Decimal(str(adv)) if adv else Decimal("0"), c.symbol)

    return tuple(sorted(eligible, key=key))


async def select_positive_control(conn: StateConn, as_of: date, *, now: date) -> CandidateSnapshot | None:
    require_personal_use()
    rows = await conn.fetch(SQL_CANDIDATES, as_of, now)
    candidates = tuple(CandidateSnapshot.model_validate(_payload(r)) for r in rows)
    ranked = rank_positive_controls(candidates)
    return ranked[0] if ranked else None
