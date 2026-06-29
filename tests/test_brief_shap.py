"""Tests for the shared SHAP-factor formatting helper (asxos/domain/brief/shap.py).

Covers ranking by |value|, bias exclusion, top-n truncation, the empty/None/bad
cases, and the asyncpg-may-hand-back-a-str path.
"""
from __future__ import annotations

from asxos.domain.brief.shap import format_top_factors, rank_shap_factors


def test_rank_orders_by_absolute_value_and_skips_bias() -> None:
    shap = {"bias": 0.9, "mom_12_1": -0.42, "earnings_yield": 0.31, "pb_ratio": 0.05}
    ranked = rank_shap_factors(shap, n=3)
    assert [k for k, _ in ranked] == ["mom_12_1", "earnings_yield", "pb_ratio"]
    # bias is excluded even though it has the largest magnitude
    assert "bias" not in dict(ranked)


def test_rank_truncates_to_n() -> None:
    shap = {"a": 0.5, "b": 0.4, "c": 0.3, "d": 0.2}
    assert len(rank_shap_factors(shap, n=2)) == 2
    assert [k for k, _ in rank_shap_factors(shap, n=2)] == ["a", "b"]


def test_format_top_factors_signed_three_dp() -> None:
    shap = {"earnings_yield": 0.31, "mom_12_1": 0.18}
    assert format_top_factors(shap, n=2) == "earnings_yield+0.310, mom_12_1+0.180"


def test_format_negative_sign() -> None:
    assert format_top_factors({"mom_12_1": -0.42}, n=1) == "mom_12_1-0.420"


def test_empty_dict_returns_empty_string() -> None:
    assert format_top_factors({}, n=3) == ""
    assert rank_shap_factors({}, n=3) == []


def test_none_returns_empty_string() -> None:
    assert format_top_factors(None, n=3) == ""


def test_only_bias_returns_empty() -> None:
    # bias is the sole key → nothing to display
    assert format_top_factors({"bias": -0.15}, n=3) == ""


def test_json_string_input_is_parsed() -> None:
    # asyncpg may hand the JSONB back as a raw str when no codec is registered
    assert format_top_factors('{"mom_12_1": 0.42}', n=1) == "mom_12_1+0.420"


def test_malformed_json_string_is_safe() -> None:
    assert format_top_factors("not json", n=1) == ""


def test_none_and_non_numeric_values_skipped() -> None:
    shap = {"a": None, "b": "x", "c": 0.2}
    ranked = rank_shap_factors(shap, n=5)
    assert ranked == [("c", 0.2)]
