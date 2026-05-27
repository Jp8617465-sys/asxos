"""
Tests for asxos/jobs/_helpers.py — assert_partial_success and UpstreamBlocked.

Helper tests are sync (no asyncio); the helper is pure and synchronous.
Per-job integration tests live in tests/test_sync_fundamentals_job.py,
tests/test_ingest_regulatory_job.py, and tests/test_ingest_news_job.py.
"""
from __future__ import annotations

import pytest

from asxos.jobs._helpers import UpstreamBlocked, assert_partial_success

# ---------------------------------------------------------------------------
# UpstreamBlocked
# ---------------------------------------------------------------------------


def test_upstream_blocked_is_runtime_error() -> None:
    """UpstreamBlocked subclasses RuntimeError so existing handlers catch it."""
    assert issubclass(UpstreamBlocked, RuntimeError)


def test_upstream_blocked_carries_message() -> None:
    exc = UpstreamBlocked("sync_prices stale")
    assert "sync_prices stale" in str(exc)


# ---------------------------------------------------------------------------
# assert_partial_success — empty input
# ---------------------------------------------------------------------------


def test_empty_results_raises_by_default() -> None:
    """Closes the silent-empty-input hole — empty input must not look like success."""
    with pytest.raises(RuntimeError, match="empty input"):
        assert_partial_success([], is_ok=lambda r: True, threshold=0.75, label="t")


def test_empty_results_with_allow_empty_returns_zero() -> None:
    """Opt-in: allow_empty=True returns 0 (e.g. when empty universe is legitimate)."""
    assert assert_partial_success(
        [], is_ok=lambda r: True, threshold=0.75, label="t", allow_empty=True
    ) == 0


# ---------------------------------------------------------------------------
# assert_partial_success — happy path
# ---------------------------------------------------------------------------


def test_all_success_returns_count() -> None:
    n = assert_partial_success(
        [True, True, True], is_ok=lambda r: r is True, threshold=0.75, label="t"
    )
    assert n == 3


def test_at_threshold_succeeds() -> None:
    """Boundary: ratio == threshold passes (>= comparison, not >)."""
    n = assert_partial_success(
        [True, True, True, False],
        is_ok=lambda r: r is True,
        threshold=0.75,
        label="t",
    )
    assert n == 3  # 3/4 = 0.75 is NOT < 0.75


def test_just_above_threshold_succeeds() -> None:
    n = assert_partial_success(
        [True] * 8 + [False] * 2,
        is_ok=lambda r: r is True,
        threshold=0.75,
        label="t",
    )
    assert n == 8  # 8/10 = 0.80 >= 0.75


# ---------------------------------------------------------------------------
# assert_partial_success — threshold breach
# ---------------------------------------------------------------------------


def test_below_threshold_raises() -> None:
    with pytest.raises(RuntimeError, match=r"only 1/4"):
        assert_partial_success(
            [True, False, False, False],
            is_ok=lambda r: r is True,
            threshold=0.75,
            label="my_job",
        )


def test_error_message_contains_label_and_threshold() -> None:
    with pytest.raises(RuntimeError) as excinfo:
        assert_partial_success(
            [False, False],
            is_ok=lambda r: r is True,
            threshold=0.75,
            label="my_job",
        )
    msg = str(excinfo.value)
    assert "my_job" in msg
    assert "75%" in msg
    assert "0.0%" in msg  # actual ratio


def test_error_message_lists_failing_identifiers_when_provided() -> None:
    """Identifier capture — operators don't have to grep stdout."""
    with pytest.raises(RuntimeError) as excinfo:
        assert_partial_success(
            [True, False, False, False],
            is_ok=lambda r: r is True,
            threshold=0.75,
            label="t",
            identifiers=["BHP.AU", "CBA.AU", "WBC.AU", "ANZ.AU"],
        )
    msg = str(excinfo.value)
    # First failing identifier must appear in the diagnostic
    assert "CBA.AU" in msg
    assert "WBC.AU" in msg
    assert "ANZ.AU" in msg


