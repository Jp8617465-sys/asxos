# Session handoff — 2026-09-03 (Amendment H campaign, Waves 2→7)

**Status:** current
**Scope:** Waves 2→7 of the Amendment H campaign — Stages 1→5 machinery, four applied migrations, three defects
**Last verified:** 2026-09-03
**Read priority:** read first
**Superseded by:** N/A

Supersedes `session-handoff-2026-09-02.md` (Waves 0→1) as the newest handoff. `docs/README.md`'s
"read first" pointer still names `session-handoff-2026-08-11.md`; that file is authority-guarded —
the fix is click **H-15**, whose text should now name this handoff.

---

## STOP — read this first: Model A's quarantine (rule #11) stands, untouched

**Nothing this session read `signals` as evidence.** The campaign built seven new domain surfaces
and a decision chain that reaches a delivery receipt, and not one of them touches Model A: no
`signals` query, no `asxos.domain.models` import, grep-pinned in five separate test files
(`test_research_registry.py`, `test_theme_candidates.py`, `test_challenge_rules.py`,
`test_decision_sizer.py`, `test_decision_staging.py`). The `DecisionPacket` contract independently
refuses a manifest naming Model A or `v1_5`.

Rule #11 remains **resolved against Model A** (`docs/model-a-decay-analysis-2026-07-11.md`) and
stands as standing policy for v1_5. It is not lifted, not weakened, and not up for reinterpretation
by anything built here. The one place the word "verdict" now appears in the schema —
`decision_dispositions.verdict` — holds **James's** reading of a packet, not a model's.

---

## What this session was

James's 2026-09-02 instruction, continued: run the Amendment H campaign autonomously —
sequencing delegated to arbi, tier not — plus an explicit in-session I5 grant, "I authorise
you to apply the migrations and then continue the work".

Waves 0 and 1 closed on 09-02. This session ran **Waves 2 through 7** and applied four
migrations under that grant.

## Where the code is

Fourteen draft PRs, one stack, none merged. **Merge in this order** — each is based on its
predecessor, so merging out of order forces rebases:

```
#185 wake + Amendment H          #192 PIT knowledge tier (0049)
 └ #186 backup fix                └ #193 replay + lineage
    └ #189 doc-drift                 └ #194 research registry (0050)
       └ #190 governor drafts           └ #195 theme + candidate engine (0051)
#187 cron health                            └ #196 challenge layer + sizer + staging
#188 0044 header                               └ #197 Stage 4 delivery chain
#191 dependency audit                             └ #198 Stage 5 outcomes (0052)
```

`#190` also carries the ledger, click-list, decision-log and this handoff.

## Migrations — applied and verified

| Migration | Ledger version | Verified |
|---|---|---|
| `0049_pit_knowledge_tier` | `20260902201241` | column + backfill state |
| `0050_research_registry` | `20260902203202` | 4 tables, triggers, CHECKs, FKs |
| `0051_theme_candidates` | `20260902204920` | 2 tables, 2 triggers, FK, 7 indexes, 0 rows |
| `0052_outcome_materialisation` | `20260903025557` | 3 tables, 3 triggers, 3 FKs, unique key, 0 rows |

Every one followed the same four steps: apply → verify at the primary source (`pg_catalog`,
never `information_schema`, which under-reported triggers once during Wave 4) → drop the
`EXPECTED_UNAPPLIED` entry on the carrying branch → record the apply in the migration header.

**`0045_segment_map` was deliberately NOT applied.** Nothing runs `build_segment_map`, it has
no workflow home, and applying it would make its allowlist entry stale and redden the daily
drift check on `main` with no PR in flight to clear it. It stays James's call (C8).

## Catalogue — what exists now that didn't on 2026-09-02

Fourteen diffs is too many to re-read at the next wake, so here is the surface in one place.
**All of it is on branches; none of it is on `main`.**

**Schema — 9 new tables + 1 new column.** Every new table is append-only, enforced by a
`BEFORE UPDATE OR DELETE` trigger, with an authoritative `payload JSONB` and shadow columns for
indexing only (the 0048 pattern).

| Migration | Adds | For |
|---|---|---|
| `0049` | `rs_fundamentals_pit.knowledge_tier` (column) | `filed` vs `estimated`, so replay reads only what was actually known |
| `0050` | `research_hypotheses`, `strategy_versions`, `research_runs`, `research_promotions` | Stage 2 registry — reproducible runs, retained failures, a promotion machine with **no code-reachable path to capital** |
| `0051` | `theme_versions`, `candidate_snapshots` | Stage 3 — a theme and a candidate as evidence, validator-fenced against carrying a recommendation |
| `0052` | `thesis_outcomes`, `delivery_receipts`, `decision_dispositions` | Stage 5 t0 + horizons; and the two delivery ledgers Wave 6 wrongly borrowed from `brief_runs` |

**Domain surfaces — 7 new.**

| Module | What it does |
|---|---|
| `asxos/domain/replay/` | Point-in-time cutoff + lineage resolver; identical hash across two runs |
| `asxos/domain/research/registry/` | Hypothesis / strategy / run contracts, promotion state machine, 12-1 momentum harness |
| `asxos/domain/themes/candidates/` | `ThemeVersion`, `CandidateSnapshot`, deterministic measures, and the **LLM extraction boundary** (tier cap, verb screen) |
| `decision_engine/challenge/` | The 14 ADR §10.4 Layer-1 rules as code + `price_detached`; template-only Layer-2 shell; disposition log |
| `decision_engine/sizer.py` | `inverse_vol_weights` re-homed **by import** behind the challenge gate; zero edits under `domain/portfolio/` |
| `decision_engine/staging.py` | `StagedOrder` — `not_executable: Literal[True]`, lots delegated to `domain/tax/lots.py` |
| `decision_engine/{delivery,outcomes,portfolio_state}.py` | One renderer for CLI and email, content-addressed receipts, t0 + horizon observation, measured book state |

