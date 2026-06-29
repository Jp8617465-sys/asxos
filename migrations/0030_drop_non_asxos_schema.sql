-- 0030_drop_non_asxos_schema.sql
-- =====================================================================
-- Single-tenant cleanup. asxos owns 42 tables (per migrations/) + 3 views
-- (current_holdings, market_context_current, stock_universe). The Supabase
-- project also held 122 NON-asxos public tables: ~50 dead artifacts from the
-- PREVIOUS asxos repo + ~70 tables of a near-empty foreign personal-finance app
-- (see docs/db-shared-project-audit-2026-06-28.md). None are referenced by
-- current asxos code; verified asxos has ZERO foreign keys into any of them.
--
-- BACKUP (in-database, survives this wipe): the 14 data-bearing tables are
-- copied via CTAS into schema `archive_dropped_20260628` BEFORE the drop. Data
-- is therefore recoverable from that schema at any time; drop the schema later
-- to reclaim the space once you're confident. (CTAS copies data only — not
-- constraints/indexes — which is sufficient for a dead-data archive.)
-- =====================================================================

CREATE SCHEMA IF NOT EXISTS archive_dropped_20260628;

-- Archive the 14 tables that hold rows (10 prev-repo legacy + 4 foreign).
CREATE TABLE archive_dropped_20260628.sector_macro_correlations AS SELECT * FROM public.sector_macro_correlations;
CREATE TABLE archive_dropped_20260628.signal_evidence_chains     AS SELECT * FROM public.signal_evidence_chains;
CREATE TABLE archive_dropped_20260628.universe_history_research   AS SELECT * FROM public.universe_history_research;
CREATE TABLE archive_dropped_20260628.universe_history           AS SELECT * FROM public.universe_history;
CREATE TABLE archive_dropped_20260628.user_preferences          AS SELECT * FROM public.user_preferences;
CREATE TABLE archive_dropped_20260628.job_completions           AS SELECT * FROM public.job_completions;
CREATE TABLE archive_dropped_20260628.semantic_memories         AS SELECT * FROM public.semantic_memories;
CREATE TABLE archive_dropped_20260628.state_property_tax_rates  AS SELECT * FROM public.state_property_tax_rates;
CREATE TABLE archive_dropped_20260628.user_portfolios          AS SELECT * FROM public.user_portfolios;
CREATE TABLE archive_dropped_20260628.model_metadata           AS SELECT * FROM public.model_metadata;
CREATE TABLE archive_dropped_20260628.signal_transitions       AS SELECT * FROM public.signal_transitions;
CREATE TABLE archive_dropped_20260628.research_runs            AS SELECT * FROM public.research_runs;
CREATE TABLE archive_dropped_20260628.signal_registry         AS SELECT * FROM public.signal_registry;
CREATE TABLE archive_dropped_20260628.data_quality_flags      AS SELECT * FROM public.data_quality_flags;

-- Dead views (over now-dropped model tables; not in asxos migrations).
DROP VIEW IF EXISTS public.v_pending_retraining_jobs;
DROP VIEW IF EXISTS public.v_recent_deployments;

-- Drop all 122 non-asxos tables. CASCADE clears inter-table FKs within the
-- dropped set; asxos has no FK into any of these (verified). Their triggers drop
-- with them; the ~12 orphaned trigger/helper functions are inert and left as an
-- optional follow-up (dropping update_model_versions_timestamp /
-- update_updated_at_column could affect kept asxos triggers, so not touched here).
DROP TABLE IF EXISTS
  public.abs_financial_benchmarks, public.advisor_audit_log, public.advisor_consent_log,
  public.advisor_conversations, public.alert_preferences, public.analyst_ratings,
  public.api_keys, public.assistant_conversations, public.assistant_usage_log,
  public.asx_announcements, public.book_returns, public.budget_goals,
  public.data_quality_flags, public.decision_explanations, public.decision_ledger,
  public.dividend_history, public.dividends_calendar, public.document_extractions,
  public.earnings_calendar, public.earnings_history, public.ensemble_signals,
  public.etf_composition_changes, public.etf_data, public.etf_holdings,
  public.expense_benchmarks, public.expense_insights, public.exposure_snapshots,
  public.features_fundamental, public.features_fundamental_trends, public.financial_profiles,
  public.fundamentals_history, public.goal_gaps, public.goal_milestones,
  public.goal_portfolio_gap, public.goal_snapshots, public.health_scores,
  public.investment_plans, public.job_completions, public.live_prices,
  public.loan_accounts, public.macro_data, public.macro_market_data,
  public.model_a_backtests, public.model_a_drift_audit, public.model_a_features_extended,
  public.model_a_ml_signals, public.model_a_predictions, public.model_a_ranked,
  public.model_a_ranked_nulls_archive, public.model_a_runs, public.model_b_ml_signals,
  public.model_c_signals, public.model_d_signals, public.model_deployment_history,
  public.model_drift_metrics, public.model_feature_importance, public.model_metadata,
  public.model_registry, public.model_retraining_queue, public.model_shap_values,
  public.model_validation_results, public.news_articles, public.nlp_announcements,
  public.notification_delivery_log, public.notification_queue, public.notifications,
  public.outperformance_configs, public.paper_positions, public.phase_2_trigger_events,
  public.plan_performance_snapshots, public.portfolio_attribution, public.portfolio_constraints,
  public.portfolio_performance, public.portfolio_rebalancing_suggestions, public.portfolio_risk_metrics,
  public.property_assets, public.property_reform_events, public.push_subscriptions,
  public.recommendation_outcomes, public.recommendation_quality_scores, public.recommendations,
  public.regulatory_alerts, public.research_runs, public.risk_exposure_snapshot,
  public.runs, public.saved_screener_queries, public.scenario_results,
  public.scenario_templates, public.screen_backtests, public.screen_matches,
  public.sector_macro_correlations, public.semantic_memories, public.sentiment,
  public.short_interest, public.signal_emissions, public.signal_evidence_chains,
  public.signal_registry, public.signal_transitions, public.state_property_tax_rates,
  public.stock_archetypes, public.stock_news, public.subscriptions,
  public.trade_annotations, public.universe_history, public.universe_history_research,
  public.user_accounts, public.user_behavioral_patterns, public.user_context,
  public.user_events, public.user_goals, public.user_holding_lots,
  public.user_holdings, public.user_memories, public.user_portfolios,
  public.user_preferences, public.user_properties, public.user_property_cashflows,
  public.user_saved_screens, public.user_settings, public.user_watchlist,
  public.vehicle_comparison_runs, public.whatif_audit
CASCADE;
