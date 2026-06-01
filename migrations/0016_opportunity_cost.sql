-- Migration 0016: opportunity cost scenarios (M-Opportunity-Cost-v1)
--
-- Stores CGT-adjusted opportunity-cost rankings per active thesis.
-- Populated weekly by asxos-compute-opportunity-cost (Sat 20:05 UTC).
-- Read by brief Section 10 (opportunity_cost collector, Phase 4).
--
-- Design: append-only per as_of — brief always reads the most-recent row
-- per (thesis_id, as_of) via the job, which inserts fresh rows each week.
-- No upsert; the job deletes stale as_of rows for the same thesis before
-- inserting to keep the table from growing unbounded.

CREATE TABLE opportunity_cost_scenarios (
    scenario_id          BIGSERIAL PRIMARY KEY,
    thesis_id            BIGINT NOT NULL REFERENCES theses(thesis_id),
    as_of                DATE NOT NULL,
    alternative_symbol   TEXT NOT NULL,
    alternative_source   TEXT NOT NULL,        -- 'watchlist' | 'cash' | 'active_thesis'
    gross_expected_return    NUMERIC(18,6),
    estimated_cgt_friction   NUMERIC(18,6),   -- fraction of position value [0, 1)
    net_expected_return      NUMERIC(18,6),   -- gross minus cgt_friction
    notes                TEXT,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ON opportunity_cost_scenarios (thesis_id, as_of);
CREATE INDEX ON opportunity_cost_scenarios (as_of);
