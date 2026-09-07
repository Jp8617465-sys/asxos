"""``asxos.backlog`` — the deterministic pre-gate for the ``backlog-roll`` lane.

Two layers, both pinned:

1. Selection logic on a small fixture: ranking, dependency gating, the derived
   denied-path eligibility, overlap skipping, the click-list, and the exit codes.
2. **Drift**: the module's denied set must cover everything the real guards deny.
   ``TestDeniedSetMirrorsTheGuards`` parses ``.claude/hooks/unattended-guard.sh`` and
   ``.claude/settings.json`` and fails if either widens without this module following.
   The hook is the control; this list is the pre-gate. A pre-gate that lags the control
   would start work the lane can never finish.

Also asserts the checked-in seed parses and, as of seeding, picks only the two proposal
drafts James already asked for — so the first real fire is predictable.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml

from asxos.backlog import (
    DEFAULT_BACKLOG,
    DENIED_FILES,
    DENIED_PREFIXES,
    BacklogSchemaError,
    click_list,
    is_denied_path,
    main,
    parse,
    paths_overlap,
    pick,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def _doc(items: list[dict]) -> dict:
    return {"version": 1, "updated": "2026-09-05", "items": items}


def _row(
    id: str,
    *,
    owner: str = "arbi",
    status: str = "open",
    route: str = "build",
    depends_on: list[str] | None = None,
    paths: list[str] | None = None,
) -> dict:
    return {
        "id": id,
        "title": f"item {id}",
        "phase": id[0],
        "owner": owner,
        "status": status,
        "depends_on": depends_on or [],
        "route": route,
        "paths": paths if paths is not None else [f"docs/proposals/{id}.md"],
        "source": "fixture",
    }


# --- denied paths --------------------------------------------------------------------


class TestDeniedPaths:
    @pytest.mark.parametrize(
        "path",
        [
            "asxos/domain/tax/positions.py",
            "asxos/domain/portfolio/allocator.py",
            "asxos/domain/models/x.py",
            "asxos/domain/theses/service.py",
            ".claude/hooks/pr-draft-guard.sh",
            ".claude/agents/arbi.md",
            ".claude/settings.json",
            ".github/workflows/full-check.yml",
            "migrations/0053_x.sql",
            "CLAUDE.md",
            "docs/product/north-star.md",
            "docs/product/memory/approved-lessons.md",
            "render.yaml",
        ],
    )
    def test_guarded_paths_are_denied(self, path: str) -> None:
        assert is_denied_path(path)

    @pytest.mark.parametrize(
        "path",
        [
            "docs/proposals/anything.md",
            "tests/test_backup_script.py",
            "asxos/backlog.py",
            "asxos/domain/decision_engine/builder.py",
            "docs/product/roadmap-state.md",
            "docs/product/backlog.yaml",
        ],
    )
    def test_ordinary_paths_are_allowed(self, path: str) -> None:
        assert not is_denied_path(path)

    def test_a_directory_containing_a_guarded_file_is_denied(self) -> None:
        # Coarse globs cannot launder a guarded file.
        assert is_denied_path("docs/product/")
        assert is_denied_path("docs/product/memory/")
        assert is_denied_path(".claude/")
        assert is_denied_path("asxos/domain/")
        assert is_denied_path("")

    def test_normalisation(self) -> None:
        assert is_denied_path("./migrations/0001.sql")
        assert is_denied_path("/CLAUDE.md")
        assert not is_denied_path("./docs/proposals/x.md")

    @pytest.mark.parametrize(
        "path",
        [
            "docs/proposals/../product/north-star.md",
            "docs/**",
            "docs/proposals/*.md",
            "docs//proposals/x.md",
            r"docs\proposals\x.md",
            "/docs/proposals/x.md",
        ],
    )
    def test_non_literal_or_non_relative_scopes_fail_closed(self, path: str) -> None:
        assert is_denied_path(path)


class TestOverlap:
    def test_distinct_files_in_one_dir_do_not_overlap(self) -> None:
        assert not paths_overlap(["docs/proposals/a.md"], ["docs/proposals/b.md"])

    def test_same_file_overlaps(self) -> None:
        assert paths_overlap(["docs/proposals/a.md"], ["docs/proposals/a.md"])

    def test_dir_contains_file_overlaps_both_ways(self) -> None:
        assert paths_overlap(["docs/proposals/"], ["docs/proposals/a.md"])
        assert paths_overlap(["docs/proposals/a.md"], ["docs/proposals/"])


# --- schema ---------------------------------------------------------------------------


class TestSchema:
    def test_minimal_valid(self) -> None:
        items = parse(_doc([_row("A-1")]))
        assert [i.id for i in items] == ["A-1"]

    @pytest.mark.parametrize(
        "mutation, fragment",
        [
            (lambda r: r.update(status="shipped"), "status"),
            (lambda r: r.update(owner="bot"), "owner"),
            (lambda r: r.update(route="yolo"), "route"),
            (lambda r: r.update(phase="B"), "disagrees"),
            (lambda r: r.update(extra=1), "unknown keys"),
            (lambda r: r.pop("source"), "missing keys"),
            (lambda r: r.update(depends_on=["Z-9"]), "unknown id"),
            (lambda r: r.update(depends_on=["A-1"]), "itself"),
            (lambda r: r.update(paths="not-a-list"), "list of strings"),
        ],
    )
    def test_rejects(self, mutation, fragment: str) -> None:
        row = _row("A-1")
        mutation(row)
        with pytest.raises(BacklogSchemaError, match=fragment):
            parse(_doc([row]))

    def test_rejects_duplicate_and_bad_ids(self) -> None:
        with pytest.raises(BacklogSchemaError, match="duplicate"):
            parse(_doc([_row("A-1"), _row("A-1")]))
        with pytest.raises(BacklogSchemaError, match="bad id"):
            parse(_doc([_row("F-1")]))

    def test_rejects_wrong_version(self) -> None:
        with pytest.raises(BacklogSchemaError, match="version"):
            parse({"version": 2, "items": [_row("A-1")]})

    def test_rejects_path_traversal_and_dependency_cycles(self) -> None:
        with pytest.raises(BacklogSchemaError, match="literal repo-relative"):
            parse(_doc([_row("A-1", paths=["docs/proposals/../product/north-star.md"])]))
        with pytest.raises(BacklogSchemaError, match="dependency cycle"):
            parse(
                _doc(
                    [
                        _row("A-1", depends_on=["A-2"]),
                        _row("A-2", depends_on=["A-1"]),
                    ]
                )
            )


# --- selection --------------------------------------------------------------------------


class TestSelection:
    def test_ranking_phase_then_dependents_then_id(self) -> None:
        items = parse(
            _doc(
                [
                    _row("B-1"),
                    _row("A-2"),
                    # A-1 has one open dependent (C-1), A-2 has none -> A-1 first.
                    _row("A-1"),
                    _row("C-1", depends_on=["A-1"]),
                ]
            )
        )
        picked, skipped = pick(items, max_items=10)
        assert [i.id for i in picked] == ["A-1", "A-2", "B-1"]
        assert skipped == []

    def test_dependency_gating_treats_unmerged_as_not_done(self) -> None:
        items = parse(
            _doc(
                [
                    _row("A-1", status="built-unmerged"),
                    _row("A-2", status="done"),
                    _row("A-3", status="void"),
                    _row("B-1", depends_on=["A-1"]),  # blocked
                    _row("B-2", depends_on=["A-2"]),  # ok
                    _row("B-3", depends_on=["A-3"]),  # ok (void counts)
                ]
            )
        )
        picked, _ = pick(items, max_items=10)
        assert [i.id for i in picked] == ["B-2", "B-3"]

    def test_only_arbi_or_both_with_buildable_route(self) -> None:
        items = parse(
            _doc(
                [
                    _row("A-1", owner="james", route="james"),
                    _row("A-2", owner="both", route="observe"),
                    _row("A-3", owner="arbi", route="attended"),
                    _row("A-4", owner="time", route="observe"),
                    _row("A-5", owner="both", route="mission"),
                    _row("A-6", owner="arbi", route="build"),
                ]
            )
        )
        picked, _ = pick(items, max_items=10)
        assert [i.id for i in picked] == ["A-5", "A-6"]

    def test_denied_path_is_never_picked_even_when_open_and_owned(self) -> None:
        items = parse(
            _doc(
                [
                    _row("A-1", paths=["asxos/domain/tax/lots.py"]),
                    _row("A-2", paths=[".github/workflows/full-check.yml"]),
                    _row("A-3", paths=["docs/proposals/ok.md", "migrations/0099.sql"]),
                    _row("A-4", paths=[]),  # no paths => nothing to build
                    _row("A-5", paths=["docs/proposals/ok.md"]),
                ]
            )
        )
        picked, _ = pick(items, max_items=10)
        assert [i.id for i in picked] == ["A-5"]

    def test_overlap_skips_the_later_pick_this_fire(self) -> None:
        items = parse(
            _doc(
                [
                    _row("A-1", paths=["docs/proposals/x.md"]),
                    _row("A-2", paths=["docs/proposals/"]),  # contains A-1's file
                    _row("A-3", paths=["tests/test_x.py"]),
                ]
            )
        )
        picked, skipped = pick(items, max_items=10)
        assert [i.id for i in picked] == ["A-1", "A-3"]
        assert [i.id for i in skipped] == ["A-2"]

    def test_max_items_caps(self) -> None:
        items = parse(_doc([_row("A-1"), _row("A-2"), _row("A-3")]))
        picked, _ = pick(items, max_items=2)
        assert [i.id for i in picked] == ["A-1", "A-2"]

    def test_click_list_includes_james_routes_and_built_unmerged_work(self) -> None:
        items = parse(
            _doc(
                [
                    _row("A-1", owner="james", route="james"),
                    _row("A-2", owner="james", route="james", depends_on=["A-1"]),
                    _row("A-3", owner="both", route="james"),
                    _row("A-4", owner="james", route="james", status="done"),
                    _row("A-5", owner="james", route="james", status="built-unmerged"),
                    _row("A-6", owner="arbi", route="build", status="built-unmerged"),
                ]
            )
        )
        assert [i.id for i in click_list(items)] == ["A-1", "A-3", "A-5", "A-6"]


# --- CLI + exit codes -------------------------------------------------------------------


class TestCli:
    def _write(self, tmp_path: Path, items: list[dict]) -> Path:
        p = tmp_path / "backlog.yaml"
        p.write_text(yaml.safe_dump(_doc(items), sort_keys=False), encoding="utf-8")
        return p

    def test_exit_0_and_json_shape_when_picked(self, tmp_path: Path, capsys) -> None:
        p = self._write(tmp_path, [_row("A-1"), _row("B-1", owner="james", route="james")])
        assert main(["--backlog", str(p)]) == 0
        out = json.loads(capsys.readouterr().out)
        assert {
            "generated",
            "backlog_updated",
            "eligible",
            "picked",
            "skipped_overlap",
            "click_list",
        } <= out.keys()
        assert [i["id"] for i in out["picked"]] == ["A-1"]
        assert [i["id"] for i in out["click_list"]] == ["B-1"]

    def test_exit_3_when_nothing_eligible_but_click_list_still_emitted(
        self, tmp_path: Path, capsys
    ) -> None:
        p = self._write(tmp_path, [_row("A-1", owner="james", route="james")])
        assert main(["--backlog", str(p)]) == 3
        out = json.loads(capsys.readouterr().out)
        assert out["picked"] == []
        assert [i["id"] for i in out["click_list"]] == ["A-1"]

    def test_exit_2_on_schema_error(self, tmp_path: Path, capsys) -> None:
        p = self._write(tmp_path, [_row("A-1", status="nope")])
        assert main(["--backlog", str(p)]) == 2
        assert "schema error" in capsys.readouterr().err

    def test_exit_2_on_missing_file(self, tmp_path: Path) -> None:
        assert main(["--backlog", str(tmp_path / "missing.yaml")]) == 2

    @pytest.mark.parametrize("value", ["0", "-1", "4"])
    def test_exit_2_when_max_is_outside_bounded_lane_limit(
        self, tmp_path: Path, capsys, value: str
    ) -> None:
        p = self._write(tmp_path, [_row("A-1")])
        assert main(["--backlog", str(p), "--max", value]) == 2
        assert "--max must be between 1 and 3" in capsys.readouterr().err


# --- the checked-in seed ---------------------------------------------------------------


class TestSeed:
    def test_seed_parses(self) -> None:
        items = __import__("asxos.backlog", fromlist=["load"]).load(DEFAULT_BACKLOG)
        assert len(items) >= 60
        # The seed must not declare anything eligible that the guard would deny. E-11 is
        # the deliberate negative example: open, arbi-owned, and on a .github path.
        for it in items:
            if (
                it.owner in {"arbi", "both"}
                and it.route in {"build", "mission"}
                and it.status == "open"
            ):
                denied = any(is_denied_path(p) for p in it.paths)
                assert denied == (it.id == "E-11"), it.id

    def test_ids_rank_numerically_not_lexically(self) -> None:
        items = parse(
            _doc(
                [
                    _row("B-10", owner="james", route="james"),
                    _row("B-5", owner="james", route="james"),
                    _row("B-13a", owner="james", route="james"),
                    _row("B-13", owner="james", route="james"),
                ]
            )
        )
        assert [i.id for i in click_list(items)] == ["B-5", "B-10", "B-13", "B-13a"]

    def test_seed_after_the_merge_train_landed_is_click_list_only(self) -> None:
        """Re-pinned 2026-09-06 (was: "after the two proposal drafts landed", 09-05).
        James un-drafted and merged the whole #185–#200 stack on 2026-09-05, so A-0 and
        A-2…A-17 are done, B-13a/B-14a landed inside #200, C-2 and C-11 were observed,
        and the lead click is now A-20 — the HC_BACKLOG_URL secret the backlog-roll lane
        fails without. Still no arbi-owned item that is open, guard-safe AND buildable
        without a live session: E-17 (doc-expiry sweep) is deliberately `attended`, so
        the picker correctly exits 3 and the click-list is the whole output. Re-pin
        deliberately if a future seed change makes something newly eligible."""
        items = __import__("asxos.backlog", fromlist=["load"]).load(DEFAULT_BACKLOG)
        picked, skipped = pick(items, max_items=10)
        assert picked == []
        assert skipped == []
        clicks = [i.id for i in click_list(items)]
        assert clicks[0] == "A-20", clicks
        assert "A-24" in clicks  # the issue-snapshot ruleset red is James's (.github path)
        assert "A-0" not in clicks  # discharged 2026-09-05
        assert "B-13a" not in clicks and "B-14a" not in clicks  # merged in #200
        assert "E-11" not in clicks  # .github path, correctly refused regardless of route
        assert "E-17" not in clicks  # attended, arbi-owned: neither a pick nor a click


# --- drift against the real guards ------------------------------------------------------


class TestDeniedSetMirrorsTheGuards:
    HOOK = REPO_ROOT / ".claude" / "hooks" / "unattended-guard.sh"
    SETTINGS = REPO_ROOT / ".claude" / "settings.json"

    def test_capital_fragments_are_denied_prefixes(self) -> None:
        text = self.HOOK.read_text(encoding="utf-8")
        block = re.search(r"CAPITAL_FRAGMENTS=\((.*?)\)", text, re.S)
        assert block, "CAPITAL_FRAGMENTS not found in unattended-guard.sh"
        frags = re.findall(r'"([^"]+)"', block.group(1))
        assert frags, "no fragments parsed"
        for frag in frags:
            assert frag in DENIED_PREFIXES, f"{frag} is in the hook but not in asxos.backlog"

    def test_authority_case_patterns_are_denied(self) -> None:
        text = self.HOOK.read_text(encoding="utf-8")
        fn = re.search(r"is_authority_path\(\) \{(.*?)\n\}", text, re.S)
        assert fn, "is_authority_path() not found"
        pats = re.findall(r"^\s*([^\s#)]+)\)\s*return 0", fn.group(1), re.M)
        assert pats, "no case patterns parsed"
        for alt in "|".join(pats).split("|"):
            alt = alt.strip()
            if alt.endswith("/*"):
                assert alt[:-1] in DENIED_PREFIXES, alt
            else:
                assert alt in DENIED_FILES, alt

    def test_settings_edit_denies_are_covered(self) -> None:
        deny = json.loads(self.SETTINGS.read_text(encoding="utf-8"))["permissions"]["deny"]
        edits = [d for d in deny if d.startswith("Edit(")]
        assert edits
        for rule in edits:
            target = rule[len("Edit(") : -1].lstrip("/")
            if target.endswith("/**"):
                assert target[: -len("**")] in DENIED_PREFIXES, rule
            else:
                assert target in DENIED_FILES, rule
