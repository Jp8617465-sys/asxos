-- Migration 0012 — theses, themes, theme_holdings, thesis_revisions
--
-- M-Thesis-1: structured investment thesis layer.
-- Design decisions documented in docs/strategy/M-THESIS-1_IMPLEMENTATION_PLAN_V2.md §3.
--
-- Key choices:
--   BIGSERIAL throughout (not SERIAL)                                  — Item 11c
--   No FK on theses.symbol → universe (watchlist may be unregistered)  — Item 7
--   theme_holdings PK is (theme_id, symbol) not (theme_id, thesis_id)  — Item 8 / spec Part 6.3
--   timeline_days (not horizon_months + expires_at)                    — Item 9 / spec 6.1
--   thesis_text nullable in DB; hard-fail in enter_thesis()            — Item 10
--   Event model in thesis_revisions; diff JSONB + reasoning required   — Items 2, 4
--   Stop/target direction-aware CHECK deferred (v1 long-only deferral) — ESCALATE A
--   NUMERIC(18,6) on all monetary/statistical columns                  — CLAUDE.md non-negotiable #5
-- ─────────────────────────────────────────────────────────────────────────────

BEGIN;

-- ─────────────────────────────────────────────────────────────────────────────
-- themes  (no FK dependencies; create first)
-- Aligned to spec Part 6.2 + D6 (adjacent_codes) + D8 (stage_suggested).
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE themes (
    theme_id         BIGSERIAL    PRIMARY KEY,
    theme_code       TEXT         NOT NULL UNIQUE,
    -- slug identifier: 'ai-infrastructure', 'lithium-oversupply-unwinding'
    name             TEXT         NOT NULL,
    description      TEXT         NOT NULL,
    conviction_band  TEXT         NOT NULL DEFAULT 'medium'
                         CHECK (conviction_band IN ('low', 'medium', 'high')),
    stage            TEXT         NOT NULL DEFAULT 'early'
                         CHECK (stage IN ('early', 'early-institutional',
                                          'broad-institutional', 'mainstream',
                                          'late-retail', 'mature')),
    -- 6-value enum per spec Part 6.2; matches worked-example brief language.
    stage_suggested  TEXT
                         CHECK (stage_suggested IN ('early', 'early-institutional',
                                                    'broad-institutional', 'mainstream',
                                                    'late-retail', 'mature')),
    -- D8: output of M-Theme-Stage-Detection auto-classifier (future milestone).
    -- NULL means classifier has not run yet or theme is too new.
    adjacent_codes   TEXT[]       NOT NULL DEFAULT '{}',
    -- D6: user-maintained list of related theme_codes.
    -- e.g. ['lithium-battery-demand', 'ev-adoption'] for a lithium theme.
    started_at       DATE         NOT NULL DEFAULT CURRENT_DATE,
    retired_at       DATE,
    -- NULL = active theme. Set when theme no longer investable.
    -- No 'retired' status value — retirement is a date, not a state.
    last_reviewed_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
    -- Updated whenever the user runs asx theme review <code>.
);

CREATE INDEX idx_themes_code ON themes (theme_code);
CREATE INDEX idx_themes_active ON themes (started_at) WHERE retired_at IS NULL;


-- ─────────────────────────────────────────────────────────────────────────────
-- theses  (no FK dependency on universe — watchlist may contain unregistered symbols)
-- Aligned to spec Part 6.1 + D2 (watchlist = status='watching') + D3 (status='research').
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE theses (
    thesis_id           BIGSERIAL    PRIMARY KEY,

    symbol              TEXT         NOT NULL,
    -- Validated at service layer: must end with .AU or .US.
    -- Intentionally NOT a FK to universe — watchlist may contain unregistered symbols.

    status              TEXT         NOT NULL DEFAULT 'watching'
                            CHECK (status IN ('research', 'watching', 'active',
                                              'exited', 'expired')),
    -- 'research'  — idea being developed; no entry plan yet
    -- 'watching'  — entry plan set, waiting for conditions
    -- 'active'    — capital deployed (enter_thesis called)
    -- 'exited'    — position closed (exit_thesis called)
    -- 'expired'   — thesis invalidated or timeline lapsed without entry

    thesis_text         TEXT,
    -- NULL is valid for research/watching status (no thesis articulated yet).
    -- enter_thesis() hard-fails (raises ValueError) if thesis_text IS NULL OR ''.
    -- You cannot enter capital on an unarticulated thesis.

    entry_band_lower    NUMERIC(18,6),
    entry_band_upper    NUMERIC(18,6),
    CONSTRAINT theses_entry_band_order
        CHECK (entry_band_lower IS NULL OR entry_band_upper IS NULL
               OR entry_band_lower <= entry_band_upper),
    -- Both NULL for research status (no price plan yet).

    stop_price          NUMERIC(18,6),
    target_price        NUMERIC(18,6),
    -- Nullable for research/watching; enter_thesis() hard-fails if either is NULL.
    -- Direction-aware sanity CHECK (stop < entry, target > entry) deferred:
    -- requires explicit direction column. Add when v1 long-only assumption is formalised.

    timeline_days       INTEGER,
    -- Days from opened_at to expected exit. CLI --timeline 18m → 540.
    -- Compute day-N-of-M: (CURRENT_DATE - opened_at::date) / timeline_days
    -- Compute deadline:   opened_at::date + timeline_days
    -- NULL for research status.

    invalidation_conditions JSONB   NOT NULL DEFAULT '[]'::jsonb,
    -- Array of: {"condition": TEXT, "status": "active"|"triggered"|"resolved", "note": TEXT|null}
    -- Status is manual in v1; M-Thesis-Revisit-Engine automates triggers in a future milestone.

    themes              TEXT[]       NOT NULL DEFAULT '{}',
    -- Denormalised fast-lookup: theme_codes attached to this thesis.
    -- Kept in sync with theme_holdings at write time by service layer.
    -- Do not update this column directly — use ThesisService.attach_theme().

    actual_entry_price  NUMERIC(18,6),
    actual_entry_at     TIMESTAMPTZ,
    actual_exit_price   NUMERIC(18,6),
    actual_exit_at      TIMESTAMPTZ,

    last_revisited_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    -- Updated on every write: open_thesis, enter_thesis, revise_thesis,
    -- exit_thesis, review_thesis (reviewed_no_change).
    -- The morning brief uses this to surface overdue theses.
    revisit_due_at      TIMESTAMPTZ  NOT NULL DEFAULT (NOW() + INTERVAL '30 days'),
    -- Reset to NOW() + 30 days on every revisit action.
    -- M-Thesis-Revisit-Engine makes this dynamic based on distance-to-entry (Part 8.3).

    opened_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    closed_at           TIMESTAMPTZ
    -- Set when status transitions to 'exited' or 'expired'.
);

