# arbi authority memory (pointer index — ladder level 2)

**Status:** current · read-only during runs · CODEOWNERS-gated on `main`
**This file holds NO original content.** It points at the real authority so there is exactly
one source of truth (duplicating it here would create a second editable copy — a poisoning
surface, and a violation of `docs/README.md`'s "trust the authoritative source" rule).

arbi reads this at wake level 2, then follows the pointers — **the real files win over this
index.**

## The authority (follow these; do not restate them)

- **Non-negotiables + rule #11 (Model A quarantine):** `../../../CLAUDE.md` (## Non-negotiable rules)
- **arbi's authority + limits:** `../arbi-constitution.md`
- **Source-of-truth ladder (how conflicts resolve):** `../arbi-authority.md`
- **Permission tiers (Infrastructure I0–I6 + Portfolio P0–P6) + circuit breakers:** `../arbi-permission-model.md`
- **Portfolio decision-support charter + capital mandate:** `../portfolio-manager-charter.md` + `../portfolio-policy.md`
- **Hard gates + scorecard:** `../arbi-scorecard.md`
- **Promotion gate (candidate → approved):** `../arbi-promotion-gate.md`
- **The Output / non-negotiable firewall:** `../north-star.md`
- **Personal-advice firewall + portfolio invariants:** `../../../.claude/rules/portfolio-conventions.md`

If a lesson in `approved-lessons.md` (level 6) ever conflicts with any file above, the file
above wins; flag the lesson stale and draft its correction for review.
