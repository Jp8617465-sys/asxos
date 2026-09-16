"""asxos/domain/tax/feed.py — the G12 security-level dividend characterisation (spec v1.7 §3, §10)."""
from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal as D
from typing import Any

import pytest

from asxos.domain.decision_engine.types import verify_content_hash
from asxos.domain.tax import feed

CUTOFF = datetime(2026, 9, 16, 20, 40, tzinfo=UTC)
AS_OF = CUTOFF.date()


def _rec(ex: date, amount: D | None = D("2.70"), franking: D | None = D("100"), pay: date | None = None, symbol: str = "CBA.AU") -> feed.DividendRecord:
    return feed.DividendRecord(symbol=symbol, ex_date=ex, pay_date=pay, dividend_amount=amount, franking_pct=franking)


def test_cba_window_fully_declared_passes_with_the_spec_gross_up() -> None:
    """TC-26 (spec §11): two fully franked dividends in the window, default 30% rate;
    credit = cash × 1.0 × 0.30 / 0.70 (spec §3)."""
    recs = [_rec(date(2026, 2, 18), D("2.25")), _rec(date(2026, 8, 19), D("2.70"), pay=date(2026, 9, 29))]
    c = feed.characterise_dividends(recs, symbol="CBA.AU", cutoff=CUTOFF)
    assert c.readiness == "pass" and c.undeclared == () and len(c.records) == 2
    assert c.cash_ttm == D("4.950000")
    assert c.franking_credit_ttm == (D("4.95") * D("0.30") / D("0.70")).quantize(D("0.000001"))
    assert c.grossed_up_ttm == c.cash_ttm + c.franking_credit_ttm
    assert c.known_at == datetime(2026, 8, 19, 23, 59, 59, tzinfo=UTC)
    ref = feed.tax_reference_for(c, tax_assessment_id="taxref-cba-1-2026-09-16", as_of=AS_OF, knowledge_cutoff=CUTOFF, created_at=CUTOFF)
    assert (ref.readiness, ref.applicability) == ("pass", "applicable") and verify_content_hash(ref)


def test_base_rate_entity_rate_reproduces_the_spec_worked_example() -> None:
    """TC-26(c) (spec §11): spec §3's own $1,000/25% worked example — credit $333.33, grossed-up
    $1,333.33 — reproduced through the feed's `corporate_tax_rate` parameter. Not yet wired end
    to end from `universe.corporate_tax_rate` (A-31 decision 3: stays unread)."""
    c = feed.characterise_dividends(
        [_rec(date(2026, 8, 19), D("1000"))], symbol="CBA.AU", cutoff=CUTOFF, corporate_tax_rate=D("0.25")
    )
    assert c.readiness == "pass" and c.corporate_tax_rate == D("0.25")
    assert c.franking_credit_ttm == D("333.333333")
    assert c.grossed_up_ttm == D("1333.333333")


def test_explicitly_declared_zero_franking_is_unfranked_and_computes() -> None:
    c = feed.characterise_dividends([_rec(date(2026, 8, 19), D("1.00"), D("0"))], symbol="CBA.AU", cutoff=CUTOFF)
    assert c.readiness == "pass" and c.franking_credit_ttm == D("0") and c.cash_ttm == D("1.000000")


def test_undeclared_franking_blocks_the_pass_and_names_the_row() -> None:
    """TC-26(b) (spec §11); spec v1.7 §10: NULL is undeclared, never 0 (migration 0027:57)."""
    recs = [_rec(date(2026, 2, 18)), _rec(date(2026, 8, 19), franking=None)]
    c = feed.characterise_dividends(recs, symbol="CBA.AU", cutoff=CUTOFF)
    assert c.readiness == "unknown"
    assert c.undeclared == ("CBA.AU ex 2026-08-19: franking_pct undeclared (NULL, not 0)",)
    assert c.cash_ttm == D("2.700000")  # the declared row still counts; the undeclared one is named, not zeroed
    ref = feed.tax_reference_for(c, tax_assessment_id="t", as_of=AS_OF, knowledge_cutoff=CUTOFF, created_at=CUTOFF)
    assert (ref.readiness, ref.applicability) == ("unknown", "uncertain")


def test_undeclared_amount_also_blocks() -> None:
    c = feed.characterise_dividends([_rec(date(2026, 8, 19), amount=None)], symbol="CBA.AU", cutoff=CUTOFF)
    assert c.readiness == "unknown" and "dividend_amount undeclared" in c.undeclared[0]


def test_empty_window_is_unknown_not_fail() -> None:
    c = feed.characterise_dividends([_rec(date(2025, 9, 16))], symbol="CBA.AU", cutoff=CUTOFF)  # exactly 365 days: outside
    assert c.readiness == "unknown" and c.records == () and "no dividend row" in c.undeclared[0]
    assert c.known_at == CUTOFF


