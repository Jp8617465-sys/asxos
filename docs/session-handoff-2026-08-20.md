# Session handoff — 2026-08-20

**Status:** current
**Read priority:** read first
**Supersedes:** `docs/session-handoff-2026-08-18.md`

---

## STOP — read first

**1. Rule #11 (Model A quarantine) STANDS. Model A's code is now deleted — that is NOT grounds
to drop the rule.** PR #144 (`da64c1b`) removed the training chain, artefacts, feature engine
and signal machinery. `CLAUDE.md:25` names exactly one removal condition — a *new* model
clearing a pre-registered decay bar AND earning `approved_for_allocation` — and pre-emptively
forbids removal "on the basis of v1_5". Deleting v1_5's code is a fact about v1_5. Compliance is
now **partly by absence and partly by the surviving gate**: `production_gate.py`, the
`model_versions` / `signal_outcomes` tables and `cli/model.py` were deliberately kept because
the gate is generic and governs whatever model comes next.

**2. ⏰ TIME-BOXED — migration `0044` must be applied before Sat 2026-08-22 16:00 UTC.**
Verified live 2026-08-20: `rs_fundamentals_pit.currency` **does not exist** in production, but
merged code (#142) UPSERTs it. `weekly-research.yml` runs `derive_fundamentals_pit.py` as an
*ordered blocking step*, so the run fails there **and blocks `sync_fundamentals` beneath it**.
Apply **Patch 0** (comment corrections) first — see below. This is arbi's defect: code and
migration were drafted together, but only code could merge.

**3. `/pm-review` is unsafe until Patch 2 lands.** `thesis-coherence-guard` queries
`FROM signals WHERE model='model_a'`. #144 deleted every writer, so it returns **frozen Model A
SHAP evidence presented as current** into a synthesis that informs real holding decisions —
worse than an error, because it looks like a working answer. Its frontmatter says "use
**PROACTIVELY**", so avoiding the command does not fully contain it.

---

## What shipped

**Merged by James (three PRs, in dependency order):**

| PR | Commit | What |
|---|---|---|
| #144 | `da64c1b` | Model A retired — training chain, artefacts, feature engine, signal machinery, `cli/signal.py`, `brief/shap.py`, `compute_opportunity_cost.py`, 14 test files |
| #142 | `32ed2f5` | Segment-valuation architecture **+ L0 substrate** (D1/D2/D3 as real code) + draft migrations `0044`/`0045` |
| #141 | `59fb835` | Render fully retired from the repo |

**Open and green (draft, awaiting James):**

- **#146** `claude/live-validation-followup-2026-08-20` — the live-validation fix. CLEAN/MERGEABLE.
- **#143** `claude/reconciliation-2026-08-19` — the reconciliation record, refreshed. CLEAN/MERGEABLE.

**Side effect worth knowing:** the full suite now runs **2303 passed / 0 failed / 0 errors**.
The long-documented joblib/lightgbm sandbox collection-error gap died with Model A. `CLAUDE.md`'s
entire "Known test environment gaps" section is now obsolete.

---

## The finding that matters: mocks passed, production did not

#142's substrate merged with 69 green tests, **all `FakeConn`-mocked**. Dry-running the merged
code against production read-only found:

| | Mocked tests said | Production said |
|---|---|---|
| Currency fallback | ✅ passes | **Defect** — blank stored as `''`, not NULL |
| D3 alias fallback branch | ✅ passes | **0 of 4,418** — never fires |
| D3's actual value | unmeasurable | **233 symbols repaired** (5.3%) |
| FX scope | ~12 currencies | **20** |
| D2 hybrid filter | ✅ passes | ✅ **2,393 → 2,350, correct** |

The dead-fallback result falsifies a **design premise**, not a line of code: D3 treated
`gics_sector` and `universe.sector` as independent vocabularies, but both propagate from the same
EODHD `General.Sector` field, so they go blank together (all 515 candidates are `''`). The
resolver is correct; the framing wasn't. Full detail in
`docs/proposals/segval-live-validation-2026-08-20.md`.

This is the second instance of the lesson `portfolio-conventions.md` already records from Phase
2a. **Mocked tests plus review loops are not sufficient for anything that touches live data
shape.** Dry-run read-only before it ships.

---

## Pending, requiring James

1. **Apply `0044` before Sat 16:00 UTC** — apply **Patch 0** first (three superseded figures;
   one lands in `COMMENT ON COLUMN` as permanent metadata: 612→**530**, 14→**20**, 102→**947**).
   Then `0045` (not time-boxed — nothing runs `build_segment_map` yet). Then bump
   `REQUIRED_MIGRATIONS` from 96 to the **observed** count, not a guessed +1.
2. **Merge #146 and #143.**
3. **Patch 1 — schedule `detect_theme_stages`** (un-refreshed since at latest 2026-08-12).
   ⚠️ Confirm the KEEP ruling is in force first: it is recorded as Amendment F, which lives only
   on unmerged #143, and `scheduler-inventory-2026-08-13.md:196` still classifies the job
   **DECIDE / governor call**.
4. **Patch 2 — `thesis-coherence-guard`: amputate, don't retire.** Its step 4
   (`thesis_revisions` thesis-fatigue check) is live and model-independent; deleting the whole
   agent throws working discipline away.
5. **`CLAUDE.md` is stale in ~17 places** — the obsolete test-gaps section, rule #11's framing,
   the migration ceiling (says 0043, now 0045), `ml-conventions.md`'s description (now a stub),
   four dead slash commands, and a subagent breakdown summing to 23 of 25.

---

## Boundaries held

No merges by arbi (`push-guard.sh:133` denied `gh pr merge` — correctly, on the one attempt).
No migration applied — arbi holds only read-only Supabase tools, and application is James's
under three independent rules. No capital action, no production write, no authority file
self-applied. Rule #11 untouched and restated. All live verification was read-only SELECT.
