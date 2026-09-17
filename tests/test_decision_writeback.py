"""A-47: a built decision packet records that it examined a thesis -- and nothing else.

The load-bearing property is negative: this path must never reset the revisit
clock. `asxos/domain/theses/discipline.py` states the invariant its staleness
escalation depends on (every clock reset is a human keystroke), and
`asxos/brief/compose.py` implements it as an explicit allowlist of "answering"
revision types. So the tests here bind three literals together -- the type the
writeback emits, the type migration 0060 admits, and the allowlist compose.py
counts -- and fail if any of them drifts.
"""
from __future__ import annotations

import re
from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

import jobs.backfill_packet_examinations as backfill_mod
from asxos.domain.decision_engine import writeback

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "asxos/brief/compose.py"
MIGRATION = ROOT / "migrations/0060_thesis_revisions_packet_examined.sql"
DISCIPLINE = ROOT / "asxos/domain/theses/discipline.py"

#: The answering set as verified against compose.py on 2026-09-17. If compose.py
#: changes this list the test below fails on purpose: the writeback's safety rests
#: on packet_examined staying OUTSIDE it, and a silent widening would defeat that.
ANSWERING_AS_VERIFIED = {
    "target_adjusted", "reviewed_no_change", "status_change", "entered",
    "expired", "exited", "exited_by_stop", "exited_by_target",
}


def _answering_allowlist_from_compose() -> set[str]:
    src = COMPOSE.read_text()
    m = re.search(r"last_answering_revision_at.*?revision_type IN \((.*?)\)", src, re.S) or re.search(
        r"revision_type IN \((.*?)\)\s*\)\s*AS last_answering_revision_at", src, re.S
    )
    assert m, "compose.py no longer carries the answering-revision allowlist this writeback depends on"
    return set(re.findall(r"'([a-z_]+)'", m.group(1)))


def _case(*, tiers: tuple[str, ...] = ("verified", "inferred"), state: str = "abstain") -> Any:
    return SimpleNamespace(
        decision=SimpleNamespace(
            decision_packet_id="dpk-cba-1-2026-09-16",
            content_hash="c" * 64,
            as_of=date(2026, 9, 16),
            knowledge_cutoff=datetime(2026, 9, 16, 20, 40, tzinfo=UTC),
            recommendation_state=state,
            challenge_result_id="chl-cba-1-2026-09-16",
            expires_at=datetime(2026, 10, 15, tzinfo=UTC),
        ),
        evidence=SimpleNamespace(items=tuple(SimpleNamespace(evidence_tier=t) for t in tiers)),
    )


class FakeConn:
    def __init__(self, *, already: bool = False) -> None:
        self.already = already
        self.fetchrow_calls: list[tuple[str, tuple[object, ...]]] = []
        self.execute_calls: list[tuple[str, tuple[object, ...]]] = []

    async def fetchrow(self, query: str, *args: object) -> Any:
        self.fetchrow_calls.append((query, args))
        return {"?column?": 1} if self.already else None

    async def execute(self, query: str, *args: object) -> str:
        self.execute_calls.append((query, args))
        return "INSERT 0 1"


# --- the three literals are one literal ---------------------------------------


def test_packet_examined_is_outside_the_brief_answering_allowlist() -> None:
    allowlist = _answering_allowlist_from_compose()
    assert allowlist == ANSWERING_AS_VERIFIED, (
        f"compose.py's answering allowlist changed to {sorted(allowlist)}; re-verify that "
        f"{writeback.REVISION_TYPE!r} must still sit outside it before updating this pin"
    )
    assert writeback.REVISION_TYPE not in allowlist, (
        "packet_examined would count as an ANSWER in the brief -- a job could then reset the "
        "staleness clock, which is the exact failure discipline.py names"
    )


def test_migration_0060_admits_exactly_the_type_the_writeback_emits() -> None:
    sql = MIGRATION.read_text()
    m = re.search(r"CHECK \(revision_type IN \((.*?)\)\)", sql, re.S)
    assert m, "0060 must carry the widened CHECK"
    admitted = set(re.findall(r"'([a-z_]+)'", m.group(1)))
    assert writeback.REVISION_TYPE in admitted
    # Expand-only: every pre-existing type from 0021 is still admitted.
    for t in ("opened", "assumption_change", "target_adjusted", "stop_adjusted", "timeline_extended",
              "reviewed_no_change", "status_change", "entered", "exited", "exited_by_stop",
              "exited_by_target", "expired", "analyst_action"):
        assert t in admitted, f"0060 dropped {t!r}; the widening must be expand-only"


def test_discipline_docstring_names_the_exception_it_now_carries() -> None:
    """§10: a doc that live state contradicts is fixed in the same PR. This pins the fix."""
    text = " ".join(DISCIPLINE.read_text().split())  # the docstring wraps; match on words
    assert "packet_examined" in text and "record_system_examination" in text
    assert "A system examination is not a human revisit" in text


# --- the writeback never touches the clock -----------------------------------------


