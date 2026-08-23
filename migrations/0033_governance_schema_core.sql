-- 0033_governance_schema_core.sql
--
-- Governance schema, Phase 1 (governance-first-architecture-2026-06-30.md
-- Section 4.1, 4.2, Phase 1 entry in Section 7).
--
-- Adds the provenance/approval state machine for AI-agent-originated content,
-- orthogonal to theses.status (the existing research/watching/active/exited
-- investment lifecycle, unchanged). governance_status answers "is this content
-- trustworthy enough to exist/be acted on"; status answers "is capital deployed".
--
-- DEFAULT 'approved' on theses.governance_status grandfathers every existing
-- human-authored row with zero behaviour change -- this is the load-bearing
-- design choice that keeps the existing single-shot `asx thesis open` CLI flow
-- completely unaffected. The draft->evidence_complete->pending_review->approved
-- crawl is exclusively the on-ramp for agent-originated content (Section 4.1).
--
-- New tables (evidence + audit trail; no DDL against themes/theme_holdings/
-- macro_theses here -- their governance columns are Phase 2, not this migration):
--   thesis_evidence   -- evidence attached to an existing thesis
--   agent_evidence     -- pre-thesis evidence (macro/theme research, no thesis yet)
--   agent_runs         -- every agent invocation, whether or not acted on
--   governance_events  -- append-only audit trail of every governance_status transition
--
-- snapshot_data / snapshot_hash: an immutable snapshot of the literal DB row(s)
-- observed at cite-time, not a re-runnable query -- queries/schemas/data drift,
-- a stored query cannot reliably reproduce what was actually seen (doc Section
-- 4.2). snapshot_hash = sha256(canonical_json(snapshot_data)) proves the stored
-- snapshot wasn't edited after the fact; it does NOT (and cannot) prove the live
-- table still matches -- a weaker, separate guarantee this design doesn't claim.
--
-- Applied via: mcp__supabase__apply_migration

-- ============================================================
-- theses: two new governance columns
-- ============================================================
ALTER TABLE theses
    ADD COLUMN governance_status TEXT NOT NULL DEFAULT 'approved'
        CHECK (governance_status IN ('draft','evidence_complete','pending_review','approved','rejected','retired')),
    ADD COLUMN source_run_id BIGINT;  -- FK added below, after agent_runs exists

COMMENT ON COLUMN theses.governance_status IS
    'Provenance/approval state, orthogonal to status (investment lifecycle). '
    'DEFAULT approved grandfathers all existing human-authored rows -- this '
    'column did not exist before migration 0033. See '
    'docs/proposals/governance-first-architecture-2026-06-30.md Section 4.1.';

COMMENT ON COLUMN theses.source_run_id IS
    'NULL = human-authored (the default/common case). Non-NULL references the '
    'agent_runs row that produced this thesis as a draft proposal.';

