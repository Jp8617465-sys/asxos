"""Deterministic picker over ``docs/product/backlog.yaml`` (Amendment K, 2026-09-05).

The ``backlog-roll`` standing lane runs this BEFORE the agent. It answers two questions
with no model in the loop:

1. ``picked`` — which arbi-owned, dependency-met, reversible items may this fire build,
   on independent ``claude/**`` branches, without touching a path the unattended guard
   would refuse.
2. ``click_list`` — which James-owned items are unblocked right now. This is the lane's
   primary product. Once the Amendment H train lands, most of the backlog is his, and
   the honest job of a constant mission is to surface that daily and mechanically.

Why the denied-path list lives HERE and not only in the hook: eligibility is DERIVED
from an item's ``paths``, never declared. The YAML cannot mark something safe that
``.claude/hooks/unattended-guard.sh`` would deny — ``tests/test_backlog_next.py`` parses
the hook and ``.claude/settings.json`` and fails if this list drifts behind them. The
hook stays the control; this is the pre-gate that keeps a fire from starting work it
could never finish.

Why ``scripts/`` is a shim and the logic is in ``asxos/``: same reason as
``asxos/schema_drift.py`` — ``scripts/`` is not a package, so the importable, mypy-checked
copy has to live in the tree. ``scripts/backlog_next.py`` only parses argv and exits.

Ranking is unblocking-first: phase A→E, then the item with the MOST open dependents,
then id. Independent branches only — stacking needs a force-push, which the guard
denies unattended — so a pick whose paths overlap an earlier pick is skipped this fire.

Exit codes (via :func:`main`): 0 picked at least one · 2 schema error · 3 nothing
eligible (the click-list is still emitted — that is the point).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from asxos.clock import today

DEFAULT_BACKLOG = Path(__file__).resolve().parents[1] / "docs" / "product" / "backlog.yaml"

PHASES: tuple[str, ...] = ("A", "B", "C", "D", "E")
OWNERS: frozenset[str] = frozenset({"arbi", "james", "both", "time"})
STATUSES: frozenset[str] = frozenset(
    {"done", "built-unmerged", "open", "blocked", "parked", "void"}
)
ROUTES: frozenset[str] = frozenset({"build", "mission", "attended", "james", "observe"})

# A dependency is met only when the dependency is finished or was voided. A PR that
# exists but is unmerged is NOT done — that distinction is the whole reason A-0 sits
# at the top of every click-list until James un-drafts.
SATISFIED: frozenset[str] = frozenset({"done", "void"})
# Routes the lane may build. ``attended`` is arbi's but needs a live session;
# ``james`` and ``observe`` are never built.
BUILDABLE_ROUTES: frozenset[str] = frozenset({"build", "mission"})
PICKABLE_OWNERS: frozenset[str] = frozenset({"arbi", "both"})
CLICK_STATUSES: frozenset[str] = frozenset({"open", "built-unmerged"})

_ID_RE = re.compile(r"^[A-E]-\d+[a-z]?$")
_GLOB_META_RE = re.compile(r"[*?\[\]{}]")
_REQUIRED = ("id", "title", "phase", "owner", "status", "depends_on", "route", "paths", "source")

# --- The denied set — mirrors the guards, never widens the grant --------------------
#
# Exact files: ``.claude/hooks/unattended-guard.sh`` ``is_authority_path()`` plus every
# ``Edit(/<file>)`` in ``.claude/settings.json`` ``permissions.deny``.
DENIED_FILES: frozenset[str] = frozenset(
    {
        "CLAUDE.md",
        ".env",
        "render.yaml",
        ".claude/settings.json",
        ".claude/settings.local.json",
        ".claude/agents/arbi.md",
        "docs/README.md",
        "docs/product/north-star.md",
        "docs/product/arbi-constitution.md",
        "docs/product/arbi-authority.md",
        "docs/product/arbi-permission-model.md",
        "docs/product/arbi-harness.md",
        "docs/product/arbi-scorecard.md",
        "docs/product/arbi-promotion-gate.md",
        "docs/product/arbi-memory-policy.md",
        "docs/product/arbi-dream-policy.md",
        "docs/product/arbi-managed-agent-spec.md",
        "docs/product/arbi-autonomy-loop.md",
        "docs/product/arbi-goal-recipes.md",
        "docs/product/arbi-evals.md",
        "docs/product/guilfoyle-mission-control.md",
        "docs/product/portfolio-manager-charter.md",
        "docs/product/portfolio-policy.md",
        "docs/product/recommendation-schema.md",
        "docs/product/data-contracts.md",
        "docs/product/memory/approved-lessons.md",
        "docs/product/memory/authority-lessons.md",
        "docs/product/memory/project-facts.md",
        "docs/product/memory/promotion-log.md",
        "docs/product/memory/rejected-candidates.md",
    }
)
# Directory prefixes (trailing slash): the guard's ``CAPITAL_FRAGMENTS`` (capital-adjacent
# code is human-only under the loop), ``.claude/hooks/`` (authority), every
# ``Edit(/<dir>/**)`` deny in settings.json, and ``migrations/`` (applying one is I5;
# drafting one unattended would be a PR that can never be verified in the lane).
DENIED_PREFIXES: tuple[str, ...] = (
    "asxos/domain/portfolio/",
    "asxos/domain/tax/",
    "asxos/domain/models/",
    "asxos/domain/theses/",
    ".claude/hooks/",
    ".claude/agents/",
    ".claude/commands/",
    ".claude/rules/",
    ".claude/skills/",
    ".github/",
    "docs/product/rubrics/",
    "migrations/",
)


class BacklogSchemaError(ValueError):
    """The YAML does not match the documented schema. Exit 2, never a guess."""


@dataclass(frozen=True)
class Item:
    id: str
    title: str
    phase: str
    owner: str
    status: str
    depends_on: tuple[str, ...]
    route: str
    paths: tuple[str, ...]
    source: str
    # Filled by :func:`annotate`, not from the file.
    open_dependents: int = field(default=0, compare=False)

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "phase": self.phase,
            "owner": self.owner,
            "status": self.status,
            "route": self.route,
            "depends_on": list(self.depends_on),
            "paths": list(self.paths),
            "source": self.source,
            "open_dependents": self.open_dependents,
        }


# --- Paths -------------------------------------------------------------------------


def _norm(p: str) -> str:
    p = p.strip().replace("\\", "/")
    while p.startswith("./"):
        p = p[2:]
    return p.lstrip("/")


def _scope_is_canonical(path: str) -> bool:
    """Only literal, repo-relative file or directory scopes are executable grants."""
    raw = path.strip()
    if not raw or raw.startswith("/") or "\\" in raw or "//" in raw:
        return False
    while raw.startswith("./"):
        raw = raw[2:]
    if not raw or _GLOB_META_RE.search(raw):
        return False
    return all(part not in {"", ".", ".."} for part in raw.rstrip("/").split("/"))


def is_denied_path(path: str) -> bool:
    """True if ``path`` is, is inside, or CONTAINS anything the guards deny.

    "Contains" is deliberate: an item whose ``paths`` says ``docs/product/`` would be
    licensed to touch ``north-star.md``. A directory glob broader than the denied set is
    denied, so a coarse path can never launder a guarded file.
    """
    if not _scope_is_canonical(path):
        return True
    p = _norm(path)
    if p in DENIED_FILES:
        return True
    p_dir = p if p.endswith("/") else p + "/"
    for prefix in DENIED_PREFIXES:
        if p.startswith(prefix) or p_dir == prefix or prefix.startswith(p_dir):
            return True
    return any(f.startswith(p_dir) for f in DENIED_FILES)


def paths_overlap(a: Iterable[str], b: Iterable[str]) -> bool:
    """Two branches would collide if either side's path equals, contains, or sits inside
    the other's. Distinct files in one directory do not overlap."""
    for x in a:
        xn = _norm(x)
        xd = xn if xn.endswith("/") else xn + "/"
        for y in b:
            yn = _norm(y)
            yd = yn if yn.endswith("/") else yn + "/"
            if xn == yn or yn.startswith(xd) or xn.startswith(yd):
                return True
    return False


