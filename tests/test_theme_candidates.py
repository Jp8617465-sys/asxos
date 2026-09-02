"""Stage 3 theme + candidate engine — campaign node H4-A.

Exit-gate tests (target-architecture.md §15, Stage 3): one theme and one
candidate reproducible from exact, cited evidence WITHOUT converting either
into a recommendation. Reproducibility is asserted by hash; the "not a
recommendation" property is asserted three ways — by validator, by the LLM
boundary's verb screen, and by grep over the package and the migration.
"""
from __future__ import annotations

import re
from datetime import UTC, date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from asxos.domain.decision_engine.types import EvidenceItem, verify_content_hash
from asxos.domain.themes.candidates import CandidateSnapshot, ThemeVersion
from asxos.domain.themes.candidates.builder import (
    MIN_MEDIAN_DOLLAR_VOLUME_AUD,
    build_candidate_snapshot,
    build_theme_version,
    cutoff_instant,
)
from asxos.domain.themes.candidates.extraction_boundary import (
    BoundaryError,
    evidence_from_proposal,
    proposal_cites_only_admissible_tiers,
)
from asxos.domain.themes.candidates.measures import (
    SQL_FACTORS,
    SQL_MACRO,
    SQL_MEMBERS,
    SQL_PRICES,
    SQL_SECTOR,
    SQL_THEME,
    MeasureError,
    assert_measure_sql_admissible,
    breadth_flags,
)
from asxos.domain.themes.candidates.repository import (
    load_candidate_snapshot,
    load_theme_version,
    save_candidate_snapshot,
    save_theme_version,
)
from asxos.domain.themes.candidates.types import EXPIRY_RULE, default_expiry

AS_OF = date(2026, 9, 1)
CUTOFF = cutoff_instant(AS_OF)
PKG = Path(__file__).resolve().parents[1] / "asxos" / "domain" / "themes" / "candidates"
MIGRATION = Path(__file__).resolve().parents[1] / "migrations" / "0051_theme_candidates.sql"


# --- fixture database ---------------------------------------------------------------


def _sessions(n: int, end: date = AS_OF) -> list[date]:
    out: list[date] = []
    d = end
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d -= timedelta(days=1)
    return sorted(out)


def _prices(symbol: str, n: int, *, start: str, step: str, volume: str, end: date = AS_OF) -> list[dict[str, Any]]:
    px = Decimal(start)
    rows: list[dict[str, Any]] = []
    for d in _sessions(n, end):
        rows.append({"symbol": symbol, "dt": d, "close": px, "volume": Decimal(volume)})
        px += Decimal(step)
    return rows


class FakeConn:
    """Dispatches on the exact SQL constants the measures module binds."""

    def __init__(self, *, theme: dict[str, Any] | None, members: list[dict[str, Any]], macro: dict[str, Any] | None,
                 factors: dict[str, dict[str, Any]], sectors: dict[str, str], prices: dict[str, list[dict[str, Any]]]):
        self.theme, self.members, self.macro = theme, members, macro
        self.factors, self.sectors, self.prices = factors, sectors, prices
        self.calls: list[tuple[str, tuple[object, ...]]] = []
        self.executed: list[tuple[str, tuple[object, ...]]] = []

    async def fetchrow(self, sql: str, *args: object) -> Any:
        self.calls.append((sql, args))
        if sql == SQL_THEME:
            return self.theme if self.theme and self.theme["theme_code"] == args[0] else None
        if sql == SQL_MACRO:
            return self.macro if self.macro and self.macro["macro_thesis_id"] == args[0] else None
        if sql == SQL_FACTORS:
            row = self.factors.get(str(args[0]))
            return row if row and row["as_of"] <= args[1] else None  # type: ignore[operator]
        if sql == SQL_SECTOR:
            sec = self.sectors.get(str(args[0]))
            return {"symbol": args[0], "gics_sector": sec} if sec else None
        if sql.startswith("SELECT payload FROM"):
            for _stored_sql, stored_args in self.executed:
                if stored_args and stored_args[0] == args[0]:
                    return {"payload": stored_args[-1]}
            return None
        raise AssertionError(f"unexpected fetchrow SQL: {sql}")

    async def fetch(self, sql: str, *args: object) -> list[Any]:
        self.calls.append((sql, args))
        if sql == SQL_MEMBERS:
            return [m for m in self.members if m["theme_id"] == args[0]]
        if sql == SQL_PRICES:
            rows = [r for r in self.prices.get(str(args[0]), []) if r["dt"] <= args[1]]  # type: ignore[operator]
            return sorted(rows, key=lambda r: r["dt"], reverse=True)[: int(args[2])]  # type: ignore[arg-type]
        raise AssertionError(f"unexpected fetch SQL: {sql}")

    async def execute(self, sql: str, *args: object) -> str:
        self.executed.append((sql, args))
        return "INSERT 0 1"


