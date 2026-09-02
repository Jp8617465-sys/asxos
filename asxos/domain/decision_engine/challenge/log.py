"""Finding / disposition log — the only calibration signal before Slice 4 (ADR §1.6).

Every finding a challenge produces is persisted with the `ChallengeResult`
(migration 0048 `challenge_results`, append-only, content-addressed) — that
is the FINDING log and needs no new table. The DISPOSITION (did James accept
the finding or override it) has no slot on the frozen `ChallengeResult`
contract, so this wave carries it in memory as `FindingDisposition` and feeds
it back into the outcome ladder: a `material` finding blocks `pass` until it
carries an `accepted` disposition, and every `overridden` blocking finding is
counted — the override rate on `blocking` is the primary health metric named
in §1.6. Persisting dispositions is the next migration window's item, stated
in the PR body rather than smuggled in here.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from asxos.domain.decision_engine.types import ChallengeFinding, Contract, require_utc

Disposition = Literal["accepted", "overridden"]


def finding_key(finding: ChallengeFinding) -> str:
    """Stable identity for a finding: severity + text + sorted evidence ids."""
    return f"{finding.severity}|{finding.finding}|{','.join(sorted(finding.evidence_ids))}"


class FindingDisposition(Contract):
    finding_key: str = Field(min_length=1, max_length=12_000)
    disposition: Disposition
    reason: str = Field(min_length=1, max_length=5_000)
    recorded_by: Literal["james"] = "james"
    recorded_at: datetime

    def matches(self, finding: ChallengeFinding) -> bool:
        return self.finding_key == finding_key(finding)


class DispositionLog(Contract):
    entries: tuple[FindingDisposition, ...] = Field(default=(), max_length=1_000)

    def for_finding(self, finding: ChallengeFinding) -> FindingDisposition | None:
        for entry in reversed(self.entries):
            if entry.matches(finding):
                return entry
        return None

    def accepted(self, finding: ChallengeFinding) -> bool:
        entry = self.for_finding(finding)
        return entry is not None and entry.disposition == "accepted"

    def override_rate_blocking(self, findings: tuple[ChallengeFinding, ...]) -> tuple[int, int]:
        """(overridden blocking findings, blocking findings) — the §1.6 health metric."""
        blocking = [f for f in findings if f.severity == "blocking"]
        overridden = [f for f in blocking if (e := self.for_finding(f)) is not None and e.disposition == "overridden"]
        return len(overridden), len(blocking)


def record(log: DispositionLog, finding: ChallengeFinding, *, disposition: Disposition, reason: str, at: datetime) -> DispositionLog:
    entry = FindingDisposition(
        finding_key=finding_key(finding), disposition=disposition, reason=reason, recorded_at=require_utc(at)
    )
    return DispositionLog(entries=(*log.entries, entry))
