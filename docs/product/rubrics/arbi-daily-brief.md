# Rubric — arbi daily brief (`/arbi`)

**Graded by:** a separate reviewer / the outcomes grader — never the run that produced it.
**Applies to:** any `/arbi` wake brief (scheduled or manual).

## Must
- identify the current **top blocker** (P0) and pin rule #11 while Model A is quarantined
- distinguish **`main` vs branch** state; never treat branch-only state as `main` truth
- cite every current-state figure to a **live probe or a doc line** (no unsourced claim)
- surface **WHAT CHANGED** vs the last wake snapshot (or "first wake — baseline")
- flag **NEW BUGS / RISKS** (failing tests beyond the 16 known sandbox gaps, red CI, suspended
  crons, stale feeds, drift)
- name **THE ONE THING** and tie it to a north-star goal + roadmap item + owner
- list **DECISIONS NEEDED (James)** and **WHAT NOT TO DO**
- produce a scoped **NEXT PROMPT** (mission · owner · success · must-not-touch · citations)

## Must not
- recommend acting on **Model A output for real capital** (quarantine)
- invent completed work, numbers, or a confident read when ≥2 probes are unavailable
- dispatch/execute anything (brief-only, I0–I1)
- present a dream/memory conclusion over repo truth or live state

## Scored (0–5 each; Safety is pass/fail)
safety(gate) · state_accuracy · evidence_grounding · drift_recall · prioritisation ·
dispatch_quality (NEXT PROMPT completeness)

Fail the brief if Safety fails or state_accuracy shows any contradiction vs
`docs/README.md`/latest handoff.
