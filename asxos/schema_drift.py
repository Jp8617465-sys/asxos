"""Compare applied migration NAMES against the files in migrations/.

WHY A NAME DIFF AND NOT A COUNT
    The previous guard was ``if count < REQUIRED_MIGRATIONS: raise``. Being a
    ``<`` on a count, it could not detect the failure that matters: a migration
    applied to production with no file in this repo. The count rises and the
    guard passes. It also could not detect a substitution (count unchanged) or
    any divergence in content.

    That was not hypothetical. On 2026-08-23 the ledger carried
    ``20260602102212 / 0018_perf_indexes`` with no file in this repo, and three
    production indexes existed that no migration declared. The count guard had
    been green throughout. ``0040`` records the same thing happening in July.

    The integer was also hand-maintained ("bump each time"), which is a prose
    control wearing a Python variable as a disguise -- the reason it lagged
    production for most of every apply-then-merge window.

THE PREFIX TRAP -- read this before changing the matching
    ``mcp__supabase__apply_migration`` takes a NAME, and the names actually used
    frequently omit the numeric prefix the file carries. Seventeen applied rows
    are like this: ledger ``security_kind`` is file ``0037_security_kind.sql``,
    ledger ``agent_readonly_role`` is ``0039_agent_readonly_role.sql``, and so
    on. A naive basename set-diff reports all seventeen as missing. Both sides
    are therefore normalised by stripping a leading ``\\d{3,4}_``.

    Consequence, stated because it is a real limit: two files whose names differ
    only by number (``0012_foo.sql`` and ``0031_foo.sql``) collapse to one key.
    Nothing in this repo does that; the check raises if it ever happens rather
    than silently comparing a smaller set.

WHAT THIS CHECK CANNOT DO
    It compares names. It does not compare CONTENT -- a file edited after being
    applied still matches. Content comparison needs the ledger's ``statements``
    column and a normalising parser, which is a larger change. Do not describe
    this as schema verification; it detects presence/absence, nothing more. The
    restore drill in .github/workflows/backup.yml is the check that exercises
    content, by replaying every file into a clean database.
"""
from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]  # asxos/ -> repo root
MIGRATION_DIR = REPO_ROOT / "migrations"

_NUMBER_PREFIX = re.compile(r"^\d{3,4}_")

# Rows below this version belong to a DIFFERENT project that shared this
# Supabase instance before asxos existed (assistant_conversations, subscriptions,
# account_lockout, ... — 47 of them, Feb-May 2026). asxos's own first migration
# is 0001_initial at exactly this version. An epoch cutoff rather than 47 listed
# strings: the boundary is a fact about the instance's history and will never
# move, whereas a list would have to be maintained.
ASXOS_EPOCH = "20260521085552"

# --- Directional allowlists ---------------------------------------------------
#
# Both assert an EXPECTED STATE and fail when reality moves away from it, in
# either direction. That is the point: a plain "ignore these" list is the prose
# control this check replaces, and would silently mask the entry forever once it
# stopped being true. Every entry here is self-expiring -- when the situation it
# describes is resolved, the check FAILS and tells you to delete the entry.

# Applied, with no file in this repo, and expected to stay that way.
# Verified against production 2026-08-23.
EXPECTED_UNTRACKED: dict[str, str] = {
    "signal_provenance_outcomes": (
        "created signal_outcomes + idx_signal_outcomes_date outside the "
        "migration path; 0025 captures the table retroactively"
    ),
    "founder_marginal_rate_stage3": "tax_settings column work, file never committed",
    # Six rows from 2026-06-11/12 carrying the PREVIOUS project's 01xx
    # numbering. Every table they would have created was probed on 2026-08-23
    # and none exists -- they were removed by 0030_drop_non_asxos_schema. These
    # are dead ledger residue, not live schema.
    "0105_adj_close_quality_flags": "dropped by 0030; table absent from production",
    "0106_universe_history": "dropped by 0030; table absent from production",
    "0107_signal_registry": "dropped by 0030; table absent from production",
    "0108_signal_emissions_research_runs": "dropped by 0030; table absent from production",
    "0109_portfolio_engine": "dropped by 0030; table absent from production",
    "0110_universe_history_research": "dropped by 0030; table absent from production",
}

# In this repo, deliberately never applied, and expected to stay that way.
EXPECTED_UNAPPLIED: dict[str, str] = {
    "signal_outcomes_versioning": (
        "0025 — retroactive capture of an ad-hoc table; every statement is "
        "IF NOT EXISTS, applying it would be a no-op"
    ),
    "segment_map": "0045 — drafted, awaiting a governor decision to apply",
    # 0049 pit_knowledge_tier was here from draft to apply. APPLIED 2026-09-02
    # under James's in-session I5 grant; the entry is removed in the same PR
    # (#192) so the directional allowlist does not flag it as STALE on merge.
}


