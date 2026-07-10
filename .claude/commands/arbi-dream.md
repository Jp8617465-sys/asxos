# arbi dream — memory consolidation — `/arbi-dream`

No arguments. arbi's **sleep cycle**: consolidate the week's committed artifacts into a
*candidate* lesson set. A dream never mutates its inputs and is **never authoritative** —
it produces a candidate that only becomes memory via `/arbi-promote` (a reviewed PR merge).
Git-native (`docs/product/memory/`); the Managed Agents Dreams feature is an optional
backend, not required. See `arbi-dream-policy.md`, `arbi-memory-policy.md`.

## Why a command (not the agent)

A subagent can't fan out or open a PR; the main loop can. `/arbi-dream` reads the artifacts,
dispatches a consolidation agent, and writes one candidate file on a branch → draft PR.

## Step 1 — Gather the committed inputs (read-only)

Read, capturing each by commit SHA for provenance (the git equivalent of "reads N past
sessions"): the newest `docs/session-handoff-*.md`; `docs/product/decision-log.md`;
`docs/product/arbi-run-ledger.md`; `docs/product/risk-register.md`;
`docs/product/roadmap-state.md`; and `docs/product/memory/working/*.md` written since the
last dream. Never edit any input.

## Step 2 — Dispatch the consolidation

Dispatch an agent (e.g. `technical-writer` for phrasing, or the main loop) to apply the
`arbi-dream-policy.md` rules: **dedupe** overlapping working notes (list merged run_ids);
**drop stale** conclusions (a newer, higher-ladder artifact supersedes — list them, don't
silently delete); **name repeated mistakes** (≥2 occurrences → a durable pattern);
**extract durable lessons** (each with an evidence citation — ledger row / `file:line`);
**surface contradictions** vs `docs/README.md`/newest handoff **for James** (never
auto-resolve — a level-7 dream can't adjudicate a level-4 conflict); **carry safety
verbatim** (rule #11, s766B firewall, permission tiers — never summarised).

## Step 3 — Write ONE candidate file (on a branch)

Create `docs/product/memory/dream-candidates/YYYY-MM-DD-dream.md` with the frontmatter
shape from `arbi-dream-policy.md`: `status: candidate`, `completed: true` (a partial/failed
dream MUST set this false/absent → it is archived, never promoted), `window`, `inputs` (the
SHAs), then the sections: Durable lessons (each with `proposed_target` =
`approved-lessons.md` | `project-facts.md` | a governance-doc PR→James), Repeated
mistakes, Stale conclusions to retire, Contradictions for James, Safety carried verbatim,
Dedup log. Commit on a `claude/arbi-mem/YYYY-MM-DD` branch.

## Step 4 — Open a docs-only DRAFT PR

Open a draft PR carrying the candidate. Do **not** merge, do **not** touch
`approved-lessons.md` (that's promotion). Report the PR to James.

## Boundaries

- Writes only `dream-candidates/` on a `claude/**` branch — never `main`, never
  `approved-lessons.md`/authority files, never a merge (the unattended-guard hook enforces
  this mechanically when scheduled).
- Candidate ≠ truth: a dream (ladder 7) never overrides repo docs (4) or live state (3).
- Partial/failed dream → `completed:false` → archived, not promoted.
