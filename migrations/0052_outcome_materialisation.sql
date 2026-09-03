-- 0052_outcome_materialisation.sql
-- =====================================================================
--
-- DRAFT — NOT APPLIED. Apply only under James's I5 grant (Amendment H,
-- 2026-09-02), after the carrying branch's tests are green.
--
-- Stage 5 / ADR Slice 4 — outcome materialisation, plus the two delivery
-- ledgers Wave 6 should not have borrowed.
--
-- 1. `thesis_outcomes` replaces the deleted `jobs/track_signal_outcomes.py`
--    (ADR §6 Slice 4), generalising the `macro_thesis_outcomes` pattern of
--    migration 0041 from macro theses to decision packets. One row per
--    (packet, horizon): the t0 row records what was KNOWN and CLAIMED at the
--    cutoff; each horizon row records what HAPPENED at 21 / 63 / 126 trading
--    sessions (`OUTCOME_WINDOWS_TRADING_DAYS`, decision_engine/types.py).
--
-- 2. `delivery_receipts` and `decision_dispositions` correct a Wave 6
--    shortcut. `DeliveryReceipt` rows were written into `brief_runs` to
--    avoid opening a migration; but `asxos/brief/deltas.py`'s
--    `_PRIOR_BRIEF_SQL` selects the most recent `brief_runs` row with
--    `as_of < $1` and does NOT filter on row kind, so a decision receipt
--    was returned as "the prior brief" and skewed the brief's since-last
--    timestamp. One table whose rows mean two things is the defect; these
--    tables are the fix. `brief_runs` goes back to meaning exactly one
--    thing: a composed morning brief.
--
-- Same shape as 0048/0050/0051: one authoritative `payload JSONB` per row
-- holding the complete `model.model_dump(mode="json")`; every other column
-- is a NON-AUTHORITATIVE shadow copy for indexing only; reconstruction is
-- exclusively `Model.model_validate(payload)`; append-only by trigger.
-- No user_id/auth/RLS (rule #4).
--
-- NOT A RECOMMENDATION, AND NOT AN ALPHA CLAIM. An outcome row records a
-- measurement and its named unavailability states (governor ruling F1: the
-- benchmark comparison is reported `unavailable` while the accumulation
-- index is absent, never proxied). There is no verdict, score, weight,
-- size or promote/retire column: a learning review is a human act on the
-- evidence these rows carry, and one observation is never an alpha claim
-- (`target-architecture.md` §15 Stage 5).
-- =====================================================================

CREATE OR REPLACE FUNCTION _outcome_forbid_mutation()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION
        'append-only: % on % is forbidden -- outcomes, receipts and '
        'dispositions are immutable records of what happened; write a new '
        'row instead',
        TG_OP, TG_TABLE_NAME;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- thesis_outcomes  (ThesisOutcome) — t0 + horizon observations
-- ============================================================
CREATE TABLE thesis_outcomes (
    outcome_id              VARCHAR(200) PRIMARY KEY
                            CHECK (char_length(outcome_id) >= 1),
    content_hash            VARCHAR(64)  NOT NULL UNIQUE
                            CHECK (content_hash ~ '^[0-9a-f]{64}$'),
    decision_packet_id      VARCHAR(200) NOT NULL
                            REFERENCES decision_packets(decision_packet_id),
    symbol                  TEXT         NOT NULL,
    -- 0 = t0 (what was known and claimed); otherwise a ratified horizon.
    horizon_trading_days    INTEGER      NOT NULL
                            CHECK (horizon_trading_days IN (0, 21, 63, 126)),
    -- The session this horizon falls due on, resolved through the packet's
    -- own TradingSessionCalendar -- never weekday arithmetic.
    due_at                  TIMESTAMPTZ  NOT NULL,
    as_of                   DATE         NOT NULL,
    knowledge_cutoff        TIMESTAMPTZ  NOT NULL,
    observation_state       VARCHAR(30)  NOT NULL
                            CHECK (observation_state IN
                                ('recorded', 'observed', 'unobservable')),
    benchmark_state         VARCHAR(40)  NOT NULL,
    created_at              TIMESTAMPTZ  NOT NULL,
    payload                 JSONB        NOT NULL
                            CHECK (jsonb_typeof(payload) = 'object')
                            CHECK (payload->>'outcome_id' = outcome_id)
                            CHECK (payload->>'content_hash' = content_hash),
    -- The scheduled row and its observation are BOTH facts, so the pair is
    -- unique per state rather than per horizon: an observation is appended
    -- beside the row that scheduled it, never written over it (the trigger
    -- below forbids the UPDATE that would).
    UNIQUE (decision_packet_id, horizon_trading_days, observation_state)
);
CREATE INDEX idx_thesis_outcomes_due ON thesis_outcomes (due_at, observation_state);
CREATE INDEX idx_thesis_outcomes_symbol ON thesis_outcomes (symbol, as_of);
CREATE TRIGGER thesis_outcomes_forbid_mutation
    BEFORE UPDATE OR DELETE ON thesis_outcomes
    FOR EACH ROW EXECUTE FUNCTION _outcome_forbid_mutation();
COMMENT ON TABLE thesis_outcomes IS
    'Outcome ledger for governed decision packets (ADR Slice 4, Stage 5). '
    'horizon_trading_days = 0 is the t0 record of what was known and claimed; '
    '21/63/126 are the ratified observation horizons, each resolved through '
    'the packet''s own trading calendar. Append-only; payload authoritative. '
    'Carries measurements and named unavailability states only -- no verdict, '
    'no score, no alpha claim from a single observation.';

-- ============================================================
-- delivery_receipts  (DeliveryReceipt) — what James was actually shown
-- ============================================================
CREATE TABLE delivery_receipts (
    receipt_id              VARCHAR(200) PRIMARY KEY
                            CHECK (char_length(receipt_id) >= 1),
    content_hash            VARCHAR(64)  NOT NULL UNIQUE
                            CHECK (content_hash ~ '^[0-9a-f]{64}$'),
    decision_packet_id      VARCHAR(200) NOT NULL
                            REFERENCES decision_packets(decision_packet_id),
    decision_content_hash   VARCHAR(64)  NOT NULL
                            CHECK (decision_content_hash ~ '^[0-9a-f]{64}$'),
    render_sha256           VARCHAR(64)  NOT NULL
                            CHECK (render_sha256 ~ '^[0-9a-f]{64}$'),
    render_bytes            INTEGER      NOT NULL CHECK (render_bytes > 0),
    channel                 VARCHAR(10)  NOT NULL CHECK (channel IN ('cli', 'email')),
    delivered_at            TIMESTAMPTZ  NOT NULL,
    resend_message_id       TEXT         NULL,
    -- The exact bytes delivered, so `render_sha256` can be re-verified from
    -- the row itself rather than trusted.
    rendered_html           TEXT         NOT NULL CHECK (char_length(rendered_html) > 0),
    payload                 JSONB        NOT NULL
                            CHECK (jsonb_typeof(payload) = 'object')
                            CHECK (payload->>'receipt_id' = receipt_id)
                            CHECK (payload->>'content_hash' = content_hash)
);
CREATE INDEX idx_delivery_receipts_packet ON delivery_receipts (decision_packet_id, delivered_at);
CREATE TRIGGER delivery_receipts_forbid_mutation
    BEFORE UPDATE OR DELETE ON delivery_receipts
    FOR EACH ROW EXECUTE FUNCTION _outcome_forbid_mutation();
COMMENT ON TABLE delivery_receipts IS
    'One row per delivery of a decision packet (CLI or email), carrying the '
    'exact rendered bytes and their sha256 so what James saw is provable. '
    'Replaces the Wave 6 shortcut of writing receipts into brief_runs, which '
    'made a receipt row indistinguishable from a composed brief to '
    'asxos/brief/deltas.py. Append-only.';

-- ============================================================
-- decision_dispositions  (Disposition) — what James decided
-- ============================================================
CREATE TABLE decision_dispositions (
    disposition_id          VARCHAR(200) PRIMARY KEY
                            CHECK (char_length(disposition_id) >= 1),
    content_hash            VARCHAR(64)  NOT NULL UNIQUE
                            CHECK (content_hash ~ '^[0-9a-f]{64}$'),
    decision_packet_id      VARCHAR(200) NOT NULL
                            REFERENCES decision_packets(decision_packet_id),
    decision_content_hash   VARCHAR(64)  NOT NULL
                            CHECK (decision_content_hash ~ '^[0-9a-f]{64}$'),
    verdict                 VARCHAR(20)  NOT NULL
                            CHECK (verdict IN
                                ('accept', 'request_revision', 'reject', 'defer')),
    recorded_at             TIMESTAMPTZ  NOT NULL,
    payload                 JSONB        NOT NULL
                            CHECK (jsonb_typeof(payload) = 'object')
                            CHECK (payload->>'disposition_id' = disposition_id)
                            CHECK (payload->>'content_hash' = content_hash)
);
CREATE INDEX idx_decision_dispositions_packet ON decision_dispositions (decision_packet_id, recorded_at);
CREATE TRIGGER decision_dispositions_forbid_mutation
    BEFORE UPDATE OR DELETE ON decision_dispositions
    FOR EACH ROW EXECUTE FUNCTION _outcome_forbid_mutation();
COMMENT ON TABLE decision_dispositions IS
    'James''s recorded reading of a decision packet, bound to the packet''s '
    'content hash so a disposition cannot silently follow a changed packet. '
    'An accepting disposition on an ACTION state is the only thing that can '
    'produce a PaperIntent; no row here executes anything. Append-only.';