# --- Loading + validation ------------------------------------------------------------


def _expect_str(row: Mapping[str, Any], key: str, item_id: str) -> str:
    v = row.get(key)
    if not isinstance(v, str) or not v.strip():
        raise BacklogSchemaError(f"{item_id}: '{key}' must be a non-empty string")
    return v.strip()


def _expect_list_of_str(row: Mapping[str, Any], key: str, item_id: str) -> tuple[str, ...]:
    v = row.get(key)
    if v is None:
        return ()
    if not isinstance(v, list) or not all(isinstance(x, str) for x in v):
        raise BacklogSchemaError(f"{item_id}: '{key}' must be a list of strings")
    return tuple(x.strip() for x in v)


def parse(doc: Mapping[str, Any]) -> list[Item]:
    """Validate a loaded YAML mapping and return items in file order."""
    if not isinstance(doc, Mapping):
        raise BacklogSchemaError("top level must be a mapping")
    if doc.get("version") != 1:
        raise BacklogSchemaError(f"unsupported version: {doc.get('version')!r}")
    rows = doc.get("items")
    if not isinstance(rows, list) or not rows:
        raise BacklogSchemaError("'items' must be a non-empty list")

    items: list[Item] = []
    seen: set[str] = set()
    for raw in rows:
        if not isinstance(raw, Mapping):
            raise BacklogSchemaError(f"item is not a mapping: {raw!r}")
        item_id = str(raw.get("id", "?"))
        unknown = set(raw) - set(_REQUIRED)
        if unknown:
            raise BacklogSchemaError(f"{item_id}: unknown keys {sorted(unknown)}")
        missing = [k for k in _REQUIRED if k not in raw]
        if missing:
            raise BacklogSchemaError(f"{item_id}: missing keys {missing}")
        if not _ID_RE.match(item_id):
            raise BacklogSchemaError(f"bad id {item_id!r} (expected e.g. A-0, B-13a)")
        if item_id in seen:
            raise BacklogSchemaError(f"duplicate id {item_id}")
        seen.add(item_id)

        phase = _expect_str(raw, "phase", item_id)
        owner = _expect_str(raw, "owner", item_id)
        status = _expect_str(raw, "status", item_id)
        route = _expect_str(raw, "route", item_id)
        if phase not in PHASES:
            raise BacklogSchemaError(f"{item_id}: phase {phase!r} not in {PHASES}")
        if phase != item_id[0]:
            raise BacklogSchemaError(f"{item_id}: phase {phase!r} disagrees with id prefix")
        if owner not in OWNERS:
            raise BacklogSchemaError(f"{item_id}: owner {owner!r} not in {sorted(OWNERS)}")
        if status not in STATUSES:
            raise BacklogSchemaError(f"{item_id}: status {status!r} not in {sorted(STATUSES)}")
        if route not in ROUTES:
            raise BacklogSchemaError(f"{item_id}: route {route!r} not in {sorted(ROUTES)}")

        paths = _expect_list_of_str(raw, "paths", item_id)
        invalid_paths = [path for path in paths if not _scope_is_canonical(path)]
        if invalid_paths:
            raise BacklogSchemaError(
                f"{item_id}: paths must be literal repo-relative scopes: {invalid_paths!r}"
            )

        items.append(
            Item(
                id=item_id,
                title=_expect_str(raw, "title", item_id),
                phase=phase,
                owner=owner,
                status=status,
                depends_on=_expect_list_of_str(raw, "depends_on", item_id),
                route=route,
                paths=paths,
                source=_expect_str(raw, "source", item_id),
            )
        )

    ids = {i.id for i in items}
    for it in items:
        for dep in it.depends_on:
            if dep == it.id:
                raise BacklogSchemaError(f"{it.id}: depends on itself")
            if dep not in ids:
                raise BacklogSchemaError(f"{it.id}: depends_on unknown id {dep!r}")

    by_id = {item.id: item for item in items}
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(item_id: str) -> None:
        if item_id in visiting:
            raise BacklogSchemaError(f"dependency cycle includes {item_id}")
        if item_id in visited:
            return
        visiting.add(item_id)
        for dependency in by_id[item_id].depends_on:
            visit(dependency)
        visiting.remove(item_id)
        visited.add(item_id)

    for item_id in by_id:
        visit(item_id)
    return annotate(items)


