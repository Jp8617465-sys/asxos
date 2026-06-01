-- Migration 0017: theme stage metadata (M-Theme-Stage-Detection)
--
-- Adds stage_metadata JSONB to themes. Stores the classifier output each time
-- detect_theme_stages runs: classifier_version, conditions_fired, evaluated_at.
-- User-confirmed field (themes.stage) is NEVER written by the job.
-- Only themes.stage_suggested and themes.stage_metadata are auto-updated.

ALTER TABLE themes
    ADD COLUMN stage_metadata JSONB;
