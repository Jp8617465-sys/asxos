# Session handoff — 2026-08-22

**Status:** current
**Read priority:** read first
**Supersedes:** the merge-train close in this same file (ledger
`close-2026-08-22-merge-train`, `main` then @ `62ccceb`) and
`docs/session-handoff-2026-08-21.md`
**Written for:** a new session with zero context.
**Close:** `/arbi-close` after the harness rebuild + `/arbi-promote`.
Ledger row `close-2026-08-22-harness-promote`. Score **4.4 provisional**.

---

## STOP — read first

**1. Rule #11 (Model A quarantine) STANDS.** Do not use Model A output —
signals, candidate scans, allocator runs, or new thesis proposals derived
from it — as a basis for real capital decisions. Removal still requires a
**new** model clearing a pre-registered decay bar AND earning
`approved_for_allocation`.

**2. Memory on `main` is L1–L45.** Promoted this session as **#159**
(`1ee184d`). Live `dream-candidates/` has only `README.md` + `archive/`.
Do not re-promote 17.x / 18.x / 22.x.

**3. The harness rebuild is on `main` as #158** (`70b0156`). Review-gate
is gone. Attended Edit of `.claude/settings.json`, `.claude/hooks/**`, and
`CLAUDE.md` is un-denied. `unattended-guard.sh` is unchanged and still
treats those three as authority when `ARBI_UNATTENDED=1`. Operating map:
`docs/product/harness-profiles.md`. User `defaultMode: auto` is **not**
applied — James owns `~/.claude/settings.json`.

**4. `/pm-review HUBS.NYSE` owed by #149 is OBSERVED.** Four fan-out
agents, zero Model A / `signals` figures, verdict **REVIEW**. Do **not**
re-open the "unsafe until patch C" claim.

**5. The agent DB role is inert.** `asxos_agent_ro` exists; the MCP
authenticates as `supabase_read_only_user`. See
`docs/proposals/agent-db-role-the-control-is-inert-2026-08-22.md`.

**6. W1-2 (V1 brief section) was CHALLENGEd and did not run.** Still not
#1. Packet-first renderer stays P6-01 / Stage 6.

---

## What this session did

James (Cursor Cloud Agent): execute the harness rebuild → merge #158 →
"are there new lessons?" → merge them → `/arbi-close`.

| Item | Result |
|---|---|
| Harness rebuild | **#158** `70b0156` — official modes, `/build`, `/arbi-run` stub, review-gate deleted, Fix A+B, Cursor I5/I6 port, G8 |
| #153 | **MERGED** as dream-only after rebase onto `main` (`f31ab51`). Not a second SB PR |
| `/arbi-promote` | **#159** `1ee184d` — L27–L45 + amendments to L11/L17/L19/L22/L23/L26 |
| W1-2 | Still not executed (CHALLENGE stands) |

## Merges this close (on `main`)

| PR | SHA | What |
|---|---|---|
| **#158** | `70b0156` | Harness rebuild |
| **#153** | `f31ab51` | 2026-08-22 dream candidate |
| **#159** | `1ee184d` | Promote L27–L45 |

`main` tip: `1ee184d`. Each head was `full-check` green. No `--admin`.
James authorized every I6 merge in this session.

**Amendment E.** **renders:** TLS.AU FY2024 PIT abstain already on `main`
via #155 (`presentation_sha256`
`1224d5f35440e55eb721bba0fbb65c12d018202bf79cdb6051517f81df7baac0`).
**captures:** n/a — this close is docs + already-merged PRs.
**defect:** holdout evals / `episode_score` trend on #159 recorded NOT RUN
(same honesty as #125 / L26). User `defaultMode` not applied.

## Sprint-state at close

- Git: `main` @ `1ee184d`. **Zero open PRs** at probe (this close PR is
  the next one). Working tree clean on the close branch.
- Migrations: latest applied `20260821080458` (`fundamentals_pit_currency`)
  via Supabase `list_migrations`. `REQUIRED_MIGRATIONS = 97` on `main`.
  `0045` on disk, **not** applied. Disk count 43 SQL files (0042 reserved).
- Tests: required `full-check` SUCCESS on `main` push of `1ee184d`
  (run `32601337738`, 1m16s). This close does not re-run the suite.
- Issues: `gh issue list` 403 from this token (`repository.issues`).
- Memory: `approved-lessons.md` has **44** `## L*` headings (L1–L45;
  L6 struck in place so the heading count is not 45). Promotion-log row
  2026-08-22 present.

## Must not

Apply 0045 / INSERT `screening_rules` / touch 0042 / read `signals` as
evidence / tax math / V2 or portfolio-brief flags / F4 / capital.
Do not re-promote archived 17.x / 18.x / 22.x. Do not start W1-2 as #1.
Do not set `defaultMode` in project settings. Do not treat a spoken grant
as a config write (L39).

## James still owns

`permissions.defaultMode: "auto"` in `~/.claude/settings.json` (runbook
`docs/product/runbooks/claude-code-user-settings.md`); MCP alias pin /
OAuth; `supabase-ro` → `asxos_agent_ro` then REVOKE; second GitHub
identity; dark-launch #1/#4 by **2026-08-28**; F4; `0043`/`0044` false
DRAFT headers; thesis authorship; Amendment E retroactivity on
#113–#122; HUBS A$701 FX; standing 7b; **this close PR onto `main`**
(handoffs that live only on a branch are a process defect —
`docs/README.md`).

## Next

James names the next unit. Written later-candidates: screening seed
INSERT (I5), apply 0045 (I5), MCP principal repoint (James). W1-2 stays
CHALLENGEd. The promotion backlog that L34 names is **closed**.
