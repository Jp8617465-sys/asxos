"""Point-in-time replay and lineage — Stage 1 exit clauses (1) and (2).

`target-architecture.md` §15, Stage 1 exit gate:

  (1) one historical decision date can be replayed using ONLY facts with
      `known_at <= cutoff`;
  (2) raw-to-canonical lineage resolves exactly.

`cutoff.replay_snapshot()` answers (1): it assembles the facts that were
knowable for one symbol at one cutoff, refuses anything whose provenance is
not `filed` unless the caller opts in, and hashes the result so two runs can
be compared byte-for-byte. `lineage.resolve_lineage()` answers (2): every
canonical row the snapshot used is traced to the raw source rows it was
derived from, and any gap is reported rather than papered over.

Read-only. No Model A. No capital. Nothing here recommends anything.
"""
from __future__ import annotations

from asxos.domain.replay.cutoff import ReplaySnapshot, replay_snapshot, snapshot_hash
from asxos.domain.replay.lineage import LineageReport, resolve_lineage

__all__ = [
    "LineageReport",
    "ReplaySnapshot",
    "replay_snapshot",
    "resolve_lineage",
    "snapshot_hash",
]
