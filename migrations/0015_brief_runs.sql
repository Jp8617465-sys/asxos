-- M-Brief-Skeleton: persistent brief composition record.
--
-- Append-only per briefing day. brief_id is the canonical PK.
-- The brief reading surface queries on as_of; composed_at disambiguates
-- re-runs (e.g. manual backfills). resend_message_id is populated by
-- compose_brief.py after Resend confirms dispatch.

CREATE TABLE brief_runs (
    brief_id          BIGSERIAL PRIMARY KEY,
    as_of             DATE NOT NULL,
    composed_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    rendered_html     TEXT,
    snapshot_json     JSONB,
    section_runs      JSONB NOT NULL DEFAULT '{}',
    resend_message_id TEXT
);

CREATE INDEX ON brief_runs (as_of, composed_at DESC);