def load(path: Path = DEFAULT_BACKLOG) -> list[Item]:
    with path.open(encoding="utf-8") as fh:
        doc = yaml.safe_load(fh)
    return parse(doc)


def annotate(items: Sequence[Item]) -> list[Item]:
    """Fill ``open_dependents`` — how many unfinished items wait on each one."""
    counts: dict[str, int] = {i.id: 0 for i in items}
    for it in items:
        if it.status in SATISFIED:
            continue
        for dep in it.depends_on:
            counts[dep] += 1
    return [
        Item(
            **{
                **i.as_dict(),
                "depends_on": i.depends_on,
                "paths": i.paths,
                "open_dependents": counts[i.id],
            }
        )
        for i in items
    ]


# --- Selection -----------------------------------------------------------------------


def deps_satisfied(item: Item, by_id: Mapping[str, Item]) -> bool:
    return all(by_id[d].status in SATISFIED for d in item.depends_on)


def eligible(item: Item, by_id: Mapping[str, Item]) -> bool:
    """May the lane build this item on this fire?"""
    return (
        item.owner in PICKABLE_OWNERS
        and item.route in BUILDABLE_ROUTES
        and item.status == "open"
        and deps_satisfied(item, by_id)
        and bool(item.paths)
        and not any(is_denied_path(p) for p in item.paths)
    )


