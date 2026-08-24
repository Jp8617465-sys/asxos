# asxos: Delivery System Diagnostic

**Prepared:** 23 August 2026
**Scope:** repo-wide analysis of `asxos-main` (781 files, 7.7 MB uncompressed)
**Question posed:** *"We produce a lot of documents but the work gets lost, there's no ticketing system, and we never really produce much code."*
**Method:** static analysis of the uploaded snapshot. No git history was included in the archive, so commit cadence and PR merge rates are inferred from document references rather than measured directly. Every figure below is reproducible from the files as shipped.

---

## Executive summary

**Your diagnosis is half right, and the half that's wrong is the important half.**

You *are* producing code. 32,473 lines of source, 37,142 lines of tests, 43 migrations, 11 CI workflows, roughly 158 PRs. The engineering hygiene is genuinely strong: ruff, mypy and pytest gate every PR, there are zero `TODO`/`FIXME`/`HACK` markers in 32k lines of Python, and the test-to-source ratio is 1.14:1. Most teams would take this codebase.

The problem is not that work gets lost. **The problem is that you already built a ticketing system, in prose, and prose cannot hold state.**

There are eight competing backlog documents. The nominated "single live queue" is a 145 KB markdown file. Four of the other seven carry hand-written banners reading `⚠️ NOT A QUEUE` pointing back at it. 42% of all documents contain the word `SUPERSEDED`. There are 562 occurrences of `STALE`. There is a 56 KB document, `doc-truth-map-2026-08-13.md`, whose entire purpose is to track which of your other documents are still true.

That last artifact is the diagnosis in one file. When a system needs a document to track the truth-status of its documents, the documentation layer has stopped serving the product and become the product.

The felt experience of "we never produce much code" is real, but it is a **ratio** problem, not a **volume** problem. For every line of source you ship, you write 1.78 lines of prose. And unlike code, that prose has no compiler, no type checker, and no test suite. Consistency across 269 documents can only be restored by hand, so you periodically spend entire sessions on reconciliation sweeps (`SB0-01`, `SB0-02`) that produce zero executable output.

**The recommendation is not to build a ticketing system. It is to stop maintaining the one you have and switch to GitHub Issues, which you already pay for, already reference in `/sprint-state`, and already have CLI access to from Claude Code.**

---

## Exhibit 1: The production ratio

| Layer | Files | Lines | Notes |
|---|---|---|---|
| Markdown (docs + `.claude`) | 269 | 57,945 | 573,092 words ≈ 1,150 printed pages |
| Python source (`asxos/`) | 170 | 32,473 | |
| Python tests (`tests/`) | 128 | 37,142 | healthy 1.14:1 vs source |
| SQL migrations | 43 | — | |

**Prose-to-source ratio: 1.78 : 1.**

Total documentation on disk is 3.9 MB. Total source is 1.8 MB. You have written more than twice as much English as Python.

For calibration: 573,092 words is longer than *War and Peace*. It was written in roughly 90 days.

## Exhibit 2: Production is accelerating, not stabilising

Dated documents created per month:

| Month | New dated docs |
|---|---|
| June 2026 | 6 |
| July 2026 | 44 |
| August 2026 (22 days) | 54 |

August is running at **2.45 new documents per day**. This is the signature of a system where writing is the path of least resistance and the cost of a new document is perceived as near zero. It is not near zero: each new document creates an update obligation against every prior document it touches.

## Exhibit 3: Eight backlogs, therefore zero backlogs

| Document | Lines | Self-declared status |
|---|---|---|
| `docs/product/roadmap-state.md` | 1,686 | "the single live queue" |
| `docs/next-session-backlog.md` | 444 | "⚠️ NOT A QUEUE" |
| `docs/maintenance/guards-backlog.md` | 439 | living, `last_updated: 2026-05-28` |
| `docs/product/arbi-operating-backlog.md` | 140 | "⚠️ NOT A QUEUE" |
| `docs/product/cleanup-backlog.md` | 69 | "⚠️ NOT A QUEUE" |
| `docs/executable-roadmap-2026-07-04.md` | — | superseded |
| `docs/archive/backlog-test-coverage.md` | — | archived |
| `asxos/secondbrain/roadmap.py` | — | roadmap logic in *code* |

