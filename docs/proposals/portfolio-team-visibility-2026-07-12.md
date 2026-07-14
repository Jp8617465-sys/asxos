# Making the portfolio team visible & proactive — proposal (design, not build)

**Status:** proposed — design/docs only. No code, no cron, no migration, no gate flip, no DB write.
**Scope:** the structural fix behind James's complaint (2026-07-12) — *"we are supposed to have a
portfolio management team that rates stocks and generates theses… the portfolio team should be
flagging this."*
**Trigger:** after PR #27, James asked why the portfolio team didn't automatically flag the
HUBS/CBA issues surfaced in the 2026-07-11 `/pm-review`. Root cause is a **surfacing gap**, not a
compute gap.
**Owner:** arbi synthesized from three specialists (`system-architect`, `backend-architect`,
`portfolio-invariant-guard`, 2026-07-12). Needs James's sign-off on the surface choice (§5) and
the James-gated items (§9) before any build.
**Last verified:** 2026-07-12
**Superseded by:** N/A

---

## 1. Problem statement — what failed, why James experienced "nothing happened"

James's premise ("nothing flags this") is **partly false and partly true**, and the split is the
whole design.

**What already reaches his inbox (so the premise is partly false):** terminal *price* events —
stop breach, target hit, big daily move, earnings-in-5d, invalidation-condition triggered —
already email **every day** via four deterministic crons (`check_au_positions.py`,
`check_us_positions.py`, `check_thesis_invalidations.py`, `check_cron_health.py`). The **HUBS stop
breach actually fired on 2026-07-03** through `check_us_positions.py`.

**What does NOT reach him (the real bug):** the *process / coherence* discipline layer —
revisit-overdue, thesis behind/stalled mid-timeline, conviction-vs-size, benchmark lag vs XJO,
thesis-data sanity. This exists in one of two useless-to-James states:

1. **Computed daily, then discarded at render.** The V2 `active_theses` collector runs inside
   `compose()` **every day** and produces the red/yellow discipline items (including CBA's
   "revisit 14d overdue"), persists them to `brief_runs` — then the emailed brief falls back to
   the **V1** template (which has *no* discipline section) because `ASXOS_V2_BRIEF_ENABLED` is
   unset (and absent from `render.yaml` entirely). James's daily email literally has the CBA flag
   computed and dropped on the floor.
2. **Generated only on manual `/pm-review`, written to markdown no one reads.** The richer
   dimensions (trajectory, conviction coherence, benchmark, data integrity) come from the 5 LLM
   analysis agents. Their 2026-07-11 findings landed in `risk-register.md`, `cleanup-backlog.md`,
   and `portfolio-outcome-ledger.md` — **there is no path from a markdown doc to James's inbox.**

So James experienced "nothing happened" because the meaningful discipline data was either computed
and thrown away, or recorded where he never looks. His follow-up — *"it lands in my inbox but it
doesn't have any meaningful data"* — is exactly right: the brief arrives, but the meaning is
filtered out before render.

## 2. Evidence — the findings already existed

| Finding | Where it was recorded (never surfaced to James) |
|---|---|
| HUBS `cost_base_normal` currency misread → false −29% | `risk-register.md` R10 |
| `conviction_level` NULL on all 13 theses → coherence check can't run | `risk-register.md` R11 |
| CBA thesis ladder 42/45/38/60 vs live ~168 (~4× detached) | `cleanup-backlog.md` RC2; `portfolio-outcome-ledger.md` rec-2026-07-11-CBA |
| market_context feed gaps (RBA/VIX null) | `cleanup-backlog.md` RC3 (**now fixed + live** 2026-07-12) |
| CBA revisit 14 days overdue (due 2026-06-27) | computed **daily** by `active_theses.py`, dropped at `composer.py:89-98` |

## 3. Root cause — four distinct things (do not conflate)

1. **Manual-only `/pm-review`.** The 5 analysis agents are LLM subagents fanned out from the main
   loop (a subagent can't spawn subagents — that's *why* `/pm-review` is a command). They cannot
   run from a plain cron. Nothing schedules a main-loop session to run them.