def test_writeback_module_emits_no_update_and_names_no_clock_column() -> None:
    """Checked on the AST, not the text: docstrings and comments are allowed to *explain*
    what the module never does; only code and SQL/string constants are held to it."""
    import ast

    tree = ast.parse((ROOT / "asxos/domain/decision_engine/writeback.py").read_text())
    docstrings: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            first = node.body[0] if node.body else None
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                docstrings.add(id(first.value))
    forbidden = ("UPDATE ", "last_revisited_at", "revisit_due_at", "governance_status")
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docstrings:
            for f in forbidden:
                assert f not in node.value, (
                    f"writeback.py has a string constant containing {f!r} (line {node.lineno}): "
                    "this path records an examination and must never reset the clock or "
                    "transition governance"
                )
        if isinstance(node, ast.Name):
            assert node.id not in forbidden[1:], f"writeback.py references {node.id!r} (line {node.lineno})"
        if isinstance(node, ast.Attribute):
            assert node.attr not in forbidden[1:], f"writeback.py references .{node.attr} (line {node.lineno})"


async def test_record_routes_through_the_single_insert_site_and_writes_no_sql_itself() -> None:
    conn = FakeConn()
    with patch.object(writeback, "record_system_examination", AsyncMock()) as rec:
        written = await writeback.record_packet_examination(conn, thesis_id=1, case=_case())
    assert written is True
    rec.assert_awaited_once()
    kw = rec.await_args.kwargs
    assert kw["thesis_id"] == 1
    assert kw["examined_at"] == datetime(2026, 9, 16, 20, 40, tzinfo=UTC)
    assert kw["evidence_confidence"] == "inferred"  # weakest of (verified, inferred)
    assert kw["evidence_citations"] == [
        "decision_packet:dpk-cba-1-2026-09-16", "content_hash:" + "c" * 64,
    ]
    assert kw["diff"]["recommendation_state"] == "abstain"
    # The module itself issued no INSERT/UPDATE -- only the existence probe.
    assert conn.execute_calls == []
    assert len(conn.fetchrow_calls) == 1 and "thesis_revisions" in conn.fetchrow_calls[0][0]


async def test_a_second_run_for_the_same_packet_writes_nothing() -> None:
    conn = FakeConn(already=True)
    with patch.object(writeback, "record_system_examination", AsyncMock()) as rec:
        written = await writeback.record_packet_examination(conn, thesis_id=1, case=_case())
    assert written is False
    rec.assert_not_awaited()


def test_confidence_is_the_weakest_tier_and_refuses_an_empty_packet() -> None:
    assert writeback.evidence_confidence_for(_case(tiers=("verified", "speculative", "inferred"))) == "speculative"
    assert writeback.evidence_confidence_for(_case(tiers=("verified",))) == "verified"
    with pytest.raises(ValueError, match="no evidence items"):
        writeback.evidence_confidence_for(_case(tiers=()))


def test_reasoning_states_the_packet_and_contains_no_directive() -> None:
    """s766B: the row records what the packet concluded, never what James should do."""
    text = writeback.reasoning_for(_case(state="exit_review"))
    assert "dpk-cba-1-2026-09-16" in text and "exit_review" in text
    assert "does not reset the revisit clock" in text
    # Word-bounded: "recommendation_state" is a field name, "recommend" would be a directive.
    for verb in (r"\bbuy\b", r"\bsell\b", r"\bshould\b", r"\brecommend(s|ed)?\b", r"\baccumulate\b", r"\btake a position\b"):
        assert not re.search(verb, text, re.I), f"reasoning must not carry the directive {verb!r}"


# --- the service entry is narrow ----------------------------------------------------


async def test_record_system_examination_cannot_choose_the_type_or_the_source() -> None:
    from asxos.domain.theses import service

    conn = FakeConn()
    await service.record_system_examination(
        conn, thesis_id=1, examined_at=datetime(2026, 9, 16, tzinfo=UTC),
        reasoning="x", evidence_confidence="verified", evidence_citations=["decision_packet:p"],
    )
    assert len(conn.execute_calls) == 1
    sql, args = conn.execute_calls[0]
    assert "INSERT INTO thesis_revisions" in sql and "UPDATE" not in sql
    assert args[2] == "packet_examined"
    assert args[5] == "system_screen"


async def test_record_system_examination_enforces_0034_provenance_before_postgres() -> None:
    from asxos.domain.theses import service

    with pytest.raises(ValueError, match="evidence_confidence and at least one"):
        await service.record_system_examination(
            FakeConn(), thesis_id=1, examined_at=datetime(2026, 9, 16, tzinfo=UTC),
            reasoning="x", evidence_confidence="verified", evidence_citations=[],
        )


# --- the backfill job -----------------------------------------------------------------


def test_backfill_selects_only_approved_theses_via_the_composed_key() -> None:
    q = backfill_mod.SQL_PACKETS_FOR_APPROVED_THESES
    assert "governance_status = 'approved'" in q and "closed_at IS NULL" in q
    assert "tv.symbol || '.' || tv.exchange = t.symbol" in q, (
        "thesis_versions keys on (symbol, exchange) while theses keys on 'SYM.EXCH'; the "
        "composed key is the live join and was verified to resolve (1:CBA.AU) on 2026-09-17"
    )
    assert "thesis_version_id" in q
