---
paths:
  - asxos/domain/**
---

# Domain purity — `asxos/domain/**`

The rule this file states was already the architecture of record
(`docs/foundation/phase-4-architecture-system-architect.md:114,225` — *"`domain/` is
pure functions … no Service classes, no repository injection"*) and already the
implicit house style of every package written since `decision_engine`. It was never
written down in one place, and until 2026-09-17 nothing checked it. Both are now
fixed: this file is the statement, `tests/test_domain_purity.py` is the enforcement.

Background and the audit that produced the allow-list:
`docs/proposals/hybrid-tdd-assessment-2026-09-17.md`.

---

## The rule

**A module under `asxos/domain/` must not import a DB driver, an HTTP client, a
templating engine, or a numeric-array library.** Concretely, the forbidden names are
`asyncpg`, `asxos.db`, `httpx`, `jinja2`, `numpy`, `pandas` — enforced by
`tests/test_domain_purity.py`, which fails on any new one and names the file and line.

Forbidden anywhere in the file, including inside `if TYPE_CHECKING:` and inside a
function body. A type-only `import asyncpg` costs nothing at runtime but still puts
the concrete driver type in the module's annotations, which is exactly what the
`Protocol` ports below exist to avoid.

`asxos.domain.*` is never forbidden — pure modules import each other constantly.
Neither is `dateutil`, `pydantic`, or `Decimal`: deterministic, no I/O.

## What replaces each one

**A connection → a `Protocol` port at the bottom of the module.** Declare the two or
three methods you actually call, and the domain never sees the driver. Seventeen
modules already do this; the clearest is `asxos/domain/tax/feed.py` (*"Pure functions
first; the one DB read sits at the bottom behind a Protocol"*), and
`asxos/domain/decision_engine/repository.py:77` states the payoff: *"Named explicitly
(rather than importing `asyncpg.Connection`) so tests can pass a plain mock object
without constructing a real connection."*

```python
class FeedConn(Protocol):
    async def fetch(self, query: str, *args: object) -> list[Any]: ...
```

**SQL text is allowed in domain; executing it is not.** Put statements in
module-level `Final[str]` constants and assert them admissible at import, as
`asxos/domain/valuation/inputs.py` and `asxos/domain/tax/feed.py` do. That is how a
pure unit test can assert a query never touches a forbidden surface (rule #11's
`signals` table, say) with no database. `asxos/domain/screening/evaluator.py` goes
further and *generates* WHERE clauses purely; only `evaluate_rule` executes them.

**An HTTP client → the caller fetches, the domain parses.** The pattern is
`asxos/ingestion/regulatory.py`: *"Network I/O is pushed to fetchers in the job
script — parsers are pure functions over bytes/strings."* `asxos/ingestion/eodhd.py`
carries the postmortem of the one time normalisation crept back into a client (a
quota error became indistinguishable from a quiet news day).

**A job that computes while it queries → load, then compute.** Map rows to frozen
dataclasses at the boundary and hand them to a pure function.
`asxos/domain/portfolio/monitor.py` + `monitor_loader.py` is the reference pair;
`asxos/domain/portfolio/snapshot.py` + `jobs/snapshot_portfolio.py` is the same split
applied to the daily snapshot.

## Two adjacent hazards, neither caught by the import gate

**Never mutate the process-global `Decimal` context.** `getcontext().prec = 40` at
import time changes precision for every other module for the life of the process, and
it silently did: the franking gross-up constant in
`asxos/domain/valuation/residual_income.py` evaluated to a different value depending
on which module the test suite imported first (found 2026-09-16, fixed 2026-09-17).
Use a module-local `Context` with `localcontext`, as
`asxos/domain/valuation/numeric.py` documents and does.

**Be deliberate about which context a persisted figure is computed under.** If a
function divides and its result is stored, widening its precision changes stored
history. `asxos/domain/portfolio/snapshot.py` therefore runs under the ambient
context on purpose, and says so — the opposite choice from `valuation/numeric.py`,
for a stated reason. Either is fine; silently changing one is not.

## The allow-list is shrink-only

`tests/test_domain_purity.py::_KNOWN_VIOLATORS` records the files that already broke
the rule when the gate landed, so a pre-existing violation does not block unrelated
work. It moves one direction. The test also fails when an allow-listed file *stops*
violating the rule, so the list cannot go stale while looking maintained.

**Never add a file to that list to make a new violation pass.** Convert the import to
a port instead. If a file genuinely warrants an exemption, that is a decision to
record in the assessment doc, with a reason, not a line quietly added to a frozenset.

The entries worth retiring first, in rough order of value:

1. `asxos/domain/brief/collectors/*` and `composer.py` — seven collectors call
   `acquire()` and open their own connection, which is the least testable shape in
   the repo. `composer.py` is inconsistent inside one function: two collectors take
   a `conn`, the third self-acquires.
2. `asxos/domain/portfolio/monitor_loader.py`, `paper_trade.py`,
   `asxos/domain/prices/coverage.py` — `TYPE_CHECKING`-only imports whose bodies are
   already pure. Swapping `asyncpg.Connection` for a `Protocol` in the annotations
   is close to a no-op and removes three entries.
3. `asxos/domain/theses/service.py` — the most entrenched (1,346 lines, 38 SQL
   statements, `asyncpg.Record` in its mappers at `:114` and `:166`). Its business
   rules are interleaved with SQL inside a transaction. Carve out pure predicates
   opportunistically, when a change already touches the function; do not attempt it
   wholesale. It is also the module whose emitted statement ORDER is load-bearing
   against a live trigger (see `portfolio-conventions.md`, and L7/L11).

## What this rule is not

It is not an argument for repository interfaces. `phase-4:225` rejected
`BaseService`/`BaseRepository` deliberately, and
`phase-2-survives-the-fire.md:133` says why: *"do not add an architectural seam …
unless a real second user is about to appear."* The ports here are narrow structural
`Protocol`s over the methods actually called — not an abstraction layer.

It is also not a claim that a pure unit test is sufficient evidence. Lessons L7 and
L11, and the seven-instance amendment in `docs/product/memory/lessons.md`, all record
the same failure: a mocked connection accepted as proof. A mocked connection does not
enforce a constraint or a trigger. Purity makes the *arithmetic* cheap to prove; a
DB-touching change still gets its emitted statements replayed against the real schema
once, in a rolled-back transaction.
