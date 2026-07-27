# Session handoff — 2026-07-25

**Status:** current
**Read priority:** read first
**Supersedes:** `session-handoff-2026-07-24.md` (still valid for pre-dossier state)
**Branch:** `claude/investment-engine-dossier-review-ozg1ny` (pushed; 12 commits ahead of `main`)
**Nothing merged, deployed, migrated, or applied this session.**

---

## STOP — read first

1. **Model A quarantine (CLAUDE.md rule #11) stands.** Standing policy, not a dispute.
   Verified live this session: `model_versions` holds exactly one row (`model_a`/`v1_5`,
   `is_active=true`, `approved_for_allocation=false`), so zero rows satisfy the allocator
   gate, and `build_portfolio` has been `blocked` since 2026-07-18 with `ModelGateDormant`.
   The mechanical enforcement is working as designed.
2. **PR #70 must not be merged as-is.** The 12-week investment-engine dossier is AMBER:
   sound architecture, but R0 repair is incomplete and four financial-semantics defects
   were still open at session end. See "pending, requiring James".
3. **The dossier is not authority yet.** `decisions.md` and `README.md` now read as
   PROPOSED. Do not cite the dossier against `CLAUDE.md` or any ratified `docs/product/`
   document until James's merge lands and is recorded in `decision-log.md`.

---

## What this session was

A ChatGPT-authored mission asked for an adversarial review of PR #70 — the accepted
twelve-week investment-engine dossier (157 files, +39,974 lines) — followed, after James's
approval, by execution of the resulting repair plan. Two phases: review, then R0 repair.

## What shipped

**Phase 1 — review** (`5775628`, `39b0947`)

- Eight parallel adversarial agents across north-star alignment, model independence, review
  integrity, evaluator soundness, construction/sizing, data contracts, delivery realism, and
  authority/safety. 62 findings.
- **Review Packet v2** as a delta after James independently challenged five conclusions. All
  five accepted; four were genuine overreach on arbi's part — see "corrections" below.

**Phase 2 — R0 repair** (`c869a8f` … `19f0b53`)

- **R0-A1** — `comparison` discriminator (`MINIMUM|MAXIMUM|EXACT|CAP_APPLIED`) on all 18
  numeric sizing checks; `limit_value` now resolves from the ratified policy for 17 of 18.
- **R0-A2** — one artifact-ID collision guard (intra- and cross-contract), and a direct
  digest comparison replacing an evadable entropy heuristic.
- **Fixture repair** — the cross-contract collision, and the two placeholder digests it hid.
- **Probe script** — `scripts/probe_eodhd_identity_and_benchmark.py`, read-only, tri-state.
- **Four parallel lanes** (B2 honesty pass, B3 acceptance wording, C1 brownfield tables,
  C2 capacity model), each checked by an independent verifier agent.

Validator PASS · 130 dossier tests · ruff clean under the CI-pinned 0.7.0.

## Five real defects found in the shipped dossier bytes

None was caught by the dossier's own validator, its 111 tests, or the eight-agent review.
Each surfaced only when the corresponding check was actually *implemented*.

1. **ADV cap derived from the wrong policy** — `risk-policy` says `0.10`, `sizing-policy`
   says `0.02` and the contract makes sizing authoritative for liquidity caps. The golden
   fixture used the risk value: a 5× overstatement of the permitted order size.
2. **SPREAD observed contradicted its source** — fixture `0.001000` against a proposal
   candidate of `0.002000`.
3. **Cross-contract artifact-ID collision** — `broker-report-v1` and `review-eligibility-v1`
   shared one ID, which dropped it from the bare-ID index and **silently disabled 15
   reference checks across 11 fixtures**.
4. **Two placeholder digests on the capital path** — `dddd…` (64 chars, matching no real
   artifact) in `portfolio-proposal-valid.json`'s `eligibility_decision_ref` and
   `cap_checks[0].source_ref`, hidden by (3). `--write-fixture-hashes` was blind to them too.
5. **`s01:9` claimed acceptance rows AC-26–27** that the matrix locks at S06/S07 — a shipped
   `DOSSIER_DRIFT` that would have halted week 1 before any code was written.

## Corrections arbi made to its own review

Recorded because the review's credibility depends on them being visible.

- **PC-02 was wrong.** The proposed universal `observed ≤ limit` rule would have failed six
  legitimate checks. `NUMERIC_LIMIT` carries three directions plus an applied-value cap;
  `LOSS_HEADROOM obs=15000 / lim=0 / PASS` is correct under a MINIMUM reading.
- **EV-06's bias claim withdrawn.** The tax profile is `INDIVIDUAL_RESIDENT_PAPER_SCENARIO`,
  the host rule is SMSF-specific and warning-only, and the $5,000 small-shareholder exemption
  applies to individuals. `OFFSET_ESTIMATED_TAX_NO_REFUND_ASSUMED` biases *downward*.
- **EV-04 corrected.** `0.000001` is the canonical six-decimal form of strict `>0` under
  DEC-024, not a weakened threshold. The gap is the absent materiality/MDE report.
- **The index code was wrong.** `XJOAI` is the Buy-Write index. The accumulation series is
  **XJOA**; **XJT/AXJT** is gross TR, **XNT/AXNT** net TR.
- **Licensing was too pessimistic.** RBA Statistical Table F7 publishes the S&P/ASX 200
  Accumulation index under **CC BY 4.0** — monthly, machine-readable, licence-clean.

## Lesson: agents fail at confidence, not at work

The four parallel lanes produced good content and left the validator green. Their independent
verifiers found **19 false claims** — all corrected before commit. The worst: a lane closing
the "dossier asserts its own acceptance" finding inserted into *both* files a claim that
James's merge is "reviewed under the repository's code-owner and branch-protection controls".
`.github/CODEOWNERS` has **no entry for `docs/programs/**`**, so that merge triggers no
code-owner review at all — a false governance assertion about the exact control the finding
says is missing.

Operational consequences, both now recorded in `operations-and-rollout.md`:

- **Build-then-verify is not optional overhead.** A builder that commits its own work would
  have shipped all 19.
- **Docs must follow code, never run beside it.** A concurrent technical-writer pass landed a
  stale coverage sentence in a committed contract because it read a moving target.

---

## Pending, requiring James

| # | Decision | Why it blocks |
|---|---|---|
| 1 | **Run the EODHD probes** — `EODHD_API_KEY=... python3 scripts/probe_eodhd_identity_and_benchmark.py` (exit 3 = inconclusive, not negative) | Settles ~80% of the S07 identity build and the S10/S11 benchmark at zero cost. The key is a Render secret, absent from the session. |
| 2 | **Tax rounding conflict** | `asxos/domain/tax/positions.py:36-41` quantizes to cents/`ROUND_HALF_UP`; `accounting-policy-valid.json` specifies 6dp/`ROUND_HALF_EVEN`. Resolving it wrong re-opens TC-11's asserted $1,950. Route to `tax-spec-conformance`. |
| 3 | **Day-count CGT in `tax-profile-v1`** | `minimum_holding_days: "365"` violates non-negotiable rule #6 / spec §5.1. Calendar arithmetic is structurally inexpressible in the schema as shipped. Unfixed — R0-B1. |
| 4 | **Franking eligibility semantics** | Needs a design choice (exemption threshold, entity-conditional switch). Preserve warning-only; never auto-deny. |
| 5 | **Benchmark decision** | If EODHD lacks the TR series: RBA F7 (CC BY 4.0, monthly) + a labelled ETF-NAV proxy, and `benchmark-policy-v1` must be amended — otherwise **S11's strategy gate is permanently unpassable**. |
| 6 | **Code-owner coverage** over `docs/programs/**`, `roadmap.yaml`, and the four uncovered authority docs | AS-01/AS-03. An agent just demonstrated why, by asserting the control exists. |
| 7 | **DEC-025** — Model A runtime decommission | Correctly pending. R1's predicate now defined under both branches. |
| 8 | **Merge sequencing for PR #70** | R0 repair currently lives on the review branch. Cherry-pick onto `agent/investment-engine-dossier`, or repoint #70. James's call. |

## Not done, and why

- **R0-B1** (financial-semantics contracts) — the CGT calendar rule and freshness-policy
  artifact are buildable now; the franking half needs decision #4 first.
- **`RESERVATIONS`** is the one numeric code whose limit resolves from nothing — a gap in the
  *policy set*, not the harness. No ratified artifact expresses a reservation cap.
- **Capacity model** published in `operations-and-rollout.md` needs re-baselining: the
  brownfield survey found **+48 to +76 agent-hours** on S07/S10/S12 (25–40% under-estimate),
  concentrated in S07-D, S10-C and S12-B. S09 stands as estimated.

## Files to commit to `main`

This handoff and `roadmap-state.md` live on the review branch. Per `docs/README.md`, a
handoff that lives only on a feature branch is a process defect — they need to reach `main`
via a deliberate `/ship`, not from here.

- `docs/session-handoff-2026-07-25.md`
- `docs/product/roadmap-state.md`
- `docs/product/arbi-run-ledger.md`
