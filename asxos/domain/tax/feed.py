"""
The G12 tax feed (F-E2E r2 S9): a security-level dividend characterisation from
`rs_corporate_actions`, and the `TaxAssessmentReference` it earns.

What a `pass` asserts — ruled by arbi under James's 2026-09-16 delegation
(decision-log row sprint-r2-s9, A-31 decision 1): **a security-level
characterisation only.** Real, point-in-time dividend events for the security
exist in the research store for the trailing 365 calendar days and every one
of them carries a declared cash amount and a declared franking percentage. It
asserts nothing about a position, a quantity, an account type or an after-tax
dollar figure — those are position-level producers (`TAX_ASSESSMENT_PRODUCERS`
in `results_review/contracts.py`) that need a holding this packet does not
have. `applicability` is `applicable` only for an ASX (`.AU`) security: the
franking regime in spec §3 is Australian, and every other exchange keeps the
unresolved reference.

Missing franking (A-31 decision 2): a NULL `franking_pct` is **undeclared,
never 0** (migration 0027:57; `ingestion/corporate_actions.py`). An undeclared
value inside the window blocks the pass — readiness stays `unknown` and the
row is named — and spec §3 / §10 are amended (v1.7) so "treat as unfranked"
applies only to an explicitly declared 0%. No carry-forward, no inference.

`tax_settings` (A-31 decision 3) stays unread: a security-level
characterisation is the gross-up alone (spec §3), which needs neither a
marginal rate nor an account type. The per-share franking credit uses the
spec's validation formula with `DEFAULT_CORPORATE_TAX_RATE`;
`universe.corporate_tax_rate` is still unread, so a base-rate entity's credit
is overstated here and the claim says so.

Point in time: a dividend row becomes known at 23:59:59 UTC on its ex-date
(the `derive_statement_known_at` end-of-day convention), so a row whose
ex-date is the cutoff's own day is not knowable at a morning cutoff. Rows
after the cutoff are dropped in Python, never trusted to the SQL alone.

Pure functions first; the one DB read sits at the bottom behind a Protocol
and is fenced against every rule #11 token at import.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from itertools import pairwise
from typing import Any, Final, Literal, Protocol

from asxos.domain.decision_engine.types import TaxAssessmentReference
from asxos.domain.tax.franking import franking_credit
from asxos.domain.tax.types import DEFAULT_CORPORATE_TAX_RATE, Dividend

#: Trailing window for the characterisation, calendar days (an annual payer
#: whose last ex-date is 366 days old is `unknown`, not `fail` — stated, not padded).
WINDOW_DAYS: Final[int] = 365
KNOWN_AT_UTC_TIME: Final[time] = time(23, 59, 59)
_Q6: Final[Decimal] = Decimal("0.000001")

_FORBIDDEN: Final[tuple[str, ...]] = (
    r"\bsignals\b", r"\bshap_", r"\bprob_up\b", r"\bsignal_label\b", r"\bmodel_a\b",
    r"\bexpected_return\b", r"\bsignal_outcomes\b", r"\bmodel_versions\b", r"\bholding_lots\b",
    r"\btax_settings\b",
)
_ADMISSIBLE: Final[frozenset[str]] = frozenset({"rs_corporate_actions"})


class FeedError(RuntimeError):
    """The feed could not be read honestly. Reported, never guessed."""


def assert_feed_sql_admissible(sql: str) -> None:
    lowered = sql.lower()
    for token in _FORBIDDEN:
        if re.search(token, lowered):
            raise FeedError(f"forbidden token {token!r} in tax feed SQL")
    words = lowered.split()
    tables = {w.strip(",;") for prev, w in pairwise(words) if prev in {"from", "join"}}
    if not tables <= _ADMISSIBLE:
        raise FeedError(f"tax feed SQL touches non-admissible table(s): {sorted(tables)}")


@dataclass(frozen=True)
class DividendRecord:
    """One `rs_corporate_actions` dividend row as stored: `franking_pct` is 0..100 or None."""

    symbol: str
    ex_date: date
    pay_date: date | None
    dividend_amount: Decimal | None
    franking_pct: Decimal | None

    @property
    def known_at(self) -> datetime:
        return datetime.combine(self.ex_date, KNOWN_AT_UTC_TIME, tzinfo=UTC)


@dataclass(frozen=True)
class DividendCharacterisation:
    symbol: str
    as_of: date
    knowledge_cutoff: datetime
    readiness: Literal["pass", "unknown"]
    records: tuple[DividendRecord, ...]
    undeclared: tuple[str, ...]
    cash_ttm: Decimal
    franking_credit_ttm: Decimal
    corporate_tax_rate: Decimal
    data_mode: Literal["real"] = "real"

    @property
    def grossed_up_ttm(self) -> Decimal:
        return self.cash_ttm + self.franking_credit_ttm

    @property
    def known_at(self) -> datetime:
        """The latest row's ex-date end of day, or the cutoff when nothing was found."""
        return max((r.known_at for r in self.records), default=self.knowledge_cutoff)

    @property
    def observed_at(self) -> date:
        """The event date this characterisation is anchored on: the latest
        dividend's ex-date in the window, or `as_of` when the window is empty.
        Always `<= known_at.date()` by construction (the pair the calendar
        entry above produces), which is what `EvidenceItem` requires."""
        return max((r.ex_date for r in self.records), default=self.as_of)


def _q(value: Decimal) -> Decimal:
    return value.quantize(_Q6)


def _dec(value: object) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, float):
        raise FeedError("float reached the tax feed — every figure must be Decimal")
    return Decimal(str(value))