-- ============================================================
-- agent_runs: every agent invocation, whether or not the human acts on it
-- ============================================================
CREATE TABLE agent_runs (
    run_id              BIGSERIAL    PRIMARY KEY,
    agent_name          TEXT         NOT NULL,
    invoked_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    subject             TEXT,        -- symbol, theme_code, or NULL for macro-economist
    summary             TEXT         NOT NULL,
    claim_count         INT          NOT NULL DEFAULT 0,
    verified_count      INT          NOT NULL DEFAULT 0,
    inferred_count      INT          NOT NULL DEFAULT 0,
    speculative_count   INT          NOT NULL DEFAULT 0,
    -- Full 4-value vocabulary landed now even though only 'thesis' is
    -- reachable in Phase 1 -- macro_thesis/theme/theme_holding are Phase 2
    -- object types; landing the closed CHECK vocabulary once avoids a second
    -- migration purely to widen a CHECK later.
    object_type         TEXT CHECK (object_type IN ('macro_thesis','theme','theme_holding','thesis')),
    proposed_object      JSONB,       -- typed by object_type; validated against a Pydantic
                                       -- model before use; NEVER raw SQL, never table/column
                                       -- names as data (doc Section 4.2 "structured proposals,
                                       -- never raw SQL")
    acted_on             BOOLEAN      NOT NULL DEFAULT FALSE,  -- flipped only by the
                                                                -- approve/reject/draft-creation
                                                                -- service functions
    resulting_object_id   BIGINT,     -- the created row's PK, whichever table object_type names

    CONSTRAINT agent_runs_object_type_and_proposed_together
        CHECK ((object_type IS NULL) = (proposed_object IS NULL))
        -- Both nullable together (an evidence-only run, e.g. market-context-narrator,
        -- proposes nothing) but not independently -- a proposed_object with no
        -- object_type (or vice versa) is malformed, not merely unusual.
);

CREATE INDEX idx_agent_runs_agent_invoked ON agent_runs (agent_name, invoked_at DESC);
CREATE INDEX idx_agent_runs_unacted ON agent_runs (invoked_at DESC) WHERE acted_on = FALSE AND proposed_object IS NOT NULL;

COMMENT ON TABLE agent_runs IS
    'Every discovery/analysis agent invocation. object_type/proposed_object are '
    'a typed proposal, validated against a Pydantic schema before any write -- '
    'this table never stores raw SQL. See asxos/domain/theses/schemas.py.';

-- Now that agent_runs exists, add the FK deferred above.
ALTER TABLE theses
    ADD CONSTRAINT theses_source_run_id_fkey
        FOREIGN KEY (source_run_id) REFERENCES agent_runs(run_id);

-- ============================================================
-- thesis_evidence: evidence attached to an EXISTING thesis
-- ============================================================
CREATE TABLE thesis_evidence (
    evidence_id      BIGSERIAL    PRIMARY KEY,
    thesis_id        BIGINT       NOT NULL REFERENCES theses(thesis_id) ON DELETE CASCADE,
    cited_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    source_agent     TEXT         NOT NULL,  -- matches .claude/agents/<name>.md slug
    tier             TEXT         NOT NULL CHECK (tier IN ('verified','inferred','speculative')),
    claim_text       TEXT         NOT NULL CHECK (claim_text <> ''),
    source_type      TEXT         NOT NULL DEFAULT 'db_query' CHECK (source_type IN ('db_query','external_url')),
    source_table     TEXT,        -- locator only, NULL for speculative; not authoritative
    source_as_of     TIMESTAMPTZ, -- as_of/dt of the cited row, NOT cited_at
    retrieved_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    source_url       TEXT,        -- reserved for a future web-sourcing agent; unused today
                                   -- (no current agent has WebFetch/WebSearch) -- costs
                                   -- nothing to reserve the column now
    snapshot_data    JSONB,       -- the literal row(s) observed at cite-time; NULL only
                                   -- for speculative
    snapshot_hash    TEXT,        -- sha256(canonical_json(snapshot_data)), hex; tamper-evidence
    superseded_at    TIMESTAMPTZ, -- set when re-evaluated and replaced; NULL = live

    CONSTRAINT thesis_evidence_url_requires_external
        CHECK (source_url IS NULL OR source_type = 'external_url'),
    CONSTRAINT thesis_evidence_hash_format
        CHECK (snapshot_hash IS NULL OR snapshot_hash ~ '^[0-9a-f]{64}$'),
    CONSTRAINT thesis_evidence_snapshot_required_unless_speculative
        CHECK (tier = 'speculative' OR snapshot_data IS NOT NULL)
);
CREATE INDEX idx_thesis_evidence_thesis ON thesis_evidence (thesis_id, cited_at DESC);

-- ============================================================
-- agent_evidence: PRE-thesis evidence (macro/theme research, no thesis_id FK)
-- ============================================================
CREATE TABLE agent_evidence (
    evidence_id           BIGSERIAL    PRIMARY KEY,
    agent_name            TEXT         NOT NULL,
    created_at            TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    claim                 TEXT         NOT NULL CHECK (claim <> ''),
    tier                  TEXT         NOT NULL CHECK (tier IN ('verified','inferred','speculative')),
    source_type           TEXT         NOT NULL DEFAULT 'db_query' CHECK (source_type IN ('db_query','external_url')),
    source_table          TEXT,
    source_as_of          TIMESTAMPTZ,
    retrieved_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    source_url            TEXT,
    snapshot_data         JSONB,
    snapshot_hash         TEXT CHECK (snapshot_hash IS NULL OR snapshot_hash ~ '^[0-9a-f]{64}$'),
    related_symbol        TEXT,
    related_theme_code    TEXT REFERENCES themes(theme_code),
    promoted_to_thesis_id BIGINT REFERENCES theses(thesis_id),  -- the join seam
    status                TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','promoted','dismissed')),

    CONSTRAINT agent_evidence_url_requires_external
        CHECK (source_url IS NULL OR source_type = 'external_url'),
    CONSTRAINT agent_evidence_snapshot_required_unless_speculative
        CHECK (tier = 'speculative' OR snapshot_data IS NOT NULL)
);
CREATE INDEX idx_agent_evidence_agent_created ON agent_evidence (agent_name, created_at DESC);
CREATE INDEX idx_agent_evidence_open ON agent_evidence (created_at DESC) WHERE status = 'open';
CREATE INDEX idx_agent_evidence_promoted_thesis ON agent_evidence (promoted_to_thesis_id) WHERE promoted_to_thesis_id IS NOT NULL;

-- ============================================================
-- governance_events: append-only audit trail of every governance_status transition
-- ============================================================
CREATE TABLE governance_events (
    event_id     BIGSERIAL PRIMARY KEY,
    -- Full 4-value vocabulary landed now (see agent_runs.object_type comment above)
    -- even though Phase 1 only ever writes object_type='thesis' rows.
    object_type  TEXT NOT NULL CHECK (object_type IN ('thesis','macro_thesis','theme','theme_holding')),
    object_id    BIGINT NOT NULL,  -- theses.thesis_id in Phase 1; macro_theses.macro_thesis_id /
                                    -- themes.theme_id / theme_holdings.holding_id from Phase 2
    from_status  TEXT NOT NULL CHECK (from_status IN ('draft','evidence_complete','pending_review','approved','rejected','retired')),
    to_status    TEXT NOT NULL CHECK (to_status IN ('draft','evidence_complete','pending_review','approved','rejected','retired')),
    event_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reasoning    TEXT NOT NULL CHECK (reasoning <> ''),
    actor        TEXT NOT NULL DEFAULT 'human' CHECK (actor IN ('human','agent')),
    -- Ties this audit row to the exact transaction that wrote it -- the trigger
    -- (migration 0034) checks pg_current_xact_id() equality, not a time window.
    -- A time-window check is insufficient: a legitimate row from an unrelated
    -- transaction within the window would otherwise satisfy the check for a
    -- completely different, unaudited UPDATE on the same object.
    xact_id      BIGINT NOT NULL DEFAULT pg_current_xact_id()::text::bigint
);
CREATE INDEX idx_governance_events_object ON governance_events (object_type, object_id, event_at DESC);
CREATE INDEX idx_governance_events_xact ON governance_events (object_type, object_id, to_status, xact_id);

COMMENT ON TABLE governance_events IS
    'Append-only. Every governance_status transition on any governed table '
    'must have a matching row here, written in the SAME transaction as the '
    'UPDATE -- enforced by the theses_governance_audit trigger (migration 0034), '
    'not merely a service-layer convention. See '
    'docs/proposals/governance-first-architecture-2026-06-30.md Section 4.7.';
