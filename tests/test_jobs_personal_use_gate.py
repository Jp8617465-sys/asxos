"""Firewall-gate regression: personal-data jobs hard-fail without ASXOS_PERSONAL_USE=1.

R14 audit follow-up (2026-07-18): snapshot_portfolio, check_au_positions,
check_us_positions and check_thesis_invalidations read/write holdings + theses
(personal-advice data under s766B). Before this change they relied SOLELY on
render.yaml setting the env var -- no in-code backstop like build_portfolio.py
has, so a manual run or render.yaml drift would silently process personal data.

compute_opportunity_cost (sprint follow-up, 2026-07-19) ranks redeployment
candidates against active theses -- same personal-advice-data class -- and had
the same gap: render.yaml-only enforcement, no in-code backstop.

``require_personal_use_job()`` is that backstop. These tests pin (a) the helper's
own behaviour and (b) that each entry point calls it BEFORE any DB access, so a
missing flag fails loud (CLAUDE.md #10) rather than reaching init_pool().
"""
from __future__ import annotations

import asyncio
from datetime import date

import pytest

from asxos.jobs._helpers import require_personal_use_job


def test_helper_raises_when_flag_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ASXOS_PERSONAL_USE", raising=False)
    with pytest.raises(RuntimeError, match="ASXOS_PERSONAL_USE"):
        require_personal_use_job()


def test_helper_raises_when_flag_not_one(monkeypatch: pytest.MonkeyPatch) -> None:
    # Any value other than exactly "1" must fail closed.
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "0")
    with pytest.raises(RuntimeError, match="ASXOS_PERSONAL_USE"):
        require_personal_use_job()


def test_helper_passes_when_flag_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    require_personal_use_job()  # must not raise


@pytest.mark.parametrize(
    "module_name, entry",
    [
        ("jobs.snapshot_portfolio", lambda m: m.main(None, None)),
        ("jobs.check_au_positions", lambda m: m._run(date(2026, 7, 18))),
        ("jobs.check_us_positions", lambda m: m._run(date(2026, 7, 18))),
        ("jobs.check_thesis_invalidations", lambda m: m._run(date(2026, 7, 18))),
        ("jobs.compute_opportunity_cost", lambda m: m.main()),
    ],
)
def test_job_entry_point_gated(
    monkeypatch: pytest.MonkeyPatch, module_name: str, entry: object
) -> None:
    # The gate is the first statement of each entry point (before init_pool),
    # so a missing flag raises RuntimeError without ever touching the DB.
    import importlib

    monkeypatch.delenv("ASXOS_PERSONAL_USE", raising=False)
    module = importlib.import_module(module_name)
    with pytest.raises(RuntimeError, match="ASXOS_PERSONAL_USE"):
        asyncio.run(entry(module))  # type: ignore[operator]