def _id_sort_key(item_id: str) -> tuple[int, str]:
    """``B-5`` before ``B-10``; ``B-13`` before ``B-13a``. Never a string sort on ids."""
    m = re.match(r"^[A-E]-(\d+)([a-z]?)$", item_id)
    assert m, item_id  # parse() already validated the shape
    return (int(m.group(1)), m.group(2))


def rank_key(item: Item) -> tuple[int, int, int, str]:
    num, suffix = _id_sort_key(item.id)
    return (PHASES.index(item.phase), -item.open_dependents, num, suffix)


def pick(items: Sequence[Item], max_items: int) -> tuple[list[Item], list[Item]]:
    """Return ``(picked, skipped_for_overlap)`` in rank order."""
    by_id = {i.id: i for i in items}
    picked: list[Item] = []
    skipped: list[Item] = []
    for it in sorted((i for i in items if eligible(i, by_id)), key=rank_key):
        if len(picked) >= max_items:
            break
        if any(paths_overlap(it.paths, p.paths) for p in picked):
            skipped.append(it)
            continue
        picked.append(it)
    return picked, skipped


def click_list(items: Sequence[Item]) -> list[Item]:
    """Every item that needs James's hand and is unblocked right now."""
    by_id = {i.id: i for i in items}
    return sorted(
        (
            i
            for i in items
            if (
                (i.status == "built-unmerged" or i.route == "james")
                and i.status in CLICK_STATUSES
                and deps_satisfied(i, by_id)
            )
        ),
        key=rank_key,
    )


def report(items: Sequence[Item], max_items: int, backlog_updated: Any) -> dict[str, Any]:
    picked, skipped = pick(items, max_items)
    by_id = {i.id: i for i in items}
    return {
        "generated": today().isoformat(),
        "backlog_updated": str(backlog_updated),
        "eligible": sum(1 for i in items if eligible(i, by_id)),
        "picked": [i.as_dict() for i in picked],
        "skipped_overlap": [i.id for i in skipped],
        "click_list": [i.as_dict() for i in click_list(items)],
    }


# --- CLI -----------------------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="backlog_next",
        description="Pick the next unattended-safe backlog items and list James's clicks.",
    )
    ap.add_argument("--backlog", type=Path, default=DEFAULT_BACKLOG)
    ap.add_argument("--max", type=int, default=3, dest="max_items")
    ap.add_argument("--json", action="store_true", help="emit JSON only (default)")
    ns = ap.parse_args(argv)

    if not 1 <= ns.max_items <= 3:
        print("backlog_next: schema error: --max must be between 1 and 3", file=sys.stderr)
        return 2

    try:
        with ns.backlog.open(encoding="utf-8") as fh:
            doc = yaml.safe_load(fh)
        items = parse(doc)
    except (OSError, yaml.YAMLError, BacklogSchemaError) as exc:
        print(f"backlog_next: schema error: {exc}", file=sys.stderr)
        return 2

    out = report(items, ns.max_items, doc.get("updated"))
    print(json.dumps(out, indent=2, sort_keys=False))
    return 0 if out["picked"] else 3
