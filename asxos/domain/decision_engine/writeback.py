"""A-47: a built decision packet records that it examined a thesis.

Before this module, `jobs/build_decision_packets.py` challenged every approved
thesis daily and wrote the result to `decision_packets` -- and nothing wrote to
the thesis's own discipline ledger. Measured 2026-09-17: CBA (thesis 1) had three
packets, three challenge results, and exactly one `thesis_revisions` row ever,
the `opened` one from 2026-05-28. The system examined the thesis three times
and recorded none of it where discipline lives.

WHAT THIS DOES NOT DO, AND WHY IT IS THE POINT. It never writes
`theses.last_revisited_at` or `revisit_due_at`. `asxos/domain/theses/discipline.py`
states the invariant its staleness escalation depends on: every clock reset is a
human keystroke, so no job, agent or model can suppress a staleness finding. A
packet build is a system examination, not a human revisit. CBA stays overdue
after this lands -- correctly -- until James looks. What changes is that when he
does, the examinations are on the ledger, each citing the packet it came from.

The row goes in as `revision_type='packet_examined'` (migration 0060), which is
deliberately OUTSIDE the brief's answering-revision allowlist
(`asxos/brief/compose.py`, `last_answering_revision_at`), so no reader counts it
as an answer. Reusing `reviewed_no_change` would have let a machine "buy another
N days" -- the failure discipline.py names by that exact type.

The INSERT itself stays in `asxos/domain/theses/service.py` (the single
`INSERT INTO thesis_revisions` site); this module only decides what to record
and routes through the narrow public entry there.
"""
from __future__ import annotations

from typing import Any, Final

from asxos.domain.decision_engine.types import DecisionCase, EvidenceTier
from asxos.domain.theses.service import record_system_examination

#: The revision type 0060 admits for this path. Bound to the compose.py
#: allowlist by tests/test_decision_writeback.py so the two cannot drift apart.
REVISION_TYPE: Final[str] = "packet_examined"

#: Weakest-first, so the recorded confidence is the packet's weakest evidence.
_TIER_RANK: Final[dict[str, int]] = {"speculative": 0, "inferred": 1, "verified": 2}

SQL_EXAMINATION_EXISTS: Final[str] = (
    "SELECT 1 FROM thesis_revisions "
    "WHERE thesis_id = $1 AND revision_type = $2 AND evidence_citations ? $3 LIMIT 1"
)


def evidence_confidence_for(case: DecisionCase) -> EvidenceTier:
    """The weakest tier among the packet's evidence items -- conservative by design.

    `EvidenceTier` and `thesis_revisions.evidence_confidence` share the same three
    values (verified / inferred / speculative), so this needs no translation.
    """
    tiers = [item.evidence_tier for item in case.evidence.items]
    if not tiers:
        raise ValueError(
            f"packet {case.decision.decision_packet_id} carries no evidence items -- "
            "an examination with nothing behind it is not recorded"
        )
    weakest = min(tiers, key=lambda t: _TIER_RANK[t])
    return weakest


def reasoning_for(case: DecisionCase) -> str:
    """What the row says. A statement of fact about the packet, never a directive (s766B)."""
    d = case.decision
    return (
        f"Decision packet {d.decision_packet_id} examined this thesis at {d.as_of.isoformat()} "
        f"and reached recommendation_state={d.recommendation_state!r} "
        f"(challenge {d.challenge_result_id}). Recorded by build_decision_packets. "
        "This row is a system examination and does not reset the revisit clock."
    )


def citations_for(case: DecisionCase) -> list[str]:
    """The packet id and its content hash -- enough to replay exactly what was examined."""
    d = case.decision
    return [f"decision_packet:{d.decision_packet_id}", f"content_hash:{d.content_hash}"]


async def examination_exists(conn: Any, *, thesis_id: int, packet_id: str) -> bool:
    """`thesis_revisions` has no unique on the packet, so idempotency is checked, not enforced."""
    row = await conn.fetchrow(
        SQL_EXAMINATION_EXISTS, thesis_id, REVISION_TYPE, f"decision_packet:{packet_id}"
    )
    return row is not None


async def record_packet_examination(conn: Any, *, thesis_id: int, case: DecisionCase) -> bool:
    """Append one `packet_examined` row for this packet; False if already recorded.

    Idempotent on the packet id via `examination_exists`. Writes exactly one
    INSERT (through `theses.service`) and nothing else -- no UPDATE to `theses`,
    ever. Returns whether a row was written so the caller can count honestly.
    """
    packet_id = case.decision.decision_packet_id
    if await examination_exists(conn, thesis_id=thesis_id, packet_id=packet_id):
        return False
    await record_system_examination(
        conn,
        thesis_id=thesis_id,
        examined_at=case.decision.knowledge_cutoff,
        reasoning=reasoning_for(case),
        evidence_confidence=evidence_confidence_for(case),
        evidence_citations=citations_for(case),
        diff={
            "recommendation_state": case.decision.recommendation_state,
            "decision_packet_id": packet_id,
            "challenge_result_id": case.decision.challenge_result_id,
            "expires_at": case.decision.expires_at.isoformat(),
        },
    )
    return True