The supersession banners are evidence that you have already diagnosed this correctly and applied the only fix prose allows: writing more prose. It doesn't hold, because it requires a human to remember to update N documents every time one changes.

The nominated single queue, `roadmap-state.md`, has a status header that is itself fifteen lines of nested corrections about corrections, including one noting that a prior standing correction was reversed by PRs #144/#142/#141.

## Exhibit 4: Document status fields are unreliable in both directions

This is the load-bearing finding. Spot-checking proposals marked "NOT yet built" against the source:

| Proposal | Doc says | Code says |
|---|---|---|
| `multi-instrument-expansion-2026-07-11.md` | "NOT yet built" | **Shipped.** `_TYPE_TO_KIND` in `asxos/ingestion/universe.py` maps ETF/FUND/Preferred/Notes/BOND; `migrations/0037_security_kind.sql` exists; the code comments cite "proposal §7.3" |
| `thesis-coverage-framework-2026-07-11.md` | "NOT yet built" | **Substantially shipped.** `asxos/domain/theses/` carries 1,165-line `service.py`, plus `discipline.py`, `trajectory.py` |
| `portfolio-team-visibility-2026-07-12.md` | "NOT yet built" | **Genuinely not built.** No source or migration hits |

You cannot determine what is done by reading the documents. You can only determine it by reading the source. **That is the precise mechanism by which work "gets lost"** — not deletion, but the loss of any trustworthy index into what exists.

Note the direction of the error on row 1: you personally asked for ETFs, a proposal was written, the feature was *built*, and the document still says it wasn't. Work isn't disappearing into a void. It's disappearing into a filing system that doesn't know it arrived.

## Exhibit 5: The session-handoff tax

16 `session-handoff-*.md` documents, 153,668 bytes total, averaging 9.6 KB each.

Each session opens by reading the previous handoff and closes by writing the next. That is a fixed cost on both ends of every working session, and it compounds: handoffs increasingly summarise other handoffs rather than describing the system.

This artifact exists only because state lives in prose. If state lived in issues, the handoff would be one command.

## Exhibit 6: Context budget crowded out before work begins

| Surface | Bytes |
|---|---|
| 26 agent definitions (`.claude/agents/`) | 113,197 |
| 33 slash commands (`.claude/commands/`) | 89,500 |
| `docs/product/roadmap-state.md` | 145,585 |
| `CLAUDE.md` | 24,712 |
| Other governance markdown | ~50,000 |
| **Total** | **423,120 (~106,000 tokens)** |

Even on a 1M-token context, that is a large share of attention spent on process before the model reads a line of the problem. On a 200k context it is more than half the window.

26 agents and 33 commands is more standing process than most 20-person engineering organisations run. The `arbi-run-ledger.md` already records a `KNOWN COVERAGE GAP` admitting its own core invariant ("every arbi run leaves a row here") is not satisfied, which suggests the machinery has outgrown the ability to operate it.

## Exhibit 7: What is actually healthy (do not break these)

- **CI is real.** `full-check.yml` runs ruff, mypy and the full pytest suite on every PR and push. Ten other workflows cover ML tests, migrations, backup, PR review.
- **Zero code debt markers.** No `TODO`, `FIXME`, `HACK` or `XXX` anywhere in `asxos/`, `jobs/` or `scripts/`. Genuinely unusual.
- **Test discipline.** 128 test files, more test lines than source lines.
- **Clean domain structure.** `asxos/domain/` is properly separated into bounded contexts (theses, themes, screening, portfolio, decision_engine, results_review).
- **Doc craft is high.** Status, Owner, Scope, Last verified and Superseded-by fields on most documents. The failure is not carelessness. It is that careful prose does not scale to 269 interdependent files.

**The debt has been fully displaced from the code layer into the documentation layer.** Zero TODOs in the source, 562 STALE markers in the docs.

---

## Diagnosis: three mechanisms

**1. No addressable unit of work.**
A task exists as a paragraph inside a 145 KB file. It has no ID, no state field, no owner field, no created-date, and no query interface. You cannot ask "what is open?" You can only read. Reading does not scale; querying does.