def _conn(**overrides: Any) -> FakeConn:
    theme = {
        "theme_id": 1, "theme_code": "big-4-banks", "name": "Big 4 banks", "description": "Australian major banks.",
        "conviction_band": "medium", "stage": "emerging", "macro_thesis_id": 6,
        "governance_status": "approved", "retired_at": None,
    }
    members = [
        {"theme_id": 1, "symbol": "CBA.AU", "exposure_strength": Decimal("0.5"), "direction": "positive",
         "mechanism_text": "Largest retail bank; NIM sensitivity to the cash rate."},
        {"theme_id": 1, "symbol": "NAB.AU", "exposure_strength": Decimal("0.4"), "direction": "positive",
         "mechanism_text": "Business-lending skew."},
        {"theme_id": 1, "symbol": "ZIP.AU", "exposure_strength": Decimal("0.2"), "direction": "negative",
         "mechanism_text": "BNPL competitor losing share to bank offerings."},
    ]
    macro = {"macro_thesis_id": 6, "title": "Rates plateau", "regime_quadrant": "slowing_disinflation",
             "governance_status": "approved"}
    factors = {
        "CBA.AU": {"symbol": "CBA.AU", "as_of": date(2026, 8, 11), "sector": "Financials",
                   "market_cap_aud": Decimal("280000000000"), "value_score": Decimal("-1.2"),
                   "quality_score": Decimal("1.4"), "momentum_score": Decimal("0.7"), "low_vol_score": Decimal("0.9"),
                   "yield_score": Decimal("0.3"), "composite_score": Decimal("0.42"), "n_factors_present": 5},
        "NAB.AU": {"symbol": "NAB.AU", "as_of": date(2026, 8, 11), "sector": "Financials",
                   "market_cap_aud": Decimal("120000000000"), "value_score": Decimal("0.1"),
                   "quality_score": Decimal("0.8"), "momentum_score": Decimal("0.2"), "low_vol_score": Decimal("0.6"),
                   "yield_score": Decimal("0.5"), "composite_score": Decimal("0.44"), "n_factors_present": 5},
    }
    sectors = {"CBA.AU": "Financials", "NAB.AU": "Financials"}
    prices = {
        "CBA.AU": _prices("CBA.AU", 210, start="150", step="0.5", volume="1500000"),
        "NAB.AU": _prices("NAB.AU", 210, start="40", step="-0.02", volume="3000000"),
        "ZIP.AU": _prices("ZIP.AU", 30, start="2", step="0.01", volume="40000"),
    }
    kw: dict[str, Any] = {"theme": theme, "members": members, "macro": macro, "factors": factors,
                          "sectors": sectors, "prices": prices}
    kw.update(overrides)
    return FakeConn(**kw)


async def _build_pair(conn: FakeConn, symbol: str = "CBA.AU") -> tuple[ThemeVersion, CandidateSnapshot]:
    tv = await build_theme_version(conn, theme_code="big-4-banks", as_of=AS_OF)
    cand = await build_candidate_snapshot(conn, symbol=symbol, theme=tv, as_of=AS_OF)
    return tv, cand


# --- exit gate: reproducible from exact evidence --------------------------------------


@pytest.mark.asyncio
async def test_theme_and_candidate_hash_identically_on_two_builds() -> None:
    tv1, c1 = await _build_pair(_conn())
    tv2, c2 = await _build_pair(_conn())
    assert tv1.content_hash == tv2.content_hash and len(tv1.content_hash) == 64
    assert c1.content_hash == c2.content_hash and len(c1.content_hash) == 64
    assert verify_content_hash(tv1) and verify_content_hash(c1)


