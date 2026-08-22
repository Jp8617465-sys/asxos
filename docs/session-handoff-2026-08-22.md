# Session handoff — 2026-08-22

**Status:** current
**Read priority:** read first
**Supersedes:** `docs/session-handoff-2026-08-21.md`
**Written for:** a new session with zero context.

---

## STOP — read first

**1. Rule #11 (Model A quarantine) STANDS.** Do not use Model A output — signals,
candidate scans, allocator runs, or new thesis proposals derived from it — as a
basis for real capital decisions. Removal still requires a **new** model clearing
a pre-registered decay bar AND earning `approved_for_allocation`.

**2. `/pm-review HUBS.NYSE` owed by #149 is OBSERVED.** Four fan-out agents, zero
Model A / `signals` figures, verdict **REVIEW**. Direct `thesis-coherence-guard`
on thesis 2: **NEEDS REVIEW** (revisit due 2026-08-03, 19d overdue). Do **not**
re-open the "unsafe until patch C" claim from the pre-#149 #152 handoff — that
row is discharged. The mechanical residual is a **repoint** of the MCP principal
to `asxos_agent_ro`, not a REVOKE against that inert role.

**3. W1-1 is integration evidence, not Stage 4.** `asxos_pit_db` is a hashed
research-store snapshot. G2 stays closed. First honest outcome is `abstain` with
G2/G3/G5 named. **Merged as #155** (`d7e8242`).

**4. The agent DB role is inert.** `asxos_agent_ro` exists; the MCP authenticates
as `supabase_read_only_user` (`rolbypassrls`, `pg_read_all_data`). See
`docs/proposals/agent-db-role-the-control-is-inert-2026-08-22.md` and
`docs/proposals/db-access-remediation-2026-08-22.md`.

---

## Merge train (James-authorized I6, 2026-08-22)

| PR | Result |
|---|---|
| **#155** | W1-1 PIT path. TLS.AU FY2024 `renders:` abstain. `d7e8242` |
| **#151** | Tier 2a liquidity gate + `screening_runs` audit. `67b3bae` |
| **#154** | Migration-drift asymmetry + stop-out names the stop. `f0b8f9c` |
| **#152** | This branch — SB1-02 → SB3-01 + `roquery`. In the train |
| **#153** | **HELD.** Dream overlay; 18/20 commits shared with #152. Do not merge as a second SB PR |

No `--admin`. Branch protection required each head up to date; each later PR was
rebased `--onto origin/main` with `--force-with-lease`.

---

## What #152 carries (the remaining unit)

Second-brain lane: read-only probes, contradiction/staleness detection, mission
context schema freeze, `scripts/roquery.py`, G1 recorded (`P3-01`/`P3-02`
approved; `SB4-01` parked). `REQUIRED_MIGRATIONS` 96→97 was already on `main`
via #154 — the duplicate bump commit was skipped on rebase.

`.claude/**` patches in `docs/proposals/claude-config-patches-2026-08-22/` stay
**unapplied**. Patch C (`thesis-coherence-guard` signals amputation) is **stale**
against #149. A/B remain James's (authority files).

---

## Must not

Apply 0045 / INSERT `screening_rules` / touch 0042 / read `signals` as evidence /
tax math / V2 or portfolio-brief flags / F4 / capital. Do not merge #153 in this
train. Do not open a parallel SB PR.

## James still owns

Dark-launch #1/#4 by 2026-08-28; F4; 0039 + MCP **repoint** then REVOKE;
`0043`/`0044` false DRAFT headers; thesis authorship; Amendment E retroactivity
on #113–#122; HUBS A$701 FX; `.claude/settings.json` allow-rule / defaultMode.

## Next

After #152 merges: James names the next unit. #153 needs a **dream-only** rebase
onto the new `main` before any `/arbi-promote` consideration.
