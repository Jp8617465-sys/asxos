"""
Structural guard: `asxos/domain/**` must not import a DB driver, an HTTP client, a
templating engine, or a numeric-array library.

WHY THIS EXISTS. `docs/foundation/phase-4-architecture-system-architect.md` states
the rule in prose: "`domain/` is pure functions ... no Service classes, no
repository injection." `.claude/rules/api-conventions.md` restates it for tests:
"mock `asxos.db.acquire` and pass synthetic asyncpg `Record`-shaped dicts" — which
only makes sense if the thing being tested does not import the driver itself.
Seventeen modules under `asxos/domain/` already follow this by declaring a narrow
`typing.Protocol` for exactly the connection methods they need instead of
importing `asyncpg` (`asxos/domain/tax/feed.py:246`, `asxos/domain/decision_engine/
repository.py:77`, etc.) — see the docs/proposals/hybrid-tdd-assessment-2026-09-17.md
assessment. Until this test existed, that pattern was a convention a reader could
notice, not a property anything re-checked; a new module could import `asyncpg`
directly and nothing would fail.

THE ALLOW-LIST IS SHRINK-ONLY. It records every file that violated the rule when
this test was written (2026-09-17), so a pre-existing violation does not block
unrelated work. A file leaving the list (because it was converted to a Protocol
port, per `docs/proposals/hybrid-tdd-assessment-2026-09-17.md` §7 action 3, or
simply stopped importing the forbidden name) must also leave `_KNOWN_VIOLATORS` —
enforced below — so the list cannot silently go stale. A NEW file, or an existing
file gaining a NEW forbidden import, fails loudly and by name. Never add a file to
this list to make a new violation "pass" — fix the import instead, per the
`Protocol`-port pattern the rest of `domain/` already uses.

Includes imports inside `if TYPE_CHECKING:` blocks and inside function bodies (a
lazy or type-only `import asyncpg` still couples the module to the concrete
driver type in its annotations, which is exactly what the `Protocol` ports exist
to avoid — see `asxos/domain/portfolio/monitor_loader.py`, `paper_trade.py`,
`asxos/domain/prices/coverage.py`).

RUNS ANYWHERE: pure `ast` + `pathlib`, no imports of the modules under test, so it
executes in the bare sandbox lane as well as CI (pattern follows
tests/test_cli_model_independence.py).
"""
from __future__ import annotations

import ast
import pathlib

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_DOMAIN_ROOT = _ROOT / "asxos" / "domain"

# Third-party packages that couple a "pure" domain module to a driver, an HTTP
# client, a templating engine, or a numeric-array library. Not forbidden
# repo-wide — jobs/, the CLI, and asxos/brief/ (the V1 renderer) may use all of
# these; only asxos/domain/** may not.
_FORBIDDEN_THIRD_PARTY = frozenset({"asyncpg", "httpx", "jinja2", "numpy", "pandas"})

# First-party modules that reach the global connection pool. asxos.domain.* itself
# is never forbidden — pure domain modules import each other constantly.
_FORBIDDEN_FIRST_PARTY = frozenset({"asxos.db"})

