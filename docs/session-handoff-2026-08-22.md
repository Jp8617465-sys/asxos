# Session handoff — 2026-08-22

**Status:** current
**Read priority:** read first
**Supersedes:** `docs/session-handoff-2026-08-21.md`
**Written for:** a new session with zero context.
**Close:** `/arbi-close` after James's I6 merge train. Ledger row
`close-2026-08-22-merge-train`. Score **4.4 provisional**.

---

## STOP — read first

**1. Rule #11 (Model A quarantine) STANDS.** Do not use Model A output — signals,
candidate scans, allocator runs, or new thesis proposals derived from it — as a
basis for real capital decisions. Removal still requires a **new** model clearing
a pre-registered decay bar AND earning `approved_for_allocation`.

**2. `/pm-review HUBS.NYSE` owed by #149 is OBSERVED.** Four fan-out agents, zero
Model A / `signals` figures, verdict **REVIEW**. Direct `thesis-coherence-guard`
on thesis 2: **NEEDS REVIEW** (revisit due 2026-08-03, 19d overdue). Do **not**
re-open the "unsafe until patch C" claim — #149 discharged it. The mechanical
residual is a **repoint** of the MCP principal to `asxos_agent_ro`, not a REVOKE
against that inert role.

**3. W1-1 is integration evidence, not Stage 4.** `asxos_pit_db` is a hashed
research-store snapshot. G2 stays closed. First honest outcome is `abstain` with
G2/G3/G5 named. **On `main` as #155** (`d7e8242`).

**4. The agent DB role is inert.** `asxos_agent_ro` exists; the MCP authenticates
as `supabase_read_only_user` (`rolbypassrls`, `pg_read_all_data`). See
`docs/proposals/agent-db-role-the-control-is-inert-2026-08-22.md` and
`docs/proposals/db-access-remediation-2026-08-22.md`.

**5. W1-2 (V1 brief section) was CHALLENGEd and did not run.** `/arbi-mission`
empty args wrapped arbi's #1. Four of five red-team lenses fired. James then
named the merge train instead of a sixth production thread.

---

## What this session did

James: Claude sessions finished → execute a chain → `/arbi-mission` (plan) →
merge train if green.

| Item | Result |
|---|---|
| W0 | `/pm-review HUBS.NYSE` observed (REVIEW; zero Model A) |
| W1-1 | #155 `d7e8242` — PIT path; TLS.AU FY2024 `renders:` abstain |
| W1-2 | **CHALLENGE.** Not executed. |
| I6 train | #155 → #151 → #154 → #152. No `--admin`. |
| #153 | **HELD.** Dream overlay of #152 (18/20 commits shared). Still draft, `CONFLICTING`. |

## Merge train (on `main`)

| PR | SHA | What |
|---|---|---|
| **#155** | `d7e8242` | W1-1 `asxos_pit_db` |
| **#151** | `67b3bae` | Tier 2a liquidity + `screening_runs` audit |
| **#154** | `f0b8f9c` | Drift asymmetry + stop-out names the stop |
| **#152** | `62ccceb` | SB1-02 → SB3-01 + `roquery`. Duplicate `REQUIRED_MIGRATIONS` bump skipped |

`main` tip: `62ccceb`. Branch protection required each head up to date; later
PRs were rebased `--onto origin/main` with `--force-with-lease`.

**Amendment E.** **renders:** TLS.AU FY2024 PIT (already recorded on #155;
`presentation_sha256` `1224d5f35440e55eb721bba0fbb65c12d018202bf79cdb6051517f81df7baac0`).
**captures:** n/a — this close is a merge train, not a table write.
**defect:** #153 remains `DIRTY`/`CONFLICTING`; `asx results-review show` was
not fired on this VM (no `DATABASE_URL`) — stated, not papered.

## Sprint-state at close

- Git: `main` @ `62ccceb`. One open PR: #153 draft, conflicting
  (`claude/arbi-mem/2026-08-22`). Unique dream commits vs the #152 squash
  are `a976173` + `450709e`; the rest is the already-merged SB lane.
- Migrations: latest applied `20260821080458` (`fundamentals_pit_currency`)
  via Supabase `list_migrations`. `REQUIRED_MIGRATIONS = 97` on `main`.
  `0045` on disk, **not** applied. Disk count 43 SQL files (0042 reserved).
- Tests: last green is required `full-check` on `62ccceb` (and on each of
  the four merge heads). This close does not re-run the suite.
- Issues: `gh issue list` 403 from this token (`repository.issues`).

## Must not

Apply 0045 / INSERT `screening_rules` / touch 0042 / read `signals` as evidence /
tax math / V2 or portfolio-brief flags / F4 / capital. Do not merge #153 as a
second SB PR. Do not start W1-2.

## James still owns

Dark-launch #1/#4 by **2026-08-28**; F4; 0039 + MCP **repoint** then REVOKE;
`0043`/`0044` false DRAFT headers; thesis authorship; Amendment E retroactivity
on #113–#122; HUBS A$701 FX; `.claude/settings.json` allow-rule / defaultMode;
**this close PR onto `main`** (handoffs that live only on a branch are a process
defect — `docs/README.md`).

## Next

James names the next unit. Written later-candidates: screening seed (liquidity
already on `main` via #151 — a *seed INSERT* is still I5), 0045 (I5), SB work
already on `main` via #152. #153 needs a **dream-only** rebase onto `62ccceb`
before any `/arbi-promote` look.