def test_ex_date_on_the_cutoff_day_is_not_knowable_at_a_morning_cutoff() -> None:
    morning = datetime(2026, 9, 16, 6, 40, tzinfo=UTC)
    same_day = _rec(date(2026, 9, 16))
    c = feed.characterise_dividends([same_day, _rec(date(2026, 2, 18))], symbol="CBA.AU", cutoff=morning)
    assert [r.ex_date for r in c.records] == [date(2026, 2, 18)]
    later = feed.characterise_dividends([same_day], symbol="CBA.AU", cutoff=datetime(2026, 9, 16, 23, 59, 59, tzinfo=UTC))
    assert [r.ex_date for r in later.records] == [date(2026, 9, 16)]


def test_other_symbols_are_ignored_and_a_non_asx_name_never_passes() -> None:
    recs = [_rec(date(2026, 8, 19), symbol="NAB.AU"), _rec(date(2026, 8, 19), symbol="HUBS.NYSE")]
    c = feed.characterise_dividends(recs, symbol="HUBS.NYSE", cutoff=CUTOFF)
    assert c.readiness == "pass" and len(c.records) == 1
    ref = feed.tax_reference_for(c, tax_assessment_id="t", as_of=AS_OF, knowledge_cutoff=CUTOFF, created_at=CUTOFF)
    assert (ref.readiness, ref.applicability) == ("unknown", "uncertain")


def test_reference_refuses_a_characterisation_for_another_cutoff() -> None:
    c = feed.characterise_dividends([_rec(date(2026, 8, 19))], symbol="CBA.AU", cutoff=CUTOFF)
    with pytest.raises(feed.FeedError, match="different cutoff"):
        feed.tax_reference_for(c, tax_assessment_id="t", as_of=AS_OF, knowledge_cutoff=datetime(2026, 9, 15, 20, tzinfo=UTC), created_at=CUTOFF)


def test_cutoff_must_be_utc_and_floats_are_refused() -> None:
    with pytest.raises(feed.FeedError, match="UTC"):
        feed.characterise_dividends([], symbol="CBA.AU", cutoff=datetime(2026, 9, 16, 20))
    with pytest.raises(feed.FeedError, match="float"):
        feed._dec(1.5)


def test_claim_carries_every_figure_and_the_ruling() -> None:
    c = feed.characterise_dividends([_rec(date(2026, 8, 19), franking=None)], symbol="CBA.AU", cutoff=CUTOFF)
    text = feed.claim_for(c)
    for fragment in ("cash_ttm=", "franking_credit_ttm=", "corporate_tax_rate=0.30", "readiness=unknown", "undeclared:", "A-31 decision 1", "resolved_by=arbi"):
        assert fragment in text


def test_sql_is_fenced_to_the_research_store_and_rule_11_tokens() -> None:
    feed.assert_feed_sql_admissible(feed.SQL_DIVIDENDS_WINDOW)
    with pytest.raises(feed.FeedError, match="non-admissible"):
        feed.assert_feed_sql_admissible("SELECT 1 FROM holding_lots_x JOIN prices")
    with pytest.raises(feed.FeedError, match="forbidden"):
        feed.assert_feed_sql_admissible("SELECT prob_up FROM rs_corporate_actions")
    with pytest.raises(feed.FeedError, match="forbidden"):
        feed.assert_feed_sql_admissible("SELECT 1 FROM tax_settings")


async def test_loader_reads_the_window_and_converts_rows() -> None:
    class Conn:
        def __init__(self) -> None:
            self.args: tuple[object, ...] = ()

        async def fetch(self, query: str, *args: object) -> list[Any]:
            assert query == feed.SQL_DIVIDENDS_WINDOW
            self.args = args
            return [
                {"symbol": "CBA.AU", "ex_date": date(2026, 8, 19), "pay_date": date(2026, 9, 29), "dividend_amount": D("2.70"), "franking_pct": D("100")},
                {"symbol": "CBA.AU", "ex_date": "2026-02-18", "pay_date": None, "dividend_amount": D("2.25"), "franking_pct": None},
            ]

    conn = Conn()
    c = await feed.load_dividend_characterisation(conn, "CBA.AU", CUTOFF)
    assert conn.args == ("CBA.AU", date(2025, 9, 16), AS_OF)
    assert c.readiness == "unknown" and [r.ex_date for r in c.records] == [date(2026, 2, 18), date(2026, 8, 19)]
    assert c.records[0].pay_date is None and c.records[1].pay_date == date(2026, 9, 29)