# Shrink-only. One relative path (posix, from repo root) per known violation as of
# 2026-09-17 — see docs/proposals/hybrid-tdd-assessment-2026-09-17.md §2 for the
# audit that produced this list. Do not add a new entry to silence a new
# violation; do not leave a stale entry once a violation is fixed (the test below
# checks both directions).
_KNOWN_VIOLATORS = frozenset(
    {
        "asxos/domain/brief/collectors/active_theses.py",
        "asxos/domain/brief/collectors/market_context.py",
        "asxos/domain/brief/collectors/new_ideas.py",
        "asxos/domain/brief/collectors/opportunity_cost.py",
        "asxos/domain/brief/collectors/theme_dashboard.py",
        "asxos/domain/brief/collectors/underlying_drivers.py",
        "asxos/domain/brief/collectors/watchlist.py",
        "asxos/domain/brief/composer.py",
        "asxos/domain/brief/renderer.py",
        "asxos/domain/decision_engine/delivery.py",
        "asxos/domain/decision_engine/renderer.py",
        "asxos/domain/governance/agent_run_guards.py",
        "asxos/domain/governance/agent_run_service.py",
        "asxos/domain/governance/transitions.py",
        "asxos/domain/macro_theses/service.py",
        "asxos/domain/portfolio/holdings.py",  # merged into main 2026-09-18 (#327/#328),
        # after this list was first written; same shape as the others (asyncpg.
        # Connection in a type annotation only).
        "asxos/domain/portfolio/monitor_loader.py",
        "asxos/domain/portfolio/paper_trade.py",
        "asxos/domain/portfolio/profile.py",
        "asxos/domain/portfolio/volatility.py",
        "asxos/domain/prices/coverage.py",
        "asxos/domain/research/alpha_eval.py",
        "asxos/domain/research/alpha_loader.py",
        "asxos/domain/research/factor_scores.py",
        "asxos/domain/research/segment_map.py",
        "asxos/domain/screening/evaluator.py",
        "asxos/domain/themes/service.py",
        "asxos/domain/theses/service.py",
            }
)


def _violations(path: pathlib.Path) -> list[tuple[int, str]]:
    """(lineno, forbidden dotted name) for every forbidden import in `path`.

    Walks the whole tree, not just module level, so a forbidden import nested in
    a function body or an `if TYPE_CHECKING:` block is still caught.
    """
    tree = ast.parse(path.read_text(), filename=str(path))
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root in _FORBIDDEN_THIRD_PARTY or alias.name in _FORBIDDEN_FIRST_PARTY:
                    found.append((node.lineno, alias.name))
        elif isinstance(node, ast.ImportFrom):
            if node.module is None:
                continue  # a relative `from . import x` — none exist under domain/
            root = node.module.split(".")[0]
            if root in _FORBIDDEN_THIRD_PARTY or node.module in _FORBIDDEN_FIRST_PARTY:
                found.append((node.lineno, node.module))
    return found


def test_domain_purity_scan_reaches_the_whole_package() -> None:
    """Sanity guard: the walk must really be scanning domain/, not finding nothing."""
    files = list(_DOMAIN_ROOT.rglob("*.py"))
    assert len(files) > 100, (
        f"only found {len(files)} files under asxos/domain/ — the scan is not "
        "reaching the package, so it is not proving anything"
    )


def test_domain_modules_do_not_import_driver_network_or_array_libraries() -> None:
    """The gate itself: no asxos/domain/** file may import a forbidden name
    unless it is on the shrink-only allow-list — and every allow-listed file must
    still actually violate the rule, or the list has gone stale.
    """
    new_violations: list[str] = []
    now_clean: list[str] = []

    for path in sorted(_DOMAIN_ROOT.rglob("*.py")):
        rel = path.relative_to(_ROOT).as_posix()
        violations = _violations(path)
        if violations and rel not in _KNOWN_VIOLATORS:
            for lineno, name in violations:
                new_violations.append(
                    f"{rel}:{lineno} imports {name} — asxos/domain/** must be pure "
                    "(no DB driver, HTTP client, templating engine, or array "
                    "library). Use a typing.Protocol port instead, per "
                    "asxos/domain/tax/feed.py or asxos/domain/decision_engine/"
                    "repository.py. If this file is meant to be exempt, that is a "
                    "decision for docs/proposals/hybrid-tdd-assessment-2026-09-17.md "
                    "to record, not this test to silence."
                )
        if not violations and rel in _KNOWN_VIOLATORS:
            now_clean.append(rel)

    assert not new_violations, "new domain-purity violation(s):\n  " + "\n  ".join(
        new_violations
    )
    assert not now_clean, (
        "these files are in _KNOWN_VIOLATORS but no longer violate the rule — "
        "remove them from the allow-list (it is shrink-only):\n  "
        + "\n  ".join(now_clean)
    )
