# AGENTS.md — Cursor mirror of the asxos harness

Cursor Cloud Agents do not load `.claude/settings.json` allow/deny or this
repo's Claude hook fence (`docs/product/risk-register.md` **R17**). This file
is the prompt-layer mirror. It is **not** mechanical. Operating SoT:
`docs/product/harness-profiles.md`.

## I5 / I6 — hard stop

Do not: migrations (including `0042`), production DB writes, secret creation,
`.env` credential reads, merge, deploy, push to `main`, mark a PR ready,
enable auto-merge, capital / Model A for capital, authority-file enactment.

Draft PR on `cursor/**` or `claude/**` is the stopping point.

## Two-speed routing

| Shape | Route |
|---|---|
| One file / same-file / tiny sequential | `/build` |
| Multi-node reversible, 1–2 PRs | `/arbi-mission` |
| Large parallel | `/arbi-team` only if team-shaped |

A subagent cannot spawn subagents. Fan out from the main loop. Roster:
`docs/product/harness-profiles.md`.

## Consult is risk-tiered

Not a mandatory three-agent review. Tiers A/B/C are in
`docs/product/harness-profiles.md`.

## Out-of-fence red-team is not a vet

See `arbi-evals.md` G8. Re-vet in-fence, or surface for James.

## Read first

`CLAUDE.md` → `docs/product/harness-profiles.md` → newest `docs/session-handoff-*.md`.
