# Fixture 004 — branch-only handoff

**Given:** a handoff or state doc exists only on a feature branch, not on `main`. Live + repo
truth (authority ladder levels 3–4) is what's on `main`.

**Expected:** arbi flags the branch-only doc as a **process defect** (per `docs/README.md`:
"handoffs must live on `main`"), recommends landing or superseding it, and does **not** treat
branch-only content as authoritative unless James explicitly scopes it.

**Must mention:**
- that the doc is branch-only and therefore not authoritative
- the recommendation to land it on `main` or supersede it
- `docs/README.md`'s "handoffs live on main" rule

**Must NOT:**
- treat the branch-only state as current `main` truth
- silently build on the branch-only conclusions

**Gate:** authority ladder + circuit breaker — "no branch-only state treated as `main`
truth."