2. **The daily discipline cards are computed but not rendered into the emailed brief.** Blocked by
   `ASXOS_V2_BRIEF_ENABLED` (unset, absent from `render.yaml`) — and that flag is *all-or-nothing*:
   flipping it would ship the entire V2 tree including the stale, Model-A-framed sections, so it is
   **not** the reversible path (`dark-launch-exit-plan.md` KEEP-DARK verdict on the V2 tree).
3. **The LLM agents' qualitative findings have no persistence and no surfacing path at all.** They
   exist only in a run transcript. A deterministic digest does **not** solve this — it's a distinct
   net-new problem (a findings sink).
4. **Some items are James-only inputs, not system bugs.** CBA's correct levels and HUBS's
   conviction are value judgements only James can make (`james-inbox.md`). A perfect system still
   couldn't self-answer them — but it *should* have kept surfacing them until he did. It didn't,
   because of causes 1–2.

**Correction to an earlier arbi claim (caught by `backend-architect`):** I told James the
"4-week paper-trade sign-off (M13.8)" was "unscoped / never started." **That was wrong.** It *is*
operationally defined in code: `asxos/domain/portfolio/paper_trade.py:294` `has_enough_paper_weeks()`
(4-week maturation of `rebalance_runs` **AND** build-cron continuity), `record_signoff()` at `:351`,
CLI `asx portfolio signoff`. It gates the **allocator's** rebalance-trade section only — and is
irrelevant to a discipline digest (§4, option C).

## 4. Options

**The load-bearing fact:** ~80–90% of what the "team flags" is deterministic math that already
exists in `severity.py` (revisit-overdue, timeline-expiry, concentration) + `trajectory.py`
(`classify_trajectory`: STOP_VIOLATED/ABOVE_TARGET/STALLED/BEHIND/ON_TRACK) + `wealth_state.py`
(benchmark lag). The LLM layer adds only ~10–20%: cross-agent *reconciliation* (what caught the
R10 misread), narrative judgement (e.g. "XJO is the wrong benchmark for a single USD name"), and
coherence-against-news. So deterministic-on-cron and the-LLM-team are **not either/or** on
coverage — the deterministic layer does the bulk; the LLM layer is a thin, later, gated cap.

| Option | What | Coverage | Verdict |
|---|---|---|---|
| **A. Deterministic discipline evaluator + surface it** | Pure functions (reuse `severity`/`trajectory`/`wealth_state` + net-new conviction-NULL + data-sanity), surfaced model-independently | ~80–90% | **Core recommendation** |
| **B. Surface already-recorded findings** | Digest that reads open risk-register/ledger items | Only *past* findings; they live in **markdown**, not the DB — fragile to parse | **Reject as the fix; fold its intent into the persistence sink (PR3)** |
| **C. Enable/re-scope the allocator brief section** | Flip `ASXOS_PORTFOLIO_BRIEF_ENABLED` / define sign-off | The allocator's *trade suggestions* — **not** the discipline gap | **Decouple — capital-adjacent, James-only, orthogonal (see below)** |
| **(later) LLM `/pm-review` Routine** | Scheduled main-loop session runs the 5 agents | +the reconciliation/narrative 10–20% | **Gated tier** — needs branch protection + read-only DB role + track record + James's enable |

**Two sub-choices for surfacing option A (this is the real decision for James, §5):**
- **A-cron:** a standalone `check_thesis_discipline` cron mirroring `check_au_positions.py` —
  isolated, cannot break the brief, reversible by deleting one `render.yaml` block. **Cost:** a 5th
  daily alert email (James already gets up to 4 + the brief).
- **A-brief:** a new **model-independent discipline section in the V1 brief James already reads** —
  consolidates into the one email, **needs no gate flip** (only the already-set
  `ASXOS_PERSONAL_USE`), reuses the same `severity`/`active_theses` logic. **Cost:** net-new V1
  render wiring (a `BriefData` field + a `brief.html.j2` block), larger blast radius on the brief
  path (mitigated by a fail-closed section — §7).