**2. Supersession is manual, and its cost is quadratic.**
Every new document creates an obligation to update every prior document it contradicts. With 269 documents that obligation is unpayable, so it is paid in periodic reconciliation sweeps that consume whole sessions and ship nothing. `doc-truth-map-2026-08-13.md` (56 KB) is the monument to this.

**3. Deliberation has no exit condition.**
Nine proposals sit in `docs/proposals/` still marked proposed or unauthorised, several six weeks old. `finance-red-team-2026-08-08-appendices.md` alone is 258 KB. Nothing forces a proposal to terminate in either a merged PR or a deletion, so the natural resting state of an idea is "well-documented and not built."

---

## Recommendations

Ordered by impact-to-effort. R1 through R3 are the intervention; R4 onward is consolidation.

### R1. GitHub Issues becomes the sole system of record for actionable work
**Effort: 1 day. Impact: high.**

You already have this. `/sprint-state` already calls `gh issue list` — as step 5 of 5, an afterthought. Promote it to step 1 and make it authoritative.

The rule, enforced in `CLAUDE.md`:

> An item of work is actionable **only** if it is an open GitHub Issue. Documents may describe, argue and record. Documents may not hold state.

Why GitHub Issues over Linear or Jira: zero migration, already provisioned, and `gh` CLI is directly drivable by Claude Code without an MCP connector. If you later want better UX, Linear has an MCP and the migration path from Issues is trivial. Do not evaluate tools now; that is another document.

**Bootstrap:** one session, read `roadmap-state.md` Stages 0→6 and the nine open proposals, emit one Issue per actionable item with a link back to the source document. Expect 40 to 80 issues. Then freeze `roadmap-state.md` read-only.

### R2. Retire seven of the eight backlogs
**Effort: 2 hours. Impact: high.**

Delete `next-session-backlog.md`, `arbi-operating-backlog.md`, `cleanup-backlog.md`, `executable-roadmap-2026-07-04.md`. They already declare themselves not-queues. Keeping them costs reading time and creates the risk of acting on a stale ranking.

`guards-backlog.md` is capital-adjacent and should convert to labelled Issues (`guard`, `p0`) rather than being deleted.

`roadmap-state.md` becomes a **generated** artifact: a weekly `gh issue list` dump, not a maintained document. Generated files never go stale, because nobody is asked to remember them.

### R3. Kill the session handoff
**Effort: 0. Impact: high, compounding.**

Once state is in Issues, the handoff is:

```bash
gh issue list --state open --label in-progress
gh pr list --state open
```

Permit at most a 10-line `docs/WHERE-I-STOPPED.md`, overwritten each session, never dated, never archived. Ban new `session-handoff-*.md` files. This recovers a fixed tax at both ends of every session and stops the archive growing.

### R4. Split documentation into two classes with different rules
**Effort: 1 day to reclassify. Impact: high, structural.**

The O(N²) update problem exists because documents are treated as living. Most should not be.

**Class A — Decision records. Immutable.**
Dated, written once, never edited. A later decision supersedes an earlier one by *reference*, not by editing the earlier file. Standard ADR pattern. This eliminates the update obligation entirely: a 2026-07-11 record is always a true statement about 2026-07-11.
Everything in `docs/proposals/` and every audit becomes Class A.

**Class B — Living references. Few, small, owned.**
Hard cap: **five documents.** Candidates: `README.md`, `CLAUDE.md`, `target-architecture.md`, a runbook, and the generated queue view. Each has a named owner and a review date. Anything else that wants to be living must displace one of the five.

Everything currently living that is neither → `docs/archive/` or delete. Files with a `SUPERSEDED` banner and no unique content should be deleted, not archived. The archive is where you put things you might need; 36 files is already more than you will ever revisit.

### R5. Cut the governance surface by 60%
**Effort: half a day. Impact: medium-high.**

26 agents and 33 commands is unsustainable for a solo operator plus agents. Instrument first, then cut: log which commands are actually invoked over two weeks, retire everything with zero invocations.

