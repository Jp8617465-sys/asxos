# "Hybrid TDD" for asxos — assessment against the current state

**Status:** assessment by arbi, 2026-09-17, at James's instruction — *"Explore this philosophy for
asxos… all positives and negatives as well as comparison to current state. This is from Gemini."*
**Method:** three read-only audits from the main loop (domain-layer purity, test-suite posture,
adapter boundary) over `asxos/domain/`, `tests/`, `jobs/`, `asxos/cli/`, `asxos/brief/` and the
foundation docs; every load-bearing claim below was re-verified by grep before it was written. No
code changed. Nothing here reads `signals` or any other rule #11 surface.
**Scope:** the philosophy as stated — pure domain layer, failing test suite first with all external
state mocked, thin adapters, "frontend and basic CRUD built for speed" — translated from its
TypeScript/Vitest/Stripe framing into this repo's terms.
**Class if the §7 actions are taken:** Green for 1–3 and 6, Tier B docs for 4 (`.claude/` is
James-merges), Amber for 5 (email send path).

---

## Bottom line

asxos already *is* a Hybrid-TDD codebase in its stated doctrine and in roughly 80% of its domain
code, and in three respects it is stricter than the philosophy asks. The philosophy is worth
adopting as a **name** for a convention that already exists but is only followed in packages written
after `decision_engine` (mid-2026). Two of its planks should be rejected outright for this repo:
"test CRUD lightly" (the previous repo died at the DB boundary, not in the maths) and "mock all
external state" as the *only* proof (lessons L7/L11 record seven incidents where a mock was accepted
as evidence). The one genuinely new thing it would bring is a **mechanised import-purity gate** — the
domain-purity rule is today a docstring convention, not a test.

---

## 1. The philosophy, translated to asxos