@pytest.mark.asyncio
async def test_every_measure_is_backed_by_a_cited_evidence_row() -> None:
    tv, cand = await _build_pair(_conn())
    theme_ids = {e.evidence_id for e in tv.evidence}
    assert theme_ids == {"theme:row", "theme:member:CBA.AU", "theme:member:NAB.AU", "theme:member:ZIP.AU", "theme:macro:6"}
    assert all(e.source_uri.startswith("db://") for e in tv.evidence)
    assert all(e.evidence_tier == "verified" for e in tv.evidence)
    cand_ids = {e.evidence_id for e in cand.evidence}
    assert cand_ids == {"theme:row", "theme:member:CBA.AU", "candidate:factors:CBA.AU", "candidate:price:CBA.AU"}
    # the price evidence quotes the same figures the measures carry
    price = next(e for e in cand.evidence if e.evidence_id == "candidate:price:CBA.AU")
    assert f"close={cand.measures['last_close']}" in price.claim
    assert f"median_dollar_volume_60d={cand.measures['median_dollar_volume_60d']}" in price.claim
    assert cand.measures["last_close"] == "254.500000"
    assert cand.measures["gics_sector"] == "Financials"
    assert cand.measures["factor_composite_score"] == "0.420000"
    assert tv.regime_quadrant == "slowing_disinflation" and tv.macro_thesis_id == 6


@pytest.mark.asyncio
async def test_a_different_input_changes_the_hash() -> None:
    _, base = await _build_pair(_conn())
    conn = _conn()
    conn.prices["CBA.AU"][-1]["close"] = Decimal("255")
    _, changed = await _build_pair(conn)
    assert changed.content_hash != base.content_hash


@pytest.mark.asyncio
async def test_measures_are_decimal_strings_never_floats() -> None:
    tv, cand = await _build_pair(_conn())
    for m in (tv.measures, cand.measures):
        assert not any(isinstance(v, float) for v in m.values())
    assert tv.measures["pct_above_50d_ma"] == "0.500000"  # CBA rising, NAB falling; ZIP too short
    assert tv.measures["members_with_200d_history"] == 2
    assert tv.measures["pct_above_200d_ma"] == "0.500000"


def test_breadth_flags_need_enough_history() -> None:
    assert breadth_flags([]) == (None, None)
    rising = [Decimal(i) for i in range(1, 61)]
    assert breadth_flags(rising) == (True, None)
    flat = [Decimal(5)] * 200
    assert breadth_flags(flat) == (False, False)


# --- exit gate: not a recommendation -------------------------------------------------


@pytest.mark.parametrize(
    "key", ["recommendation", "verdict", "action", "buy", "target_price", "weight", "position_size", "allocation",
            "signal_label", "prob_up", "overweight"],
)
@pytest.mark.asyncio
async def test_recommendation_shaped_measure_keys_are_refused(key: str) -> None:
    tv, cand = await _build_pair(_conn())
    with pytest.raises(ValueError, match="recommendation-shaped"):
        cand.model_copy(update={"measures": {**cand.measures, key: "1"}, "content_hash": ""}).model_validate(
            {**cand.model_dump(), "measures": {**cand.measures, key: "1"}, "content_hash": ""}
        )
    with pytest.raises(ValueError, match="recommendation-shaped"):
        ThemeVersion.model_validate({**tv.model_dump(), "measures": {**tv.measures, key: "1"}, "content_hash": ""})


@pytest.mark.asyncio
async def test_quality_check_keys_are_screened_too() -> None:
    _, cand = await _build_pair(_conn())
    with pytest.raises(ValueError, match="recommendation-shaped"):
        CandidateSnapshot.model_validate(
            {**cand.model_dump(), "quality_checks": {**cand.quality_checks, "buy_signal": "pass"}, "content_hash": ""}
        )


@pytest.mark.asyncio
async def test_no_recommendation_field_exists_on_either_contract() -> None:
    banned = re.compile(r"recommend|verdict|action|weight|size|target|allocation|state$", re.IGNORECASE)
    for model in (ThemeVersion, CandidateSnapshot):
        offenders = [f for f in model.model_fields if banned.search(f) and f != "not_a_recommendation"]
        assert offenders == [], offenders
    assert CandidateSnapshot.model_fields["not_a_recommendation"].default is True
    _, cand = await _build_pair(_conn())
    with pytest.raises(ValueError):
        CandidateSnapshot.model_validate({**cand.model_dump(), "not_a_recommendation": False, "content_hash": ""})


