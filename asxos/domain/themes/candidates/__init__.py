"""Theme and candidate engine — Stage 3 (target-architecture.md §15).

`types.py` — `ThemeVersion` and `CandidateSnapshot`, content-addressed and
validator-fenced so neither can carry a recommendation, weight, size, target
or verdict. `measures.py` — deterministic breadth, factor and liquidity
measures from bound SQL. `extraction_boundary.py` — the ONLY place LLM text
enters, as `EvidenceItem`s that are tier-capped and verb-screened. `builder.py`
— assembles both artifacts from a governed theme. `repository.py` — append-only
persistence (migration 0051).

A candidate is evidence. It becomes anything more only by passing through the
decision engine's gate, where rule #11 and the s766B firewall already live.
"""
from __future__ import annotations

from asxos.domain.themes.candidates.types import CandidateSnapshot, ThemeVersion

__all__ = ["CandidateSnapshot", "ThemeVersion"]
