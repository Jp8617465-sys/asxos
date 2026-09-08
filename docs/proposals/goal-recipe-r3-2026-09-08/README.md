# Goal recipe R3 — the autonomy-evidence window (2026-09-08)

Staged, not applied. `docs/product/arbi-goal-recipes.md` is a fenced authority path
(`.claude/settings.json:97` denies `Edit`; `.claude/hooks/authority-guard.sh:69`;
`asxos/backlog.py:94`), and `AGENTS.md` §8 permits an agent to draft a change to an
authority file but never to land it. Same shape as `fence-integrity-2026-09-06/`: the
diff is authored and verified; applying it is James's step.

## What it adds

One recipe, R3, and one recipe rule. Nothing in R1/R2 is edited.

**The goal it encodes** — the plan's own promotion bar (§13) and `AGENTS.md` §10's
Green-earning evidence, stated as an observed outcome with a counter:

> 20 consecutive low-risk product slices move from admitted contract → Claude patch →
> external exact-SHA check → landing → observed product outcome, with zero James clicks,
> zero boundary escapes, and zero fuse trips.

The recipe defines what counts as a slice (admitted `#204` sub-issue with a product-facing
outcome; landed through the `P9` exact-SHA check; observed; zero clicks; consecutive), states
that the count lives on Issue `#204` and nowhere in Markdown/YAML (`AGENTS.md` §11), and
records the measured state at launch: **0/20, cannot yet increment** — `AUTONOMY` absent,
`asxos-control` absent, no App-owned check (`#205` findings). Every R3 window therefore
advances the plan's §23.8 preconditions in order; the launch block lists them.

**Rule 6** records that `AGENTS.md` binds where R1/R2 wording (which still names Render)
differs. It is a clarification, not a boundary change: a recipe can only narrow `AGENTS.md`.

## Applying

```sh
git apply --check docs/proposals/goal-recipe-r3-2026-09-08/arbi-goal-recipes-R3.patch
git apply         docs/proposals/goal-recipe-r3-2026-09-08/arbi-goal-recipes-R3.patch
scripts/check_doc_expiry.sh
make check
```

Then, so the count has a home before the first window: add a `## Autonomy counter`
line to the body of Issue `#204` reading `0/20 — cannot increment until P9 observed and
AUTONOMY=STANDING attested`. The recipe forbids tracking it anywhere else.

The patch was generated from a scratch copy of the recipe file (`diff -u`) and verified
with `git apply --check` against `main` at the commit named in this directory's PR. The
fenced file was not opened for writing.

## Launching

Paste the R3 `/goal` block from the applied recipe verbatim, per
`docs/product/runbooks/reversible-work-window.md` step 6. The executor model is a launch
parameter, not part of the envelope. The first open step at launch is expected to be
step 2 (Phase-0 verdict) or the JAMES_NEEDED pivot from step 1, since F-E2E r1's positive
control is one James-authored thesis away (`e2e-run-findings-2026-09-07.md`).

## Out of scope, observed

- R1's "no raw Render mutation" and rule 5's "PR 7b preconditions" predate `AGENTS.md`.
  Rule 6 makes `AGENTS.md` win rather than rewording them; a rewrite is its own change.
- `runbooks/reversible-work-window.md` still says "R1 or R2" at step 2; it should read
  "R1, R2 or R3" once this lands. Not patched here — the runbook is not fenced and the
  one-line edit can ride the same PR James applies this in.