Target: **8 agents, 10 commands.** Bias toward keeping the ones that produce artifacts (`/ship`, `/thesis`, `/arbi-run`) over the ones that produce assessments (`/pm-review`, `/quality-check`, `/health-check`), since assessment commands are the ones that generate documents.

Expected recovery: roughly 60,000 tokens of context per session, spent on the problem instead of the process.

### R6. Definition of done is a merged PR
**Effort: 0. Impact: high, cultural.**

Write it into `CLAUDE.md` explicitly:

> A proposal is not progress. A plan is not progress. An audit is not progress. Progress is a merged PR or a closed Issue. A session that produced neither produced nothing, regardless of how much was written.

This is the single line most likely to change behaviour, because the current implicit scoring function rewards document production and the felt sense that "we never produce much code" is the direct output of that mismatch.

### R7. WIP limits
**Effort: 0. Impact: medium.**

- **Maximum 3 open proposals.** A fourth cannot be started until one is merged, converted to Issues, or deleted.
- **Maximum 1 new document per session.** Forces the question "does this need to be a document, or is it an Issue comment?" The honest answer is usually the latter.
- **Proposals expire at 30 days.** An unbuilt 30-day-old proposal is auto-deleted. If it mattered, it will be rewritten; if it doesn't get rewritten, it didn't matter. Nine proposals currently fail this test.

### R8. Retire the reconciliation sweep
**Effort: 0. Impact: medium.**

`SB0-01` and `SB0-02` style doc-truth sweeps are pure maintenance of a substrate you are about to abandon. Once R1 through R4 land, do not run another one. `doc-truth-map-2026-08-13.md` should be deleted rather than updated. Nothing downstream should depend on it.

---

## 30 / 60 / 90

**Days 1–30: convert**
- R1 Issues bootstrap (one session, 40–80 issues)
- R2 delete redundant backlogs, freeze `roadmap-state.md`
- R3 ban new handoffs
- R6 the definition-of-done line into `CLAUDE.md`
- *Exit test:* you can answer "what's next?" in one command, with no file open.

**Days 31–60: consolidate**
- R4 reclassify docs; enforce the five-document living cap
- R5 instrument then cut agents and commands
- R7 WIP limits active
- *Exit test:* living documents ≤ 5; `SUPERSEDED` count falling, not rising.

**Days 61–90: verify**
- R8 no reconciliation sweeps run
- Measure prose-to-source ratio; target below 0.5:1
- *Exit test:* three consecutive weeks where every session closed with a merged PR.

---

## What not to do

**Do not build a custom tracking system.** `asxos/secondbrain/roadmap.py` suggests the instinct exists. Resist it. A bespoke tracker is another artifact to maintain, and the failure mode you have is *too many maintained artifacts*.

**Do not run a documentation audit to fix the documentation.** That is what `doc-truth-map` was, and it is 56 KB. Cut, don't reconcile.

**Do not touch the code layer.** Test coverage, CI gates and module boundaries are all healthy. There is a real risk of an improvement programme wandering into the codebase because the codebase is more pleasant to work on than the filing cabinet. The codebase is not the problem.

**Do not write a plan for this plan.** If a document is produced in response to this report, the pattern has reasserted itself. The first action is a terminal command, not a file.

---

## Metrics

Track four numbers weekly. All are one command.

| Metric | Now | 90-day target |
|---|---|---|
| Prose-to-source line ratio | 1.78 : 1 | < 0.5 : 1 |
| Living documents | ~162 | ≤ 5 |
| `SUPERSEDED` + `STALE` occurrences | 860 | < 50 |
| New docs per working day | 2.45 | < 0.3 |

```bash
# prose-to-source ratio
echo "scale=2; $(find docs .claude -name '*.md' -exec cat {} + | wc -l) / $(find asxos -name '*.py' -exec cat {} + | wc -l)" | bc

# decay markers
grep -rio "SUPERSEDED\|STALE" docs/ | wc -l
```

---

## The one-line version

You did not fail to build a ticketing system. You built an extremely sophisticated one out of a material that cannot hold state, and you are now paying more to maintain it than it returns. Move state into GitHub Issues, make documents immutable records rather than living truth, and let the codebase — which is in good shape — go back to being the point.
