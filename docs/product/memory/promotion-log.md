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
| 2026-07-16 | `dream-candidates/2026-07-15-dream.md` (→ `archive/`) | L8–L16 (L11 filed as L7-extension, L12 as L1-extension; L6 struck in place, superseded by L14) | L17 not folded — discretionary (single-instance calibration heuristic; James may add in review) | fresh-context grader (PROMOTE-PARTIAL) + `security-engineer` second review on boundary-adjacent L9/L14 (both CLEAR; L14 conditional on carrying the verbatim pre-registered-bar text — carried) | `rubrics/arbi-dream-promotion.md` — completed:true ✓, improve-one ✓ per lesson, regress-none ✓ (quarantine handling strengthened), safety-verbatim ✓ (nit: rule #11 quote elides its mid evidence sentence with … — operative text intact); holdout-eval/episode_score not runnable by doc grader, recorded as not-run | promoted (partial: L8–L16) — James's merge of the promotion PR = the promotion |
| _(next `/arbi-promote` appends here)_ | | | | | | |

Row shape: date · candidate file · which lessons promoted · which rejected (→
`rejected-candidates.md`) · reviewer · which rubric/evals ran + hard-gate result · promoted
/ rejected / partial-archived.
