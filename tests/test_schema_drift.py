"""Name-based migration drift detection.

The guard this replaces was `count < REQUIRED_MIGRATIONS`, which by construction
could not see a migration applied to production with no file in this repo — the
count rises and it passes. Every test below that asserts a FAILURE is asserting
something the old guard could not detect at all.
"""
from __future__ import annotations

import pytest

from asxos.schema_drift import (
    ASXOS_EPOCH,
    EXPECTED_UNAPPLIED,
    EXPECTED_UNTRACKED,
    MigrationDrift,
    _key,
    applied_names_from_rows,
    compare,
    repo_migration_keys,
)

# A minimal repo shaped like the real one: one plain file, one whose ledger name
# omits the numeric prefix, and the two deliberately-unapplied files.
REPO = {
    "initial": "0001_initial.sql",
    "security_kind": "0037_security_kind.sql",
    "signal_outcomes_versioning": "0025_signal_outcomes_versioning.sql",
    "segment_map": "0045_segment_map.sql",
}
APPLIED = ["0001_initial", "security_kind"]

# Fixture allowlists, so these unit tests exercise the diff logic rather than the
# real ones (which name real files and would report themselves stale against this
# miniature repo). The real allowlists are asserted separately, against the real
# migration directory, in test_live_allowlists_match_the_real_repo.
FIX_UNTRACKED = {"founder_marginal_rate_stage3": "file never committed"}
FIX_UNAPPLIED = {
    "signal_outcomes_versioning": "no-op if applied",
    "segment_map": "awaiting a governor decision",
}


def _compare(applied, repo, **kw):
    kw.setdefault("expected_untracked", FIX_UNTRACKED)
    kw.setdefault("expected_unapplied", FIX_UNAPPLIED)
    return compare(applied, repo, **kw)


def test_clean_repo_has_no_problems() -> None:
    assert _compare(APPLIED, REPO) == []


def test_prefix_is_normalised_on_both_sides() -> None:
    """The trap that would have produced 17 false positives on first run.

    apply_migration takes a NAME, and seventeen applied rows omit the numeric
    prefix their file carries — ledger `security_kind` is file
    `0037_security_kind.sql`. Matching basenames literally reports every one of
    them as applied-but-not-in-repo.
    """
    assert _key("security_kind") == _key("0037_security_kind")
    assert _key("0110_universe_history_research") == "universe_history_research"
    # The whole point: this pair must match despite differing by prefix.
    assert (
        compare(
            ["security_kind"],
            {"security_kind": "0037_security_kind.sql"},
            expected_untracked={},
            expected_unapplied={},
        )
        == []
    )


def test_applied_but_not_in_repo_fails() -> None:
    problems = _compare([*APPLIED, "mystery_migration"], REPO)
    assert len(problems) == 1
    assert "APPLIED BUT NOT IN REPO" in problems[0]
    assert "mystery_migration" in problems[0]


def test_in_repo_but_not_applied_fails() -> None:
    repo = {**REPO, "brand_new": "0046_brand_new.sql"}
    problems = _compare(APPLIED, repo)
    assert len(problems) == 1
    assert "IN REPO BUT NOT APPLIED" in problems[0]
    assert "0046_brand_new.sql" in problems[0]


def test_allowlisted_untracked_is_accepted() -> None:
    assert _compare([*APPLIED, "founder_marginal_rate_stage3"], REPO) == []


def test_allowlisted_unapplied_is_accepted() -> None:
    """0025 and 0045 are in the repo and deliberately never applied."""
    assert _compare(APPLIED, REPO) == []


# --- The self-expiring property ----------------------------------------------
#
# A plain "ignore these" list is the prose control this check replaces: once an
# entry stops being true it masks the very thing it was written for, forever.
# Both allowlists therefore assert an expected state and fail when it changes.


def test_untracked_allowlist_expires_when_the_file_appears() -> None:
    repo = {**REPO, "founder_marginal_rate_stage3": "0046_founder_marginal_rate_stage3.sql"}
    problems = _compare([*APPLIED, "founder_marginal_rate_stage3"], repo)
    assert len(problems) == 1
    assert "STALE ALLOWLIST ENTRY" in problems[0]
    assert "delete it" in problems[0]


def test_unapplied_allowlist_expires_when_it_gets_applied() -> None:
    """The case that matters most: 0045 is applied one day and must not stay masked."""
    problems = _compare([*APPLIED, "0045_segment_map"], REPO)
    assert len(problems) == 1
    assert "STALE ALLOWLIST ENTRY" in problems[0]
    assert "segment_map" in problems[0]


def test_unapplied_allowlist_expires_when_the_file_is_deleted() -> None:
    repo = {k: v for k, v in REPO.items() if k != "segment_map"}
    problems = _compare(APPLIED, repo)
    assert len(problems) == 1
    assert "STALE ALLOWLIST ENTRY" in problems[0]


# --- Epoch cutoff -------------------------------------------------------------


def test_pre_asxos_rows_are_excluded_by_epoch() -> None:
    """47 rows predate asxos on a shared Supabase instance; 0001_initial is the epoch."""
    rows = [
        ("20260217004354", "add_assistant_conversations"),
        ("20260513114900", "0100_property_alpha"),
        (ASXOS_EPOCH, "0001_initial"),
        ("20260821080458", "fundamentals_pit_currency"),
    ]
    assert applied_names_from_rows(rows) == ["0001_initial", "fundamentals_pit_currency"]


def test_epoch_boundary_is_inclusive_of_initial() -> None:
    assert applied_names_from_rows([(ASXOS_EPOCH, "0001_initial")]) == ["0001_initial"]


# --- Real repo ----------------------------------------------------------------


def test_repo_keys_are_unique_and_cover_every_file() -> None:
    keys = repo_migration_keys()
    assert len(keys) == 50, f"expected 50 .sql files, found {len(keys)}"
    assert "perf_indexes" in keys, "0018 must be tracked after its reconstruction"
    assert "screening_runs_comment_fix" in keys, "0046 comment fix must be tracked"
    assert "brief_section_gold" in keys, "0047 gold table must be tracked"
    assert "decision_packets" in keys, "0048 decision-spine tables must be tracked"
    assert "pit_knowledge_tier" in keys, "0049 knowledge-tier column must be tracked"
    assert "research_registry" in keys, "0050 research registry must be tracked"
    assert "theme_candidates" in keys, "0051 theme/candidate tables must be tracked"
    assert "initial" in keys


def test_duplicate_normalised_keys_raise() -> None:
    """Two files differing only by number collapse to one key — refuse rather than
    silently compare a smaller set."""
    import pathlib
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        d = pathlib.Path(tmp)
        (d / "0012_foo.sql").write_text("-- x")
        (d / "0031_foo.sql").write_text("-- x")
        with pytest.raises(MigrationDrift, match="normalise to the same key"):
            repo_migration_keys(d)


def test_live_allowlists_match_the_real_repo() -> None:
    """Every EXPECTED_UNAPPLIED entry must name a file that actually exists, and
    no EXPECTED_UNTRACKED entry may name one that does. This is the same
    self-expiry the unit tests cover, asserted against the real migrations/ so a
    stale entry fails in CI without a database."""
    keys = repo_migration_keys()
    for name in EXPECTED_UNAPPLIED:
        assert _key(name) in keys, f"{name!r} is allowlisted as unapplied but has no file"
    for name in EXPECTED_UNTRACKED:
        assert _key(name) not in keys, (
            f"{name!r} is allowlisted as untracked but migrations/ now has a file — "
            "delete the entry"
        )
