-- 0062_mandate.sql
-- The mandate layer (James's ruling, 2026-09-19): "the financial agents should
-- decide capital and structure from my income goals and future ambitions."
--
-- Two tables. `financial_goals` is what James states — investable assets,
-- income, savings, target wealth, horizon, drawdown tolerance, near-term
-- liquidity calls, account type, marginal rate, brokerage. `mandates` is what
-- a versioned, pure derivation (asxos/domain/mandate/derive.py) computes from
-- one goals row — deployable capital, cash floor, minimum position, feasible
-- name count, per-name cap, stop band, risk per position, ETF-core share and
-- sleeve allocations — plus the memo James ratifies. A ratified mandate is the
-- capital/risk calibration ADR D1 §1.1 records as "set without (a) drawdown
-- tolerance or (b) liquidity calls being supplied", and the P5-01 ruling
-- (james-inbox H-32, parked since 2026-09-06) that every Stage 4 packet has
-- been closing `abstain` on. It resolves that ruling by derivation plus one
-- ratification, not by eight hand-ruled numbers.
--
-- WHY TABLES, NOT A DOCUMENT. decision_engine/sizer.py, build_decision_packets
-- and the sleeve job read the mandate nightly; a row is content-addressed and
-- its ratification is a governance_events fact a BEFORE UPDATE trigger can
-- check. A document has to be parsed and cannot be the thing a trigger sees.
--
-- PERSONAL DATA. Income and net worth are behind ASXOS_PERSONAL_USE (AGENTS.md
-- §2) and are revoked from the agent read-only role (0039): the discovery and
-- analysis agents read the derived mandate's caps through the sizer, never the
-- goals themselves.
--
-- APPEND-ONLY. financial_goals refuses every UPDATE and DELETE (0053 pattern).
-- mandates refuses DELETE and refuses any UPDATE that changes a column other
-- than governance_status — the one column the 0034-pattern audit trigger below
-- governs, so an approval is a governance_events fact and nothing else about a
-- mandate can drift after it was derived.
--
-- Expand-only. Numbered after 0060 (ledger head 20260917114415). 0042 stays
-- reserved; 0045 stays unapplied.

BEGIN;

-- ---------------------------------------------------------------------------
-- financial_goals — what James states. One row per statement; never edited.
-- ---------------------------------------------------------------------------
CREATE TABLE financial_goals (
    goal_version_id         BIGSERIAL     PRIMARY KEY,
    as_of                   DATE          NOT NULL,
    investable_assets_aud   NUMERIC(18,6) NOT NULL CHECK (investable_assets_aud >= 0),
    income_aud_pa           NUMERIC(18,6) NOT NULL CHECK (income_aud_pa >= 0),
    savings_aud_pa          NUMERIC(18,6) NOT NULL CHECK (savings_aud_pa >= 0),
    target_wealth_aud       NUMERIC(18,6) NOT NULL CHECK (target_wealth_aud > 0),
    horizon_years           INTEGER       NOT NULL CHECK (horizon_years BETWEEN 1 AND 50),
    drawdown_tolerance_pct  NUMERIC(18,6) NOT NULL CHECK (drawdown_tolerance_pct > 0 AND drawdown_tolerance_pct <= 100),
    liquidity_needs         JSONB         NOT NULL DEFAULT '[]'::jsonb,   -- [{"due": "YYYY-MM-DD", "amount_aud": "0.000000", "label": "..."}]
    emergency_months        INTEGER       NOT NULL CHECK (emergency_months BETWEEN 0 AND 24),
    account_type            TEXT          NOT NULL CHECK (account_type IN ('individual','smsf')),
    marginal_rate_pct       NUMERIC(18,6) NOT NULL CHECK (marginal_rate_pct >= 0 AND marginal_rate_pct <= 60),
    brokerage_aud_per_side  NUMERIC(18,6) NOT NULL CHECK (brokerage_aud_per_side >= 0),
    stated_by               TEXT          NOT NULL DEFAULT 'james' CHECK (stated_by = 'james'),
    content_hash            TEXT          NOT NULL UNIQUE CHECK (content_hash ~ '^[0-9a-f]{64}$'),
    payload                 JSONB         NOT NULL,   -- the full Goals contract, the source of truth for re-derivation
    created_at              TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_financial_goals_asof ON financial_goals (as_of DESC, goal_version_id DESC);

CREATE OR REPLACE FUNCTION _financial_goals_forbid_mutation() RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION
        'financial_goals is append-only: % on goal_version_id=% is refused — state a new goals row',
        TG_OP, OLD.goal_version_id;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER financial_goals_forbid_mutation
    BEFORE UPDATE OR DELETE ON financial_goals
    FOR EACH ROW EXECUTE FUNCTION _financial_goals_forbid_mutation();

-- ---------------------------------------------------------------------------
-- mandates — what the derivation computed from one goals row, and its
-- governance state. governance_status is the only mutable column.
-- ---------------------------------------------------------------------------
CREATE TABLE mandates (
    mandate_id          BIGSERIAL     PRIMARY KEY,
    goal_version_id     BIGINT        NOT NULL REFERENCES financial_goals (goal_version_id),
    as_of               DATE          NOT NULL,
    derivation_version  TEXT          NOT NULL CHECK (derivation_version <> ''),
    goals_content_hash  TEXT          NOT NULL CHECK (goals_content_hash ~ '^[0-9a-f]{64}$'),
    content_hash        TEXT          NOT NULL UNIQUE CHECK (content_hash ~ '^[0-9a-f]{64}$'),
    outputs             JSONB         NOT NULL,   -- the Mandate contract's outputs, every figure with traced_to
    memo_html           TEXT          NOT NULL CHECK (memo_html <> ''),
    -- No DEFAULT, deliberately: 0059 records what a column DEFAULT on
    -- governance_status did to theses (eleven unreviewed rows laundered
    -- into 'approved'). The writer states the initial status explicitly.
    governance_status   TEXT          NOT NULL CHECK (governance_status IN ('pending_review','approved','rejected','retired')),
    created_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_mandates_status_asof ON mandates (governance_status, as_of DESC);

-- Only governance_status may change, and only via the audited path below.
CREATE OR REPLACE FUNCTION _mandates_forbid_mutation() RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'mandates is append-only: DELETE on mandate_id=% is refused', OLD.mandate_id;
    END IF;
    IF (to_jsonb(NEW) - 'governance_status') <> (to_jsonb(OLD) - 'governance_status') THEN
        RAISE EXCEPTION
            'mandates is append-only except governance_status: UPDATE on mandate_id=% changes a derived column — derive a new mandate instead',
            OLD.mandate_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER mandates_forbid_mutation
    BEFORE UPDATE OR DELETE ON mandates
    FOR EACH ROW EXECUTE FUNCTION _mandates_forbid_mutation();

-- ---------------------------------------------------------------------------
-- Governance audit. Widen governance_events.object_type to admit 'mandate'
-- (0033 landed the CHECK inline; Postgres named it
-- governance_events_object_type_check), then the same per-table BEFORE UPDATE
-- audit trigger 0034 built for theses — its own function, not a shared one
-- with TG_ARGV dispatch (0036's header records why the shared form fails).
-- ---------------------------------------------------------------------------
ALTER TABLE governance_events
    DROP CONSTRAINT IF EXISTS governance_events_object_type_check;
ALTER TABLE governance_events
    ADD CONSTRAINT governance_events_object_type_check
    CHECK (object_type IN ('thesis','macro_thesis','theme','theme_holding','mandate'));

CREATE OR REPLACE FUNCTION _check_mandates_governance_audit() RETURNS TRIGGER AS $$
BEGIN
    IF NEW.governance_status = OLD.governance_status THEN
        RETURN NEW;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM governance_events
        WHERE object_type = 'mandate'
          AND object_id = NEW.mandate_id
          AND from_status = OLD.governance_status
          AND to_status = NEW.governance_status
          AND xact_id = pg_current_xact_id()::text::bigint
    ) THEN
        RAISE EXCEPTION 'governance_status transition from % to % on mandate % '
            'requires a matching governance_events row (same from_status, '
            'to_status) written in the SAME transaction (xact %) -- '
            'use asxos/domain/mandate/repository.py approve_mandate()/reject_mandate(), '
            'not a direct UPDATE.',
            OLD.governance_status, NEW.governance_status, NEW.mandate_id, pg_current_xact_id();
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER mandates_governance_audit
    BEFORE UPDATE OF governance_status ON mandates
    FOR EACH ROW EXECUTE FUNCTION _check_mandates_governance_audit();

-- ---------------------------------------------------------------------------
-- Personal data: not readable by the agent read-only role (0039).
-- The derived caps reach agents through the sizer; the goals do not.
-- ---------------------------------------------------------------------------
REVOKE ALL ON financial_goals FROM asxos_agent_ro;
REVOKE ALL ON mandates FROM asxos_agent_ro;

COMMENT ON TABLE financial_goals IS
    'James''s stated goals (0062). Append-only; personal data behind ASXOS_PERSONAL_USE; revoked from asxos_agent_ro.';
COMMENT ON TABLE mandates IS
    'Derived mandate per goals row (0062). governance_status is the only mutable column and is audited by governance_events (object_type=''mandate'').';

COMMIT;