**CLI — 4 new groups:** `asx replay`, `asx research`, `asx candidates`, and `asx decision`
(`build`, `record-t0`, `observe`, `positive-control`, `dispose` — all five personal-use gated).

**Tests:** 2735 → **4219** passed, 1 skipped (the `MIGRATION_TEST_DATABASE_URL` opt-in,
unchanged). ruff and mypy clean throughout.

## Three defects found — all mine, all caught before James ran anything

1. **The min-CGT staging test asserted a wrong number** (Wave 5). It expected the *higher*
   post-discount gain — 6,250 against a true minimum of 5,000 — and passed only because of
   `lots.py`'s partial-draw ordering. `tax-spec-conformance` caught it. Fixture re-based;
   gains now asserted numerically rather than rationalised in a comment.
2. **Decision receipts were written into `brief_runs`** (Wave 6, fixed in Wave 7). The brief's
   `_PRIOR_BRIEF_SQL` takes the newest `brief_runs` row with `as_of < $1` and does not filter
   on row kind, so a receipt was returned as "the prior brief". Fixed at the schema level in
   0052 — receipts and dispositions have their own tables — and pinned with an AST-based test
   that fails if any string literal in the decision engine names `brief_runs` again.

3. **`portfolio_state.py` claimed a firewall it only half had** (Wave 6, fixed after the
   consult). Its docstring said "Every public function checks `ASXOS_PERSONAL_USE`"; that was
   true of two of five loaders. No bypass existed — the other three read prices and candidate
   snapshots, not holdings — but a false defence-in-depth claim is exactly what a later reader
   trusts. `security-engineer` caught it. The three missing gates were added, so the sentence
   became true, rather than the sentence being weakened to match the code; an AST test now
   asserts the property instead of the prose.

The second was found only because a `security-engineer` consult died on a rate limit and left
one unanswered question behind. **A dead agent's last question is still a finding.**

Defects 1 and 3 are the same species: a claim asserted without verifying it. That is why the
session score carries a `repeated_mistake` penalty rather than treating them as two unrelated
slips (`arbi-run-ledger.md`, `close-2026-09-03`).

## What did NOT happen, and why

- **No Stage cell was flipped.** Stage 1's wording is James's ruling (H-23); Stage 3 and 4 need
  live renders (H-27a, H-33b); Stage 4 additionally needs a second governed theme member
  (H-33a) because the only governed theme's sole member, CBA.AU, is a *negative* control by the
  Stage 4 text; Stage 5 is t0 only. Flipping a cell because a work order landed is what
  `roadmap-state.md:58-60` forbids.
- **No live render.** This sandbox holds a `DATABASE_URL` but `asyncpg` cannot complete a
  connection to the pooler (sixth recorded instance). Every live CLI run is a James click.
- **Nothing merged, no secret, no workflow edit, no environment flip, no capital action.**
  Rule #11 untouched: `signals` is never read, grep-pinned in five test files.

## What is waiting on James

`docs/product/james-inbox.md` § Amendment H click-list — **H-01 through H-38**. The queue grew
this session (18 → 38), which is the campaign's honest cost: it converted buildable work into
built work and everything else into a click. The ones that actually gate progress, in order:

1. **H-03** inspect the backup archive, then **H-04/H-05/H-06/H-07** (merge #186, secret,
   workflow patch, dispatch) — red since 2026-08-23 and only you can close it.
2. **Merge the stack** in the order above. Until then this is all inventory.
3. **H-33a** approve a second governed theme member — the true blocker on the Stage 4 positive
   control, and governance rather than code.
4. Rulings, ~15 minutes total: **H-16** dark surfaces, **H-17** CBA thesis #1, **H-23** Stage 1
   cell wording, **H-29a** the two `price_detached` thresholds, **H-29b** a tax-spec amendment
   for lot selection, **H-38** retention/erasure for stored renders.

## Files to commit (Step 4 — reminder, not a push)

A handoff that lives only on a feature branch is a process defect (`docs/README.md`). These are
on **`claude/amendment-h-governor-drafts`** (PR #190) and are seen by the next session only once
they reach `main`:

- `docs/product/roadmap-state.md` — header, Stages annotation, In flight, ranked queue, Last wake snapshot
- `docs/product/arbi-run-ledger.md` — per-wave rows + the scored `close-2026-09-03` row
- `docs/product/decision-log.md` — the D-8 / D-9 row
- `docs/product/james-inbox.md` — click-list H-29 … H-38
- `docs/session-handoff-2026-09-03.md` — this file

Nothing here merges, pushes to `main`, deploys, or migrates. That is `/ship`'s job, done
deliberately.

## Standing lessons from this session

- A shortcut taken to avoid opening a migration is a schema decision in disguise. When a
  migration is coming anyway, the shortcut has no upside left.
- Verify DDL at `pg_catalog`, not `information_schema` — the latter reported zero triggers on
  tables that had them.
- A passing test that encodes a wrong number is worse than no test: it converts an open
  question into a settled falsehood. Assert the arithmetic, don't narrate it.
