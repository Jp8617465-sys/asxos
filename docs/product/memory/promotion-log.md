# arbi promotion log — candidate → approved audit trail

**Status:** current · append-only · CODEOWNERS-gated on `main`
**Scope:** every candidate→approved (or →rejected) movement, so the gate is auditable
**Owner:** written by `/arbi-promote`'s PR; the reviewer (James) is the merger

The promotion gate's visible record: nothing reaches `approved-lessons.md` except through a
row here, and the **grader is never the run that produced the candidate** (CODEOWNERS
enforces James/a fresh-context reviewer). Makes "grader ≠ producer" auditable.

---

| Date | Candidate | Promoted lessons | Rejected | Reviewer | Evals / gate | Result |
|---|---|---|---|---|---|---|
| 2026-07-10 | (seed) `approved-lessons.md` L1–L7 | L1–L7 (session-authored, human-reviewed) | — | James (this session) | manual review; `arbi-dream-promotion.md` rubric | promoted |
| _(next `/arbi-promote` appends here)_ | | | | | | |

Row shape: date · candidate file · which lessons promoted · which rejected (→
`rejected-candidates.md`) · reviewer · which rubric/evals ran + hard-gate result · promoted
/ rejected / partial-archived.