def test_error_message_truncates_failing_identifiers_to_ten() -> None:
    """At most 10 identifiers shown; remainder counted in '+N more'."""
    results = [False] * 15
    identifiers = [f"sym_{i}" for i in range(15)]
    with pytest.raises(RuntimeError) as excinfo:
        assert_partial_success(
            results,
            is_ok=lambda r: r is True,
            threshold=0.75,
            label="t",
            identifiers=identifiers,
        )
    msg = str(excinfo.value)
    assert "sym_0" in msg
    assert "sym_9" in msg  # 10th entry (0-indexed)
    assert "+5 more" in msg
    # 11th entry should NOT appear in the list (but the count covers it)
    assert "'sym_10'" not in msg


def test_error_message_no_identifiers_section_when_none_passed() -> None:
    with pytest.raises(RuntimeError) as excinfo:
        assert_partial_success(
            [False, False],
            is_ok=lambda r: r is True,
            threshold=0.75,
            label="t",
        )
    assert "first failing" not in str(excinfo.value)


# ---------------------------------------------------------------------------
# assert_partial_success — predicate handles exceptions in gather results
# ---------------------------------------------------------------------------


def test_predicate_handles_baseexception_entries() -> None:
    """When caller used return_exceptions=True, predicate filters exceptions."""
    results = [1, RuntimeError("boom"), 2, ValueError("nope")]
    # Predicate excludes exceptions
    n = assert_partial_success(
        results,
        is_ok=lambda r: isinstance(r, int),
        threshold=0.5,  # 2/4 = 0.5 passes
        label="t",
    )
    assert n == 2


def test_baseexception_below_threshold_raises_with_identifiers() -> None:
    results = [1, RuntimeError("x"), RuntimeError("y"), RuntimeError("z")]
    identifiers = ["a", "b", "c", "d"]
    with pytest.raises(RuntimeError) as excinfo:
        assert_partial_success(
            results,
            is_ok=lambda r: isinstance(r, int),
            threshold=0.75,
            label="t",
            identifiers=identifiers,
        )
    msg = str(excinfo.value)
    # Failing items are b, c, d (where the exceptions are)
    assert "'b'" in msg
    assert "'c'" in msg
    assert "'d'" in msg


# ---------------------------------------------------------------------------
# assert_partial_success — int|None pattern (ingest_regulatory)
# ---------------------------------------------------------------------------


def test_int_or_none_predicate_distinguishes_zero_from_failure() -> None:
    """The 'int | None' pattern: 0 is success (no new rows); None is failure."""
    # 2/3 sources succeeded (one with 0 new rows, one with 5); 1 failed
    results = [0, 5, None]
    n = assert_partial_success(
        results,
        is_ok=lambda r: r is not None,
        threshold=0.5,
        label="t",
    )
    assert n == 2


def test_int_or_none_below_threshold_raises() -> None:
    results = [None, None, 5]  # 1/3 succeeded; below 0.5
    with pytest.raises(RuntimeError, match=r"only 1/3"):
        assert_partial_success(
            results,
            is_ok=lambda r: r is not None,
            threshold=0.5,
            label="t",
        )


# ---------------------------------------------------------------------------
# assert_partial_success — threshold parameter discipline
# ---------------------------------------------------------------------------


def test_threshold_zero_always_passes() -> None:
    """threshold=0.0 means any success ratio (including 0) passes."""
    n = assert_partial_success(
        [False, False], is_ok=lambda r: r is True, threshold=0.0, label="t"
    )
    assert n == 0  # 0/2 == 0.0 is NOT < 0.0


def test_threshold_one_requires_all_success() -> None:
    with pytest.raises(RuntimeError):
        assert_partial_success(
            [True, True, False],
            is_ok=lambda r: r is True,
            threshold=1.0,
            label="t",
        )


def test_threshold_is_required_keyword() -> None:
    """threshold has no default; callsites must pick deliberately."""
    with pytest.raises(TypeError):
        # Intentionally missing threshold=
        assert_partial_success(  # type: ignore[call-arg]
            [True], is_ok=lambda r: r is True, label="t"
        )
