"""Unit tests for jobs/ingest_regulatory.py — the degraded-source visibility path.

Pure-function tests over ``_degraded_note``: no network, no DB. They pin the
behaviour that makes a silently-dead RSS source (e.g. Treasury WAF-403 from
Render egress) visible via ``job_runs.error_message`` + ``check_cron_health``,
instead of hiding behind the 0.5 partial-success threshold.
"""
from __future__ import annotations

from jobs.ingest_regulatory import SOURCES, _degraded_note


def test_degraded_note_flags_a_dead_source() -> None:
    # SOURCES == [RBA, Treasury]; Treasury hard-failed (None), RBA returned 3.
    note = _degraded_note(SOURCES, [3, None])
    assert note is not None
    assert "Treasury" in note
    assert "1/2" in note


def test_degraded_note_none_when_all_healthy() -> None:
    # 0 rows is a healthy slow-news-day outcome, NOT a dead feed — only None counts.
    assert _degraded_note(SOURCES, [3, 0]) is None
    assert _degraded_note(SOURCES, [0, 0]) is None


def test_degraded_note_flags_all_dead() -> None:
    note = _degraded_note(SOURCES, [None, None])
    assert note is not None
    assert "2/2" in note
    assert "RBA" in note and "Treasury" in note