CREATE INDEX idx_theses_status_revisit
    ON theses (status, revisit_due_at)
    WHERE status IN ('watching', 'active');
-- Supports: morning-brief query "open theses ordered by revisit urgency"

CREATE INDEX idx_theses_symbol ON theses (symbol, opened_at DESC);
-- Supports: asx thesis show <symbol> (most-recent-first)


-- ─────────────────────────────────────────────────────────────────────────────
-- thesis_revisions  (append-only event log; every discipline event recorded here)
-- Aligned to spec Part 6.4 + Item 2 (reviewed_no_change) + Item 4 (diff + reasoning).
--
-- Serialisation contract (Item 4):
--   diff format: {"field": {"old": "serialised_value", "new": "serialised_value"}}
--   Decimal values: str(Decimal_value) — e.g. Decimal("55.123456") → "55.123456"
--   Parse back with Decimal(str_value). Never float(). Document in service.py.
--   Empty dict ({}) for reviewed_no_change — no fields changed, only reasoning recorded.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE thesis_revisions (
    revision_id     BIGSERIAL    PRIMARY KEY,
    thesis_id       BIGINT       NOT NULL REFERENCES theses(thesis_id) ON DELETE CASCADE,
    revised_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    revision_type   TEXT         NOT NULL
                        CHECK (revision_type IN (
                            'opened',             -- first record; created by open_thesis()
                            'assumption_change',  -- thesis_text or invalidation conditions revised
                            'target_adjusted',    -- target_price changed
                            'stop_adjusted',      -- stop_price changed
                            'timeline_extended',  -- timeline_days changed
                            'reviewed_no_change', -- deliberate hold; discipline event
                            'status_change',      -- generic status transition (research→watching etc)
                            'entered',            -- watching→active; capital deployed
                            'exited',             -- exited at will (not stop/target triggered)
                            'exited_by_stop',     -- stop triggered
                            'exited_by_target',   -- target hit
                            'expired'             -- thesis invalidated or timeline lapsed
                        )),
    diff            JSONB        NOT NULL DEFAULT '{}'::jsonb,
    -- See serialisation contract above.
    -- reviewed_no_change always has diff = {} (empty object).
    reasoning       TEXT         NOT NULL,
    -- Required for every revision. Cannot be empty string.
    -- For 'opened': initial conviction summary or "Initial thesis".
    -- For 'reviewed_no_change': must state why still holding. This is the discipline.

    CONSTRAINT thesis_revisions_no_empty_reasoning
        CHECK (reasoning <> '')
);

CREATE INDEX idx_thesis_revisions_thesis
    ON thesis_revisions (thesis_id, revised_at DESC);
-- Supports: asx thesis history <id>


-- ─────────────────────────────────────────────────────────────────────────────
-- theme_holdings  (symbol-level theme membership — spec Part 6.3)
-- PK is (theme_id, symbol): exposure is a property of the stock, not a thesis.
-- One row per stock-theme pair. Persists across theses (thesis lifecycle).
-- Cross-thesis exposure query: WHERE symbol IN (SELECT symbol FROM theses WHERE status='active')
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE theme_holdings (
    theme_id          BIGINT    NOT NULL REFERENCES themes(theme_id) ON DELETE CASCADE,
    symbol            TEXT      NOT NULL,
    -- No FK to universe — watchlist names may not be in universe.
    exposure_strength NUMERIC(8,6) NOT NULL
                          CHECK (exposure_strength >= 0 AND exposure_strength <= 1),
    -- Fraction in [0,1]. 0.65 = "65% of thesis attributed to this theme".
    direction         TEXT      NOT NULL DEFAULT 'positive'
                          CHECK (direction IN ('positive', 'negative')),
    mechanism_text    TEXT      NOT NULL DEFAULT '',
    -- Free-text explanation: "CBA benefits from higher rates on NIM".
    source            TEXT      NOT NULL DEFAULT 'user'
                          CHECK (source IN ('user', 'llm_inferred', 'system_default')),
    -- 'user': manually set via CLI
    -- 'llm_inferred': M-LLM-Thesis-Structuring output (future milestone)
    -- 'system_default': placeholder when attach_theme called without strength
    last_validated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    note              TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (theme_id, symbol)
);

CREATE INDEX idx_theme_holdings_symbol ON theme_holdings (symbol);
-- Supports: asx theme show <code> → list all symbols with exposure

COMMIT;