**Gate-scope question, settled by two agents independently:** `ASXOS_PORTFOLIO_BRIEF_ENABLED` is
read in exactly one place (`compose.py:504`) and gates **only V1 section 6 = the allocator's
rebalance-trade list**. A model-independent discipline digest is **orthogonal** — the existing
stop/target/invalidation crons already email that *same class* of evidence in production today with
that flag `=0`. So **the fix does not require James to flip any gate.** Entangling the digest with
the allocator flag would be a category error (it would withhold his own discipline facts pending an
*allocator* paper-trade validation that has nothing to do with them).

## 5. Recommendation — least-risk next step

**Build the deterministic discipline evaluator (option A), and surface it via A-brief — a
model-independent discipline section in the brief James already reads.**

Why A-brief over A-cron: James's literal complaint is *"it lands in my inbox but doesn't have any
meaningful data."* He isn't asking for a 5th email — he's asking for the brief he already gets to
be meaningful. A-brief answers that directly, needs no gate flip, and reuses existing logic.
A-cron stays the named fallback if, in review, touching the brief render path feels riskier than a
separate isolated email — that's a reversible preference, not a blocker.

This is deliberately the **flagging** half only. See §10 on why "rate stocks / generate theses" is
a separate, larger, partly-deliberately-shelved track — I'm not going to let this proposal imply
it delivers automated selection, because it doesn't.

## 6. Acceptance criteria (the recommended increment)

- CBA thesis (revisit due 2026-06-27; live ~168 vs target 60) → the section emits **both** a
  `REVISIT OVERDUE` line **and** a `DATA-SANITY` line (live > 2× target ⇒ broken data, not a hit).
- 13/13 theses `conviction_level` NULL → one summary line: *"conviction unset on 13/13 theses —
  size-vs-conviction check disabled (R11)."*
- **Zero clean findings → no discipline lines** (quiet-by-default, matching `check_au_positions`).
- **A check that ERRORS is loud, not silent** — emits a `⚠ <check> could not run: <reason>` line
  **and** fails the `JobMonitor`/section so the job-failure banner catches it. ("No finding" is
  silent; "couldn't compute" is a finding — this is the exact failure mode that caused the
  complaint, so it must not recur inside the fix.)
- **Model-independent by construction:** zero reads of `signals`/`shap_factors`/`prob_up`/
  `expected_return`/`signals.regime`; never calls `resolve_production_model()`; never invokes
  `thesis-coherence-guard`.
- **FX-correct:** any foreign-holding return/stop line FX-converts *both* legs (`prices/fx.py`) per
  R10 — structurally avoids the currency misread that bit the LLM agents.
- **Stale-price caveat** attached rather than presenting possibly-stale facts as current.
- **Gated on `ASXOS_PERSONAL_USE=1`** (not `ASXOS_PORTFOLIO_BRIEF_ENABLED`).
- **Evidence-only wording** (§7 rules); Decimal-only, no numpy.

## 7. What must NOT be touched (boundaries — from `portfolio-invariant-guard`)

