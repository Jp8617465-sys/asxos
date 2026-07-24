"""Agent-run logging — Phase 2b. The write side of agent_runs/agent_evidence
that Phase 1 never built (Phase 1 only built create_thesis_from_agent_run(),
which reads an already-logged run; nothing wrote one).

log_agent_run() is the one genuinely new mechanism in Phase 2 — no
precedent anywhere in this repo. It is a generic pipeline stage, reused
identically by every discovery agent (macro-economist now; theme-researcher/
instrument-selector in Phase 2c), NOT specific to any one object_type — the
domain-specific "take a validated proposal and write a governed row"
functions (asxos/domain/macro_theses/service.py::create_macro_thesis_from_agent_run(),
its Phase 2c themes/theme_holdings siblings) are a separate, later step.

Evidence is captured from the agent's own SELECT results, not backfilled
after the fact: agent_evidence.snapshot_data is "the literal row(s) observed
at cite-time" (migration 0033) — a backfill pass re-running a query minutes
later would reconstruct an approximation, not what was actually seen. The
agent's own structured output block IS the evidence (see
.claude/agents/macro-economist.md's output contract).

evidence_citation_ids in the raw proposal JSON use two forms:
  - "local:N" — a position reference into THIS call's own evidence_raw list
    (the agent's own fresh findings, which have no real evidence_id yet at
    the time the agent wrote its output).
  - a bare int — a pre-existing agent_evidence.evidence_id from an earlier
    run (re-cited evidence). Supported for completeness; no Phase 2b agent
    produces this today.
Both forms are resolved to real evidence_ids before Pydantic validation,
since MacroThesisProposal.evidence_citation_ids is typed list[int].

References:
  asxos/domain/theses/schemas.py (the three proposal Pydantic models;
    module docstring's json.loads(raw, parse_float=Decimal) hazard)
  migrations/0033_governance_schema_core.sql (agent_runs, agent_evidence)
  docs/proposals/governance-first-architecture-2026-06-30.md Section 4.2
  CLAUDE.md non-negotiables #1, #5, #10
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from decimal import Decimal
from typing import Any

import asyncpg
from pydantic import BaseModel

from asxos.domain.theses.schemas import (
    MacroThesisProposal,
    ThemeHoldingProposal,
    ThemeProposal,
)

_KNOWN_AGENTS = frozenset({"macro-economist", "sector-screener", "theme-researcher"})  # extended in Phase 2c

_PROPOSAL_MODELS: dict[str, type[BaseModel]] = {
    "macro_thesis": MacroThesisProposal,
    "theme": ThemeProposal,
    "theme_holding": ThemeHoldingProposal,
    # 'thesis' deliberately omitted — no ThesisProposal schema exists yet
    # (see asxos/domain/theses/service.py::create_thesis_from_agent_run()'s
    # documented Phase 1/2 gap). Attempting object_type='thesis' here raises
    # a clear error below rather than a bare KeyError.
}

_VALID_TIERS = frozenset({"verified", "inferred", "speculative"})


def _canonical_json(data: dict[str, Any]) -> str:
    """Stable serialisation for hashing: sorted keys, no whitespace,
    default=str for any embedded Decimal/datetime so re-serialising a
    parse_float=Decimal-parsed structure never raises."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)


def _snapshot_hash(data: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(data).encode("utf-8")).hexdigest()


def _resolve_evidence_citations(
    citations: list[Any], position_to_id: dict[int, int]
) -> list[int]:
    resolved: list[int] = []
    for cite in citations:
        if isinstance(cite, str) and cite.startswith("local:"):
            position_str = cite.removeprefix("local:")
            if not position_str.isdigit():
                raise ValueError(f"malformed local citation {cite!r} — expected 'local:<int>'")
            position = int(position_str)
            if position not in position_to_id:
                raise ValueError(
                    f"evidence_citation_ids references {cite!r}, but only "
                    f"{len(position_to_id)} evidence claim(s) were logged in this run"
                )
            resolved.append(position_to_id[position])
        elif isinstance(cite, int):
            resolved.append(cite)
        else:
            raise ValueError(
                f"evidence_citation_ids entries must be an int or a 'local:N' "
                f"string, got {cite!r}"
            )
    return resolved