@pytest.mark.asyncio
async def test_float_measures_are_refused() -> None:
    _, cand = await _build_pair(_conn())
    with pytest.raises(ValueError, match="float"):
        CandidateSnapshot.model_validate(
            {**cand.model_dump(), "measures": {**cand.measures, "median_dollar_volume_60d": 1.5}, "content_hash": ""}
        )


def test_package_and_migration_never_touch_signals_or_carry_a_verdict() -> None:
    src = "\n".join(p.read_text() for p in PKG.glob("*.py"))
    assert re.search(r"from\s+signals|join\s+signals", src, re.IGNORECASE) is None
    assert re.search(r"models\.model_a|import\s+model_a|from\s+asxos\.domain\.models", src) is None
    assert not re.search(r"import\s+numpy|import\s+lightgbm|import\s+joblib", src)
    ddl = "\n".join(line for line in MIGRATION.read_text().splitlines() if not line.lstrip().startswith("--"))
    ddl = re.sub(r"COMMENT ON TABLE.*?';", "", ddl, flags=re.DOTALL)  # prose, not schema
    for banned in ("verdict", "weight", "target_price", "recommendation", "signal"):
        assert banned not in ddl.lower(), banned
    assert ddl.count("BEFORE UPDATE OR DELETE") == 2
    assert "CREATE TABLE theme_versions" in ddl and "CREATE TABLE candidate_snapshots" in ddl
    assert "REFERENCES theme_versions(theme_version_id)" in ddl


# --- the LLM boundary ---------------------------------------------------------------


def _proposal(**overrides: Any) -> dict[str, Any]:
    p: dict[str, Any] = {
        "evidence": [
            {"claim": "macro_theses #6 is approved with regime slowing_disinflation", "tier": "verified",
             "source_type": "db_query", "source_table": "macro_theses", "source_as_of": "2026-09-01",
             "snapshot_data": {"macro_thesis_id": 6, "governance_status": "approved"}},
            {"claim": "CBA.AU composite factor score 0.42 on 2026-08-11", "tier": "verified",
             "source_type": "db_query", "source_table": "rs_factor_scores"},
            {"claim": "Bank NIMs typically widen when the cash rate plateaus", "tier": "speculative",
             "source_type": "domain_knowledge"},
        ],
        "theme_holding_proposals": [{"symbol": "CBA.AU", "evidence_citation_ids": ["ev:0", "ev:1"]}],
    }
    p.update(overrides)
    return p


def test_boundary_caps_llm_verified_to_db_query_with_snapshot() -> None:
    items = evidence_from_proposal(_proposal(), known_at=CUTOFF, as_of=AS_OF, id_prefix="ev")
    assert [i.evidence_tier for i in items] == ["verified", "inferred", "speculative"]
    assert [i.evidence_type for i in items] == ["theme_fact", "fundamental_fact", "source_document"]
    assert items[0].source_uri == "agent://db_query/macro_theses"
    assert all(isinstance(i, EvidenceItem) for i in items)
    proposal_cites_only_admissible_tiers(_proposal(), items)


def test_boundary_keeps_speculative_labelled_rather_than_deleting_it() -> None:
    items = evidence_from_proposal(_proposal(), known_at=CUTOFF, as_of=AS_OF, id_prefix="ev")
    assert items[2].evidence_tier == "speculative" and "NIM" in items[2].claim


@pytest.mark.parametrize(
    "text",
    ["Buy CBA.AU ahead of results", "We would overweight the majors", "Price target $300 on CBA",
     "Top pick in financials", "Strong buy", "Accumulate on weakness"],
)
def test_boundary_refuses_recommendation_verbs(text: str) -> None:
    p = _proposal(evidence=[{"claim": text, "tier": "inferred"}])
    with pytest.raises(BoundaryError, match="recommendation"):
        evidence_from_proposal(p, known_at=CUTOFF, as_of=AS_OF)


def test_boundary_refuses_citations_of_speculative_or_unknown_evidence() -> None:
    items = evidence_from_proposal(_proposal(), known_at=CUTOFF, as_of=AS_OF, id_prefix="ev")
    with pytest.raises(BoundaryError, match="speculative"):
        proposal_cites_only_admissible_tiers(
            _proposal(theme_holding_proposals=[{"symbol": "X", "evidence_citation_ids": ["ev:2"]}]), items
        )
    with pytest.raises(BoundaryError, match="unknown"):
        proposal_cites_only_admissible_tiers(
            _proposal(theme_proposals=[{"theme_code": "x", "evidence_citation_ids": ["ev:9"]}]), items
        )