| Gemini plank | asxos equivalent |
|---|---|
| Pure domain module, no ORM/network/framework imports | `asxos/domain/**` must not import `asyncpg`, `asxos.db`, `httpx`, `jinja2`, `numpy` |
| Cents-as-integers or Big.js/Decimal.js | `Decimal` everywhere, `NUMERIC(18,6)` in Postgres (CLAUDE.md rule #5), quantize outputs only |
| Vitest failing suite first, mock external state | pytest, `tests/_netguard.py`, hand-rolled `FakeConn` classes, spec-§-cited tests |
| Stripe/Plaid adapter | `asxos/ingestion/eodhd.py`, `asxos/clients/fred.py`, `asxos/brief/email.py`, `asxos/db.py` + `typing.Protocol` conn ports |
| "Frontend and basic CRUD built for speed" | no frontend exists; the "CRUD" layer is jobs + CLI, which carry production invariants (idempotent UPSERTs, the s766B personal-use firewall, hard-fail gates) |

---

## 2. Scorecard against the current state

### Plank 1 — pure domain layer: **mostly met, unevenly, and unenforced**

Evidence for:
- `asxos/domain/tax/` (12 files) has zero DB/network/numpy imports. `positions.py` takes only
  dataclasses; the single DB read sits in `feed.py:246` behind `FeedConn(Protocol)` with its SQL
  fenced at import by `assert_feed_sql_admissible`. This is the reference shape.
- `asxos/domain/portfolio/build.py` alternates conn reads with pure calls into `allocator`,
  `constraints`, `rebalance` and `tax_overlay`, and its docstring states the rule.
- 17 `*Conn(Protocol)` ports across `decision_engine`, `valuation`, `results_review`, `replay`,
  `research/registry`, `themes/candidates`, `tax/feed`, `brief/gold`.
  `decision_engine/repository.py:79-85` gives the reason (tests pass a plain object, no driver).
  The architecture doc of record says it outright: *"`domain/` is pure functions … no Service
  classes, no repository injection"* (`docs/foundation/phase-4-architecture-system-architect.md:114,225`).
- Inbound non-DB boundaries are policed too: `themes/candidates/extraction_boundary.py` ("no
  numbers are computed here; the boundary transcribes, `measures.py` computes") and
  `results_review/adapter.py` ("pure in-memory, no network, no DB").

Evidence against (verified by grep, 19 files):
- **Direct driver import in domain:** `theses/service.py:26` (1,346 lines, 38 SQL statements,
  `asyncpg.Record` in mapper signatures at `:114`/`:166`), `themes/service.py:19`,
  `macro_theses/service.py:30`, `governance/transitions.py:34`, `governance/agent_run_guards.py:25`,
  `governance/agent_run_service.py:45`, `screening/evaluator.py:100`, `portfolio/profile.py:19`,
  `portfolio/volatility.py:15`, `research/segment_map.py:28`.
- **Global pool reached from domain:** seven `asxos/domain/brief/collectors/*.py` plus
  `composer.py:26` import `asxos.db.acquire` and open their own connection. `composer.py:57-61`
  is inconsistent inside one function (two collectors take `conn`, the third self-acquires).
  `decision_engine/repository.py:66` declares a Protocol port *and* imports `asxos.db`.
- **Network from domain:** `position_monitor/fetcher.py:22-24` imports the EODHD and FRED clients
  concretely. Nothing abstracts the HTTP clients.
- **Presentation in domain:** `decision_engine/renderer.py:12` and `delivery.py:42` import `jinja2`.
- **Fused compute in a job:** `jobs/snapshot_portfolio.py:148-269` `_compute_holdings_mv`
  interleaves three `conn.fetch` calls with the FX conversion, market-value accumulation and
  FX-P&L decomposition. The portfolio's headline numbers are not unit-testable without a fake
  connection. The fix pattern exists one directory away (`domain/portfolio/monitor.py` +
  `monitor_loader.py`).
- **Import-time side effect in a "pure" module:** `portfolio/monitor.py:39` sets
  `getcontext().prec = 40` on the process-global Decimal context. `valuation/numeric.py:2-8`
  documents exactly why this is wrong and uses `localcontext` instead. Any module importing
  `portfolio.monitor` silently changes precision for everything else in the process.

### Plank 1b — exact precision: **exceeds the philosophy**

- `Decimal(` / `float(` counts: `tax/` 67/0, `decision_engine/` 153/0, `portfolio/` 139/1 (the
  one is a position-count interpolation, not money). Zero `: float` fields in any Pydantic contract.
- Pydantic validators actively reject float inputs (`theses/schemas.py:90-93`), and the
  deserialisation contract mandates `json.loads(raw, parse_float=Decimal)`. `serde/canonical.py`
  encodes Decimal as a string, never a float.
- The SMSF one-third CGT discount is built from `Fraction(1, 3)` rather than a decimal literal
  (`tax/types.py:20`).
- One genuine monetary float: `research/factor_scores.py:148` computes a franking credit with
  `float(_GROSS_UP)`. Scoped as "measurement only", but it is the exception that shows the gate is
  prose.

The philosophy's "cents as integers" alternative would be a regression here: CGT bases keep full
precision and only ledger lines quantize (`tax/positions.py:36-41`), which integers cannot express.

### Plank 2 — TDD suite: **test-alongside with spec citation, not test-first; mocks mechanised; CRUD tested heavily**

- 189 test files, 2,670 top-level test functions; 4,634 passed / 12 skipped at `main` `e751595`
  (handoff 2026-09-17). The largest files are mock-free pure-domain suites: allocator 55,
  constraints 32, tax overlay 28, all 125 tax tests. About 65% of test modules contain no mock
  marker at all.
- Spec citation is dense and bidirectional: `§` appears in 30 test files
  (`test_tax_positions.py` 21 times), tests carry `TC-NN` conformance IDs, CLAUDE.md cites test
  node IDs back, and a `tax-spec-conformance` agent is routed on any `tests/test_tax_*` touch. The
  philosophy asks for "edge cases"; asxos asks for "the spec section this case defends".
- "Mock external state" is not asserted in prose, it is enforced: `tests/_netguard.py` patches
  socket entry points and denies even loopback; `conftest.py` scrubs credential-shaped env vars
  and repoints `HOME` so the production `.env` is unreachable. Only one real-DB lane exists, doubly
  gated behind `MIGRATION_TEST_DATABASE_URL` and a database-name check.
- **Test-first is not mandated and is deliberately displaced.** `BUILD_GUIDE.md §6.5` prescribes
  "sketch the test first, implement, iterate to green" *in the same session*; `AGENTS.md §5`
  enforces only "a behaviour change with no test delta is incomplete". Zero red-green language
  anywhere; squash-merge history makes ordering unobservable in any case.
- **CRUD is tested heavily, not lightly:** CLI 117 tests across 21 of 23 modules, jobs 149, brief
  composition 201. The mock-density top 15 is entirely this layer. 39 assertions pin SQL text
  (mostly `ON CONFLICT` idempotency contracts), which is the brittleness the philosophy warns
  about, although the intent is behavioural.
- No fast lane by design (`AGENTS.md §4`): the full suite is the unit of feedback, the opposite of
  a tight failing-test inner loop.
- One dead asset: `tests/support/characterize.py`, a documented snapshot harness with zero call
  sites (the postmortem forbids snapshot tests).

### Plank 3 — adapter layer: **thin and single-owner for vendors; diffuse for the DB**

- EODHD: one client, `lru_cache` factory, semaphore, tenacity retry, secret-redacting error
  rebuild; every row-shaping function is a separate pure parser. `eodhd.py:110-137` records the one
  time normalisation crept into the client (a quota error became indistinguishable from a quiet
  news day) and why it was moved out.
- RBA RSS and GitHub decisions are textbook: fetch in the job, parse in a pure module over bytes,
  upsert takes the conn.
- FRED normalises inside the client (fused, but returns a frozen dataclass, no business logic).
- Email: `asxos/brief/email.py:53 _send_via_resend` is the seam, but **six jobs re-implement
  `resend.Emails.send` inline** with their own env reads and differing failure handling
  (`check_au_positions`, `check_us_positions`, `check_thesis_invalidations`, `check_cron_health`,
  `score_macro_theses`, `validate_price_data`).
- DB: `asxos/db.py` is 60 lines. Connections are injected as parameters (160 `acquire()` sites,
  all in jobs/CLI/API except the brief collectors above). Only four repository modules exist; SQL
  otherwise lives inline in services, jobs and `asxos/brief/compose.py` (1,522 lines). The Protocol
  ports are driver-shaped (`fetch`/`execute`), not domain-repository-shaped — a deliberate
  anti-ceremony choice (`phase-4:225`).
- Brief path: collect → frozen `BriefData` → JSONB gold layer → pure `render_html` → `send_brief`,
  split across two jobs so `collect()` never runs on the send path.

---

## 3. Positives of adopting the philosophy (as a named convention)

1. **It names something the repo already believes but only half-enforces.** The Protocol-port +
   `Final[str]` SQL + import-time admissibility assertion pattern exists in every package written
   since `decision_engine`. Older packages (`theses`, `themes`, `governance`, `screening`) predate
   it. A written rule turns "the newer style" into "the style".
2. **A purity gate is cheap and would have caught real defects.** An import-graph test
   (`asxos/domain/**` must not import `asyncpg`, `asxos.db`, `httpx`, `jinja2`, `numpy`, `pandas`
   outside an allow-list) is about 40 lines, runs in milliseconds, and would today flag 19 files,
   the `factor_scores.py` float and the `monitor.py` global-context leak. The repo already has this
   shape of test for a sibling invariant: `tests/test_cli_model_independence.py` guards that no ML
   import reaches the CLI.
3. **Pure compute over dataclasses is postmortem lesson 10 made structural** ("spec-first for
   non-trivial domain logic"). Where it holds (`tax/`, `portfolio/monitor.py`) the tests are the
   largest, cleanest, mock-free files in the suite. Where it does not (`snapshot_portfolio.py`) the
   headline portfolio numbers have no pure test at all.
4. **The solo-founder velocity argument is real here.** One user, no second engineer, an agent
   operator: pure functions over typed inputs are the cheapest thing for an agent to test correctly
   and the hardest thing for it to get subtly wrong. The mock-heavy adapter tests are where fakes
   have twice patched out the thing they claimed to test (L11 amendment, instance 4).
5. **Decimal discipline aligns exactly**, and asxos's version (validators reject float,
   `Fraction`-built rates, quantize-outputs-only) is the more rigorous form. Nothing to change;
   worth writing down as the standard the philosophy is measured against.

## 4. Negatives and risks of adopting it as written

1. **"Test CRUD lightly" is the opposite of this repo's lesson.**
   `docs/foundation/phase-b-failure-postmortem.md` (contributing factors, schema drift): five
   schema-drift commits in one month, *"none of these were caught by CI — the test suite runs
   against an in-memory or migration-bootstrapped database, not the production Supabase."* The
   predecessor's domain maths was fine; it died at the DB boundary. The jobs/CLI layer here carries
   idempotency, the s766B personal-use firewall (63 call sites), hard-fail gates and the governance
   trigger-order invariant. Cutting those tests to "build for speed" would remove the only tests
   defending the failure class that actually happened.
2. **"Mock all external state" as the proof standard is already known to be insufficient.** L7,
   L11 and the seven-instance amendment: a mocked connection passed every unit test and two review
   loops while the emitted INSERT/UPDATE order was live-broken; a 1,264-passing suite proved nothing
   about a `NOT NULL` rejection; a 57-passing suite had fakes that patched out the worker under
   test. The repo's standing rule is "replay the exact emitted statement against the real schema
   once, rolled back". The philosophy has no such step. Adopting it naively would regress the
   culture.
3. **Test-first ordering is unobservable and unenforceable here.** Squash merges erase commit
   order; an agent operator writes test and implementation in one turn. Mandating "failing suite
   first" would be theatre. The enforceable form already exists (`AGENTS.md §5`, test delta
   required); the useful form is BUILD_GUIDE §6.5's "sketch the test shape before the
   implementation".
4. **Repository-interface ceremony was rejected on purpose.** `phase-4:225` and
   `phase-2-survives-the-fire.md:133` ("do not add an architectural seam unless a real second user
   is about to appear") explain why ports are driver-shaped Protocols, not `ThesisRepository` ABCs.
   The Stripe/Plaid adapter-interface plank, read literally, would reintroduce the layer the
   previous repo drowned in. Keep the Protocol shape.
5. **Purity absolutism has a cost at the SQL-generation seam.** `screening/evaluator.py` generates
   WHERE clauses purely and only `evaluate_rule` executes them; `screening-conventions.md:117`
   records that mocked SQL tests "prove call shape, not planner-level correctness". A purity gate
   must permit SQL *text* in domain (as `Final[str]` constants with admissibility assertions) or it
   forbids the current best practice.
6. **The test budget is already far past the postmortem's own target** (lesson 6: about 400
   load-bearing tests; today 4,634 passing). The philosophy pushes toward more unit tests, not
   fewer. The pressure this repo needs is the reverse: fewer, named-failure-class tests, and one
   real-DB lane that runs on the write path.

## 5. Where asxos is ahead of the philosophy

- Spec-section citation and conformance IDs on tests (the philosophy asks only for "edge cases").
- Import-time SQL admissibility fences that keep rule #11 (no Model A reads) out of domain SQL
  without a database.
- A mechanised network tripwire rather than a mocking convention.
- Float rejection at the validator, not just Decimal typing.
- Documented postmortems *inside the adapter code* for the times the boundary leaked
  (`eodhd.py:110-137`).
- A persisted JSONB gold layer between collect and render, so rendering has no live query shape.

## 6. Where asxos is behind it

- No mechanised purity gate on `asxos/domain/`; 19 files violate the stated rule.
- `jobs/snapshot_portfolio.py` computes the portfolio's headline numbers inside SQL loops.
- Brief V2 collectors self-acquire connections (untestable without patching the global).
- `portfolio/monitor.py:39` mutates global Decimal precision at import.
- Six duplicated inline email senders instead of the one seam.
- `theses/service.py` is the entrenched legacy: business rules (status, governance, non-null
  checks in `enter_thesis`) are interleaved with SQL inside a transaction, with no extractable pure
  `can_enter(thesis)`.

---

## 7. Recommendation

Adopt the philosophy **as a written convention with a mechanised gate**, not as a test-ordering
mandate and not as "CRUD lightly". If James says go, the work is small:

| # | Action | Files | Class | Reversal |
|---|---|---|---|---|
| 1 | Add `tests/test_domain_purity.py`: walk `asxos/domain/**`, assert no import of `asyncpg`, `asxos.db`, `httpx`, `jinja2`, `numpy`, `pandas`; explicit allow-list for the 19 known violators with a comment that the list only shrinks. Model on `tests/test_cli_model_independence.py`. | new test | Green | revert |
| 2 | Fix `asxos/domain/portfolio/monitor.py:39`: replace `getcontext().prec = 40` with a `localcontext` in the functions that need it, per `valuation/numeric.py`. Add a test that importing the module leaves `getcontext().prec` unchanged. | `monitor.py`, test | Green | revert |
| 3 | Extract the pure compute from `jobs/snapshot_portfolio.py:148-269` into `asxos/domain/portfolio/snapshot.py` (`compute_holdings_mv(fx_rate, holding_rows, us_cost_rows, as_of) -> SnapshotValues`), leaving the three `conn.fetch` calls in the job. Add mock-free tests for the AUD conversion, MV accumulation and FX-P&L decomposition. Verify by a dry-run dispatch producing identical rows to the current head. | job, new domain module, tests | Green (no schema; `portfolio_daily_snapshots` is re-derivable) | revert |
| 4 | Write the convention into `.claude/rules/domain-purity.md` (Protocol port at the bottom, `Final[str]` SQL with admissibility assertion, no global context mutation, SQL text permitted, driver import forbidden) and cross-link from `AGENTS.md §5`. `.claude/**` is draft-and-James-merges (`AGENTS.md §8`). | `.claude/rules/domain-purity.md`, `AGENTS.md` | Tier B docs | James merges |
| 5 | Deduplicate the six inline Resend senders onto `asxos/brief/email.py::_send_via_resend`. | six jobs | Amber (email send path) | revert; no data |
| 6 | Delete `tests/support/characterize.py` (zero call sites; snapshot tests forbidden by postmortem lesson 6). | one file | Green | revert |

Explicitly **not** recommended:
- Mandating failing-test-first commits (unobservable under squash; the `AGENTS.md §5` test-delta
  gate is the enforceable form).
- Thinning CLI/job tests. Keep them; convert SQL-text assertions to behaviour where a fake can
  observe the behaviour, otherwise leave them.
- Introducing `ThesisRepository`-style ABCs. Keep driver-shaped Protocols.
- Refactoring `theses/service.py` wholesale now. It is the biggest violator but also the most
  live-verified against triggers; carve out pure predicates only when a change already touches the
  function.

Ordering: 1 and 2 first (one PR), 3 second (its own PR with the dry-run comparison), 4 alongside 3
as a separate `.claude/` PR for James, 5 and 6 opportunistic.

## 8. Verification (if the §7 actions are executed)

- `make check` green locally; `full-check` green on the branch head.
- `pytest tests/test_domain_purity.py -q` fails when a forbidden import is added to a
  non-allow-listed domain module (prove by a temporary edit, then revert).
- After action 2: importing `asxos.domain.portfolio.monitor` leaves `getcontext().prec` at 28.
- For action 3: dispatch `snapshot_portfolio` dry-run on the branch and diff the computed
  `holdings_mv_aud`, `us_mv_aud`, `us_fx_pnl_aud` against the current `main` values for the same
  `as_of`; identical to six decimal places.
- For action 5: send one real alert from each refactored job via a manual dispatch; confirm receipt.
