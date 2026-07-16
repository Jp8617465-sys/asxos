# Security + Performance findings log — the loop's cross-run memory

**Status:** current (append-only; written by the security/perf mission loop)
**Scope:** every finding the every-8h loop surfaces, its severity, and its disposition
**Owner:** the loop appends; James reviews; rows are immutable once written
**Rules:** `security-perf-mission-loop.md`

This is the single pane for "what has the loop found over time" **and** the dedup source
(`security-perf-mission-loop.md` §5). It rides inside each draft PR, so its `main` copy plus
every open PR's copy together form the authoritative history. Do not delete rows.

## Disposition legend

- `drafted` — a draft PR was opened for this finding (link in the row)
- `deduped` — already in flight (an open PR exists); no action this fire
- `deferred` — real but out-of-scope or lower-severity than this fire's pick (reason required)
- `dismissed` — investigated, not a real issue (reason required)
- `heartbeat` — a fire that opened no PR; proves the loop ran (silence ≠ calm)

## Log (append below; newest at bottom)

| Date (UTC) | Fire | Class | Severity | Finding | Disposition | PR / reason |
|---|---|---|---|---|---|---|
| 2026-07-15 | seed | — | — | Log initialized alongside `security-perf-mission-loop.md`. No fire has run yet. | heartbeat | first live fire: next `30 23,7,15 * * *` after enablement |
