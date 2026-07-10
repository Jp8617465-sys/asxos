# arbi eval fixtures

**Status:** current
**Scope:** the concrete test fixtures the promotion gate + reviewers run arbi against
**Owner:** James (governor); graded outside arbi

Each fixture is a scenario with a known-right response, in the shape the scorecard and
rubrics grade against. They are the holdout set `arbi-promotion-gate.md` runs a candidate
prompt/memory/policy against; a candidate must not regress rubric pass-rate on these.
`arbi-evals.md` is the narrative index (golden scenarios G1–G7); these files are the
executable-shaped version, and expand as new failure modes are found.

## Fixture format

```
Given        the repo/live state arbi is handed
Expected     the behaviour a correct arbi produces
Must mention the facts/boundaries that must appear
Must NOT     the outputs that fail the fixture
Gate         the required refusal / approval gate / circuit breaker
```

## Fixtures

| # | Fixture | Guards | Maps to |
|---|---|---|---|
| 001 | `fixture-001-model-a-quarantined.md` | rule #11 / capital boundary | G1 |
| 002 | `fixture-002-open-pr-docs-only.md` | Tier 3 docs-PR discipline | — |
| 003 | `fixture-003-failed-ci.md` | drift recall vs known-gap noise | G2 |
| 004 | `fixture-004-branch-only-handoff.md` | authority ladder (main vs branch) | — |
| 005 | `fixture-005-capital-impacting-request.md` | reserved-to-James / firewall | G5-adjacent |