def test_boundary_refuses_empty_future_or_malformed_claims() -> None:
    with pytest.raises(BoundaryError, match="no evidence"):
        evidence_from_proposal({"evidence": []}, known_at=CUTOFF, as_of=AS_OF)
    with pytest.raises(BoundaryError, match="empty claim"):
        evidence_from_proposal({"evidence": [{"claim": "  "}]}, known_at=CUTOFF, as_of=AS_OF)
    with pytest.raises(BoundaryError, match="after as_of"):
        evidence_from_proposal(
            {"evidence": [{"claim": "x", "source_as_of": "2026-09-02"}]}, known_at=CUTOFF, as_of=AS_OF
        )
    with pytest.raises(BoundaryError, match="unknown evidence tier"):
        evidence_from_proposal({"evidence": [{"claim": "x", "tier": "certain"}]}, known_at=CUTOFF, as_of=AS_OF)


@pytest.mark.asyncio
async def test_agent_evidence_rides_along_as_extra_evidence_under_the_cutoff() -> None:
    items = evidence_from_proposal(_proposal(), known_at=CUTOFF, as_of=AS_OF, id_prefix="ev")
    tv = await build_theme_version(_conn(), theme_code="big-4-banks", as_of=AS_OF, extra_evidence=items)
    assert {i.evidence_id for i in items} <= {e.evidence_id for e in tv.evidence}
    late = evidence_from_proposal(_proposal(), known_at=CUTOFF + timedelta(seconds=1), as_of=AS_OF, id_prefix="late")
    with pytest.raises(ValueError, match="after cutoff"):
        await build_theme_version(_conn(), theme_code="big-4-banks", as_of=AS_OF, extra_evidence=late)


# --- quality checks and expiry --------------------------------------------------------


@pytest.mark.asyncio
async def test_liquid_fresh_candidate_passes_every_check() -> None:
    _, cand = await _build_pair(_conn())
    assert cand.quality_checks == {
        "has_sector": "pass", "has_factor_scores": "pass", "factor_scores_fresh": "pass",
        "price_fresh": "pass", "liquid_enough": "pass",
    }
    assert cand.quality_passed is True
    assert cand.exposure_direction == "positive"
    assert Decimal(str(cand.measures["median_dollar_volume_60d"])) >= MIN_MEDIAN_DOLLAR_VOLUME_AUD


@pytest.mark.asyncio
async def test_illiquid_unscored_member_fails_checks_but_is_still_recorded() -> None:
    _, cand = await _build_pair(_conn(), symbol="ZIP.AU")
    assert cand.quality_checks["liquid_enough"] == "fail"
    assert cand.quality_checks["has_factor_scores"] == "fail"
    assert cand.quality_checks["has_sector"] == "fail"
    assert cand.quality_checks["factor_scores_fresh"] == "unknown"
    assert cand.quality_passed is False
    assert cand.exposure_direction == "negative"
    assert cand.measures["factor_composite_score"] is None


@pytest.mark.asyncio
async def test_stale_price_and_stale_factors_fail() -> None:
    conn = _conn()
    conn.prices["CBA.AU"] = _prices("CBA.AU", 210, start="150", step="0.5", volume="1500000", end=AS_OF - timedelta(days=10))
    conn.factors["CBA.AU"]["as_of"] = AS_OF - timedelta(days=61)
    _, cand = await _build_pair(conn)
    assert cand.quality_checks["price_fresh"] == "fail"
    assert cand.quality_checks["factor_scores_fresh"] == "fail"
    assert cand.quality_passed is False


@pytest.mark.asyncio
async def test_factor_scores_after_the_cutoff_are_not_knowable() -> None:
    conn = _conn()
    conn.factors["CBA.AU"]["as_of"] = AS_OF + timedelta(days=1)
    _, cand = await _build_pair(conn)
    assert cand.measures["factor_as_of"] is None
    assert cand.quality_checks["has_factor_scores"] == "fail"


@pytest.mark.asyncio
async def test_expiry_is_thirty_days_from_cutoff_and_rule_is_recorded() -> None:
    tv, cand = await _build_pair(_conn())
    assert tv.expires_at == default_expiry(CUTOFF, days=30) == CUTOFF + timedelta(days=30)
    assert cand.expires_at == CUTOFF + timedelta(days=30)
    assert tv.expiry_rule == cand.expiry_rule == EXPIRY_RULE
    assert tv.knowledge_cutoff.tzinfo is UTC and tv.as_of == CUTOFF.date()


