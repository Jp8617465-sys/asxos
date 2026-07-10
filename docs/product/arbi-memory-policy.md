# arbi memory policy — layered stores, poisoning defence

**Status:** current
**Scope:** how arbi's persistent memory is structured so authority can't be poisoned by
untrusted input
**Last verified:** 2026-07-10
**Owner:** James (governor)
**Superseded by:** N/A

arbi will read GitHub, PRs, web docs, logs, and other agents' output — **some of it
untrusted.** Anthropic's memory guidance warns that a read-write store can be *poisoned*:
malicious content written into memory is later read back as trusted. The defence is **never
let arbi write to the store it treats as authoritative.** Memory is split by purpose and by
trust, not kept as one blob.

---

## The stores

| Store | Access | Trust | Holds |
|---|---|---|---|
| `asxos-authority-memory` | **read-only** | authoritative | constitution, source hierarchy, non-negotiables, permission tiers |
| `asxos-project-memory` | **read-only** | authoritative | stable repo conventions, known systems, recurring file map |
| `asxos-arbi-working-memory` | **read-write** | untrusted-until-reviewed | run summaries, mistakes, useful patterns, unresolved questions |
| `asxos-dream-candidate-memory` | **read-only after generation** | candidate | dream output awaiting promotion |
| `asxos-approved-learning-memory` | **read-only during normal runs** | authoritative | only promoted lessons that passed the gate |

## The rules

- **arbi never writes to a store it reads as authority.** During normal work it *reads*
  authority/project/approved-learning (read-only) and *writes* only working memory. This is
  the poisoning firewall: even if working memory is corrupted by untrusted input, it is not
  an authority level: it is **untrusted-until-reviewed** and always ranks below repo truth
  (`arbi-authority.md` levels 3–4) and below *approved* memory (level 6). A read from working
  memory is advisory only, never authoritative — it reaches an authoritative store solely
  through the promotion gate.
- **Promotion is the only bridge** from working/dream memory to approved-learning. Nothing
  reaches an authoritative read-only store except through `arbi-promotion-gate.md`.
- **Scope by purpose.** A store holds one kind of thing. No mixing authority with run notes.
- **Condense before full.** Prune/condense working memory before stores fill; a dream can
  consolidate fragmented content into a *separate* output store (never mutating the input).
- **The ladder still governs reads.** Per `arbi-authority.md`, approved memory (level 6) and
  dream memory (level 7) never override repo docs (level 4) or live state (level 3).

## Today vs the platform

**Update (2026-07-10): persistent memory is now git-native** — see
`docs/product/memory/README.md`. The read-only/read-write split is realised by GitHub
**branch protection + CODEOWNERS + path**, a *mechanical* upgrade over a provisioned store
flag (closes part of R5/R7). Managed Agents stores are an optional hosted backend with the
identical split. The paragraph below predates this and describes the platform mapping.


Today arbi has **no persistent memory store** — its "memory" is the git-tracked docs
(`roadmap-state.md` decision log, `arbi-run-ledger.md`, dated handoffs), which are inherently
read-only-until-committed and human-reviewed, so the poisoning surface is minimal. The store
model above maps onto Anthropic **Managed Agents memory stores** (persist across sessions,
mounted into the sandbox, per-store read-only/read-write). Provision them with the
read-only/read-write split above; do **not** collapse them into one read-write store.
