# Session handoff — 2026-08-22

**Status:** current
**Read priority:** read first
**Supersedes:** `docs/session-handoff-2026-08-21.md`

---

## STOP — read first

**1. Rule #11 (Model A quarantine) STANDS.** Do not use Model A output — signals,
candidate scans, allocator runs, or new thesis proposals derived from it — as a
basis for real capital decisions. Removal still requires a **new** model clearing
a pre-registered decay bar AND earning `approved_for_allocation`.

**2. `/pm-review HUBS.NYSE` owed by #149 is OBSERVED.** Four fan-out agents, zero
Model A / `signals` figures, verdict **REVIEW**. Direct `thesis-coherence-guard`
on thesis 2: **NEEDS REVIEW** (revisit due 2026-08-03, 19d overdue). The
mechanical residual — `REVOKE SELECT ON signals` for the agent role — is still
James's.

**3. W1-1 is integration evidence, not Stage 4.** `asxos_pit_db` is a hashed
research-store snapshot. G2 (ASX announcement feed) stays closed. First honest
outcome is `abstain` with G2/G3/G5 named. Do not label PIT as an announcement
and do not label a fixture `data_mode=real`.

---

## What this session did

James: Claude sessions finished; write the final plan and start executing a
chain. The 2026-08-22 red-team CHALLENGEd a four-wave campaign. Binding shape:
**one work order, one branch, one draft PR, one close.**

| Item | Result |
|---|---|
| Envelope | `docs/proposals/repo-integration-chain-2026-08-22.md` |
| W1-1 code | `AcquisitionPath` += `asxos_pit_db`; `pit_db.py`; `asx results-review show` |
| Tests | 105 targeted tests pass; fixture never-real regression held |
| **renders:** | `docs/proposals/w11-tls-pit-renders-2026-08-22.md` — TLS.AU FY2024, `abstain`, sha256 `1224d5f35440e55eb721bba0fbb65c12d018202bf79cdb6051517f81df7baac0` |

Honest limit: this cloud VM had no `DATABASE_URL`, so the CLI was not fired
against the app role. The live snapshot was SELECTed from the four allowlisted
tables only, then run through `adapt_pit_snapshot` + `present_adapted`.

## Must not (still)

Merge / un-draft / push `main` / apply 0045 / INSERT `screening_rules` /
touch 0042 / read `signals` / tax math / V2 flags / F4 / capital. Do not start
a second work order in this PR.

## James still owns

Dark-launch #1/#4 by 2026-08-28; F4 capital/risk calibration; 0039 + `REVOKE
SELECT ON signals`; thesis authorship; Amendment E retroactivity on #113–#122;
HUBS A$701 FX (0.6450 estimated vs 0.7171 vendor).

## Next (after this PR closes)

James names the next unit. Candidates the red-team already ranked *later*:
screening seed, 0045, SB1-02. Not this PR.
