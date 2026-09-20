"""The one-off that retires the two theses approved before the gate existed.

What matters here is not that it retires two rows — it is everything it refuses
to do on the way.

The job hardcodes two thesis ids, which is only safe while the rows are what it
believes. So it re-checks each premise before writing and raises rather than
proceeding: the symbol must match the id, the status must still be `approved`,
and the evidence count must still be zero. If someone has cited evidence for
either row since this was written, the marking needs re-deciding by a person, not
replaying by a job.

It must also leave the HUBS **position** alone. Retiring a thesis is a statement
about content, not about a holding; `holding_lots` and `current_holdings` are the
portfolio's source of truth and this job must never name them.
"""
from __future__ import annotations

import re
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
import yaml

import jobs.mark_pre_gate_theses as job_mod
from asxos.domain.theses.types import Thesis

ROOT = Path(__file__).resolve().parents[1]


def _thesis(thesis_id: int, symbol: str, governance_status: str = "approved") -> Thesis:
    """A real Thesis with placeholder fields; only the three this job reads vary."""
    now = datetime(2026, 5, 28, tzinfo=UTC)
    return Thesis(
        thesis_id=thesis_id, symbol=symbol, status="watching",
        governance_status=governance_status,
        thesis_text="placeholder",
        entry_band_lower=None, entry_band_upper=None,
        stop_price=None, target_price=None, timeline_days=None,
        invalidation_conditions=(), themes=(),
        actual_entry_price=None, actual_entry_at=None,
        actual_exit_price=None, actual_exit_at=None,
        last_revisited_at=now, revisit_due_at=now, opened_at=now, closed_at=None,
    )


class FakeConn:
    def __init__(self) -> None:
        self.executed: list[str] = []

    def transaction(self) -> Any:
        @asynccontextmanager
        async def _tx() -> Any:
            yield

        return _tx()


class Harness:
    """Stands in for the service layer, recording what the job asked it to do."""

    def __init__(
        self,
        *,
        theses: dict[int, Thesis] | None = None,
        evidence: dict[int, list[dict[str, Any]]] | None = None,
    ) -> None:
        self.theses = theses or {
            1: _thesis(1, "CBA.AU"),
            2: _thesis(2, "HUBS.NYSE"),
        }
        self.evidence = evidence or {}
        self.retired: list[tuple[int, str]] = []

    async def get_thesis(self, conn: Any, thesis_id: int) -> Thesis | None:
        return self.theses.get(thesis_id)

    async def list_thesis_evidence(
        self, conn: Any, thesis_id: int, **kwargs: Any
    ) -> list[dict[str, Any]]:
        return self.evidence.get(thesis_id, [])

    async def retire_object(self, conn: Any, thesis_id: int, *, reasoning: str) -> Thesis:
        self.retired.append((thesis_id, reasoning))
        return self.theses[thesis_id]


@pytest.fixture
def harness(monkeypatch: pytest.MonkeyPatch) -> Harness:
    h = Harness()
    monkeypatch.setattr(job_mod.svc, "get_thesis", h.get_thesis)
    monkeypatch.setattr(job_mod.svc, "list_thesis_evidence", h.list_thesis_evidence)
    monkeypatch.setattr(job_mod.svc, "retire_object", h.retire_object)

    @asynccontextmanager
    async def _acquire() -> Any:
        yield FakeConn()

    monkeypatch.setattr(job_mod, "acquire", _acquire)
    return h


# --- the default writes nothing ----------------------------------------------------


async def test_dry_run_is_the_default_and_opens_no_write_path(harness: Harness) -> None:
    summary = await job_mod.run(persist=False)
    assert harness.retired == []
    assert summary["planned"] == ["CBA.AU", "HUBS.NYSE"]
    assert summary["retired"] == []


async def test_persist_retires_both_through_the_service_helper(harness: Harness) -> None:
    summary = await job_mod.run(persist=True)
    assert [tid for tid, _ in harness.retired] == [1, 2]
    assert summary["retired"] == ["CBA.AU", "HUBS.NYSE"]


async def test_a_second_run_writes_nothing(harness: Harness) -> None:
    harness.theses = {
        1: _thesis(1, "CBA.AU", "retired"),
        2: _thesis(2, "HUBS.NYSE", "retired"),
    }
    summary = await job_mod.run(persist=True)
    assert harness.retired == []
    assert summary["skipped_already_retired"] == ["CBA.AU", "HUBS.NYSE"]


# --- every premise is re-checked, not assumed --------------------------------------


