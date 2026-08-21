# Arbi second-brain pattern review: LLM knowledge bases

**Status:** reviewed pattern input; accepted only through the amendments named below
**Prepared:** 2026-08-12 (Australia/Brisbane)
**Mission:** `arbi-second-brain-karpathy-pattern-review-2026-08-12`
**Observed base:** `claude/arbi-outcome-second-brain-plan@f4ea38f`
**Source evaluated:** the verbatim "LLM Knowledge Bases" excerpt supplied by James in the mission
prompt; [author profile](https://x.com/karpathy) supplied for attribution; canonical post URL not
provided or independently verified in this docs-only mission
**Authority ceiling:** docs-only analysis; no implementation or permission authority

## 1. Verdict

**ADAPT the knowledge-compilation pattern, not the personal tool stack.**

The article validates several choices already present in Arbi: Markdown as a durable substrate,
LLM-assisted consolidation, compact indexes, derived outputs that add to future context, and
periodic integrity checks. It also exposes useful gaps in the current plan: source material and
generated knowledge views need an explicit trust boundary; compiled views need rebuildability and
provenance; query outputs need a controlled filing route; and knowledge health checks should be
executable.

ASXOS should not copy a generic `raw/` and `wiki/` hierarchy into the repository. It already has an
authority ladder, canonical product documents, financial evidence contracts, git-native memory,
and a promotion firewall. A parallel wiki could launder an LLM summary into apparent authority and
recreate the duplicate-truth problem the second-brain programme is meant to remove.

The useful pattern folds into existing `SB0`, `SB2`, `SB3`, `SB4`, and `SB5`. It creates no new
programme mission, queue, permission, service, or runtime dependency.

## 2. Pattern-to-ASXOS comparison

| Article pattern | Current ASXOS position | Decision | Why |
|---|---|---|---|
| Collect source documents into a raw corpus | ASXOS has canonical repo sources, live observations, retained history, and the target `EvidencePacket`; it does not have one generic knowledge-ingest directory | `ADAPT` | Preserve each source in its correct authority/evidence system. Add source identity and manifest references, not a duplicate corpus |
| Incrementally compile a Markdown wiki | Git-native memory already uses Markdown pointer indexes, working notes, dream candidates, and approved lessons | `ADAPT` | Generated concept/index pages can be rebuildable retrieval views, never a new authority layer |
| Categorise concepts, link articles, and maintain backlinks | Pointer indexes exist, but backlinks and generated concept relationships are not systematic | `KEEP` | Backlinks and compact concept indexes can improve retrieval and contradiction detection without changing authority |
| Ask complex questions against a modest Markdown corpus | Arbi and Claude can search files, but context selection is manual and often loads oversized state documents | `KEEP` | This directly supports the planned `ContextManifest` and file-backed-first retrieval approach |
| File useful answers back into the knowledge base | Working memory and dream candidates already provide non-authoritative write destinations | `ADAPT` | A query output may enter working memory or become a dream candidate; it cannot update approved truth directly |
| Render Markdown, slides, and images as durable outputs | Markdown reports and briefs already exist; richer views are not the current bottleneck | `KEEP` for Markdown; `DEFER` richer formats | Output must name a consumer and preserve source links. Slides/images are optional presentation, not memory truth |
| Run LLM health checks for inconsistency and missing data | Contradiction detection and executable evals are planned but largely manual today | `KEEP` with constraints | Detect missing or inconsistent data, but never silently impute a material fact. Missing remains explicit until sourced |
| Add a small search engine and CLI | Repository search is adequate for many current questions; SB3 has not yet measured retrieval failure | `DEFER` | Build only after context-manifest evals show a named query class cannot meet recall/latency/citation targets |
| Use Obsidian as the frontend | All proposed artifacts are ordinary Markdown | `OPTIONAL` | Obsidian may view the files locally, but cannot be a runtime, storage, or authority dependency |
| Generate synthetic data and fine-tune on the corpus | No retrieval baseline, eval set, or source-safe training corpus exists | `REJECT FOR NOW` | Weights obscure source freshness and provenance; file-backed retrieval is cheaper, reversible, and auditable at current scale |

## 3. Trust-preserving architecture

```text
authoritative repo sources + admitted live observations + external source artifacts
  -> source manifest (identity, origin, observed_at, rights, content hash)
  -> rebuildable compiled views (index, concept page, backlinks, concise summary)
  -> ContextManifest for one mission or question
  -> answer/report with claim-level citations
  -> optional working-memory record or dream candidate
  -> independent eval and promotion gate
  -> approved lesson only after James-controlled review
```

### 3.1 Source is not view

A source artifact is retained evidence. A compiled page is a disposable view over named sources.
Deleting and rebuilding every compiled page from the same source manifest should preserve its
material claims. If it cannot be rebuilt, it is unmanaged prose rather than a trustworthy view.

Every generated current claim needs:

- source identity and exact location or content hash;
- generator/prompt/version identity where an LLM contributed;
- generated and source observation times;
- confidence and explicit unavailable/conflict state;
- freshness or recheck condition;
- predecessor/supersession identity; and
- authority classification.

Generated views remain below live observations and canonical repo documents under
[`arbi-authority.md`](../product/arbi-authority.md). Their prose never upgrades the authority of
their inputs.

Until `SB0` ratifies any different path, a persisted compiled view is a `working_output`: it may be
written only under the existing `docs/product/memory/working/` path on a `claude/**` branch and is
ladder-8, untrusted-until-reviewed. Committing it does not promote its claims. A dream may derive a
candidate from it; promotion still follows the existing candidate and approved-memory paths. An
LLM-generated view must not be placed among ordinary canonical product docs where its path could
make it appear to be level-4 project truth.

### 3.2 Product evidence is not knowledge convenience

Financial facts admitted to an investment case still pass the point-in-time evidence contracts in
`target-architecture.md` and the adopted decision engine. A convenient knowledge page cannot
substitute for `EvidencePacket`, source cutoff, citation, Decimal, licensing, or challenge gates.
The knowledge layer helps find and explain evidence; it does not admit evidence into a decision.

### 3.3 Query output is not approved memory

Useful Q&A should be durable when it has future value, but its first destination is an untrusted
working record. Repeated, outcome-supported lessons may become dream candidates. Promotion remains
the only bridge to approved learning under
[`arbi-memory-policy.md`](../product/arbi-memory-policy.md) and
[`arbi-promotion-gate.md`](../product/arbi-promotion-gate.md).

## 4. Minimum amendments adopted

The main programme is amended without adding backlog IDs:

- `SB0` classifies source artifacts, compiled views, working outputs, dream candidates, and
  approved memory as distinct trust roles.
- `SB2` treats current projections, indexes, summaries, and backlinks as rebuildable views and
  detects stale or unsupported compiled claims.
- `SB3` defines the `ContextManifest` as a compiled retrieval view, with claim/source coverage and
  retrieval evaluation before custom search infrastructure.
- `SB4` adds provenance, broken-link, stale-view, unsupported-summary, and silent-imputation
  fixtures.
- `SB5` sends filed Q&A through working memory, observed outcomes, holdout evaluation, and the
  independent promotion gate.

No directory layout, plugin, search service, vector database, knowledge graph, image pipeline, or
fine-tuning work is approved by this review.

## 5. Knowledge health checks

The first implementation should be deterministic where possible:

1. every generated page resolves all declared source references;
2. every material current claim has at least one admissible source;
3. no source is represented by two conflicting current summaries without an explicit conflict;
4. no generated view is newer than its source manifest while still carrying a stale digest;
5. removed or superseded source identities invalidate dependent views;
6. missing data remains `unavailable` or `conflict`, never an LLM-imputed fact;
7. backlinks are reciprocal where the schema requires them;
8. a context manifest covers all required mission inputs and excludes irrelevant authority levels;
9. answers cite the exact compiled view and underlying source; and
10. a candidate answer cannot write directly to approved memory.

LLM review may suggest missing links, concepts, or research questions. Deterministic checks and
source review decide whether the resulting view is valid.

## 6. Deferred capability gates

Custom search, embeddings, vector retrieval, knowledge graphs, or a web UI become eligible only if
file-backed retrieval is measured against a versioned query set and fails a named target such as:

- required-source recall;
- claim citation coverage;
- stale-source rejection;
- context size or latency; or
- repeated inability to answer a named product/mission question.

Fine-tuning is rejected under the current Arbi architecture: `arbi-dream-policy.md` defines
learning as memory plus evaluation, never weight changes. Reconsideration requires an explicit
James-approved policy amendment plus a separate rights, poisoning-threat, holdout-evaluation,
update, rollback, freshness, and source-citation case. Retrieval failure alone is insufficient.

## 7. Independent gates

The mission red-team returned `PASS` only with these constraints:

- no celebrity-practice copying without an ASXOS consumer;
- no recency-driven queue change;
- no source laundering through generated summaries;
- no duplicate knowledge hierarchy;
- no generic memory infrastructure before retrieval evidence; and
- no new Karpathy-specific mission or backlog ID.

Guilfoyle returned `READY_TO_EXECUTE` for a docs-only comparison, programme amendment, independent
architecture review, validation, and local commit.

## 8. Mission receipt

```yaml
mission_id: arbi-second-brain-karpathy-pattern-review-2026-08-12
source_authority: James direct instruction
baseline: f4ea38f
route: /arbi-mission
authority: I2 docs-only
red_team: PASS_WITH_CONSTRAINTS
guilfoyle: READY_TO_EXECUTE
independent_architecture_review: PASS_AFTER_CORRECTIONS
files_allowed:
  - docs/proposals/arbi-second-brain-karpathy-pattern-review-2026-08-12.md
  - docs/proposals/asxos-outcome-engine-and-arbi-second-brain-execution-plan-2026-08-12.md
  - docs/product/arbi-run-ledger.md
forbidden_boundaries_crossed: none
implementation_code: none
production_or_database_action: none
new_queue_or_mission_id: none
validation:
  diff_check: passed
  ruff: passed
  mypy: passed_160_source_files
  pytest: 1926_passed_1_failed_16_collection_errors_1_skipped_2_xfailed
  pytest_environment_note: shared_local_venv_missing_joblib_and_lightgbm
github_ci:
  full_check: passed_2_of_2
  targeted_ml_tests: passed_2_of_2
draft_pr: https://github.com/Jp8617465-sys/asxos/pull/95
readiness: READY_FOR_REVIEW
```
