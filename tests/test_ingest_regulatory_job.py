"""Unit tests for jobs/ingest_regulatory.py — the degraded-source visibility path.

Pure-function tests over ``_degraded_note``: no network, no DB. They pin the
behaviour that makes a silently-dead RSS source (e.g. Treasury WAF-403 from
Render egress) visible via ``job_runs.error_message`` + ``check_cron_health``,
instead of hiding behind the partial-success threshold.

The ``_degraded_note`` tests below use a local 2-item ``SourceSpec`` fixture
rather than the production ``SOURCES`` list, deliberately: production
``SOURCES`` shrank to a single entry when Treasury was retired
(2026-07-18), and these tests exercise ``_degraded_note``'s general
N-source behaviour, not however many sources production happens to have
today — that exact coupling is what broke when Treasury was removed
(``zip(sources, totals, strict=True)`` raising ``ValueError`` against a
2-item ``totals`` list once ``SOURCES`` shrank to 1 item).
"""
from __future__ import annotations

import pytest

from asxos.jobs._helpers import assert_partial_success
from jobs.ingest_regulatory import SOURCES, SourceSpec, _degraded_note

_FIXTURE_SOURCES = [
    SourceSpec("A", "https://example.com/a", "other"),
    SourceSpec("B", "https://example.com/b", "other"),
]


def test_degraded_note_flags_a_dead_source() -> None:
    # _FIXTURE_SOURCES == [A, B]; B hard-failed (None), A returned 3.
    note = _degraded_note(_FIXTURE_SOURCES, [3, None])
    assert note is not None
    assert "B" in note
    assert "1/2" in note


def test_degraded_note_none_when_all_healthy() -> None:
    # 0 rows is a healthy slow-news-day outcome, NOT a dead feed — only None counts.
    assert _degraded_note(_FIXTURE_SOURCES, [3, 0]) is None
    assert _degraded_note(_FIXTURE_SOURCES, [0, 0]) is None


def test_degraded_note_flags_all_dead() -> None:
    note = _degraded_note(_FIXTURE_SOURCES, [None, None])
    assert note is not None
    assert "2/2" in note
    assert "A" in note and "B" in note


def test_sources_is_rba_only() -> None:
    """Canary: forces a human to touch this test (and the threshold
    constant in main()) if a second source is ever re-added — the pairing
    that silently didn't happen for Treasury at threshold=0.5."""
    assert [s.name for s in SOURCES] == ["RBA"]


def test_solo_rba_failure_hard_fails() -> None:
    """Regression pin for the Treasury dead-feed incident (2026-07-18):
    with N=1, a solo source failure must hard-fail via
    assert_partial_success, not degrade silently the way 1/2 did before
    Treasury's removal."""
    with pytest.raises(RuntimeError, match=r"only 0/1 succeeded"):
        assert_partial_success(
            [None],
            is_ok=lambda r: r is not None,
            threshold=1.0,
            label="ingest_regulatory",
            identifiers=[s.name for s in SOURCES],
            allow_empty=False,
        )


def test_solo_rba_zero_events_is_healthy_not_failure() -> None:
    """0 events is a slow-news-day, not a failure — must still pass at
    threshold=1.0."""
    n_ok = assert_partial_success(
        [0],
        is_ok=lambda r: r is not None,
        threshold=1.0,
        label="ingest_regulatory",
        identifiers=[s.name for s in SOURCES],
        allow_empty=False,
    )
    assert n_ok == 1