async def test_a_renumbered_id_refuses_rather_than_retiring_the_wrong_thesis(
    harness: Harness,
) -> None:
    harness.theses[2] = _thesis(2, "WBC.AU")
    with pytest.raises(RuntimeError, match=re.escape("expected 'HUBS.NYSE'")):
        await job_mod.run(persist=True)
    assert harness.retired == [], "nothing may be written once a premise fails"


async def test_a_missing_thesis_refuses(harness: Harness) -> None:
    del harness.theses[1]
    with pytest.raises(RuntimeError, match="does not exist"):
        await job_mod.run(persist=True)


async def test_a_row_moved_deliberately_is_not_this_jobs_to_touch(harness: Harness) -> None:
    """A row someone put at pending_review was moved on purpose. This job exists
    only for rows that took the pre-0059 DEFAULT."""
    harness.theses[1] = _thesis(1, "CBA.AU", "pending_review")
    with pytest.raises(RuntimeError, match="not 'approved'"):
        await job_mod.run(persist=True)
    assert harness.retired == []


async def test_evidence_appearing_since_this_was_written_refuses(harness: Harness) -> None:
    """The whole premise is that these two rows have no evidence. If one now does,
    a person decides again — the job does not replay a stale judgement."""
    harness.evidence = {2: [{"evidence_id": 99}]}
    with pytest.raises(RuntimeError, match="evidence row"):
        await job_mod.run(persist=True)
    assert harness.retired == [], "CBA must not be retired on a run that aborts on HUBS"


# --- what the reasoning has to say -------------------------------------------------


def test_each_reasoning_names_what_the_row_is_and_why_it_is_not_an_approval() -> None:
    """The reasoning IS the marking — it is what a reader finds six months from now.

    Pinned because a later edit that trimmed it to "retired, stale" would leave the
    rows marked and the meaning gone, and nothing else in the system would notice.
    """
    cba_symbol, cba = job_mod.MARKINGS[1]
    hubs_symbol, hubs = job_mod.MARKINGS[2]
    assert (cba_symbol, hubs_symbol) == ("CBA.AU", "HUBS.NYSE")

    assert "Demo fixture" in cba
    assert "0059" in cba and "DEFAULT" in cba
    assert "No evidence was backfilled" in cba

    assert "ESPP" in hubs
    assert "not a thesis James formed" in hubs
    assert "HOLDING is untouched" in hubs
    assert "0059" in hubs and "DEFAULT" in hubs
    assert "No evidence was backfilled" in hubs


def test_the_job_never_names_a_holdings_table() -> None:
    """Retiring a thesis is a statement about content, not about a position."""
    source = (ROOT / "jobs/mark_pre_gate_theses.py").read_text()
    body = "\n".join(
        line for line in source.splitlines() if not line.lstrip().startswith("#")
    )
    # The docstring and MARKINGS text mention them by name on purpose; what must not
    # exist is a query against them.
    for table in ("holding_lots", "current_holdings"):
        assert f"FROM {table}" not in body
        assert f"UPDATE {table}" not in body
        assert f"INTO {table}" not in body


def test_the_job_writes_no_revision_and_moves_no_clock() -> None:
    source = (ROOT / "jobs/mark_pre_gate_theses.py").read_text()
    body = "\n".join(
        line
        for line in source.splitlines()
        if not line.lstrip().startswith("#") and "--" not in line
    )
    assert "_insert_revision" not in body
    assert "record_system_examination" not in body
    assert "add_thesis_evidence" not in body
    assert "log_evidence" not in body


# --- the lane ----------------------------------------------------------------------


def test_the_lane_is_dispatch_only_and_defaults_to_writing_nothing() -> None:
    wf = yaml.safe_load((ROOT / ".github/workflows/mark-pre-gate-theses.yml").read_text())
    # PyYAML parses a bare `on:` key as the boolean True.
    triggers = wf[True] if True in wf else wf["on"]
    assert set(triggers) == {"workflow_dispatch"}, "a correction lane must never be scheduled"
    assert triggers["workflow_dispatch"]["inputs"]["persist"]["default"] is False

    job = wf["jobs"]["mark"]
    assert job["steps"][0]["with"]["ref"] == "refs/heads/main"
    assert job["env"]["ASXOS_PERSONAL_USE"] == "1"
    # DATABASE_URL and nothing else: no EODHD, FRED, RESEND, GitHub or Supabase token.
    secrets = [v for v in job["env"].values() if isinstance(v, str) and "secrets." in v]
    assert secrets == ["${{ secrets.DATABASE_URL }}"]
