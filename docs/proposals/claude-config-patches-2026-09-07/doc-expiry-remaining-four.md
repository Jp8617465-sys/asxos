# The four remaining expired docs — patch for James, 2026-09-07

**Status:** drafted, **NOT applied.** Each move below requires editing a **deny-listed** file, so
arbi cannot make it (`.claude/settings.json` `permissions.deny`; `authority-guard.sh`
`AUTHORITY_FRAGMENTS` — verified by synthetic payload this session: `docs/README.md` **DENY**,
`.claude/commands/arbi-close.md` **DENY**, `docs/product/north-star.md` **DENY**).
Companion to the E-17 sweep PR, which took `check_doc_expiry.sh` from **25 → 4**. Applying this
takes it to **0**.

## Why these four and not the other 21

The sweep archived the two event records whose referrers were all editable, and allowlisted 19 docs
that inbound references treat as standing sources. These four are genuine event records — but each
is indexed by `docs/README.md`, the docs map. **Moving a file without updating the index that points
at it is how an index rots**, so the move and the repoint must land together, and only you can make
the repoint half.

## The moves

```bash
git mv docs/asxos-live-readiness-audit-2026-07-04.md                     docs/archive/
git mv docs/session-handoff-2026-07-04.md                                docs/archive/
git mv docs/research/claude-fundamentals-audit-handoff-2026-07-04.md     docs/archive/research/
git mv docs/research/repo-navigation-audit-and-plan-prompt-2026-07-04.md docs/archive/research/
```

Destinations follow the existing convention (preserve the relative subpath): `docs/archive/` already
holds six `session-handoff-*.md`; `docs/archive/research/` already holds seven research docs.

## The repoints that must land in the same commit

**1. `docs/README.md`** — four index lines gain the `archive/` prefix:

| Line | Change |
|---|---|
| `:67` | `session-handoff-2026-07-04.md` → `archive/session-handoff-2026-07-04.md` |
| `:89` | `research/repo-navigation-audit-and-plan-prompt-2026-07-04.md` → `archive/research/…` |
| `:90` | `research/claude-fundamentals-audit-handoff-2026-07-04.md` → `archive/research/…` |
| `:91` | `asxos-live-readiness-audit-2026-07-04.md` → `archive/asxos-live-readiness-audit-2026-07-04.md` |

All four already carry a **HISTORICAL** or superseded marker in their index entry, which is the
evidence they are event records; only the path is wrong after the move.

**2. `.claude/commands/arbi-close.md:52`** cites `docs/session-handoff-2026-07-04.md` as the handoff
**format exemplar**. Repoint it to the newest handoff rather than the archive path — an exemplar
should track the current shape:

```diff
-existing handoff format (see `docs/session-handoff-2026-07-04.md`): a `Status: current` /
+existing handoff format (see the newest `docs/session-handoff-*.md`): a `Status: current` /
```

**3. `docs/product/north-star.md:15`** says its claims derive from
`docs/session-handoff-2026-07-04.md` and adds *"If those move, re-derive this."* The file's own
instruction is therefore triggered by this move. Minimum honest edit — update the path and note the
derivation is unchanged:

```diff
-`docs/session-handoff-2026-07-04.md` — not invented. If those move, re-derive this.
+`docs/archive/session-handoff-2026-07-04.md` — not invented. If those move, re-derive this.
+(Path updated 2026-09-__ by an archive move; the derivation itself is unchanged.)
```

## Verify

```
bash scripts/check_doc_expiry.sh   # expect exit 0
git grep -n "session-handoff-2026-07-04\|asxos-live-readiness-audit-2026-07-04" -- ':!docs/archive'
```
The second command should return only the three repointed lines above (plus dated sibling docs that
are themselves archived or allowlisted, which are historical records and correctly keep the old
path in their prose).

## What this does not do

No deletion — `git mv` only, never `git rm`, never a glob (the script's own rule at `:161-164`).
No content edit to any moved doc.