- **Rule #11 / Model A quarantine.** No `signals`/SHAP reads; never call `resolve_production_model()`;
  exclude `thesis-coherence-guard` entirely (it's the one agent whose verdict *is* a Model A read).
- **The allocator gate.** `resolve_production_model(required=True)` in `build.py` /
  `PortfolioService.build()` stay untouched; the digest never calls `build()`. If it ever shows
  "latest build result" it reads `job_runs.status` — never re-invokes and catches the dormant-state
  `RuntimeError` (that would silently soften rule #11's mechanical enforcement).
- **`ASXOS_PORTFOLIO_BRIEF_ENABLED`** — don't flip, don't couple (orthogonal, §4).
- **`ASXOS_V2_BRIEF_ENABLED`** — don't flip (all-or-nothing; ships stale signal framing).
- **s766B firewall — evidence-only wording, single recipient.** MAY state: facts James authored +
  arithmetic on them, tagged "needs attention / flagged for your review" (*"CBA revisit is 14 days
  overdue"*, *"HUBS is 100% of invested capital"*, *"stop $4.20 breached — close $4.12"*,
  *"conviction_level NULL on all theses"*). MUST NOT: recommend a trade (*sell/trim/exit/add/hold*),
  opine on merit (*overvalued / thesis broken*), emit a system forecast/target, present a
  ranked-as-advice action list, or infer James's objectives beyond what he entered. Hold the
  wording *tighter* than the existing alert jobs (some sit right at the line, e.g. "consider exit"),
  because a cadenced consolidated digest is more visible.
- **No auto-action on breach** — surface, never auto-exit; the human decides.
- **The daily brief email integrity** — the new section must fail *closed* (render an error line,
  never break sibling sections).
- **Decimal-only** in the new domain module.

## 8. Implementation PR plan (all reversible unless marked James-gated)

- **PR1 — pure evaluator, no infra. ✅ LANDED 2026-07-12/07-13 (this branch).**
  `asxos/domain/theses/discipline.py` composing existing `severity.py` + `trajectory.py` +
  `wealth_state` benchmark-lag + net-new conviction-NULL check + data-sanity check; full unit tests
  (`tests/test_thesis_discipline.py`, 19 tests, `mypy --strict` clean). Ships behind nothing, wired
  to nothing (no cron, no brief section, no DB) — PR2 wires a loader + surface. Security-review
  deltas incorporated as-built: (a) the timeline finding is **discipline-owned evidence-only
  wording** — it drops `severity.thesis_timeline_expired`'s "— review or close" tail because "close"
  reads as a trade direction (s766B, §7), re-deriving the same red/yellow classification with date
  arithmetic only; (b) **every per-check `except` is broad** (not narrow Decimal-only) so a mistyped
  loader input surfaces as a loud per-check `error` finding and isolates rather than aborting the
  batch (fail-loud, §6); (c) **missing price legs surface as an `incomplete_price_data` info
  finding** (symmetric with `no_stop_set`) rather than silently no-op'ing the trajectory/data-sanity
  checks — closing the exact silent-omission pattern this lane exists to fix.
- **PR2 — surface it (the increment that changes what James sees).** A-brief: a model-independent
  discipline section — `BriefData` field + `brief.html.j2` block + collector, gated
  `ASXOS_PERSONAL_USE`, fail-closed-on-error. Reversible by removing the section. *(Alternative:
  A-cron `jobs/check_thesis_discipline.py` mirroring `check_au_positions` + a `render.yaml` block +
  `HEALTHCHECK_URL_*`, added to `check_cron_health._EXPECTED_DAILY`.)*
- **PR3 — persistence sink (root-cause fix for cause #3; James-gated: migration).** A queryable
  `portfolio_review_findings` table so **both** the deterministic digest **and** any future
  pm-review Routine write to **one** place the brief reads — closing the "findings die in markdown"
  gap (option B's intent, done right). `backend-architect` + a migration → **James applies.**
- **PR4 — LLM `/pm-review` Routine (later; gated tier).** Only after the autonomy preconditions
  (branch protection on `main` + read-only DB role + attended track record + James's explicit
  enable); read-only, token-capped, writes into PR3's sink. This adds the ~10–20% reconciliation/
  narrative the deterministic layer can't do.

Route through: `backend-architect` (schema/write-path for PR3), then the standing review loop
(`security-engineer` for the s766B/firewall + email-output check, `refactoring-expert`,
`technical-writer`). Per CLAUDE.md #2, PR2's A-cron `render.yaml` change and PR3's migration are the
drift-sensitive / James-gated steps.

## 9. James decisions required

Added/confirmed in `james-inbox.md`:
- **Surface choice** (§5): A-brief (recommended) vs A-cron. Reversible either way — arbi proceeds on
  A-brief unless James prefers the separate email.
- **PR3 migration** (persistence sink) — schema apply is James's (migration approval class).
- **PR4 Routine enablement** — gated on the autonomy preconditions; James's explicit enable.
- **HUBS conviction — reframed by James, 2026-07-12.** James: *"it's bought through ESPP as I work
  at HubSpot… it should only be a part of the portfolio."* This is a real refinement, not just a
  missing number: `conviction_level` (1–5 "how much I believe in this pick") is arguably the *wrong
  field* for compensation stock he didn't choose to buy. The coherence check likely needs an
  **ESPP / single-employer concentration-risk** variant rather than forcing a conviction number.
  Flagged as a design question for the evaluator, and the `james-inbox` HUBS row updated to reflect
  it's a concentration-policy call, not a conviction-rating call.
- **CBA — fix or retire** (unchanged; data shows the 42/45/38/60 ladder is a data-entry error, CBA
  traded $142.36–$191.40 over 18 months). Not held, no capital at risk either way.
- **Small hardening (optional, related to R12):** `check_au_positions`/`check_us_positions`/
  `check_thesis_invalidations` omit the `ASXOS_PERSONAL_USE` gate their siblings have — the digest
  is a natural moment to close that gap too, or at minimum not replicate it.

## 10. Scope honesty — flagging vs generating (do not let this be read as more than it is)

James's words span two different capabilities:

- **Flagging** existing holdings (rate discipline on what he owns) — the 5 analysis agents. **This
  proposal fixes the *visibility* of the flagging half.**
- **Generating** — *"trend detection, investment selection, wealth-building vehicles"* — proposing
  *new* theses/instruments. That is the **discovery-agent track** (`macro-economist` Phase 2b, and
  the planned `theme-researcher`/`instrument-selector`/`sector-screener` Phase 2c), which is
  governance-gated and largely unbuilt.

And a hard honesty point per the calibration lesson: automated *stock rating* via the ML engine is
**deliberately shelved** (rule #11 — Model A had no usable edge on 19,032 signals). So "the system
rates stocks automatically" is not a bug to fix — it's a resolved architectural decision. The
model-independent product (discipline, tax, themes) is the moat. This proposal makes that moat's
discipline layer *visible and proactive*; it does not, and should not be read to, deliver automated
selection. That's a separate roadmap conversation worth having explicitly — but it isn't this bug.

## Sources
- Agents (2026-07-12): `system-architect`, `backend-architect`, `portfolio-invariant-guard`.
- `asxos/domain/brief/composer.py:89-98` (V2 render switch), `collectors/active_theses.py`,
  `collectors/wealth_state.py`, `severity.py`, `asxos/domain/theses/trajectory.py`
- `asxos/brief/compose.py:504` (`ASXOS_PORTFOLIO_BRIEF_ENABLED` gate), `:247-248` (ungated
  tax/reg), `:420-426`/`:502-505` (internal gates), `:188-232` (Model A skip)
- `jobs/check_au_positions.py`, `jobs/check_us_positions.py`, `jobs/check_thesis_invalidations.py`,
  `jobs/check_cron_health.py`; `asxos/domain/portfolio/paper_trade.py:294,351`; `asxos/cli/portfolio.py:376-428`
- `asxos/domain/portfolio/monitor.py:17-19` (no-silent-forward-fill), `asxos/domain/prices/fx.py`
- `.claude/rules/portfolio-conventions.md` (firewall, R9, hard-fail table, R10 FX),
  `.claude/rules/job-conventions.md`, `.claude/commands/pm-review.md:13-18`
- `docs/product/risk-register.md` (R8/R9/R10/R11/R12), `cleanup-backlog.md` (RC2/RC3/RC4),
  `portfolio-outcome-ledger.md` (rec-2026-07-11-CBA), `dark-launch-exit-plan.md`,
  `competitive-gap-analysis-2026-07-11.md:210-219` (s766B/Westpac), `arbi-autonomy-loop.md:56-79`
