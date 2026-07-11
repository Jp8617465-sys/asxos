# arbi memory — the second brain (git-native)

**Status:** current
**Scope:** arbi's persistent memory, implemented in git (Claude Code) — Managed Agents optional
**Last verified:** 2026-07-10
**Owner:** James (governor) via CODEOWNERS; arbi writes only candidates/working on branches
**Superseded by:** N/A

arbi has no trained weights and (in Claude Code) no managed memory store — its memory **is
these git-tracked files**. Trust isn't a store flag; it's reconstructed from three things:
**which branch** a file lives on (`main` = protected/authoritative; `claude/**` =
untrusted-until-reviewed), **which path** it sits at, and **who can merge it** (CODEOWNERS —
arbi cannot self-approve). The invariant: **write-authority is inversely proportional to
trust.** arbi freely writes the least-trusted layers; it can never *directly* write the
most-trusted ones. The PR-merge-to-`main` is the only ratchet upward — the mechanical
realisation of `arbi-memory-policy.md`'s poisoning firewall (a mechanical upgrade over
today's prompt-only enforcement, risk R5/R7).

---

## The map (store → file → ladder → trust)

| Layer | Git path | Ladder | Lives on | Trust | Content |
|---|---|---|---|---|---|
| authority | `authority-lessons.md` | 2 | `main` (protected) | authoritative | **pointer** → governance set + CLAUDE.md |
| project facts | `project-facts.md` | 4 | `main` (protected) | authoritative | **pointer** → CLAUDE.md, docs/README, rules |
| audited run history | `../decision-log.md`, `../arbi-run-ledger.md`, `../risk-register.md`, `../roadmap-state.md`, `../../session-handoff-*.md` | 4–5 | `main` (protected) | authoritative, James-audited | already exists — the committed ledgers |
| approved learning | `approved-lessons.md` | 6 | `main` (protected) | authoritative | promoted arbi lessons only |
| dream candidate | `dream-candidates/*.md` | 7 | `claude/**` (in a PR) | candidate | dream output awaiting promotion |
| working | `working/*.md` | 8 | `claude/**` (in a PR) | untrusted-until-reviewed | raw per-run notes |

`authority-lessons.md` and `project-facts.md` are **pointer indexes, not copies** — the real
authority already lives in the governance files; duplicating it would create a second
editable copy (a poisoning surface). `approved-lessons.md` is the only layer that accretes
genuinely new knowledge. Working memory is **one append-only file per run** (conflict-free
across parallel branches; mirrors `migrations/` + dated handoffs).

## Read/write discipline (the one rule)

**arbi writes only to `claude/**` branches, and only into `working/` and `dream-candidates/`.
Everything on protected `main` (levels 2–6) changes only through a reviewed merge.**

- **Scheduled unattended (PR 7a, today):** reads all; writes **nothing** (output-only brief).
- **Scheduled unattended (PR 7b, gated):** writes `working/<run>.md` + weekly
  `dream-candidates/<date>.md` on a branch → **draft PR**; never `main`, never
  `approved-lessons.md`, never a merge.
- **Interactive `/arbi` / `/arbi-close`:** appends `working/*` + ledgers on a branch; James
  commits/merges.
- **Promotion (`/arbi-promote` / review):** appends `approved-lessons.md` on `main` **via
  reviewed merge only** (CODEOWNERS → James).

## Wake read-order (authority ladder — higher wins)

L0 James's instruction · L2 `authority-lessons.md` (→ real governance files win) · L3 live
snapshot · L4 `docs/README`, newest handoff, `project-facts.md` · L5 the ledgers
(**`decision-log.md` first** — did the last "one thing" hold up?) · L6 `approved-lessons.md`
· L7 open `dream-candidates/*` (advisory, never overrides repo truth) · L8 `working/*`.

A lower level never overrides a higher one: a dream (L7) saying "Phase 2c unblocked" loses to
a handoff (L4) still listing it blocked.

## Mechanical enforcement (the git firewall)

`.github/CODEOWNERS` makes **James the required reviewer** of `approved-lessons.md` +
`authority-lessons.md` + `project-facts.md` + every `arbi-*.md`. With branch protection on
`main` (require PR + `full-check` green + CODEOWNERS approval; no direct pushes; arbi's
identity cannot self-approve), promotion becomes a merge arbi **cannot perform on itself** —
the git form of I6 "never standing" and the promotion gate's "grader ≠ producer."
Branch-protection setup is a James/`backend-architect` action (a repo-config change), tracked
alongside the read-only-DB-role work (R2/R5).
