"""Macro-thesis domain — Phase 2a/2b of the governance-first architecture.

Own package, not folded into asxos/domain/themes/: a macro thesis has an
independent lifecycle driven by its own agent (macro-economist) — it can
exist, be approved, and be retired with zero themes ever linked to it
(themes.macro_thesis_id is ON DELETE SET NULL, optional from the theme's
side). See docs/proposals/governance-first-architecture-2026-06-30.md
Section 5.5 and the Phase 2a plan's module-boundary decision.
"""
