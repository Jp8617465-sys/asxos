# Session handoff — 2026-09-03 (Amendment H campaign, Waves 2→7)

**Status:** current · written at campaign close
**Predecessor:** `docs/session-handoff-2026-09-02.md` (Waves 0→1)

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

## Two defects found — both mine, both caught before James ran anything

1. **The min-CGT staging test asserted a wrong number** (Wave 5). It expected the *higher*
   post-discount gain — 6,250 against a true minimum of 5,000 — and passed only because of
   `lots.py`'s partial-draw ordering. `tax-spec-conformance` caught it. Fixture re-based;
   gains now asserted numerically rather than rationalised in a comment.
2. **Decision receipts were written into `brief_runs`** (Wave 6, fixed in Wave 7). The brief's
   `_PRIOR_BRIEF_SQL` takes the newest `brief_runs` row with `as_of < $1` and does not filter
   on row kind, so a receipt was returned as "the prior brief". Fixed at the schema level in
   0052 — receipts and dispositions have their own tables — and pinned with an AST-based test
   that fails if any string literal in the decision engine names `brief_runs` again.

The second was found only because a `security-engineer` consult died on a rate limit and left
one unanswered question behind. **A dead agent's last question is still a finding.**

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

`docs/product/james-inbox.md` § Amendment H click-list — H-01 through H-37. The ones that
actually gate progress, in order:

1. **H-03** inspect the backup archive, then **H-05/H-06/H-07** (secret, workflow patch,
   dispatch) — the backup has been red since 2026-08-23 and only James can close it.
2. **Merge the stack** in the order above.
3. **H-33a** approve a second governed theme member — this is the true blocker on the Stage 4
   positive control, not code.
4. Rulings: **H-16** dark surfaces, **H-17** CBA thesis #1, **H-23** Stage 1 cell wording,
   **H-29a** the `price_detached` thresholds, **H-29b** a tax-spec amendment for lot selection.

## Standing lessons from this session

- A shortcut taken to avoid opening a migration is a schema decision in disguise. When a
  migration is coming anyway, the shortcut has no upside left.
- Verify DDL at `pg_catalog`, not `information_schema` — the latter reported zero triggers on
  tables that had them.
- A passing test that encodes a wrong number is worse than no test: it converts an open
  question into a settled falsehood. Assert the arithmetic, don't narrate it.