def characterise_dividends(
    records: tuple[DividendRecord, ...] | list[DividendRecord],
    *,
    symbol: str,
    cutoff: datetime,
    window_days: int = WINDOW_DAYS,
    corporate_tax_rate: Decimal = DEFAULT_CORPORATE_TAX_RATE,
) -> DividendCharacterisation:
    """The security-level characterisation for the trailing window at `cutoff`.

    `pass` iff at least one row is knowable at the cutoff inside the window and
    every such row declares both `dividend_amount` and `franking_pct`; otherwise
    `unknown`, naming each undeclared row and an empty window.
    """
    if cutoff.tzinfo is None or cutoff.utcoffset() != timedelta(0):
        raise FeedError("cutoff must be an explicit UTC instant")
    as_of = cutoff.date()
    window_start = as_of - timedelta(days=window_days)
    in_window = tuple(
        sorted(
            (
                r for r in records
                if r.symbol == symbol and r.known_at <= cutoff and window_start < r.ex_date <= as_of
            ),
            key=lambda r: r.ex_date,
        )
    )
    undeclared: list[str] = []
    cash = Decimal("0")
    credit = Decimal("0")
    for r in in_window:
        if r.dividend_amount is None or r.franking_pct is None:
            missing = "dividend_amount" if r.dividend_amount is None else "franking_pct"
            undeclared.append(f"{symbol} ex {r.ex_date.isoformat()}: {missing} undeclared (NULL, not 0)")
            continue
        div = Dividend(
            symbol=symbol,
            pay_date=r.pay_date or r.ex_date,
            cash_dividend=r.dividend_amount,
            franking_pct=r.franking_pct / Decimal("100"),
            corporate_tax_rate=corporate_tax_rate,
        )
        cash += div.cash_dividend
        credit += franking_credit(div)
    if not in_window:
        undeclared.append(
            f"{symbol}: no dividend row with ex-date in ({window_start.isoformat()}, {as_of.isoformat()}] "
            f"knowable at {cutoff.isoformat()}"
        )
    return DividendCharacterisation(
        symbol=symbol,
        as_of=as_of,
        knowledge_cutoff=cutoff,
        readiness="unknown" if undeclared else "pass",
        records=in_window,
        undeclared=tuple(undeclared),
        cash_ttm=_q(cash),
        franking_credit_ttm=_q(credit),
        corporate_tax_rate=corporate_tax_rate,
    )


def tax_reference_for(
    characterisation: DividendCharacterisation,
    *,
    tax_assessment_id: str,
    as_of: date,
    knowledge_cutoff: datetime,
    created_at: datetime,
) -> TaxAssessmentReference:
    """The reference a characterisation earns: `pass`/`applicable` for a declared
    ASX window, otherwise the same unresolved shape the builder always carried."""
    if characterisation.as_of != as_of or characterisation.knowledge_cutoff != knowledge_cutoff:
        raise FeedError("the dividend characterisation was built for a different cutoff")
    if characterisation.data_mode != "real":
        raise FeedError("a readiness pass requires real data — the claim would be unearned")
    is_asx = characterisation.symbol.endswith(".AU")
    passed = characterisation.readiness == "pass" and is_asx
    return TaxAssessmentReference(
        tax_assessment_id=tax_assessment_id,
        as_of=as_of,
        knowledge_cutoff=knowledge_cutoff,
        created_at=created_at,
        applicability="applicable" if passed else "uncertain",
        readiness="pass" if passed else "unknown",
    )


def claim_for(c: DividendCharacterisation) -> str:
    """The `tax_fact` evidence claim: every figure and every gap, in one sentence."""
    head = (
        f"rs_corporate_actions dividends for {c.symbol}, ex-dates in the {WINDOW_DAYS}-day window "
        f"to {c.as_of.isoformat()} knowable at {c.knowledge_cutoff.isoformat()}: {len(c.records)} row(s); "
        f"cash_ttm={c.cash_ttm} per share, franking_credit_ttm={c.franking_credit_ttm} "
        f"(validation formula, corporate_tax_rate={c.corporate_tax_rate}; universe.corporate_tax_rate unread), "
        f"grossed_up_ttm={c.grossed_up_ttm}; readiness={c.readiness}"
    )
    if c.undeclared:
        head += "; undeclared: " + " | ".join(c.undeclared)
    return (
        head + ". Security-level characterisation only (A-31 decision 1, resolved_by=arbi 2026-09-16); "
        "no position, quantity or after-tax figure is asserted."
    )


# --- the one read ----------------------------------------------------------------


class FeedConn(Protocol):
    async def fetch(self, query: str, *args: object) -> list[Any]: ...


SQL_DIVIDENDS_WINDOW: Final[str] = (
    "SELECT symbol, ex_date, pay_date, dividend_amount, franking_pct "
    "FROM rs_corporate_actions "
    "WHERE symbol = $1 AND action_type = 'dividend' AND ex_date > $2 AND ex_date <= $3 "
    "ORDER BY ex_date"
)
assert_feed_sql_admissible(SQL_DIVIDENDS_WINDOW)


def _as_date(value: object) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


async def load_dividend_characterisation(
    conn: FeedConn, symbol: str, cutoff: datetime, *, window_days: int = WINDOW_DAYS
) -> DividendCharacterisation:
    as_of = cutoff.date()
    rows = await conn.fetch(SQL_DIVIDENDS_WINDOW, symbol, as_of - timedelta(days=window_days), as_of)
    records = [
        DividendRecord(
            symbol=str(r["symbol"]),
            ex_date=_as_date(r["ex_date"]),
            pay_date=_as_date(r["pay_date"]) if r.get("pay_date") is not None else None,
            dividend_amount=_dec(r.get("dividend_amount")),
            franking_pct=_dec(r.get("franking_pct")),
        )
        for r in rows
    ]
    return characterise_dividends(records, symbol=symbol, cutoff=cutoff, window_days=window_days)
