"""Persistence for the decision-engine contract chain — Slice 1 (D5).

Targets `migrations/0048_decision_packets.sql` (authored alongside this
module, NOT YET APPLIED — James applies it via
`mcp__supabase__apply_migration`; this module is inert against a live
database until then). Five append-only tables, one per top-level
`ContentAddressedContract` in `asxos/domain/decision_engine/types.py`
(FROZEN — never edited to make persistence easier):
`evidence_packets -> thesis_versions -> challenge_results ->
portfolio_assessments -> decision_packets`.

Round-trip fidelity is the load-bearing property (migration 0048 header):
every table's `payload JSONB` column is the sole authoritative source for
reconstruction (`ModelClass.model_validate(row["payload"])`). Every other
column on these tables is a derived, NON-AUTHORITATIVE shadow copy for
indexing/filtering — `load()`/`load_case()` never read a value back from a
shadow column. `NUMERIC(18,6)`/`TIMESTAMPTZ` round-trip through Postgres at
a fixed display scale that can differ in string form from what
`model_dump(mode="json")` originally produced even when numerically equal
(`Decimal("100")` vs `Decimal("100.000000")`), which would silently break
`verify_content_hash()` if a shadow column were ever read back instead.

Deliberate correction of the mission brief's literal `save(packet:
DecisionPacket)` / `supersede(old_id, new: DecisionPacket)` signatures —
documented here rather than silently changed. A bare `DecisionPacket` only
carries ID/hash references to its four upstream artifacts
(`evidence_packet_id`, `thesis_version_id`, `challenge_result_id`,
`portfolio_assessment_id`); it never carries their bodies. A function typed
on `DecisionPacket` alone cannot construct the four upstream rows the same
brief also requires it to insert. `DecisionCase` (types.py:546) is the only
object that actually bundles all five bodies (`evidence`, `thesis`,
`challenge`, `portfolio`, `decision`) — and constructing one already forces
every one of `DecisionCase`'s own integrity checks (identity linkage,
content-hash verification, evidence-citation closure, temporal
chain-ordering) to pass before `save()` ever touches the database. `save`
and `supersede` below are typed on `DecisionCase`; this is the minimal
correction that makes the stated behaviour (one transaction, five INSERTs,
dependency order, payload = `model_dump(mode="json")`, shadow columns from
the same object) possible at all, not a redesign of it.

`load_case()`'s case-level wrapper fields (`case_id`, `label`,
`changed_since_prior`) are NOT persisted anywhere in migration 0048 — no
table carries them, by design: they are `DecisionCase`-only presentation
metadata, not part of the immutable artifact chain the migration protects.
`load_case()` therefore derives them deterministically from the persisted
`decision_packet_id`/`supersedes_packet_id` rather than inventing
free-floating state. This means `save(case)` followed by `load_case(id)`
reproduces the five underlying artifacts exactly but NOT necessarily the
original `case_id`/`label`/`changed_since_prior` strings — only `load()`
(which returns the bare `DecisionPacket`) is asserted byte-for-byte
round-trip identical by the test suite.

Import-isolation, matching `results_review/pit_db.py`: this module reads
only through `asxos.db.acquire()` / injected connections and the five
tables above. It never reads `signals`, `signal_outcomes`,
`model_versions.prob_up`/`shap_factors`, or any other Model A surface
(rule #11) — nothing here has a reason to.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any, Protocol

from asxos import db
from asxos.domain.decision_engine.types import (
    ChallengeResult,
    DecisionCase,
    DecisionPacket,
    EvidencePacket,
    PortfolioAssessment,
    ThesisVersion,
)


class RepositoryConn(Protocol):
    """The subset of `asyncpg.Connection` this module relies on.

    Named explicitly (rather than importing `asyncpg.Connection`) so tests
    can pass a plain mock object without constructing a real connection —
    matching `.claude/rules/api-conventions.md`'s testing convention ("mock
    `asxos.db.acquire` and pass synthetic asyncpg `Record`-shaped dicts").
    """

    async def execute(self, query: str, *args: object) -> str: ...

    async def fetchrow(
        self, query: str, *args: object
    ) -> Mapping[str, object] | None: ...

    def transaction(self) -> Any: ...


class DecisionPacketNotFoundError(LookupError):
    """Raised when `load()`/`load_case()` cannot find the requested packet."""


def _payload(row: Mapping[str, object]) -> dict[str, object]:
    """Extract and JSON-decode a row's `payload` column.

    asyncpg returns `jsonb` columns as raw JSON text (no codec is registered
    in `asxos/db.py`), while a mocked test connection may hand back an
    already-decoded `dict` directly — mirroring the existing
    `isinstance(raw, str)` guard convention at
    `asxos/domain/theses/service.py:112-113` for exactly the same reason.
    """
    raw = row["payload"]
    if isinstance(raw, str):
        return dict(json.loads(raw))
    if isinstance(raw, Mapping):
        return dict(raw)
    raise TypeError(f"unexpected payload column type: {type(raw)!r}")


def _dump(model: EvidencePacket | ThesisVersion | ChallengeResult | PortfolioAssessment | DecisionPacket) -> str:
    """Canonical JSON text for a `payload::jsonb` bind parameter."""
    return json.dumps(model.model_dump(mode="json"))


async def _insert_evidence_packet(conn: RepositoryConn, evidence: EvidencePacket) -> None:
    await conn.execute(
        """
        INSERT INTO evidence_packets
            (evidence_packet_id, content_hash, as_of, knowledge_cutoff,
             expires_at, data_mode, created_at, payload)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb)
        ON CONFLICT (evidence_packet_id) DO NOTHING
        """,
        evidence.evidence_packet_id,
        evidence.content_hash,
        evidence.as_of,
        evidence.knowledge_cutoff,
        evidence.expires_at,
        evidence.data_mode,
        evidence.created_at,
        _dump(evidence),
    )


async def _insert_thesis_version(conn: RepositoryConn, thesis: ThesisVersion) -> None:
    await conn.execute(
        """
        INSERT INTO thesis_versions
            (thesis_version_id, content_hash, security_id, symbol, exchange,
             version, evidence_packet_id, as_of, knowledge_cutoff, created_at,
             theme, investment_question, variant_view, thesis_summary,
             horizon_months, payload)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14,
                $15, $16::jsonb)
        ON CONFLICT (thesis_version_id) DO NOTHING
        """,
        thesis.thesis_version_id,
        thesis.content_hash,
        thesis.security_id,
        thesis.symbol,
        thesis.exchange,
        thesis.version,
        thesis.evidence_packet_id,
        thesis.as_of,
        thesis.knowledge_cutoff,
        thesis.created_at,
        thesis.theme,
        thesis.investment_question,
        thesis.variant_view,
        thesis.thesis_summary,
        thesis.horizon_months,
        _dump(thesis),
    )


async def _insert_challenge_result(conn: RepositoryConn, challenge: ChallengeResult) -> None:
    await conn.execute(
        """
        INSERT INTO challenge_results
            (challenge_result_id, content_hash, thesis_version_id,
             evidence_packet_id, as_of, knowledge_cutoff, created_at,
             outcome, strongest_bear_case, independent_of_author, payload)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11::jsonb)
        ON CONFLICT (challenge_result_id) DO NOTHING
        """,
        challenge.challenge_result_id,
        challenge.content_hash,
        challenge.thesis_version_id,
        challenge.evidence_packet_id,
        challenge.as_of,
        challenge.knowledge_cutoff,
        challenge.created_at,
        challenge.outcome,
        challenge.strongest_bear_case,
        challenge.independent_of_author,
        _dump(challenge),
    )


async def _insert_portfolio_assessment(
    conn: RepositoryConn, portfolio: PortfolioAssessment
) -> None:
    await conn.execute(
        """
        INSERT INTO portfolio_assessments
            (portfolio_assessment_id, content_hash, portfolio_snapshot_id,
             thesis_version_id, as_of, knowledge_cutoff, created_at,
             assessment_state, loss_budget_aud, marginal_risk,
             opportunity_cost, payload)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12::jsonb)
        ON CONFLICT (portfolio_assessment_id) DO NOTHING
        """,
        portfolio.portfolio_assessment_id,
        portfolio.content_hash,
        portfolio.portfolio_snapshot_id,
        portfolio.thesis_version_id,
        portfolio.as_of,
        portfolio.knowledge_cutoff,
        portfolio.created_at,
        portfolio.assessment_state,
        portfolio.loss_budget_aud,
        portfolio.marginal_risk,
        portfolio.opportunity_cost,
        _dump(portfolio),
    )


async def _insert_decision_packet(conn: RepositoryConn, decision: DecisionPacket) -> None:
    await conn.execute(
        """
        INSERT INTO decision_packets
            (decision_packet_id, content_hash, schema_version, as_of,
             knowledge_cutoff, recommendation_state, expires_at,
             expiry_reason, portfolio_snapshot_id, evidence_packet_id,
             thesis_version_id, challenge_result_id, portfolio_assessment_id,
             benchmark_id, staging_framework, scenario_summary, risk_summary,
             decision_ask, model_independence, created_at,
             supersedes_packet_id, payload)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14,
                $15, $16, $17, $18, $19, $20, $21, $22::jsonb)
        """,
        decision.decision_packet_id,
        decision.content_hash,
        decision.schema_version,
        decision.as_of,
        decision.knowledge_cutoff,
        decision.recommendation_state,
        decision.expires_at,
        decision.expiry_reason,
        decision.portfolio_snapshot_id,
        decision.evidence_packet_id,
        decision.thesis_version_id,
        decision.challenge_result_id,
        decision.portfolio_assessment_id,
        decision.benchmark_id,
        decision.staging_framework,
        decision.scenario_summary,
        decision.risk_summary,
        decision.decision_ask,
        decision.model_independence,
        decision.created_at,
        decision.supersedes_packet_id,
        _dump(decision),
    )


async def save(case: DecisionCase, *, conn: RepositoryConn | None = None) -> None:
    """Persist one fully-linked `DecisionCase` in dependency order.

    See the module docstring for why this is typed on `DecisionCase` rather
    than the mission brief's literal `DecisionPacket`. Runs inside a single
    transaction: `evidence_packets -> thesis_versions -> challenge_results
    -> portfolio_assessments -> decision_packets`. The four upstream
    artifact INSERTs are `ON CONFLICT DO NOTHING` (content-addressed —
    `DecisionCase`'s own validators already proved identical id implies
    identical content, see `verify_content_hash` in
    `validate_identity_integrity_and_gate_chain`); `decision_packets` is
    never conflict-skipped — every `decision_packet_id` is expected to be
    new, and the table's forbid-mutation trigger backstops that.

    `conn` is an injection seam for tests and for callers that already hold
    a transaction; the default acquires a fresh connection from
    `asxos.db.acquire()`.
    """
    if conn is not None:
        async with conn.transaction():
            await _insert_evidence_packet(conn, case.evidence)
            await _insert_thesis_version(conn, case.thesis)
            await _insert_challenge_result(conn, case.challenge)
            await _insert_portfolio_assessment(conn, case.portfolio)
            await _insert_decision_packet(conn, case.decision)
        return
    async with db.acquire() as live_conn:
        async with live_conn.transaction():
            await _insert_evidence_packet(live_conn, case.evidence)
            await _insert_thesis_version(live_conn, case.thesis)
            await _insert_challenge_result(live_conn, case.challenge)
            await _insert_portfolio_assessment(live_conn, case.portfolio)
            await _insert_decision_packet(live_conn, case.decision)


async def load(
    decision_packet_id: str, *, conn: RepositoryConn | None = None
) -> DecisionPacket:
    """Reconstruct a `DecisionPacket` exclusively from `decision_packets.payload`.

    Never reads a shadow column (see module docstring). Raises
    `DecisionPacketNotFoundError` if no row exists.
    """
    query = "SELECT payload FROM decision_packets WHERE decision_packet_id = $1"
    if conn is not None:
        row = await conn.fetchrow(query, decision_packet_id)
    else:
        async with db.acquire() as live_conn:
            row = await live_conn.fetchrow(query, decision_packet_id)
    if row is None:
        raise DecisionPacketNotFoundError(
            f"no decision_packets row for decision_packet_id={decision_packet_id!r}"
        )
    return DecisionPacket.model_validate(_payload(row))


async def load_case(
    decision_packet_id: str, *, conn: RepositoryConn | None = None
) -> DecisionCase:
    """Reconstruct a full `DecisionCase` from the five persisted payloads.

    Fetches `decision_packets` by id, then its four referenced upstream
    rows by the ids the decision itself carries
    (`evidence_packet_id`/`thesis_version_id`/`challenge_result_id`/
    `portfolio_assessment_id`) — every fetch reconstructs exclusively via
    `ModelClass.model_validate(row["payload"])`, never a shadow column.

    `case_id`/`label`/`changed_since_prior` are not persisted anywhere in
    migration 0048 (see module docstring) — they are derived deterministically
    from the decision packet's own identity rather than invented, so calling
    this twice for the same `decision_packet_id` is idempotent.
    """

    async def _fetch_one(
        active_conn: RepositoryConn, table: str, id_column: str, id_value: str
    ) -> dict[str, object]:
        # table/id_column are hardcoded literals passed by _load_all() below,
        # never caller-supplied input — same trust boundary as
        # asxos/domain/governance/transitions.py::apply_governance_transition().
        row = await active_conn.fetchrow(
            f"SELECT payload FROM {table} WHERE {id_column} = $1",
            id_value,
        )
        if row is None:
            raise DecisionPacketNotFoundError(
                f"no {table} row for {id_column}={id_value!r}"
            )
        return _payload(row)

    async def _load_all(active_conn: RepositoryConn) -> DecisionCase:
        decision_payload = await _fetch_one(
            active_conn, "decision_packets", "decision_packet_id", decision_packet_id
        )
        decision = DecisionPacket.model_validate(decision_payload)
        evidence = EvidencePacket.model_validate(
            await _fetch_one(
                active_conn,
                "evidence_packets",
                "evidence_packet_id",
                decision.evidence_packet_id,
            )
        )
        thesis = ThesisVersion.model_validate(
            await _fetch_one(
                active_conn,
                "thesis_versions",
                "thesis_version_id",
                decision.thesis_version_id,
            )
        )
        challenge = ChallengeResult.model_validate(
            await _fetch_one(
                active_conn,
                "challenge_results",
                "challenge_result_id",
                decision.challenge_result_id,
            )
        )
        portfolio = PortfolioAssessment.model_validate(
            await _fetch_one(
                active_conn,
                "portfolio_assessments",
                "portfolio_assessment_id",
                decision.portfolio_assessment_id,
            )
        )
        changed_since_prior = (
            f"Supersedes decision_packet_id={decision.supersedes_packet_id}."
            if decision.supersedes_packet_id is not None
            else "Initial decision packet on file for this case; no prior version."
        )
        return DecisionCase(
            case_id=decision.decision_packet_id,
            label=f"Persisted decision case for {decision.decision_packet_id}",
            changed_since_prior=changed_since_prior,
            evidence=evidence,
            thesis=thesis,
            challenge=challenge,
            portfolio=portfolio,
            decision=decision,
        )

    if conn is not None:
        return await _load_all(conn)
    async with db.acquire() as live_conn:
        return await _load_all(live_conn)


async def supersede(
    old_id: str, new: DecisionCase, *, conn: RepositoryConn | None = None
) -> None:
    """Append-only supersession: INSERT `new`, never UPDATE `old_id`'s row.

    Asserts `new.decision.supersedes_packet_id == old_id`, then delegates to
    `save(new)` — a pure INSERT. The `decision_packets_forbid_mutation`
    trigger (migration 0048) backstops this mechanically even if a future
    caller tries to UPDATE the old row directly.
    """
    if new.decision.supersedes_packet_id != old_id:
        raise ValueError(
            "supersede() requires new.decision.supersedes_packet_id == old_id "
            f"(got {new.decision.supersedes_packet_id!r} != {old_id!r})"
        )
    await save(new, conn=conn)
