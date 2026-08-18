# Plan — arbi toward maximal north-star-anchored autonomy

**Status:** draft plan (advisory) · **Date:** 2026-08-18 · **Owner to ratify:** James (governor)
**Basis:** `arbi-permission-model.md`, `arbi-autonomy-loop.md`, `arbi.md`,
`docs/session-handoff-2026-08-18.md`. This plan changes no grant; grants move only by James.

---

## The honest frame

The organising principle is **reversible vs irreversible, not autonomous vs not**
(`arbi-permission-model.md`). "Most autonomous" therefore means: **maximise standing autonomy
across every reversible tier (infra I0–I4, portfolio P0–P4) while the irreversible tiers
(I5–I6 merge/deploy/migrations/secrets, P5–P6 policy/execution) stay permanently human.** The
permanent human firewall — merge = deploy, capital = James's broker (s766B) — is what *makes*
broad reversible autonomy safe. We do not grow autonomy by removing gates; we grow it by
earning standing rights on the reversible side and making the irreversible taps cheap.

## Where arbi stands today (`arbi-permission-model.md §Where arbi stands`)

- **Infra:** standing I0–I1 (read + think + draft). I2 (docs write) only inside an invoked
  command. I3–I6 not granted.
- **Portfolio:** standing P0 (read-only). P1–P2 only inside `/pm-review`; memos
  model-independent (rule #11). P3–P6 not granted; `portfolio-outcome-ledger.md` empty.

## The objective function: the north star, made measurable

arbi already ranks by moat defensibility and cites a north-star goal per action (`arbi.md`).
To *centre* autonomy on the output, close the loop:

1. **Score outcomes against moat layers.** `arbi-scorecard.md` + `arbi-run-ledger.md` should
   record whether each shipped "one thing" advanced a moat layer (discipline/tax/themes),
   under **Amendment D** ("correct-and-empty is not done" — a unit is incomplete while its
   live-data output is empty/unavailable/demo-only, `roadmap-state.md`).
2. **Feed it back.** The weekly `/arbi-dream` → monthly `/arbi-promote` memory loop promotes
   lessons that improved north-star progress and retires ones that didn't. That turns
   "autonomous" into "autonomous *toward the output*," not toward feature velocity.

## Gates to standing unattended autonomy (the 7a → 7b flip)

From `arbi-autonomy-loop.md §Activation`, with today's status:

| # | Precondition | Status |
|---|---|---|
| 0 | **Re-anchor the map** to post-Render/post-Model-A (this session's finding) | **OPEN** — see the reconciliation work order |
| 1 | Model A dispute resolved | ✅ (2026-07-11; now *deleted*, quarantine standing) |
| 2 | Branch protection on `main` | ✅ configured — but `enforce_admins:false` and CODEOWNERS advisory at 0 approvals |
| 3 | R2 read-only Postgres role (`0039_agent_readonly_role.sql`, drafted, not applied) | **OPEN** |
| 4 | Review identity ≠ PR author (makes CODEOWNERS mechanical) | **OPEN** — demonstrated prerequisite: PR #137 merged touching `CLAUDE.md` with no review |
| 5 | Track record — clean scorecards over a sustained attended window | **OPEN** |
| 6 | James's explicit enable | **OPEN** |

Gate 4 is the linchpin the 2026-08-18 handoff upgraded "from fine print to a demonstrated
prerequisite": with one identity, GitHub allows only gate-everything or gate-nothing, so the
"grader ≠ producer" merge gate is aspirational until a second identity (a second account or a
GitHub App) exists.

## The live-state feed (the enabler nobody has yet)

arbi is only as good as the snapshot it reconciles, and by its own ladder **live state
outranks repo docs**. Its old `/catchup` probe read Render health — that half is now dead.
The single highest-leverage enabler is a **current, trustworthy live-state feed on the new
substrate**: GitHub Actions run status (per-workflow last-run outcome) + Supabase
data-freshness. Without it, every unattended brief risks the "branch-only treated as main
truth" circuit breaker.

## Execution substrate — decide deliberately

Jobs are now GitHub Actions (settled). The *autonomy-loop* execution substrate is still open:
Claude Code Routines, `.github/workflows/claude-execute.yml` (attended I3/I4), or **Cursor
Cloud Agents** (isolated branch + draft PR per mission). Recommendation: evaluate Cloud
Agents as the unattended reversible builder — the branch-to-draft-PR shape fits natively and
it sidesteps the pre-existing Render/Routine assumptions.

## Staged rollout

- **Stage A — re-anchor + rewire (now, reversible).** Apply the reconciliation work order
  (map truth); rewire the live-state probe to GitHub Actions + Supabase freshness; land the
  guard fixes so agent Write/Edit and doc writes work unattended (the `authority-guard.sh`
  cwd/false-positive class — PR #111 §3).
- **Stage B — mechanical backstops (James).** Apply `0039` read-only DB role; stand up the
  second review identity so CODEOWNERS is enforced. These are what make "provably fenced,"
  not "trusted."
- **Stage C — track record (attended).** Run the inner loop attended (`/arbi` → `/arbi-run`
  → review → draft PR), logging clean scorecards over a sustained window; wire the
  north-star scoring above.
- **Stage D — flip 7b (James).** Enable standing scheduled autonomy lowest-risk-first:
  weekly `/arbi-dream` (writes only a branch) → daily read-only brief (7a, already live) →
  daily reversible build-loop, each driving to a green draft PR and stopping at merge.

## End state

arbi holds standing autonomy across all reversible work on both ladders: it wakes on a
schedule, reconciles a *current* live-state feed against a *current* north star, drafts the
next mission, fans specialists out to a green draft PR, and learns each cycle — while every
irreversible act (merge, migration, capital) stays a fast human tap and the north-star
scorecard is the loop's feedback signal.

## Permanent human gates (never promoted, by design)

I5–I6 (irreversible infra), P5 (capital-policy change, draft-only forever), P6 (execution —
not a tool arbi holds). No track record unlocks these.
