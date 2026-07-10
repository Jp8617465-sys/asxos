# arbi dream policy — the sleep cycle

**Status:** current
**Scope:** how arbi consolidates memory between work cycles, and why a dream is never truth
**Last verified:** 2026-07-10
**Owner:** James (governor)
**Superseded by:** N/A

A **dream is not the agent thinking while it works.** It is a separate memory-consolidation
job that runs *after* the work — arbi's sleep cycle. Per Anthropic's Dreams (research
preview): Claude reflects on past sessions to curate memory and surface insights; a dream
reads an existing memory store **plus 1–100 past sessions** and produces a **new, separate,
reorganised output store** — it does **not** modify the input store, so the output can be
reviewed or discarded.

---

## What a dream may do

Over the last N arbi sessions + current working memory:

- deduplicate overlapping notes
- remove stale conclusions
- find repeated mistakes and name the durable pattern
- extract durable, reusable lessons
- surface contradictions for a human to resolve

Output → `asxos-dream-candidate-memory` (candidate only).

## What a dream may NOT do

- **It is candidate synthesis, not authority.** A dream output (ladder level 7) may **not**
  override `CLAUDE.md`, `docs/README.md`, the latest handoff, live repo state, or the
  constitution.
- **It does not self-promote.** Nothing a dream produces becomes approved memory without
  passing `arbi-promotion-gate.md`.
- **It does not compress away safety.** If consolidation would blur a boundary (rule #11, the
  s766B firewall, the permission tiers), that item is preserved verbatim, not summarised.
- **Partial/failed dreams are archived, not used.** Anthropic notes the output store remains
  available even when a dream fails or is cancelled — so arbi must never promote partial dream
  output. A dream that didn't complete cleanly is archived and ignored.

## Cadence

```
Daily    — write structured run memories (the waking loop → arbi-run-ledger.md)
Weekly   — dream over the last ~10–50 sessions → candidate memory
Monthly  — compare candidate memory against holdout evals; promote if better; archive stale
           working memory
```

## The full loop (where dreams sit)

```
observe → decide → act/delegate → evaluate (arbi-scorecard.md) → write run memory
       → DREAM (consolidate) → promotion gate (evals) → approved memory → better context
```

Learning is mediated through **memory + evaluation**, never by changing model weights. The
dream makes arbi a self-improving operating system rather than a recurring prompt — but only
because it is paired with the scorecard and the promotion gate. Without those, a dream just
launders yesterday's mistakes into tomorrow's context.

## Today vs the platform

**Update (2026-07-10): the dream is now git-native** — `/arbi-dream` reads the committed
artifacts and writes `docs/product/memory/dream-candidates/<date>.md` on a `claude/**`
branch → draft PR; promotion via `/arbi-promote` (a CODEOWNER-reviewed merge). Managed
Agents Dreams is an optional hosted backend. The paragraph below is the platform mapping.


No dream runtime exists in this repo. This policy is the spec for when arbi runs on Anthropic
**Managed Agents** with **Dreams** enabled. Until then, the manual analogue is `/arbi-close`
appending honest run outcomes to the decision log + `arbi-run-ledger.md`, and a periodic human
review that promotes durable lessons — same shape, done by hand.
