# arbi rejected candidates — the anti-memory

**Status:** current · read-only during runs · CODEOWNERS-gated on `main`
**Scope:** conclusions arbi tried and **rejected** — so it never circles back to them
**Owner:** promoted-to-rejected via review; never written by an unattended run

The most underrated memory layer: **what NOT to relearn.** A lesson that was proposed and
found wrong lives here with the reason, so a future dream/wake doesn't resurrect it. Ranked
as high-value anti-memory (a rejected conclusion outranks a fresh dream re-proposing it).

---

| # | Rejected conclusion | Why rejected | Date · source |
|---|---|---|---|
| RC1 | "Model A blocks the whole product." | Too broad. Scan `wf_f54323f5-d7d` proved the tax/thesis/discipline/theme/governance layers are authoritative independent of Model A; the quarantine gates only the allocator path + opportunity-cost. (→ lesson L1) | 2026-07-10 · `north-star.md` |
| RC2 | "Managed Agents is required before useful autonomy." | Repo-native git + GitHub branch-protection/PRs/CI + Routines + the guard hook carry v1; Managed Agents is an optional hosted backend. (→ lesson L2) | 2026-07-10 · `arbi-autonomy-loop.md` |
| RC3 | "Revoking `approved_for_allocation` is safe to enforce the quarantine (before the brief is decoupled)." | R9 showed it would hard-fail the whole brief and hide every Model-A-independent thesis card. Fixed by R9 (`required=False` for display paths). | 2026-07-10 · `risk-register.md` R9 |
| RC4 | "Local ruff is fine to gate on." | Local ruff (0.15.8) ≠ CI (0.7.0) → false diffs + a missed F401. Must pin to CI's version. (→ lesson L3) | 2026-07-10 · R9 CI |
| RC5 | "A misdiagnosed resource-limit error is a recurring failure mode worth a lesson." | One occurrence (2026-07-18, a session limit misread as a monthly spend limit), no recurrence in 3½ weeks, and already captured at ladder 5 in `decision-log.md`. Incidental, not durable. | 2026-08-14 · `dream-candidates/2026-07-21-dream.md` L-cand-21.6 |
| RC6 | "Low-volume pipelines fail silently; high-volume ones announce themselves." | Mechanism plausible; **evidence wrong.** `rs_factor_scores` (11 symbols, 0.000) was a *high-volume upstream* job failing loudly — `derive_fundamentals_pit` timeouts, fixed by PR #85 → 3,308 symbols (`roadmap-state.md:163`) — and the producer was then retired (`weekly-research.yml:16-18`). The AU 10y is a **monthly** FRED series (`IRLTLT01AUM156N`); "frozen 14 sessions" is expected. Re-propose only with evidence that survives L17. | 2026-08-14 · `dream-candidates/2026-08-05-dream.md` L-cand-05.3 |
| RC7 | "Use the durable `create_trigger` Routine rather than session-only `CronCreate` for scheduled work." | Superseded for anything job-shaped: `scheduler-inventory-2026-08-13.md:9-11,56-62` makes five scheduled GitHub Actions workflows the authoritative substrate; neither tool appears in it. Survives only as a narrow Claude-Code-Routines fact. | 2026-08-14 · `dream-candidates/2026-08-05-dream.md` RM-2 |
| RC8 | "Governor ruled 2026-08-14 that tasks #14/#15/#16 decouple from #13." | Not rejected as false — rejected as **unpromotable**. A level-7 dream is the only trace of a level-0 statement; promoting it would launder a session utterance into level-6 authority, which is exactly what `arbi-memory-policy.md`'s poisoning firewall exists to prevent. `#16` has no repository definition at all. James confirms it and it lands in `roadmap-state.md`'s alias table (level 5). | 2026-08-14 · `dream-candidates/2026-08-14-dream.md` L-cand-14.10 |

Add a row whenever a candidate is rejected in promotion, or a prior belief is disproven.
Never delete — a rejected idea removed is an idea free to return.