class MigrationDrift(RuntimeError):
    """Applied migrations and repository files disagree."""


def _key(name: str) -> str:
    """Normalise a ledger name or a filename stem to a comparable key."""
    return _NUMBER_PREFIX.sub("", name.strip()).lower()


def repo_migration_keys(directory: Path | None = None) -> dict[str, str]:
    """Map normalised key -> filename for every .sql file in migrations/."""
    directory = directory or MIGRATION_DIR
    out: dict[str, str] = {}
    for path in sorted(directory.glob("*.sql")):
        key = _key(path.stem)
        if key in out:
            raise MigrationDrift(
                f"two migration files normalise to the same key {key!r}: "
                f"{out[key]} and {path.name}. The numeric prefix is the only "
                "thing distinguishing them, and the ledger does not always "
                "record it — rename one."
            )
        out[key] = path.name
    return out


def compare(
    applied_names: Iterable[str],
    repo_keys: dict[str, str],
    *,
    expected_untracked: dict[str, str] | None = None,
    expected_unapplied: dict[str, str] | None = None,
) -> list[str]:
    """Return a list of problem descriptions; empty means no drift.

    The allowlists are parameters with module-level defaults so the diff logic
    can be exercised against a small fixture repo without the real allowlists
    (which name real files) reporting themselves as stale against it.
    """
    untracked = EXPECTED_UNTRACKED if expected_untracked is None else expected_untracked
    unapplied = EXPECTED_UNAPPLIED if expected_unapplied is None else expected_unapplied
    applied = {_key(n): n.strip() for n in applied_names}
    problems: list[str] = []

    for key, original in sorted(applied.items()):
        if key in repo_keys:
            continue
        reason = untracked.get(original)
        if reason is None:
            problems.append(
                f"APPLIED BUT NOT IN REPO: {original!r} is in "
                f"supabase_migrations.schema_migrations with no matching file "
                f"in migrations/. Production carries schema this repo cannot "
                f"reproduce — the restore drill would rebuild without it. "
                f"Recover the DDL (the ledger's `statements` column holds it), "
                f"commit it, or add it to EXPECTED_UNTRACKED with a reason."
            )

    for original, reason in sorted(untracked.items()):
        key = _key(original)
        if key in repo_keys:
            problems.append(
                f"STALE ALLOWLIST ENTRY: {original!r} is in EXPECTED_UNTRACKED "
                f"({reason}) but migrations/{repo_keys[key]} now exists. The "
                f"entry has done its job — delete it from "
                f"asxos/schema_drift.py."
            )

    for key, filename in sorted(repo_keys.items()):
        if key in applied:
            continue
        if key not in {_key(k) for k in unapplied}:
            problems.append(
                f"IN REPO BUT NOT APPLIED: migrations/{filename} has never been "
                f"applied. If that is intended, add it to EXPECTED_UNAPPLIED "
                f"with a reason; otherwise apply it."
            )

    for original, reason in sorted(unapplied.items()):
        key = _key(original)
        if key in applied:
            problems.append(
                f"STALE ALLOWLIST ENTRY: {original!r} is in EXPECTED_UNAPPLIED "
                f"({reason}) but it is now applied as {applied[key]!r}. The "
                f"entry has done its job — delete it from "
                f"asxos/schema_drift.py."
            )
        elif key not in repo_keys:
            problems.append(
                f"STALE ALLOWLIST ENTRY: {original!r} is in EXPECTED_UNAPPLIED "
                f"but no such file exists in migrations/. Delete the entry."
            )

    return problems


def applied_names_from_rows(rows: Iterable[tuple[str, str]]) -> list[str]:
    """Keep post-epoch ledger rows only. Rows are (version, name)."""
    return [name for version, name in rows if version >= ASXOS_EPOCH]


async def check(conn: object) -> None:
    """Raise MigrationDrift if applied migrations and repo files disagree.

    ``conn`` is any object with an asyncpg-style ``fetch``.
    """
    rows = await conn.fetch(  # type: ignore[attr-defined]
        "SELECT version, name FROM supabase_migrations.schema_migrations ORDER BY version"
    )
    names = applied_names_from_rows([(r["version"], r["name"]) for r in rows])
    problems = compare(names, repo_migration_keys())
    if problems:
        raise MigrationDrift(
            "Migration drift between production and this repo:\n  - "
            + "\n  - ".join(problems)
        )
