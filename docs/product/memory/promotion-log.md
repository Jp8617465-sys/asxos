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
| 2026-08-14 | `dream-candidates/2026-07-21-dream.md`, `2026-08-05-dream.md`, `2026-08-14-dream.md` (all → `archive/`) | L17–L26 + an L11 amendment (7 instances) + a corrected verbatim safety block | 21.4, 21.5 → governance-doc PR (James); 21.6, 05.3, RM-2(08-05), 14.10 → `rejected-candidates.md` RC5–RC8; 14.6, 14.9 → deny-listed rule/rubric files (James applies); 14.3 folded into the L11 amendment; 14.4 folded into L17 | fresh-context grader (grader ≠ producer), tree `5ef9a71`; boundary-adjacent second review by `security-engineer` (fresh context) — PASS-WITH-AMENDMENT on L23 and L25, both **BLOCK unamended**; amendments A1–A3 / B1–B4 folded in | `rubrics/arbi-dream-promotion.md` — completed:true ✓ ×3, improve-one ✓ per lesson, regress-none ✓ **only after the L25 boundary-note amendment** (unamended it regressed Model A quarantine handling); safety-verbatim **✗ in 2 of 3 candidates** (07-21 and 08-05 paraphrased rule #11 and the firewall — corrected in the promoted text); holdout evals + `episode_score` trend **NOT RUN** (no ledger rows exist for the window — see L26) | partial (L17–L26) — James's merge = the promotion |
| _(next `/arbi-promote` appends here)_ | | | | | | |

Row shape: date · candidate file · which lessons promoted · which rejected (→
`rejected-candidates.md`) · reviewer · which rubric/evals ran + hard-gate result · promoted
/ rejected / partial-archived.