async def log_agent_run(
    conn: asyncpg.Connection,
    agent_name: str,
    *,
    subject: str | None,
    summary: str,
    object_type: str | None,
    proposal_raw: str | None,
    evidence_raw: str | None,
) -> int:
    """Validate an agent's proposal + evidence and persist them as
    agent_evidence rows + one agent_runs row, in one transaction. Returns
    the new run_id.

    Hard-fails on:
      - agent_name not in _KNOWN_AGENTS
      - (object_type is None) != (proposal_raw is None) — mirrors the
        agent_runs_object_type_and_proposed_together DB CHECK; failing here
        gives a clean ValueError instead of an asyncpg CheckViolationError
      - object_type == 'thesis' (no ThesisProposal schema exists — see
        module docstring)
      - empty summary
      - a claim dict missing required fields (claim/tier), or tier not in
        verified/inferred/speculative
      - a proposal's evidence_citation_ids referencing a local:N position
        that wasn't logged in this call, or a malformed citation
      - Pydantic validation failure on the resolved proposal
      - any resolved evidence_citation_ids entry not resolving to a real,
        non-speculative agent_evidence row (the DB round-trip check
        schemas.py's own docstring says the Pydantic layer can't do alone)
    """
    if agent_name not in _KNOWN_AGENTS:
        raise ValueError(
            f"Unknown agent_name {agent_name!r} — must be one of {sorted(_KNOWN_AGENTS)}"
        )
    if (object_type is None) != (proposal_raw is None):
        raise ValueError(
            "object_type and proposal_raw must be given together or both omitted "
            f"(got object_type={object_type!r}, proposal_raw="
            f"{'<given>' if proposal_raw else None!r})"
        )
    if object_type == "thesis":
        raise ValueError(
            "object_type='thesis' has no Pydantic schema to validate against yet "
            "(m14_candidate_agentic_thesis_drafter) — see "
            "asxos/domain/theses/service.py::create_thesis_from_agent_run()'s "
            "documented Phase 1/2 gap."
        )
    if object_type is not None and object_type not in _PROPOSAL_MODELS:
        raise ValueError(
            f"Unknown object_type {object_type!r} — must be one of "
            f"{sorted(_PROPOSAL_MODELS)}"
        )
    if not summary or not summary.strip():
        raise ValueError("summary is required to log an agent run")

    async with conn.transaction():
        # ------------------------------------------------------------
        # Step 1: insert fresh evidence claims (if any), collect real IDs.
        # ------------------------------------------------------------
        position_to_id: dict[int, int] = {}
        verified_count = inferred_count = speculative_count = 0
        claim_count = 0

        if evidence_raw:
            claims = json.loads(evidence_raw, parse_float=Decimal)
            claim_count = len(claims)
            for position, claim in enumerate(claims):
                tier = claim.get("tier")
                if tier not in _VALID_TIERS:
                    raise ValueError(
                        f"evidence claim at position {position} has tier={tier!r}, "
                        f"must be one of {sorted(_VALID_TIERS)}"
                    )
                claim_text = claim.get("claim")
                if not claim_text or not str(claim_text).strip():
                    raise ValueError(
                        f"evidence claim at position {position} is missing a non-empty 'claim'"
                    )
                snapshot_data = claim.get("snapshot_data")
                if tier != "speculative" and snapshot_data is None:
                    raise ValueError(
                        f"evidence claim at position {position} has tier={tier!r} "
                        "but no snapshot_data — only speculative claims may omit it"
                    )
                snapshot_hash = _snapshot_hash(snapshot_data) if snapshot_data is not None else None

                source_as_of = claim.get("source_as_of")
                if isinstance(source_as_of, str):
                    # JSON has no timestamp type — the agent contract emits
                    # source_as_of as an ISO-8601 string, but asyncpg's
                    # TIMESTAMPTZ codec accepts only datetime objects (a str
                    # bind raises at execute time against a real connection;
                    # mocked tests can't see this, same failure class as the
                    # transition-order incident in transitions.py).
                    try:
                        source_as_of = datetime.fromisoformat(source_as_of)
                    except ValueError as exc:
                        raise ValueError(
                            f"evidence claim at position {position} has a "
                            f"non-ISO-8601 source_as_of {source_as_of!r}"
                        ) from exc

                if tier == "verified":
                    verified_count += 1
                elif tier == "inferred":
                    inferred_count += 1
                else:
                    speculative_count += 1

                evidence_row = await conn.fetchrow(
                    """
                    INSERT INTO agent_evidence
                        (agent_name, claim, tier, source_type, source_table,
                         source_as_of, source_url, snapshot_data, snapshot_hash,
                         related_symbol, related_theme_code)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb, $9, $10, $11)
                    RETURNING evidence_id
                    """,
                    agent_name,
                    claim_text,
                    tier,
                    claim.get("source_type", "db_query"),
                    claim.get("source_table"),
                    source_as_of,
                    claim.get("source_url"),
                    # default=str: snapshot_data was parsed with parse_float=
                    # Decimal (per schemas.py's documented hazard), so a bare
                    # json.dumps() would raise TypeError on any Decimal value.
                    # Serialising Decimals as strings (not JSON numbers) also
                    # matches this codebase's existing convention for Decimal-
                    # in-JSONB (theses/service.py's diff JSONB contract) —
                    # exact precision preserved, not just crash-avoidance.
                    json.dumps(snapshot_data, default=str) if snapshot_data is not None else None,
                    snapshot_hash,
                    claim.get("related_symbol"),
                    claim.get("related_theme_code"),
                )
                position_to_id[position] = evidence_row["evidence_id"]

        # ------------------------------------------------------------
        # Step 2: resolve + validate the proposal, if any.
        # ------------------------------------------------------------
        proposed_object_json: str | None = None
        if proposal_raw is not None:
            proposal_dict = json.loads(proposal_raw, parse_float=Decimal)
            raw_citations = proposal_dict.get("evidence_citation_ids", [])
            resolved_ids = _resolve_evidence_citations(raw_citations, position_to_id)
            proposal_dict["evidence_citation_ids"] = resolved_ids

            model_cls = _PROPOSAL_MODELS[object_type]  # type: ignore[index]
            proposal = model_cls(**proposal_dict)

            # DB round-trip check the Pydantic layer can't do alone (schemas.py
            # module docstring) — every cited ID must be a real, non-speculative
            # agent_evidence row.
            if resolved_ids:
                tier_rows = await conn.fetch(
                    "SELECT evidence_id, tier FROM agent_evidence WHERE evidence_id = ANY($1::bigint[])",
                    resolved_ids,
                )
                tier_by_id = {r["evidence_id"]: r["tier"] for r in tier_rows}
                for eid in resolved_ids:
                    if eid not in tier_by_id:
                        raise ValueError(
                            f"evidence_citation_ids references evidence_id={eid}, "
                            "which does not exist in agent_evidence"
                        )
                    if tier_by_id[eid] == "speculative":
                        raise ValueError(
                            f"evidence_citation_ids references evidence_id={eid}, "
                            "which has tier='speculative' — only verified/inferred "
                            "evidence may be cited"
                        )

            proposed_object_json = json.dumps(proposal.model_dump(mode="json"))

        # ------------------------------------------------------------
        # Step 3: insert the agent_runs row.
        # ------------------------------------------------------------
        row = await conn.fetchrow(
            """
            INSERT INTO agent_runs
                (agent_name, subject, summary, claim_count, verified_count,
                 inferred_count, speculative_count, object_type, proposed_object)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9::jsonb)
            RETURNING run_id
            """,
            agent_name,
            subject,
            summary,
            claim_count,
            verified_count,
            inferred_count,
            speculative_count,
            object_type,
            proposed_object_json,
        )
        return int(row["run_id"])  # asyncpg Record.__getitem__ returns Any