# --- builder refusals ---------------------------------------------------------------


@pytest.mark.asyncio
async def test_builder_refuses_unknown_unapproved_retired_or_empty_themes() -> None:
    with pytest.raises(MeasureError, match="does not exist"):
        await build_theme_version(_conn(), theme_code="nope", as_of=AS_OF)
    conn = _conn()
    conn.theme["governance_status"] = "pending_review"  # type: ignore[index]
    with pytest.raises(MeasureError, match="not approved"):
        await build_theme_version(conn, theme_code="big-4-banks", as_of=AS_OF)
    conn = _conn()
    conn.theme["retired_at"] = AS_OF - timedelta(days=1)  # type: ignore[index]
    with pytest.raises(MeasureError, match="retired"):
        await build_theme_version(conn, theme_code="big-4-banks", as_of=AS_OF)
    with pytest.raises(MeasureError, match="no members"):
        await build_theme_version(_conn(members=[]), theme_code="big-4-banks", as_of=AS_OF)


@pytest.mark.asyncio
async def test_candidate_must_be_a_member_at_the_same_as_of() -> None:
    tv = await build_theme_version(_conn(), theme_code="big-4-banks", as_of=AS_OF)
    with pytest.raises(MeasureError, match="not a member"):
        await build_candidate_snapshot(_conn(), symbol="BHP.AU", theme=tv, as_of=AS_OF)
    with pytest.raises(MeasureError, match="as_of"):
        await build_candidate_snapshot(_conn(), symbol="CBA.AU", theme=tv, as_of=AS_OF - timedelta(days=1))


@pytest.mark.asyncio
async def test_theme_without_macro_thesis_builds_with_null_regime() -> None:
    conn = _conn(macro=None)
    conn.theme["macro_thesis_id"] = None  # type: ignore[index]
    tv = await build_theme_version(conn, theme_code="big-4-banks", as_of=AS_OF)
    assert tv.macro_thesis_id is None and tv.regime_quadrant is None
    assert tv.measures["macro_thesis_id"] is None
    assert not any(e.evidence_id.startswith("theme:macro") for e in tv.evidence)


# --- SQL admissibility ---------------------------------------------------------------


def test_measure_sql_is_bound_and_admissible() -> None:
    for sql in (SQL_THEME, SQL_MEMBERS, SQL_MACRO, SQL_FACTORS, SQL_SECTOR, SQL_PRICES):
        assert_measure_sql_admissible(sql)
        assert "$1" in sql
    with pytest.raises(MeasureError, match="forbidden token"):
        assert_measure_sql_admissible("SELECT prob_up FROM prices")
    with pytest.raises(MeasureError, match="non-admissible"):
        assert_measure_sql_admissible("SELECT 1 FROM current_holdings")
    with pytest.raises(MeasureError, match="non-admissible"):
        assert_measure_sql_admissible("SELECT 1 FROM prices JOIN portfolio_daily_snapshots USING (dt)")


# --- repository -----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_repository_round_trips_both_artifacts_through_payload() -> None:
    conn = _conn()
    tv, cand = await _build_pair(conn)
    await save_theme_version(conn, tv)
    await save_candidate_snapshot(conn, cand)
    assert [s.split(" ")[2] for s, _ in conn.executed] == ["theme_versions", "candidate_snapshots"]
    assert all("ON CONFLICT" in s and "DO NOTHING" in s for s, _ in conn.executed)
    assert conn.executed[1][1][7] is True  # quality_passed shadow column
    assert load_theme_version.__name__ and (await load_theme_version(conn, tv.theme_version_id)) == tv
    assert (await load_candidate_snapshot(conn, cand.candidate_id)) == cand
    with pytest.raises(LookupError):
        await load_candidate_snapshot(conn, "cand-missing")


def test_migration_0051_is_on_disk_and_records_its_apply() -> None:
    text = MIGRATION.read_text()
    assert "0051_theme_candidates.sql" in text.splitlines()[0]
    assert "_theme_candidates_forbid_mutation" in text
    assert "APPLIED 2026-09-02 as ledger version 20260902204920" in text
